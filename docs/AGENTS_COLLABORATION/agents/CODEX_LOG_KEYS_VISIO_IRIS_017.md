# Codex — Cles reelles logs visio Iris — Objectif 017

## But

Aligner DeepSeek, Claude, Kimi et Codex sur les **vraies cles console** presentes dans `static/simli.html`.

DeepSeek peut garder son arbre de diagnostic, mais il doit lire les noms reels ci-dessous.

## Cles console a utiliser

| Etape | Cle reelle |
|---|---|
| init VAD | `vad_init` |
| AudioContext initial | `vad_actx_state_init` |
| AudioContext suspendu | `vad_actx_suspended_init`, `vad_actx_suspended` |
| AudioContext repris | `vad_actx_resumed` |
| erreur resume | `vad_actx_resume_fail`, `vad_resume_err` |
| piste micro | `vad_track` |
| piste absente | `vad_track_missing` |
| piste mauvaise | `vad_track_bad` |
| piste muted | `vad_track_muted` |
| pas d'AudioContext | `vad_no_audiocontext` |
| RMS | `vad_rms` |
| debut parole | `vad_speech_start` |
| chunks MediaRecorder | `vad_chunks` |
| blob audio | `vad_blob_size` |
| audio trop court | `vad_audio_empty` |
| envoi STT | `vad_send` |
| token absent | `vad_no_token` |
| statut STT | `vad_stt_http` |
| JWT STT expire | `vad_jwt_expired` |
| STT HTTP erreur | `vad_stt_err` |
| duree Whisper | `vad_whisper_ms` |
| transcription vide | `vad_transcribe_empty` |
| texte transcrit | `vad_transcribed` |
| erreur transcription | `vad_transcribe_err` |
| statut LLM | `llm_http` |
| erreur LLM | `llm_http_err`, `llm_fetch_err`, `llm_empty` |
| statut TTS | `tts_http` |
| erreur TTS | `tts_error`, `tts_fetch_err` |
| lecture audio | `audio_play_start`, `audio_play_end`, `audio_error`, `audio_play_blocked` |
| latence totale | `total_latency_ms` |
| vision demarree | `vision_start` |
| pas de camera | `vision_no_track` |
| description vision | `vision_change` |
| erreur vision | `vision_api_err`, `vision_fetch_err`, `vision_tick_error` |

## Phrase de test minimale

`Iris, est-ce que tu m'entends ? Reponds seulement : oui Ludovic.`

## Regle de diagnostic

Le dernier log present avant une absence indique le maillon casse.

Exemples :

- `vad_rms ... PAROLE` present mais pas `vad_speech_start` : seuil/timing VAD.
- `vad_speech_start` present mais `vad_chunks=0` : MediaRecorder.
- `vad_blob_size` present mais pas `vad_stt_http` : fetch STT reseau/auth/CORS.
- `vad_stt_http=200` mais `vad_transcribe_empty` : audio inaudible ou Whisper.
- `vad_transcribed` correct mais pas `llm_http=200` : route chat/LLM.
- `llm_http=200` mais pas `tts_http=200` : TTS.
- `tts_http=200` mais pas `audio_play_start` : lecture audio bloquee.
- `vision_no_track` repete : camera non disponible pour la boucle vision.

## Sortie attendue DeepSeek

Un tableau par phrase avec :

- derniere cle presente ;
- premiere cle absente ou rouge ;
- maillon casse ;
- patch minimal recommande.
