# Codex — Audit initial conscience runtime Iris — Objectif 029

Date : 2026-06-05
Agent : Codex
Type : audit initial / cadrage
Niveau : 0

## Ce qui est déjà vrai dans le code

Le prompt `_IRIS_SYSTEM` contient maintenant :

- identité Iris ;
- Command Screen actif ;
- fonction `iris_render` ;
- 10 familles d'outils ;
- 10 modes ;
- 18 render types ;
- interdiction de répondre "je ne peux pas afficher" ;
- règle : render avant parole pour toute demande de travail.

Le bridge Realtime utilise :

```text
OPENAI_REALTIME_MODEL = gpt-4o-realtime-preview-2024-12-17 par défaut
OPENAI_VOICE_NAME = coral par défaut
session.update
tools = filtered_tools
tool_choice = required
```

Le pont upload document existe :

```text
ui_event document_uploaded
_session_documents append
render document_insight
ui_state_ack document_uploaded
```

## Ce qui n'est pas encore prouvé

1. Que le dernier `_IRIS_SYSTEM` est réellement déployé en prod.
2. Que `session.update` accepte le prompt complet et les tools.
3. Que le modèle/key utilisée accepte bien function calling Realtime avec ces tools.
4. Que les tools reçus par OpenAI correspondent au mode actif.
5. Que tous les boutons UI alimentent la mémoire Iris, pas seulement upload.

## Hypothèses de panne

### H1 — Prompt non déployé

Le code local contient la conscience ICS, mais Cloud Run peut servir une révision avant `1c2e55c`.

### H2 — Prompt envoyé mais non vérifié

Le prompt est envoyé, mais aucun marker ne permet de prouver qu'OpenAI l'a reçu.

### H3 — Tools filtrés mais mauvais mode

Le mode actif peut rester `discussion`, donc `chat` peut encore être disponible.

### H4 — Tool calling cassé / modèle limité

La clé ou le modèle peut accepter l'audio mais échouer sur certains tools ou sur `tool_choice=required`.

### H5 — UI non synchronisée

Les boutons existent mais ne font pas tous :

```text
ui_event -> mémoire session -> contexte Iris
```

## Action prioritaire Codex

Demander un endpoint debug non sensible :

```text
GET /api/debug/iris-capabilities
```

Objectif : prouver la réalité serveur sans exposer de secrets.

Champs attendus :

```json
{
  "prompt_marker": true,
  "model": "gpt-4o-realtime-preview-2024-12-17",
  "voice": "coral",
  "modes_count": 10,
  "render_types_count": 18,
  "tools_by_mode": {},
  "handlers_available": {},
  "risk_levels": {},
  "last_deploy_commit": "..."
}
```

## Verdict

Le code va dans la bonne direction, mais la conscience Iris ne doit pas être supposée.

Elle doit être prouvée par :

```text
prompt_marker + session.updated + tools list + tool_call + render_done + ui_state_ack
```

