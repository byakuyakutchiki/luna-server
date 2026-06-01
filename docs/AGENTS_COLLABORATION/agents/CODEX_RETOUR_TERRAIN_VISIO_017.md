# Codex — Retour terrain Ludovic visio — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : risque
Niveau : 0

## Retour terrain Ludovic

Test reel visio apres derniers deploiements.

Constats utilisateur :
- la voix reste bizarre et non naturelle ;
- la fluidite est mauvaise ;
- il y a un souci de lenteur ;
- Luna/Iris ne repond pas correctement ;
- elle indique ne pas comprendre ce que Ludovic dit ;
- donc la boucle conversationnelle n'est pas validee.

## Conclusion produit

La visio ne peut pas etre consideree comme fonctionnelle.

Le probleme n'est plus seulement :
- choix de voix ;
- avatar ;
- CSS ;
- affichage Daily/Simli.

Le probleme principal est la boucle vivante :
`micro Ludovic -> STT -> comprehension -> reponse -> TTS -> restitution naturelle`.

## Cibles non atteintes

| Target | Etat terrain |
|---|---|
| Voix feminine francaise naturelle | KO |
| Latence conversationnelle acceptable | KO |
| Comprend Ludovic | KO |
| Repond a la question posee | KO |
| Ne dit pas "je ne comprends pas" en boucle | KO |
| Experience secretaire credible | KO |

## Decision de coordination

Priorite P0 :
1. capturer un test reel avec `tools/agents/visio_realtime_capture.ps1` ;
2. isoler si le probleme vient du STT, du prompt, du LLM, du TTS, du bridge Simli ou de la boucle audio ;
3. ne plus deployer de patch voix/image seul tant que la boucle conversationnelle n'est pas prouvee.

## Missions agents

Kimi :
- evaluer le ressenti voix/delai comme UX humaine ;
- proposer une cible voix acceptable, mais ne pas valider la visio tant que la comprehension est KO.

DeepSeek :
- auditer le flux technique complet STT/LLM/TTS ;
- chercher pourquoi Luna dit qu'elle ne comprend pas alors que le micro est autorise.

Claude :
- ne plus patcher au feeling ;
- attendre la capture realtime et les logs ;
- coder ensuite uniquement le maillon identifie comme cause racine.

Codex :
- organiser le prochain test reel court ;
- produire la matrice preuve -> cause -> correctif.

