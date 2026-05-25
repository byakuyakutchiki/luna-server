# DeepSeek — Avis Objectif 005

**Date** : 2026-05-25

## Résumé rapide

J'ai lu le briefing `CLAUDE_TO_DEEPSEEK_005.md`. Je confirme la branche locale `ds/objectif-005-events-voix` est créée.
Le travail consiste à vérifier les points d'injection JS autour de `startVoice()` et le timer 20s, et proposer corrections si nécessaire.

---

## Vérifications `startVoice()`

| Point d'injection | Ligne repère | Présent ? | Correctement placé ? | Commentaire / Risque |
|---|---:|---:|---:|---|
| `voice_button_clicked` (reset `_apkEventCount`) | ? | non trouvé | non | `sendApkEvent` et reset absent de `static/index.html`. Doit être ajouté dans le click handler du bouton `voiceBtn`.
| déclaration `var _apkEventCount` | ? | non trouvé | non | variable non trouvée dans `static/index.html` (présente uniquement dans `CLAUDE_TO_DEEPSEEK_005.md`), ajouter en tête du bloc vocal.
| déclaration `var _voiceNoAudioTimer` | ? | non trouvé | non | idem, doit exister et être géré.
| déclaration `_voiceFirstAudioSent` / `_voiceFirstAudioReceived` | ? | non trouvé | non | idem.
| fonction `sendApkEvent(eventName, extra)` | ? | non trouvé | non | Absente du `static/index.html` actuel — nécessaire pour appeler `/api/apk/event`.
| `voice_ws_opened` (démarrage timer 20s) | dans `voiceWs.onopen` | partie `onopen` présente | timer non trouvé | Ajouter `sendApkEvent("voice_ws_opened")` et `clear/setTimeout` ici.
| `voice_audio_sent` (ScriptProcessor) | dans `onaudioprocess` | `onaudioprocess` existe | `sendApkEvent` absent | Injecter `voice_audio_sent` lors du premier envoi audio.
| `voice_audio_sent` (AudioWorklet port.onmessage) | worklet handler | worklet port handler présent | `sendApkEvent` absent | idem.
| `voice_audio_received` (onmessage data.type === 'audio') | in `voiceWs.onmessage` | `audio` handling exists | `sendApkEvent` absent | ajout : clear timer + send event.
| annulation timer `_voiceNoAudioTimer` dans `onclose` et `stopVoice()` | `voiceWs.onclose` + `stopVoice()` | `onclose` and `stopVoice` present | timer cancel not present | ensure `clearTimeout(_voiceNoAudioTimer)` in both locations.


## Corrections nécessaires (proposition)

1. Ajouter en haut du scope vocal (dans le bloc JS global du overlay) :

```javascript
var _apkEventCount = 0;
var _voiceNoAudioTimer = null;
var _voiceFirstAudioSent = false;
var _voiceFirstAudioReceived = false;
```

2. Implémenter `sendApkEvent()` (compact, sans secrets) :

```javascript
function sendApkEvent(eventName, extra) {
  if (typeof _apkEventCount === 'undefined') _apkEventCount = 0;
  if (_apkEventCount >= 10) return;
  _apkEventCount++;
  var tok = typeof getToken === 'function' ? getToken() : null;
  if (!tok) return;
  var payload = { event: eventName, ts: Math.floor(Date.now()/1000), session_ts: _voiceStartTime ? Math.floor(_voiceStartTime/1000) : 0, apk_version: "2.8", screen: "home" };
  if (extra) Object.keys(extra).forEach(function(k){ payload[k]=extra[k]; });
  try { fetch('/api/apk/event', { method:'POST', headers:{'Content-Type':'application/json','Authorization':'Bearer '+tok}, body: JSON.stringify(payload) }); } catch(e){}
}
```

3. Dans le `voiceBtn` click handler :
- Réinitialiser `_apkEventCount = 0; _voiceFirstAudioSent = false; _voiceFirstAudioReceived = false;`
- Appeler `sendApkEvent('voice_button_clicked')`.

4. Dans `voiceWs.onopen` :
- Appeler `sendApkEvent('voice_ws_opened')`.
- Démarrer `_voiceNoAudioTimer = setTimeout(function(){ if(!_voiceFirstAudioReceived) sendApkEvent('voice_no_audio_after_timeout'); }, 20000);`

5. Dans `workletNode.port.onmessage` et `scriptNode.onaudioprocess` :
- Au premier chunk audio envoyé : si `_voiceFirstAudioSent === false` { `_voiceFirstAudioSent = true; sendApkEvent('voice_audio_sent');` }

6. Dans `voiceWs.onmessage` quand `data.type === 'audio'` :
- Si `_voiceFirstAudioReceived === false` { `_voiceFirstAudioReceived = true; sendApkEvent('voice_audio_received'); clearTimeout(_voiceNoAudioTimer);` }

7. Dans `voiceWs.onclose` et `stopVoice()` :
- `if (_voiceNoAudioTimer) { clearTimeout(_voiceNoAudioTimer); _voiceNoAudioTimer = null; }`
- `sendApkEvent('voice_ws_closed', {ws_close_code: evt.code})` (dans onclose)

## Risques de régression identifiés

- Ajout de `fetch()` peut augmenter le nombre de requêtes réseau côté APK; limiter via `_apkEventCount` et sampling.
- Mauvais emplacement de reset (`startVoice()` vs click handler) peut empêcher les reconnexions de conserver état correctement.
- Erreurs JS lors d'un `getToken()` manquant : `sendApkEvent` doit être resilient.

## Tests proposés (sans téléphone)

- Grep statique pour vérifier que `sendApkEvent` et variables sont présentes.
- Tests unitaires JS (sinon manuels) : simuler `voiceWs.onopen` et vérifier que `setTimeout` est démarré et `sendApkEvent` appelé (mock fetch).
- Simuler `onaudioprocess` et `port.onmessage` pour vérifier `voice_audio_sent` annonce une seule fois.
- Simuler `onmessage` audio pour vérifier `voice_audio_received` clear timer.

## Validation Ludovic requise ?

Oui — validation demandée pour toute action qui modifierait l'APK ou les comportements utilisateur visibles. Pour les events non destructifs, proposer la PR et demander validation.

---

## Actions suivantes que je peux faire maintenant

- Implémenter les modifications proposées dans `static/index.html` sur la branche `ds/objectif-005-events-voix` et ouvrir une PR (si tu me valides de pousser).
- Ou seulement produire le fichier `agents/DEEPSEEK_AVIS_005.md` (déjà créé) et attendre validation.

Indique si je dois appliquer les changements JS et pousser la PR.