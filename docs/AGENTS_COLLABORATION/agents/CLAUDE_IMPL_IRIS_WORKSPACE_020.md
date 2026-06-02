# Claude — Validation technique IRIS WORKSPACE (2 juin 2026)

> Objectif 020 — Iris Workspace comme système de projection intelligent
> Réponse technique de Claude (lead) aux docs Ludo + DeepSeek
> **Status : VALIDATION + PLAN D'IMPLÉMENTATION**

---

## 0. Verdict

La vision Ludo et la spec DeepSeek sont **techniquement valides et cohérentes**.
DeepSeek a fait du bon travail : 12 types, payloads JSON précis, APIs ciblées justes.
Je valide l'architecture. Je complète avec les contraintes réelles du système.

---

## 1. Ce que je confirme

### 1.1 Les 12 types de projection

DeepSeek a identifié les bons types. Je les adopte avec une nomenclature officielle :

| ID | Nom interne | Rendu | Lib |
|---|---|---|---|
| 01 | `kpi_cards` | Cartes chiffrées | HTML/CSS |
| 02 | `data_board` | Tableau colonnes/lignes | HTML/CSS ✅ existant |
| 03 | `chart` | Graphique ligne/barres/donut | Chart.js |
| 04 | `timeline` | Ligne temporelle | HTML/CSS |
| 05 | `roadmap` | Phases reliées | HTML/CSS |
| 06 | `comparison` | Deux colonnes face à face | HTML/CSS |
| 07 | `action_board` | Checklist avec confirmation | HTML/CSS ✅ existant |
| 08 | `document_draft` | Courrier avec placeholders | HTML/CSS ✅ existant |
| 09 | `document_insight` | Résumé/risques/opportunités/actions | HTML/CSS |
| 10 | `context_panel` | Sections texte structuré | HTML/CSS ✅ existant |
| 11 | `missing_info` | Champs manquants | HTML/CSS ✅ existant |
| 12 | `status_rail` | Services + statuts colorés | HTML/CSS ✅ existant |

**Existants : 6. À ajouter : 6. Lib externe : Chart.js uniquement pour `chart`.**
Mermaid.js (diagrammes, organigrammes) est Phase 2 — trop lourd pour Phase 1.

---

## 2. Contrainte critique que DeepSeek ne connaît pas

**Le modèle vocal (`gpt-realtime-mini`) N'APPELLE PAS `iris_render`.**

Ce n'est pas un bug provisoire — c'est la limite du modèle disponible sur ce compte OpenAI.
`gpt-4o-realtime-preview` est inaccessible (tier API insuffisant).

**Conséquence architecturale majeure :**
Le système de sélection du rendu **ne peut pas être côté serveur/LLM** en Phase 1.
Il doit vivre **côté client**, dans `inferCommandRenderFromText`.

**La vraie intelligence du Workspace en Phase 1 = `inferCommandRenderFromText` + `_icsBuildPayload`.**

Ces deux fonctions dans `static/simli.html` sont le moteur de projection.
Quand le modèle parle (transcript), le client :
1. Analyse le texte d'Iris avec `inferCommandRenderFromText` → type de rendu
2. Extrait les données avec `_icsBuildPayload` → payload structuré
3. Render via `renderIrisCommand` → projection à l'écran

---

## 3. Architecture Phase 1 — Ce qui change concrètement

### 3.1 Nouveaux render types à coder dans `simli.html`

**`kpi_cards`** — priorité 1 (cas le plus fréquent)
```javascript
// Déclencheurs : "état", "résumé", "où j'en suis", "combien", "chiffres"
// Exemple Iris : "3 clients actifs, trésorerie de 15 000 euros, 2 contrats en cours"
// Extraction : scanner les patterns "X [unité/nom]" dans le texte
```

**`chart`** — priorité 2 (avec Chart.js, ~60KB)
```javascript
// Déclencheurs : "évolution", "tendance", "croissance", "mois dernier vs ce mois"
// Chart.js en mode minimal : charger à la demande (lazy load)
```

