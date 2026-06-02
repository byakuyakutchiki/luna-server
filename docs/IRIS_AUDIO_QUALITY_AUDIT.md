# Iris Audio — Audit Qualité Conversationnelle

**Date** : 2026-06-02  
**Auteur** : Claude  
**Commit** : en cours  
**Statut** : audit + corrections P0/P1 appliquées

---

## 1. Bugs bloquants corrigés (P0)

### Bug 1 — Bouton raccrocher inopérant

**Cause identifiée** : `doHangup()` dépendait d'une `Promise.race` avec un timeout de 1200ms.
Si la Promise échouait silencieusement, la navigation était retardée ou bloquée.
De plus, `_irisAudio` continuait de jouer pendant le raccrocher.

**Corrections appliquées** :
- Ajout d'un hard fallback `setTimeout(navigate, 2500)` au démarrage de `doHangup()`
- Arrêt immédiat de `_irisAudio` + `_irisReplying = false` avant toute autre logique
- Bouton plus grand : `min-height: 52px; min-width: 160px; padding: 15px 44px`
- `touch-action: manipulation` pour éviter le délai 300ms sur mobile
- `bottom: 24px` (était 16px) pour sortir de la zone de navigation Android

---

## 2. Latence conversationnelle (P1)

### Mesures théoriques par étape (pipeline séquentiel)

| Étape | Durée mesurée / estimée | Log |
|---|---|---|
| Silence wait (VAD) | **700ms** (était 1400ms — -700ms) | `VAD_SILENCE_MS` |
| STT Whisper (API) | ~350–600ms | `vad_whisper_ms` |
| LLM GPT-4o-mini | ~350–600ms | `llm_done` |
| TTS OpenAI tts-1 | ~300–500ms | `tts_done` |
| Buffer + play | ~50ms | `audio_play_start` |
| **TOTAL estimé** | **~1750–2400ms** | `turn_total_from_silence_ms` |

### Métriques loggées (F12 → Console)

```
[INFO][simli] speech_end_ms          : durée de la phrase utilisateur (ms)
[INFO][simli] vad_whisper_ms         : STT Whisper (ms)
[INFO][simli] llm_done               : LLM response (ms depuis _irisReply start)
[INFO][simli] tts_done               : TTS generation (ms depuis llm_done)
[INFO][simli] time_to_first_audio_ms : LLM + TTS total (ms depuis _irisReply start)
[INFO][simli] turn_total_from_silence_ms : total depuis fin de parole utilisateur
[INFO][simli] total_latency_ms       : total depuis _irisReply start jusqu'à fin audio
```

### Correction appliquée

- `VAD_SILENCE_MS` : **1400 → 700ms** (gain : ~700ms par tour)
- `getUserMedia` audio : ajout `echoCancellation: true, noiseSuppression: true, autoGainControl: true`

---

## 3. Goulot d'étranglement principal identifié

**Le pipeline STT → LLM → TTS est fondamentalement séquentiel.**

```
Fin de parole
    ↓ 700ms (silence wait)
    ↓ ~500ms (Whisper)
    ↓ ~500ms (GPT-4o-mini)
    ↓ ~400ms (OpenAI TTS tts-1)
    ↓ audio commence
```

**Total irréductible avec cette architecture : ~1600–2100ms**

Pour atteindre l'expérience ChatGPT Voice (<1 seconde perçue), il faut une architecture différente.

---

## 4. Chemin vers ChatGPT Voice quality

### Option A — OpenAI Realtime API (recommandée pour le futur)

```
WebSocket Realtime
    Audio input (streaming) → STT simultané → LLM en stream → TTS chunk par chunk
    Latence totale : ~300–600ms
```

**Avantage** : architecture pipeline → une seule connexion WebSocket, barge-in natif, latence < 1s  
**Complexité** : refonte complète du pipeline front + backend  
**Coût** : ~0.06$/min audio input + output

### Option B — Streaming TTS (gain ~200–300ms)

LLM stream → dès 30 tokens reçus → démarrer TTS sur ce premier chunk → jouer pendant que la suite génère.

**Gain** : supprime le délai d'attente de la réponse LLM complète avant TTS  
**Complexité** : moyenne — chunked streaming backend, MediaSource API front  

### Option C — Pré-chauffage (gain mineur, ~50ms)

Garder un `OpenAI()` client initialisé entre les requêtes (évite la création d'un nouveau client à chaque appel).

**Gain** : ~50ms par requête  
**Complexité** : faible

---

## 5. Audit pipeline — zéro doublon confirmé

| Élément | Statut |
|---|---|
| VAD | ✅ Un seul (ScriptProcessor + silence timer) |
| STT | ✅ Un seul (Whisper via `/api/visio/transcribe`) |
| LLM | ✅ Un seul (GPT-4o-mini via `/api/visio/chat`) |
| TTS | ✅ Un seul (OpenAI tts-1 via `/api/visio/tts`) |
| WebRTC Daily | ✅ Désactivé (bypass dans `_launchVisioFlow`) |
| Simli / Tavus | ✅ Désactivés (aucun appel `/api/call` ou `/api/simli/start`) |
| ElevenLabs | ✅ Retiré du pipeline Iris (conservé pour épisodes) |
| speechSynthesis | ✅ Absent du code actif |
| Double getUserMedia | ✅ Résolu (Daily désactivé → un seul `getUserMedia`) |

---

## 6. État actuel (post-corrections P0/P1)

```
PIPELINE IRIS AUDIO — ACTIF
════════════════════════════════════════════════════════════
getUserMedia({ echoCancellation, noiseSuppression, autoGainControl })
    ↓
AudioContext ScriptProcessor(2048)
    ↓ RMS > 0.018 → start MediaRecorder
    ↓ RMS < 0.018 pendant 700ms → stop MediaRecorder
    ↓
POST /api/visio/transcribe → Whisper-1 (fr)
    ↓
POST /api/visio/chat → GPT-4o-mini (max_tokens=45, temp=0.45)
    ↓
POST /api/visio/tts → OpenAI tts-1, voice=nova
    ↓
new Audio(blob).play() → navigateur
    ↓
Métriques loggées : turn_total_from_silence_ms
```

---

## 7. Recommandation architecture pour la prochaine phase

**Décision suggérée à Ludovic :**

Choisir entre deux trajectoires :

| Trajectoire | Latence | Complexité | Coût |
|---|---|---|---|
| **A — OpenAI Realtime** | ~400ms | Élevée (refonte) | ~0.06$/min |
| **B — Streaming TTS** | ~1200ms | Moyenne | Identique |
| **C — Garder actuel** | ~1800ms | Aucune | Identique |

**Recommandation Claude** : Phase 1 → Option B (streaming TTS, gain visible sans refonte totale).  
Phase 2 → Option A (Realtime API) quand le produit est stabilisé et le budget audio validé.

---

*Corrections P0/P1 appliquées dans ce même commit. Aucune nouvelle fonctionnalité ajoutée.*
