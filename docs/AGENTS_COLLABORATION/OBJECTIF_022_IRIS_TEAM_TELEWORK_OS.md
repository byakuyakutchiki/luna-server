# Objectif 022 — Iris Team / Telework Operating System

## Statut

Ouvert — cadrage produit Codex actif.

## Vision fondateur

Iris ne doit pas etre seulement une IA qui affiche des tableaux ou des graphiques.

Iris doit devenir un **centre de commande de travail** utile a :

- une personne seule en teletravail ;
- une equipe en reunion ;
- un dirigeant qui pilote des dossiers ;
- une entreprise qui veut organiser, produire, decider et suivre.

Phrase cible :

> Iris transforme une conversation de travail en actions concretes, visibles, organisees et validables.

Elle ecoute, comprend, structure, affiche, prepare, demande confirmation, puis execute seulement quand c'est autorise.

## Difference Luna / Iris

| Entite | Role | Limite |
|---|---|---|
| Luna | Compagne conversationnelle, conseil, discussion, vision large, figure dirigeante YAWatch | Oriente vers Iris quand il faut produire, agir, organiser ou manipuler des outils |
| Iris | Operatrice du centre de commande : documents, recherche, equipe, actions, decisions, outils, conformité | Ne doit jamais executer une action sensible sans validation |

Luna parle.
Iris travaille.

## Target exacte

Quand l'utilisateur travaille avec Iris, il doit sentir :

1. qu'Iris comprend le contexte ;
2. qu'elle sait quel outil activer ;
3. que l'ecran de travail bouge en temps reel ;
4. que les resultats sont visibles, modifiables, telechargeables ou validables ;
5. que les actions sensibles sont bloquees jusqu'a confirmation ;
6. qu'une equipe peut collaborer sans perdre le fil.

Un livrable est valide seulement si le chemin complet fonctionne :

`intention utilisateur -> outil reel -> garde-fou -> rendu visuel -> action/validation -> preuve`

## Familles de capacites

### 1. Assistant de reunion

Objectif : aider une equipe pendant une reunion.

Capacites attendues :

- prendre des notes automatiquement ;
- identifier les decisions prises ;
- detecter les sujets ouverts ;
- reperer qui doit faire quoi ;
- creer les taches a la fin ;
- generer un compte-rendu propre ;
- preparer l'envoi du compte-rendu apres validation ;
- afficher participants, roles, decisions, actions ;
- signaler les zones floues : "budget non decide", "echeance non confirmee".

Render types attendus :

- `meeting_board`
- `action_board`
- `decision_board`
- `document_draft`
- `status_rail`

Preuve attendue :

- demander : "Iris, prends les notes de cette reunion et sors les decisions" ;
- voir un `meeting_board` evoluer ;
- obtenir une synthese finale telechargeable ou copiable ;
- aucune action envoyee sans confirmation.

### 2. Assistant teletravail individuel

Objectif : aider une personne a organiser et produire sa journee.

Capacites attendues :

- organiser la journee ;
- prioriser les taches ;
- rappeler les urgences ;
- transformer une idee orale en plan d'action ;
- suivre les objectifs de la semaine ;
- resumer les documents recus ;
- preparer les emails ;
- dire : "Tu as 3 sujets ouverts : lequel on termine maintenant ?"

Render types attendus :

- `kanban_board`
- `roadmap`
- `action_board`
- `status_rail`
- `document_insight`

Preuve attendue :

- demander : "Iris, organise ma journee de travail" ;
- voir un kanban ou une roadmap, pas un paragraphe ;
- verifier que les priorites sont modifiables.

### 3. Assistant equipe / projet

Objectif : permettre a une equipe de travailler ensemble dans Iris.

Capacites attendues :

- creer un espace de session ;
- inviter un participant ;
- afficher les roles ;
- afficher les responsabilites ;
- suivre l'avancement ;
- muter/exclure un invite seulement par l'owner ;
- afficher les decisions et actions en direct ;
- centraliser les documents utiles ;
- montrer qui est responsable de quoi.

Render types attendus :

- `session_panel`
- `meeting_board`
- `kanban_board`
- `status_rail`
- `action_board`

Preuve attendue :

- session owner + invite ;
- participant visible ;
- action sensible demandee par invite -> validation owner obligatoire ;
- mute/kick visibles mais non dangereux.

### 4. Assistant dirigeant

Objectif : aider un fondateur ou manager a piloter.

Capacites attendues :

- preparer business plan ;
- preparer budget ;
- comparer fournisseurs ou concurrents ;
- structurer une decision ;
- suivre objectifs/KPI ;
- produire courrier, note, synthese ;
- chercher une information externe avec sources ;
- alerter sur risques : cout, RGPD, delai, action sensible.

Render types attendus :

- `kpi_cards`
- `chart`
- `budget_board`
- `comparison`
- `decision_board`
- `document_draft`
- `research_board` si implemente, sinon `context_panel` avec sources.

Preuve attendue :

- demander : "Iris, prepare un business plan visuel pour mon projet" ;
- voir KPI + budget + roadmap + document draft ;
- si donnees manquantes, voir `missing_info` clair.

### 5. Assistant documents

Objectif : faire du porte-documents un outil de travail reel.

Capacites attendues :

- uploader un document ;
- analyser PDF/contrat/facture/devis ;
- extraire dates et risques ;
- comparer deux documents ;
- classer automatiquement ;
- generer un resume telechargeable ;
- retrouver un document du souscripteur ;
- respecter droits, consentement, suppression.

Render types attendus :

- `document_insight`
- `document_draft`
- `comparison`
- `timeline`
- `action_board`

