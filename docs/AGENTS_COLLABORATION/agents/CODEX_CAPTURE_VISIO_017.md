# Codex — Capture terrain visio — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : test terrain / risque
Niveau : 0

## Sessions capturees

1. Capture realtime :
   `docs/AGENTS_COLLABORATION/phone_tests/visio-realtime-20260601-210019/`

2. Six captures espacees :
   `docs/AGENTS_COLLABORATION/phone_tests/visio-6-captures-20260601-210124/`

## Ce qui est prouve visuellement

Captures `capture_01.png` a `capture_06.png` :
- la visio est active ;
- l'ecran affiche `Luna active` ;
- l'ecran affiche `Luna voit` ;
- l'appel Daily indique `2 people in call` ;
- l'avatar est visible ;
- la camera utilisateur est visible en miniature ;
- sur `capture_06.png`, Ludovic leve la main et cela apparait dans la miniature.

Conclusion visuelle :
- la camera utilisateur est bien accessible a l'interface ;
- l'affichage `Luna voit` ne prouve pas encore que Luna/Iris interprete réellement l'image ;
- la visio est lancee, mais la boucle intelligente n'est pas prouvee.

## Ce qui est prouve par logcat

Fichier :
`docs/AGENTS_COLLABORATION/phone_tests/visio-6-captures-20260601-210124/logcat_filtered_tail.txt`

Signaux notables :
- `RecognitionClient #onStartOfSpeech`
- `RecognitionService#onStartOfSpeech`
- nombreux `AudioRecordImpl [audioRecordData][mute]`
- nombreux `AudioTrackImpl [audioTrackData][zero]`
- warnings Chromium WebRTC : `No decodable frame ... requesting keyframe`
- warnings audio : `Critical Jitter Error`, `HAL write blocked`

Interpretation prudente :
- Android demarre bien un service de reconnaissance vocale a un moment du test ;
- cela ne prouve pas qu'un texte STT arrive dans le JavaScript Luna ;
- les logs audio montrent plusieurs flux muets/zero, ce qui peut expliquer une experience lente ou silencieuse ;
- les warnings WebRTC video indiquent des frames non decodables, a surveiller pour la qualite visio.

## Ce qui n'est PAS encore prouve

Absents des preuves :
- `speech_reco` côté JS Luna ;
- `speech_start` avec texte Ludovic ;
- `stt_done` ;
- `llm_start` / `llm_done` ;
- `/api/visio/chat` status ;
- `/api/visio/tts` status ;
- `tts_done` ;
- `audio_play_start` / `audio_play_end` ;
- `total_latency_ms` ;
- preuve que Luna interprete `je leve la main`.

Conclusion :
la capture ne suffit pas encore pour valider la boucle :
`micro -> STT -> comprehension -> reponse -> TTS -> action`.

## Problème capture DevTools

Fichier :
`docs/AGENTS_COLLABORATION/phone_tests/visio-realtime-20260601-210019/webview_console_visio.jsonl`

Le capteur DevTools s'est attache a une cible `about:blank`, avec logs Google Ads, pas a la page Luna/Simli active.

Preuve :
`webview_targets.json` contient :
- `title`: `about:blank`
- `url`: `about:blank`
- `faviconUrl`: `https://googleads.g.doubleclick.net/favicon.ico`

Donc :
- la capture console WebView actuelle n'est pas exploitable pour les logs Luna ;
- il faut corriger l'attache DevTools pour viser la bonne cible WebView ou ajouter un bridge de logs applicatif.

## Matrice provisoire preuve -> cause

| Preuve | Ce que cela dit | Cause probable | Action |
|---|---|---|---|
| Visio active + 2 personnes | Daily/Simli rejoint | Lancement OK | Ne pas re-debugger le lancement |
| Miniature camera avec main levee | Camera utilisateur disponible dans l'UI | Source video OK côté interface | Il manque l'analyse vision réelle |
| `RecognitionService#onStartOfSpeech` | Android reco vocale demarre | STT systeme existe | Verifier si JS reçoit le transcript |
| Absence `llm_done/tts_done/total_latency_ms` | Boucle applicative non prouvee | Logs non captes ou pipeline casse | Bridge logs obligatoire |
| `AudioRecordImpl mute` répété | Flux micro possiblement muet | micro coupé, conflit Daily, ou silence perçu | Auditer contraintes micro / mute |
| `AudioTrackImpl zero` répété | Flux audio sortie possiblement vide | TTS muet, buffer zero, ou piste Daily inactive | Auditer playback et TTS |
| `No decodable frame` WebRTC | Flux video remote instable | encodage/decodage Daily/Simli | Surveiller qualite image |
| DevTools `about:blank` | Mauvaise cible capturée | script DevTools trop naïf | Corriger script ou bridge logs |

## Décision Codex

La visio reste NON VALIDEE.

On a prouve :
- appel visio actif ;
- camera utilisateur visible ;
- main levee visible dans la miniature ;
- presence d'un demarrage Android speech recognition.

On n'a pas prouve :
- que Luna entend Ludovic ;
- que le texte arrive au backend ;
- que le LLM repond ;
- que le TTS joue naturellement ;
- que Luna voit/interprete la main levee.

## Prochaine action recommandee

Claude :
- ajouter un bridge de logs applicatif non sensible depuis `static/simli.html` vers une surface capturable :
  - console fiable ;
  - `window.__lunaVisioLogs` exportable ;
  - ou endpoint debug non sensible.
- logs obligatoires :
  `speech_reco`, `speech_start`, `speech_text`, `llm_start`, `llm_done`, `tts_start`, `tts_done`, `audio_play_start`, `audio_play_end`, `total_latency_ms`.

DeepSeek :
- contre-auditer ces preuves partielles ;
- confirmer si `RecognitionService#onStartOfSpeech` suffit a infirmer l'hypothese "Web Speech API absente" ;
- analyser `AudioRecordImpl mute` et `AudioTrackImpl zero`.

Kimi :
- auditer visuellement les captures : avatar, libelle `Chatbot`, boutons, credibilite secretaire, mini camera, statut `Luna voit`.

Codex :
- corriger le script DevTools pour ne pas capturer `about:blank` ;
- relancer un test court apres bridge de logs.

