# Codex — Verdict F12 STT 500 visio Iris — Objectif 017

## Preuve terrain

Logs F12 Ludovic :

- `vad_rms ... PAROLE` present ;
- `vad_speech_start` present ;
- `vad_chunks=1` present ;
- `vad_blob_size=23480b` / `31208b` present ;
- `vad_send` present ;
- `vad_stt_http=500` repete ;
- `POST /api/visio/transcribe 500`.

## Conclusion

La rupture principale n'est pas le micro.

La chaine client fonctionne jusqu'a l'envoi audio :

`micro -> VAD -> MediaRecorder -> blob -> POST /api/visio/transcribe`

Le maillon casse est :

`/api/visio/transcribe` cote backend Whisper/STT.

## Cause probable

La route utilisait `openai_client`, construit par `build_llm_client`.

Ce client est OpenAI-compatible et peut pointer vers un provider LLM (`deepseek`, `kimi`, etc.) selon `LLM_PROVIDER`.

Pour Whisper audio, il faut forcer un vrai client OpenAI audio avec `OPENAI_API_KEY`.

## Patch Codex

Fichiers touches :

- `luna_web.py`
- `static/simli.html`

Changements :

- `/api/visio/transcribe` force un client `OpenAI(api_key=OPENAI_API_KEY)` pour Whisper ;
- si `OPENAI_API_KEY` est absente, erreur 503 explicite ;
- log backend `bytes`, `content_type`, `filename` ;
- suffixe temporaire adapte au MIME (`webm`, `mp4`, `ogg`, `wav`, `mp3`) ;
- erreur OpenAI transformee en `502` explicite au lieu de `500` opaque ;
- frontend envoie l'extension selon le MIME du blob ;
- frontend loggue le corps d'erreur STT (`vad_stt_err`) ;
- ajout meta `mobile-web-app-capable` ;
- patch UI anti-superposition : barre actions compacte en largeur reduite, bouton raccrocher deplace a droite.

## Verification

`luna_web.py` compile avec le runtime Python Codex.

## Test attendu apres deploy

Dans F12, la phrase :

`Iris, est-ce que tu m'entends ? Reponds seulement oui Ludovic.`

Doit produire :

- `vad_stt_http 200`
- `vad_transcribed ...`
- `llm_http 200`
- `tts_http 200`
- `audio_play_start`
- `total_latency_ms`

Si `vad_stt_http` reste `502/503`, la cause sera exposee dans `vad_stt_err`.

## Decision

Deployable pour test terrain : **oui**.

Refonte graphique complete : **toujours niveau 2**, a cadrer apres preuve que le pipeline vocal de base repond.
