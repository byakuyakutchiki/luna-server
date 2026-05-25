# DeepSeek — Avis Objectif 005

**Date** : 2026-05-25

## Résumé rapide

Audit effectué sur `static/index.html` dans la branche locale `ds/objectif-005-events-voix`.
Constat principal : la base du monitoring vocal existe, mais la collecte d’événements APK `sendApkEvent()` n’est pas présente dans le code actuel.

---

## Vérifications `startVoice()`

| Point d'injection | Lignes observées | Présent ? | Correctement placé ? | Commentaire / Risque |
|---|---:|---:|---:|---|
| `voiceBtn` click handler | 7818 | oui | oui | `voiceBtn.addEventListener("click", function() { startVoice(false); });` existe, mais pas de reset d’état ni d’événement APK. |
| déclaration `var _apkEventCount` | N/A | non | non | aucune déclaration observée dans `static/index.html`. |
| déclaration `var _voiceNoAudioTimer` | N/A | non | non | aucune déclaration observée dans `static/index.html`. |
| déclaration `_voiceFirstAudioSent` / `_voiceFirstAudioReceived` | N/A | non | non | aucune déclaration observée. |
| fonction `sendApkEvent(eventName, extra)` | N/A | non | non | pas de définition dans `static/index.html`. |
| `voiceWs.onopen` | 7640 | oui | partiel | `voiceWs.onopen` existe, mais aucun timer 20s et aucun envoi d’événement APK. |
| `voice_audio_sent` ScriptProcessor | 7610 | oui | partiel | `scriptNode.onaudioprocess` envoie l’audio, mais pas de `sendApkEvent` sur le premier chunk. |
| `voice_audio_sent` AudioWorklet port.onmessage | 7668 | oui | partiel | `workletNode.port.onmessage` envoie l’audio, mais pas de `sendApkEvent` sur le premier chunk. |
| `voice_audio_received` | 7654 | oui | partiel | `data.type === "audio"` est géré, mais pas de `sendApkEvent` ni de clear timer. |
| `voiceWs.onclose` | 7718 | oui | partiel | `voiceWs.onclose` existe, mais aucun clear timer ni événement APK. |
| `stopVoice()` | 7795 | oui | partiel | `stopVoice()` nettoie bien les ressources, mais n’annule pas de timer lié à un timeout de silence et n’envoie pas d’événement APK. |

## Constat clé

Le bug réel peut actuellement être détecté, mais le code ne remonte pas suffisamment d’événements :
- il n’y a pas de `sendApkEvent` dans `static/index.html`
- il n’y a pas de timer silence 20s associé à un événement `voice_no_audio_after_timeout`
- les états `audio_sent` / `audio_received` ne sont pas tracés vers le serveur
- aucune métrique `voice_button_clicked` n’est envoyée au démarrage de la session vocale

Cela signifie que le cockpit ne peut pas encore prouver que la panne voix se produit après le bouton, après ouverture du WS, et sans audio entrant.

## Corrections nécessaires

1. Ajouter en haut du scope vocal :

```javascript
var _apkEventCount = 0;
var _voiceNoAudioTimer = null;
var _voiceFirstAudioSent = false;
var _voiceFirstAudioReceived = false;
```

2. Ajouter `sendApkEvent()` :

```javascript
function sendApkEvent(eventName, extra) {
  if (typeof _apkEventCount === 'undefined') _apkEventCount = 0;
  if (_apkEventCount >= 10) return;
  _apkEventCount++;
  var tok = typeof getToken === 'function' ? getToken() : null;
  if (!tok) return;
  var payload = {
    event: eventName,
    ts: Math.floor(Date.now() / 1000),
    session_ts: _voiceStartTime ? Math.floor(_voiceStartTime / 1000) : 0,
    screen: 'home'
  };
  if (extra) Object.keys(extra).forEach(function(k) { payload[k] = extra[k]; });
  try {
    fetch('/api/apk/event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + tok
      },
      body: JSON.stringify(payload)
    });
  } catch(e) {}
}
```

3. Dans le click handler du bouton vocal :
- `_apkEventCount = 0;`
- `_voiceFirstAudioSent = false;`
- `_voiceFirstAudioReceived = false;`
- `sendApkEvent('voice_button_clicked');`

4. Dans `voiceWs.onopen` :
- `sendApkEvent('voice_ws_opened');`
- démarrer `_voiceNoAudioTimer = setTimeout(function() { if (!_voiceFirstAudioReceived) sendApkEvent('voice_no_audio_after_timeout'); }, 20000);`

5. Dans `workletNode.port.onmessage` et `scriptNode.onaudioprocess` :
- au premier package audio envoyé, si `_voiceFirstAudioSent === false` :
  - `_voiceFirstAudioSent = true;`
  - `sendApkEvent('voice_audio_sent');`

6. Dans `voiceWs.onmessage` pour `data.type === 'audio'` :
- si `_voiceFirstAudioReceived === false` :
  - `_voiceFirstAudioReceived = true;`
  - `clearTimeout(_voiceNoAudioTimer);`
  - `sendApkEvent('voice_audio_received');`

7. Dans `voiceWs.onclose` et `stopVoice()` :
- `if (_voiceNoAudioTimer) { clearTimeout(_voiceNoAudioTimer); _voiceNoAudioTimer = null; }`
- `sendApkEvent('voice_ws_closed', { ws_close_code: evt.code });` dans `onclose`

## Risques de régression identifiés

- La collecte d’événements ajoute du trafic réseau côté APK ; limiter à 10 événements par session est juste.
- Si le reset d’état est fait après `startVoice(false)` ou dans `startVoice()` plutôt que dans le click handler, la logique de reconnexion peut réinitialiser les compteurs au mauvais moment.
- `getToken()` peut être absent dans certains contextes ; `sendApkEvent` doit échouer silencieusement.

## Tests proposés (sans téléphone)

- Grep statique : `grep -n "sendApkEvent" static/index.html` doit être vide aujourd’hui, puis contenir les points d’injection après correction.
- Vérifier la présence des variables : `_apkEventCount`, `_voiceNoAudioTimer`, `_voiceFirstAudioSent`, `_voiceFirstAudioReceived`.
- Vérifier les handlers : `voiceWs.onopen`, `scriptNode.onaudioprocess`, `workletNode.port.onmessage`, `voiceWs.onmessage`, `voiceWs.onclose`, `stopVoice()`.
- Simulation JS possible : mock `voiceWs` et `fetch`, appeler `startVoice()` et valider l’ordre des appels.

## Validation Ludovic requise ?

Oui — le code doit être vérifié sur APK réel avant toute correction fonctionnelle du circuit voix.

---

## Conclusion DeepSeek

Le monitoring n’est pas encore actif dans le fichier actuel. Je recommande de livrer d’abord l’instrumentation `sendApkEvent` et le timer silence 20s, puis de retester sur téléphone.

Ensuite, DeepSeek pourra confirmer que le cockpit voit bien la panne voix réelle et fournir un diagnostic précis.
