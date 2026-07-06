# Flow Map — Guardian Voice → SOS

## Chaîne complète (Web Speech, APK actuel)

```
[Utilisateur parle]
    ↓
WebView charge /guardian
    ↓
guardian.html s'initialise
    ↓
Authentification (token natif + localStorage)
    ↓
checkSession() → GET /api/guardian/sessions → SID existant ?
    ↓
guardianStart() → POST /api/guardian/start → nouveau SID
    ↓
_vocalStart() → crée SpeechRecognition
    ↓
rec.start() → demande micro
    ↓
rec.onstart → UI "écoute"
    ↓
rec.onresult → event.resultIndex / event.results
    ↓
_vocalMatch(transcript, isFinal)
    ↓
_normalise + EMERGENCY_KW match
    ↓
hit=true → _voiceCaptureActive=true + timer 4s
    ↓
isFinal ou timeout → openVocalCountdown()
    ↓
countdown n=15s → 0
    ↓
_triggerSOSVocal()
    ↓
POST /api/guardian/sos/{SID}
    ↓
backend → Twilio (appel) + SMS
    ↓
réponse 200 + guardian_session_id
```

## Chaîne VOSK natif (Phase 2 — non activée)

```
[Utilisateur parle]
    ↓
GuardianService natif (VOSK) écoute en tâche de fond
    ↓
Java appelle window.lunaEmergencyVoiceDetected(text, confidence, context)
    ↓
openVocalCountdown()
    ↓
_triggerSOSVocal()
```

> **Note** : VOSK natif n’est PAS activé dans l’APK actuel. `setGuardianProtection()` est commentée dans `MainActivity.java`. L’écoute vocale repasse par Web Speech dans la WebView.

## Points de rupture possibles

1. **Pas de SID** : `guardianStart()` ou `checkSession()` échoue.
2. **`_vocalStart()` ne s’exécute pas** : garde `setGuardianProtection`, SpeechRecognition absent, ou état bloquant.
3. **`rec.start()` échoue** : permission micro refusée.
4. **`onresult` n’est pas appelé** : micro non fonctionnel (pourtant Speech Test fonctionne).
5. **`_vocalMatch` ne matche pas** : transcript corrompu par répétition ou mot-clé absent.
6. **`openVocalCountdown` n’est pas appelé** : état `_vocalActive` ou `_sosInProgress` bloque.
7. **`_triggerSOSVocal` ne part pas** : `SID` absent ou `_sosInProgress` bloque.
8. **Backend refuse** : 401, 404, erreur serveur.

## Première rupture probable

D’après les constats terrain :
- Speech Test fonctionne → micro et WebView OK.
- Guardian affiche « Luna écoute INACTIF » → `_vocalStart()` ne démarre pas ou s’arrête.

La première rupture probable est donc :
> **Activation de l’écoute Guardian réelle** (`_vocalStart()` non appelée ou bloquée).

Si `_vocalStart()` s’exécute mais que `onresult` ne mène pas à `openVocalCountdown`, alors la rupture est au niveau :
> **Passage `onresult` → matcher**.
