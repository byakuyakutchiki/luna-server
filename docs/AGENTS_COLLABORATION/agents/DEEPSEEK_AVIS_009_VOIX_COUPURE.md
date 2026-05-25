# DeepSeek Avis 009 — Diagnostic de coupures audio Luna

**Date** : 2026-05-25  
**Objectif** : 009 — Stabilité voix Luna  
**Auteur** : DeepSeek (agent diagnostic temps réel)  
**Mission** : Analyser télémétrie APK et définir seuils incident "voice_cut_mid_response"

---

## Synthèse

La voix Luna fonctionne (gpt-realtime-mini confirmé en test réel), mais se coupe prématurément pendant les réponses. DeepSeek propose :

1. **Définition du problème** : Incident "voice_cut_mid_response" détecté quand playback audio commence puis s'arrête < 10s après
2. **Format telémétrie APK** : JSON structuré pour détecter et diagnostiquer ce scénario
3. **Seuils déclenchement** : Trois scénarios types (client timeout, serveur timeout, interruption VAD)
4. **Diagnostics par scénario** : Actions recommandées pour chaque cas

---

## 1. Analyse code `startVoice()` — Chronologie événements

### Flux normal (cas de succès)

```
1. voice_button_clicked
2. getUserMedia() → microphone_permission_granted
3. voiceWs = new WebSocket(...) 
4. voiceWs.onopen → voice_ws_opened
5. voiceWs.send(audio) → voice_audio_sent (first audio chunk)
   [_voiceFirstAudioSent = true — protège envoi dupliqué]
6. voiceWs.onmessage({type:"audio"}) → voice_audio_received (first chunk from server)
   [Clearing _voiceNoAudioTimer (20s timeout)]
   [_setStatus("Luna parle...", "speak")]
7. voiceWs.onmessage({type:"audio_done"}) → Luna finit réponse
   [_setStatus("Luna ecoute...", "listen")]
8. stopVoice() → voice_session_ended
9. voiceWs.onclose → voice_ws_closed
```

### Flux coupure audio (cas d'erreur)

```
1-6. [identique à flux normal]
7. ⚠️ WebSocket se ferme AVANT audio_done
   voiceWs.onclose({code: ???}) → voice_ws_closed
   [pas de audio_done reçu]
8. stopVoice() → voice_session_ended (via timeout 3000ms ou manuel)
```

### Détection de coupure

```
Coupure détectée si :
  - voice_audio_received reçu (première audio : ✅)
  - voice_ws_closed reçu AVANT audio_done (❌)
  - Temps écoulé entre audio_received et ws_closed < 10 secondes
```

---

## 2. Événements APK actuels

Définis dans `luna_web.py:20265-20275` (`_VOICE_EVENTS_ALLOWED`) :

```
voice_button_clicked          — Utilisateur appuie sur le bouton
microphone_permission_granted — Permission micro accordée
microphone_permission_denied  — Permission micro refusée (NotAllowedError)
voice_ws_opened               — WebSocket ouvert
voice_audio_sent              — Premier audio envoyé (guard: _voiceFirstAudioSent)
voice_audio_received          — Premier audio reçu du serveur (clears 20s timer)
voice_no_audio_after_timeout  — Timer 20s sans audio reçu
voice_ws_closed               — WebSocket fermé {ws_close_code: N}
voice_ws_error                — Erreur WebSocket
voice_session_ended           — Session terminée (stopVoice() appelé)
```

---

## 3. Seuils et conditions de coupure audio

### Scénario A : Coupure client rapide (1-3s après playback start)

**Indicateurs** :
- `voice_audio_received` reçu ✅
- `voice_ws_closed` avec code **1001** (Going Away) ou **1006** (Abnormal Closure)
- Temps écoulé : 1-3 secondes
- `voice_no_audio_after_timeout` **ABSENT** (audio a bien commencé)

