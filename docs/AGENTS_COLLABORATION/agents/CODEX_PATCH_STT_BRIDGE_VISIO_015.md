# Codex — Patch STT bridge / logs visio — Objectif 015

Agent : Codex
Date : 2026-05-31
Statut : patch code pousse, non deploye

---

## Pourquoi ce patch

Retour terrain Ludovic : Iris parle, mais n'entend pas correctement et ne repond pas vraiment.

Audit Codex du code courant `static/simli.html` :

1. `SpeechRecognition` capture deja la voix locale de Ludovic pour les notes.
2. Ce texte est seulement stocke dans `_visioTranscript`.
3. Il n'est pas envoye au bot Simli.
4. `_sendAppMessageToBot()` etait defini dans le scope de `actCinematicZoom()`, alors que plusieurs fonctions globales l'appellent aussi (vision, upload, mute, etc.).
5. Les logs `rLog()` etaient envoyes au serveur, mais pas visibles dans F12, ce qui empechait Ludovic/Kimi de diagnostiquer proprement.

Conclusion : on peut ajouter un pont de secours non visible.

---

## Ce que le patch fait

Fichier modifie : `static/simli.html`

1. `rLog()` ecrit aussi dans la console navigateur :
   - `[INFO][simli] ...`
   - `[WARN][simli] ...`
   - `[ERROR][simli] ...`

2. `_sendAppMessageToBot()` devient globale :
   - utilisable par la vision ;
   - utilisable par l'upload ;
   - utilisable par le mute ;
   - utilisable par le pont STT local.

3. Le code loggue des events Daily utiles :
   - `participant-updated`
   - `track-started`
   - `track-stopped`
   - audio local / remote quand disponible.

4. Le code detecte si Daily/Simli a deja envoye une utterance utilisateur :
   - `conversation.utterance` role utilisateur -> `_dailyUserSpeechSeen = true`

5. Si Daily/Simli ne prouve pas qu'il a vu la parole utilisateur, le `SpeechRecognition` local envoie la phrase au bot :

   `[Voix utilisateur transcrite localement] ...`

   via `sendAppMessage`.

---

## Ce que ce patch ne fait pas

- Il ne change pas l'UI.
- Il ne change pas Cloud Run.
- Il ne change pas la voix.
- Il ne consomme pas Twilio/SMS/appel/email/paiement.
- Il ne corrige pas la qualite vocale.
- Il ne corrige pas l'architecture Simli si elle est fondamentalement inadaptee.

---

## Risques

| Risque | Niveau | Mitigation |
| --- | --- | --- |
| Doublon si Simli STT marche et ne publie pas `conversation.utterance` au frontend | moyen | Le pont est debounce 2,5s ; test terrain requis |
| `SpeechRecognition` indisponible selon navigateur/WebView | moyen | Log `speech_reco non disponible` |
| Simli ignore `conversation.echo` comme parole utilisateur | moyen | Le log `local_stt_bridge_sent` prouvera au moins l'envoi |
| Le bot recoit le texte comme message systeme et non user | moyen | A valider avec test court |

---

## Test terrain apres deploiement valide

Session < 45s :

1. Ouvrir F12 console.
2. Lancer visio.
3. Dire : "Tu m'entends ? Reponds simplement oui."
4. Chercher :
   - `speech_captured`
   - `local_stt_bridge_sent`
   - `app_msg_conversation_utterance`
   - `track_started local audio`
   - `track_started remote audio`
5. Verdict :
   - si `speech_captured` + `local_stt_bridge_sent` + Iris repond : secours local STT fonctionne.
   - si `speech_captured` absent : probleme navigateur SpeechRecognition/micro.
   - si `local_stt_bridge_sent` present mais aucune reponse : Simli ignore l'app message, architecture a revoir.

---

## Decision Codex

Ce patch est une correction niveau 1/2 : non visible, mais comportement conversationnel modifie.

Il peut etre pousse sur GitHub, mais ne doit pas etre deploye sans validation Ludovic.

Il donne a Claude/Kimi/DeepSeek une base concrete pour tester et diagnostiquer au lieu de continuer a supposer.
