# Codex — Audit F12 Iris sans tool/render — Objectif 026

Date : 2026-06-04
Agent : Codex
Type : audit terrain / cause probable
Niveau : 0

## Constat terrain

Logs fournis par Ludovic :

```text
[INFO][simli] pipeline_audio playing
[INFO][simli] pipeline_transcript_iris Je comprends ce que tu veux. Malheureusement, je ne peux pas ...
[INFO][simli] pipeline_transcript_iris Parfait, allons-y étape par étape. Je vais te dicter le text...
[INFO][simli] ics_working Iris prépare
```

Capture :

- Le Command Screen affiche `Diagnostic en cours`.
- Dernier maillon atteint : `transcript_iris`.
- Aucun `tool_call`, aucun `render`, aucun `render_done`.

Conclusion : le micro, le texte Iris et l'audio fonctionnent. Le maillon cassé est entre la réponse OpenAI et le déclenchement réel d'un outil / rendu visuel.

## Cause probable 1 — session WS ouverte sans mode

Dans `static/simli.html`, la connexion WebSocket est ouverte ainsi :

```js
var wsUrl = proto + '//' + location.host + '/ws/iris-voice?token=' + encodeURIComponent(token);
```

Le mode actif (`tableau`, `document`, `recherche`, etc.) n'est pas transmis au démarrage.

Impact :

- Le backend démarre en mode par défaut.
- Si le mode n'est pas changé après connexion, Iris peut rester en mode discussion.
- Le Command Screen attend un rendu, mais le serveur n'a pas été forcé dans le bon contexte métier.

Correctif attendu :

```js
var wsUrl = proto + '//' + location.host
  + '/ws/iris-voice?token=' + encodeURIComponent(token)
  + '&mode=' + encodeURIComponent(_currentMode || 'discussion');
```

## Cause probable 2 — `chat` contourne le rendu

Dans `integrations/openai/web_voice_bridge.py`, `_build_filtered_tools()` ajoute toujours `chat` :

```py
allowed = set(get_mode_tools(mode_id))
allowed.add("chat")
```

Même avec :

```py
"tool_choice": "required"
```

OpenAI peut choisir l'outil `chat`, donc la contrainte "outil obligatoire" est respectée techniquement, mais aucun travail visuel n'est produit.

Impact :

- Iris dit "je vais préparer".
- Le panneau passe en `ics_working`.
- Aucun `iris_render` n'arrive.
- Au bout de 10 secondes, diagnostic.

Correctif attendu :

- Garder `chat` seulement dans le mode `discussion`.
- En modes productifs (`tableau`, `document`, `recherche`, `analyse`, `reunion`, etc.), retirer `chat` ou le rendre fallback secondaire.
- Si Iris promet un travail sans tool_call, déclencher un fallback serveur déterministe vers `iris_render`, pas seulement un message texte.

## Cause probable 3 — production pas forcément sur le dernier main

Le dernier main audité contient le commit `6d204ce` qui aligne mieux le dispatch sur `RISK_LEVELS`.

Mais les logs F12 ne montrent pas encore :

```text
tool_call
render
render_done
mode_changed
```

Action : vérifier que la révision Cloud Run active contient bien `6d204ce` ou plus récent.

## Ce que F12 / DevTools AI doit vérifier

Demander au panneau Assistance IA de DevTools :

```text
Analyse cette page Iris. Ne cherche pas GitHub. Vérifie uniquement le runtime.

1. Dans Network > WS, ouvre /ws/iris-voice.
2. Donne l'URL exacte du WebSocket : contient-elle mode=tableau, mode=document, mode=recherche, etc. ?
3. Dans Messages, cherche les événements : mode_changed, tool_call, iris_render, render, render_done.
4. Dans Console, filtre : mode_select, mode_changed, pipeline_transcript_iris, tool_call, render, render_done, ics_working.
5. Si le dernier événement est transcript_iris sans tool_call/render, conclus : rupture LLM -> outil.
6. Si le WebSocket est ouvert sans mode=, conclus : session démarrée en mode discussion.
7. Si un outil chat est choisi, conclus : chat contourne le rendu visuel.
8. Donne le dernier message WebSocket reçu et le premier événement attendu absent.
```

## Mission Claude

1. Corriger `static/simli.html` pour passer `mode` dans l'URL `/ws/iris-voice`.
2. Modifier `_build_filtered_tools()` :
   - `chat` seulement en mode `discussion`.
   - en mode productif, imposer les outils métier du mode.
3. Ajouter un log client visible au démarrage :

```text
iris_ws_open mode=<mode>
```

4. Ajouter un log serveur :

```text
mode_selected=<mode> tools=[...]
```

5. Déployer seulement après push GitHub et validation Ludovic/Kimi si impact UX visible.

## Mission Kimi

1. Vérifier que l'utilisateur voit clairement le mode actif.
2. Si l'utilisateur demande un tableau / graphique / document, vérifier que l'UI bascule ou confirme le bon mode sans friction.
3. Interdire UX : panneau diagnostic si le système peut plutôt afficher une action claire.
4. Vérifier que le rendu final n'est pas un gros texte brut.

## Mission DeepSeek

1. Auditer si `chat` doit être totalement interdit en modes productifs.
2. Auditer le fallback déterministe : promesse Iris sans outil => `iris_render` serveur automatique.
3. Vérifier la cohérence `VOICE_TOOLS_BY_MODE`, `RISK_LEVELS`, `handle_iris_tool`, `_iris_auto_render`.
4. Vérifier Cloud Run : dernier commit déployé = main récent.

## Verdict

Iris n'est pas bloquée par l'écran. L'écran révèle une rupture plus haute :

```text
voix utilisateur -> OpenAI -> transcript Iris -> PAS de tool_call -> PAS de render -> diagnostic
```

Le bug principal est un problème de canalisation : Iris est encore autorisée à parler quand elle devrait agir.

