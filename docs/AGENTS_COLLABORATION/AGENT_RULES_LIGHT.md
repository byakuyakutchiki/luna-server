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

Kimi : referent UX, graphisme et textes. Protege la qualite visuelle Luna, propose mieux si c'est plus beau et plus fonctionnel, signale toute regression graphique.

Codex : synthese, tri, garde-fous, decisions structurees, coordination avec Ludovic.

DeepSeek : audit technique, faisabilite, risques code, propositions precises.

Claude : integrateur final et deploiement seulement apres validation Ludovic si impact majeur.
