# Claude — Implémentation Capability Router V1 — Objectif 026

Date : 2026-06-04
Agent : Claude (lead technique)
Type : implémentation backend — aucune action sensible réelle

---

## 1. Résumé des changements

| Fichier | Nature | Lignes impactées |
|---|---|---|
| `integrations/iris/modes.py` | Ajout `RISK_LEVELS` | +45 lignes |
| `integrations/openai/web_voice_bridge.py` | Ajout `initial_mode` au constructeur | +3 lignes |
| `luna_web.py` | Mode extraction + logs preuve + action_board niveau 3 | +70 lignes |

---

## 2. `RISK_LEVELS` (modes.py)

Dictionnaire `Dict[str, int]` — 35 outils classifiés :

| Niveau | Exemples | Comportement |
|---|---|---|
| 1 — automatique | `search_web`, `get_weather`, `iris_render`, `chat` | Exécution directe |
| 2 — guidé | `create_note`, `generate_document`, `start_meeting` | `validation_required` |
| 3 — obligatoire | `send_sms`, `call_contact`, `send_email`, `alert_contacts`, `invite_visio` | `action_board` + blocage |

---

## 3. `initial_mode` dans WebVoiceBridge

Le constructeur accepte `initial_mode: str = DEFAULT_MODE`.

`self._active_mode = initial_mode if initial_mode in IRIS_MODES else DEFAULT_MODE`

La session OpenAI est configurée avec les outils filtrés du mode dès le départ (via `_configure_session()`).

---

## 4. Extraction du mode dans `ws_iris_voice`

```
wss://.../ws/iris/voice?token=...&mode=tableau
```

- Mode validé contre `IRIS_MODES` (fallback `discussion` si inconnu)
- Log immédiat : `Iris: mode_detected=X role=Y session=Z`
- Transmis au bridge via `initial_mode=_iris_mode`

---

## 5. Logs de preuve

Chaque outil appelle maintenant :

```
Iris: tool_call fn=<nom> risk_level=<1/2/3> mode=<mode>
Iris: tool_allowed fn=<nom> risk_level=1        # si safe
Iris: tool_blocked fn=<nom> risk=3 -> action_board  # si niveau 3
Iris: render_type=<type> fn=<nom> render_done=true  # après render
```

Ces logs permettent de prouver la chaîne complète : `mode_detected → tool_call → risk_level → tool_allowed/blocked → render_type → render_done`.

---

## 6. Action Board généralisé (niveau 3)

Avant : seuls `send_sms`, `call_contact`, `send_email` avaient un `action_board` visuel.

Après : `alert_contacts` et `invite_visio` ont maintenant leur propre `action_board` avec :
- `action_type`
- `requires_confirmation: True`
- `summary` lisible
- `details` avec coût estimé et garde-fous
- ZÉRO action Twilio réelle

---

## 7. Target Cells V1 — statut après implémentation

### TC-026-01 — Graphique simple
```
Phrase : "Prépare un graphique avec janvier 10, février 20, mars 30"
Mode : tableau (?mode=tableau)
Outils filtrés : ["iris_render", "chat"]
Rendu : chart (via iris_render côté bridge, ou fallback client)
Log preuve : mode_detected=tableau → tool_call fn=iris_render risk_level=1
Statut : ✅ fonctionnel
```

### TC-026-02 — Graphique sans données
```
Phrase : "Prépare un graphique business plan"
Mode : tableau
Rendu : missing_info (Iris doit demander les chiffres)
Statut : ✅ fonctionnel (iris_render → missing_info)
```

### TC-026-03 — Recherche web
```
Phrase : "Cherche Base Legacy sur le web et affiche les sources"
Mode : recherche (?mode=recherche)
Outils filtrés : ["search_web", "get_page_info", "get_news", "iris_render", "chat"]
Tool : search_web → _iris_auto_render → research_board
Log preuve : tool_allowed fn=search_web risk_level=1 → render_type=research_board render_done=true
Statut : ✅ fonctionnel
```

### TC-026-04 — Rédaction brouillon
```
Phrase : "Rédige un courrier professionnel pour un exploitant"
Mode : redaction (?mode=redaction)
Outils filtrés : ["iris_render", "generate_document", "chat"]
Rendu : document_draft
Statut : ✅ fonctionnel
```

### TC-026-05 — SMS bloqué
```
Phrase : "Envoie un SMS à Lucas"
Mode : actions (?mode=actions)
Tool tenté : send_sms
Risk level : 3
Résultat : action_board affiché + validation_required retourné
Log preuve : tool_call fn=send_sms risk_level=3 → tool_blocked fn=send_sms risk=3 -> action_board
NO SMS RÉEL : aucun appel Twilio, aucun envoi
Statut : ✅ bloqué correctement
```

---

## 8. Ce qui n'est PAS dans ce commit

- Aucune UX mode selector (Kimi)
- Aucun badge mode actif (Kimi)
- Aucun endpoint manquant corrigé (DeepSeek)
- Aucun déploiement Cloud Run

---

## 9. Interdits respectés

- ✅ Aucun SMS réel
- ✅ Aucun appel réel
- ✅ Aucun email réel
- ✅ Aucun paiement
- ✅ Aucune suppression
- ✅ Aucune clé API dans le frontend
- ✅ Aucun secret dans GitHub
