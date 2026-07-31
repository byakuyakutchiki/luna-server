# Référentiel technique Android — Luna / Guardian

## Objectif

Ce référentiel centralise la documentation officielle Android (Google Developers et AOSP) nécessaire au développement de **Guardian**, de l'APK Luna et de toute automatisation Android pilotée par Kimi, Codex, Cursor ou DeepSeek.

Il sert de **source de vérité stable** pour répondre aux questions du type :

- Qu'est-ce qu'une application Android peut faire légalement sans root ?
- Quelles permissions sont nécessaires pour accéder au micro, à la caméra, à la localisation ?
- Comment une application peut-elle interagir avec d'autres applications ?
- Quelles sont les limites imposées par Google Play et par le sandbox Android ?
- Quels outils officiels permettent de tester ou d'automatiser un appareil Android ?

## Structure

| Fichier | Thème |
|---------|-------|
| `01_architecture_securite.md` | Sandbox, UID Linux, SELinux, processus, moindre privilège |
| `02_cycle_de_vie.md` | Activity, Service, BroadcastReceiver, ContentProvider |
| `03_permissions.md` | Permissions normales, dangereuses, spéciales, runtime, best practices |
| `04_stockage.md` | Scoped Storage, fichiers privés, MediaStore, SAF |
| `05_accessibilite.md` | Services d'accessibilité, capacités et limites |
| `06_foreground_services.md` | Foreground services, types, restrictions Android 14+ |
| `07_device_admin_enterprise.md` | Device Admin, Android Enterprise, deprecation |
| `08_work_profile.md` | Work Profile, managed profile |
| `09_adb.md` | Android Debug Bridge, commandes essentielles, sécurité |
| `10_tests_instrumentation.md` | UI Automator, Espresso, tests officiels |
| `11_intents_ipc.md` | Intents explicites/implicités, IPC, PendingIntent, URI permissions |
| `12_notifications.md` | Notifications, canaux, permissions, foreground service notification |
| `13_overlay.md` | SYSTEM_ALERT_WINDOW, draw over apps, restrictions |
| `14_micro_camera_gps.md` | Accès micro, caméra, localisation : permissions et bonnes pratiques |
| `15_bluetooth_nfc_usb.md` | Bluetooth, NFC, USB : permissions et APIs officielles |
| `16_restrictions_google_play.md` | Restrictions et politiques Google Play pour les apps sensibles |
| `17_ia_capacites_limites.md` | Ce qu'une IA peut/ne peut pas faire sur Android sans que l'app le prévoie |
| `SOURCES.md` | Index complet des sources officielles par chapitre |

## Règles d'utilisation pour les agents

1. **Toute affirmation technique doit être sourcée** par une URL officielle Google Developers ou AOSP.
2. **Ne pas interpréter** : si la doc officielle est floue, le signaler comme tel.
3. **Distinguer** : ce qui est possible en développement natif vs. ce qui est autorisé par Google Play.
4. **Distinguer** : ce qui est possible avec un appareil rooté vs. un appareil standard.
5. **Pour Guardian** : privilégier les approches nécessitant le moins de permissions et le moins de privilèges système.

## Public cible

- Kimi : UX, tests réels, compréhension des contraintes terrain.
- Codex : implémentation, permissions, manifest, code natif.
- Cursor : vérification locale, cohérence fichiers.
- DeepSeek : audit technique, risques, faisabilité.
- Ludovic : prise de décision sur les déploiements et choix d'architecture.

## Dernière mise à jour

2026-07-12 — Création initiale du référentiel.
