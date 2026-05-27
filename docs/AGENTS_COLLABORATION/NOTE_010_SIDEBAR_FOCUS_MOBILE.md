# Note Objectif 010 - Sidebar historique en mode focus mobile

**Date** : 2026-05-26  
**Source** : Ludovic / Codex  
**Statut** : consigne UX avant correction UI  

## Retour Ludovic

La sidebar qui se deploie pour afficher l'historique est une bonne idee.

Probleme restant sur telephone :

- quand la sidebar est ouverte, les barres du haut restent visibles ;
- on voit encore `Compagnon / Secretaire`, `Chat / Services`, le header Luna, etc. ;
- il y a trop d'affichages simultanes ;
- l'utilisateur ne sait plus ou regarder.

## Attendu produit

Sur mobile, quand l'utilisateur ouvre la sidebar :

```text
Sidebar ouverte = mode focus historique.
```

L'interface principale doit se calmer.

Les elements suivants doivent etre masques, desactives ou visuellement passes
derriere l'overlay pendant que la sidebar est ouverte :

- header Luna ;
- mode switcher `Compagnon / Secretaire` ;
- barre des onglets `Chat / Services / ...` ;
- elements interactifs du chat derriere.

Quand la sidebar se ferme, tout revient exactement comme avant.

## Regle UI

Il ne peut pas y avoir tous les affichages en meme temps.

L'historique doit prendre le focus, comme un panneau de navigation clair.

## Contraintes

- Ne pas casser le design premium.
- Ne pas refondre toute la page.
- Ne pas changer le systeme de conversations.
- Ne pas casser desktop/tablette.
- Correction mobile d'abord.
- Compatible Android WebView maintenant, iPhone plus tard.

## Solutions possibles

### Option A - Classe `sidebar-open`

Au moment ou la sidebar s'ouvre, ajouter une classe sur `body` :

```js
document.body.classList.add("sidebar-open");
```

Puis la retirer a la fermeture :

```js
document.body.classList.remove("sidebar-open");
```

CSS mobile :

```css
@media (max-width: 768px) {
  body.sidebar-open .header,
  body.sidebar-open .mode-switcher,
  body.sidebar-open .tabs {
    opacity: 0;
    pointer-events: none;
  }
}
```

### Option B - Overlay plus couvrant

Donner a la sidebar et a son overlay un `z-index` superieur au header, au mode
switcher et aux tabs, pour que l'historique passe visuellement au-dessus.

### Option C - Plein ecran mobile

Sur tres petit ecran, la sidebar peut prendre presque toute la largeur, avec son
propre header `Conversations` + bouton fermer.

## Recommandation Codex

Commencer par Option A + z-index propre :

- simple ;
- reversible ;
- ne touche pas a l'architecture ;
- respecte le design actuel ;
- evite d'avoir tous les affichages en meme temps.

## Validation Ludovic

Test telephone :

1. Ouvrir l'APK.
2. Ouvrir la sidebar.
3. Verifier que l'historique prend le focus.
4. Verifier que les barres `Compagnon/Secretaire` et `Chat/Services` ne restent
   pas visuellement en concurrence.
5. Fermer la sidebar.
6. Verifier que l'app revient normalement.

