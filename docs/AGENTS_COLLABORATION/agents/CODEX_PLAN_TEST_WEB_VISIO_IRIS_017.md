# Codex — Plan test web reel visio Iris — Objectif 017

## Decision

On arrete les tests a l'aveugle sur telephone.

Prochaine validation : **application web + console F12**, avant nouveau test APK.

## Pourquoi

Retour Ludovic :

- l'entree affiche encore `Visio Luna` alors que la visio est avec Iris ;
- Iris parle avec une voix ElevenLabs non naturelle ;
- Iris ne comprend pas correctement Ludovic ;
- Iris ne repond pas de facon fiable ;
- la camera/vision n'est pas prouvee ;
- l'equipe cherche trop dans le code sans prouver le pipeline reel.

## Test obligatoire en 5 etapes

Objectif : prouver exactement ou la chaine casse.

1. Ouvrir l'app web dans Chrome desktop.
2. Ouvrir F12 Console avant de lancer la visio.
3. Lancer `Visio Iris`.
4. Dire une phrase courte :
   `Iris, est-ce que tu m'entends ? Reponds seulement oui Ludovic.`
5. Copier les logs contenant :
   - `vad_track`
   - `vad_track_muted`
   - `vad_rms`
   - `vad_speech_start`
   - `vad_chunks`
   - `vad_blob_size`
   - `vad_stt_http`
   - `vad_transcribed`
   - `llm_http`
   - `tts_http`
   - `audio_play_start`
   - `total_latency_ms`
   - `vision_no_track`
   - `vision_change`

## Matrice de diagnostic

| Preuve console | Interpretation | Responsable |
|---|---|---|
| Pas de `vad_rms` | VAD pas demarre / AudioContext bloque | Claude |
| `vad_rms` toujours silence | micro non capte / mute / permission | DeepSeek |
| `vad_speech_start` absent malgre parole | seuil VAD ou AudioContext | Claude + DeepSeek |
| `vad_chunks=0` ou `vad_blob_size <500b` | MediaRecorder vide | DeepSeek |
| `vad_stt_http != 200` | Whisper/JWT/backend | Claude |
| `vad_transcribed` faux | STT mauvais / bruit / echo | Kimi + DeepSeek |
| `llm_http != 200` | reponse IA cassee | Claude |
| `tts_http != 200` | ElevenLabs/proxy TTS casse | Claude |
| `audio_play_start` absent | lecture audio bloquee | Claude |
| `total_latency_ms > 3000` | conversation non fluide | Kimi |
| `vision_no_track` repete | vision camera non fonctionnelle | Claude + DeepSeek |

## Definition conversation fluide Iris

Pour valider V1 :

- transcription correcte en moins de 1.2 s ;
- reponse LLM courte et pertinente en moins de 1 s ;
- debut voix en moins de 3 s total ;
- voix calme, dynamique, sans emotion theatrale ;
- Iris ne recapture pas sa propre voix ;
- Iris sait dire ce qu'elle a entendu ;
- Iris ne pretend pas voir si `vision_change` n'existe pas.

## Consignes equipe

### Claude

Ne pas refondre tout de suite.
Verifier d'abord la chaine avec les logs F12.
Si un maillon casse, patch minimal et mesurable.

### DeepSeek

Lire les logs F12 et rendre un verdict technique :
micro, VAD, MediaRecorder, STT, LLM, TTS, vision.
Pas de theorie sans ligne console.

### Kimi

Auditer la qualite conversationnelle :
latence, voix, naturel, statut visuel, comprehension.
Iris doit etre reactive et dynamique, pas theatrale.

### Codex

Maintenir la matrice de preuve.
Ne valider aucune correction sans log ou capture.

## Statut

Patch identite niveau 1 fait dans `static/index.html` :

- menu `+` : `Visio Luna` -> `Visio Iris` ;
- carte Conciergerie : `Visio Luna` -> `Visio Iris` ;
- confirmation : `Lancer la visio Luna ?` -> `Lancer la visio Iris ?`.