Preuve attendue :

- upload fichier test ;
- analyse visuelle ;
- document classe ;
- suppression possible avec confirmation.

### 6. Assistant communication

Objectif : preparer les communications sans declencher d'action dangereuse.

Capacites attendues :

- preparer SMS ;
- preparer email ;
- preparer courrier ;
- preparer invitation reunion ;
- resumer avant envoi ;
- demander confirmation ;
- bloquer horaires interdits ;
- bloquer numeros d'urgence ;
- journaliser resultat.

Render types attendus :

- `action_board`
- `document_draft`
- `contact_board`
- `status_rail`

Preuve attendue :

- demander : "Iris, envoie un SMS a Lucas" ;
- Iris affiche brouillon + validation requise ;
- aucun SMS reel sans validation explicite.

### 7. Assistant recherche externe

Objectif : connecter Iris au monde exterieur.

Capacites attendues :

- chercher sur le web ;
- citer sources ;
- resumer page ou article ;
- comparer offres/prix/fournisseurs ;
- produire une veille ;
- ramener l'information dans le Command Screen.

Render types attendus :

- `research_board` a creer si absent ;
- fallback `context_panel` avec sources ;
- `comparison`
- `decision_board`

Preuve attendue :

- demander : "Iris, cherche Base Legacy sur le web et montre-moi les sources" ;
- voir sources, resume, limites ;
- pas de phrase "je n'ai pas acces" si l'outil est branche.

### 8. Assistant vision

Objectif : comprendre ce qui se passe dans l'environnement.

Capacites attendues :

- decrire ce qu'elle voit ;
- lire un document montre a la camera ;
- detecter presence/absence ;
- detecter objets utiles : ordinateur, papier, facture, ecran ;
- comprendre contexte reunion ;
- dire clairement si la vision n'est pas active.

Render types attendus :

- `context_panel`
- `document_insight`
- `status_rail`
- `media_board`

Preuve attendue :

- demander : "Iris, qu'est-ce que tu vois ?" ;
- obtenir soit une description reelle, soit un statut clair "vision inactive" avec cause.

### 9. Assistant conformite / garde-fous

Objectif : eviter qu'Iris fasse une action illegale, couteuse ou dangereuse.

Capacites attendues :

- verifier action sensible ;
- demander consentement ;
- bloquer SMS/appel/email sans confirmation ;
- bloquer suppression sans double confirmation ;
- respecter RGPD ;
- limiter donnees personnelles ;
- signaler incertitude juridique ;
- verifier quotas/couts avant action.

Render types attendus :

- `action_board`
- `status_rail`
- `missing_info`

Preuve attendue :

- toute action sensible affiche "validation requise" ;
- pas d'execution sans retour succes reel.

### 10. Assistant Jarvis / centre de commande

Objectif : donner une experience futuriste mais utile.

Capacites attendues :

- "prepare-moi un dossier complet sur X" ;
- "surveille ce sujet" ;
- "rappelle-moi demain" ;
- "cree une mission" ;
- "invite quelqu'un dans la session" ;
- "montre-moi ou on en est" ;
- "transforme notre discussion en plan executable" ;
- afficher le travail en temps reel : tool_start, render_update, render_done.

Render types attendus :

- `status_rail`
- `roadmap`
- `kanban_board`
- `meeting_board`
- `document_draft`
- `research_board`

Preuve attendue :

- voir l'ecran bouger pendant le travail ;
- pas d'attente silencieuse ;
- si blocage > 10s, afficher la cause probable.

## Regle temps reel

Iris doit montrer son travail progressivement :

1. `Iris analyse...`
2. `Iris cherche...`
3. `Iris structure...`
4. `Iris projette...`
5. `Pret — modifier / telecharger / sauvegarder / envoyer apres validation`

Interdit :

- rester silencieuse plus de 10 secondes sans feedback ;
- remplir l'ecran avec son speech ;
- dire "patiente" sans barre/etat visible ;
- presenter un faux resultat comme termine.

## Missions agents

### Kimi

Produire l'UX complete de Iris Team / Telework OS :

- desktop ;
- mobile ;
- mode clair/sombre ;
- ecran reunion ;
- ecran teletravail ;
- ecran projet ;
- ecran documents ;
- ecran communication ;
- ecran recherche ;
- etats temps reel ;
- criteres premium/non cheap.

Livrable :

`docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_TEAM_TELEWORK_OS_022.md`

### DeepSeek

Produire le contrat technique :

`intent -> tool -> render_type -> garde-fou -> preuve`

Verifier :

- outils existants ;
- routes manquantes ;
- outils exposes a OpenAI Realtime ;
- handlers frontend ;
- filtres de droits ;
- risques cout/Twilio/RGPD.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_TECH_IRIS_TEAM_TELEWORK_OS_022.md`

### Kimi Code

Quand Kimi UX + DeepSeek technique sont lus, coder seulement la V1 non dangereuse :

- rendu temps reel ;
- meeting_board ;
- kanban_board ;
- document_draft ;
- action_board validation_required ;
- pas de SMS/appel/email reel ;
- pas de suppression ;
- pas de stockage cloud nouveau sans validation.

### Codex

Coordonner, verifier la target cell, refuser les livrables incomplets, produire les consignes finales.

## Definition de livraison

Objectif 022 n'est pas livre quand Iris "dit" qu'elle peut aider.

Objectif 022 est livre quand Iris :

- comprend le contexte ;
- affiche le bon ecran ;
- fait bouger le workspace ;
- produit un livrable exploitable ;
- demande validation si action ;
- donne une preuve du resultat.
