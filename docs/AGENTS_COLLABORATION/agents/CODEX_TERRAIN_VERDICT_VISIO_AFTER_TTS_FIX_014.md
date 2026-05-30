# Codex — Verdict terrain apres fix TTS — Objectif 014

Agent : Codex  
Date : 2026-05-31  
Source : retour terrain Ludovic apres revision `luna-beta-00463-ktx`  
Statut : sortie audio debloquee, visio non validee  

---

## Retour terrain Ludovic

Apres changement de cle ElevenLabs et deploiement Cloud Run :

1. L'assistante parle maintenant.
2. Elle s'est presentee avec un nom percu comme "Riff" au lieu de "Iris".
3. La qualite vocale n'est pas satisfaisante.
4. La voix a un accent anglais trop prononce.
5. L'image/avatar est distordue.
6. Elle n'entend toujours pas ce que Ludovic dit.
7. Elle ne repond pas vraiment a Ludovic.

---

## Decision Codex

La sortie audio est debloquee, mais la visio n'est pas fonctionnelle.

On ne doit pas declarer Objectif 014 resolu.

Le probleme se decoupe maintenant en 4 chantiers P0/P1 :

| Priorite | Probleme | Statut |
| --- | --- | --- |
| P0 | Iris n'entend pas Ludovic / ne repond pas | bloque la promesse visio |
| P0 | Mauvaise identite prononcee ("Riff" au lieu de "Iris") | casse la credibilite |
| P1 | Voix Alice accent anglais / qualite faible | acceptable seulement pour test, pas produit |
| P1 | Image/avatar distordu | regression UX visuelle |

---

## Lecture produit

Le fait qu'Iris parle prouve que :

- la nouvelle cle ElevenLabs fonctionne ;
- Cloud Run transmet bien une cle TTS utilisable ;
- Simli peut generer au moins une sortie vocale.

Mais le fait qu'elle n'entende pas Ludovic prouve que :

- le flux entrant micro/STT n'est pas valide ;
- la conversation n'est pas encore interactive ;
- la visio reste une animation vocale, pas une secretaire.

---

## Hypotheses techniques prioritaires

### H1 — STT / micro Simli non actif ou non transmis

L'utilisateur parle, mais Simli/LLM ne recoit pas le texte. A verifier avec logs Daily/Simli et transcript.

### H2 — Permission micro Daily/WebView partielle

Le navigateur autorise peut-etre la camera ou la room, mais la piste audio locale n'est pas publiee correctement.

### H3 — Bot present mais non configure pour ecouter/repondre apres firstMessage

Le `firstMessage` est joue, mais la session n'entre pas en boucle conversationnelle.

### H4 — Prompt/voix prononce mal "Iris"

Avec accent anglais, "Iris" peut etre mal prononce ou percu comme "Riff". Il faut forcer la prononciation ou choisir un autre nom/voix pour les tests.

### H5 — Distorsion image due au conteneur iframe/video

Le rendu Daily/Simli peut etre etire par CSS (`width/height: 100%`) sans respect de ratio, ou par l'avatar/face ID lui-meme.

---

## Taches imposees

### Claude — diagnostic interaction micro/STT + image

Claude doit produire :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_DIAGNOSTIC_STT_IMAGE_014.md`

Contenu attendu :

1. confirmer si Daily publie la piste audio locale ;
2. confirmer si Simli recoit des utterances utilisateur ;
3. verifier si `conversation.utterance` arrive dans `app-message` ;
4. verifier si `_visioTranscript` contient des phrases utilisateur ;
5. verifier les permissions micro navigateur/WebView ;
6. auditer la distorsion image : iframe, video, object-fit, aspect ratio ;
7. proposer un patch minimal non visible ou faiblement visible ;
8. ne pas deployer sans validation si UI visible ou Cloud Run.

### DeepSeek — contre-audit STT/Simli

DeepSeek doit produire :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_STT_SIMLI_COUNTER_AUDIT_014.md`

Contenu attendu :

1. payload Simli requis pour ecoute micro / STT ;
2. verification endpoint `/auto/start/configurable` pour interaction bidirectionnelle ;
3. differencier `firstMessage` joue vs vraie conversation ;
4. verifier events Daily utiles : participants, tracks, app-message, transcription ;
5. identifier instrumentation minimale pour prouver "Ludovic est entendu".

### Kimi — avis voix/identite/avatar

Kimi doit produire :

`docs/AGENTS_COLLABORATION/agents/KIMI_VOICE_IDENTITY_IMAGE_014.md`

Contenu attendu :

1. verdict UX sur la voix Alice : acceptable / non acceptable ;
2. proposition de voix feminine FR plus credible, accessible dans ElevenLabs si possible ;
3. solution pour eviter "Iris" prononce comme "Riff" : prononciation, phrase, nom, SSML si supporte ;
4. verdict image/avatar distordu avec capture ou description ;
5. decision Ludovic requise : choix voix, nom, avatar, correction visuelle.

---

## Interdictions

- ne pas tester longtemps Simli ;
- ne pas redeployer au hasard ;
- ne pas changer de voix sans test court ElevenLabs direct ;
- ne pas ajouter de barre texte intrusive ;
- ne pas lancer SMS/appel/email/paiement/reservation ;
- ne pas mettre de secret dans GitHub.

---

## Prompt court pour Claude

Claude, lis :

`docs/AGENTS_COLLABORATION/agents/CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`

Retour terrain : Iris parle maintenant, mais elle se presente comme "Riff", la voix a un accent anglais, l'image est distordue, et surtout elle n'entend pas Ludovic / ne repond pas.

Ta priorite n'est plus ElevenLabs. Ta priorite est STT/micro/interaction + distorsion image.

Livrable GitHub :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_DIAGNOSTIC_STT_IMAGE_014.md`

Ne deploie rien sans validation.

---

## Prompt court pour DeepSeek

DeepSeek, lis :

`docs/AGENTS_COLLABORATION/agents/CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`

Contre-audit requis : pourquoi Simli joue le firstMessage mais n'entend pas Ludovic ensuite ?

Livrable GitHub :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_STT_SIMLI_COUNTER_AUDIT_014.md`

Pas de secret, pas de session longue, pas de deploiement.

---

## Prompt court pour Kimi

Kimi, lis :

`docs/AGENTS_COLLABORATION/agents/CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`

Ton role terrain UX : voix, identite, image.

Livrable GitHub :

`docs/AGENTS_COLLABORATION/agents/KIMI_VOICE_IDENTITY_IMAGE_014.md`

Verdict attendu : la voix actuelle n'est pas produit-ready si accent anglais + mauvaise prononciation. Propose une option plus credible et plus elegante, sans regression graphique.
