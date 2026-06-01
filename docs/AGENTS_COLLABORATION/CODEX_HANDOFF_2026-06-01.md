# Codex handoff — Luna / mini-entreprise IA

Date : 2026-06-01  
Repo principal Windows : `C:\Users\saint\Documents\Codex\2026-05-25\luna-server-objectif-006-fresh`  
GitHub : `byakuyakutchiki/luna-server`  

## Qui je suis dans Luna

Je suis Codex, coordinatrice technique et produit pour Luna.

Mon role n'est pas seulement de coder. Je dois :

- structurer les objectifs avant que les agents codent ;
- transformer les retours terrain Ludovic en decisions claires ;
- eviter que Claude, Kimi ou DeepSeek partent dans tous les sens ;
- proteger l'application contre les regressions graphiques, UX et fonctionnelles ;
- maintenir la regle : si ce n'est pas sur GitHub, ce n'est pas livre ;
- ne jamais deployer, lancer SMS/appel/email/paiement/reservation, modifier secrets/Cloud/DB sans validation Ludovic ;
- remonter a Ludovic uniquement les decisions niveau 2/3.

## Mini-entreprise agents

Source de verite : GitHub.

Fichiers principaux :

- `docs/AGENTS_COLLABORATION/AGENT_CHANNEL.md`
- `docs/AGENTS_COLLABORATION/QUEUE.md`
- `docs/AGENTS_COLLABORATION/OBJECTIFS_ACTIFS.md`
- `docs/AGENTS_COLLABORATION/DECISIONS_PENDING.md`
- `docs/AGENTS_COLLABORATION/DECISIONS_VALIDATED.md`
- `docs/AGENTS_COLLABORATION/AGENT_RULES_LIGHT.md`

Roles :

- **Ludovic** : fondateur, validation absolue niveau 2/3.
- **Claude** : integration finale, code, Cloud Run, deploy seulement apres feu vert.
- **Kimi** : UX, graphisme, qualite visuelle, voix, rendu terrain.
- **DeepSeek** : audit technique, risques, faisabilite, contre-audit code.
- **Codex** : coordination, synthese, decisions, garde-fous, matrice de tests, participation code niveau faible risque.

## Regles fortes Ludovic

- Luna doit toujours aller vers plus beau, plus fluide, plus fonctionnel.
- Aucune regression graphique acceptable.
- Ne pas creer de grosse UI visible non validee.
- Ne pas travailler dans le vide : chaque bouton/fonction doit avoir une target claire.
- Pour chaque chantier, definir d'abord : objectif, options attendues, cible utilisateur, preuve de succes, logs/tests.
- Les agents doivent pousser leurs resultats sur GitHub, pas seulement les afficher dans leur terminal.

## Objectifs recents

### Objectif 010 — Chat / titres / recherche

Etat connu :

- Sidebar mobile validee.
- Recherche plein texte historique codee.
- Titres tronques a 4 mots a l'affichage.
- En attente / a surveiller : deploiement et non-regression.

### Objectif 011 — Services / conciergerie

Etat connu :

- Audit Kimi fait.
- Audit granulaire fait.
- Avis Claude/Codex presents.
- P0 identifies : confirmation dialog sur Appeler + Visio.
- Attention Twilio : cout eleve, ne pas tester appels/SMS inutilement.

### Objectif 012 — Canal de decision agents

Etat connu :

- Infrastructure de gouvernance creee.
- Canal GitHub utilise comme salle de decision.
- Agents autonomes niveau 0/1, Ludovic consulte niveau 2/3.

### Objectif 014 — Recadrage visio reelle

But :

- arreter de coder sans vision produit ;
- definir ce qu'Iris/Luna doit faire en visio ;
- comprendre les contextes implicites : personnel, professionnel, demo exploitant, assistance, invite tiers, administratif/document, urgence ;
- options attendues : notes, resume, actions a suivre, observation camera, rappel, recherche, document, texte secours discret, invitation tiers, actions sensibles encadrees.

Documents importants :

- `docs/AGENTS_COLLABORATION/OBJECTIF_014_RECADRAGE_VISIO_REELLE.md`
- `docs/AGENTS_COLLABORATION/agents/CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`
- `docs/AGENTS_COLLABORATION/agents/KIMI_REAL_VISIO_UX_014.md`
- `docs/AGENTS_COLLABORATION/agents/CLAUDE_PLAN_VISIO_014.md`

### Objectif 015/016 — Visio temps reel / STT / voix / vision camera

Probleme terrain :

