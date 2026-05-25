# Claude — Avis Objectif 007

**Date** : 2026-05-25  
**Objectif** : Télémétrie vocale précise APK  
**Rôle** : Lead technique — diagnostic, implémentation, déploiement

---

## Cause du problème identifiée

### Bug 1 — session_ts = 0 pour les premiers événements (CRITIQUE)

Dans `sendApkEvent()` (objectif 005), le champ `session_ts` utilisait `_voiceStartTime` :
```javascript
session_ts: _voiceStartTime ? Math.floor(_voiceStartTime / 1000) : 0,
```

`_voiceStartTime` n'est défini qu'à l'intérieur de `startVoice()`. Donc quand
`voice_button_clicked` était envoyé (avant l'appel à `startVoice()`), `session_ts = 0`.

En Python, `0` est falsy. L'ancien code avait :
```python
sid = ev.get("session_ts") or ev.get("ts") or "unknown"
```
→ `0 or ev.get("ts")` → chaque événement avec `session_ts=0` tombait dans sa propre
micro-session identifiée par son `ts` individuel.

La "dernière session" retournée par `max()` était celle avec le ts individuel le plus élevé,
soit `voice_session_ended` (dernier événement chronologiquement).

**Résultat** : seul `voice_session_ended` apparaissait dans le cockpit — les 9 événements
antérieurs étaient dans des micro-sessions distinctes, jamais affichées.

### Bug 2 — plafond _apkEventCount trop bas

`_apkEventCount >= 10` bloquait à 10 événements alors que 21 sont nécessaires.

---

## Fix appliqué

### index.html

**1. Nouveau timestamp de session** :
```javascript
var _voiceSessionStartTs = 0;
// Fixé au moment du clic, avant tout sendApkEvent
_voiceSessionStartTs = Date.now();
// Utilisé par tous les événements : session_ts: Math.floor(_voiceSessionStartTs/1000)
// Réinitialisé à 0 APRÈS voice_session_ended dans stopVoice()
```

**2. Plafond porté à 30** :
```javascript
if (_apkEventCount >= 30) return;
```

**3. 19 événements instrumentés** (ordre chronologique) :
- `voice_click_received` — clic reçu
- `voice_token_missing` / `voice_token_present` — token vérifié au clic
- `voice_start_entered` — entrée dans startVoice()
- `voice_state_blocked` — voiceActive déjà true
- `voice_micro_request_started` — avant getUserMedia
- `voice_micro_permission_granted` — getUserMedia OK
- `voice_micro_permission_denied` — getUserMedia échoue
- `voice_capture_started` — audio capture active
- `voice_ws_create_started` — avant new WebSocket()
- `voice_ws_create_failed` — exception constructor WebSocket
- `voice_ws_opened` — onopen
- `voice_first_audio_chunk_sent` — premier chunk audio envoyé
- `voice_first_audio_chunk_received` — premier chunk audio reçu
- `voice_playback_started` — lecture démarrée
- `voice_no_audio_after_timeout` — timer 20s
- `voice_ws_closed` — onclose
- `voice_ws_error` — onerror
- `voice_session_ended` — stopVoice()

### luna_web.py

- `_VOICE_EVENTS_ALLOWED` : 21 nouveaux + 5 anciens (rétrocompat)
- `_VOICE_EVENT_LABELS` : 28 labels français
- `_analyze_voice_events` : fix groupement session_ts (`0` falsy → `str(raw_sid)` conditionnel)
  + nouveaux scénarios : `token_missing`, `state_blocked`, `ws_create_failed`

---

## Test de validation

Session simulée envoyée avec `session_ts=1779727369` → 6 événements :
```
voice_click_received, voice_token_present, voice_start_entered,
voice_micro_request_started, voice_micro_permission_denied, voice_session_ended
```

Résultat API :
```
STATUS: mic_denied
SUMMARY: Bouton appuyé — mais la permission microphone n'a pas été accordée
6 événements groupés dans la même session
```

**Le regroupement par session_ts fonctionne.** ✅

---

## Déploiement

- Commit : `01ac7a5` (main)
- Révision Cloud Run : `luna-beta-00439-7v9`
- Statut : **actif et servi à 100%**

---

## Prochaine étape pour les agents

| Agent | Tâche |
|---|---|
| **DeepSeek** | Auditer static/index.html sur main — vérifier les injections, l'ordre des événements, et si d'autres chemins (4574, 6978, 6984) peuvent déclencher startVoice sans passer par le handler click instrumenté |
| **Kimi** | Rédiger les textes `luna_knows/guesses/recommends/cannot` pour les 8 scénarios de l'objectif 007 |
| **Cursor** | Vérifier UI mobile et non-régression du bouton vocal sur petit écran |
| **Codex** | Confirmer les critères de validation + rédiger CODEX_AVIS_007.md |
| **Ludovic** | Tester sur téléphone réel — appuyer sur le bouton vocal et copier le résultat du cockpit |

---

## Interdictions maintenues

- Pas de correction voix fonctionnelle avant chronologie suffisante
- Pas de déploiement sans validation Ludovic
- Pas d'audio brut, transcript, position
- Pas de rebuild APK pour cette phase
