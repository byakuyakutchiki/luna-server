# Avis Kimi — Objectif 003 Cerveau APK

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Audit documentaire promesse utilisateur vs réalité APK
Date : 2026-05-25
Branche : `kimi/objectif-003-cerveau-apk`

---

## 1. Audit documentation : promesse vs observable réellement

### Promesses documentées (source de vérité)

| Promesse | Document source | Ligne / section |
|---|---|---|
| "Voix doit permettre à l'utilisateur de parler naturellement à Luna" | `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` | § Vision produit |
| "Feedback immédiat en moins d'une seconde" | `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` | § Mention spéciale fondateur |
| "Jamais de silence si le micro, OpenAI, quota, WebSocket ou navigateur bloque" | `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` | § Mention spéciale fondateur |
| "Voix féminine par défaut : coral" | `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` | § Mention spéciale fondateur |
| "Clic bouton Voix → feedback immédiat → permission micro → OpenAI Realtime → WebSocket voix → voix féminine → budget/quota → contexte → outils autorisés → transcription → mémoire/rapport → cleanup" | `docs/CAHIER_DES_CHARGES_MONITORING.md` | §12 Objectif utilisateur |
| "Bouton Voix silencieux au clic = critical" | `docs/CAHIER_DES_CHARGES_MONITORING.md` | §12 Statuts |
| "Voix dans APK : fix AudioWorklet déployé mais à valider sur appareil réel" | `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md` | § Points d'attention actifs |

### Ce qui est observable réellement aujourd'hui

| Élément | Observable ? | Comment |
|---|---|---|
| Code du bouton voix présent | ✅ OUI | `_check_objective_voix` vérifie `"lunaVoiceBtn" in _html` |
| Bouton cablé au bon flux | ✅ OUI | `_check_objective_voix` vérifie `"startVoice" in _html` et `"ws/luna-voice" in _html` |
| Feedback clic présent dans le code | ✅ OUI | `_check_objective_voix` vérifie `"voiceOverlay" in _html` |
| Gestion refus micro présente dans le code | ✅ OUI | `_check_objective_voix` vérifie `"NotAllowedError" in _html` |
| Voix féminine configurée côté serveur | ⚠️ PARTIEL | `_check_objective_voix` vérifie `OPENAI_VOICE_NAME` env var, mais ne vérifie pas que la valeur runtime est bien appliquée à OpenAI |
| **Un téléphone réel a cliqué sur le bouton** | ❌ NON | Aucun événement, aucun log, aucune métrique |
| **Le micro s'est activé avec succès sur un téléphone** | ❌ NON | Aucune télémétrie APK ne remonte cette info |
| **Un WebSocket voix s'est ouvert depuis un téléphone** | ❌ NON | Le serveur voit les connexions WS mais ne sait pas distinguer téléphone vs navigateur desktop |
| **De l'audio a été envoyé par le téléphone** | ❌ NON | Le serveur reçoit des chunks audio mais ne sait pas si c'est du téléphone |
| **De l'audio a été reçu par le téléphone** | ❌ NON | Le serveur envoie des deltas audio mais ne sait pas si le téléphone les a joués |
| **L'utilisateur a entendu Luna parler** | ❌ NON | Aucun signal de confirmation côté client |
| **La voix entendue était bien féminine** | ❌ NON | Aucune validation utilisateur remontée |
| **La session s'est terminée normalement** | ❌ NON | Pas d'événement de fin de session côté APK |
| **La transcription a été sauvegardée** | ⚠️ PARTIEL | Le serveur sauvegarde, mais ne sait pas si c'était une session téléphone |
| **L'APK est vivante et à jour** | ❌ NON | Aucun heartbeat APK existant |

### Verdict audit

**Le monitoring actuel est un "audit de code", pas un "audit d'expérience".**

Il prouve que le serveur est prêt à servir la voix, mais il ne prouve pas qu'un appareil réel a jamais utilisé cette fonctionnalité avec succès. Le statut `ok` affiché pour "voix" dans `ETAT_ACTUEL.md` est fondé sur la présence de code et de configuration, pas sur une validation empirique sur l'appareil fondateur.

---

## 2. Signaux manquants pour prouver fonctionnalité sur appareil réel

