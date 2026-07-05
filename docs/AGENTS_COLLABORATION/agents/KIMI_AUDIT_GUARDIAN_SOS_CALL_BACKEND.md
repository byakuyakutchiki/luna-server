# Audit backend — appel vocal manquant sur SOS Guardian

**Agent** : Kimi Code CLI  
**Date** : 2026-07-05  
**Révision déployée en trace** : `luna-beta-00984-zew`  
**Branche** : `fix/guardian-voice-context-on-stable-ui`  
**Statut** : audit terminé, patch backend identifié, redéploiement trace 0 % requis.

---

## 1. Symptôme terrain (Ludovic)

Test sur `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian` :

- ✅ Contexte vocal capturé.
- ✅ Compte à rebours OK.
- ✅ SMS reçu après countdown.
- ✅ Pas de doublon constaté.
- ❌ **Aucun appel reçu.**

Erreur Sentry :

```
SOS call failed for +33658477952:
'TwilioVoiceClient' object has no attribute 'initiate_announcement_call'
Route : POST /api/guardian/sos/{session_id}
```

---

## 2. Diagnostic

### 2.1 Où `/api/guardian/sos/{session_id}` appelle-t-il les appels ?

Dans `luna_web.py`, lignes ~15590–15620 :

```python
_call_on = os.getenv("GUARDIAN_CALL_ENABLED", "true").lower() in ("1", "true", "yes")
if _call_on and contacts and voice_client and getattr(voice_client, "is_configured", False):
    ...
    for _c in contacts:
        _phone = ...
        if _test_mode:
            logger.info(f"[GUARDIAN_CALL test] appel simulé → {_phone}")
            call_results["placed"] += 1
            continue
        try:
            _ok, _cd = await asyncio.to_thread(voice_client.initiate_announcement_call, _phone, _call_msg)
            call_results["placed" if _ok else "failed"] += 1
        except Exception as _e:
            call_results["failed"] += 1
            logger.error(f"SOS call failed for {_phone}: {_e}")
```

### 2.2 Quelle classe définit `TwilioVoiceClient` ?

`integrations/twilio/voice_client.py`, classe `TwilioVoiceClient`.

### 2.3 Quelles méthodes existent dans le repo local ?

Dans le **working tree** (fichier modifié mais non commité) :

- `initiate_call(self, to)` — l. 99
- `initiate_call_async(self, to)` — l. 153
- `initiate_announcement_call(self, to, message)` — l. 171
- `get_call_status(self, call_sid)` — l. 218
- `make_call_to(self, to, twiml_url)` — l. 251
- `make_call_to_async(self, to, twiml_url)` — l. 273
- `terminate_call(self, call_sid)` / `terminate_call_async(...)` — l. 317

### 2.4 Quelles méthodes existent dans le commit déployé ?

Dans le commit `6638062` (révision `luna-beta-00984-zew`) :

```bash
git show 6638062:integrations/twilio/voice_client.py | grep -n "def "
```

Résultat :

```
99:    def initiate_call(self, to: str) -> Tuple[bool, Dict[str, Any]]:
153:    async def initiate_call_async(self, to: str) -> Tuple[bool, Dict[str, Any]]:
166:    def generate_twiml(self, call_sid: str = "") -> str:
251:    def make_call_to(self, to: str, twiml_url: str) -> Tuple[bool, Dict[str, Any]]:
273:    async def make_call_to_async(self, to: str, twiml_url: str) -> Tuple[bool, Dict[str, Any]]:
317:    async def terminate_call_async(self, call_sid: str) -> bool:
```

**Conclusion** : `initiate_announcement_call` et `get_call_status` sont **absents** du commit déployé, mais présents dans le working tree non commité.

### 2.5 Pourquoi l'erreur Sentry ?

Le déploiement `luna-beta-00984-zew` a été construit avec `git archive 6638062`. Seuls les fichiers du commit ont été empaquetés. Les modifications non commitées du working tree (dont `voice_client.py`) ont été ignorées.

`luna_web.py` dans le commit appelle `voice_client.initiate_announcement_call(...)`, mais le `voice_client.py` du même commit ne définit pas cette méthode. D'où l'erreur.

### 2.6 Comparaison avec les commits récents

Recherche dans l'historique :

```bash
git log --all --oneline -S "initiate_announcement_call" -- integrations/twilio/voice_client.py
```

Résultat : **aucun commit** n'a introducé cette méthode dans `voice_client.py`.

La méthode a été ajoutée manuellement dans le working tree (probablement lors de la stabilisation production), mais n'a jamais été commitée dans Git. `luna_web.py` l'utilise pourtant depuis le commit `7407b84` (`feat(guardian): adresse precise dans SMS SOS via reverse geocoding`).

### 2.7 Preuve que la méthode fonctionnait en production

