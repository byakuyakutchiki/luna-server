# Codex — Fix source graphique Iris — Objectif 022

Date : 2026-06-03
Agent : Codex
Type : correctif bug terrain / Command Screen

## Retour terrain

Capture Ludovic :
- Command Screen brouillon ;
- Iris affiche un graphique vide ;
- le contexte du graphique contient une phrase d'accueil : "Bonjour et bienvenue..." ;
- Iris decrit un graphique imaginaire au lieu d'afficher un rendu utile.

## Cause identifiee

Le bug se joue dans `static/simli.html`.

### 1. Mauvaise source de texte

Quand Iris repond sans `iris_render` serveur, le fallback local analysait le texte d'Iris (`_icsIrisResponseText`) au lieu de la derniere demande utilisateur.

Effet :

```text
Demande utilisateur : "fais-moi un graphique"
Réponse Iris : "Bonjour et bienvenue..."
Fallback : construit le graphique depuis "Bonjour et bienvenue..."
```

Donc le panneau affichait :

```text
Graphique demandé : Bonjour et bienvenue...
```

### 2. Faux graphique par defaut

`_icsBuildPayload('chart')` fabriquait toujours :

```js
labels: ['Période 1', 'Période 2', 'Période 3']
data: [0, 0, 0]
```

Effet :
- graphique vide ;
- impression de faux rendu ;
- aucune vraie donnee projetee.

### 3. Bug latent

`inferCommandRenderFromText()` utilisait `sourceText` dans une condition `contact_board`, alors que cette variable n'existe pas dans cette fonction.

## Patch applique

Fichier : `static/simli.html`

1. Ajout `_icsLastUserRequestText` pour memoriser la derniere demande utilisateur.
2. `_afSendTextToIris()` met a jour cette demande avant envoi.
3. Le fallback render utilise la demande utilisateur comme source principale.
4. Si Iris parle sans demande utilisateur recente, le fallback ne rend plus un panneau depuis une salutation.
5. `_icsBuildPayload('chart')` extrait les nombres depuis la demande.
6. Si moins de 2 nombres sont trouves, Iris affiche `missing_info` au lieu d'un faux graphique.
7. `renderIrisCommand()` bloque aussi tout `chart` vide venant du serveur.
8. Correction `sourceText` -> `text` dans `inferCommandRenderFromText()`.

## Target Cell

| Element | Valeur |
|---|---|
| Objectif | 022 — Iris Real-Time Command Screen |
| Target exacte | Un graphique affiche de vraies donnees ou demande clairement les donnees manquantes |
| Capacite | demande utilisateur -> render_type chart/missing_info -> rendu utile |
| Backend | inchangé |
| Frontend | fallback + payload chart corriges |
| Garde-fou | aucun faux graphique `[0,0,0]` |
| Statut | code non prouve terrain |

## Tests attendus

### Test 1 — sans chiffres

Demande :

```text
Iris, fais-moi un graphique pour mon business plan.
```

Attendu :
- pas de faux graphique vide ;
- panneau `Infos manquantes` ou `Graphique à construire` ;
- demandes : donnees chiffrees, libelles/periodes, type de graphique.

### Test 2 — avec chiffres

Demande :

```text
Iris, fais un graphique avec janvier 1200, fevrier 1800, mars 2400.
```

Attendu :
- render `chart` ;
- labels Valeur 1/2/3 ou donnees equivalentes ;
- data `[1200, 1800, 2400]` ;
- pas de contexte "Bonjour et bienvenue".

### Test 3 — salutation Iris

Attendu :
- une salutation seule ne doit pas ouvrir de graphique ;
- aucun rendu base sur le texte d'accueil Iris.

## Mission Kimi

Auditer visuellement :
- le panneau est-il moins brouillon ?
- le bloc "infos manquantes" est-il lisible ?
- les actions Modifier/Copier/Telecharger ne dominent-elles pas trop l'ecran mobile ?

## Mission DeepSeek

Contre-auditer :
- verifier que le fallback local n'utilise plus le texte Iris comme source principale ;
- verifier que `chart` vide est bloque ;
- proposer extraction plus robuste labels + nombres si besoin.
