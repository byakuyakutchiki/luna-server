# Claude — Diagnostic P0 Audio Silencieux — Objectif 014

Agent : Claude  
Date : 2026-05-30  
Statut : diagnostic terrain — aucun déploiement  
Référence : `CODEX_INCIDENT_P0_VISIO_AUDIO_SILENT_014.md`

---

## 1. Env vars Cloud Run — état réel (noms seulement, aucune valeur)

Révision analysée : `luna-beta-00462-q7n`  
Source : `gcloud run services describe luna-beta --region=europe-west1`

| Variable | Présence Cloud Run | Remarque |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Présente avec valeur | Utilisée par `customLLMConfig.llmAPIKey` |
| `SIMLI_API_KEY` | ✅ Présente avec valeur | Clé Simli opérationnelle |
| `SIMLI_FACE_ID` | ✅ Présente avec valeur | Face ID `b9e5f...` |
| `ELEVENLABS_API_KEY` | ✅ Présente avec valeur | Ajoutée dans ce déploiement |
| `ELEVENLABS_VOICE_ID` | ✅ Présente avec valeur | `6BlZrFdruL4hpXFHmHUC` (Alice) |
| `CARTESIA_API_KEY` | ⚠️ Présente **sans valeur** | Variable définie mais vide (`""`) |
| `CARTESIA_VOICE_ID` | ❌ Absente | Non configurée |
| `ADMIN_NUMBER` | ✅ Présente avec valeur | Requis au démarrage |

**Résultat** : CARTESIA_API_KEY vide → `os.getenv("CARTESIA_API_KEY", "")` retourne `""` (falsy) → le code prend la branche ElevenLabs. Aucune confusion Cartesia. ✅

---

## 2. Payload Simli envoyé — reconstruit depuis le code (sans secrets)

Fichier : `luna_web.py` lignes `6807–6907`, fonction `_start_simli_visio()`  
Endpoint : `POST https://api.simli.ai/auto/start/configurable`

```json
{
  "simliAPIKey": "***SIMLI_API_KEY***",
  "faceId": "b9e5f***",
  "systemPrompt": "[french_prefix ~300 chars] + [contexte profil/météo/actualités ~variable]",
  "firstMessage": "Bonjour Ludovic ! C'est Iris, votre secrétaire. Je vous vois et je vous entends. Comment puis-je vous aider ?",
  "customLLMConfig": {
    "model": "gpt-4o-mini",
    "baseURL": "https://api.openai.com/v1",
    "llmAPIKey": "***OPENAI_API_KEY***"
  },
  "maxSessionLength": 3600,
  "maxIdleTime": 60,
  "ttsProvider": "ElevenLabs",
  "voiceId": "6BlZrFdruL4hpXFHmHUC",
  "ttsAPIKey": "***ELEVENLABS_API_KEY***",
  "elevenlabsLanguageCode": "fr"
}
```

**Chemin de code exact** (`luna_web.py:6869–6878`) :
```python
if cartesia_key:           # "" → False → pas Cartesia
    ...
elif elevenlabs_key:       # "sk_db8..." → True → ElevenLabs
    payload["ttsProvider"] = "ElevenLabs"
    payload["voiceId"] = os.getenv("ELEVENLABS_VOICE_ID", "Z9ZHGvFZ90R0h0x1prsJ")
    payload["ttsAPIKey"] = elevenlabs_key
    payload["elevenlabsLanguageCode"] = "fr"
```

---

## 3. Réponse Simli — statut et champs utiles

**Logs disponibles** : insuffisants. Le logger imprime l'erreur si `resp.status_code != 200`  
(`logger.error(f"Simli auto/start error {resp.status_code}: {data}")`)  
mais ne loggue rien si c'est un succès 200. Aucun log de réponse positive en prod.

**Parsing de la réponse** (`luna_web.py:6895–6903`) :
```python
conv_url = data.get("roomUrl") or data.get("room_url") or ""
session_id = data.get("sessionId") or data.get("session_id") or ""
```

**Ce qu'on peut déduire** : Puisque Ludovic voit l'interface visio (avatar présent, pas d'erreur d'écran), la réponse Simli a renvoyé un `roomUrl` → session créée avec succès. Le problème est **après** la création de session : audio absent dans la room.

---

## 4. Logs Daily/WebRTC disponibles

**Côté serveur** : aucun log Daily — tout est côté navigateur dans `rLog()`.

