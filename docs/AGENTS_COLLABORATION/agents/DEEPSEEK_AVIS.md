# Avis DeepSeek

Agent : DeepSeek
Date : 25 mai 2026
Rôle : Analyse alternative, détection risques, propositions d'optimisation

## Contexte initial

Lecture demandée : `AGENTS.md`, `OBJECTIFS_ACTIFS.md`, `DEEPSEEK_AVIS.md`.

Note : `OBJECTIFS_ACTIFS.md` n'a pas été trouvée dans le dépôt lors de l'analyse (repo local non à jour). L'analyse se base sur les sources disponibles et la logique de `startVoice()` plus `integrations/openai/web_voice_bridge.py`.

---

## OBJECTIF 001 — Analyse pipeline voix Luna

### Architecture globale

1. **Vue navigateur / UI**
   - Le bouton `lunaVoiceBtn` déclenche `startVoice(false)`.
   - `startVoice()` bascule l'état local, affiche l'overlay vocal, initialise les contextes audio et la capture micro.
   - Le micro est demandé avec `navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } })`.
   - Le code essaie d'utiliser un `AudioWorklet` si disponible, sinon un `ScriptProcessorNode` de secours.
   - Le flux audio est converti en PCM16 à 24 kHz, encodé en base64 puis envoyé via WebSocket vers `ws://` ou `wss://.../ws/luna-voice`.

2. **Reconnexion et historique**
   - En cas de fermeture WS, `onclose` tente une reconnexion automatique jusqu'à `_voiceMaxReconnects` (3 tentatives).
   - Lors de la reconnexion, les 10 dernières lignes de transcript sont exposées via `history=` dans l'URL.
   - Ceci permet au serveur de réinjecter un historique court dans le contexte OpenAI.

3. **Client / WebSocket**
   - Le client gère les messages `ready`, `audio`, `audio_done`, `interrupt`, `transcript`, `tool_call`, `warning`, `ended`, `error`.
   - Le client maintient un ping applicatif toutes les 20 s via `pong` et un timer local / serveur.
   - `stopVoice()` envoie un `stop` au serveur, ferme le WebSocket, arrête la capture micro, et injecte la transcription dans le chat.

4. **Serveur `/ws/luna-voice`**
   - Route FastAPI / Starlette acceptant le WebSocket.
   - Authentification par JWT `token` query param.
   - Vérification de la clé OpenAI et du budget avec `_check_budget_guard()` avant d'ouvrir la session.
   - Construit un contexte vocal enrichi avec `build_voice_context()` et une clause « mode assistant vocal direct » pour Jarvis.
   - Charge l'historique si présent, sinon tente de récupérer les derniers messages cross-canal stockés en Redis.
   - Appelle `WebVoiceBridge(...)` avec `tool_handler` et paramètres d'environnement.

5. **Bridge OpenAI `WebVoiceBridge`**
   - Ouvre un WebSocket vers l'API OpenAI Realtime (`wss://api.openai.com/v1/realtime?model=...`).
   - Configure la session avec audio entrée/sortie PCM 24 kHz, VAD serveur, outils (`VOICE_TOOLS`) et choix automatique.
   - Lance 3 tâches concurrentes : relais client→OpenAI, relais OpenAI→client, timer/max duration, keepalive, elapsed broadcast.
   - Transmet les chunks audio du navigateur vers OpenAI sous forme `input_audio_buffer.append`.
   - Reçoit les paquets audio de réponse OpenAI et les relaie au navigateur.
   - Gère les événements de transcription utilisateur / Luna et les renvoie au client.
   - Traite les tool calls via `_handle_tool_call()` et renvoie le résultat au modèle et au client.
   - Garde un journal des erreurs clients / OpenAI, et stoppe la session après seuils définis.

6. **Après-session**
   - Quand le bridge se termine, le serveur sauvegarde la transcription dans la mémoire.
   - Si la voix dure > 0.5 min et contient 4+ échanges, le serveur génère un compte-rendu automatique via l'API chat OpenAI.
   - Le résumé vocal est stocké comme note et peut être poussé en notification Redis.

---

### Risques cachés identifiés

1. **Dépendance forte à l'API OpenAI Realtime**
   - Le code attend des événements spécifiques (`response.audio.delta`, `conversation.item.input_audio_transcription.completed`, `response.function_call_arguments.done`, etc.).
   - Tout changement de protocole OpenAI ou du modèle utilisé peut casser la voix sans alerte globale.