### Signaux déjà présents côté APK (MainActivity.java)

L'APK dispose déjà de :
- `sendLog()` (ligne 337-357) : envoie des logs vers `/api/logs/client`
- `onConsoleMessage()` (ligne 206-214) : capture les logs JS et les envoie au serveur
- `onPageStarted()` / `onPageFinished()` (ligne 313-320) : log navigation
- `onPermissionRequest()` (ligne 217-252) : gère les permissions micro/caméra
- `onReceivedError()` (ligne 308-310) : log les erreurs WebView
- `checkForUpdate()` (ligne 435-470) : vérifie version serveur

Mais ces logs sont **bruts, non structurés, non agrégés** et n'alimentent pas le monitoring objectif.

### Signaux critiques manquants

Pour prouver que la voix fonctionne sur appareil réel, il manque :

| # | Signal manquant | Pourquoi il est critique |
|---|---|---|
| 1 | `apk_started` | Savoir si le téléphone fondateur a ouvert l'app |
| 2 | `frontend_build_seen` | Vérifier que l'APK charge bien le dernier `index.html` déployé |
| 3 | `voice_button_clicked` | Confirmer que l'utilisateur a interagi avec le bouton |
| 4 | `microphone_permission_granted` / `denied` | Savoir si le blocage est côté permission Android |
| 5 | `voice_ws_opened` (depuis APK) | Confirmer que la WebView a ouvert le WebSocket |
| 6 | `voice_audio_chunk_sent` | Prouver que le téléphone capture et envoie du son |
| 7 | `voice_audio_chunk_received` | Prouver que le téléphone reçoit du son du serveur |
| 8 | `voice_no_audio_after_timeout` | Détecter le bug "silencieux après 20s" côté téléphone |
| 9 | `voice_session_ended_normal` / `ended_error` | Comprendre pourquoi la session s'arrête |
| 10 | `javascript_error` filtré voix | Capturer les erreurs JS liées à `startVoice()` ou `AudioWorklet` |
| 11 | `apk_version` + `device_model` | Savoir quelle version de l'APK est réellement installée |
| 12 | `cloud_url_loaded` | Vérifier que l'APK charge bien la bonne URL Cloud Run |

### Signaux déjà partiellement présents mais inutilisés

- `sendLog("nav", "LOAD OK: " + url, ...)` → pourrait servir de heartbeat implicite, mais n'est pas exploité par le monitoring
- `onConsoleMessage()` → capture déjà les erreurs JS, mais elles ne sont pas agrégées ni exposées dans `/api/admin/objectives`

---

## 3. Comparaison APK / WebView / Cloud Run / Monitoring

### Tableau comparatif des 4 couches

| Dimension | APK réelle (Android) | WebView (index.html) | Cloud Run (serveur) | Monitoring (`/api/admin/objectives`) |
|---|---|---|---|---|
| **Version observée** | `CURRENT_VERSION = "2.8"` (MainActivity.java:50) | `frontend_build` non défini | Ne sait pas quelle version APK est utilisée | Ne vérifie pas la version APK |
| **User-Agent** | `"LunaApp/2.8"` ajouté (MainActivity.java:110) | Détecte `LunaApp/` pour fallback ScriptProcessor (index.html:7588) | Reçoit l'UA mais ne l'exploite pas dans le monitoring | Ne vérifie pas la présence de l'UA |
| **Permissions** | Gère micro/caméra via Android PermissionRequest (MainActivity.java:217-252) | Affiche un message si `NotAllowedError` | Ne sait pas si la permission a été accordée ou refusée | Vérifie que `NotAllowedError` est dans le code HTML |
| **Audio capture** | Dépend de la WebView + permissions | `ScriptProcessorNode` en fallback WebView | Reçoit les chunks PCM16 base64 | Ne vérifie pas si l'audio est réellement capturé |
| **Audio playback** | Dépend de la WebView | Joue via `AudioContext` | Envoie les deltas audio | Ne vérifie pas si l'audio est joué |
| **WebSocket voix** | Ouvre via WebView JS | `voiceWs = new WebSocket(wsUrl)` | `@app.websocket("/ws/luna-voice")` | `ws_voice_ok = True` (hardcodé) |
| **Reconnexion** | Non implémentée côté natif | Auto-reconnexion x3 (index.html:7729-7740) | Gère la session côté serveur | Vérifie que `_reconnectVoiceWs` est dans le HTML |
| **Heartbeat / vie** | Aucun heartbeat structuré | Aucun | Aucune route `/api/apk/heartbeat` | Aucun check "appareil vu" |
| **Erreurs** | `sendLog()` vers `/api/logs/client` (brut) | `console.error` capturé par `onConsoleMessage` | Logs serveur | Pas d'agrégation des erreurs APK |
| **Statut déclaré** | — | — | — | `"voix": "ok"` (ETAT_ACTUEL.md) |
| **Statut réel** | Inconnu | Inconnu | Serveur prêt | **Ne reflète pas l'expérience téléphone** |

