# DeepSeek — Avis Objectif 007

**Date** : 2026-05-25
**Branche** : ds/objectif-007-telemetrie-voix

## Objectif

Instrumenter la chaîne vocale APK pour capturer TOUTES les étapes critiques du flux, plutôt que seulement la fin de session.

## Constat du test réel Ludovic (Objectif 006)

- Heartbeat APK visible : OK
- Mais seul événement remontant : `voice_session_ended`
- Aucun des événements intermédiaires n'a remonté

## Analyse technique

### Problème principal identifié

Fonction `sendApkEvent()` ligne 7273 contient une faille silencieuse :

```javascript
function sendApkEvent(eventName, extra) {
  if (_apkEventCount >= 10) return;   // Limite OK
  _apkEventCount++;                    // PROBLÈME 1 : incrément AVANT vérification token
  var tok = typeof getToken === "function" ? getToken() : null;
  if (!tok) return;                   // PROBLÈME 2 : sort silencieusement si token absent
  // ... fetch send
}
```

**Conséquence détectée :**
- Si le token n'est pas présent lors des PREMIERS appels `sendApkEvent()` (ex: `voice_button_clicked`, `voice_ws_opened`, `voice_audio_sent`, etc.), l'événement est **silencieusement ignoré** mais le compteur `_apkEventCount` est quand même incrémenté.
- Après 10 appels à `sendApkEvent()` sans token valide, le compteur atteint 10 et bloque TOUS les événements suivants.
- `voice_session_ended` dans `stopVoice()` est appelé EN DERNIER. Si le token devient valide entre-temps, cet événement SEUL remonte.

### Événements actuellement présents (lignes confirmées)

| Événement | Ligne | Présence | Problème |
|---|---:|---|---|
| `voice_button_clicked` | 7865 | ✓ | Dépend du token au moment du clic |
| `microphone_permission_granted` | 7601 | ✓ | Seulement si `getUserMedia` succeed |
| `microphone_permission_denied` | 7794 | ✓ | Seulement si erreur `NotAllowedError` |
| `voice_ws_opened` | 7662 | ✓ | Dépend du token + WS création réussie |
| `voice_audio_sent` | 7642, 7701 | ✓ | Seulement 1x (guard `_voiceFirstAudioSent`) |
| `voice_audio_received` | 7710 | ✓ | Seulement 1x + clear timer |
| `voice_no_audio_after_timeout` | 7666 | ✓ | Après 20s si no audio |
| `voice_ws_closed` | 7756 | ✓ | Seulement si WS effectivement ouvert |
| `voice_ws_error` | 7787 | ✓ | Seulement si erreur |
| `voice_session_ended` | 7837 | ✓ | Appelé dans `stopVoice()` |

### Événements MANQUANTS pour tracer la chaîne complète

Pour Objective 007, ajouter ces points de capture pour identifier précisément où le flux bloque :

1. **`voice_click_received`** → aussitôt après le clic du bouton HTML (ligne 7861)
   - avant toute vérification d'état
   - permet de savoir si le clic a bien atteint le JS

2. **`voice_start_entered`** → ligne 7577 (entrée de `startVoice()`)
   - trace l'entrée dans la fonction

3. **`voice_token_check_failed`** → nouvelle injection
   - si `getToken()` retourne vide/null
   - avant toute autre action

4. **`voice_state_blocked`** → ligne 7578 (vérification `if (voiceActive && !isReconnect)`)
   - si une session est déjà active

5. **`voice_screen_blocked`** → ligne 7580 (vérification écran visible)
   - si appContainer pas visible ou worldActive

6. **`voice_micro_request_started`** → ligne 7595 (avant `getUserMedia`)
   - capture le début de la demande de permission

7. **`voice_micro_list_failed`** → si `getUserMedia` échoue
   - capture les différents codes d'erreur

8. **`voice_context_creation_failed`** → si création AudioContext échoue
   - si l'audio API n'est pas disponible

9. **`voice_ws_create_started`** → ligne 7653 (avant création WebSocket)
   - trace la tentative de création WS

10. **`voice_ws_create_failed`** → si `new WebSocket()` génère une erreur
    - si l'URL est invalide ou WebSocket API absent

11. **`voice_ws_open_timeout`** → si WS n'ouvre jamais après 10s
    - complément au `onopen`

12. **`voice_audio_capture_started`** → après que ScriptProcessor/AudioWorklet soit configuré
    - indique que la chaîne audio est prête

13. **`voice_first_audio_send_failed`** → si le premier `voiceWs.send()` échoue
    - capture les erreurs d'envoi

14. **`voice_playback_started`** → ligne 7720 (avant `_queueAudio()`)
    - trace le début du playback

15. **`voice_playback_failed`** → si `_queueAudio()` ou speaker échoue
    - capture les erreurs de restitution audio

## Propositions de corrections minimales

### Correction 1 : Vérifier le token très tôt

Ligne 7861, dans le click handler, ajouter :

