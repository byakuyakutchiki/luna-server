# Android WebView Map

## Fichiers Android concernés (pour référence d’audit uniquement)

| Fichier | Rôle |
|---|---|
| `android-app/java/fr/yawatch/luna/MainActivity.java` | WebView, LunaBridge, permissions, debug panel |
| `android-app/java/fr/yawatch/luna/GuardianService.java` | Service foreground **notification uniquement** en Phase 1 |
| `android-app/AndroidManifest.xml` | Permissions (RECORD_AUDIO, LOCATION, FOREGROUND_SERVICE, etc.) |

> Cette branche ne modifie aucun de ces fichiers. Ce document sert uniquement à cartographier le système pour l’audit.

## WebView

- Classe : `android.webkit.WebView`
- URL chargée : `LUNA_URL` dans `MainActivity.java`
- Valeur actuelle observée : `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian`
- JavaScript activé : oui
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

Méthodes observées utiles pour l’audit :
- `showNotification(title, body)`
- `startGuardianService(title, contacts)` / `stopGuardianService()`
- `setLastTriggerStatus(status)`
- `setLastGuardianSessionId(sessionId)`
- `reportJsState(json)` / `logEvent(category, message)` / `setLastApiStatus(...)` (ajoutés pour l’audit terrain)

## ⚠️ Clarification sur GuardianService

`GuardianService` est actuellement un **service foreground de notification**. Il ne fait pas d’écoute vocale native persistante. Il ne doit pas être présenté comme une source VOSK validée.

L’écoute vocale dans l’APK repasse par la WebView et la Web Speech API.

## Hardware variables

L’APK est installée sur le téléphone de l’utilisateur. Cela introduit des variables externes :
- Micro physique (qualité, bruit, occlusion).
- Version Android / WebView.
- Gestion des permissions par l’OEM.
- Batterie / Doze mode.
- Réseau mobile / Wi-Fi.
- Autres applications utilisant le micro.
