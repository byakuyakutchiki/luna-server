# Cursor - Mission UI premium loupe sidebar Objectif 010

**Date** : 2026-05-26  
**Priorite** : haute  
**Role** : deuxieme regard UI mobile / design premium  

## Mission

Auditer pourquoi la loupe de recherche de la sidebar n'apparait pas dans l'APK
Android alors que le code contient maintenant un element DOM `.conv-search-icon`.

Lire :

```text
docs/AGENTS_COLLABORATION/NOTE_UI_PREMIUM_LOUPE_SIDEBAR_010.md
```

## Ce que Cursor doit verifier

- superposition entre icone et input ;
- `z-index` ;
- opacite/couleur trop faible ;
- `overflow:hidden` dans les parents ;
- padding insuffisant ;
- conflits entre CSS de base et surcharge premium ;
- rendu Android WebView ;
- rendu futur iPhone.

## Livrable attendu

```text
docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_UI_LOUPE_010.md
```

Contenu :

- cause probable ;
- lignes concernees ;
- proposition CSS/HTML minimale ;
- risque de regression ;
- validation visuelle attendue.

## Regle

Preserver le style premium. Ne pas proposer une correction grossiere.

