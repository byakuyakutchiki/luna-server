# Codex — Patch double getUserMedia — Objectif 017

Date : 2026-06-02
Agent : Codex
Type : correctif niveau 1

## Problème

La visio ouvrait déjà le micro via Daily.js, puis le VAD demandait un second `getUserMedia({ audio: true })`.
Sur WebView/mobile, deux prises micro peuvent créer une piste muette, instable ou concurrencer Daily.

## Correctif

`_startVAD()` cherche maintenant d'abord la piste audio locale Daily :

- `local.tracks.audio.persistentTrack`
- puis `local.tracks.audio.track`

Si la piste Daily est vivante, le VAD construit `new MediaStream([track])` et écoute cette piste.
Si elle est absente, le code garde un fallback `getUserMedia`.

## Garde-fous

- La piste empruntée à Daily n'est pas stoppée par `_stopVAD()`.
- Les pistes ouvertes par le fallback `getUserMedia` restent stoppées normalement.
- Logs ajoutés :
  - `vad_daily_track_probe`
  - `vad_using_daily_track`
  - `vad_getusermedia_fallback`
  - `vad_stream_source`
  - `vad_borrowed_track_kept`

## Test attendu F12

Après déploiement :

1. `vad_using_daily_track` idéalement.
2. Sinon `vad_getusermedia_fallback`, ce qui reste fonctionnel mais signale que Daily ne donne pas sa piste.
3. `vad_track ... muted=false`.
4. `vad_stt_http 200`.
5. `vad_transcribed ...`.
6. `llm_http 200`.
7. `tts_http 200`.
8. `audio_play_start`.

## Décision

Pas de décision Ludovic requise pour ce patch : il réduit un conflit micro sans changer le design global.
La refonte UI visio reste une décision niveau 2.
