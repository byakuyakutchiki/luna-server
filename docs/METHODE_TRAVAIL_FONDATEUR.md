# Methode de travail — Interet fondateur, qualite produit, exploitants

Ce document formalise la maniere de travailler sur Luna avec Ludo, fondateur de YAWatch.

Il sert de boussole pour Codex, Claude, Kimi, DeepSeek et toute IA ou developpeur intervenant sur le repo.

## Intention de Ludo

Ludo est le fondateur. Le but n'est pas seulement que le code compile : le but est que l'application fonctionne en production, protege les droits du fondateur, donne une experience haut de gamme aux utilisateurs, et permette aux exploitants de developper leurs clients sans detourner la technologie.

Les IA doivent donc optimiser pour :

- l'interet du fondateur ;
- la stabilite de l'application ;
- la qualite graphique et fonctionnelle ;
- le respect du modele de licence ;
- la tracabilite des royalties ;
- la separation propre entre ce que l'exploitant peut voir et ce que le fondateur doit proteger.

## Principe produit

Avant toute extension ambitieuse, tous les boutons, onglets et parcours existants doivent fonctionner.

Un onglet est valide seulement si :

- il s'ouvre sans erreur ;
- les boutons visibles declenchent une action utile ;
- l'utilisateur recoit un resultat comprehensible ;
- les erreurs sont affichees proprement ;
- le monitoring peut dire si l'objectif est atteint ;
- aucune modification ne degrade l'interface.

## Qualite graphique

Luna doit donner une impression de produit premium.

Toute modification UI doit respecter :

- lisibilite mobile ;
- boutons visibles et accessibles ;
- pas de texte qui deborde ;
- pas de regression visuelle ;
- pas d'interface brouillonne ajoutee vite fait ;
- coherence avec le style existant.

Si une IA modifie `static/`, elle doit verifier que les ecrans critiques restent utilisables.

## Architecture fondateur / exploitant

L'exploitant utilise une licence pour exploiter Luna avec ses clients.

Il doit pouvoir :

- configurer son serveur ;
- gerer ses clients ;
- suivre son activite ;
- utiliser les fonctionnalites necessaires a son exploitation ;
- payer les royalties dues au fondateur.

Il ne doit pas pouvoir :

- contourner la licence ;
- supprimer le mecanisme de royalties ;
- acceder aux secrets du fondateur ;
- se donner des droits fondateur ;
- voir du code ou des informations qui permettraient de reproduire l'architecture protegee ;
- neutraliser le monitoring licence sans alerte.

## Donnees visibles par le fondateur

Le fondateur doit avoir une vue suffisante pour proteger ses droits, sans entrer abusivement dans la comptabilite interne de l'exploitant.

Le fondateur peut legitimement suivre :

- licence active ou non ;
- serveur actif ou bloque ;
- nombre de clients actifs ;
- nombre d'abonnes ;
- plans vendus ;
- chiffre d'affaires servant de base aux royalties, si prevu par contrat ;
- royalties dues ;
- paiements de royalties ;
- anomalies licence ;
- tentatives de contournement ;
- etat global du serveur exploitant ;
- qualite de service globale.

Le fondateur ne doit pas chercher a voir :

- la comptabilite interne complete de l'entreprise exploitante ;
- les depenses detaillees hors Luna ;
- les donnees privees inutiles des clients ;
- les informations qui ne sont pas necessaires au contrat de licence.

## Protection licence et anti-contournement

Le monitoring doit inclure des signaux de protection :

- heartbeat licence ;
- statut licence `active`, `degraded`, `blocked` ;
- integrite des fichiers sensibles ;
- detection de modification suspecte ;
- detection de suppression du heartbeat ;
- incoherence entre clients actifs et royalties declarees ;
- absence prolongee de reporting ;
- changements suspects de configuration ;
- alerte fondateur en cas de violation.

Les fichiers critiques incluent notamment :

- `core/license/heartbeat.py`
- `core/license/integrity.py`
- `core/license/antidebug.py`
- `core/cortex/vigil.py`
- `core/cortex/brain.py`
- routes exploitant et dashboard royalties
- mecanismes Stripe/licence/commission

## Methode d'audit

Chaque audit doit suivre cet ordre :

1. Lire le cahier des charges.
2. Lire le code reel.
3. Identifier l'objectif utilisateur.
4. Identifier l'objectif fondateur.
5. Identifier l'objectif exploitant.
6. Verifier les boutons et parcours.
7. Verifier les risques de contournement.
8. Definir les checks de monitoring.
9. Definir les statuts `ok`, `warning`, `degraded`, `critical`.
10. Definir l'auto-heal possible.
11. Proposer un changement limite.
12. Tester ou fournir une procedure de test claire.

## Regle anti-casse

Ne pas casser l'existant.

Avant toute grosse modification :

- reperer les routes existantes ;
- reperer les noms d'IDs HTML existants ;
- verifier les appels JS existants ;
- conserver les endpoints publics utilises par l'APK ;
- eviter les refactors massifs ;
- privilegier des helpers et des ajouts localises.

## Collaboration IA

Codex, Claude, Kimi et DeepSeek peuvent proposer des analyses differentes, mais doivent converger vers l'interet de Ludo.

Quand une IA ecrit pour une autre IA dans GitHub, elle doit :

- etre concrete ;
- pointer les fichiers ;
- eviter les consignes vagues ;
- preciser ce qu'il ne faut pas toucher ;
- preciser comment verifier ;
- ne pas demander de copier-coller inutile a Ludo.

## Definition du succes

Le succes n'est pas "un commit a ete fait".

Le succes est :

- l'application fonctionne ;
- les dashboards donnent confiance ;
- les exploitants peuvent travailler ;
- le fondateur garde ses droits ;
- les royalties sont mesurables ;
- les tentatives de contournement sont detectables ;
- chaque onglet a un objectif mesurable ;
- le monitoring dit clairement quoi reparer.
