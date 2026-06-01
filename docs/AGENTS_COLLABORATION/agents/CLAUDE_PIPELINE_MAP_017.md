# Claude — Cartographie pipeline visio — Objectif 017

Agent : Claude  
Objectif : 017  
Date : 2026-06-01  
Type : analyse — aucun patch tant que Codex n'a pas la preuve terrain  

---

## Règle appliquée

Je ne code pas. Je mappe. Codex capture. Ensuite on décide.

---

## Les 6 maillons et leur état probable

### Maillon 1 — STT (Web Speech API)

**Code** : `simli.html:2261`
```javascript
var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SR) { rLog('info', 'simli', 'speech_reco', 'non disponible'); return; }
```

**Risque ÉLEVÉ** : `window.SpeechRecognition` est `undefined` dans Android WebView.  
La Web Speech API fonctionne dans Chrome navigateur, pas dans les WebView apps.  
Si `SR` est undefined → la fonction `return` immédiatement → **pipeline mort dès le départ**.

**Log à chercher dans la console WebView** :
- `speech_reco = non disponible` → STT mort, cause racine probable
- `speech_reco = démarré fr-FR` → STT vivant, maillon suivant à auditer

---

### Maillon 2 — Boucle écho sur firstMessage Simli

**Risque ÉLEVÉ** : le `firstMessage` Simli ("Bonjour Ludovic…") passe par Daily WebRTC audio, **pas** par `_irisAudio`. Donc `_irisReplying` est `false` quand il joue. Si Web Speech API est déjà actif, il capture la voix de Simli comme si c'était Ludovic → envoie au LLM → LLM reçoit une phrase bizarre → "je ne comprends pas".

**Log à chercher** :
- `speech_start` suivi d'un texte ressemblant à la salutation Simli → boucle écho confirmée

**Point de code** : `simli.html:1279` — `_startSpeechCapture()` lancé sur `joined-meeting`, avant même que le bot joue le firstMessage.

---

### Maillon 3 — Auth JWT (`authFetch`)

**Code** : `simli.html:2198` — `authFetch('/api/visio/chat', ...)`

**Risque MOYEN** : si le token JWT est expiré ou absent dans l'APK → 401 → `llm_fetch_err` loggué mais silencieux côté utilisateur.

**Log à chercher** :
- `llm_fetch_err` → chercher si la cause est 401 (token) ou réseau
- `llm_done` → auth OK

---

### Maillon 4 — Endpoint LLM `/api/visio/chat`

**Code** : `luna_web.py:7503`

**État** : prompt correct (Iris, français, 1-2 phrases, max 150 tokens). Single-turn sans mémoire de conversation.

**Risque FAIBLE** : l'endpoint est simple et testé. Mais si le STT capture la voix de Simli (maillon 2), le LLM reçoit une phrase incohérente et répond "je ne comprends pas" — ce qui correspond exactement au retour terrain Codex.

**Log à chercher** :
- `llm_done = Xms` → endpoint OK, regarder le texte reçu par le LLM
- `llm_empty` → réponse LLM vide (rare)

---

### Maillon 5 — TTS `/api/visio/tts`

**Code** : `luna_web.py:7546` + `simli.html:2216`

**Risque MOYEN** : Cloud Run lit `ELEVENLABS_VOICE_ID` depuis les variables d'environnement. Si la variable est absente → fallback sur une voice_id vide → ElevenLabs 422.

**À vérifier** : est-ce que `ELEVENLABS_VOICE_ID=Z9ZHGvFZ90R0h0x1prsJ` est bien dans les Cloud Run env vars de la révision 00470 ?

**Log à chercher** :
- `tts_done = Xms` → OK
- `tts_error = 422` ou `tts_error = 401` → voice_id ou clé manquante

---

### Maillon 6 — Playback audio dans WebView

**Code** : `simli.html:2244` — `_irisAudio.play()`

**Risque MOYEN** : Android WebView peut bloquer `audio.play()` sans geste utilisateur précédent. Le pretest demande bien les permissions micro, mais pas forcément audio playback.

**Log à chercher** :
- `audio_play_blocked` → autoplay bloqué WebView
- `audio_play_start` → playback OK

---

## Matrice de diagnostic rapide

| Log observé | Maillon cassé | Cause probable |
|---|---|---|
| `speech_reco = non disponible` | 1 — STT | Web Speech API absent du WebView |
| `speech_start` = texte de Simli | 2 — Écho | STT capture la voix Simli avant Ludovic |
| `llm_fetch_err` | 3 — Auth | Token JWT expiré ou 401 |
| `llm_done` + `tts_error = 4xx` | 5 — TTS | Clé ou voice_id manquante |
| `audio_play_blocked` | 6 — Playback | Autoplay WebView bloqué |
| `total_latency_ms > 6000` | 4 ou 5 | LLM lent ou TTS lent |
| Aucun log `speech_*` | 1 — STT | Pipeline mort dès la détection SR |

---

## Ce que Codex doit capturer

Pour identifier le maillon cassé, il faut **un seul test de 20 secondes** avec la console WebView ouverte :

```
adb forward tcp:9222 localabstract:webview_devtools_remote_<pid>
```

Chercher dans les logs console :
1. `speech_reco` → valide ou non disponible ?
2. `speech_start` → le texte est-il celui de Ludovic ou de Simli ?
3. `llm_done` ou `llm_fetch_err` ?
4. `total_latency_ms` ou `audio_play_blocked` ?

**Un seul de ces 4 logs suffit à identifier la cause racine.**

---

## Ce que je ne code pas avant preuve

- Pas de remplacement Web Speech API → backend STT (Whisper)
- Pas de délai `setTimeout` avant `_startSpeechCapture()`
- Pas de filtre sur le firstMessage Simli
- Pas de modification du prompt LLM
- Pas de patch ElevenLabs

Tout correctif attendra la matrice `preuve → cause → patch` de Codex.
