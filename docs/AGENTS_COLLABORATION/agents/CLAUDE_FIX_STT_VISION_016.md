# Claude — Fix STT + Vision — Objectif 016

Agent : Claude  
Date : 2026-06-01  
Statut : code livré, déploiement en attente validation Ludovic  

---

## Bugs diagnostiqués

### Bug 1 — STT mort (Iris n'entend pas Ludovic)

**Cause** : `startAudioOff: false` dans `dailyCall.join()` → Daily.js capture le micro en exclusivité via WebRTC → Web Speech API reçoit un flux dégradé ou bloqué.

**Fix** : `startAudioOff: true` → Daily ne prend pas le micro. Web Speech API a l'accès exclusif.

Cohérence architecture : on ne transmet PAS l'audio de Ludovic à Simli via Daily (Option B-lite gère le STT nous-mêmes). Daily sert uniquement à recevoir l'audio du bot Simli (firstMessage).

### Bug 2 — Vision no_track (caméra `vision_no_track` à chaque tick)

**Cause** : `_getLocalVideoTrack()` lisait `dailyCall.participants().local.tracks.video`. En mode iframe Daily.js, le frame parent n't a pas accès aux tracks de l'iframe → retourne toujours `null`.

**Fix** :
1. Dans `_startCamTest` : conserver le stream caméra dans `_visionCameraStream` au lieu de le stopper
2. `_getLocalVideoTrack` lit d'abord `_visionCameraStream` (parent frame context)
3. `startVideoOff: true` dans `dailyCall.join()` → Daily ne concurrence pas notre stream
4. Libération propre du stream au hangup

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `static/simli.html` | `startAudioOff: true` + `startVideoOff: true` dans `dailyCall.join()` |
| `static/simli.html` | `_visionCameraStream` : stream caméra conservé depuis pretest |
| `static/simli.html` | `_getLocalVideoTrack()` refactorisé : lit `_visionCameraStream` en priorité |
| `static/simli.html` | Hangup : libère `_visionCameraStream` proprement |

---

## Logs attendus après fix

```
[INFO][simli] speech_reco = démarré fr-FR         ← STT actif
[INFO][simli] speech_start = "tu m'entends ?"     ← Ludovic capté
[INFO][simli] llm_done = 823ms
[INFO][simli] tts_done = 612ms
[INFO][simli] total_latency_ms = 1847ms            ← réponse vocale

[INFO][simli] vision_start = loop démarré
[INFO][simli] track_started local:video            ← ou vision_tick sans no_track
```

Au lieu des logs bugués :
```
[WARN][simli] speech_err = not-allowed             ← (ou pas de speech_start du tout)
[INFO][simli] vision_no_track = caméra non disponible  ← à chaque tick
```

---

## Test terrain demandé à Codex/Ludovic

1. Ouvrir la visio
2. Passer le pretest (clic Autoriser micro + caméra)
3. Attendre la salutation
4. Dire **"tu m'entends ?"**
5. F12 → Console → vérifier :
   - `speech_start` apparaît ✅
   - `total_latency_ms` apparaît (< 4000ms) ✅
   - `vision_no_track` disparaît ✅

---

## Ce que Kimi doit vérifier

- La salutation initiale (firstMessage Simli) s'entend toujours après `startAudioOff: true`
- Le délai de réponse est < 3s sur un réseau 4G standard

## Ce que DeepSeek doit auditer

- La libération `_visionCameraStream` au hangup est-elle thread-safe ?
- Le fallback `try { dailyCall.participants()... }` est-il utile ou dead code ?
- Y a-t-il un cas où `_visionCameraStream` est null mais une track Daily est dispo ?
