# Codex — Gap cible Documents / Porte-document — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : risque / proposition
Niveau : 0

## Constat terrain

Capture de reference :
`docs/AGENTS_COLLABORATION/phone_tests/codex-functional-sweep-20260601-202016/05-lasttab-secretary.png`

Ecran reel observe sur telephone :
- titre `Mes Documents` ;
- quatre compteurs `Total`, `En attente`, `En retard`, `Regle`, tous a 0 ;
- champ recherche ;
- bouton `Scanner` ;
- filtre unique `Tous` ;
- etat vide `Aucun document scanne` ;
- bloc replie `Documents generes par Luna`.

## Cible demandee par Ludovic

Source :
- `docs/CAHIER_DES_CHARGES_MONITORING.md`, section `Documents — Vault IA`
- `docs/PROMPT_CLAUDE_MONITORING_DOCUMENTS.md`

L'objectif n'est pas un simple stockage de fichiers. Luna doit etre un grand porte-document de vie courante :
- scanner ;
- classer automatiquement ;
- rendre visible dans une bibliotheque claire ;
- retrouver par recherche, categorie ou timeline ;
- expliquer le contenu ;
- detecter echeances / urgences ;
- proposer l'action utile : relance, paiement, courrier, appel organisme, formulaire, rappel.

## Gap cible vs reel

| Cible porte-document | Etat reel telephone | Gap |
|---|---|---|
| Repertoires Identite, Sante, Domicile, Finances, Travail, Famille, Vehicule, Assurances, Administratif, Factures, Urgence, Autres | Filtre unique `Tous` | Les repertoires attendus ne sont pas visibles |
| Bibliotheque claire | Etat vide + liste absente | Pas de structure de bibliotheque quand aucun document n'existe |
| Timeline | Absente de l'onglet mobile | Route v2 existe, mais surface mobile non visible |
| Documents urgents / echeances | Absents de l'onglet mobile | Pas de priorisation utilisateur |
| Actions suggerees | Absentes de l'onglet mobile | Luna ne montre pas quoi faire avec un document |
| Detail document : resume, organisme, date, montant, echeance | Non testable depuis l'ecran vide | Pas de carte exemple / etat de demo non sensible |
| Chat : "retrouve ma facture EDF" | Non prouve | Besoin d'un test non destructif avec document factice |
| Suppression / consentement / RGPD | Non visible sur cet ecran | Controle utilisateur incomplet dans la surface mobile |
| Documents generes par Luna | Visible mais separe | Confusion possible entre documents scannes et documents produits |

## Hypothese technique

Le backend v2 semble exister :
- `/api/documents/v2/dashboard`
- `/api/documents/v2/timeline`
- `/api/documents/v2/categories`
- `/api/documents/v2/actions/{doc_id}`
- `/api/documents/v2/actions/execute`

Mais l'onglet mobile `static/index.html` affiche une version minimale et ne rend pas encore l'experience "porte-document" attendue.

## Recommandation

Ouvrir Objectif 018 — Documents / Porte-document reel.

Definition de fini :
1. Ecran mobile Documents montre les grandes categories meme a vide.
2. L'etat vide explique la promesse utile sans roman : scanner, classer, retrouver, agir.
3. Le dashboard montre `Urgent`, `A traiter`, `Echeances`, `Categories`.
4. Un document factice non sensible peut etre scanne/teste.
5. Luna peut retrouver ce document par recherche et proposer au moins une action.
6. Aucune action sensible reelle n'est lancee sans confirmation.

## Missions agents proposees

Kimi :
- auditer l'UX mobile Documents en partant de la capture reelle ;
- proposer une version premium, lisible, sans regresser le style Luna ;
- separer clairement `Porte-document` et `Documents generes par Luna`.

DeepSeek :
- verifier si les routes v2 sont branchees a l'onglet mobile ;
- cartographier `static/index.html` vs `static/documents.html` vs routes `/api/documents/v2/*` ;
- signaler le patch minimal pour exposer le vrai dashboard sans casser le scan.

Claude :
- attendre les avis Kimi/DeepSeek ;
- ne pas coder tant que la cible UI Documents n'est pas validee ;
- preparer ensuite un patch minimal niveau 1 si uniquement surfacage UI / route existante.

Codex :
- coordonner la matrice cible -> preuve terrain -> patch ;
- tester sur telephone reel apres patch ;
- ne valider que si le rendu sert le porte-document, pas seulement un ecran vide plus joli.

