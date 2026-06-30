# Codex Audit - Voice Guardian 01 Juillet

Branche auditee: `audit/voice-guardian-01juil`

Revision observee: `7e0a25f`

Date: 2026-07-01

Mode: audit lecture seule initial. Ce fichier publie l'avis Codex sur GitHub a la demande de l'utilisateur. Aucun correctif code n'est inclus dans ce commit.

## Avis Codex

La reconnaissance vocale Guardian n'est pas encore operationnelle au niveau attendu pour une fonction de securite. Les bips entendus par Ludovic sont coherents avec le fonctionnement du `SpeechRecognizer` Android: le code contient deja une rustine qui mute les flux audio pour masquer les tonalites systeme. La non-detection est egalement plausible: le demarrage de l'ecoute depend d'une chaine fragile permission micro -> session `SID` -> JS -> service foreground, et le bug `requestCode 77` bloque explicitement le redemarrage apres autorisation micro.

Conclusion courte: il faut corriger le chemin actuel pour stabiliser l'APK tout de suite, mais la bonne architecture cible n'est probablement pas `SpeechRecognizer` Google en boucle. Pour une ecoute permanente silencieuse, offline et fiable, il faut faire un POC VOSK ou moteur equivalent.

## 1. Reconnaissance vocale Android

### Constats

Le code confirme que `SpeechRecognizer` produit des bips start/stop.

Evidence:

- `android-app/java/fr/yawatch/luna/GuardianService.java:96-100` documente le bip systeme au demarrage/arret de chaque cycle.
- `android-app/java/fr/yawatch/luna/GuardianService.java:101-110` mute temporairement `STREAM_MUSIC`, `STREAM_SYSTEM` et `STREAM_NOTIFICATION`.
- `android-app/java/fr/yawatch/luna/GuardianService.java:367-373` mute avant `mSR.startListening(intent)` puis demute 1,2 s plus tard.
- `android-app/java/fr/yawatch/luna/GuardianService.java:301-305` remute en `onEndOfSpeech`.

Ce n'est pas un vrai mode silencieux. C'est une rustine qui change le volume systeme. Elle peut rater la fenetre du bip, couper temporairement un autre son legitime, ou produire une alternance perceptible si les cycles sont frequents.

Le cycle de redemarrage reste agressif.

Evidence:

- `android-app/java/fr/yawatch/luna/GuardianService.java:313-321` redemarre en 200 ms sur `ERROR_NO_MATCH` ou `ERROR_SPEECH_TIMEOUT`.
- `android-app/java/fr/yawatch/luna/GuardianService.java:339-340` redemarre aussi en 200 ms quand aucun mot-cle final n'est trouve.
- `android-app/java/fr/yawatch/luna/MainActivity.java:910-921` a le meme pattern cote reconnaissance native in-app.
- `android-app/java/fr/yawatch/luna/MainActivity.java:942-944` redemarre aussi en 200 ms sans mot-cle.

Meme avec les silences allonges dans `GuardianService` (`6000`, `4000`, `1000` ms aux lignes `360-364`), le service detruit et recree regulierement le recognizer. C'est exactement le type de mecanique qui cree bips intermittents et etats "veille/ecoute" difficiles a interpreter.

### Fiabilite

Le service attend maintenant les resultats finaux, pas les partiels.

Evidence:

- `android-app/java/fr/yawatch/luna/GuardianService.java:343-349` ne declenche plus sur resultats partiels.
- `android-app/java/fr/yawatch/luna/MainActivity.java:947-951` meme choix cote `MainActivity`.

Ce choix reduit les faux positifs, mais il peut expliquer une partie du ressenti "je le dis et il ne reconnait pas", surtout avec des phrases courtes, du bruit, ou si le recognizer n'arrive jamais a un final stable.

### Recommandation

Court terme:

1. Logguer chaque etat du recognizer dans `/api/apk/event`: `sr_start`, `sr_ready`, `sr_error`, `sr_final`, `sr_match`, `sr_no_match`, avec code erreur et transcript tronque.
2. Ajouter un etat UI clair: `Micro autorise`, `Session Guardian active`, `Service foreground actif`, `Ecoute native active`, `Dernier transcript`.
3. Reduire les doubles chemins: ne pas lancer en meme temps Web Speech et service natif quand le service foreground est actif.

Architecture cible:

