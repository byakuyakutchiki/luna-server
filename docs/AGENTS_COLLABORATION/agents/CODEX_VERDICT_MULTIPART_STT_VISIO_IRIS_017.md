# Codex — Verdict multipart STT visio Iris — Objectif 017

## Preuve terrain

F12 Ludovic :

`vad_stt_err HTTP 500 {"ok":false,"error":"The `python-multipart` library must be installed to use form parsing."}`

## Conclusion

Cause concrete trouvee :

Cloud Run n'a pas `python-multipart`.

La route `/api/visio/transcribe` appelle `await request.form()` pour lire le fichier audio `FormData`.

Sans `python-multipart`, FastAPI echoue avant Whisper.

## Pourquoi on ne le voyait pas avant

`requirements.txt` contient deja `python-multipart`.

Mais Docker Cloud Run installe :

`requirements-cloudrun.txt`

Ce fichier ne contenait pas `python-multipart`.

## Patch Codex

Fichiers touches :

- `requirements-cloudrun.txt` : ajout `python-multipart>=0.0.6` ;
- `static/simli.html` :
  - badge vision honnete : `Vision en attente` / `Vision active`, plus `Iris voit` abusif ;
  - masque bas pour cacher la barre Daily blanche et reduire l'effet de boutons inutiles ;
  - garde les corrections STT precedentes.

## Test attendu apres deploy

Phrase :

`Iris, est-ce que tu m'entends ? Reponds seulement oui Ludovic.`

On veut voir :

- `vad_stt_http 200`
- `vad_transcribed ...`
- `llm_http 200`
- `tts_http 200`
- `audio_play_start`

Si `vad_stt_http` n'est pas 200, copier `vad_stt_err` complet.

## Statut

Deployable : **oui**.

Priorite : deployer puis retester F12 avant tout autre debat voix/refonte.
