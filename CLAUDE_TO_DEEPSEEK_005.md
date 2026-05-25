# Claude → DeepSeek — Briefing Objectif 005

**Date** : 2026-05-25
**Objectif** : Événements voix APK — prouver ce qui se passe quand Ludovic appuie sur le bouton vocal

---

## Ce que Claude a déjà implémenté (côté serveur + JS)

### Côté serveur — `luna_web.py`

| Élément | Statut |
|---|---|
| `POST /api/apk/event` | ✅ implémenté |
| Whitelist 10 événements | ✅ (seuls les événements listés ci-dessous sont acceptés) |
| Auth JWT (luna_token) | ✅ via `_verify_jwt()` |
| Filtrage champs payload | ✅ seuls les champs autorisés sont stockés |
| Redis `luna:apk:voice:events` | ✅ max 50 entrées, TTL 24h |
| `_analyze_voice_events()` | ✅ diagnostic par session |
| `GET /api/admin/apk-voice-events` | ✅ endpoint fondateur |

### Côté JS — `static/index.html`

#### Variables ajoutées (ligne ~7277 dans le fichier final)
```javascript
var _apkEventCount = 0;
var _voiceNoAudioTimer = null;
var _voiceFirstAudioSent = false;
var _voiceFirstAudioReceived = false;
```

#### Fonction `sendApkEvent()` ajoutée (ligne ~7279)
```javascript
function sendApkEvent(eventName, extra) {
  if (_apkEventCount >= 10) return;
  _apkEventCount++;
  var tok = typeof getToken === "function" ? getToken() : null;
  if (!tok) return;
  var payload = { event: eventName, ts: Math.floor(Date.now() / 1000),
    session_ts: _voiceStartTime ? Math.floor(_voiceStartTime / 1000) : 0,
    apk_version: "2.8", screen: "home" };
  if (extra) Object.keys(extra).forEach(function(k) { payload[k] = extra[k]; });
  fetch("/api/apk/event", { method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": "Bearer " + tok },
    body: JSON.stringify(payload) }).catch(function() {});
}
```

#### Points d'injection réalisés

| Événement | Où (repère dans le code) | Ce qui est injecté |
|---|---|---|
| `voice_button_clicked` | Click handler de `voiceBtn` | Reset compteurs + envoi |
| `microphone_permission_granted` | Après `getUserMedia` success | `sendApkEvent("microphone_permission_granted")` |
| `microphone_permission_denied` | Catch block, si `err.name === "NotAllowedError"` | `sendApkEvent("microphone_permission_denied", ...)` |
| `voice_ws_opened` | Début de `voiceWs.onopen` | `sendApkEvent("voice_ws_opened")` + démarrage timer 20s |
| `voice_audio_sent` | ScriptProcessor `onaudioprocess` ET worklet `port.onmessage` (first time) | `sendApkEvent("voice_audio_sent")` |
| `voice_audio_received` | `onmessage` quand `data.type === "audio"` (first time) | Clear timer + `sendApkEvent("voice_audio_received")` |
| `voice_no_audio_after_timeout` | `setTimeout(20000)` démarré dans `onopen` | Envoi si `_voiceFirstAudioReceived === false` |
| `voice_ws_closed` | Début de `voiceWs.onclose` | `sendApkEvent("voice_ws_closed", {ws_close_code: evt.code})` |
| `voice_ws_error` | Début de `voiceWs.onerror` | `sendApkEvent("voice_ws_error")` |
| `voice_session_ended` | Dans `stopVoice()` avant `voiceWs.close()` | `sendApkEvent("voice_session_ended")` |

---

## Ce que DeepSeek doit faire

### Tâche principale : vérification de l'implémentation dans `static/index.html`

**Branche à créer** : `ds/objectif-005-events-voix`

1. Lire `static/index.html` — chercher `sendApkEvent` pour localiser tous les points d'injection.
2. Vérifier que `_voiceFirstAudioSent` est correctement réinitialisé à `false` dans le click handler (non dans `startVoice()` pour éviter les réinitialisations sur reconnexion).
3. Vérifier que le timer `_voiceNoAudioTimer` est bien annulé dans `onclose` ET dans `stopVoice()` — pas seulement dans `onopen`.
4. Vérifier que `sendApkEvent("voice_audio_sent")` est bien injecté aux **deux** endroits :
   - ScriptProcessor : dans `scriptNode.onaudioprocess`, avant `voiceWs.send()`
   - AudioWorklet : dans `workletNode.port.onmessage`, avant `voiceWs.send()`
5. Vérifier que `_apkEventCount = 0` est bien réinitialisé dans le **click handler** (pas dans `startVoice()` pour éviter reset sur reconnexion).
6. Proposer dans `ds/objectif-005-events-voix` les corrections ou confirmations dans `agents/DEEPSEEK_AVIS_005.md`.

### Format attendu de `agents/DEEPSEEK_AVIS_005.md`

```markdown
# DeepSeek — Avis Objectif 005

**Date** : 2026-05-25

## Vérifications startVoice()

| Point d'injection | Ligne | Présent ? | Correctement placé ? | Risque ? |
|---|---|---|---|---|
| voice_button_clicked | XXX | oui/non | oui/non | — |
| ... | ... | ... | ... | ... |

## Corrections nécessaires

[Si rien à corriger : "Aucune correction nécessaire — implémentation conforme."]

## Risques de régression identifiés

[Liste ou "Aucun risque identifié."]

## Tests proposés (sans téléphone)

[grep ou lecture statique pour valider]

## Validation Ludovic requise ?

oui / non
```

### Ce que DeepSeek ne doit PAS faire

- Ne pas modifier `luna_web.py`
- Ne pas modifier `MainActivity.java`
- Ne pas corriger la voix elle-même — seulement les événements de monitoring
- Ne pas envoyer d'audio brut, transcript ou position dans les événements
- Ne pas déployer sur Cloud Run

---

## Contexte général

Le bug réel : Ludovic appuie sur le bouton vocal dans l'APK, attend 15-20 secondes, n'entend rien.
Le cockpit doit pouvoir dire : "Bouton appuyé, micro OK, WebSocket ouvert — mais aucun audio reçu après 20s."

L'implémentation JS est déjà en place côté serveur et JS. DeepSeek confirme que les injections sont correctes et propose des corrections si nécessaire.

**Important** : L'objectif 004 (heartbeat APK) n'est pas encore confirmé sur téléphone réel — l'APK doit être rebuildée. Le déploiement de l'objectif 005 attendra la confirmation de Ludovic après le premier heartbeat réel.
