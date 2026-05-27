# Cursor - Mission sidebar focus mobile Objectif 010

**Date** : 2026-05-26  
**Role** : UI mobile / finition premium  

## Mission

Auditer et proposer la correction minimale pour que la sidebar historique prenne
le focus sur mobile.

Lire :

```text
docs/AGENTS_COLLABORATION/NOTE_010_SIDEBAR_FOCUS_MOBILE.md
```

## Probleme a confirmer

Sur Android, quand la sidebar est ouverte, les barres du haut restent visibles :

- header Luna ;
- `Compagnon / Secretaire` ;
- `Chat / Services / ...`.

Cela surcharge l'ecran.

## Livrable attendu

```text
docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_SIDEBAR_FOCUS_010.md
```

Contenu :

- cause visuelle ;
- z-index actuel des elements ;
- proposition CSS/JS minimale ;
- impact Android/iPhone ;
- risque de regression.

## Regle

Preserver le style premium. La sidebar doit etre plus claire, pas plus pauvre.

