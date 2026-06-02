# Architecture Audio Audit — Visio Iris

**Date** : 2026-06-02  
**Auteur** : Claude  
**Statut** : audit uniquement — aucune modification  
**Fichiers lus** : `static/simli.html`, `luna_web.py`, `.env`

---

## 1. Cartographie des points d'entrée audio

### Entrées microphone (getUserMedia)

| # | Ligne | Contexte | Audio | Vidéo |
|---|---|---|---|---|
| 1 | `simli.html:945` | Pré-test micro (écran démarrage) | `true` | `false` |
| 2 | `simli.html:1024` | Pré-test caméra (écran démarrage) | `false` | `true` |
| 3 | `simli.html:2653` | `_startVAD()` — réutilise track Daily si disponible | — | — |
| 4 | `simli.html:2658` | `_startVAD()` — fallback `getUserMedia` si Daily ne donne pas sa piste | `true` | `false` |

Daily.js (`dailyCall.join()`, ligne 1588) ouvre lui-même une prise micro via WebRTC. Paramètre : **`startAudioOff: true`** — Daily joint la session avec le micro LOCAL **muet côté WebRTC**. Cela signifie que le provider (Simli/Tavus) ne reçoit **pas** la voix de Ludovic via le canal WebRTC.

---

### AudioContext

| # | Variable | Ligne | Créé quand |
|---|---|---|---|
| 1 | `_pretestAudioCtx` | `simli.html:977` | Pendant le pré-test micro sur l'écran démarrage |
| 2 | `_vadAudioCtx` | `simli.html:2575` | Quand `_startVAD()` est appelé (après `joined-meeting`) |
| 3 | Interne Daily.js | interne SDK | Daily.js crée son propre AudioContext pour WebRTC (non accessible) |

**Total : 2 AudioContext créés par notre code + 1 interne Daily.js = 3 simultanés potentiels.**

---

### MediaStream

| # | Variable | Ligne | Source |
|---|---|---|---|
| 1 | (local) pré-test | `simli.html:945` | getUserMedia audio |
| 2 | (local) pré-test cam | `simli.html:1024` | getUserMedia video |
| 3 | `_vadStream` | `simli.html:2658` ou `2653` | getUserMedia audio OU MediaStream([dailyTrack]) |
| 4 | `_visionCameraStream` | usage vision | Track vidéo Daily pour la vision caméra |
| 5 | WebRTC Daily | interne SDK | Géré par Daily.js (audio + vidéo WebRTC) |

---

### Sorties audio

| # | Type | Ligne | Propriétaire |
|---|---|---|---|
| 1 | `<audio id="ambientAudio">` | `simli.html:659` | Musique d'ambiance cinématique |
| 2 | `<audio id="phoneSfx">` | `simli.html:660` | Sons téléphone (vibration, sonnerie) |
| 3 | `new Audio(url)` — `_irisAudio` | `simli.html:2393` | **TTS ElevenLabs B-lite** — voix d'Iris |
| 4 | WebRTC Daily iframe | interne provider | **TTS du provider** (Simli ou Tavus) via WebRTC speakers |

**Total : 4 sorties audio, dont 2 peuvent jouer la voix d'Iris simultanément.**

---

### STT (Speech-To-Text)

| # | Endpoint | Ligne | Qui l'appelle |
|---|---|---|---|
| 1 | `POST /api/visio/transcribe` (Whisper) | `simli.html:2479` | Notre VAD B-lite |
| 2 | STT interne Simli | côté serveur Simli | **Potentiellement actif** si Simli reçoit de l'audio (mais `startAudioOff: true`) |
| 3 | STT interne Tavus | côté serveur Tavus | Actif uniquement si plan Premium/Fondateur et Tavus configuré |

---

### LLM

| # | Endpoint | Ligne | Qui l'appelle |
|---|---|---|---|
| 1 | `POST /api/visio/chat` (GPT-4o-mini) | `simli.html:2335` | Notre pipeline B-lite |
| 2 | LLM interne Simli | `luna_web.py:6871` | GPT-4o-mini configuré dans le payload Simli (`customLLMConfig`) |
| 3 | LLM interne Tavus | Tavus API | Tavus handle STT+LLM entièrement |

---

### TTS (Text-To-Speech)

| # | Endpoint | Ligne | Qui l'appelle | Sortie |
|---|---|---|---|---|
| 1 | `POST /api/visio/tts` (ElevenLabs) | `simli.html:2372` | Notre pipeline B-lite | `new Audio()` browser tag |
| 2 | ElevenLabs via Simli | `luna_web.py:6883` | Simli API (côté serveur Simli) | WebRTC Daily iframe |
| 3 | TTS interne Tavus | Tavus API | Tavus | WebRTC Daily iframe |

