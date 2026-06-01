# DeepSeek — Chasse rupture pipeline visio Iris — Objectif 017

Source : DeepSeek web, transmis par Ludovic le 2026-06-01.
Agent : DeepSeek
Type : audit technique / risque
Niveau : 0

## Methode

Tracer chaque maillon du pipeline du point de vue du code et chercher les ruptures silencieuses :
- celles qui ne produisent pas d'erreur visible ;
- celles qui laissent l'interface active mais cassent le flux voix.

## Labels Iris

DeepSeek confirme les incoherences reperees par Codex :
- `Luna voit`
- `Luna active`
- `Luna muette`
- `Luna voit et peut en parler`
- `Chatbot`

Le commit Claude `89d9a1d` a deja remplace les labels visibles Luna -> Iris dans `static/simli.html`.

## 7 points de rupture possibles

| Point | Rupture | Probabilite | Impact | Preuve a collecter |
|---|---|---:|---|---|
| 1 | Micro silencieux | Elevee | VAD tourne, RMS reste a 0 | Logs RMS |
| 2 | AudioContext suspendu | Tres elevee | ScriptProcessor ne traite rien | `AudioContext.state` |
| 3 | MediaRecorder vide | Elevee | Blob vide, Whisper inutile | `audioChunks.length`, `blob.size` |
| 4 | JWT expire | Moyenne | 401 silencieux sur `/api/visio/transcribe` | HTTP status STT/LLM/TTS |
| 5 | Conflit Daily/Simli sur micro | Moyenne | Daily prend/parasite le micro | Ordre iframe/VAD + flux tracks |
| 6 | Whisper langue non forcee | Faible | Mauvaise transcription | `language="fr"` |
| 7 | Mute non synchronise | Faible | VAD actif mais silence | Etat mute UI / track enabled |

## Logs obligatoires pour Codex / Claude

### AudioContext

```js
console.log('[Iris] AudioContext state:', audioContext.state);
```

Attendu : `running`, pas `suspended`.

### Micro

```js
console.log('[Iris] Micro tracks:', stream.getAudioTracks());
console.log('[Iris] Track readyState:', track.readyState);
console.log('[Iris] Track enabled:', track.enabled);
```

Attendu : track `live` et `enabled=true`.

### RMS

```js
console.log('[Iris] RMS:', rms);
```

Attendu : RMS > `0.018` quand Ludovic parle.

### MediaRecorder

```js
console.log('[Iris] Chunks recorded:', chunks.length);
console.log('[Iris] Blob size:', blob.size);
```

Attendu : blob > 1000 bytes.

### HTTP status

```js
console.log('[Iris] STT status:', sttRes.status);
console.log('[Iris] LLM status:', llmRes.status);
console.log('[Iris] TTS status:', ttsRes.status);
```

Attendu : 200 pour les trois.

### Ordre chargement

```js
console.log('[Iris] VAD start time:', ...);
console.log('[Iris] Daily iframe load time:', ...);
```

But : verifier conflit micro Daily/Simli vs VAD.

## Correctif minimal propose par DeepSeek

Dans `_startVAD()` :
- logguer `AudioContext.state` ;
- appeler `audioContext.resume()` si `suspended` ;
- verifier la track micro ;
- logguer track label/readyState/enabled ;
- surveiller periodiquement si AudioContext redevient suspendu.

## Decision Codex

Sans ces logs, chaque test terrain reste trop flou.

Avant de valider la visio :
1. prouver que l'AudioContext est `running` ;
2. prouver que le micro produit un RMS > seuil ;
3. prouver que MediaRecorder produit un blob non vide ;
4. prouver que `/api/visio/transcribe`, `/api/visio/chat`, `/api/visio/tts` retournent 200 ;
5. prouver que la reponse audio joue.

## Message AGENT_CHANNEL.md

Agent : DeepSeek
Objectif : 017
Type : chasse rupture pipeline visio
Résumé : 7 points de rupture identifiés. Les plus probables : AudioContext suspendu sur mobile, MediaRecorder vide, micro silencieux/RMS nul. Autres : JWT 401 silencieux, conflit Daily/Simli sur micro, Whisper sans langue forcee, mute non synchronise. Correctif minimal : logs AudioContext + resume(), track micro, RMS, blob size, HTTP status STT/LLM/TTS.
Fichier concerné : static/simli.html fonction `_startVAD()`
Risque : eleve si pipeline muet sans logs
Décision Ludovic requise : non
Action proposée : Claude ajoute les logs et garde-fous, Codex capture, DeepSeek contre-audite.

