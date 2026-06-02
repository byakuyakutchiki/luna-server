# Codex — Fix régression `_guestCount` visio Iris — Objectif 017

Date : 2026-06-02
Agent : Codex
Type : correctif régression niveau 1

## Symptôme terrain

Après le patch latence/persona, Iris transcrit la voix mais ne répond plus.

Log décisif :

```text
vad_transcribed ...
llm_start
vad_transcribe_err ReferenceError: _guestCount is not defined
```

## Cause

`_irisReply()` envoyait `participants_count: _guestCount + 1` vers `/api/visio/chat`.

Mais `_guestCount` était déclaré localement dans le bloc Daily participant, donc invisible depuis `_irisReply()`.
Le JavaScript plantait avant l'appel LLM.

## Correctif

- `_guestCount` est maintenant une variable globale visio.
- Elle est réinitialisée à `0` au démarrage Daily.
- Le payload utilise un garde-fou :

```js
(typeof _guestCount === 'number' ? _guestCount : 0) + 1
```

## À ne pas confondre

- `tabs:outgoing.message.ready` : bruit extension navigateur / DevTools, pas Luna.
- `ScriptProcessorNode deprecated` : dette technique V2 AudioWorklet, pas bloquant.
- `vad_getusermedia_fallback` : attendu si Daily ne fournit pas sa piste locale ; le micro fallback fonctionne si `vad_track ... muted=false`.

## Test attendu

Après déploiement :

```text
vad_transcribed ...
llm_start
llm_http 200
tts_http 200
time_to_first_audio_ms ...
audio_play_start
```