2. **Reconnexion WebSocket fragile**
   - La reconnexion repose sur l'état du WebSocket et une logique locale simple.
   - Si la fermeture WS est causée par un `4001` ou `1011`, la session termine proprement ; sinon elle tente plusieurs fois.
   - Le token JWT en query param expose potentiellement un vecteur si le lien est intercepté.

3. **Audio capture / compatibilité WebView**
   - Le fallback vers `ScriptProcessorNode` est utile, mais sur certains WebView mobiles cela peut être bloqué ou mal pris en charge.
   - La détection `_isWebView` est très basique (`/LunaApp/` dans userAgent), donc d'autres WebView peuvent ignorer la logique.

4. **Gestion des erreurs utilisateur**
   - `startVoice()` gère `NotAllowedError`, `NotFoundError`, `NotReadableError` et affiche un message.
   - Par contre, si `voiceWs` se bloque avant `ready`, le retour utilisateur peut rester flou.

5. **Outils vocaux et hallucinations**
   - En cas d'échec d'un outil d'action, le bridge ajoute une clé `IMPORTANT` pour forcer Luna à dire que l'action a échoué.
   - Cela couvre bien l'anti-hallucination, mais dépend du modèle et du prompt pour être effectif.

6. **Risque de coût / quotas**
   - Le bridge vérifie le budget avant ouverture, mais ne semble pas limiter le nombre de sessions au runtime à part `_realtime_semaphore`.
   - La durée max côté serveur est réglable via `VOICE_MAX_DURATION`, mais le client peut aussi interrompre après 15 min.

---

### Optimisations possibles

1. **Renforcer l'authentification WebSocket**
   - Passer à un header `Authorization` plutôt qu'un `token` en query string si possible.
   - Ajouter une durée de vie courte ou un nonce pour limiter le risque de replay.

2. **Améliorer le suivi d'état côté client**
   - Actuellement l'état vocal est principalement visuel et local.
   - Ajouter des codes d'erreur plus structurés au client pour distinguer « service indisponible » / « micro refusé » / « timeout OpenAI ».

3. **Clarifier la gestion des tools**
   - Documenter ou tracer l'enchaînement `response.function_call_arguments.done` → `tool_handler` → `response.create`.
   - Vérifier que les outils de type `hang_up` sont bien traités comme fin de session sans boucle infinie.

4. **Consolider le fallback audio**
   - Au lieu de tester seulement l'User-Agent LunaApp, détecter systématiquement la présence d'`AudioWorklet` avant de choisir le chemin.
   - Ajouter un message spécifique si la capture audio est activée mais que la conversion PCM échoue.

5. **Monitoring / métriques**
   - Le serveur peut déjà publier `web_voice_bridge_available` et la présence de la route.
   - Il serait utile d'ajouter un indicateur de sessions actives, reconnects et erreurs OpenAI dans `GET /api/admin/objectives`.

---

### Verdict DeepSeek — Objectif 001

La famille `startVoice()` + `web_voice_bridge.py` forme une architecture cohérente :
- le client capture et encode l'audio,
- le serveur relaye le flux vers OpenAI Realtime,
- la réponse audio, les transcriptions et les tool calls sont renvoyés au navigateur.

**Points forts** : design direct navigateur ↔ OpenAI sans Twilio/Tavus, gestion de reconnexion et d'historique contextuel, stockage de transcript et génération automatique de compte-rendu.

**Points d'attention** : dépendance critique au protocole OpenAI Realtime, auth WebSocket en query param, compatibilité WebView / capture micro potentiellement fragile.

**Conclusion** : la pipeline voix est bien structurée, mais elle mérite une revue de robustesse sur les parcours d'erreur et l'authentification WS avant une mise en production large.

---

## OBJECTIF 003 — Cerveau APK / télémétrie appareil réel

### Schéma heartbeat proposé

Le client APK envoie un heartbeat périodique (tous les 30s à 5min selon batterie/réseau) vers un endpoint dédié. Payload JSON minimal :

```json
{
   "ts": 1690000000,
   "tenant_id": "<tenant-id-ou-hash>",
   "apk_version": "1.2.3",
   "frontend_build": "2026-05-25:abcd1234",
   "webview_user_agent": "...",
   "cloudrun_url": "https://...",
   "screen_active": true,
   "mic_permission": "granted|denied|unknown",
   "voice_button_pressed": false,
   "ws_voice_state": "closed|connecting|open|error",
   "audio_sent": false,
   "audio_received": false,
   "last_js_error": "Error message truncated...",
   "last_contact": 1690000000
}
```

