# Codex — Decision fondateur Simli V1 budget — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : decision / cadrage
Niveau : 0

## Decision Ludovic

Ludovic ne veut pas de retour Tavus maintenant.

Raison :
- contrainte budget ;
- Simli est le meilleur choix actuel pour Luna ;
- l'equipe doit savoir coder autour de Simli au lieu de fuir vers une solution plus chere.

Formulation fondateur :
> "Je ne veux pas de retour Tavus car on n'a pas les fonds. Simli est notre meilleur choix, a nous de savoir coder."

## Consequence

Tavus reste un benchmark UX/architecture, pas une direction immediate.

La V1 visio Luna doit donc viser le meilleur resultat possible avec :
- Simli pour avatar / visio ;
- Whisper ou STT serveur si WebView SpeechRecognition est fragile ;
- VAD cote client ;
- anti-echo ;
- historique conversationnel ;
- TTS ElevenLabs optimise ;
- instrumentation latence ;
- iterations mesurees.

## Etat apres commit Claude `a7af50e`

Le commit `a7af50e feat(visio): VAD pipeline + conversation history — Objectif 017` est une vraie avance.

Elements confirmes dans le code :
- VAD automatique dans `static/simli.html` ;
- seuil RMS `0.018` ;
- silence timeout `1400ms` ;
- `MediaRecorder` automatique ;
- transcription `POST /api/visio/transcribe` ;
- route backend Whisper dans `luna_web.py` ;
- historique conversationnel envoye a `/api/visio/chat` ;
- etat `speaking` dans `static/luna.css` ;
- fallback PTT conserve.

## Position Codex

La strategie devient :
1. ne pas migrer Tavus ;
2. deployer/tester Simli VAD uniquement si Ludovic donne le feu vert Cloud Run ;
3. mesurer en terrain reel ;
4. corriger par maillon prouve ;
5. viser progressivement le benchmark Tavus-level sans payer Tavus.

## Prochaine validation terrain

Apres deploiement valide par Ludovic :
- ouvrir visio courte ;
- verifier orbe : idle -> listening -> thinking -> speaking ;
- verifier logs `vad_start`, `vad_speech_start`, `vad_send`, `vad_whisper_ms`, `vad_transcribed`, `llm_done`, `tts_done`, `audio_play_start`, `total_latency_ms` ;
- verifier que Ludovic obtient une vraie reponse apres avoir parle ;
- verifier que la voix est moins bizarre avec les nouveaux settings.

## Decision ouverte

Deploiement Cloud Run du commit `a7af50e`.

Decision Ludovic requise : oui.

