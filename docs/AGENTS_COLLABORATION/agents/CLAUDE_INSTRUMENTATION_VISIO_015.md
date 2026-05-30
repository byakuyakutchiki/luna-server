# Claude — Instrumentation visio temps réel — Objectif 015

Agent : Claude  
Date : 2026-05-31  
Statut : instrumentation ajoutée + analyse code — pas de déploiement  
Référence : `OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`

---

## 1. Analyse : piste audio locale publiée ?

### État du code

Après mon patch (`luna-beta-00465-6wh`), Daily.js est initialisé via `DailyIframe.wrap(existingIframe)` sur un `<iframe id="dailyIframe">` pré-existant avec `allow="camera; microphone; autoplay; ..."` posé avant `join()`.

`join()` est appelé avec `startAudioOff: false` → Daily demande le micro.

### Ce qu'on ne savait pas jusqu'ici

Le code ne vérifiait jamais l'état réel de la piste audio locale après `joined-meeting`. Il pouvait y avoir :
- `playable` → micro actif et publié ✅
- `interrupted` → micro coupé par le navigateur
- `blocked` → permission refusée
- `absent` → micro non initialisé

### Sonde ajoutée

```javascript
// 1s après joined-meeting
var local = dailyCall.participants().local;
var aState = local.tracks.audio.state;
rLog('info', 'simli', 'probe_local_audio', aState);
```

**Log attendu en console** : `[INFO][simli] probe_local_audio = "playable"` si micro OK.  
Si `"blocked"` → race condition ou permission refusée → STT mort confirmé.

---

## 2. Analyse : piste audio bot reçue ?

### Ce qu'on ne savait pas

Le bot Simli rejoint la room (event `bot_joined` loggué), mais on ne vérifiait pas si sa piste audio était dans l'état `playable`. Si la piste audio bot est `absent` ou `off`, on ne peut pas entendre Iris — même si ElevenLabs fonctionne.

### Sonde ajoutée

```javascript
// 2s après bot_joined
var bot = dailyCall.participants()[_simliBotId];
var aState = bot.tracks.audio.state;
rLog('info', 'simli', 'probe_bot_audio', aState);
```

**Log attendu** : `[INFO][simli] probe_bot_audio = "playable"` si Iris peut parler.

---

## 3. Analyse : `conversation.utterance` reçu ?

### Ce que le code fait déjà

Le handler `app-message` logguait TOUS les types d'événements sauf `conversation.tool_call` et `conversation.echo`. Un event de type `conversation.utterance` serait loggué comme :
`[INFO][simli] app_msg_conversation_utterance = {...}`

### Sonde ajoutée

En plus du log générique, on loggue maintenant explicitement :

```javascript
if (props.role === 'user') {
  rLog('info', 'simli', 'stt_user_utterance', props.text.substring(0, 60));
}
```

**Log attendu** : `[INFO][simli] stt_user_utterance = "tu m'entends ?"` si Simli comprend Ludovic.  
**Si absent** → STT ne transmet pas au LLM → boucle conversationnelle cassée.

---

## 4. Analyse : mesure de latence

### Sonde ajoutée

```javascript
if (props.role === 'user') { _userSpeechTs = Date.now(); }
else if (props.role === 'assistant' && _userSpeechTs) {
  rLog('info', 'simli', 'latency_ms', String(Date.now() - _userSpeechTs));
}
```

**Log attendu** : `[INFO][simli] latency_ms = 3200` (ms entre fin utterance user et début réponse assistant).  
Acceptable : < 4000ms. Mauvais : > 6000ms.

---

## 5. Analyse : tracks démarrés / stoppés

### Sondes ajoutées

```javascript
dailyCall.on('track-started', function(e) {
  var who = e.participant.local ? 'local' : (bot ? 'bot' : 'guest');
  rLog('info', 'simli', 'track_started', who + ':' + e.track.kind);
});
dailyCall.on('track-stopped', function(e) {
  rLog('info', 'simli', 'track_stopped', who + ':' + e.track.kind);
});
```

**Logs attendus en séquence** :
```
track_started local:audio
track_started local:video
track_started bot:audio
track_started bot:video
```

Si `track_started bot:audio` est absent → le bot ne publie aucune piste audio → silence côté Iris.

---

## 6. Analyse : distorsion image / avatar

### Cause A identifiée — CSS `min()` overridé par Daily.js

