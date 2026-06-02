# Iris Command Screen — Brief équipe IA (2 juin 2026)

> Document de travail pour DeepSeek, Kimi, Codex.
> Claude = lead technique. Ludo = fondateur. Rien ne se déploie sans validation Ludo.

---

## C'est quoi l'Iris Command Screen ?

Panneau visuel holographique qui s'affiche à droite pendant une conversation vocale avec Iris (page `/simli`).
L'idée : **l'écran est un participant à la conversation**, pas une réponse optionnelle.
Quand Iris parle, l'écran affiche le contenu structuré. Iris annonce en 1 phrase ce qu'elle vient d'afficher.

Exemple concret :
- Ludo dit : "Affiche-moi un tableau de mes dépenses"
- L'écran s'ouvre en mode ANALYSE (immédiatement)
- Iris prépare le tableau → appelle `iris_render(data_board, {...})` → le tableau apparaît
- Iris dit : "Voici tes dépenses du mois."

---

## Architecture technique

```
Browser (simli.html)
    │
    ├── WebSocket /ws/iris-voice
    │       │
    │       └── WebVoiceBridge (web_voice_bridge.py)
    │               │
    │               └── OpenAI Realtime API (gpt-realtime-mini)
    │
    └── Messages entrants du serveur :
            {type:"audio"}           → chunks audio PCM16
            {type:"audio_done"}      → fin du stream audio
            {type:"transcript", role:"user"|"luna", text:"..."}
            {type:"render", render_type:"...", payload:{...}}   ← iris_render
            {type:"tool_call", name:"...", status:"..."}
            {type:"error", message:"..."}
            {type:"ended", reason:"..."}
```

### Fichiers clés

| Fichier | Rôle |
|---|---|
| `static/simli.html` | Toute la UI + JS de l'ICS |
| `integrations/openai/web_voice_bridge.py` | Bridge WS → OpenAI. Gère `iris_render` (ligne ~633) |
| `integrations/openai/realtime_bridge.py` | `VOICE_TOOLS` liste (iris_render ligne ~595) |
| `luna_web.py` | `_IRIS_SYSTEM` prompt (ligne ~8912) + endpoint `/ws/iris-voice` |

---

## Séquence d'événements OpenAI Realtime (ordre réel)

```
OpenAI → response.audio.delta      (×N, chunks audio)
OpenAI → response.audio.done       → bridge envoie {type:"audio_done"} au client
OpenAI → response.audio_transcript.done → bridge envoie {type:"transcript", role:"luna", text:"..."}
```

**IMPORTANT** : `audio_done` arrive AVANT le transcript.
Tout fallback déclenché sur `audio_done` sera vide.

---

## Fallback client actuel (ce qui est codé dans simli.html)

### Variables globales ICS
```javascript
var _icsLastServerRender = 0;    // timestamp du dernier render reçu du serveur
var _icsLastUserSpoke    = 0;    // timestamp du dernier message utilisateur
var _icsIrisResponseText = '';   // texte accumulé de la réponse Iris
var _icsFallbackTimer    = null; // debounce timer pour le fallback
```

### Déclenchement du fallback
Quand `{type:"transcript", role:"luna"}` arrive :
1. Accumule le texte dans `_icsIrisResponseText`
2. Reset debounce 300ms
3. Après 300ms sans nouveau transcript : si `_icsLastServerRender <= _icsLastUserSpoke` → affiche fallback

Fallback payload :
```javascript
var _fbType = inferCommandRenderFromText(_fbText) || 'context_panel';
var _fbPl   = _fbType === 'context_panel'
    ? { title: 'Iris', sections: [{ heading: 'Réponse', body: _fbText }] }
    : _icsBuildPayload(_fbType, _fbText);
```

### `inferCommandRenderFromText(text)` — routeur local
Détecte le type de render à partir du texte (user ou Iris) :
```javascript
function inferCommandRenderFromText(text) {
  var t = String(text||'').toLowerCase();
  if (/\b(tableau|table|colonnes?|données|compare[zr]?|liste[zr]?|grille|affiche.*(données|résultats|chiffres))\b/.test(t)) return 'data_board';
  if (/\b(courrier|lettre|mail|email|message officiel|réponse écrite|rédige|redige|écris|ecris|brouillon|note officielle)\b/.test(t)) return 'document_draft';
  if (/\b(checklist|liste de tâches?|plan d'?action|todo|étapes?|etapes?|organise|fais.*(liste|plan|checklist))\b/.test(t)) return 'action_board';
  if (/\b(état|etat|statut|services?|diagnostic|quotas?|santé|sante|check)\b/.test(t)) return 'status_rail';
  if (/\b(explique|analyse[zr]?|résume|resume|contexte|comprends?|qu.est-ce)\b/.test(t)) return 'context_panel';
  if (/\b(panneau|command screen|workspace|bureau|workbench|espace de travail)\b/.test(t)) return 'data_board';
  if (/\b(affiche|montre|ouvre|montrez?[-\s]moi|fais[-\s]voir|afficher|montrer)\b/.test(t)) return 'context_panel';
  return '';
}
```

---

## 6 types de render — format payload

### `data_board` — tableau
```json
{
  "render_type": "data_board",
  "payload": {
    "title": "Titre du tableau",
    "columns": ["Col1", "Col2", "Statut"],
    "rows": [["val1", "val2", "ok"], ["val3", "val4", "warn"]],
    "summary": "Résumé optionnel"
  }
}
```

