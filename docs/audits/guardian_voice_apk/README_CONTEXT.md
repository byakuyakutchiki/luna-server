# Contexte — Audit Guardian Voice APK

## Date
2026-07-06

## Branche
`docs/audit-guardian-voice-apk-2026-07-06`

## Objectif
Comprendre pourquoi la reconnaissance vocale fonctionne dans la page de test `speech_test.html` mais pas dans la page Guardian réelle sur l’APK Android.

Cette branche est un **document d’audit uniquement**. Aucun fichier applicatif n’est modifié ici.

## Environnement terrain
- Téléphone Android de l’utilisateur (hardware réel).
- APK installée par-dessus l’ancienne version (mise à jour, pas réinstallation).
- APK version observée : `3.8 (29)`.
- Backend pointé par l’APK : `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian`.

> **Important hardware** : l’APK est exécutée sur un téléphone physique. Cela introduit des variables externes : micro, version WebView, gestion des permissions par l’OEM, batterie/Doze, réseau, autres apps utilisant le micro.

## Comportement observé

### Page Guardian réelle (`/guardian`)
- Guardian s’ouvre.
- Authentification OK (token présent).
- **« Luna écoute » affiche INACTIF.**
- `Last /trigger status` : `-`.
- `Last guardian_session_id` : `-`.
- Le SOS vocal ne part jamais depuis l’APK.
- **L’appel backend `/api/guardian/sos/{sid}` (ou `/trigger`) n’est jamais atteint.**

### Page de test (`/static/debug/speech_test.html`)
- `window.SpeechRecognition` : `true`.
- `new SpeechRecognition()` : OK.
- `rec.start()` appelé.
- `onstart` déclenché.
- `onresult` déclenché.
- Transcript reçu mais avec répétitions : `ààà l'aide…`, `ààà l'aide à l'aide…`

## Conclusion partielle
Le matériel (micro) et la WebView supportent SpeechRecognition. Le problème est dans la chaîne qui relie la reconnaissance vocale au déclenchement SOS dans `guardian.html`, ou dans le fait que Guardian réel n’active pas cette chaîne.

## Hypothèses en cours
1. **Activation de l’écoute Guardian réelle** : `_vocalStart()` n’est pas appelée ou s’arrête avant `rec.start()`.
2. **Passage onresult → matcher** : le transcript est reconstruit avec répétitions, ce qui peut perturber la détection de mot-clé.
3. **APK pointe vers trace---...** : la révision Cloud Run chargée pourrait ne pas contenir les derniers patches.
4. **Etat bloquant** : `_vocalActive`, `_sosInProgress` ou absence de `SID` bloquent la chaîne.

## Contraintes
- Aucun correctif métier sans validation explicite.
- Aucun changement backend.
- Aucune refonte architecture.
- Aucun build APK ni déploiement depuis cette branche.