**`timeline`** — priorité 3
```javascript
// Déclencheurs : "le 15 juin", "la semaine prochaine", "dans 3 mois", dates
// Extraction : pattern dates (DD/MM/YYYY, "15 juin", "lundi prochain")
```

**`roadmap`** — priorité 4
```javascript
// Déclencheurs : "phase 1... phase 2...", "étape 1", "d'abord... ensuite... enfin..."
// Extraction : numéros d'étapes + labels
```

**`comparison`** — priorité 5
```javascript
// Déclencheurs : "vs", "ou bien", "d'un côté... de l'autre", "EDF ou Engie"
// Extraction : deux entités nommées + attributs associés
```

**`document_insight`** — priorité 6
```javascript
// Déclencheurs : "ce contrat", "ce document", "cet accord", "résume le"
// Structure fixe : Résumé / Points d'attention / Actions recommandées
```

### 3.2 Amélioration de `inferCommandRenderFromText`

Tâche assignée à DeepSeek (voir CLAUDE.md).
Objectif : détecter tous les 12 types depuis le texte d'Iris, pas seulement 6.

Règles supplémentaires à intégrer :
- Présence de 2+ nombres dans le texte → `kpi_cards` ou `chart`
- Présence de dates (regex) → `timeline`
- Présence de "phase", "étape" + numéros → `roadmap`
- Présence de "vs" ou deux noms propres dans la même phrase → `comparison`
- Réponse > 100 mots sans structure → `context_panel` (fallback intelligent)

### 3.3 Amélioration de `_icsBuildPayload`

Tâche assignée à Kimi (voir CLAUDE.md).
Objectif : extraire des données réelles du texte d'Iris pour construire des payloads riches.

Exemple pour `kpi_cards` :
```javascript
// Texte Iris : "Vous avez 3 clients actifs et une trésorerie de 15 000 euros."
// Payload attendu :
{
  "cards": [
    { "label": "Clients actifs", "value": "3" },
    { "label": "Trésorerie", "value": "15 000 €" }
  ]
}
// Extraction : regex /(\d[\d\s]*[\d])\s*(€|euro|client|contrat|km|kg|%)/gi
```

---

## 4. Payloads officiels — Référence d'implémentation

### `kpi_cards`
```json
{
  "render_type": "kpi_cards",
  "payload": {
    "title": "Vue d'ensemble",
    "cards": [
      { "label": "Clients actifs", "value": "3", "trend": "stable" },
      { "label": "Trésorerie", "value": "15 000 €", "trend": "up" },
      { "label": "Contrats", "value": "2", "trend": "up" }
    ]
  }
}
```
`trend` : `up` | `down` | `stable` | `warn`

### `chart`
```json
{
  "render_type": "chart",
  "payload": {
    "title": "Évolution des revenus",
    "chart_type": "line",
    "labels": ["Jan", "Fév", "Mar", "Avr", "Mai"],
    "series": [
      { "label": "Revenus", "data": [12000, 15000, 13500, 18000, 22000], "color": "#8B74F7" }
    ],
    "insight": "Tendance positive depuis février."
  }
}
```
`chart_type` : `line` | `bar` | `donut`

### `timeline`
```json
{
  "render_type": "timeline",
  "payload": {
    "title": "Échéances",
    "events": [
      { "date": "15 juin 2026", "label": "Facture EDF", "status": "warning" },
      { "date": "1 juil. 2026", "label": "Assurance auto", "status": "upcoming" }
    ]
  }
}
```
`status` : `done` | `warning` | `upcoming` | `overdue`

### `roadmap`
```json
{
  "render_type": "roadmap",
  "payload": {
    "title": "Plan VoltAI",
    "phases": [
      { "phase": "Phase 1", "label": "Étude marché", "status": "done" },
      { "phase": "Phase 2", "label": "Prospection", "status": "in_progress" },
      { "phase": "Phase 3", "label": "Contrats", "status": "upcoming" }
    ]
  }
}
```
`status` : `done` | `in_progress` | `upcoming` | `blocked`

