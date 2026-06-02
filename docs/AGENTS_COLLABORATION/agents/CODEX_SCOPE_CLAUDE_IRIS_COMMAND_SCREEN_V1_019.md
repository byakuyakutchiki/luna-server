# Codex — Scope Claude Iris Command Screen V1 — Objectif 019

Date : 2026-06-02  
Agent : Codex  
Type : synthèse / ordre de code pour Claude  
Niveau : 2 — visible, déploiement seulement après validation Ludovic  

## Sources lues

- `CODEX_RECADRAGE_IRIS_COMMAND_SCREEN_019.md`
- `DEEPSEEK_DIRECTION_ARTISTIQUE_IRIS_COMMAND_SCREEN_019.md`
- `DEEPSEEK_CONTRAT_TECHNIQUE_IRIS_COMMAND_SCREEN_019.md`
- `KIMI_UX_IRIS_COMMAND_SCREEN_019.md`

## Décision Codex

Claude peut coder une **V1 visuelle garantie**, mais pas une usine à gaz.

Le but immédiat n'est pas de finaliser tous les documents, PDF, sauvegardes et actions réelles. Le but est de corriger l'échec produit constaté :

> Quand Iris dit qu'elle affiche ou prépare quelque chose, un écran visuel réel doit apparaître.

## Scope V1 à coder

### Fichier principal

Priorité : modifier `static/simli.html`, car c'est l'écran Iris Audio actif aujourd'hui.

Ne pas créer une nouvelle route isolée qui ne serait pas visible dans le parcours réel, sauf si elle est utilisée par `/simli`.

### 1. Remplacer le Workbench texte par Iris Command Screen

Créer ou renommer les blocs existants :

- `#afWorkbench` -> concept `#irisCommandScreen` ou classe équivalente ;
- header : `Iris Command Screen` ;
- Status Rail ;
- zone de rendu principal ;
- Context Panel ;
- Missing Info Panel ;
- actions locales.

### 2. Implémenter les 6 render_type côté frontend

Fonction obligatoire :

```javascript
renderIrisCommand(payload)
```

Elle doit gérer :

- `data_board`
- `document_draft`
- `action_board`
- `context_panel`
- `missing_info`
- `status_rail`

Chaque type doit produire du HTML visuel, pas du texte brut.

### 3. Garantir un rendu immédiat même sans backend parfait

V1 doit inclure un routeur local d'intention :

```javascript
inferCommandRenderFromText(text)
```

Exemples :

- "affiche un tableau" -> `data_board`
- "prépare un courrier" -> `document_draft`
- "fais une checklist" -> `action_board`
- "explique / analyse" -> `context_panel`
- demande incomplète -> `missing_info`
- "état / services / diagnostic" -> `status_rail`

Raison : Ludovic ne doit plus voir Iris dire "je ne peux pas afficher" si le frontend sait afficher.

### 4. Accepter un futur message serveur `render`

Dans le handler WebSocket existant, ajouter :

```javascript
if (data.type === 'render') renderIrisCommand(data)
```

Cela prépare le contrat DeepSeek sans bloquer la V1.

### 5. Prompt Iris

Dans `luna_web.py`, compléter le prompt Iris :

- interdiction de dire "je ne peux pas afficher directement" ;
- si tableau/document/checklist demandé, dire brièvement que l'écran de travail s'ouvre ;
- demander les informations manquantes si besoin ;
- ne jamais prétendre exécuter une action réelle ;
- action sensible = validation requise.

Important : ne pas forcer Iris à parler longtemps. Le visuel doit faire le travail.

### 6. Design

Respecter Kimi :

- noir OLED ;
- verre fumé ;
- violet Iris ;
- pas vert Simli ;
- pas markdown visible ;
- pas emojis dans Command Screen ;
- animations sobres ;
- mobile sans superposition ;
- Status Rail toujours visible.

## Livrables attendus de Claude

1. Patch code.
2. Rapport :
   `docs/AGENTS_COLLABORATION/agents/CLAUDE_IMPL_IRIS_COMMAND_SCREEN_019.md`
3. Message AGENT_CHANNEL court.
4. Pas de déploiement sans feu vert Ludovic.

## Tests obligatoires avant de dire "c'est prêt"

Claude doit tester localement ou en prévisualisation :

1. `affiche un tableau avec type, montant, date, statut`
   - attendu : Data Board HTML visuel, pas markdown.
2. `prépare un courrier pour un exploitant`
   - attendu : Document Draft visuel.
3. `fais une checklist pour finaliser Iris`
   - attendu : Action Board avec cartes / cases.
4. `envoie un SMS`
   - attendu : Action Board validation requise, aucune action envoyée.
5. Mobile :
   - pas de bouton superposé ;
   - panneau lisible ;
   - Status Rail visible.

## Ce qui est interdit à Claude

- Dire "c'est bon" sans capture ou preuve visuelle.
- Livrer un tableau markdown.
- Recoder un panneau texte générique.
- Ajouter une action réelle.
- Déployer sans validation Ludovic.
- Ignorer Kimi ou DeepSeek.

## Position finale

Claude a maintenant assez d'éléments pour coder une V1 utile.

Codex tranche : V1 = frontend visuel robuste + prompt corrigé + support futur `render`.

Le backend JSON complet peut être renforcé en V2, mais la V1 doit déjà afficher visuellement les demandes principales.
