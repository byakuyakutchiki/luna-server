# Codex — Patch prerogatives Iris Render — Objectif 021

Date : 2026-06-03
Agent : Codex
Type : correctif contrat outil / conscience Command Screen

## Probleme terrain

Ludovic demande a Iris d'utiliser son tableau pour produire un graphique.

Comportement observe :
- Iris parle comme si elle n'avait pas la main sur son propre ecran ;
- elle peut dire qu'elle ne peut pas afficher ou manipuler un tableau/graphique ;
- le Command Screen existe, mais Iris ne se comporte pas comme une operatrice qui pilote son workspace.

## Cause identifiee

Le frontend `static/simli.html` sait deja afficher de nombreux rendus :
- `chart`
- `kpi_cards`
- `timeline`
- `roadmap`
- `comparison`
- `document_insight`
- `kanban_board`
- `contact_board`
- `map_board`
- `decision_board`
- `budget_board`
- `meeting_board`
- `media_board`
- `form_board`

Mais le tool vocal `iris_render` dans `integrations/openai/realtime_bridge.py` ne declarait que 6 `render_type`.

Donc Iris n'avait pas officiellement le droit, dans son contrat OpenAI Realtime, de demander :

```json
{"render_type":"chart"}
```

Le prompt serveur `_IRIS_SYSTEM` dans `luna_web.py` disait aussi "tableaux", mais pas assez clairement :
- qu'Iris pilote son propre Command Screen ;
- qu'un graphique depuis tableau/chiffres doit appeler `iris_render(render_type="chart")` ;
- qu'elle ne doit jamais dire qu'elle ne peut pas utiliser son tableau.

## Patch applique

### 1. `integrations/openai/realtime_bridge.py`

Le tool `iris_render` declare maintenant les 20 types supportes par le frontend :

- `data_board`
- `document_draft`
- `action_board`
- `context_panel`
- `missing_info`
- `status_rail`
- `kpi_cards`
- `chart`
- `timeline`
- `roadmap`
- `comparison`
- `document_insight`
- `kanban_board`
- `contact_board`
- `map_board`
- `decision_board`
- `budget_board`
- `meeting_board`
- `media_board`
- `form_board`

La description dit explicitement :
- Iris a la main sur son ecran ;
- si l'utilisateur demande un graphique depuis tableau/chiffres, utiliser `chart` ;
- ne jamais dire qu'elle ne peut pas utiliser son tableau.

### 2. `luna_web.py`

Le system prompt Iris precise maintenant :
- elle peut preparer tableaux, graphiques, KPI, budgets, cartes, timelines, roadmaps et dossiers ;
- le Command Screen est son ecran de travail ;
- toute demande graphique/chiffree doit appeler `iris_render` avant parole ;
- la phrase "je ne peux pas utiliser mon tableau pour faire un graphique" est interdite.

## Target Cell

| Element | Valeur |
|---|---|
| Objectif | 021 — Iris Capability Gateway |
| Target exacte | Iris sait qu'elle pilote son Command Screen et peut transformer des donnees/tableaux en graphique |
| Capacite | `intent -> iris_render(chart) -> Command Screen chart -> parole breve` |
| Backend | `VOICE_TOOLS.iris_render` accepte `chart` |
| Frontend | `static/simli.html` rend deja `chart` via Chart.js |
| Garde-fou | Aucun acte sensible, rendu visuel seulement |
| Statut | code non prouve terrain |

## Tests attendus

1. Dire : "Iris, fais-moi un tableau simple avec trois chiffres, puis transforme-le en graphique."
2. Attendu :
   - Iris ne s'excuse pas ;
   - elle appelle ou declenche `iris_render` ;
   - le Command Screen affiche `Graphique` ;
   - elle parle en une phrase courte, sans lire le tableau.

3. Dire : "Utilise ton tableau pour faire un graphique de mon business plan."
4. Attendu :
   - si les chiffres manquent, Iris affiche `missing_info` ou un `chart` provisoire avec champs manquants ;
   - elle pose une seule question utile ;
   - elle ne dit jamais qu'elle ne peut pas.

## Mission Kimi

Auditer le rendu reel apres deploiement :
- le graphique est-il beau, lisible, premium ?
- le panneau ressemble-t-il a un ecran de travail futuriste, pas a un chatbot ?
- le mode clair/sombre est-il coherent ?
- le texte visible est-il minimal ?

## Mission DeepSeek

Contre-auditer le contrat technique :
- verifier que les 20 `render_type` exposes par le tool correspondent aux handlers frontend ;
- verifier que `web_voice_bridge.py` transmet bien `render_type` sans filtrage ;
- proposer les 5 phrases de test qui prouvent `chart`, `kpi_cards`, `budget_board`, `decision_board`, `document_draft`.

## Verdict Codex

Ce patch ne suffit pas a livrer la capacite comme "atteinte".

Il transforme le statut de :

`partiel — Iris ne connait pas ses prerogatives`

vers :

`code non prouve — contrat corrige, test terrain requis`