Passer a un moteur offline continu type VOSK pour le wake/danger phrase spotting. `SpeechRecognizer` Google n'est pas concu comme un detecteur permanent silencieux. Il est fait pour des sessions de reconnaissance, pas pour une veille securite continue.

## 2. Faisabilite VOSK dans le build actuel non-Gradle

Le build Android est manuel.

Evidence:

- `android-app/build.sh:18-30` compile/link les ressources avec `aapt2`.
- `android-app/build.sh:32-39` compile Java avec `javac`.
- `android-app/build.sh:41-46` cree le DEX avec `d8`.
- `android-app/build.sh:48-56` ajoute `classes.dex` dans l'APK et zipalign.

Donc il n'y a pas de Gradle pour resoudre automatiquement un AAR Maven, copier des `.so`, fusionner des assets ou gerer les transitive dependencies.

Implication:

VOSK est faisable, mais il faut traiter l'integration comme une integration native manuelle:

- ajouter le JAR/classes de l'AAR VOSK au classpath `javac` et a l'entree `d8`;
- extraire et packager les bibliotheques natives `.so` par ABI dans l'APK;
- ajouter le modele francais dans `assets/` ou comme ressource copiee au premier lancement;
- adapter `build.sh` pour zipper assets + `lib/<abi>/*.so`;
- prevoir la taille APK: le modele FR small est typiquement de l'ordre de plusieurs dizaines de Mo, le modele complet est beaucoup trop gros pour ce besoin.

Recommandation:

Faire un POC VOSK minimal avant refonte complete:

1. Un seul mot-cle cible: `au secours`.
2. Mode foreground service uniquement.
3. Aucun TTS.
4. Telemetrie locale et serveur sur resultats partiels/finals.
5. Test terrain sur le telephone de Ludovic: ecran allume, ecran verrouille, poche, bruit ambiant, distance 1-3 metres.

Decision recommandee:

POC VOSK maintenant, mais ne pas basculer production tant que la taille APK, batterie et detection terrain ne sont pas mesurees.

## 3. TTS Guardian

Le TTS est maintenant muet par defaut.

Evidence:

- `static/guardian.html:976-982` pose la regle produit: ecouter ne signifie pas faire du bruit.
- `static/guardian.html:983-985` bloque toute parole si `localStorage.luna_voice !== '1'`.
- `static/guardian.html:1132-1133` supprime le diagnostic TTS automatique au demarrage.

Mais le code garde beaucoup d'appels `guardianSpeak` et `maybeSpeak`.

Evidence:

- `static/guardian.html:1154` parle au demarrage si opt-in.
- `static/guardian.html:1688` parle pendant le countdown si opt-in.
- `static/guardian.html:1696` parle les chiffres du countdown.
- `static/guardian.html:1720`, `1727`, `1742` parlent annulation / activation / confirmation.
- `static/guardian.html:1762`, `1776`, `1890`, `1924` peuvent parler dans des chemins de verification/resume/chute.

Risque:

Meme opt-in, le TTS peut relancer un larsen si le micro natif reste actif. `guardianSpeak` suspend seulement `_vocalRec` Web Speech (`static/guardian.html:988-1005`), pas `GuardianService`.

Recommandation:

1. Garder TTS opt-in.
2. Ajouter une seule API sonore centralisee: `guardianAudioPolicy.canSpeak(context)`.
3. Quand TTS parle, suspendre explicitement le service natif ou ignorer tout transcript pendant une fenetre `tts_playing + 1.5s`.
4. Ne jamais lire les chiffres du compte a rebours a voix haute en mode Guardian.
5. Pour une personne en danger, preferer vibration + UI + notification silencieuse.

## 4. Chaine d'activation et bug `requestCode 77`

Bug confirme.

Evidence:

- `android-app/java/fr/yawatch/luna/MainActivity.java:774-776` demande `RECORD_AUDIO` avec `requestCode 77`.
- `android-app/java/fr/yawatch/luna/MainActivity.java:822-827` redemande aussi le micro avec `77`.
- `android-app/java/fr/yawatch/luna/MainActivity.java:1250-1281` ne traite pas `77`.

Impact:

Apres une reinstall, les permissions sont remises a zero. Si l'utilisateur active Guardian, Android demande le micro, l'utilisateur accepte, mais le callback ne relance ni `setGuardianProtection(true, ...)`, ni `startNativeSR()`, ni `GuardianService` avec `listen=true`. Resultat: l'UI peut donner l'impression que Guardian est actif alors que l'ecoute ne l'est pas.

