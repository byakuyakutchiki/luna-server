# DeepSeek — Avis Objectif 006

**Date** : 2026-05-25
**Branche** : codex/objectif-006-validation-cerveau

## Objectif

Vérifier si le cerveau Luna voit la panne vocale réelle de Ludovic avant toute correction.

## Résumé

Sur la branche Objective 6, l'instrumentation de monitoring voix est en place dans `static/index.html` et le serveur a un endpoint `POST /api/apk/event` avec analyse `GET /api/admin/apk-voice-events`.

### Verdict technique

- `sendApkEvent()` est présent.
- `voice_button_clicked` est envoyé au clic du bouton vocal.
- `voice_ws_opened` est envoyé dans `voiceWs.onopen`.
- `voice_audio_sent` est envoyé lors du premier chunk audio, pour les deux modes microphone : `ScriptProcessor` et `AudioWorklet`.
- `voice_audio_received` est envoyé au premier chunk audio de retour.
- `voice_no_audio_after_timeout` est envoyé après 20 secondes si aucun audio reçu.
- `voice_ws_closed`, `voice_ws_error`, `voice_session_ended`, `microphone_permission_granted` et `microphone_permission_denied` sont tous présents.
- Le serveur stocke uniquement les événements autorisés et exécute `_analyze_voice_events()` pour produire un diagnostic lisible.

## Vérifications effectuées

### `static/index.html`

- Lignes 7268-7271 : déclarations de variables de télémétrie.
- Lignes 7273-7282 : fonction `sendApkEvent()` avec limite 10 événements.
- Ligne 7601 : envoi `microphone_permission_granted` juste après `getUserMedia` success.
- Ligne 7642 : `voice_audio_sent` sur le premier chunk via `ScriptProcessor`.
- Ligne 7701 : `voice_audio_sent` sur le premier chunk via `AudioWorklet`.
- Ligne 7707-7710 : `voice_audio_received` avec clear timer et envoi d’événement.
- Ligne 7662-7666 : `voice_ws_opened` + timer 20s + envoi `voice_no_audio_after_timeout`.
- Ligne 7756-7757 : `voice_ws_closed` + clear timer.
- Ligne 7787 : `voice_ws_error`.
- Ligne 7837-7838 : `voice_session_ended` + clear timer.
- Lignes 7862-7865 : reset `_apkEventCount`, `_voiceFirstAudioSent`, `_voiceFirstAudioReceived`; envoi `voice_button_clicked` avant `startVoice(false)`.

### `luna_web.py`

- `POST /api/apk/event` vérifié et protégé par JWT via `_verify_jwt()`.
- Liste blanche d’événements strictement contrôlée.
- Analyse des événements via `_analyze_voice_events(events)` produisant des scénarios humains : `no_audio_timeout`, `mic_denied`, `ws_error`, `ok`, `partial`.
- Endpoint `GET /api/admin/apk-voice-events` disponible pour le cockpit fondateur.

## Conclusion

Le cerveau Luna est techniquement capable de voir la panne vocale réelle si les événements atteignent bien le serveur.
La trajectoire d’instrumentation est correcte : la panne peut être identifiée comme l’un des cas suivants
- aucune réponse audio après 20s
- permission micro refusée
- erreur WebSocket
- session terminée sans réponse

## Risques / points à surveiller

- Si `getToken()` est absent ou invalide dans le WebView, les événements ne seront pas envoyés ; l’analyse peut alors rester vide.
- `sendApkEvent()` limite à 10 événements, ce qui est souhaitable, mais rend la captation sensible à des erreurs de token précoces.
- Si le téléphone n’a pas de heartbeat actif, l’objectif 6 ne pourra pas être validé avant que le cockpit voie le téléphone fondateur.

## Recommandations DeepSeek

1. Confirmer avec Ludovic que `GET /api/admin/apk-voice-events` renvoie des événements après un test.
2. Vérifier que le dernier événement de la session est bien `voice_no_audio_after_timeout` lorsque la panne se produit.
3. Si la panne persiste sans aucun événement, enquêter d’abord sur le JWT / token `getToken()` côté WebView.
4. Ne pas corriger le flux audio avant d’avoir au moins un diagnostic de session complet (`no_audio_timeout`, `ws_error` ou `mic_denied`).

## Validation Ludovic requise ?

Oui — ce diagnostic doit être validé par le test réel sur téléphone avant tout correctif fonctionnel.