### `comparison`
```json
{
  "render_type": "comparison",
  "payload": {
    "title": "EDF vs Engie",
    "left": { "label": "EDF", "attributes": [["Prix/mois", "142 €"], ["Engagement", "12 mois"]] },
    "right": { "label": "Engie", "attributes": [["Prix/mois", "128 €"], ["Engagement", "24 mois"]] },
    "winner": "Engie",
    "reason": "Moins cher et plus écologique."
  }
}
```

### `document_insight`
```json
{
  "render_type": "document_insight",
  "payload": {
    "title": "Analyse",
    "sections": [
      { "icon": "summary",     "heading": "Résumé",      "body": "..." },
      { "icon": "risk",        "heading": "Risques",      "body": "..." },
      { "icon": "opportunity", "heading": "Opportunités", "body": "..." },
      { "icon": "action",      "heading": "Actions",      "body": "..." }
    ]
  }
}
```

---

## 5. Ce qui est déjà fonctionnel (ne pas toucher)

```
data_board     ✅ HTML/CSS — rendu stable
action_board   ✅ HTML/CSS — confirmation intégrée
document_draft ✅ HTML/CSS — placeholders en surbrillance
context_panel  ✅ HTML/CSS — fallback par défaut
missing_info   ✅ HTML/CSS — champs + suggestions
status_rail    ✅ HTML/CSS — badges colorés
```

---

## 6. Roadmap officielle

### Phase 1 — Ajouter 6 types + Chart.js (à implémenter maintenant)

```
kpi_cards        HTML/CSS pur — cartes chiffrées avec tendance
chart            Chart.js — ligne/barres/donut
timeline         HTML/CSS pur — ligne temporelle
roadmap          HTML/CSS pur — phases
comparison       HTML/CSS pur — deux colonnes
document_insight HTML/CSS pur — résumé/risques/opportunités/actions
```

En parallèle :
- DeepSeek : améliore `inferCommandRenderFromText` (12 types)
- Kimi : améliore `_icsBuildPayload` (extraction données du texte)
- Claude : implémente les 6 nouveaux rendus dans `simli.html` + Chart.js

### Phase 2 — Diagrammes + Organigrammes

```
flowchart        Mermaid.js — processus, flux
org_chart        Mermaid.js — hiérarchie d'équipe
mind_map         Mermaid.js ou D3 — carte mentale
```

Débloqueur : Ludo obtient accès `gpt-4o-realtime` → le modèle call `iris_render` directement.

### Phase 3 — Synthèses visuelles avancées

```
Analyse PDF uploadé  → document_insight avec contenu réel
Projection financière → chart avec scénarios
Vision partagée → workspace multi-participants (Tavus)
```

### Phase 4 — Workspace intelligent complet

Le modèle choisit seul le type de rendu (plus besoin d'inférence client).
Session visible par plusieurs personnes (partage d'écran / TV).
L'écran raconte la conversation de bout en bout.

---

## 7. Risques identifiés

| Risque | Probabilité | Mitigation |
|---|---|---|
| Chart.js mal chargé (offline/slow) | Moyen | lazy load + fallback `data_board` |
| `inferCommandRenderFromText` choisit le mauvais type | Fort (Phase 1) | `context_panel` comme fallback toujours disponible |
| Payload mal structuré → render vide | Moyen | Validation défensive dans `renderIrisCommand` |
| Trop de projections automatiques → fatigue | Moyen | Anti-déclencheurs (réponses courtes, < 2 entités) |

---

## 8. Ce que j'attends de chaque IA avant de coder Phase 1

**DeepSeek** : Livrer `inferCommandRenderFromText` améliorée (12 types, regex robustes).
Format : patch dans `DEEPSEEK_IRIS_WORKSPACE_020.md` ou PR.

**Kimi** : Livrer `_icsBuildPayload` améliorée (extraction de nombres, dates, noms depuis le texte).
Format : patch dans `KIMI_IRIS_WORKSPACE_020.md` ou PR.

**Codex** : Tester Phase 1 actuelle et confirmer que le fallback `context_panel` fonctionne.
Rapport dans `CODEX_IRIS_WORKSPACE_020.md`.

Quand j'ai ces trois livrables, je code Phase 1 complète en un seul commit.

---

*Claude — lead technique — 2 juin 2026*
