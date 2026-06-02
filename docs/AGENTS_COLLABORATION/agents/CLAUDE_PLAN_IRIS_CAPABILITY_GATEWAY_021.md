# Claude — Plan V1 Iris Capability Gateway — Objectif 021

Date : 2026-06-02
Agent : Claude (lead technique backend)
Type : plan d'implémentation — pas encore de code
Sources lues : TARGET_CELL.md, TARGET_REGISTER.md, OBJECTIF_021, KIMI_UX, DEEPSEEK_TARGET_CELL, CODEX_ARBITRAGE

---

## 0. Constat honnête avant de planifier

Avant de planifier quoi que ce soit, voici l'état réel du code après audit.

### Ce qui existe et fonctionne côté backend

```
_dispatch_chat_tool() — luna_web.py ligne ~5312
```

Les outils suivants EXISTENT et sont opérationnels :

| Tool | Statut réel | Accessible à Iris ? |
|---|---|---|
| `search_web` | ✅ implémenté | ✅ dans `safe_tools` de `handle_iris_tool` |
| `search_places` | ✅ implémenté | ✅ dans `safe_tools` |
| `get_page_info` | ✅ implémenté | ✅ dans `safe_tools` |
| `get_weather` | ✅ implémenté | ✅ dans `safe_tools` |
| `get_news` | ✅ implémenté | ✅ dans `safe_tools` |
| `get_contacts` | ✅ implémenté | ✅ dans `safe_tools` |
| `search_documents` | ✅ implémenté | ✅ dans `safe_tools` |
| `list_folders` | ✅ implémenté | ✅ dans `safe_tools` |
| `get_budget_analysis` | ✅ implémenté | ✅ dans `safe_tools` |
| `send_sms` | ✅ implémenté | ❌ dans `sensitive_tools` (retourne validation_required) |
| `send_email` | ✅ implémenté | ❌ dans `sensitive_tools` |
| `call_contact` | ✅ implémenté | ❌ dans `sensitive_tools` |

### Le vrai problème — le chaînon manquant

Les outils existent. Iris PEUT les appeler. Mais il manque le maillon central :

```
Tool retourne données JSON
       ↓
??? ← GAP : personne ne transforme le JSON en render_type
       ↓
Client ne voit rien (ou context_panel générique)
```

`gpt-realtime-mini` peut appeler `search_web` → il reçoit les résultats → il ne sait pas
systématiquement qu'il doit appeler `iris_render` ensuite avec ces données.

**La solution : le Capability Gateway Bridge.**

Quand un tool de la Couche A/B/C retourne des données, le backend doit
automatiquement construire et envoyer le bon `render_type` sans attendre qu'Iris
décide de le faire. Iris parle. L'écran s'allume. Toujours.

---

## 1. Architecture Capability Gateway Bridge

### Principe

```
Iris (voix) → appelle tool → handle_iris_tool() dispatche
                                    ↓
                         _dispatch_chat_tool() retourne résultat
                                    ↓
                    [NOUVEAU] _iris_auto_render(tool_name, result, ws_client)
                                    ↓
                    → construit render_type adapté
                    → envoie WS au client IMMÉDIATEMENT
                                    ↓
                    → retourne aussi le résultat texte à Iris
                       (pour qu'elle puisse commenter verbalement)
```

### Emplacement

Modification dans `handle_iris_tool()` — `luna_web.py` :

```python
if function_name in safe_tools:
    result = await _dispatch_chat_tool(function_name, arguments or {}, tid, "iris_voice")
    # NOUVEAU : auto-render selon le tool
    render_payload = _iris_build_render(function_name, arguments, result)
    if render_payload and ws_client:
        await ws_client.send_text(json.dumps(render_payload))
    return result
```

La fonction `_iris_build_render()` est la pièce centrale du Gateway.
Elle connaît : quel tool → quel render_type → comment transformer le résultat.

---

## 2. Target Cell — Capacité 1 : Recherche externe

