# Codex — Verdict terrain visio Iris latence/persona — Objectif 017

Date : 2026-06-02
Agent : Codex
Type : verdict terrain + patch niveau 1

## Verdict

La chaîne technique répond enfin :

- STT : `vad_stt_http 200`
- Whisper : `vad_transcribed ...`
- LLM : `llm_http 200`
- TTS : `tts_http 200`
- Audio : `audio_play_start`

Mais l'expérience produit n'est pas validée :

- temps avant réponse trop long ;
- voix encore trop lente / pas assez jeune ;
- Iris répond trop administratif ;
- Iris ne porte pas encore assez son rôle de concierge technique / Jarvis de Luna ;
- réponses parfois pauvres malgré les capacités réelles du cahier des charges.

## Lecture des erreurs console

- `tabs:outgoing.message.ready` : bruit extension navigateur / DevTools, pas Luna.
- `favicon.ico 404` : bruit cosmétique, corrigé par route `/favicon.ico`.

## Lecture des logs utiles

Exemples terrain :

- `vad_whisper_ms` : 838 à 2616 ms
- `llm_done` : 1458 à 2385 ms
- `tts_done` : 1191 à 2350 ms
- `total_latency_ms` : souvent 11 à 13 s pour les réponses longues

Important : `total_latency_ms` mesure actuellement jusqu'à la fin audio, donc il inclut aussi la durée de lecture. Codex ajoute `time_to_first_audio_ms` pour mesurer le délai réel avant qu'Iris commence à parler.

## Patch appliqué

1. `static/simli.html`
   - Ajout de `vision_context` dans `/api/visio/chat`.
   - Ajout de `participants_count`.
   - Ajout du log `time_to_first_audio_ms`.
   - Historique réduit pour accélérer.

2. `luna_web.py`
   - Contexte visio court : profil, contacts de confiance, notes récentes.
   - Persona Iris renforcé : jeune adulte, vive, technique, proactive, concierge/Jarvis.
   - Réponses limitées par défaut à une phrase courte.
   - `max_tokens` réduit à 75 et température à 0.45.
   - TTS configurable : `ELEVENLABS_MODEL_ID`, `ELEVENLABS_STABILITY`, `ELEVENLABS_SIMILARITY`, `ELEVENLABS_STYLE`, `ELEVENLABS_SPEAKER_BOOST`.
   - Défaut TTS basse latence : `eleven_flash_v2_5`, fallback automatique `eleven_multilingual_v2` si échec.
   - Route `/favicon.ico` ajoutée.

## Cible produit

Iris en visio doit être :

- rapide : début de voix < 3 s en V1 ;
- claire : 1 phrase par défaut ;
- jeune et dynamique : environ 25 ans dans le ton ;
- compétente : concierge technique, pas secrétaire administrative plate ;
- contextuelle : vision caméra, notes, contacts, participants, projet commun ;
- sûre : toute action sensible reste confirmée avant exécution réelle.

## Décision Ludovic requise

Oui pour le changement de voix Cloud Run si on force une nouvelle voix ElevenLabs.

Recommandation Kimi existante :

- Camille : `Z9ZHGvFZ90R0h0x1prsJ`
- Nelly : `iFBdB4I143qF5ByX6o5A`

## Tests attendus après déploiement

Dans F12 :

- plus de `favicon.ico 404`;
- pas de `SyntaxError`;
- `time_to_first_audio_ms` visible ;
- cible : < 3000 ms sur phrases simples ;
- Iris doit répondre à “quels sont tes rôles pendant la visio ?” en mode concierge proactive, pas administratif.