Autres trous d'activation:

- `static/guardian.html:1115-1119` ne cree `SID` qu'apres `/api/guardian/start`; sans contacts d'urgence, le backend renvoie `422 no_emergency_contacts` (`luna_web.py:15211-15215`).
- `static/guardian.html:1139-1141` lance Web Speech puis `startNativeVoiceGuardian()` seulement apres session Web active.
- `static/guardian.html:1144-1149` demarre `startGuardianService`, mais sans `listen=true`; le vrai mode protection permanente passe plutot par `setGuardianProtection`.
- `android-app/java/fr/yawatch/luna/BootReceiver.java:28` relance le service avec `listen=false`; apres reboot, presence oui, micro non.
- `android-app/AndroidManifest.xml:21-22` declare `FOREGROUND_SERVICE_MICROPHONE`, mais la permission runtime micro reste indispensable.
- `android-app/AndroidManifest.xml:27-28` demande l'exemption batterie, mais il faut verifier qu'elle est effectivement accordee sur l'appareil.

Recommandation court terme:

1. Traiter `requestCode == 77` dans `onRequestPermissionsResult`.
2. Apres accord, relire les prefs `guardian.listen_enabled` / `overlay_enabled` et relancer `setGuardianProtection(listen, overlay)` ou directement `GuardianService` avec `listen=true`.
3. Si refus, afficher un etat bloquant: `Guardian pas operationnel: micro refuse`.
4. Exposer un diagnostic fondateur: permission micro, overlay, optimisation batterie, service actif, recognizer disponible, dernier evenement SR.

## 5. Mots-cles

La liste a ete fortement resserree.

Evidence:

- `android-app/java/fr/yawatch/luna/GuardianService.java:59-75`.
- `android-app/java/fr/yawatch/luna/MainActivity.java:94-108`.
- `static/guardian.html:1521-1541`.
- `core/safety/voice_emergency.py:39-43` explique pourquoi `aide-moi`, `aidez-moi` et `a l'aide` ont ete retires des declencheurs immediats.

Avis:

Retirer `aide moi` est correct: trop ambigu pour un assistant. Retirer `a l'aide` est discutable pour Guardian. En conversation generique, c'est ambigu. En mode Guardian permanent, c'est aussi une formule naturelle de detresse. Mais la remettre en declenchement direct risque de recreer des faux positifs.

Recommandation:

- Ne pas remettre `aide moi` en immediate.
- Remettre `a l'aide` uniquement avec une logique stricte:
  - phrase courte ou isolee (`a l'aide`, `aidez moi`, `a l'aide s'il vous plait`);
  - pas suivie d'un contexte instrumental (`a l'aide de`, `aide moi a ecrire`, etc.);
  - declenche une confirmation silencieuse/countdown, pas un envoi direct.
- Garder `au secours` comme mot-cle immediate principal.

## 6. Architecture recommandee

### Phase A - stabilisation immediate

1. Fix `requestCode 77`.
2. Ajouter telemetrie SR complete.
3. Corriger l'UI pour distinguer `Guardian actif` de `Micro vraiment en ecoute`.
4. Eviter double micro Web Speech + service natif.
5. Garder TTS off par defaut.

### Phase B - POC VOSK

Objectif: prouver une veille offline continue, silencieuse, sans bips, avec detection robuste de `au secours`.

Critere de succes:

- zero bip sur 10 minutes d'ecoute;
- detection de `au secours` a 1 m, 2 m, 3 m;
- pas de faux positif sur conversation normale;
- batterie acceptable sur 30 minutes;
- APK installable via le build non-Gradle adapte.

### Phase C - refonte production

Si POC valide:

- VOSK devient le detecteur local de wake/danger phrases.
- Web Speech devient fallback seulement quand le service natif est indisponible.
- Iris/LLM reste pour interpretation nuancee, pas pour veille permanente.
- TTS reste opt-in et suspend toujours l'ecoute locale pendant playback.

## Priorite finale

1. Corriger le bug permission `77` maintenant.
2. Ajouter diagnostic/telemetrie pour savoir si Guardian ecoute vraiment.
3. Faire un POC VOSK rapidement.
4. Reintroduire prudemment `a l'aide` comme signal de confirmation, pas alerte directe.
5. Ne pas chercher a rendre `SpeechRecognizer` parfait: il ne l'est pas pour ce cas d'usage.

