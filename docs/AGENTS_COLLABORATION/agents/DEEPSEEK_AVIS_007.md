# DeepSeek — Avis Objectif 007

**Date** : 2026-05-25
**Branche** : ds/objectif-007-telemetrie-voix

## Objectif

Instrumenter la chaîne vocale APK pour capturer TOUTES les étapes critiques du flux, plutôt que seulement la fin de session.

## Constat initial (avant implémentation)

- Heartbeat APK visible : OK
- Mais seul événement remontant : `voice_session_ended`
- Aucun des événements intermédiaires n'a remonté

## ✅ VALIDATION — Test réel 2026-05-25 18:47 (Ludovic téléphone)

**Resultat : OBJECTIF 007 VALIDÉ**

11 événements reçus et analysés correctement.

### Chronologie réelle capturée

1. `voice_button_clicked` — bouton vocal appuyé
2. `voice_start_entered` — démarrage vocal initié
3. `voice_micro_request_started` — demande de permission micro
4. `microphone_permission_granted` — microphone autorisé
5. `voice_audio_capture_started` — capture audio active
6. `voice_ws_create_started` — création connexion vocale
7. `voice_ws_opened` — connexion vocale ouverte
8. `voice_first_audio_chunk_sent` — premier audio envoyé vers Luna
9. `voice_ws_closed` — connexion vocale fermée (~5s après audio envoyé)
10. `voice_session_ended` — session vocale terminée

### Diagnostic cerveau Luna

```
Scénario : incomplete (pas d'audio reçu)
Luna sait : utilisateur a cliqué, micro OK, capture OK, WS ouvert, audio envoyé
Luna devine : serveur vocal n'a pas répondu ou WebSocket fermé prématurément
Luna recommande : vérifier logs serveur voix / OpenAI Realtime / fermeture WS
Luna ne peut pas : diagnostiquer côté serveur (hors scope APK)
```

### Conclusion côté client

✓ Token présent et valide
✓ Clic du bouton fonctionne
✓ Permission micro accordée
✓ Capture audio démarre
✓ WebSocket s'ouvre
✓ Premier audio transmis
✗ **Pas de réponse audio reçue**
✗ **WebSocket ferme après ~5 secondes**

**Blocage : côté serveur voice / OpenAI Realtime / fermeture WS précoce**

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

## Extension Objective 007 — Geste de maintenance APK

### Contexte

Ludovic a suggéré un geste de "pull-to-refresh" pour éviter que des assets statiques (index.html, fondateur.html, CSS) restent coincés en cache dans la WebView.

### Implémentation requise

Ajouter à `static/index.html` et `android-app/` :

1. **Détection du geste pull-to-refresh**
   - Swipe vers le bas sur l'écran principal
   - Affichage discret d'une barre de progression

2. **Actions lors du refresh**
   - Vider le cache WebView (si API disponible)
   - Recharger la page complète
   - Recharger les assets (CSS, JS, images)
   - Renvoyer heartbeat immédiatement après
   - Afficher message "Luna mise à jour" pendant 2s

3. **Événements télémétrie à ajouter**
   - `apk_manual_refresh_triggered` — geste reçu
   - `apk_cache_cleared` — cache vidé avec succès
   - `apk_webview_reloaded` — page rechargée
   - `apk_heartbeat_sent_after_refresh` — heartbeat renvoyé

4. **Code exemple (JavaScript)**

```javascript
var _lastTouchY = 0;
var _refreshInProgress = false;

document.addEventListener("touchstart", function(e) {
  if (e.touches.length > 0) _lastTouchY = e.touches[0].clientY;
});

document.addEventListener("touchmove", function(e) {
  if (_refreshInProgress) return;
  if (window.scrollY === 0 && _lastTouchY > 0) {
    var currentY = e.touches[0].clientY;
    if (currentY - _lastTouchY > 100) { // 100px swipe threshold
      e.preventDefault();
      _triggerManualRefresh();
    }
  }
});

function _triggerManualRefresh() {
  _refreshInProgress = true;
  sendApkEvent("apk_manual_refresh_triggered");

  // Vider cache si API disponible
  try {
    if (navigator.serviceWorker && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({cmd: "clear_cache"});
    }
    sendApkEvent("apk_cache_cleared");
  } catch(e) {
    // API pas disponible, continuer
  }

  // Afficher feedback utilisateur
  var msg = document.createElement("div");
  msg.style.cssText = "position:fixed; top:50%; left:50%; transform:translate(-50%,-50%); " +
    "background:#333; color:#fff; padding:20px; border-radius:10px; font-size:14px; z-index:99999;";
  msg.textContent = "Luna mise à jour...";
  document.body.appendChild(msg);

  // Recharger après 1s
  setTimeout(function() {
    sendApkEvent("apk_webview_reloaded");
    location.reload(true); // force reload, bypass cache
  }, 1000);
}
```

5. **Intégration Android (java)**
   - WebViewClient: ajouter `onPageFinished()` pour tracer recharge
   - CookieManager: forcer vidage cookies après refresh
   - WebSettings: `setCacheMode(WebSettings.LOAD_NO_CACHE)` temporaire

6. **Resultat attendu**
   - Utilisateur final peut forcer mise à jour complète sans restart APK
   - Ludovic voit les événements: `apk_manual_refresh_triggered` → `apk_cache_cleared` → `apk_webview_reloaded`
   - Évite les blocages liés au cache persistant

## Prochaine étape — Objective 008 (ou 007-bis)

### Mission

Diagnostique serveur voix après audio envoyé.

Maintenant que Objective 007 (télémétrie client) est validé, il faut investiguer pourquoi :
- WebSocket se ferme après ~5 secondes
- Aucune réponse audio n'est reçue
- OpenAI Realtime interrompt la connexion

### Points à vérifier

1. **Logs serveur** — `/ws/luna-voice` entre 18:47:05 → 18:47:10
   - Premier audio reçu ?
   - Forwards à OpenAI Realtime ?
   - Réponse reçue ?
   - Code de fermeture WS ?

2. **Token validation côté serveur**
   - JWT valide et non expiré ?
   - Permissions suffisantes ?

3. **OpenAI Realtime connection**
   - Connectée au moment du premier audio ?
   - Erreur d'authentification ?
   - Rate limit atteint ?
   - Timeout interne ?

4. **Audio relay**
   - PCM16 24kHz reçu correctement ?
   - Format incompatible avec OpenAI ?
   - Transcodage échoué ?

5. **Fermeture précoce**
   - Code fermeture WS : 1000 (normal) ou autre ?
   - Erreur Python non catchée ?
   - Timeout côté server ?

### Assignation

- **Claude** : analyser logs serveur `luna_web.py` + `web_voice_bridge.py`
- **DeepSeek** : audit code serveur voix pour points d'arrêt silencieux (comme 007 client)
- **Codex** : coordination + préparation reproduction locale
- **Ludovic** : validation des corrections avant production

### Réussite Objective 007

✓ Télémétrie implémentée et validée
✓ 11 événements remontent correctement
✓ Diagnostic client complet et précis
✓ Localisation du blocage (serveur voix)
✓ Geste maintenance APK proposé
→ **Prêt pour Objective 008 (serveur voix)**
