# Codex — Test URL production visio Iris — Objectif 017

## URL testee

`https://luna-beta-674304336025.europe-west1.run.app/`

`https://luna-beta-674304336025.europe-west1.run.app/simli?duration=1&_v=31`

## Verification Codex depuis Windows

La racine repond :

`HTTP 200`

La page `/simli` repond :

`HTTP 200`

## Etat production observe

La page servie en production contient encore :

- `>Iris voit<`

La page servie ne contient pas encore :

- `Vision en attente`
- `#tavusFrame::after`

Conclusion :

La production testee par Ludovic n'a pas encore la totalite du patch UI/vision `e6f0bc3`.

Le frontend contient en revanche deja :

- `mobile-web-app-capable`
- le log detaille `vad_stt_err` avec corps serveur.

## Implication

Si Ludovic reteste avant rebuild/deploy complet Cloud Run, il peut encore voir :

- le badge incoherent `Iris voit` ;
- les controles bas Daily/Simli visibles ;
- le 500 `python-multipart` si l'image Cloud Run n'a pas ete reconstruite.

## Bug raccrocher

Retour Ludovic :

> Il faut appuyer plusieurs fois sur `Raccrocher`, ce n'est pas pris en compte dès la première fois.

Cause probable code :

- le bouton demandait une confirmation native `confirm(...)` ;
- `doHangup()` attendait jusqu'a 5 secondes la generation auto des notes avant de naviguer ;
- aucun etat visuel ne disait que la fermeture etait en cours.

Patch Codex :

- clic direct sur `Raccrocher`, sans confirmation supplementaire ;
- bouton desactive immediatement ;
- texte `Fermeture…` ;
- cache la barre actions + PTT ;
- timeout auto-save notes reduit de 5 secondes a 1.2 seconde ;
- z-index du bouton augmente pour rester au-dessus des couches video.

## Test attendu apres deploy

1. Ouvrir une visio Iris.
2. Cliquer une fois sur `Raccrocher`.
3. Le bouton doit passer a `Fermeture…`.
4. Retour accueil attendu en environ 1 a 2 secondes.

## Statut

Deploy requis avant nouveau verdict terrain.