Mon patch CSS :
```css
#tavusFrame iframe {
  width: min(100vw, calc(100vh * 9 / 16));
  height: min(100vh, calc(100vw * 16 / 9));
}
```

**Problème** : Daily.js injecte ses propres styles inline sur l'iframe via `iframeStyle` ou via son SDK. Ces styles inline (`style="width:100%;height:100%"`) ont priorité sur les règles CSS. Le `min()` est ignoré.

**Preuve à vérifier** : dans DevTools → inspecter l'élément `#dailyIframe` → onglet Computed → voir si `width`/`height` viennent d'un `style=""` inline.

### Cause B identifiée — ratio Simli avatar inconnu

Le ratio de la vidéo bot Simli dépend du `faceId` utilisé (`b9e5fba3...`). Si Simli génère un flux 1:1 (carré) et qu'on contrainte à 9:16, l'avatar est comprimé horizontalement. Si Simli génère du 16:9 et qu'on est en portrait, c'est étiré.

**On ne connaît pas le ratio natif de ce faceId.**

### Patch CSS corrigé (niveau 1 — à tester en local)

Forcer via `!important` pour passer au-dessus du style inline de Daily.js :

```css
#tavusFrame {
  position: fixed; inset: 0; z-index: 20;
  display: flex; align-items: center; justify-content: center;
  background: #000;
  opacity: 0; transition: opacity 1.5s ease; pointer-events: none;
}
#tavusFrame.visible { opacity: 1; pointer-events: auto; }
#tavusFrame iframe {
  border: none !important;
  /* Ratio portrait 9:16 — à ajuster si le faceId Simli est 16:9 */
  width: min(100vw, calc(100vh * 9 / 16)) !important;
  height: min(100vh, calc(100vw * 16 / 9)) !important;
}
```

**Alternative** : passer `iframeStyle` correct dans `DailyIframe.wrap()` (si supporté par la version Daily.js chargée).

---

## 7. Problème critique identifié : `DailyIframe.wrap()` et version Daily.js

### Risque

Le code tombe en fallback `createFrame()` si `window.DailyIframe.wrap` n'existe pas. La version de Daily.js chargée depuis `https://unpkg.com/@daily-co/daily-js` (sans version fixe) peut être n'importe quelle release.

`DailyIframe.wrap()` existe depuis Daily.js v0.9.x. Si une version antérieure est chargée → fallback `createFrame` → le `allow` est posé synchronement juste après (correction dans mon code) → devrait fonctionner aussi.

**Sonde pour vérifier** : en console navigateur :
```javascript
console.log(window.DailyIframe && window.DailyIframe.version);
console.log(typeof window.DailyIframe.wrap);
```

---

## 8. Récapitulatif des logs à collecter (test < 30s)

Demander à Ludovic d'ouvrir la console (F12) avant de lancer la visio et de chercher :

| Log attendu | Signification |
|---|---|
| `probe_local_audio = "playable"` | Micro de Ludovic actif ✅ |
| `probe_local_audio = "blocked"` | Micro bloqué → STT mort ❌ |
| `bot_joined` | Bot Simli dans la room |
| `probe_bot_audio = "playable"` | Bot peut parler ✅ |
| `track_started local:audio` | Piste audio locale démarrée |
| `track_started bot:audio` | Piste audio bot démarrée |
| `stt_user_utterance = "..."` | Simli a compris Ludovic ✅ |
| `latency_ms = XXXX` | Latence user→réponse en ms |
| `daily_error` ou `daily_cam_error` | Erreur Daily |

---

## 9. Ce qui reste à valider (non déployé, non testé)

| Patch | Statut | Niveau |
|---|---|---|
| Instrumentation rLog sondes | ✅ Dans le code — à déployer | 2 (validation Ludo) |
| CSS `!important` ratio iframe | ❌ Non appliqué — ratio Simli inconnu | 1 puis 2 |
| Vérifier version Daily.js | ❌ Non vérifié | 0 (console navigateur) |
| Voix FR native | ❌ Non testé — attendre Kimi | 2 |

---

## 10. Prochaine action recommandée

**Étape 1** — Déployer cette instrumentation (Ludovic valide).  
**Étape 2** — Ludovic teste une visio < 30s et envoie les logs console.  
**Étape 3** — Les logs disent si le micro est capturé, si le bot publie audio, si STT fonctionne.  
**Étape 4** — Sur la base des logs, Claude propose le patch ciblé exact.

Sans ces logs, tout nouveau patch est au hasard.
