# Codex — Retour terrain post-salutation visio — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : risque
Niveau : 0

## Retour Ludovic

Pendant la visio :
- Iris/Luna se presente au demarrage ;
- elle appelle Ludovic `user` car l'utilisateur n'est pas encore inscrit/connecte avec profil complet ;
- apres cette presentation initiale, elle ne repond plus aux phrases de Ludovic.

## Importance diagnostic

Ce retour reduit le champ du probleme :
- le son de sortie initial fonctionne au moins partiellement ;
- le firstMessage / salutation est lu ;
- la panne principale arrive apres la salutation, quand Ludovic parle.

Donc la cause la plus probable n'est pas une panne globale de TTS.
La cause probable est dans le tour utilisateur :
`micro utilisateur -> STT -> texte -> LLM -> TTS reponse`.

## Hypotheses prioritaires

| Hypothese | Probabilite | Preuve attendue |
|---|---:|---|
| STT WebView ne transmet pas le texte a Luna | Haute | Pas de `speech_start` / `speech_text` JS apres parole Ludovic |
| STT capture la salutation ou le son avatar au lieu de Ludovic | Haute | Transcript incoherent ou phrase de l'avatar dans `speech_text` |
| Micro Daily/Simli consomme ou mute le flux utile | Moyenne | `AudioRecordImpl mute`, absence transcript, conflit piste audio |
| Auth/API `/api/visio/chat` echoue apres STT | Moyenne | `llm_fetch_err`, 401/403/500 |
| TTS reponse bloque apres LLM | Moyenne | `llm_done` present mais pas `tts_done/audio_play_start` |
| Identite `user` | Faible pour la panne | Profil absent normal si non inscrit ; a corriger plus tard via session/profil |

## Decision Codex

La salutation initiale ne valide pas la visio.
Elle prouve seulement que la session peut produire un message initial.

Definition de fini minimale :
1. Ludovic parle apres la salutation ;
2. le transcript exact apparait ;
3. `/api/visio/chat` recoit ce transcript ;
4. Luna repond en francais naturel ;
5. la latence du tour complet est mesuree ;
6. aucune capture de la voix avatar n'est traitee comme voix utilisateur.

## Action proposee

Claude :
- ajouter un bridge logs applicatif non sensible pour capturer le tour post-salutation ;
- logger explicitement :
  `after_first_message`, `speech_available`, `speech_start`, `speech_text`, `llm_start`, `llm_done`, `tts_start`, `tts_done`, `audio_play_start`, `total_latency_ms`.

DeepSeek :
- contre-auditer ce nouveau fait : firstMessage OK mais post-salutation KO.

Kimi :
- garder le verdict UX NON VALIDE : une salutation sans dialogue n'est pas une secretaire.