- Simli affiche l'avatar et sort de l'audio.
- Voix initiale Alice mauvaise : accent anglais, lente, pateuse, "Iris" entendu "Riff".
- Kimi recommande Camille `Z9ZHGvFZ90R0h0x1prsJ` pour test.
- Ludovic a pris ElevenLabs, mais il faut rester econome.
- Iris ne repondait pas car Simli auto ne prouvait pas le STT.
- Logs terrain ont montre :
  - micro local playable ;
  - bot Simli joined ;
  - SpeechRecognition navigateur capte Ludovic ;
  - pas de `stt_user_utterance` Simli ;
  - `conversation.echo` inefficace ;
  - risque de boucle en captant la voix d'Iris ;
  - `vision_no_track` pour camera.

Architecture retenue pour test :

```text
Web Speech API -> /api/visio/chat -> /api/visio/tts -> lecture audio frontend
```

Commit important :

- `f224954 feat(015): Option B-lite pipeline conversationnel contrôlé`
- `6033091 fix(016): STT + vision — libérer micro/caméra de Daily.js`
- `b5873fa agent: cadrer reprise option b lite visio`

Derniere correction Claude `6033091` :

- Cause Iris n'entend pas : Daily.js prenait le micro exclusivement.
- Fix : `startAudioOff: true` pour liberer le micro Web Speech API.
- Cause camera : parent frame ne pouvait pas lire les tracks iframe Daily.
- Fix : stream camera conserve depuis le pretest, vision loop l'utilise directement.

Claude doit deployer ce fix sur Cloud Run depuis la VM :

```bash
cd /home/ludo/luna-server
git pull origin main
gcloud run deploy luna-beta --source=. --region=europe-west1 --project=crypto-parser-475411-k4
```

Codex a tente de deployer depuis Windows, mais `gcloud` n'est pas disponible dans cette session Windows. Claude doit le faire depuis la VM.

## Logs de validation attendus apres deploiement

Pour une phrase simple en visio, la console F12 doit montrer :

```text
speech_start
speech_end
stt_done
llm_start
llm_done
tts_start
tts_done
audio_play_start
audio_play_end
total_latency_ms
```

Pour la camera, il faut ne plus voir :

```text
vision_no_track
```

Si les logs cassent :

| Logs observes | Conclusion |
|---|---|
| aucun `speech_start` | B-lite non deployee, SpeechRecognition non lance, navigateur bloque |
| `speech_start` sans `llm_start` | bug frontend `_irisReply()` ou `_irisReplying` bloque |
| `llm_start` sans `llm_done` | endpoint `/api/visio/chat` KO |
| `tts_start` sans `tts_done` | endpoint `/api/visio/tts` KO ou ElevenLabs |
| `audio_play_start` sans reponse utile | audio joue mais UX/texte mauvais |
| `total_latency_ms` > 4000 regulierement | conversation non fluide |
| `vision_no_track` | camera parent toujours non exploitee |

## Definition conversation fluide

- Excellent : < 1.5 s.
- Acceptable V1 : 1.5 s a 3 s.
- Limite : 3 s a 4 s.
- Echec produit : > 4 s regulierement.
- Echec total : > 6 s.
- Reponses simples : 1 a 2 phrases.
- Pas de capture de la propre voix d'Iris comme demande utilisateur.

## Ne pas oublier

- Le bouton/feature visio doit avoir des targets claires avant patch.
- La voix seule ne suffit pas : une voix qui parle dans le vide = lecteur audio, pas secretaire.
- La vision camera est un chantier separe de B-lite.
- Twilio coute cher : aucun SMS/appel de test sans validation explicite.
- ElevenLabs coute aussi : tests courts, peu nombreux, logs utiles.
- Simli a 1000 minutes rechargees mais il faut rester econome.

## Dernier statut connu

- Repo local Windows propre apres push `b5873fa`.
- `gcloud` absent de la session Windows Codex.
- Claude doit deployer `6033091` depuis la VM.
- Apres deploiement, Ludovic doit tester une visio courte et copier les logs F12.
- Codex doit ensuite analyser les logs et dire exactement quel maillon est valide ou casse.

## Phrase de reprise nouvelle session

Si une nouvelle session Codex demarre, Ludovic peut ecrire :

```text
Lis docs/AGENTS_COLLABORATION/CODEX_HANDOFF_2026-06-01.md et reprends ton role de coordinatrice Codex Luna.
Verifie GitHub, lis AGENT_CHANNEL.md, QUEUE.md et les derniers fichiers agents, puis dis-moi ou on en est sur la visio.
```

