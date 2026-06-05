# Codex — Fix iris_render payload direct — Objectif 029

Date : 2026-06-05
Agent : Codex
Type : correctif niveau 1

## Problème

Le schema `iris_render` demande normalement :

```json
{
  "render_type": "chart",
  "payload": {
    "title": "...",
    "labels": [],
    "datasets": []
  }
}
```

Mais OpenAI Realtime peut parfois produire :

```json
{
  "render_type": "chart",
  "title": "...",
  "labels": [],
  "datasets": []
}
```

Avant le correctif, le serveur faisait :

```python
payload = args.get("payload", {})
```

Résultat : si OpenAI ne wrappe pas dans `payload`, le Command Screen reçoit un rendu vide.

## Correctif

Dans `integrations/openai/web_voice_bridge.py`, `iris_render` accepte désormais 3 cas :

1. `payload` présent et non vide :
   - `payload_source=payload`

2. données directes au niveau racine :
   - `payload_source=args_unwrapped`
   - le serveur reconstruit le payload depuis `title`, `rows`, `boxes`, `labels`, etc.

3. payload totalement vide :
   - `payload_source=empty_payload_fallback`
   - rendu `missing_info` affiché au lieu d'un panneau blanc.

## Logs attendus

```text
WebVoice: render_type=<type> fn=iris_render payload_source=<source> keys=[...] render_done=true
```

## Pourquoi c'est important

Iris ne doit jamais donner l'impression qu'elle "n'a pas d'écran".
Si elle appelle `iris_render`, même imparfaitement, le serveur doit protéger l'expérience utilisateur et produire un rendu visible.

## Tests à faire

1. `Iris, fais un graphique avec janvier 10, février 20, mars 30.`
2. `Iris, fais un tableau avec Produit A 120 et Produit B 230.`
3. `Iris, prépare un courrier de relance client.`

PASS si Cloud Run montre :

```text
tool_call iris_render
payload_source=payload OU args_unwrapped
render_done=true
```

et si le Command Screen affiche un rendu visible.
