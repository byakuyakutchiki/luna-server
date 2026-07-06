.md
# Logs à collecter sur le terrain

## Panneau diagnostic natif (APK)

Ouvrir : appui long sur l’écran Guardian.

Informations critiques à noter :

- `URL` : vérifier la révision Cloud Run chargée.
- `Page` : `guardian.html` attendu.
- `SpeechRecognition dispo` : doit être `oui`.
- `Luna écoute` : `active` ou `inactive`.
- `RECORD_AUDIO` : `✓`.
- `ACCESS_FINE_LOCATION` : `✓` ou `✗`.
- `GuardianService` : `running` ou `arrêté`.
- `Dernière erreur JS`.

## Journal des événements

Dans le panneau diagnostic, bouton `Voir journal` puis `Copier`.

Rechercher dans le journal les lignes suivantes :

```
GUARDIAN  guardian.html charge URL=...
AUDIO     ENTER _vocalStart
AUDIO     setGuardianProtection=...
AUDIO     SpeechRecognition object=...
AUDIO     rec.start() appel
AUDIO     SpeechRecognition demarre
AUDIO     onresult start=... len=...
MATCH     ENTER transcript=...
MATCH     RESULT hit=...
COUNTDOWN started
SOS       CALL /api/guardian/sos/...
SOS       RESPONSE status=...
```

## adb logcat (si possible)

```bash
adb logcat -s LUNA_WEBVIEW:D chromium:D WebView:D *:S
```

## Scénario de test standard

1. Ouvrir Luna → Guardian.
2. Démarrer une session Guardian.
3. Activer l’écoute vocale.
4. Dire : *« À l’aide je suis tombé »*.
5. Attendre 20 secondes.
6. Ouvrir le diagnostic (long-press).
7. Copier le journal.
8. Si SOS déclenché : vérifier SMS et appel.

## Scénario de test Speech Test

1. Ouvrir `https://phase-a-auth---luna-beta-gly3g647na-ew.a.run.app/static/debug/speech_test.html` dans l’APK.
2. Appuyer sur Start.
3. Parler.
4. Noter si `onresult` se déclenche et quel transcript apparaît.

## Objectif des logs

Identifier la **première rupture exacte** dans la chaîne :
- Activation de l’écoute Guardian réelle, ou
- Passage `onresult` → matcher.
