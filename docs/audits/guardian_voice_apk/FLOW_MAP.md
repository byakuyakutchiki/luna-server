# Flow Map — Guardian Voice → SOS

## Chaîne complète (Web Speech, APK Phase 1)

```
[Utilisateur parle]
    ↓
WebView charge /guardian
    ↓
guardian.html s'initialise
    ↓
LunaAuth.init() → vérifie token
    ↓
checkSession() → récupère SID si session active
    ↓
guardianStart() → POST /api/guardian/start → SID
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

## Chaîne alternative (VOSK natif, APK Phase 2 — désactivée)

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

> **Note** : VOSK natif n’est PAS activé dans la Phase A/B actuelle. `setGuardianProtection()` est commentée dans `MainActivity.java`.

## Points de rupture possibles

1. **Pas de SID** : `guardianStart()` ou `checkSession()` échoue.
2. **`_vocalStart()` ne s’exécute pas** : `setGuardianProtection` existe par erreur, ou SpeechRecognition absent.
3. **`rec.start()` échoue** : permission micro refusée.
4. **`onresult` n’est pas appelé** : micro non fonctionnel.
5. **`_vocalMatch` ne matche pas** : transcript corrompu ou mot-clé absent.
6. **`openVocalCountdown` n’est pas appelé** : état `_vocalActive` ou `_sosInProgress` bloque.
7. **`_triggerSOSVocal` ne part pas** : `SID` absent ou `_sosInProgress` bloque.
8. **Backend refuse** : 401, 404, erreur serveur.
