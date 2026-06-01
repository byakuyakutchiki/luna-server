# DeepSeek — Contre-audit architecture visio Tavus benchmark — Objectif 017

Source : DeepSeek web, transmis par Ludovic le 2026-06-01.
Agent : DeepSeek
Type : contre-audit / benchmark
Niveau : 0

## Verdict

Simli ne peut pas atteindre le niveau Tavus CVI sans une refonte complete du pipeline temps reel.

La faille principale n'est pas dans la qualite de l'avatar, mais dans l'absence de trois couches critiques que Tavus possede nativement :

1. Perception temps reel : couche audio/video qui ecoute en continu.
2. Gestion du tour de parole : savoir quand parler, s'arreter, detecter une interruption.
3. Pipeline unifie : percevoir, raisonner, repondre et rendre dans une boucle continue.

Le systeme actuel Luna + Simli est un assemblage sequentiel :

`STT -> LLM -> TTS -> Simli`

Tavus vise une boucle integree :

`Perception -> Tour de parole -> LLM -> TTS -> Rendu video -> Perception`

## Tableau comparatif

| Couche | Simli actuel Luna | Tavus CVI | Pipeline maison hypothetique |
|---|---|---|---|
| Perception audio | STT WebView fragile ou Whisper batch | Ecoute continue, detection voix, emotion, bruit | WebRTC + VAD + streaming STT |
| Tour de parole | Aucun vrai gestionnaire | Detection fin de parole, interruption, pauses naturelles | VAD + interruption + buffer TTS |
| Modele video | Avatar a partir d'audio, delai 1-3s | Rendu temps reel synchronise | Simli acceptable si pipeline tres bas latence |
| LLM | Appel API externe non stream natif | Integre/configurable stream | LLM streaming + token-level TTS |
| TTS | ElevenLabs batch 1-3s | Integre temps reel | ElevenLabs streaming ou TTS local |
| Latence bout en bout | 4-8s estime | <1s annonce | 1.5-3s realiste |
| Multimodal | Vision camera non cablee | Perception video | WebRTC + analyse frames |
| Protocole | HTTP REST / assemblage | WebRTC temps reel | Migration WebRTC necessaire |
| Interruption | Impossible ou fragile | Naturelle | Buffer TTS annulable |
| Outils | LLM function calling manuel | Integres au pipeline | Faisable |

## Limites structurelles Simli actuel

1. HTTP REST au lieu d'un vrai flux temps reel.
2. Pas de Voice Activity Detection robuste.
3. TTS batch puis playback, donc latence ressentie.
4. Pas d'interruption naturelle.
5. Pas de perception continue audio/video.

## Ameliorations possibles sans migration immediate

Ces ameliorations peuvent rendre le MVP mesurable sans garantir le niveau Tavus :

1. Fallback STT serveur si Web Speech API WebView echoue.
2. Anti-echo : `echoCancellation`, `noiseSuppression`, coupure/ignore STT pendant TTS.
3. VAD cote client pour detecter fin de parole.
4. Streaming ElevenLabs pour reduire la latence percue.
5. Buffer TTS annulable.
6. Logs de latence obligatoires.

## Recommandation froide

Court terme Objectif 017/018 :
- ameliorer Simli avec patchs critiques STT, anti-echo, VAD, streaming TTS ;
- mesurer le gap reel avec le benchmark Tavus ;
- ne pas migrer sans preuve.

Moyen terme Objectif 020+ :
- faire un POC Tavus CVI sur 1 semaine si le gap reste trop grand ;
- tester persona Luna, latence reelle, qualite percue ;
- comparer cout/qualite avant decision.

Long terme :
- pipeline maison WebRTC + VAD + streaming STT/TTS si le volume justifie l'investissement ;
- horizon 3-6 mois, pas Objectif 017.

## Risques

| Risque | Detail |
|---|---|
| Lock-in Tavus | Migration trop rapide vers fournisseur proprietaire |
| Simli non patché | Impossible de savoir si le MVP est viable |
| Pipeline maison premature | Trop long pour Objectif 017 |
| Tests sans mesure | Credits brules sans decision claire |

## Message AGENT_CHANNEL.md

Agent : DeepSeek
Objectif : 017
Type : contre-audit / benchmark
Résumé : Simli ne peut pas atteindre le niveau Tavus CVI sans refonte pipeline WebRTC/VAD/streaming/interruption. Gap structurel : assemblage STT -> LLM -> TTS -> avatar vs pipeline integre perception -> tour de parole -> rendu. Recommandé : patcher Simli pour MVP mesurable (STT, anti-echo, VAD, streaming TTS), puis POC Tavus en parallele si le gap reste trop grand. Ne pas migrer sans preuve a cause du lock-in.
Fichier concerné : docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_TAVUS_BENCHMARK_017.md
Risque : eleve si Simli reste non patché ; moyen/eleve si migration Tavus precipitee
Décision Ludovic requise : oui pour arbitrage POC Tavus payant ou migration fournisseur
Action proposée : Codex mesure le gap ; Kimi definit grille UX Tavus-level ; Claude code seulement les patchs critiques prouves ; Ludovic decide si POC Tavus parallele devient prioritaire.

