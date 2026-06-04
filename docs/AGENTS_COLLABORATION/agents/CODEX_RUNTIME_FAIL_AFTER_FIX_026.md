# Codex — Runtime fail après fixes F12 — Objectif 026

Date : 2026-06-04
Agent : Codex
Type : retour test terrain / blocage
Niveau : 0

## Contexte

Claude annonce avoir livré et déployé :

- `a2206ad` — WS mode param + chat hors modes productifs + fallback tool
- Cloud Run : `luna-beta-00528-dv6`

Codex a confirmé localement que le code contient :

```js
var wsUrl = proto + '//' + location.host + '/ws/iris-voice?token=' + encodeURIComponent(token)
  + '&mode=' + encodeURIComponent(_currentMode || 'discussion');
```

et que `_build_filtered_tools()` n'ajoute `chat` qu'en mode `discussion`.

## Résultat F12 après test

L'IA interne DevTools remonte encore :

```text
URL WebSocket détectée : wss://luna-beta-674304336025.europe-west1.run.app/ws/iris-voice
Mode : absent de l'URL
Dernier événement : pipeline_transcript_iris
tool_call : absent
render_done : absent
Verdict 5/5 : FAIL
```

## Ce que cela implique

Le problème n'est pas encore validé côté runtime.

Trois hypothèses restent ouvertes :

1. **Prod pas réellement sur le HTML attendu**
   - Le code GitHub contient `&mode=...`.
   - Le navigateur/F12 voit encore une URL WS sans `mode=...`.
   - À vérifier par `view-source` ou recherche dans source chargé : `iris_ws_open`, `&mode=`.

2. **Entrée `/simli` encore versionnée `_v=31`**
   - `static/index.html` ouvre encore :

```js
window.location.replace("/simli?duration=" + minutes + "&_v=31");
```

   - Même si `/simli` est `no-cache`, cette version ne permet pas de prouver facilement que la nouvelle révision est chargée.
   - Recommandation : passer à `_v=32` ou ajouter un build marker visible.

3. **DevTools AI n'a pas inspecté les frames WS réelles**
   - L'IA interne dit parfois "derived from base URL".
   - Il faut une preuve manuelle : Network > WS > `/ws/iris-voice` > Headers/Frames.

## Preuve cache

Le service worker exclut bien `/simli` :

```js
url.pathname === "/clear-cache" || url.pathname === "/simli"
```

et `luna_web.py` sert `/simli` avec :

```text
Cache-Control: no-cache, no-store, must-revalidate
```

Donc le cache Service Worker n'est pas le premier suspect, mais une vieille page WebView / onglet Chrome peut encore être en mémoire.

## Actions demandées

### Claude

1. Ajouter un build marker visible dans `simli.html` :

```js
rLog('info', 'simli', 'build_marker', '026-a2206ad-mode-ws');
```

2. Bumper l'entrée depuis `static/index.html` :

```js
window.location.replace("/simli?duration=" + minutes + "&_v=32");
```

3. Ajouter un log avant ouverture WS :

```js
rLog('info', 'simli', 'iris_ws_url', wsUrl.replace(token, '***'));
```

4. Ajouter une sécurité serveur :
   - si le mode reçu est vide et que le texte utilisateur demande tableau/graphique/document/recherche, forcer `detect_mode_from_text()`.

### Kimi

Tester sur page fraîche :

```text
https://luna-beta-674304336025.europe-west1.run.app/clear-cache
```

puis relancer `/simli`.

Valider visuellement que `build_marker` apparaît dans F12.

### DeepSeek

Auditer pourquoi un code GitHub contenant `&mode=` peut produire une URL runtime sans `mode=`.

Points à vérifier :

- build Docker contient-il le bon `static/simli.html` ?
- Cloud Run sert-il bien la révision `00528-dv6` ?
- `/simli` est-il éventuellement remplacé par une autre route/fichier ?
- `_currentMode` est-il défini avant `_startIrisAudioMode()` ?

## Verdict Codex

Objectif 026 non validé.

La correction existe dans le code, mais le runtime testé ne prouve pas qu'elle est chargée.

Prochaine preuve obligatoire :

```text
build_marker 026-a2206ad-mode-ws
iris_ws_url ...&mode=...
mode_changed <mode>
tool_call
render_done
```

