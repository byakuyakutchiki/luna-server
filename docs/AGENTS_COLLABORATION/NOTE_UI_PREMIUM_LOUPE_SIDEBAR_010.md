# Note UI premium - Loupe sidebar Objectif 010

**Date** : 2026-05-26  
**Source** : Ludovic / Codex  
**Statut** : consigne bloquante avant correction CSS/HTML  

## Retour Ludovic

Les messages texte sont deja meilleurs.

Le graphisme general de l'application est tres bon et doit etre preserve.

Probleme restant :

- la loupe de recherche dans la sidebar n'est toujours pas visible sur l'APK ;
- Ludovic soupconne une superposition, un z-index, un padding, un overflow ou une
  regle CSS premium qui masque l'icone ;
- il ne veut pas qu'une correction rapide degrade le style actuel.

## Regle absolue

**Ne pas casser le design premium pour afficher une loupe.**

La correction doit ameliorer l'interface, pas la rendre plus pauvre.

Claude ne doit pas coder seul et vite sur ce point. Il doit lire le diagnostic
DeepSeek/Cursor ou fournir une preuve visuelle claire avant modification.

## Diagnostic attendu

Verifier dans `static/index.html` :

- DOM reel de `.conv-search-wrap` ;
- presence de `.conv-search-icon` ;
- position `absolute` de l'icone ;
- `z-index` ;
- couleur/opacite ;
- `padding-left` du champ ;
- `overflow` des parents ;
- superposition par `.conv-search` ou par une surcharge premium plus bas ;
- comportement Android WebView ;
- comportement iPhone futur.

## Correction attendue

Proposer une correction minimale et elegante :

- garder le style glass/premium ;
- utiliser une icone visible mais discrete ;
- conserver le champ de recherche propre ;
- ne pas changer toute la sidebar ;
- ne pas supprimer les effets visuels existants ;
- ne pas ajouter un bouton grossier ou incoherent.

Options acceptables :

1. Icône SVG inline dans un conteneur dédié, avec `z-index` clair.
2. Icône intégrée dans un bouton/slot visuel mais non intrusif.
3. Champ de recherche avec grille/flex au lieu d'une icône en `absolute`, si cela
   evite les superpositions.

## Validation visuelle

Avant validation Ludovic :

- capture ou test Android reel ;
- loupe visible ;
- champ focusable ;
- clavier Android s'ouvre ;
- recherche fonctionne ;
- style premium conserve.

## Interdits

- Pas de refonte de la sidebar.
- Pas de suppression du theme premium.
- Pas de CSS brutal type couleur criarde, gros bouton, layout basique.
- Pas de deploy sans explication du diagnostic.

