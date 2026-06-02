# Codex — Mission collective visio Iris — Objectif 017

## Contexte fondateur

Ludovic valide le diagnostic STT, mais refuse que l'equipe reduise le probleme a ce seul point.

La visio Iris a aussi un probleme produit :

- trop de boutons visibles ;
- superpositions ;
- doublons entre controles Luna et controles Daily/Simli ;
- statut vision incoherent ;
- boutons presents alors que leur target n'est pas prouvee ;
- experience loin du niveau attendu : visio reactive, claire, naturelle, type Tavus-level en qualite percue, sans changer de fournisseur pour l'instant.

## Decision Codex

On ne valide pas la visio Iris apres le seul fix `python-multipart`.

On lance une **audition collective obligatoire** du chantier visio.

Chaque agent doit verifier un angle different et publier sur GitHub.

## Ce que les logs ont deja prouve

| Maillon | Statut |
|---|---|
| Micro navigateur | OK |
| VAD | OK |
| MediaRecorder | OK |
| Blob audio envoye | OK |
| Backend STT | KO avant patch : `python-multipart` absent Cloud Run |
| Vision camera | Partielle : `vision_change` existe, mais UI disait trop vite `Iris voit` |
| UI visio | KO : trop de boutons, superpositions, doublons |

## Regle absolue

Aucun bouton ne doit rester visible s'il ne respecte pas ces 3 conditions :

1. target claire ;
2. etat visible coherent ;
3. preuve que l'action fonctionne ou fallback propre.

Sinon :

- cacher le bouton ;
- le deplacer dans un menu secondaire ;
- ou le marquer comme indisponible avec raison claire.

## Cartographie boutons actuels

| Bouton / controle | Target | Probleme actuel | Action attendue |
|---|---|---|---|
| `Iris active` / mute | Couper ou retablir la parole d'Iris | Libelle ambigu : micro utilisateur ou voix Iris ? | Kimi propose libelle clair ; DeepSeek verifie effet reel |
| `Analyser` | Partager document/image a Iris | Action utile mais secondaire | Garder dans menu secondaire si la conversation vocale est prioritaire |
| `Inviter` | Envoyer invitation visio | Action sensible SMS potentiel | Verification confirmation + cout + cible |
| `Partager` | Copier/partager lien | Utile mais secondaire | Menu secondaire |
| `Notes` | Resumer/sauvegarder conversation | Utile seulement si transcript fonctionne | Desactiver tant que STT non valide |
| Orb `Parler` | VAD/PTT vocal | Trop gros, recouvre avatar ; mais fonction centrale | Garder, mais design plus sobre et statut clair |
| `Raccrocher` | Terminer appel | Essentiel | Toujours visible, sans superposition |
| Badge vision | Montrer etat perception camera | `Iris voit` etait faux si vision non prouvee | `Vision en attente` puis `Vision active` seulement apres description |
| Controles Daily/Simli | Controle iframe provider | Doublons inutiles, boutons blancs moches | Claude doit verifier options SDK/provider pour les masquer vraiment |

## Missions agents

### Claude — integration code / provider

1. Deployer `e6f0bc3` seulement apres validation Ludovic.
2. Verifier apres deploy que `python-multipart` est bien installe dans Cloud Run.
3. Auditer Daily/Simli :
   - quels controles viennent de l'iframe ;
   - quelles options SDK peuvent les masquer ;
   - si impossible, proposer contournement propre sans casser micro/camera.
4. Ne pas refaire la refonte complete sans validation.
5. Publier : `CLAUDE_AUDIT_PROVIDER_CONTROLES_VISIO_017.md`.

### DeepSeek — audit technique exhaustif

1. Contre-auditer le patch `e6f0bc3`.
2. Verifier que `requirements-cloudrun.txt` est bien celui installe par Dockerfile.
3. Chercher anciennes routes/anciens flux encore branches :
   - Web Speech ancien ;
   - Simli auto STT ;
   - Tavus/Daily remnants ;
   - fonctions doublonnees ;
   - boutons relies a de vieux handlers.
4. Publier une carte des flux actifs et morts.
5. Publier : `DEEPSEEK_AUDIT_FLUX_MORTS_VISIO_017.md`.

### Kimi — UX / design / qualite percue

1. Partir de la capture Ludovic.
2. Proposer un layout Iris V1 propre :
   - avatar prioritaire ;
   - 1 action principale vocale ;
   - raccrocher toujours visible ;
   - actions secondaires rangees ;
   - pas de doublons Daily visibles ;
   - statut vision honnete.
3. Dire quels boutons doivent disparaitre de l'ecran principal.
4. Publier : `KIMI_REFONTE_UI_VISIO_IRIS_V1_017.md`.

### Codex — coordination / preuve terrain

1. Maintenir la matrice bouton -> target -> preuve.
2. Refuser toute validation sans log/capture.
3. Apres deploy, demander un seul test F12 :
   `Iris, est-ce que tu m'entends ? Reponds seulement oui Ludovic.`
4. Si STT passe, seulement ensuite tester LLM/TTS/latence.

## Critere de sortie

La visio Iris ne sera pas consideree comme correcte tant que :

- `vad_stt_http=200` ;
- `vad_transcribed` contient la phrase Ludovic ;
- `llm_http=200` ;
- `tts_http=200` ;
- `audio_play_start` existe ;
- `total_latency_ms < 3000` sur phrase courte ;
- aucun bouton inutile/doublon ne recouvre l'avatar ;
- badge vision coherent avec la realite ;
- chaque bouton visible a une target prouvee.

## Statut

Correction technique STT prete : `e6f0bc3`.

Mais la visio globale reste **non validee**.
