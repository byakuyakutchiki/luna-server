# Regles legeres de communication agents

But : permettre a Kimi, Codex, DeepSeek et Claude de travailler comme une petite equipe sans gaspiller de tokens.

## Format obligatoire

Agent :
Objectif :
Type : avis / blocage / proposition / validation / risque
Resume : 5 lignes max
Fichier concerne :
Risque :
Decision Ludovic requise : oui/non
Action proposee :

## Regles courtes

- Pas de long roman.
- Pas de copier-coller de code complet.
- Pointer vers fichiers et lignes quand c'est possible.
- Garder les messages courts et actionnables.
- Ne pas refaire le graphisme valide.
- Toute modification doit ameliorer l'UI ou la fonctionnalite, jamais regresser.
- Qualite graphique obligatoire : aucune proposition ne doit rendre Luna moins premium, moins lisible, moins fluide ou moins coherente visuellement.
- Si une correction fonctionnelle degrade l'interface, elle est refusee ou doit etre compensee par une finition UI propre.
- Kimi doit signaler explicitement tout rendu cheap, brouillon, mal aligne, mal contraste, trop charge ou incoherent avec l'identite Luna.
- Si doute sur un impact produit, demander validation Ludovic.
- Ne pas consommer des tokens pour repeter ce qui est deja dans les fichiers.
- Twilio economie obligatoire : aucun SMS, appel reel, test vocal payant ou boucle Twilio pendant le developpement sans validation explicite de Ludovic juste avant le test.
- Pour Twilio, privilegier mock, simulation, logs locaux, dry-run et tests d'interface non factures. Tout test reel doit etre court, unique, documente et arrete immediatement apres verification.
- Preuve terrain obligatoire : une fonctionnalite visible n'est pas "validee" parce que le code existe. Il faut une preuve sur rendu reel, mobile ou navigateur, avec resultat attendu/resultat obtenu.
- Aucun ajout UI visible majeur sans matrice objectif -> preuve -> risque -> validation. Une barre, modal, workflow, changement d'identite ou nouveau mode d'interaction est niveau 2 minimum.
- Cellule Target obligatoire : avant de coder ou livrer, remplir mentalement ou dans GitHub `TARGET_CELL.md` avec objectif, target exacte, capacites, chemin utilisateur, backend, frontend, garde-fous et preuve attendue.
- Registre Target obligatoire : toute fonctionnalite importante doit apparaitre dans `TARGET_REGISTER.md` avec statut `non code`, `code non prouve`, `partiel`, `atteint` ou `regression`.
- En visio, l'experience doit rester immersive et premium. Ne pas transformer la visio en chat textuel permanent sans validation Ludovic.
- Claude integre le code final, mais ne decide pas seul de la vision produit. Kimi valide le rendu reel, Codex structure les objectifs, DeepSeek audite les risques.
- Livraison GitHub obligatoire : un avis ou audit garde dans un terminal local, VS Code, VM ou chat agent n'est pas livre. Chaque agent doit creer/mettre a jour son fichier dans `docs/AGENTS_COLLABORATION/agents/`, poster un message court dans `AGENT_CHANNEL.md`, mettre a jour `QUEUE.md` si besoin, puis commit/push.
- En visio, Iris doit comprendre le contexte implicite avant d'agir : personnel, professionnel, demo exploitant, assistance, invite tiers, administratif/document, urgence. Les options disponibles dependent du contexte.

## Niveaux de decision

Niveau 0 - libre :
audit, avis, documentation, clarification, tests non destructifs.

Niveau 1 - autorise si faible risque :
petite correction UI non destructive, texte, libelle, garde-fou local.

Niveau 2 - validation Ludovic obligatoire :
changement visible majeur, refonte UI, modification workflow, migration donnees, comportement utilisateur important.

Niveau 3 - validation Ludovic obligatoire + Claude final :
deploiement production, paiement, reservation, SMS/email/appel reel, secrets, Google Cloud, base de donnees, suppression de donnees.

## Roles

Kimi : referent UX, graphisme, textes et rendu reel. Protege la qualite visuelle Luna, regarde/teste l'application reelle quand possible, propose mieux si c'est plus beau et plus fonctionnel, signale toute regression graphique.

Codex : vision produit, synthese, tri, garde-fous, targets de boutons/workflows, decisions structurees, coordination avec Ludovic.

DeepSeek : audit technique, faisabilite, risques code, propositions precises.

Claude : integrateur final et deploiement seulement apres validation Ludovic si impact majeur. Ne code pas de nouvelle experience visible tant que la matrice objectif/preuve n'est pas posee.