Remarques : envoyer uniquement des indicateurs (flags, versions, messages courts). Jamais d'audio brut ni de transcript.

### Événements APK critiques proposés

- `apk_start` — APK démarre
- `heartbeat` — périodique (voir schéma)
- `frontend_loaded` — page index.html chargée avec `build_version`
- `voice_button` — utilisateur appuie sur le bouton vocal
- `ws_open` / `ws_close` / `ws_error` — état WebSocket voix
- `audio_sent_chunk` (compteur) — indica si audio a bien été envoyé (no raw data)
- `audio_received_flag` — vrai si le client a reçu audio de réponse
- `no_audio_timeout` — pas d'audio reçu après Xs
- `mic_permission_change` — permission micro modifiée
- `js_error` — message+stack truncated
- `app_foreground` / `app_background`

Chaque événement doit être compact (timestamps, petits codes, counts) et soumis au même endpoint `POST /api/apk/telemetry/events`.

### Fichiers Android / WebView à inspecter

- `android-app/AndroidManifest.xml` — permissions et version
- `android-app/java/.../MainActivity.java` — WebView setup, `sendLog()` existant
- `android-app/build.gradle` — versionCode/versionName
- `static/index.html` — variable `__BUILD__` ou similaire (actuellement absente)
- WebView client hooks : `onConsoleMessage`, `onReceivedError`, `shouldOverrideUrlLoading`

### Endpoint serveur proposé

- `POST /api/apk/telemetry/heartbeat` — ingestion heartbeat (idempotent, small JSON)
- `POST /api/apk/telemetry/events` — ingestion événement (batched allowed)

Sécurité : s'authentifier via le même mécanisme que l'APK pour les autres appels (token utilisateur existant). Ne pas inclure de nouveaux secrets ni de clés en clair.

Rate limiting : max 1 req / 10s par appareil ; contrôle global par tenant.

### Stockage proposé

- **Temps-réel court** : Redis (liste ou stream) — derniers N heartbeats par tenant
- **Persistant agrégé** : Redis actuel suffit pour phase 1 (colonnes : tenant, apk_version, frontend_build, last_contact, ws_state)
- **Erreurs JS** : tronquer les stacks, ne pas stocker complets, max 500 chars
- **Rétention** : 30 jours détaillé, 12 mois agrégé (counts/versions)

### Affichage admin proposé

- Dashboard par tenant : dernier contact, apk_version distribution, frontend_build mismatch alerts, sessions vocales actives, reconnect rate
- Liste appareils récents (no PII) : tenant, apk_version, frontend_build, last_contact, ws_state, warning flags
- Visualisation erreurs JS (top messages, fréquence) et time-series audio loss/timeout
- Bouton action safe : demander au client d'envoyer un log compact (consent demandé) — pas d'accès à audio ni commandes de déploiement

### Risques

- **Vie privée** : envoyer trop d'informations peut devenir fingerprinting. Éviter identifiants persistants non-hashés.
- **Sécurité** : endpoint d'ingestion augmente la surface d'attaque. Auth + rate-limit indispensables.
- **Charge** : heartbeats fréquents peuvent monter en charge. Throttle côté client et serveur.
- **Données sensibles** : ne pas stocker tokens, cookies, audio brut ni transcripts.

### Correction minimale recommandée

1. Ajouter côté APK un collecteur léger qui capte les signaux listés, agrège localement (ex: 30s) et envoie un heartbeat — **en enrichissant `sendLog()` existant** (pattern déjà prouvé).
2. Mettre en place `POST /api/apk/telemetry/heartbeat` (auth existante) avec validation et rate-limiting.
3. Stocker en Redis les 10 derniers heartbeats par tenant.
4. Mettre en place règles d'alerte : mismatch frontend_build vs Cloud Run, absence de contact > 5min, taux de reconnect > 10%.

### Validation Ludovic nécessaire

- Autorisation explicite pour l'utilisation de l'endpoint et la conservation des métriques.
- Définir la politique de rétention et le niveau d'agrégation autorisé.
- Ok sur la méthode d'authentification (usage du token appliqué déjà présent dans l'APK).

---

*Fin de l'analyse DeepSeek — Objectifs 001 et 003.*