```
Objectif          : Iris cherche dehors et affiche les résultats
Fonctionnalité    : search_web → research_board
Utilisateur cible : Owner + participants session
Target exacte     : Quand on dit "cherche X", Iris affiche sources + synthèse
                    dans research_board. Pas de "je n'ai pas accès".
Capacités         : search_web, get_news, get_page_info, get_weather
Déclencheur       : voix → OpenAI appelle search_web (outil déjà dans VOICE_TOOLS ? non → à ajouter)
Backend attendu   : _dispatch_chat_tool("search_web") existe et fonctionne
Frontend attendu  : research_board HTML/CSS (à créer dans simli.html selon spec Kimi)
Données nécessaires : SERPER_API_KEY (recherche web) ou SERPER_API_KEY absent → fallback get_news
Garde-fous        : lecture seule, pas d'action, résultat peut être vide sans crash
Preuve attendue   : dire "Iris, cherche Base Legacy" → research_board s'affiche avec sources
Preuve obtenue    : —
Statut            : non code (bridge manquant + research_board manquant + VOICE_TOOLS incomplet)
Décision Ludovic  : non (lecture seule, pas d'action payante)
```

### Ce qu'il faut implémenter

1. Ajouter `search_web`, `search_places`, `get_news`, `get_weather`, `get_page_info` dans `VOICE_TOOLS` (`realtime_bridge.py`) — aujourd'hui seul `iris_render` et `invite_to_session` y sont.
2. Ajouter `research_board` dans `simli.html` (spec Kimi `KIMI_UX_IRIS_CAPABILITY_GATEWAY_021.md` section 3).
3. Ajouter `_iris_build_render("search_web", ...)` qui construit le payload `research_board`.
4. Mettre à jour `inferCommandRenderFromText` pour détecter "cherche", "actualités", "météo", "qu'en dit internet".

---

## 3. Target Cell — Capacité 2 : Documents / Vault

```
Objectif          : Iris accède au porte-documents du souscripteur
Fonctionnalité    : search_documents / list_folders → document_insight ou data_board
Utilisateur cible : Owner (invités filtrés par projects_allowed)
Target exacte     : "Montre mes documents sur BESS" → Iris liste les documents,
                    affiche document_insight si document trouvé, missing_info si vide
Capacités         : search_documents, list_folders, get_documents_summary
Déclencheur       : voix → OpenAI appelle search_documents (à ajouter dans VOICE_TOOLS)
Backend attendu   : _dispatch_chat_tool("search_documents") existe
Frontend attendu  : document_insight existe, data_board existe
Données nécessaires : documents en base pour le tid
Garde-fous        : filtre par tid obligatoire (déjà dans _dispatch_chat_tool),
                    invité guest ne voit que projects_allowed
Preuve attendue   : "Iris, retrouve mes contrats" → document_insight s'affiche
Preuve obtenue    : —
Statut            : partiel (tools existent, bridge auto-render manquant, VOICE_TOOLS incomplet)
Décision Ludovic  : non
```

### Ce qu'il faut implémenter

1. Ajouter `search_documents`, `list_folders`, `get_documents_summary` dans `VOICE_TOOLS`.
2. `_iris_build_render("search_documents", ...)` → `data_board` (liste) ou `document_insight` (analyse).
3. Filtre invité : si `_participant_role == "guest"`, `_iris_build_render` vérifie `projects_allowed`.

---

## 4. Target Cell — Capacité 3 : Action Board SMS/appel/email

```
Objectif          : Iris prépare une action sensible et attend validation
Fonctionnalité    : send_sms / call_contact / send_email → action_board (JAMAIS exécution auto)
Utilisateur cible : Owner uniquement pour l'exécution, invité peut demander
Target exacte     : "Iris, envoie un SMS à Marie" → action_board s'affiche avec
                    destinataire, message, coût estimé, boutons [Annuler] [Approuver].
                    Zéro SMS réel avant clic Approuver.
Capacités         : action_board + requires_confirmation + get_contacts (pour résoudre le nom)
Déclencheur       : voix → OpenAI appelle send_sms → intercepté dans handle_iris_tool
Backend attendu   : handle_iris_tool intercepte send_sms AVANT _dispatch_chat_tool,
                    construit action_board payload, l'envoie en WS, retourne validation_required
Frontend attendu  : action_board existant (améliorer avec coût Twilio estimé)
Données nécessaires : get_contacts (pour résoudre "Marie" → +33612...)
Garde-fous        : horaires 22h-7h, blacklist urgences, quota Twilio, validation owner
Preuve attendue   : dire "Iris, envoie SMS à Marie" → action_board visible, ZÉRO SMS envoyé
Preuve obtenue    : —
Statut            : partiel (validation_required existe mais sans render visuel WS)
Décision Ludovic  : oui — avant d'activer l'exécution réelle (pas pour la préparation)
```

### Ce qu'il faut implémenter

