# Claude — Implémentation Iris Command Screen V1 — Objectif 019

Date : 2026-06-02
Agent : Claude
Commit : fc5466d
Statut : **implémenté, en attente validation Ludovic avant déploiement**

---

## Scope réalisé

Conforme à `CODEX_SCOPE_CLAUDE_IRIS_COMMAND_SCREEN_V1_019.md`.

### 1. CSS — Iris Command Screen

- Variables CSS DeepSeek + Kimi : `--ics-violet`, `--ics-cyan`, `--ics-amber`, `--ics-coral`, `--ics-green`, `--ics-bg`, `--ics-border`
- Panneau `.ics-panel` : verre fumé (`backdrop-filter: blur(40px) saturate(180%)`), bord 1px, radius 22px
- Animation `ics-in` (scale+fade 480ms) à l'ouverture
- Status Rail `.ics-rail` : 48px, point pulsé `.ics-dot.pulse`
- Styles par état : `.st-analyse`, `.st-ready`, `.st-warning`, `.st-error` (glow colored)
- Mobile (`max-width: 820px`) : panneau pleine largeur, `max-height: 40vh`, pas de superposition

### 2. HTML — structure #irisCommandScreen

```html
<section id="irisCommandScreen" class="ics-panel">
  <div class="ics-rail">           ← Status Rail
  <div class="ics-body" id="icsBody">
    <div id="icsRender"></div>     ← zone de rendu HTML
  </div>
  <div class="ics-footer" id="icsFooter">
    <div id="icsContext">          ← Context Panel
    <div id="icsMissing">          ← Missing Info Panel
  </div>
  <div class="ics-actions">        ← Modifier/Copier/Télécharger/Fermer
```

### 3. JS — renderIrisCommand(payload)

Fonction principale. Accepte `{ render_type, payload }` ou payload direct.

6 render_type gérés :

| render_type | HTML produit |
|---|---|
| `data_board` | `<table class="ics-table">` avec headers violet, badges ok/warn/crit |
| `document_draft` | div avec titre violet, meta, corps lignes, placeholders surlignés |
| `action_board` | cartes checkbox par section + confirmation obligatoire si `requires_confirmation` |
| `context_panel` | sections empilées avec heading + body |
| `missing_info` | champs ambre + boutons suggestions |
| `status_rail` | grille services avec dots animés |

### 4. inferCommandRenderFromText(text)

Router local d'intention (regex). Exemples :
- "affiche un tableau" → `data_board`
- "prépare un courrier" → `document_draft`
- "fais une checklist" → `action_board`
- "état / diagnostic" → `status_rail`
- "explique / analyse" → `context_panel`

Garanti : si le texte contient un mot-clé, le Command Screen s'ouvre immédiatement avant même la réponse vocale d'Iris.

### 5. Support WS render

```javascript
if (data.type === 'render') renderIrisCommand(data);
```

Prêt pour le contrat backend DeepSeek V2.

### 6. tool_call → renderIrisCommand

- `status: running` → `status_rail` avec service en syncing
- `status: validation_required` → `action_board` avec confirmation obligatoire
- `status: ok/other` → `context_panel` avec résultat

### 7. Prompt Iris

Ajout dans `_IRIS_SYSTEM` :
- Interdit : "je ne peux pas afficher directement"
- Interdit : markdown lu à voix haute, tableaux texte
- Obligatoire : annoncer "J'ouvre l'écran de travail" puis poser 1 question si infos manquantes

---

## Tests à effectuer par Ludovic

1. **Vocal** : "affiche un tableau avec type, montant, date, statut"
   - Attendu : Data Board HTML, colonnes violet, badges colorés, pas de markdown

2. **Écrit** : "prépare un courrier pour un exploitant"
   - Attendu : Document Draft avec titre violet, destinataire, corps, placeholders surlignés

3. **Vocal/écrit** : "fais une checklist pour finaliser Iris"
   - Attendu : Action Board avec cartes checkbox par section

4. **Vocal/écrit** : "envoie un SMS"
   - Attendu : Action Board validation requise, boutons Confirmer/Annuler, aucun SMS envoyé

5. **Mobile** : vérifier que le panneau ne superpose pas le bouton Raccrocher

---

## Ce qui n'est pas encore fait (V2)

- Backend JSON structuré : `/ws/iris-voice` ne renvoie pas encore de `{ type: "render", render_type: ..., payload: {...} }` — Iris parle mais ne pilote pas encore le Command Screen via WebSocket. Le router local `inferCommandRenderFromText` compense en V1.
- Sauvegarde dans Documents
- PDF/DOCX
- Actions réelles avec confirmation (SMS, email)

---

## Fichiers modifiés

- `static/simli.html` : +477 lignes, -254 (CSS+HTML+JS)
- `luna_web.py` : prompt Iris mis à jour (+8 lignes)

## Pas déployé

En attente feu vert Ludovic.