**Cause probable** :
- WebView JavaScript interrompu (blocage du thread ou mémoire)
- APK perdue focus (notification, appel téléphonique)
- Client timeout interne (mais < 20s, donc pas 20s timer)

**Diagnostic DeepSeek** :
```json
{
  "incident_type": "voice_cut_mid_response",
  "scenario": "client_early_disconnect",
  "time_since_playback_start_ms": 2500,
  "ws_close_code": 1006,
  "probable_cause": "client_thread_blocked_or_lost_focus",
  "deepseek_observation": "Le serveur envoyait l'audio, mais le client WebSocket s'est fermé prématurément",
  "recommendation": "Vérifier l'historique logcats APK pour erreurs JS ou perte de focus"
}
```

---

### Scénario B : Coupure serveur modérée (5-10s après playback start)

**Indicateurs** :
- `voice_audio_received` reçu ✅
- `voice_ws_closed` avec code **1000** (Normal Closure) ou **1011** (Server Error)
- Temps écoulé : 5-10 secondes
- Pas de `audio_done` reçu

**Cause probable** :
- Timeout OpenAI Realtime session (peut-être 30s par session ?)
- Erreur OpenAI non-catchée qui ferme le stream
- Client idle counter atteint le seuil dans web_voice_bridge.py (300s global, mais peut être aussi par session)
- VAD (Voice Activity Detection) a interprété fin de voix utilisateur → OpenAI généré réponse courte → stream fermé

**Diagnostic DeepSeek** :
```json
{
  "incident_type": "voice_cut_mid_response",
  "scenario": "server_session_timeout_or_vad_interrupt",
  "time_since_playback_start_ms": 7500,
  "ws_close_code": 1000,
  "probable_cause": "openai_response_timeout_or_vad_early_interrupt",
  "deepseek_observation": "Le serveur a fermé la session de manière propre (1000), mais avant la fin du message. Possiblement timeout OpenAI ou VAD a arrêté la génération",
  "recommendation": "Claude à lire logs serveur au moment exact du test pour vérifier OpenAI state + VAD activity"
}
```

---

### Scénario C : Coupure tardive (30s+, normal mais potentiellement lié à duration max)

**Indicateurs** :
- `voice_audio_received` reçu ✅
- `voice_ws_closed` avec code **1000**
- Temps écoulé : 30+ secondes (proche du max_duration serveur)
- `audio_done` reçu avant la coupure (probablement)

**Cause probable** :
- Max duration atteint (serveur ferme session normalement après 300s = 5min)
- Comportement normal, pas un problème — réponse complète avant coupure

**Diagnostic DeepSeek** :
```json
{
  "incident_type": "voice_session_normal_end",
  "scenario": "max_duration_reached_or_natural_end",
  "time_since_playback_start_ms": 45000,
  "ws_close_code": 1000,
  "probable_cause": "session_ended_naturally_or_duration_limit",
  "deepseek_observation": "La session s'est fermée de manière propre après suffisamment de temps pour une réponse complète",
  "recommendation": "Vérifier si le message a été complètement joué. Si oui, comportement normal. Si non, c'est une coupure réelle."
}
```

---

## 4. Format JSON telémétrie pour incident detection

### Structure complète du diagnostic

