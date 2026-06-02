# Claude — Audit contrôles Daily/Simli provider visio — Objectif 017

Agent : Claude  
Date : 2026-06-02  
Commit : en cours  
Type : audit technique — contrôles provider / conflit micro

---

## Résumé

Deux problèmes distincts identifiés :

1. **Contrôles Daily.js visibles** — partiellement cachés, deux options manquantes
2. **Conflit micro Double getUserMedia** — risque élevé sur Android, probable cause de `muted=true`

---

## 1. Contrôles Daily.js dans l'iframe

### Ce qui est déjà caché

```javascript
DailyIframe.wrap(existingIframe, {
  showLeaveButton: false,       // ✅ caché
  showFullscreenButton: false,  // ✅ caché
})
```

### Ce qui reste visible (non configuré)

| Contrôle | Option Daily.js | Priorité |
|---|---|---|
| Barre participants / nom du bot | `showParticipantsBar: false` | Haute — source du label "Chatbot" |
| Vidéo locale (preview Ludovic) | `showLocalVideo: false` | Haute — doublon avec notre UI |
| Bouton nom utilisateur | `showUserNameChangeUI: false` | Moyenne |
| Micro / caméra natifs Daily | **non masquables via option** — voir section 3 | Haute |

### Patch immédiat (Niveau 1)

Ajouter dans les options de `DailyIframe.wrap()` ET `createFrame()` :

```javascript
{
  showLeaveButton: false,
  showFullscreenButton: false,
  showParticipantsBar: false,
  showLocalVideo: false,
}
```

**Impact** : supprime la barre participants (et le label "Chatbot"), supprime la preview locale.  
**Risque** : nul — options UI only, ne touche pas aux tracks WebRTC.

---

## 2. Micro et caméra natifs Daily — non masquables proprement

Les boutons mic/caméra dans l'iframe Daily sont **rendus par Daily.js à l'intérieur de l'iframe**, dans un DOM cross-origin inaccessible depuis notre page.

**Il n'existe pas d'option Daily.js standard pour masquer ces boutons dans `wrap()` ou `createFrame()`.**

Options de contournement :

| Approche | Faisabilité | Risque |
|---|---|---|
| CSS `pointer-events:none` sur l'iframe entier | Bloquant — casse tous les clics dans l'iframe | Non |
| Overlay opaque par-dessus la zone basse de l'iframe | Faisable — `div` absolu couvrant la barre basse | Moyen (layout) |
| Demander à Tavus d'activer `ui_type: "minimal"` | Dépend de l'API Tavus — à vérifier dans les options create_conversation | Meilleure option |
| Masquer l'iframe entier et n'afficher que les tracks vidéo manuellement | Complexité élevée — niveau 2 | Futur |

**Recommandation Claude** : vérifier les paramètres `conversation_properties` de l'API Tavus pour une option UI minimale. Sinon, overlay CSS sur la barre basse comme solution intermédiaire.

---

## 3. Conflit Double getUserMedia — risque élevé

### Ce qui se passe actuellement

```
daily_joined → _startSpeechCapture() → _startVAD() → getUserMedia({ audio: true })
```

Daily.js a **déjà acquis le micro** via WebRTC avant `joined-meeting`. Notre VAD appelle ensuite `getUserMedia` sur le même matériel.

**Résultat** :
- Deux flux audio simultanés depuis la même puce micro
- Sur desktop Chrome : généralement fonctionne, mais augmente le risque de muted=true
- Sur Android WebView/APK : échec probable → `vad_track_muted = true` ou `getUserMedia` rejeté
- Performance : deux AudioContext actifs en parallèle

### Preuve dans les logs F12

```
[INFO][simli] vad_rms 0.0008 silence   ← RMS proche de zéro malgré parole
[INFO][simli] vad_rms 0.0002 silence
[INFO][simli] vad_rms 0.0413 PAROLE    ← détecte parfois, pas toujours
```

Le fait que le RMS oscille proche de zéro suggère une contention hardware entre Daily et notre VAD.

### Fix recommandé — réutiliser le track Daily (pas un second getUserMedia)

Au lieu d'appeler `getUserMedia` indépendamment, récupérer la piste audio locale de Daily :

```javascript
function _startVAD() {
  if (_vadActive) return;
  _vadActive = true;

  // Réutiliser le track Daily si disponible — évite le double getUserMedia
  var dailyAudioTrack = null;
  try {
    var local = dailyCall && dailyCall.participants && dailyCall.participants().local;
    dailyAudioTrack = local && local.tracks && local.tracks.audio && local.tracks.audio.persistentTrack;
  } catch(e) {}

  if (dailyAudioTrack && dailyAudioTrack.readyState === 'live') {
    rLog('info', 'simli', 'vad_using_daily_track', 'évite double getUserMedia');
    var sharedStream = new MediaStream([dailyAudioTrack]);
    _vadStream = sharedStream;
    _setupVADWithStream(sharedStream);
  } else {
    // Fallback : getUserMedia indépendant
    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      .then(_setupVADWithStream)
      .catch(function(e) { ... });
  }
}
```

**Avantage** : un seul handle matériel, pas de contention, RMS fiable, fonctionne sur Android.  
**Risque** : `persistentTrack` disponible uniquement dans Daily.js >= 0.9. À vérifier avec la version chargée.

---

## 4. Matrice bouton → target → preuve

| Bouton visible | Target réelle | Prouvée ? | Décision |
|---|---|---|---|
| Orbe VAD (violet/rouge/cyan) | VAD start/stop → Whisper → LLM → TTS | STT 500 → fix python-multipart en cours | Garder |
| 🎙 Iris active (btnMuteLuna) | Envoie message système "tais-toi" à Tavus | Non prouvée en B-lite | À auditer |
| 📎 Analyser (btnUpload) | `/api/visio/upload` → analyse image/doc | Non testée ce sprint | À garder ou ranger |
| 👥 Inviter | Génère lien Daily | Non testée | Secondaire |
| 🔗 Partager | Modal partage | Fonctionne | Ranger |
| 📝 Notes | `/api/visio/notes` | Non testée | Secondaire |
| Iris voit (badge vision) | `/api/visio/perception` + vision loop | `vision_change` vu en F12 → actif | Garder mais affichage honnête |
| Contrôles Daily (mic/cam) | Daily WebRTC tracks | Actifs mais redondants avec VAD | Masquer si possible |
| Bouton raccrocher | `dailyCall.leave()` | Présumé fonctionnel | Garder visible |

---

## 5. Prochaines actions Claude

| Action | Niveau | Dépendance |
|---|---|---|
| Ajouter `showParticipantsBar: false` + `showLocalVideo: false` | 1 | Aucune — patch immédiat |
| Réutiliser track Daily dans `_startVAD()` | 1-2 | Vérifier version Daily.js disponible |
| Overlay CSS sur barre basse Daily | 2 | Validation Kimi layout |
| Vérifier `ui_type` minimal dans Tavus create_conversation | 1 | Accès API Tavus |

---

## Ce que Claude n'a PAS fait

- Pas de refonte layout (Niveau 2, attente Kimi)
- Pas de modification des boutons existants sans validation
- Pas de code pour le track Daily (attente validation Ludovic sur l'approche)
