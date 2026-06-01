# Claude — STT Whisper PTT + Voice fixes — Objectif 017

Agent : Claude  
Objectif : 017  
Date : 2026-06-01  
Commit : `2b8e309`  
Type : implémentation — 4 fixes DeepSeek Priority

---

## Ce qui a été fait

### Fix 1 — Backend `/api/visio/transcribe` (Whisper STT)

**Fichier** : `luna_web.py` — nouveau endpoint après `visio_tts`

```
POST /api/visio/transcribe
Content-Type: multipart/form-data
Body: audio (blob .webm)
```

- Accepte un blob audio `.webm` via `multipart/form-data`
- Transcription via `openai_client.audio.transcriptions.create(model="whisper-1", language="fr")`
- Retourne `{ ok: true, text: "...", method: "whisper" }`
- Garde le fichier temp dans `/tmp/*.webm` et le supprime après
- Sécurité : token JWT requis via middleware (Authorization header)

### Fix 2 — Frontend PTT (Push-To-Talk) dans `simli.html`

**Comportement** :
- Si `window.SpeechRecognition` est undefined (cas Android WebView) → `_pttMode = true`
- Le bouton `🎤 Parler` apparaît (était caché par défaut avec `display:none`)
- Tap 1 → `MediaRecorder.start()` + bouton vire rouge avec animation pulse
- Tap 2 → `MediaRecorder.stop()` → blob → `POST /api/visio/transcribe` → `_irisReply(text)`

**Variables** :
```javascript
var _pttMode = false;
var _pttRecording = false;
var _pttMediaRecorder = null;
var _pttChunks = [];
```

**Logs à surveiller** :
- `ptt_mode = activé — Web Speech API absent` → confirmation mode PTT
- `ptt_start` → enregistrement commencé
- `ptt_transcribed = <texte>` → Whisper a reconnu ce que Ludovic a dit
- `ptt_transcribe_empty` → audio trop court ou silence

### Fix 3 — ElevenLabs voice_settings

**Fichier** : `luna_web.py` — endpoint `visio_tts`

```python
"voice_settings": {
    "stability": 0.45,
    "similarity_boost": 0.75,
    "style": 0.3,
    "use_speaker_boost": True
}
```

Avant : voix Camille générique, aucun réglage.  
Après : voix plus naturelle, moins robotique, ton plus soutenu.

### Fix 4 — Prompt Iris amélioré

**Fichier** : `luna_web.py` — endpoint `visio_chat`

```
Avant : "Réponses courtes, naturelles, professionnelles. Jamais de longueur inutile."
Après : "Sois directe, professionnelle, et ne répète jamais les formules d'introduction.
         Si tu n'as pas compris, dis simplement : 'Pouvez-vous répéter ?' — jamais 'je ne comprends pas'."
```

---

## Ce que Codex doit tester

### Test terrain prioritaire

1. Ouvrir l'APK Luna → visio
2. Observer si le bouton `🎤 Parler` apparaît (remplace la détection SR)
3. Logger dans WebView console :
   - `ptt_mode = activé` → STT mort confirmé, PTT actif
   - `ptt_start` → enregistrement démarre
   - `ptt_transcribed` → Whisper comprend bien
4. Parler clairement 3-4 secondes → re-tapper → attendre la réponse Iris

### Matrice de résultat attendu

| Log | Signification |
|---|---|
| `ptt_mode = activé` | Web Speech API absent confirmé, PTT prend le relais |
| `ptt_transcribed = <texte>` | Whisper fonctionne, pipeline STT vivant |
| `llm_done = Xms` | LLM a répondu |
| `tts_done = Xms` | ElevenLabs a généré la voix |
| `audio_play_start` | Ludovic entend Iris |
| `total_latency_ms < 5000` | Pipeline complet OK |

### En cas de problème

| Symptôme | Cause probable |
|---|---|
| Bouton PTT n'apparaît pas | Web Speech API présent → pipeline SR actif (OK) |
| `ptt_transcribe_err` | Réseau ou JWT expiré |
| `tts_error = 422` | ElevenLabs voice_id manquante dans Cloud Run env vars |
| Audio ne joue pas | autoplay bloqué → Ludovic doit avoir interagi avant |

---

## À déployer

Ce commit doit être déployé sur Cloud Run par Ludovic pour test terrain.

**Commande** (Ludovic valide) :
```bash
gcloud run deploy luna-beta \
  --source . \
  --region europe-west1 \
  --project crypto-parser-475411-k4
```

---

## Ce qui reste à faire

- Déploiement Cloud Run (attente feu vert Ludovic)
- Test terrain Codex avec WebView DevTools connecté au BON target (Luna simli.html, pas Google Ads)
- Si PTT fonctionne : DeepSeek contre-audit des logs
- Fix optionnel : anti-écho firstMessage Simli (setTimeout avant `_startSpeechCapture`)