```json
{
  "timestamp": "2026-05-25T19:47:15+02:00",
  "session_id": "uuid-session-vocal",
  "tenant_id": "1",
  "apk_version": "2.8",
  "screen": "voice-overlay",
  "incident_type": "voice_cut_mid_response",
  "scenario": "server_session_timeout_or_vad_interrupt",
  
  "event_sequence": [
    {
      "event": "voice_button_clicked",
      "timestamp_ms": 0,
      "extra": {}
    },
    {
      "event": "microphone_permission_granted",
      "timestamp_ms": 145,
      "extra": {}
    },
    {
      "event": "voice_ws_opened",
      "timestamp_ms": 620,
      "extra": {}
    },
    {
      "event": "voice_audio_sent",
      "timestamp_ms": 890,
      "extra": {
        "first_audio_sent": true
      }
    },
    {
      "event": "voice_audio_received",
      "timestamp_ms": 3450,
      "extra": {
        "first_audio_received": true,
        "time_to_first_audio_ms": 2560
      }
    },
    {
      "event": "voice_ws_closed",
      "timestamp_ms": 7820,
      "extra": {
        "ws_close_code": 1000,
        "time_since_playback_ms": 4370
      }
    },
    {
      "event": "voice_session_ended",
      "timestamp_ms": 8100,
      "extra": {}
    }
  ],
  
  "metrics": {
    "time_button_to_permission_ms": 145,
    "time_button_to_ws_open_ms": 620,
    "time_button_to_first_audio_sent_ms": 890,
    "time_button_to_first_audio_received_ms": 3450,
    "time_button_to_ws_closed_ms": 7820,
    "time_playback_start_to_ws_closed_ms": 4370,
    "time_audio_sent_to_audio_received_ms": 2560,
    "ws_close_code": 1000,
    "session_duration_ms": 8100
  },
  
  "diagnosis": {
    "incident_detected": true,
    "incident_type": "voice_cut_mid_response",
    "scenario": "server_session_timeout_or_vad_interrupt",
    "severity": "high",
    "probable_cause": "openai_response_timeout_or_vad_early_interrupt",
    "deepseek_observation": "Premier audio reçu et playback commencé, mais WebSocket fermé après ~4s. Pas de audio_done reçu. Possiblement OpenAI a arrêté la génération prématurément.",
    "points_to_investigate": [
      "OpenAI Realtime VAD settings (silence_duration_ms: 500 peut-il être trop court ?)",
      "OpenAI session timeout après réponse générée (avant tous les delta audio envoyés)",
      "Erreur OpenAI non-loggée qui ferme le stream"
    ],
    "recommendation": "Claude à lire logs serveur au moment exact (19:47:15 ±2min) pour OpenAI state + error logs + VAD activity"
  }
}
```

---

## 5. Déploiement DeepSeek — Format telémétrie compacte

Pour stockage Redis + affichage cockpit, utiliser format compact :

```json
{
  "ts": "2026-05-25T19:47:15Z",
  "incident": "voice_cut_mid_response",
  "scenario": "server_timeout_or_vad",
  "severity": "high",
  "time_to_cut_ms": 4370,
  "ws_code": 1000,
  "cause": "openai_response_timeout_or_vad",
  "deepseek_note": "Playback 4.3s puis ws ferme. Pas audio_done.",
  "next_step": "Claude logs"
}
```

Stockage Redis :
```
luna:{tenant_id}:voice:incidents -> LPUSH + LTRIM 20 + EXPIRE 86400
```

Affichage cockpit admin :
```
GET /api/admin/voice-incidents?tenant_id=1&limit=10
→ Retourne liste des 10 derniers incidents avec diagnostics DeepSeek
```

---

## 6. Code côté APK pour enrichir telémétrie

Ajouter dans `static/index.html` après `voice_audio_received` :

```javascript
// Track playback start time
var _voicePlaybackStartTime = 0;

// Existing code: voiceWs.onmessage for {type:"audio"}
if (data.type === "audio") {
  if (!_voiceFirstAudioReceived) {
    _voiceFirstAudioReceived = true;
    _voicePlaybackStartTime = Date.now();  // ← NEW
    if (_voiceNoAudioTimer) { clearTimeout(_voiceNoAudioTimer); _voiceNoAudioTimer = null; }
    sendApkEvent("voice_audio_received");
  }
  _queueAudio(data.audio);
  _setStatus("Luna parle...", "speak");
}

// Existing code: voiceWs.onclose
voiceWs.onclose = function(evt) {
  // NEW: Si playback avait commencé, enregistrer le temps de coupure
  var timeSincePlayback = _voicePlaybackStartTime > 0 ? Date.now() - _voicePlaybackStartTime : -1;
  sendApkEvent("voice_ws_closed", {
    ws_close_code: evt.code || 0,
    time_since_playback_start_ms: timeSincePlayback,  // ← NEW
    audio_received: _voiceFirstAudioReceived          // ← NEW (pour détecter play cut)
  });
  // ... rest of onclose handler
}
```

