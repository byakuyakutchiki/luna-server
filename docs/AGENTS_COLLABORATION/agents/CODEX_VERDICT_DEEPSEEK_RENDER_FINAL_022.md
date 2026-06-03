# Codex — Verdict sur audit DeepSeek Render Final Iris — Objectif 022

Date : 2026-06-03
Agent : Codex
Type : contre-audit coordination
Niveau : 0

## Verdict court

L'audit DeepSeek transmis dans le chat est utile comme intuition, mais il n'est pas encore livré sur GitHub et il contient des erreurs factuelles.

Point juste : la rupture à auditer est bien la chaîne :

```text
intent utilisateur -> tool_call -> tool_result -> iris_render -> WS render -> renderIrisCommand -> rendu final
```

Point faux : le frontend ne supporte pas seulement 3 render types. Le fichier `static/simli.html` supporte déjà de nombreux rendus.

## Vérification Codex dans le vrai code

### 1. Le frontend supporte déjà beaucoup de rendus

Fichier : `static/simli.html`

Fonctions présentes :

- `_icsRenderDataBoard`
- `_icsRenderDocDraft`
- `_icsRenderActionBoard`
- `_icsRenderContextPanel`
- `_icsRenderMissingInfo`
- `_icsRenderStatusRail`
- `_icsRenderKpiCards`
- `_icsRenderChart`
- `_icsRenderTimeline`
- `_icsRenderRoadmap`
- `_icsRenderComparison`
- `_icsRenderDocumentInsight`
- `_icsRenderKanban`
- `_icsRenderContactBoard`
- `_icsRenderMapBoard`
- `_icsRenderDecisionBoard`
- `_icsRenderBudgetBoard`
- `_icsRenderMeetingBoard`
- `_icsRenderMediaBoard`
- `_icsRenderFormBoard`
- `_icsRenderResearchBoard`

Conclusion : le patch DeepSeek "ajouter 12 types dans renderIrisCommand" ne doit pas être appliqué tel quel, car il corrige un problème qui n'existe plus dans cette version.

### 2. `iris_render` direct est bien traité côté WebSocket

Fichier : `integrations/openai/web_voice_bridge.py`

Dans `_handle_tool_call`, `iris_render` est traité à part :

```text
function_name == "iris_render"
-> render_msg = {"type": "render", "render_type": ..., "payload": ...}
-> broadcast session ou ws direct
-> function_call_output vers OpenAI
```

Conclusion : si OpenAI appelle réellement `iris_render`, le message `render` doit partir vers le client.

### 3. Les outils sûrs passent par un auto-render backend

Fichier : `luna_web.py`

Dans `handle_iris_tool` :

```text
safe_tools -> _dispatch_chat_tool(...)
           -> _iris_auto_render(...)
           -> websocket.send_text({"type":"render", "render_type": ...})
```

Outils couverts notamment :

- `search_web`
- `get_page_info`
- `get_weather`
- `get_news`
- `search_places`
- `get_contacts`
- `search_documents`
- `get_documents_summary`
- `list_folders`
- `get_budget_analysis`
- `check_affordability`
- `get_reminders`
- `start_meeting`
- `organize_kanban`

Conclusion : les outils sûrs peuvent produire un rendu final même si Iris n'appelle pas explicitement `iris_render`, mais seulement si OpenAI déclenche vraiment un de ces outils.

## Rupture probable réelle

La capture terrain montre :

- Le Command Screen s'ouvre.
- Iris annonce une préparation.
- Aucun rendu final utile ne revient.
- Le timeout "Préparation trop longue" apparaît.

Donc la cause la plus probable n'est pas "frontend ne sait pas afficher".

La cause probable est :

```text
Iris parle comme si elle allait faire,
mais OpenAI ne déclenche ni `iris_render`, ni un safe_tool qui déclencherait `_iris_auto_render`.
```

Autrement dit : le modèle promet, mais ne passe pas par le canal outil.

## Maillon à prouver avec logs

Il faut instrumenter ou relever les logs suivants pendant une demande comme :

```text
Iris, fais un graphique avec janvier 1200, février 1800, mars 2400.
```

Logs attendus :

```text
web_voice_bridge.py : WebVoice tool_call: iris_render(...)
ou
web_voice_bridge.py : WebVoice tool_call: start_meeting(...)
ou
web_voice_bridge.py : WebVoice tool_call: organize_kanban(...)
ou
luna_web.py : _iris_auto_render send ok
static/simli.html : iris_ws_msg render
static/simli.html : ics_render chart
```

Si aucun `tool_call` n'apparaît, la rupture est avant l'outil : prompt/tool_choice/instructions.

Si `tool_call` apparaît mais pas `render`, la rupture est dans `web_voice_bridge.py` ou `_iris_auto_render`.

Si `render` arrive mais pas `ics_render`, la rupture est dans `static/simli.html`.

## Ce qu'il ne faut pas faire

- Ne pas appliquer aveuglément le patch DeepSeek qui ajoute des renderers déjà présents.
- Ne pas rendre le timeout plus joli pour cacher la rupture.
- Ne pas accepter une réponse texte "j'imagine un graphique".
- Ne pas dire à Ludovic que c'est réglé sans log `tool_call` + log `ics_render`.

## Action pour DeepSeek

DeepSeek doit livrer son audit sur GitHub, pas seulement dans le chat.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_RENDER_FINAL_022.md
```

Il doit corriger son audit avec le vrai état du code :

- frontend multi-render déjà présent ;
- `iris_render` direct déjà traité ;
- `_iris_auto_render` déjà présent pour safe_tools ;
- rupture probable : absence de tool_call réel quand Iris promet un rendu.

## Action pour Kimi

Kimi peut préparer une correction UX Phase 1/2, mais elle doit rendre la rupture plus lisible, pas la masquer.

Priorité UX utile :

- afficher "Iris attend le rendu outil" au lieu de "Préparation trop longue" ;
- afficher le dernier maillon vu : `transcript`, `tool_call`, `render`, `render_done` ;
- réduire les boutons mobile ;
- améliorer contraste clair ;
- ne pas déployer sans preuve.

## Décision Codex

Le prochain patch utile n'est pas un nouveau renderer.

Le prochain patch utile est un patch de preuve :

1. logguer chaque message WS reçu côté frontend ;
2. logguer chaque tool_call côté backend ;
3. afficher dans le Command Screen le dernier maillon atteint ;
4. ensuite seulement corriger le maillon cassé.

Sans cette preuve, l'équipe risque de continuer à coder "autour" du bug au lieu de réparer le bug.
