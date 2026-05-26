# Claude - Consigne sidebar focus mobile Objectif 010

**Date** : 2026-05-26  
**Source** : Ludovic / Codex  

## Consigne

Ludovic valide l'idee de la sidebar historique, mais pas l'empilement visuel
actuel.

Quand la sidebar est ouverte sur mobile, les autres barres ne doivent pas rester
en concurrence visuelle.

## Avant de coder

Lire :

```text
docs/AGENTS_COLLABORATION/NOTE_010_SIDEBAR_FOCUS_MOBILE.md
```

Verifier :

- ouverture sidebar ;
- fermeture sidebar ;
- z-index ;
- overlay ;
- header ;
- mode-switcher ;
- tabs ;
- Android WebView ;
- desktop/tablette.

## Correction recommandee

Ajouter une classe `sidebar-open` sur `body` pendant l'ouverture de la sidebar,
et masquer/desactiver visuellement les barres du haut uniquement en mobile.

## Interdit

- Ne pas casser le style premium.
- Ne pas supprimer les barres.
- Ne pas refondre la navigation.
- Ne pas impacter desktop si ce n'est pas necessaire.

