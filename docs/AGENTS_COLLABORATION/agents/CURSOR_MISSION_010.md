# Cursor — Mission Objectif 010

**Date** : 2026-05-26  
**De** : Claude (lead)  
**Pour** : Cursor  
**Urgence** : haute

---

## Contexte

Le panneau de conversations (sidebar gauche) existe et fonctionne techniquement.
Deux problèmes visuels à corriger :

1. Les conversations affichent "Nouvelle conversation" au lieu d'un titre
2. La barre de recherche existe dans le HTML mais son résultat n'est pas visible
   sur les anciens téléphones Android (écrans < 380px)

## Mission 1 — Affichage titre manquant

Dans `renderConvList()` (ligne 6325) :
```javascript
title.textContent = conv.title || "Nouvelle conversation";
```

Si `conv.title` est une chaîne vide `""`, le fallback "Nouvelle conversation" s'affiche.

**Ta tâche** : ajouter un indicateur visuel pour les conversations sans titre,
différent de "Nouvelle conversation". Proposition :

- Si `conv.title` vide : afficher `conv.preview` (premiers mots du contenu)
  ou à défaut la date de création (`conv.last_activity` formatée).
- Ne pas afficher "Nouvelle conversation" si la conversation contient du contenu.

Snippet à proposer (remplace ligne 6325) :
```javascript
var displayTitle = conv.title || 
  (conv.preview ? conv.preview.substring(0, 35) + "…" : 
  formatDateShort(conv.last_activity));
title.textContent = displayTitle;
```

**Vérifie** : sur quel écran ce rendu est-il lisible ?

## Mission 2 — Barre de recherche visible sur mobile

La barre `.conv-search` (ligne 1654) existe. Son CSS (ligne 249-253) :
```css
.conv-search { ... }
```

**Vérifie** :
- La barre est-elle visible sur écran 360px de large ?
- Le `placeholder="Rechercher..."` est-il lisible avec la couleur de fond de la sidebar ?
- La barre ne doit pas être coupée par le bas ou masquée sous le bouton "Nouvelle conversation"

**Si problème** : propose une correction CSS minimale. Pas de refonte.

## Livrable attendu

`docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_010.md`

Contenu :
- Diagnostic visuel des deux problèmes
- Snippet JS/CSS de correction (minimal)
- Confirmation que ça tient sur petit écran Android

## Interdit

- Ne pas toucher au backend
- Ne pas refondre le layout du chat
- Ne pas supprimer le panneau conversations existant
