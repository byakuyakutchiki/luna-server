# Codex — Verdict double couche / lip-sync visio Iris — Objectif 018

Date : 2026-06-02
Agent : Codex
Type : verdict architecture + patch stabilisation audio

## Verdict

Ludovic a raison : l'interface donne l'impression de deux dashboards superposés.

Architecture actuelle :

1. **Couche Simli/Daily**
   - Avatar visuel.
   - Room Daily.
   - Contrôles provider encore visibles ou masqués partiellement.

2. **Couche Luna/Iris**
   - VAD local.
   - Whisper STT.
   - `/api/visio/chat`.
   - `/api/visio/tts`.
   - Lecture audio via `<audio>`.
   - Boutons Iris, notes, partage, vision.

Cette architecture explique le problème de bouche :

> L'audio ElevenLabs est joué par la page web, pas injecté dans Simli comme source de parole avatar.  
> Donc la bouche de l'avatar ne suit pas la voix.

Ce n'est pas un simple bug CSS. C'est une limite de l'Option B-lite.

## Lecture des logs terrain

Le pipeline audio répond :

- `vad_stt_http 200`
- `llm_http 200`
- `tts_http 200`
- `time_to_first_audio_ms` souvent entre 1700 et 2900 ms

Mais :

- les réponses longues font monter `total_latency_ms` à 13-18 s ;
- le VAD peut relancer des captures pendant qu'un tour est encore en traitement ;
- l'image/lip-sync ne suit pas la voix.

## Patch Codex appliqué

1. Ajout d'un verrou `_vadBusy`.
   - Bloque les nouveaux tours pendant STT + LLM + TTS.
   - Évite les fragments superposés.

2. Réponses vocales raccourcies.
   - `max_tokens` : 45.
   - Instruction : 14 mots maximum sauf demande explicite.
   - Pas de markdown/listes longues lues à voix haute.
   - Si support visuel demandé : Iris dicte maintenant et indique que le vrai support sera créé dans les notes après validation.

## Décision architecture à venir

Pour retrouver bouche + voix synchronisées, il faut choisir :

### Option 1 — Assumer B-lite

- Simli = avatar décoratif.
- Audio Luna/Iris = notre `<audio>`.
- Avantage : fonctionne maintenant, économique.
- Défaut : pas de vraie bouche synchronisée.

### Option 2 — Rebrancher la voix dans Simli

- Simli doit recevoir le texte/audio comme source de parole avatar.
- Avantage : lip-sync.
- Défaut : plus complexe, risque de revenir aux problèmes STT/Simli.

### Option 3 — Simli SDK / pipeline plus propre

- Pipeline contrôlé mais audio envoyé à l'avatar pour animation.
- Avantage : architecture cible.
- Défaut : chantier niveau 2, pas patch immédiat.

## Position Codex

Ne pas refaire l'UI tant que cette décision n'est pas claire.

La refonte graphique doit suivre l'architecture :

- si B-lite assumé : design "avatar visuel + voix Iris indépendante" ;
- si lip-sync requis : chantier SDK/Simli propre avant décor.

## Prochaine action agents

- Kimi : dire si une interface sans lip-sync peut être crédible temporairement.
- DeepSeek : auditer comment envoyer audio/texte à Simli pour lip-sync sans perdre le pipeline actuel.
- Claude : ne pas coder de refonte visible avant décision architecture.
- Codex : stabiliser audio V1, puis arbitrer architecture vidéo.