---

## 2. Schéma du flux réel

```
PIPELINE 1 — PROVIDER (Simli ou Tavus)
══════════════════════════════════════════════════════════════════
Micro Ludovic → WebRTC Daily → [BLOQUÉ : startAudioOff=true]
                                         │
                   ┌──── firstMessage ──►│  Simli génère TTS au démarrage
                   │                     │  (ElevenLabs côté Simli)
                   │                     ▼
                   │             Audio WebRTC → Daily iframe → Speakers
                   │             Avatar lip-sync ──────────► Daily iframe
                   │
                   └── Après démarrage : Simli attend audio WebRTC → SILENCE
                       (Ludovic parle mais startAudioOff=true → Simli n'entend rien)


PIPELINE 2 — B-LITE (notre code)
══════════════════════════════════════════════════════════════════
Micro Ludovic
    │
    ▼
getUserMedia (ou track Daily local)
    │
    ▼
AudioContext + ScriptProcessor → RMS → VAD
    │ (seuil > 0.018)
    ▼
MediaRecorder → blob audio (.webm)
    │
    ▼
POST /api/visio/transcribe → Whisper → texte
    │
    ▼
POST /api/visio/chat → GPT-4o-mini → réponse texte
    │
    ▼
POST /api/visio/tts → ElevenLabs → blob audio (.mp3)
    │
    ▼
new Audio(blob) → play() → Speakers
    │
    ╳ NE rejoint PAS le WebRTC Daily
    ╳ NE passe PAS par Simli
    ╳ Simli avatar = IMMOBILE (ne reçoit pas cet audio)
```

---

## 3. Doublons identifiés

| Doublon | Description | Gravité |
|---|---|---|
| **2 pipelines LLM simultanés** | Simli a son propre LLM (gpt-4o-mini via `customLLMConfig`) + notre B-lite a le sien | Élevée |
| **2 pipelines TTS simultanés** | Simli ElevenLabs (WebRTC) + notre ElevenLabs (`new Audio`) | Élevée |
| **2 AudioContext** | `_pretestAudioCtx` + `_vadAudioCtx` | Faible (le prétest se termine avant le call) |
| **2 sorties audio voix Iris** | `firstMessage` Simli joue au démarrage + B-lite joue à chaque réponse | Élevée |
| **getUserMedia appelé 2 fois** | Pré-test + VAD (ou track Daily) | Moyenne |

---

## 4. Conflits identifiés

### Conflit 1 — Simli entend vs. ne répond pas ✗ GRAVE

`startAudioOff: true` dans `dailyCall.join()` → Daily joint la session avec le micro local **muet côté WebRTC**. Simli ne reçoit jamais la voix de Ludovic. Simli est configuré avec STT+LLM+TTS mais ne peut pas s'en servir. **Simli est sourd.**

Conséquence : toute la conversation passe par notre B-lite. Mais Simli a quand même joué le `firstMessage` au démarrage via son propre TTS — ce son vient du Daily iframe, pas de notre code.

### Conflit 2 — Lip-sync mort ✗ GRAVE

Notre B-lite joue la voix d'Iris via un tag `<audio>` HTML. Cet audio n'est **jamais injecté dans le WebRTC Daily**. Simli ne reçoit pas cet audio. Simli ne sait pas quand Iris parle. **La bouche de l'avatar ne bouge pas pendant les réponses B-lite.**

### Conflit 3 — firstMessage + B-lite première réponse ✗ MOYEN

Au démarrage :
1. Simli joue automatiquement le `firstMessage` (via WebRTC Daily iframe)
2. Notre B-lite attend que Ludovic parle pour s'activer

Si Ludovic répond rapidement, les deux flux audio peuvent se chevaucher.

### Conflit 4 — Double getUserMedia ✗ MOYEN

Daily.js ouvre le micro via WebRTC. Notre VAD appelle ensuite `getUserMedia` séparément (ou tente de réutiliser le track Daily). Sur Android, le hardware micro peut n'autoriser qu'une seule prise simultanée. Le patch Codex `fe325ba` tente de réutiliser le track Daily — c'est la bonne direction.

### Conflit 5 — Mute bouton ✗ FAIBLE