### Incohérences identifiées entre couches

1. **WebView vs APK** : `index.html` désactive `AudioWorklet` dès qu'elle voit `LunaApp/` dans l'UA (ligne 7588), mais cette décision est basée uniquement sur le User-Agent, pas sur une feature-detection réelle. Certaines WebView Android modernes supportent AudioWorklet mais l'APK est pénalisé.

2. **Cloud Run vs Monitoring** : Le monitoring déclare `/ws/luna-voice monté` avec `ws_voice_ok = True` hardcodé (ligne 3083). Si la route est supprimée par erreur, le monitoring continuera de mentir.

3. **APK vs Monitoring** : L'APK envoie des logs via `sendLog()` vers `/api/logs/client`, mais le monitoring `/api/admin/objectives` ne les consulte jamais. Les erreurs APK (SSL, WebView, permission refusée) sont invisibles du tableau de bord.

4. **WebView vs Cloud Run** : Le serveur envoie `ping` applicatif toutes les 25s (`web_voice_bridge.py:250`), et le client répond `pong` (`index.html:7644-7648`). Si le téléphone est en veille ou que la WebView est suspendue, ce ping échoue silencieusement côté serveur (timeout 20s ligne 171), mais l'APK n'est pas informée de la raison de la déconnexion.

---

## 4. Textes de statut lisibles pour Ludovic

### Propositions de textes pour le dashboard `apk_real_device`

#### Statut global

```json
{
  "apk_real_device": {
    "status": "ok",
    "last_seen_seconds": 38,
    "apk_version": "2.8",
    "frontend_build": "2026-05-25-voice-fix",
    "device_model": "Samsung SM-G991B",
    "voice_last_result": "session_ok_3min24s",
    "message": "Téléphone fondateur vu il y a 38 secondes. Dernière session voix : 3 min 24 s, audio envoyé et reçu."
  }
}
```

#### Variantes par situation

**Situation 1 — Téléphone jamais vu**
```json
{
  "status": "critical",
  "message": "Aucun téléphone fondateur n'a jamais envoyé de signal. L'APK est peut-être désinstallée, hors ligne, ou sur une ancienne version sans télémétrie.",
  "recommended_action": "Vérifier que l'APK v2.8+ est installée et ouverte au moins une fois."
}
```

**Situation 2 — Téléphone vu mais pas de session voix récente**
```json
{
  "status": "warning",
  "message": "Téléphone fondateur vu il y a 2 minutes, mais aucune session voix depuis 4 heures. L'utilisateur n'a peut-être pas testé la voix, ou le bouton ne répond pas.",
  "recommended_action": "Demander à Ludovic de tester le bouton vocal et de vérifier le retour audio."
}
```

**Situation 3 — Clic bouton mais permission micro refusée**
```json
{
  "status": "degraded",
  "message": "Ludovic a cliqué sur le bouton voix, mais le micro est refusé. Le téléphone affiche probablement un message d'erreur, mais la fonctionnalité est bloquée.",
  "recommended_action": "Aller dans Paramètres Android > Applications > Luna > Autorisations > Microphone > Autoriser."
}
```

