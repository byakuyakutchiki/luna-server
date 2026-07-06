# Contexte — Audit Guardian Voice APK

## Date
2026-07-06

## Branche
`audit/guardian-voice-apk-chain`

## Objectif
Comprendre pourquoi la reconnaissance vocale fonctionne dans la page de test `speech_test.html` mais pas dans la page Guardian réelle sur l’APK Android.

## Environnement terrain
- Téléphone Android de Ludovic (utilisateur final).
- APK installée par-dessus l’ancienne version (mise à jour, pas réinstallation).
- APK version : `3.8 (29)`.
- Backend pointé par l’APK : `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian`.

## Comportement observé

### Page Guardian réelle (`/guardian`)
- Guardian s’ouvre.
- Authentification OK (token présent).
- **« Luna écoute » affiche INACTIF.**
- `Last /trigger status` : `-`.
- `Last guardian_session_id` : `-`.
- Le SOS vocal ne part jamais.

### Page de test (`/static/debug/speech_test.html`)
- `window.SpeechRecognition` : `true`.
- `new SpeechRecognition()` : OK.
- `rec.start()` appelé.
- `onstart` déclenché.
- `onresult` déclenché.
- Transcript reçu mais avec répétitions : `ààà l'aide…`, `ààà l'aide à l'aide…`.

## Conclusion partielle
Le matériel (micro) et la WebView supportent SpeechRecognition. Le problème est dans la chaîne qui relie la reconnaissance vocale au déclenchement SOS dans `guardian.html`, ou dans le fait que Guardian réel n’active pas cette chaîne.

## Hypothèses en cours
1. L’APK pointe vers la révision `trace---...` qui pourrait ne pas contenir les derniers patches.
2. Guardian réel ne démarre pas `_vocalStart()` (condition de garde, permission, état).
3. Le traitement des `interimResults` corrompait les transcripts (en cours d’audit).
4. La détection de mot-clé ne matche pas à cause du texte répété.
5. Le countdown / `/trigger` n’est jamais atteint.

## Contraintes
- Aucun correctif métier sans validation.
- Aucun changement backend.
- Aucune refonte architecture.
- Logs réversibles uniquement.