Le bouton "🎙 Iris active" (btnMuteLuna) envoie un message texte à Tavus/Simli pour que l'avatar se taise. Mais notre B-lite TTS est indépendant et ne sera pas affecté par ce mute. **Les deux pipelines ne partagent pas l'état mute.**

---

## 5. Composant qui doit devenir l'autorité unique

**Actuellement : aucun n'est l'autorité — les deux coexistent sans coordination.**

### Option A — Simli/Tavus en autorité unique (pipeline provider)

```
Micro → WebRTC Daily → Simli/Tavus (STT + LLM + TTS + lip-sync)
                                          │
                                    Audio WebRTC → Daily iframe
                                    Avatar lip-sync → Daily iframe
```

**Changements requis** :
- Passer `startAudioOff: false` dans `dailyCall.join()` → Simli entend Ludovic
- Supprimer ou désactiver le démarrage de `_startSpeechCapture()` après `joined-meeting`
- Simli gère tout : STT, LLM, TTS, lip-sync

**Avantages** : lip-sync fonctionnel, pipeline simplifié, latence améliorée (tout côté Simli)  
**Inconvénients** : moins de contrôle sur le LLM/prompt, dépendance totale Simli, coût Simli  
**Bloquant** : Simli doit être configuré correctement (SIMLI_API_KEY + SIMLI_FACE_ID en Cloud Run)

---

### Option B — B-lite en autorité unique (pipeline notre code)

```
Micro → getUserMedia → VAD → Whisper → GPT-4o-mini → ElevenLabs
                                                             │
                                            new Audio().play() → Speakers
```

**Changements requis** :
- Supprimer `firstMessage` du payload Simli (ou mettre à `""`)
- Désactiver le LLM/TTS Simli (mais garder Simli pour l'avatar vidéo uniquement)
- Injecter l'audio B-lite dans WebRTC Daily pour lip-sync (complexe : nécessite `replaceTrack` ou `addTrack`)
- Ou accepter définitivement l'absence de lip-sync

**Avantages** : contrôle total du LLM (contexte, prompt, mémoire), latence mesurable  
**Inconvénients** : lip-sync absent sauf injection WebRTC complexe  
**Bloquant** : injection audio WebRTC = niveau 2, nécessite `RTCRtpSender.replaceTrack()`

---

### Option C — Hybride : Simli audio-in + B-lite LLM (non recommandé maintenant)

Utiliser l'API Simli pour lui envoyer des chunks audio (notre TTS → Simli lip-sync), tout en gardant notre LLM. Requiert l'API Simli de type "audio input" — non implémentée dans le code actuel.

---

## 6. Plan de simplification recommandé

**Option A est la voie la plus directe pour un résultat visuel cohérent (lip-sync).** Elle nécessite un test rapide : passer `startAudioOff: false`.

**Option B est la voie actuelle** — elle fonctionne (la voix sort), mais le lip-sync est mort et le restera.

### Décision requise par Ludovic / ChatGPT :

| Question | Choix A | Choix B |
|---|---|---|
| Lip-sync avatar | ✅ Simli le gère | ❌ Absent (ou très complexe) |
| Contrôle LLM/prompt | ❌ Simli gère tout | ✅ Notre GPT-4o-mini |
| Mémoire / contexte Luna | ❌ Via systemPrompt statique | ✅ Build dynamique |
| Simplicité code | ✅ Supprimer B-lite pipeline | ❌ Garder complexité actuelle |
| Dépendance Simli API | ❌ Totale | Partielle (avatar uniquement) |
| Disponibilité actuelle | SIMLI_API_KEY présent en .env | Fonctionne déjà |

**Recommandation Claude : tester Option A d'abord** (une seule ligne à changer : `startAudioOff: true` → `false`). Si le lip-sync et la réponse vocale fonctionnent, on supprime le B-lite pipeline. Si Simli ne répond pas bien, on revient à B-lite.

---

## Annexe — Variables globales audio actives

```javascript
// Capture micro
var _vadAudioCtx       // AudioContext VAD
var _vadStream         // MediaStream micro actif
var _vadProcessor      // ScriptProcessorNode
var _vadMediaRecorder  // MediaRecorder (enregistre les chunks)
var _vadChunks         // Chunks audio collectés
var _vadRecording      // bool : MediaRecorder actif
var _vadActive         // bool : pipeline VAD actif
var _vadBusy           // bool : verrou tour de parole

// Sortie audio
var _irisAudio         // new Audio() — joue TTS ElevenLabs B-lite
```

---

*Aucune modification apportée. Ce document est un état des lieux.*