**Situation 4 — WebSocket ouvert mais pas d'audio reçu (bug ~20s)**
```json
{
  "status": "critical",
  "message": "Session voix démarrée, WebSocket connecté, audio envoyé depuis le téléphone... mais aucun audio reçu du serveur après 20 secondes. Cela correspond au bug observé.",
  "recommended_action": "Vérifier la connexion OpenAI Realtime, le ping timeout (20s), et le fallback ScriptProcessorNode en WebView.",
  "technical_hint": "Le serveur a peut-être coupé le WS à cause du ping_timeout:20s. Le téléphone utilise ScriptProcessorNode (pas AudioWorklet) car LunaApp/ est détecté."
}
```

**Situation 5 — Frontend obsolète détecté**
```json
{
  "status": "warning",
  "message": "L'APK charge le frontend '2026-05-20-old-build' alors que le serveur sert '2026-05-25-voice-fix'. L'APK n'a pas rechargé la dernière version.",
  "recommended_action": "Forcer le rechargement : fermer complètement l'APK ( swipe up ) et la rouvrir. Le cache est vidé au démarrage (clearCache=true), mais la page peut être en mémoire."
}
```

**Situation 6 — Version APK obsolète**
```json
{
  "status": "warning",
  "message": "L'APK installée est en version 2.6, mais la version serveur attendue est 2.8. La mise à jour automatique n'a peut-être pas fonctionné.",
  "recommended_action": "Télécharger manuellement la dernière APK depuis le serveur ou vérifier que l'auto-update SHA-256 est correctement publié sur /api/app/version."
}
```

**Situation 7 — Tout fonctionne correctement**
```json
{
  "status": "ok",
  "message": "Téléphone fondateur en ligne. Dernière session voix : 2 min 15 s, audio bidirectionnel confirmé. Transcription sauvegardée. Aucune erreur WebView détectée.",
  "recommended_action": "Aucune action requise."
}
```

### Propositions de textes pour les événements bruts

| Événement | Texte lisible pour Ludovic | Niveau |
|---|---|---|
| `apk_started` | "Luna a été ouverte sur le téléphone" | info |
| `webview_page_loaded` | "La page Luna a fini de charger" | info |
| `voice_button_clicked` | "Bouton vocal appuyé" | info |
| `microphone_permission_granted` | "Microphone autorisé" | info |
| `microphone_permission_denied` | "Microphone refusé — aller dans Paramètres > Luna > Autorisations" | warning |
| `voice_ws_opened` | "Connexion vocale établie" | info |
| `voice_ws_closed` | "Connexion vocale fermée" | info |
| `voice_no_audio_after_timeout` | "Luna ne répond pas vocalement après 20 secondes — vérifier la connexion" | critical |
| `javascript_error` | "Erreur dans l'application : {message}" | error |
| `network_error` | "Problème réseau détecté" | warning |

---

## 5. Synthèse et recommandations Kimi

### Ce que le cerveau APK doit impérativement observer

1. **Heartbeat minimal** (`POST /api/apk/heartbeat`) : version APK, build frontend vu, modèle téléphone, URL chargée. C'est la preuve de vie.
2. **Événement `voice_button_clicked`** : sans ça, on ne sait pas si l'utilisateur interagit.
3. **Événement `microphone_permission_granted/denied`** : le blocage #1 en WebView Android.
4. **Événement `voice_no_audio_after_timeout`** : le seul moyen de capturer le bug "silencieux après 20s" côté téléphone.
5. **Agrégation des erreurs JS** : les `console.error` liés à `AudioWorklet`, `ScriptProcessor`, ou `WebSocket` doivent remonter structurés.

### Ce qu'il ne faut PAS faire

- Ne pas collecter l'audio brut (déjà interdit par les garde-fous Codex)
- Ne pas collecter le transcript privé (déjà interdit)
- Ne pas envoyer de heartbeat trop fréquent (batterie + data)
- Ne pas baser le statut "voix OK" uniquement sur la présence de code

### Le problème fondamental identifié

> **Le monitoring actuel confond "le serveur est prêt" avec "l'utilisateur peut utiliser la fonctionnalité".**

Sur l'appareil fondateur, la voix peut être `ok` côté serveur et `critical` côté téléphone sans que le monitoring ne le sache. Le cerveau APK est le seul moyen de fermer cette boucle.

---

*Document produit par Kimi Code CLI pour l'objectif 003 — branche `kimi/objectif-003-cerveau-apk`*
