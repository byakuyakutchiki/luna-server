# Codex — Scope Claude Team Workspace immersif — Objectif 035

Date : 2026-06-07
Agent : Codex
Destinataire : Claude
Type : scope implementation

## Message important

Claude, ne code pas une visio classique.
Ne code pas un dashboard plat.
Ne code pas un chatbot avec un panneau.

Le produit attendu est :

```text
une salle de travail immersive avec table centrale, sieges, tableau collaboratif et Iris comme synthese appelee au bon moment.
```

## Objectif V1

Livrer une premiere surface visuelle convaincante :

- table ou scene centrale ;
- tableau virtuel au centre ;
- sieges participants autour ;
- spectateurs separes ;
- roles/droits visibles ;
- admin controls ;
- mission brief visible ;
- bouton Avis Iris conditionnel ;
- aucune action sensible reelle.

## Graphisme attendu

Important : Ludovic insiste sur le graphisme.

Le rendu doit etre :

- high-tech ;
- immersif ;
- premium ;
- lisible ;
- dynamique ;
- coherent avec l'univers Iris/Luna ;
- pas fade ;
- pas beige/dash admin ;
- pas empilement de cartes generiques ;
- pas interface de formulaire brute.

La premiere impression doit etre :

```text
j'entre dans une salle de commandement collaborative
```

## Layout recommande

```text
┌──────────────────────────────────────────────┐
│ Titre session / Mission Brief / statut       │
├──────────────────────────────────────────────┤
│                                              │
│        sieges participants autour            │
│                                              │
│          ┌────────────────────┐              │
│          │ TABLEAU IMMERSIF   │              │
│          │ idees/doc/graph    │              │
│          │ mind map/synthese  │              │
│          └────────────────────┘              │
│                                              │
│        sieges participants autour            │
│                                              │
├───────────────┬──────────────────────────────┤
│ Spectateurs   │ Admin / sources / Avis Iris  │
└───────────────┴──────────────────────────────┘
```

## Etats participants

Chaque personne doit pouvoir afficher :

- avatar/video placeholder ;
- nom ;
- role ;
- micro ;
- camera ;
- main levee ;
- statut edition/ecoute/parle ;
- badge owner/admin/participant/spectateur.

## Roles

### Owner/Admin

Peut :

- donner la parole ;
- muter ;
- reactiver ;
- couper camera ;
- promouvoir spectateur ;
- retirer participant ;
- bannir visuellement ;
- lancer Avis Iris ;
- valider actions sensibles.

### Participant

Peut :

- parler ;
- modifier tableau si droit edition ;
- ajouter source ;
- ajouter idee ;
- voter/commenter.

### Spectateur

Peut :

- regarder ;
- ecouter ;
- demander la parole ;
- etre promu.

## Iris / IQ

Ne pas mettre Iris en conversation libre au centre.

Iris est :

- presence de synthese ;
- bouton “Avis Iris” ;
- analyse a partir du brief et des sources ;
- mode intervention.

Quand Avis Iris est lance :

- afficher `iris_opinion_requested` ;
- verrouiller visuellement le tableau ;
- afficher base de synthese ;
- montrer “Iris analyse les elements fournis” ;
- ne pas appeler SMS/email/appel.

## Target Cells V1

### TC-035-01

Page chargee -> logs :

```text
team_workspace_loaded
```

### TC-035-02

Brief incomplet -> bouton Avis Iris grise.

### TC-035-03

Brief + source -> bouton Avis Iris actif.

### TC-035-04

Spectateur demande parole -> etat “main levee”.

### TC-035-05

Admin mute un participant -> etat UI change, aucune action externe.

### TC-035-06

Mind map minimale visible :

- 3 idees ;
- 2 liens ;
- 1 source.

### TC-035-07

Avis Iris -> mode intervention :

- tableau verrouille ;
- participants en ecoute ;
- panneau synthese visible.

## Interdictions

- Pas de deploy sans validation.
- Pas de SMS/email/appel/paiement/reservation.
- Pas de suppression reelle.
- Pas de secrets.
- Pas de refonte massive hors surface Team Workspace.
- Pas de promesse "fonctionnel" sans screenshot/test F12.

## Livrables attendus

- code V1 ;
- doc agent `CLAUDE_IMPL_TEAM_WORKSPACE_035.md` ;
- logs F12 attendus ;
- screenshots si possible ;
- aucun deploiement avant accord Ludovic.