---

## 7. Seuils déclenchement DeepSeek Monitoring

```python
# En pseudo-code pour deployment

VOICE_CUT_THRESHOLDS = {
    "client_early_disconnect": {
        "min_ms": 1000,
        "max_ms": 3000,
        "ws_close_codes": [1001, 1006],
        "severity": "warning"
    },
    "server_timeout_or_vad": {
        "min_ms": 5000,
        "max_ms": 10000,
        "ws_close_codes": [1000, 1011],
        "severity": "high"
    },
    "normal_end": {
        "min_ms": 30000,
        "ws_close_codes": [1000],
        "severity": "ok"
    }
}

def classify_voice_incident(time_since_playback_ms, ws_code):
    """Retourne scenario et severity"""
    for scenario, thresholds in VOICE_CUT_THRESHOLDS.items():
        if (thresholds["min_ms"] <= time_since_playback_ms <= thresholds["max_ms"]
            and ws_code in thresholds["ws_close_codes"]):
            return scenario, thresholds["severity"]
    return "unknown", "warning"
```

---

## 8. Points clés pour Claude

1. **À lire dans les logs serveur** (heure exacte de Ludovic ±2min) :
   - Timestamp `/ws/luna-voice` créée
   - Timestamp WebSocket fermée
   - Code fermeture (1000, 1001, 1006, 1011, etc.)
   - Erreurs OpenAI : status code, message
   - VAD events (si loggés)

2. **À vérifier** :
   - OpenAI Realtime VAD timeout (silence_duration_ms: 500)
   - OpenAI session max duration (30s ?)
   - Error threshold dans web_voice_bridge (_MAX_OPENAI_ERRORS = 15)
   - Client idle timeout (300s, donc pas applicable pour coupures 5-10s)

3. **À ne pas oublier** :
   - La coupure arrive APRÈS audio_received (donc l'infrastructure client→serveur fonctionne)
   - Le problème est probablement serveur-side ou OpenAI Realtime-side
   - VAD peut interrompre si elle croit que l'utilisateur a fini de parler

---

## 9. Prochaines étapes — Coordination

| Étape | Responsable | Entrée | Sortie |
|---|---|---|---|
| Test réel + heure | **Ludovic** | — | Heure exacte + comportement |
| Logs serveur | **Claude** | Heure exacte | Cause probable + ws_code + OpenAI state |
| Télémétrie APK | **DeepSeek** | Événements APK | Seuils déclenchement incident |
| Textes cockpit | **Kimi** | Diagnostics | Messages clairs pour founder |
| UI vérification | **Cursor** | Cockpit | États vocaux corrects |
| Synthèse | **Codex** | Tous les avis | Prêt pour Claude corriger |

---

## 10. Résumé DeepSeek

✅ **Défini** : Scénario "voice_cut_mid_response" (playback commence puis s'arrête < 10s après)  
✅ **Défini** : Trois cas types (client rapide 1-3s, serveur modéré 5-10s, normal 30s+)  
✅ **Défini** : Format JSON telémétrie avec metrics et diagnosis  
✅ **Défini** : Thresholds déclenchement incident par scénario  
✅ **Prêt** : Code APK pour enrichir `voice_ws_closed` avec `time_since_playback_start_ms`  

🔄 **Attente** : Logs serveur de Claude au moment exact test Ludovic  
🔄 **Attente** : Correction proposée par Claude (1-3 lignes max)  
🔄 **Attente** : Validation Ludovic avant déploiement  

**Status** : DeepSeek diagnostics ready. Claude lead can now investigate logs.