`docs/GUARDIAN_AUDIT_RAPPORT_2026-07-04.md` (ligne 192) contient :

```
WARNING:integrations.twilio.voice_client:[EMERGENCY CALL] lancé sid=... -> +33658477952 status=queued
```

Cela prouve que la méthode `initiate_announcement_call` a fonctionné en production. Elle est donc correcte.

---

## 3. Patch minimal backend proposé

### 3.1 Fichier à modifier

| Fichier | Modification |
|---|---|
| `integrations/twilio/voice_client.py` | Ajouter `initiate_announcement_call` et `get_call_status` (contenu déjà présent dans le working tree) |

Aucune modification de :
- `static/guardian.html`
- `static/index.html`
- `static/salon.html`
- `static/simli.html`
- `luna_web.py`
- `core/guardian/engine.py`

### 3.2 Contenu du patch

Ajouter dans `TwilioVoiceClient`, après `initiate_call_async` et avant `generate_twiml` :

```python
    # ===================================================================
    # APPEL D'URGENCE — annonce directe (TwiML <Say>), robuste
    # ===================================================================
    def initiate_announcement_call(self, to: str, message: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Appel d'URGENCE robuste : Twilio appelle le destinataire et ANNONCE directement
        un message vocal (TwiML <Say> inline, répété), SANS media-stream conversationnel.
        """
        from integrations.twilio.sms_client import TwilioSMSClient
        to_normalized = TwilioSMSClient.normalize_phone(to)

        # Mode test : ne JAMAIS appeler réellement
        try:
            if get_settings().foundation_test_mode:
                logger.info(f"[SIMULATE][EMERGENCY CALL] -> {to_normalized} : {message[:90]}")
                return True, {"simulated": True, "call_sid": "SIM_ANN_" + os.urandom(3).hex(), "to": to_normalized, "status": "simulated"}
        except Exception:
            pass

        if not all([self.account_sid, self.auth_token, self.from_number]):
            return False, {"error": "Twilio non configuré (SID/token/numéro)"}

        from twilio.twiml.voice_response import VoiceResponse
        vr = VoiceResponse()
        vr.pause(length=1)
        for _ in range(2):
            vr.say(message, voice="alice", language="fr-FR")
            vr.pause(length=1)
        twiml_str = str(vr)

        try:
            call = self.client.calls.create(
                to=to_normalized,
                from_=self.from_number,
                twiml=twiml_str,
                timeout=30,
            )
            logger.warning(f"[EMERGENCY CALL] lancé sid={call.sid} -> {to_normalized} status={call.status}")
            return True, {"call_sid": call.sid, "status": call.status, "to": to_normalized}
        except Exception as e:
            logger.error(f"[EMERGENCY CALL] échec vers {to_normalized}: [{getattr(e,'code',0)}] {e}")
            return False, {"error": str(e), "code": getattr(e, "code", 0)}

    def get_call_status(self, call_sid: str) -> str:
        """Statut réel d'un appel Twilio."""
        if not call_sid or str(call_sid).startswith("SIM"):
            return "simulated"
        try:
            return self.client.calls(call_sid).fetch().status
        except Exception as e:
            return f"error:{e}"
```

### 3.3 Pourquoi aussi `get_call_status` ?

`luna_web.py` l'utilise (ligne ~18793) :

```python
st = await asyncio.to_thread(voice_client.get_call_status, sid)
```

Sans cette méthode, une autre erreur `AttributeError` surviendrait plus tard.

---

## 4. Tests dry-run / Sentry / logs

### 4.1 Test dry-run local

Le mode test est activé par `foundation_test_mode`. Dans ce mode, `initiate_announcement_call` retourne un appel simulé sans appeler Twilio.

### 4.2 Logs attendus après patch

Avec `GUARDIAN_CALL_ENABLED=true` et mode réel :

```
WARNING:integrations.twilio.voice_client:[EMERGENCY CALL] lancé sid=... -> +33658477952 status=queued
```

En mode test (`_test_mode`) :

```
INFO:luna_web:[GUARDIAN_CALL test] appel simulé → +33658477952
```

### 4.3 Sentry

Aucune erreur `AttributeError` sur `initiate_announcement_call` ne doit plus apparaître.

---

## 5. Plan de déploiement

1. **Commiter** le patch sur `fix/guardian-voice-context-on-stable-ui`.
2. **Redéployer** en trace 0 % avec la même procédure que précédemment.
3. **Tester** à nouveau sur `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian`.
4. **Valider** que l'appel est bien reçu.
5. Sur validation Ludovic, **promouvoir** la révision trace à 100 %.

---

## 6. Leçon

Le déploiement précédent a utilisé `git archive 6638062`, qui n'a pas embarqué les modifications non commitées du working tree. Désormais, tout patch backend doit être commité avant déploiement, même en trace 0 %.