**Côté frontend** (`simli.html`) — events attendus en console navigateur :
- `[INFO][simli] daily_createFrame` → iframe Daily créée
- `[INFO][simli] daily_joined` → utilisateur rejoint la room
- `[INFO][simli] bot_detected` ou `bot_joined` → bot Simli présent
- `[ERROR][simli] daily_error` → erreur Daily (absente si pas d'erreur)

**Demandé à Ludovic (section 9)** : ouvrir la console navigateur pendant le test pour voir ces events.

---

## 5. Bot : rejoint-il et publie-t-il une piste audio ?

**Non confirmé.** Les deux scénarios sont possibles :

**Scénario A** (plus probable) : Le bot rejoint la room, mais Simli ne peut pas appeler ElevenLabs avec le voice ID fourni → TTS silencieux. Simli ne publie pas de piste audio, ou publie une piste audio vide.

**Scénario B** (moins probable) : Le bot ne rejoint pas du tout. Pas d'event `bot_joined`. La room est vide côté bot → silence total.

**Preuve attendue** : console navigateur → event `bot_joined` présent ou absent.

---

## 6. Frontend — peut-il jouer l'audio entrant ?

**État du frontend analysé** :

| Vérification | Résultat |
|---|---|
| Bouton mute Luna (`btnMuteLuna`) | Par défaut : "🎙 Luna active" — **non muté** ✅ |
| Mute = soft-mute par message | `updateParticipant` non utilisé — ne coupe pas l'audio Daily réel ✅ |
| iframe autoplay | `allow="camera; microphone; autoplay; ..."` forcé à 300ms via setTimeout ✅ |
| iframe créée avec Daily.js | `DailyIframe.createFrame(tavusFrameEl, {...})` sans options de mute ✅ |
| Permissions navigateur | Le frontend demande `getUserMedia({audio:true})` — si refusé, alerte affichée |

**Conclusion frontend** : le frontend ne bloque pas l'audio. Si le bot publie une piste audio, elle devrait être entendue.

---

## 7. Hypothèses racine classées par probabilité

### H1 — 65% — Voice ID Alice inaccessible avec cette clé ElevenLabs

**Explication** : `6BlZrFdruL4hpXFHmHUC` (Alice) est une voix du **Voice Library public ElevenLabs**, pas une voix personnelle. Pour l'utiliser via API, il faut :
1. L'avoir ajoutée à "My Voices" dans le compte ElevenLabs associé à la clé
2. Avoir un plan ElevenLabs autorisant les voix partagées en API

Si ElevenLabs retourne 422 "Voice not found" ou 403 à Simli, Simli échoue silencieusement au lieu de revenir sur sa voix par défaut — car on a explicitement spécifié `ttsProvider = "ElevenLabs"`.

**Signe indirect** : La régression est exacte. Avant ce déploiement : voix masculine (TTS Simli par défaut). Après : silence complet. L'ajout d'une config ElevenLabs invalide bloque le fallback Simli.

### H2 — 15% — Champ `elevenlabsLanguageCode` non reconnu par Simli

**Explication** : Si Simli ne connaît pas `elevenlabsLanguageCode`, il peut rejeter silencieusement tout le bloc TTS et revenir à son défaut. Mais son défaut aurait produit une voix masculine (comme avant), pas du silence. Donc H2 seul ne suffit pas, il faudrait un fallback absent.

### H3 — 12% — Endpoint `/auto/start/configurable` déprécié ou en demi-mesure

**Explication** : La doc Simli marque certains endpoints `auto/*` comme deprecated. Si l'endpoint accepte la room mais n'applique plus tous les paramètres TTS, la session s'ouvre mais Iris ne parle pas.

### H4 — 5% — Bot absent de la room (problème Simli infra)

**Explication** : Le bot Simli ne rejoint pas la room Daily. Rare, mais possible si la session a été créée mais le bot n'a pas pu se connecter à Daily (problème réseau transitoire Simli).

### H5 — 3% — Android WebView bloque l'audio entrant

**Explication** : Le setTimeout de 300ms pour forcer `allow="autoplay"` sur l'iframe peut être une race condition sur certains Android. Possible si Ludovic teste depuis l'APK WebView et non un navigateur.

---

## 8. Patch minimal proposé — non déployé (niveau 2)

### Patch A — Logs Simli (niveau 1 — non destructif)

Ajouter dans `luna_web.py:_start_simli_visio()`, après le `try`:

```python
# Après la réponse Simli, logger le statut et les champs utiles (sans secrets)
logger.info(f"Simli auto/start status={resp.status_code} keys={list(data.keys()) if isinstance(data, dict) else 'non-dict'} roomUrl={'yes' if conv_url else 'no'}")
if resp.status_code != 200:
    logger.error(f"Simli auto/start error {resp.status_code}: {data}")
```

Ce patch ne change aucun comportement. Il permet de voir en Cloud Run si Simli accepte le payload.

### Patch B — Endpoint debug admin (niveau 1 — non destructif)

Ajouter une route `GET /api/debug/visio` (protégée par token admin) retournant :

```json
{
  "provider_tts": "ElevenLabs",
  "elevenlabs_key_present": true,
  "elevenlabs_voice_id_truncated": "6BlZ...mHUC",
  "cartesia_key_present": false,
  "openai_key_present": true,
  "simli_configured": true
}
```

Aucune valeur secrète, aucune action. Permet de vérifier l'état en prod sans accéder au Cloud Run.

### Patch C — Test voix ElevenLabs hors visio (niveau 1.5 — consommation minime)

Si Ludovic valide, appeler ElevenLabs directement avec la clé et la voix Alice :

```bash
curl -X POST "https://api.elevenlabs.io/v1/text-to-speech/6BlZrFdruL4hpXFHmHUC" \
  -H "xi-api-key: ***ELEVENLABS_API_KEY***" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test Iris.", "model_id": "eleven_multilingual_v2"}' \
  -o /tmp/test_iris.mp3
```

Si réponse 200 + fichier audio → ElevenLabs fonctionne avec cette voix → le problème est Simli.  
Si réponse 422 "voice_not_found" ou 403 → H1 confirmé → changer de voix.

**Coût estimé** : ~5 caractères × 0.0003$ = ~0.00015$ (négligeable).  
**Validation Ludovic requise avant d'exécuter.**

### Patch D — Changement de voix ElevenLabs (niveau 2 — déploiement)

Si H1 confirmé, remplacer `ELEVENLABS_VOICE_ID` par une voix ElevenLabs certifiée accessible :
- `pFZP5JQG7iQjIQuC4Bku` — Lily (EN, mais démontré fonctionnel en test)
- Ou trouver une voix FR dans le compte ElevenLabs lié à la clé

**Ne pas déployer sans validation Ludovic.**

---

## 9. Test court terrain — demandé à Ludovic (< 30s)

**Test 1 — Console navigateur (0 credit)**
Avant de lancer la visio :
1. Ouvrir les outils développeur du navigateur (F12 ou Réglages → Outils dev)
2. Aller dans l'onglet "Console"
3. Lancer la visio normalement
4. Observer les lignes `[INFO][simli]`
5. Chercher : `bot_joined` présent ? `daily_error` présent ?
6. Copier et envoyer les lignes console à l'équipe (aucun secret dedans)

**Test 2 — ElevenLabs hors visio (si Ludovic valide Patch C)**
Exécuter la commande curl ci-dessus sur le serveur local.  
Résultat attendu : fichier MP3 lisible ou code erreur explicite.

**Critère de succès** : Ludovic entend "Test Iris." en audio depuis `/tmp/test_iris.mp3`.

---

## 10. Synthèse

| Étage | État | Preuve |
|---|---|---|
| 1. Session Simli | ✅ Probable OK (roomUrl retourné) | Interface visio s'ouvre chez Ludovic |
| 2. Réponse API Simli | ⚠️ Non loggué | Aucun log de succès en prod |
| 3. LLM (OpenAI) | ✅ Configuré | OPENAI_API_KEY présent + customLLMConfig correct |
| 4. TTS ElevenLabs | ❌ **Suspect principal** | Voice ID Alice possiblement inaccessible |
| 5. Daily/WebRTC bot | ❓ Non confirmé | Vérifier event `bot_joined` en console |
| 6. Browser autoplay | ✅ Protégé | iframe allow + setTimeout 300ms |
| 7. Frontend mute | ✅ Non muté | btnMuteLuna = "Luna active" par défaut |
| 8. Terrain | ❌ Silence | Rapport Ludovic après déploiement |

**Action immédiate recommandée sans déploiement** :  
Ludovic ouvre la console navigateur pendant un test visio court (<30s) et envoie les logs `[simli]` à l'équipe. Ces logs permettent de confirmer ou infirmer H1 en 5 minutes.

**Action suivante si H1 confirmé (voice ID invalide)** :  
Exécuter le test curl ElevenLabs sur le serveur local (Patch C), identifier une voix FR accessible, mettre à jour `ELEVENLABS_VOICE_ID` dans Cloud Run. Niveau 2 — validation Ludovic.