### `document_draft` — courrier
```json
{
  "render_type": "document_draft",
  "payload": {
    "title": "Objet du document",
    "recipient": "Nom du destinataire",
    "body": "Corps du document\n\nAvec sauts de ligne.",
    "placeholders": ["[Destinataire]", "[Date]"]
  }
}
```

### `action_board` — checklist
```json
{
  "render_type": "action_board",
  "payload": {
    "sections": [
      { "title": "À faire", "items": [{"text": "Étape 1", "done": false, "tag": "warn"}] },
      { "title": "Fait", "items": [{"text": "Étape 0", "done": true}] }
    ],
    "requires_confirmation": false,
    "summary": "Résumé du plan"
  }
}
```

### `context_panel` — analyse
```json
{
  "render_type": "context_panel",
  "payload": {
    "title": "Titre (optionnel)",
    "sections": [
      {"heading": "Sous-titre", "body": "Texte explicatif."},
      {"heading": "Autre section", "body": "Contenu."}
    ]
  }
}
```

### `missing_info` — infos manquantes
```json
{
  "render_type": "missing_info",
  "payload": {
    "fields": ["Le destinataire", "La date souhaitée"],
    "suggestions": ["Aujourd'hui", "Cette semaine"]
  }
}
```

### `status_rail` — état des services
```json
{
  "render_type": "status_rail",
  "payload": {
    "services": [
      {"name": "SMS", "status": "active", "detail": "Twilio OK"},
      {"name": "Email", "status": "warn", "detail": "Non configuré"},
      {"name": "Vols", "status": "inactive", "detail": "Duffel désactivé"}
    ],
    "summary": "3 services vérifiés"
  }
}
```

Statuts disponibles : `active`, `warn`, `error`, `inactive`, `syncing`

---

## Ce qui marche ✅

- Écran s'ouvre en mode ANALYSE dès que l'utilisateur parle
- Boot animation holographique (0.55s) + scan-line
- HUD corners + grille holographique
- Stagger build animation sur les lignes
- Tous les 6 types de render sont implémentés et stylisés
- Fallback client sur transcript Iris (debounce 300ms)

## Ce qui est en chantier 🔧

- **Tester** que le fallback fonctionne (transcript arrive bien, context_panel s'affiche)
- `inferCommandRenderFromText` : enrichir les patterns pour détecter plus précisément le type de render depuis le texte d'Iris

## Ce qui reste à faire V2 📋

- Bouton "Sauvegarder" : envoie le contenu affiché dans le vault IA du souscripteur
- Export PDF/DOCX depuis le Command Screen
- Actions réelles avec confirmation (SMS depuis action_board, note, rappel)
- Historique des renders dans la session (navigation ← →)

---

## Instructions pour DeepSeek

**Tâche : améliorer `inferCommandRenderFromText`**

La fonction actuelle rate certains patterns dans la réponse d'Iris. Objectif : mieux détecter le type de render depuis le texte d'Iris (pas seulement du user).

Exemples que la fonction doit mieux gérer :
- "Voici les informations sur les vols Paris-Lyon" → `data_board`
- "Je t'ai préparé une lettre de résiliation" → `document_draft`
- "Voici les étapes pour renouveler ta carte" → `action_board`
- "Il me manque quelques informations" → `missing_info`
- "Vérifions l'état de tes services" → `status_rail`
- Toute réponse > 2 phrases → `context_panel` (fallback intelligent)

**Règles :**
- Ne modifier que `static/simli.html`, fonction `inferCommandRenderFromText` (ligne ~3373)
- Envoyer le patch via PR ou message dans CLAUDE.md
- Ne pas déployer — Claude valide avant

---

## Instructions pour Kimi

**Tâche : enrichir `_icsBuildPayload` pour les payloads fallback**

Quand le fallback client construit un payload à partir du texte d'Iris, le résultat est générique.
Objectif : rendre les payloads de fallback plus riches et pertinents.

Exemple actuel pour `context_panel` :
```javascript
{ title: 'Iris', sections: [{ heading: 'Réponse', body: _fbText }] }
```

Amélioration souhaitée : parser le texte d'Iris pour extraire plusieurs sections (si le texte contient des phrases séparées → une section par idée principale).

**Règles :**
- Ne modifier que `static/simli.html`, fonction `_icsBuildPayload` (ligne ~3384) + la section fallback dans le handler transcript
- Envoyer le patch via PR ou message dans CLAUDE.md
- Ne pas déployer — Claude valide avant

---

## Instructions pour Codex

**Tâche : tester et rapporter**

1. Ouvrir `/simli` sur le serveur déployé
2. Parler à Iris et noter dans le log console :
   - Est-ce que `iris_ws_open` apparaît ?
   - Est-ce que `audio_done` apparaît dans les logs serveur ?
   - Est-ce que le transcript Iris arrive (`WebVoice LUNA:` dans les logs Cloud Run) ?
   - Est-ce que l'écran se remplit avec le context_panel ?
3. Rapporter exactement ce qui se passe dans CLAUDE.md (section "Rapport Codex")

**Si l'écran reste vide** : vérifier dans la console browser si `_icsIrisResponseText` est peuplé au moment du fallback.

---

*Dernière mise à jour : 2 juin 2026 — Claude*