```javascript
voiceBtn.addEventListener("click", function() {
  // NEW: trace clic reçu AVANT vérification token
  sendApkEvent("voice_click_received");

  // NEW: vérifier token présence immédiatement
  if (!getToken()) {
    sendApkEvent("voice_token_check_failed", {reason: "getToken_empty"});
    return; // Stopper là si pas de token
  }

  _apkEventCount = 0;
  _voiceFirstAudioSent = false;
  _voiceFirstAudioReceived = false;
  sendApkEvent("voice_button_clicked");
  startVoice(false);
});
```

### Correction 2 : Incrémenter le compteur APRÈS vérification token

Dans `sendApkEvent()`, ligne 7275, déplacer l'incrément :

```javascript
function sendApkEvent(eventName, extra) {
  var tok = typeof getToken === "function" ? getToken() : null;
  if (!tok) return;  // Vérifier AVANT incrément
  if (_apkEventCount >= 10) return;
  _apkEventCount++;  // Incrémenter APRÈS vérification
  // ... rest
}
```

### Correction 3 : Ajouter des traces pour état bloquant dans `startVoice()`

Ligne 7577, ajouter au début :

```javascript
async function startVoice(isReconnect) {
  sendApkEvent("voice_start_entered", {isReconnect: isReconnect});

  if (voiceActive && !isReconnect) {
    sendApkEvent("voice_state_blocked", {reason: "already_active"});
    stopVoice();
    return;
  }

  var app = document.getElementById("appContainer");
  var worldActive = document.getElementById("tab-world") && document.getElementById("tab-world").classList.contains("active");
  if (!app || window.getComputedStyle(app).display === "none" || !getToken() || worldActive) {
    sendApkEvent("voice_screen_blocked", {
      app_visible: app && window.getComputedStyle(app).display !== "none",
      token_present: !!getToken(),
      world_active: worldActive
    });
    return;
  }
  // ... rest
}
```

### Correction 4 : Trace getUserMedia

Ligne 7595, ajouter :

```javascript
sendApkEvent("voice_micro_request_started");
try {
  micStream = await navigator.mediaDevices.getUserMedia({...});
  sendApkEvent("microphone_permission_granted");
} catch(err) {
  sendApkEvent("voice_micro_list_failed", {error_name: err.name});
  // ... handle error
}
```

### Correction 5 : Trace WebSocket création

Ligne 7653, ajouter :

```javascript
sendApkEvent("voice_ws_create_started", {url_host: location.host});
try {
  voiceWs = new WebSocket(wsUrl);
} catch(err) {
  sendApkEvent("voice_ws_create_failed", {error: err.toString().slice(0, 100)});
  // ... handle
}
```

### Correction 6 : Trace premier audio capturé

Ligne 7642 / 7701, avant `if (!_voiceFirstAudioSent)`, ajouter :

```javascript
if (!_voiceFirstAudioSent && voiceWs && voiceWs.readyState === 1) {
  _voiceFirstAudioSent = true;
  sendApkEvent("voice_first_audio_chunk_sent");
  try {
    voiceWs.send(JSON.stringify({ type: "audio", audio: _int16ToBase64(...) }));
  } catch(e) {
    sendApkEvent("voice_first_audio_send_failed", {error: e.toString().slice(0, 100)});
  }
}
```

### Correction 7 : Tracer le timeout de WS

Ligne 7662, après `voiceWs.onopen`, ajouter un timeout :

```javascript
var _wsOpenTimer = setTimeout(function() {
  if (voiceWs && voiceWs.readyState !== 1) {
    sendApkEvent("voice_ws_open_timeout", {elapsed_ms: 10000});
  }
}, 10000);
// ... dans onopen :
voiceWs.onopen = function() {
  clearTimeout(_wsOpenTimer);
  sendApkEvent("voice_ws_opened");
  // ... rest
};
```

## Chronologie attendue après implémentation (scénario succès)

1. `voice_click_received` (clic du bouton)
2. `voice_button_clicked` (validation token + réinitialisation)
3. `voice_start_entered` (entrée startVoice)
4. `voice_micro_request_started` (début demande permission)
5. `microphone_permission_granted` (permission OK)
6. `voice_ws_create_started` (création WS)
7. `voice_ws_opened` (WS connecté)
8. `voice_first_audio_chunk_sent` (premier chunk mic envoyé)
9. `voice_first_audio_chunk_received` (premier chunk réponse reçu)
10. `voice_playback_started` (audio joué)
11. `voice_session_ended` (fin session)

## Chronologie attendue (scénario erreur token absent)

1. `voice_click_received` (clic du bouton)
2. `voice_token_check_failed` (token absent)
3. (Stop ici — no autre événement)

## Chronologie attendue (scénario micro refusé)

1. `voice_click_received`
2. `voice_button_clicked`
3. `voice_start_entered`
4. `voice_micro_request_started`
5. `voice_micro_list_failed` (error: NotAllowedError)
6. `voice_session_ended`

## Validation Ludovic requise ?

Oui — cette télémétrie doit être testée sur téléphone réel avant diagnostic final.
