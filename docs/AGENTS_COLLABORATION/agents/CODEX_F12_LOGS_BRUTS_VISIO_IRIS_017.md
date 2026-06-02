# Codex — Logs F12 bruts visio Iris — Objectif 017

## Source

Retour terrain Ludovic depuis Chrome/F12 sur :

`https://luna-beta-674304336025.europe-west1.run.app/simli?duration=1&_v=31`

Contexte : test visio Iris avec console ouverte.

## Logs / erreurs navigateur

```text
simli?duration=1&_v=31:2533 [Deprecation] The ScriptProcessorNode is deprecated. Use AudioWorkletNode instead. (https://bit.ly/audio-worklet)
_setupProcessor @ simli?duration=1&_v=31:2533
(anonyme) @ simli?duration=1&_v=31:2593
Promise.then
_startVAD @ simli?duration=1&_v=31:2503
_startSpeechCapture @ simli?duration=1&_v=31:2631
(anonyme) @ simli?duration=1&_v=31:1356
o.emit @ daily-js:1
value @ daily-js:1
value @ daily-js:1
```

Interpretation Codex :

- Avertissement navigateur.
- Pas la cause du blocage actuel.
- A migrer plus tard vers `AudioWorkletNode` pour robustesse/performance, mais non prioritaire face au STT 500.

```text
VM196 vendor.js:159 Uncaught (in promise) Error: Uncaught Error: No Listener: tabs:outgoing.message.ready
```

Interpretation Codex :

- Probablement lie a une extension Chrome / DevTools / environnement navigateur.
- Pas une erreur Luna prouvee.

```text
favicon.ico:1 GET https://luna-beta-674304336025.europe-west1.run.app/favicon.ico 404 (Not Found)
```

Interpretation Codex :

- Erreur cosmetique.
- Pas liee au pipeline visio.
- A corriger plus tard avec un favicon, mais pas bloquant.

## Erreurs STT repetees

```text
fetch.js:43 POST https://luna-beta-674304336025.europe-west1.run.app/api/visio/transcribe 500 (Internal Server Error)
(anonyme) @ fetch.js:43
_sendVADAudio @ simli?duration=1&_v=31:2451
_vadMediaRecorder.onstop @ simli?duration=1&_v=31:2420
```

Cette erreur s'est repetee plusieurs fois.

Interpretation Codex :

- Le client envoie bien un audio via `_sendVADAudio`.
- Le `MediaRecorder` s'arrete et declenche bien l'envoi.
- La rupture est cote backend `/api/visio/transcribe`.

## Erreur detaillee transcribe

```text
console.js:36 [WARN][simli] vad_stt_err HTTP 500 {"ok":false,"error":"The `python-multipart` library must be installed to use form parsing."}
(anonyme) @ console.js:36
rLog @ simli?duration=1&_v=31:749
(anonyme) @ simli?duration=1&_v=31:2466
Promise.then
(anonyme) @ simli?duration=1&_v=31:2465
Promise.then
_sendVADAudio @ simli?duration=1&_v=31:2456
_vadMediaRecorder.onstop @ simli?duration=1&_v=31:2420
```

Cette erreur s'est repetee plusieurs fois.

Interpretation Codex :

- Cause racine prouvee : `python-multipart` absent de l'image Cloud Run.
- FastAPI ne peut pas parser `request.form()`.
- Whisper/OpenAI n'est meme pas atteint.
- Le patch `e6f0bc3` ajoute `python-multipart>=0.0.6` dans `requirements-cloudrun.txt`.

## Observations visuelles Ludovic

Ludovic a signale sur capture :

- trop de boutons visibles dans la visio ;
- boutons superposes ou mal positionnes ;
- gros bouton vocal central juge trop lourd ;
- controles Daily/Simli en bas visibles et inutiles ;
- bouton camera a gauche visible mais sans utilite claire pour Iris ;
- bouton micro visible mais incoherent tant que Iris ne comprend pas ;
- bouton central supplementaire non compris ;
- badge `Iris voit` incoherent si la camera/perception n'est pas réellement active ;
- experience visuelle jugee tres inferieure au niveau attendu.

## Logs utiles deja observes dans la console

Exemples vus dans les captures precedentes :

```text
[INFO][simli] vad_blob_size 35072b
[INFO][simli] vad_send 35072b
[INFO][simli] vad_stt_http 500
[INFO][simli] vad_rms 0.0008 silence
[INFO][simli] vad_rms 0.0002 silence
[INFO][simli] vision_change 1 personne présente, assis(e). Objets: sandwich.
[INFO][simli] vad_speech_start
[INFO][simli] vad_rms 0.0413 PAROLE
[INFO][simli] vad_chunks 1
[INFO][simli] vad_blob_size 31208b
[INFO][simli] vad_send 31208b
[INFO][simli] vad_stt_http 500
[INFO][simli] vision_change Personne n'est visible dans le champ de la camera.
```

Interpretation Codex :

- VAD detecte la parole.
- Blob audio existe.
- Le backend STT casse.
- Vision backend renvoie parfois une description, mais l'UI ne doit pas annoncer `Iris voit` sans contexte exact.

## A transmettre aux agents

### Claude

Verifier que le deploy inclut bien `requirements-cloudrun.txt` avec `python-multipart`.
Apres deploy, confirmer dans les logs Cloud Run que `/api/visio/transcribe` ne tombe plus sur `python-multipart`.

### DeepSeek

Utiliser ces logs comme base de contre-audit.
Ne pas repartir sur une hypothese micro : micro/VAD/blob sont prouves.
Chercher ensuite les flux morts et handlers anciens.

### Kimi

Utiliser les observations visuelles comme base de refonte UI Iris V1.
Priorite : retirer les doublons, ranger les actions secondaires, rendre la visio propre et credible.

## Statut

Le fix technique `python-multipart` est pret dans `e6f0bc3`.

La visio Iris reste non validee tant que :

- STT ne renvoie pas `200` ;
- UI boutons n'est pas clarifiee ;
- chaque bouton visible n'a pas une target prouvee.
