# Android WebView Map

## Fichiers Android concernés

| Fichier | Rôle |
|---|---|
| `android-app/java/fr/yawatch/luna/MainActivity.java` | WebView, LunaBridge, permissions, debug panel |
| `android-app/java/fr/yawatch/luna/GuardianService.java` | Service foreground (notification uniquement en Phase 1) |
| `android-app/java/fr/yawatch/luna/AuthStorage.java` | Stockage natif tokens (Phase A) |
| `android-app/java/fr/yawatch/luna/DiagnosticState.java` | Etat diagnostic (Phase audit) |
| `android-app/java/fr/yawatch/luna/DiagnosticLogger.java` | Journal diagnostic (Phase audit) |
| `android-app/AndroidManifest.xml` | Permissions (RECORD_AUDIO, LOCATION, FOREGROUND_SERVICE, etc.) |

## WebView

- Classe : `android.webkit.WebView`
- URL chargée : `LUNA_URL` dans `MainActivity.java`
- Valeur actuelle : `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian`
- JavaScript activé : oui
- `setMediaPlaybackRequiresUserGesture(false)` : non confirmé
- `WebChromeClient.onPermissionRequest` : gère `DEVICE_CAPTURE`, `AUDIO_CAPTURE`

## Permissions déclarées dans AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

## LunaBridge (interface JS ↔ Android)

Méthodes actives :
- `showNotification(title, body)`
- `storeTokens(access, refresh)` / `getTokens()` / `clearTokens()`
- `startGuardianService(title, contacts)` / `stopGuardianService()`
- `updateGuardianNotification(title, body)`
- `clearGuardianSession()`
- `setLastTriggerStatus(status)`
- `setLastGuardianSessionId(sessionId)`
- `reportJsState(json)` / `logEvent(category, message)` / `setLastApiStatus(...)`
- `getDiagnosticInfo()` / `runDiagnosticTests()` / `resetApkSession()` / `copyDiagnosticToClipboard()`

Méthode commentée (Phase 2) :
- `setGuardianProtection(boolean enabled, boolean silent)`

> Si cette méthode est accidentellement présente, `guardian.html` désactivera Web Speech en croyant que VOSK natif est actif.

## Hardware variables

L’APK est installée sur le téléphone de Ludovic. Cela introduit des variables externes :
- Micro physique (qualité, bruit, occlusion).
- Version Android / WebView.
- Gestion des permissions par l’OEM.
- Batterie / Doze mode.
- Réseau mobile / Wi-Fi.
- Autres applications utilisant le micro.