1. Dans `handle_iris_tool`, pour `send_sms` / `call_contact` / `send_email` :
   - Appeler `get_contacts` pour résoudre le nom → numéro
   - Construire `action_board` payload avec destinataire, message, coût estimé
   - Envoyer le payload en WS IMMÉDIATEMENT
   - Retourner `{"status": "validation_required", ...}` à Iris (pas d'exécution)
2. Ajouter `send_sms`, `call_contact`, `send_email` dans `VOICE_TOOLS` (avec description "prépare l'action, ne l'exécute pas").
3. L'exécution réelle (appel `_dispatch_chat_tool` effectif) reste bloquée jusqu'à validation Ludovic explicite dans une prochaine version.

---

## 5. Target Cell — Capacité 4 : Map Board avec consentement

```
Objectif          : Iris affiche une adresse / un lieu / un itinéraire
Fonctionnalité    : search_places / get_page_info → map_board
Utilisateur cible : Owner (et invités si lieu public)
Target exacte     : "Iris, où est la Tour Eiffel" → map_board s'affiche avec
                    placeholder carte, adresse, bouton Google Maps.
                    Aucune géolocalisation sans consentement explicite.
Capacités         : search_places, get_page_info (pour enrichir), navigator.geolocation (client)
Déclencheur       : voix → OpenAI appelle search_places avec query lieu
Backend attendu   : _dispatch_chat_tool("search_places") existe et retourne places[]
Frontend attendu  : map_board existant + popup consentement (spec Kimi section 5.1)
Garde-fous        : consentement localStorage avant géoloc, adresse uniquement si recherche
Preuve attendue   : "Iris, trouve un restaurant à Paris" → map_board avec résultats
Preuve obtenue    : —
Statut            : partiel (map_board existe visuellement, bridge auto-render manquant)
Décision Ludovic  : non (lecture seule)
```

### Ce qu'il faut implémenter

1. `_iris_build_render("search_places", ...)` → `map_board` avec `address` depuis `places[0]`.
2. `search_places` dans `VOICE_TOOLS`.
3. Popup consentement côté client (simli.html) avant d'appeler `navigator.geolocation`.

---

## 6. Target Cell — Capacité 5 : Teams Overlay

```
Objectif          : Owner voit les participants en temps réel, peut muter/exclure
Fonctionnalité    : IrisSessionManager → overlay HTML/CSS dans simli.html
Utilisateur cible : Owner + participants
Target exacte     : En session collaborative, panneau gauche affiche la liste des
                    participants avec rôles, indicateur qui parle, boutons mute/kick.
                    Actions invité → bannière validation owner.
Capacités         : GET /api/iris/session/{id}/status, POST /api/iris/session/{id}/revoke,
                    GET /api/iris/session/{id}/pending, POST approve/reject
Backend attendu   : TERMINÉ (commit c2b1990) — routes existent
Frontend attendu  : overlay HTML/CSS (spec Kimi KIMI_UX_IRIS_021.md Chantier 1) — NON FAIT
Garde-fous        : JWT session_id requis, seul owner peut muter/kick
Preuve attendue   : ouvrir /simli avec session_id → voir panneau participants
Preuve obtenue    : —
Statut            : partiel (backend atteint, frontend non code)
Décision Ludovic  : non (UI seulement)
```

### Ce qu'il faut implémenter

Côté `simli.html` uniquement :
1. Détection `?session=` dans l'URL ou dans le JWT → activer panneau Teams.
2. HTML/CSS overlay selon spec Kimi (240px gauche desktop, barre compacte mobile).
3. Polling `GET /api/iris/session/{id}/status` toutes les 5s → mise à jour liste.
4. Boutons mute/kick (owner only) → `POST /api/iris/session/{id}/revoke`.
5. Polling pending actions (owner only) → bannière ambre avec [Approuver]/[Refuser].

---

## 7. Target Cell — Capacité 6 : Mode clair/sombre

```
Objectif          : Utilisateur choisit le thème de l'interface Iris
Fonctionnalité    : toggle [🌙/☀] → CSS variables data-theme="light/dark"
Utilisateur cible : Tous
Target exacte     : Cliquer sur le bouton → toute l'interface change de thème.
                    Préférence persistée. Chaque render_type lisible dans les 2 thèmes.
Capacités         : CSS variables, localStorage, document.documentElement.setAttribute
Déclencheur       : clic bouton toggle dans barre basse
Backend attendu   : aucun
Frontend attendu  : CSS variables selon spec Kimi (KIMI_UX_IRIS_021.md Chantier 2)
Garde-fous        : aucun
Preuve attendue   : clic toggle → fond violet clair → tous les panneaux lisibles
Preuve obtenue    : —
Statut            : non code
Décision Ludovic  : non
```

### Ce qu'il faut implémenter

1. Ajouter les variables CSS `[data-theme="light"]` dans `simli.html` (spec Kimi complète).
2. Bouton toggle dans la barre basse.
3. `localStorage.setItem('iris-theme', ...)` et lecture au chargement.

---

## 8. Ordre d'implémentation V1

Séquence recommandée (du plus simple/prouvable au plus complexe) :

```
ÉTAPE 1 — VOICE_TOOLS (30 min)
  Ajouter dans realtime_bridge.py les tools manquants :
  search_web, search_places, get_weather, get_news, get_page_info,
  get_contacts, search_documents, list_folders, get_budget_analysis,
  send_sms, call_contact, send_email
  → Iris peut maintenant les appeler (même si l'écran ne s'allume pas encore)

ÉTAPE 2 — _iris_build_render() (2h)
  Nouvelle fonction dans luna_web.py — handle_iris_tool :
  Mappe tool_name + result → render_type payload → WS send
  Capacités : search_web → research_board, search_places → map_board,
  search_documents → document_insight/data_board,
  get_budget_analysis → budget_board, get_contacts → contact_board
  → L'écran s'allume automatiquement quand un tool retourne des données

ÉTAPE 3 — Action Board préparation (1h)
  Modifier handle_iris_tool pour send_sms/call_contact/send_email :
  intercepter AVANT dispatch, construire action_board avec coût estimé,
  envoyer en WS, retourner validation_required
  → Iris prépare, ne fait pas

ÉTAPE 4 — research_board CSS + JS (1h)
  Ajouter le type research_board dans simli.html
  (spec Kimi section 3 — sources + synthèse + badges fiabilité)

ÉTAPE 5 — Light/Dark Mode (1h)
  CSS variables + toggle + localStorage

ÉTAPE 6 — Teams Overlay HTML (2h)
  HTML/CSS overlay dans simli.html
  Polling status + approve/reject actions
  Boutons mute/kick

ÉTAPE 7 — Test terrain + preuve Codex
  Tester les 5 phrases fondatrices (OBJECTIF_021 section 4)
  Mettre à jour TARGET_REGISTER.md avec verdicts réels
```

---

## 9. Ce qui ne change PAS

- `gpt-realtime-mini` reste le modèle (contrainte compte OpenAI)
- Mode solo fonctionne sans aucune session (session_id absent = comportement actuel)
- Aucune action réelle SMS/appel/email avant validation Ludovic explicite
- Aucun déploiement sans validation Ludovic
- `CORTEX_ENABLED=false` dans deploy.sh — garde-fou permanent

---

## 10. Risques identifiés

| Risque | Probabilité | Mitigation |
|---|---|---|
| `gpt-realtime-mini` n'appelle pas les nouveaux tools | Haute | Le bridge auto-render contourne ce problème : même si Iris ne call pas le tool, le fallback transcript → context_panel reste actif |
| SERPER_API_KEY absent | Possible | Fallback `get_news` ou message `missing_info` "Recherche web non configurée" |
| Twilio non configuré | Possible | action_board s'affiche quand même, bouton Approuver désactivé avec message "Twilio non configuré" |
| Teams overlay casse le layout mobile | Possible | Toujours en barre compacte sur mobile, slide-down seulement sur tap |
| Performance polling 5s Teams | Faible | Polling conditionnel : uniquement si `?session=` dans l'URL |

---

## 11. Feux verts nécessaires avant de commencer

| Condition | Responsable | Statut |
|---|---|---|
| Kimi a livré spec research_board | Kimi | ✅ KIMI_UX_IRIS_CAPABILITY_GATEWAY_021.md |
| Kimi a livré spec light/dark variables | Kimi | ✅ KIMI_UX_IRIS_021.md |
| Kimi a livré spec Teams overlay | Kimi | ✅ KIMI_UX_IRIS_021.md |
| Codex a validé priorité V1 | Codex | ✅ CODEX_ARBITRAGE_DEEPSEEK_TARGET_CELL_021.md |
| Ludovic valide ce plan | Ludovic | ⏳ en attente |

---

*Claude — Lead technique — 2 juin 2026*
*Ne code rien tant que Ludovic n'a pas validé ce plan.*
*Objectif : 7 capacités Iris atteintes avec preuve terrain, pas annoncées.*
