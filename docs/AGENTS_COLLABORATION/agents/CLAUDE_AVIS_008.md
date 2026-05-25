# Claude — Avis Objectif 008

**Date** : 2026-05-25  
**Objectif** : Correction voix OpenAI Realtime  
**Rôle** : Lead technique — diagnostic, proposition, implémentation (après validation)

---

## Ce que j'ai trouvé (audit lecture seule)

### Problème 1 — Modèle déprécié (CAUSE PRINCIPALE)

`web_voice_bridge.py` ligne 32 :
```python
OPENAI_REALTIME_MODEL = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17")
```

Le modèle figé `gpt-4o-realtime-preview-2024-12-17` est très probablement déprécié en mai 2026.
OpenAI envoie un événement `error` puis ferme le WebSocket immédiatement après réception de `session.update`.

Log observé dans Cloud Run :
```
16:47:23  WebVoice: OpenAI Realtime connected
16:47:25  WARNING: WebVoice: OpenAI WS closed during send
```

Le délai de ~2 secondes correspond au temps entre la connexion et l'envoi de `session.update`.

---

### Problème 2 — `run()` ne vérifie pas l'échec de `_configure_session()`

`run()` (ligne 179) :
```python
await self._configure_session()

self._start_time = _time.time()
self._timer_task = asyncio.create_task(self._duration_timer())
self._keepalive_task = asyncio.create_task(self._client_keepalive())
self._elapsed_task = asyncio.create_task(self._elapsed_broadcaster())
```

Même si `_configure_session()` appelle `_ws_send_openai()` qui échoue et pose `self._running = False`,
`run()` continue. Il crée tous les tasks, puis démarre les relay tasks. Celles-ci sortent immédiatement
(boucle sur `self._running`), mais le client ne reçoit jamais de message d'erreur clair.

---

### Problème 3 — `_configure_session()` ne lit pas `session.created` avant d'envoyer `session.update`

`_configure_session()` (lignes 335-358) envoie directement `session.update` sans lire le premier
événement OpenAI.

Or, OpenAI envoie un événement `session.created` immédiatement après la connexion WebSocket.
Si le modèle est invalide, OpenAI envoie d'abord un `error` avant de fermer.

Comme `_relay_openai_to_client()` n'est pas encore démarré à ce stade, ces événements sont soit
perdus (consommés par la boucle après coup), soit la connexion est déjà fermée quand les relay
tasks démarrent.

**Conséquence** : on ne peut pas détecter que le modèle est rejeté AVANT d'avoir envoyé `session.update`.

---

### Problème 4 — Logs trompeurs (inconditionnels)

`_configure_session()` ligne 358 :
```python
await self._ws_send_openai(session_config)
logger.info(f"WebVoice: session configured (pcm16, voice={self.voice}, server_vad)")
```

`_send_greeting()` ligne 372 :
```python
await self._ws_send_openai({"type": "response.create"})
logger.info("WebVoice: greeting sent")
```

Les deux logs s'exécutent INCONDITIONNELLEMENT, même si `_ws_send_openai()` a retourné `False`.
C'est pourquoi les logs Cloud Run montrent "session configured" et "greeting sent" juste après
"OpenAI WS closed during send" — ces logs sont des faux positifs.

---

## Ce que je propose (corrections minimales — 3 fichiers)

### Correction A — `.env` Cloud Run : modèle Realtime (CRITIQUE, 1 ligne)

```
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
```

(Alias stable, pas de version figée.)

**Risque** : Zéro — variable d'environnement lue au démarrage du processus.
Si l'alias ne fonctionne pas non plus (quota différent), le log le montrera clairement.

---

### Correction B — `web_voice_bridge.py` : lire `session.created` + vérification dans `run()`

#### Dans `_configure_session()` (ligne 335) :

```python
async def _configure_session(self) -> bool:
    # Lire l'événement initial avant d'envoyer session.update
    try:
        raw = await asyncio.wait_for(self.ws_openai.recv(), timeout=5.0)
        first = json.loads(raw)
        first_type = first.get("type", "?")
        if first_type == "error":
            err = first.get("error", {})
            logger.error(f"WebVoice: OpenAI error before session.update: {err}")
            self._running = False
            await self._ws_send_client({
                "type": "error",
                "message": "Service vocal temporairement indisponible.",
            })
            return False
        logger.info(f"WebVoice: OpenAI initial event: {first_type}")
    except asyncio.TimeoutError:
        logger.warning("WebVoice: pas d'événement initial OpenAI (timeout 5s) — on continue")
    except Exception as e:
        logger.warning(f"WebVoice: lecture event initial: {e}")

    session_config = { "type": "session.update", "session": { ... } }  # inchangé
    ok = await self._ws_send_openai(session_config)
    if ok:
        logger.info(f"WebVoice: session configured (pcm16, voice={self.voice}, server_vad)")
    return ok
```

#### Dans `run()` (après ligne 179) :

```python
ok = await self._configure_session()
if not ok or not self._running:
    # run() se termine, le finally block nettoie
    return
```

#### Dans `_send_greeting()` (ligne 360) :

```python
async def _send_greeting(self):
    ok1 = await self._ws_send_openai(greeting_event)
    ok2 = await self._ws_send_openai({"type": "response.create"})
    if ok1 and ok2:
        logger.info("WebVoice: greeting sent")
    else:
        logger.warning("WebVoice: greeting send failed")
```

---

## Risque

| Correction | Régression possible |
|---|---|
| A — modèle .env | Aucune. Variable d'environnement, ne touche pas au code. |
| B — lecture session.created | Très faible. On consomme un événement informationnel. Si OpenAI ne l'envoie pas dans 5s, on continue normalement (warning dans les logs). |
| B — check `_running` dans `run()` | Aucune. Shortcircuit propre, le `finally` nettoie. |
| B — logs conditionnels | Aucune. On retire des faux positifs, pas de vraie information. |

---

## Ce que je ne touche pas

- Architecture générale du bridge (relay tasks, keepalive, tool handler)
- `_relay_openai_to_client()` — déjà gère `session.created` ligne 427
- Quotas, routes `/api/voice/*`, APK — zéro régression garantie
- `OPENAI_API_KEY` — non modifiée

---

## Décision à valider (oui/non suffit)

**Ludovic, valides-tu :**

1. ✅ La correction A : mise à jour `OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview` dans `.env` Cloud Run ?
2. ✅ La correction B : lecture `session.created` + check `_running` + logs conditionnels dans `web_voice_bridge.py` ?

Si oui à 1 + 2 → j'implémente, je fais une PR sur branche dédiée, et je déploie sur Cloud Run.
Si oui à 1 seulement → je modifie uniquement la variable `.env` (via gcloud), pas de code.

**Critère de succès** : Log Cloud Run montre `session.created` → `session configured` → `greeting sent`
sans `WARNING: OpenAI WS closed during send`, puis `response.audio.delta` apparaît.

---

## Prochaine étape pour les autres agents

| Agent | Tâche |
|---|---|
| **DeepSeek** | Auditer `_configure_session()` et `_relay_openai_to_client()` — confirmer qu'aucun autre point ne peut fermer le WS prématurément |
| **Kimi** | Textes cockpit : "Service vocal indisponible", "Quota vocal épuisé", "Bridge fermé pendant session.update" |
| **Codex** | Synthèse : la correction modèle suffit-elle seule ? `voice_token_missing` design decision |
| **Cursor** | Non-régression UI — vérifier que les labels `_VOICE_EVENT_LABELS` couvrent les nouveaux scénarios |
