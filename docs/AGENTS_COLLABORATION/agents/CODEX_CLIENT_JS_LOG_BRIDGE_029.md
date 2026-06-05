# Codex — Pont F12 vers Cloud Run — Objectif 029

Date : 2026-06-05
Agent : Codex
Type : implementation niveau 1

## Problème

Claude ne voit pas la console F12 du navigateur. Or les blocages Iris actuels peuvent être côté client :

- erreur JavaScript ;
- promesse non gérée ;
- fichier script/CSS non chargé ;
- WebSocket ouvert mais handler client cassé ;
- rendu ICS reçu mais non affiché.

## Correctif livré

### Client `static/simli.html`

Ajout d'une capture automatique :

```text
window error -> rLog(error, client_js, window_error)
unhandledrejection -> rLog(error, client_js, unhandled_rejection)
SCRIPT/LINK resource error -> rLog(error, client_js, resource_error)
```

Sécurité :

- déduplication 30 secondes par erreur ;
- troncature ;
- masquage Bearer token, `token=...`, clés `sk_...`, `api_key`.

### Serveur `luna_web.py`

`/api/debug/log` continue de stocker dans Redis, mais les erreurs critiques sont maintenant aussi recopiées dans Cloud Run :

```text
[CLIENT-DEBUG] error [client_js] ...
```

Cela permet à Claude de voir les erreurs F12 sans demander un copier-coller à Ludovic.

## À chercher dans Cloud Run

```text
CLIENT-DEBUG
client_js
window_error
unhandled_rejection
resource_error
ics_work_timeout
ics_render
iris_ws_error
ui_state_ack
```

## Validation

Checks locaux :

```text
python -m py_compile luna_web.py : OK
node --check scripts inline simli.html : OK
```

## Garde-fous

- Aucun secret loggé volontairement.
- Aucun SMS/email/appel déclenché.
- Aucun changement Cloud/base/secrets.
