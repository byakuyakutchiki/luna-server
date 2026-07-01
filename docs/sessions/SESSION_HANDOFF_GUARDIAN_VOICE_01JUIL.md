# Session de travail — Guardian voix / VOSK (01 juillet 2026)

Document de reprise : pour continuer dans une nouvelle session Claude sans rien perdre.
Repo : `byakuyakutchiki/luna-server` · Arbre local prod : `/home/ludo/luna-prod` (branche `feat/guardian-lifecycle`).

---

## 🎯 Objectif de la session
Rendre Guardian **fiable, discret et sans fausses alertes** : écoute permanente **silencieuse** (zéro bip) qui détecte les appels de détresse (« à l'aide », « au secours »…) et laisse toujours **le temps d'annuler** avant d'alerter les proches.

## ✅ Ce qui est FAIT et qui marche (prouvé)
- **Plus de bip d'écoute/veille.** Cause = double SpeechRecognizer Google (natif + Web Speech de la WebView). Remplacé par **VOSK** (moteur hors-ligne, zéro bip). Web Speech coupé à la source dans l'APK.
- **VOSK détecte** « au secours » ET « à l'aide » — prouvé par la télémétrie (`vosk_match`).
- **Voice-only** : les déclencheurs AUTOMATIQUES qui causaient les fausses alertes sont **désactivés** — détection de **chute** (accéléromètre, partait dès qu'on bougeait le tél), **immobilité prolongée**, **sortie de zone (geofence)**, **check-in manqué**. Guardian ne réagit plus qu'aux **appels vocaux**.
- **Plus de boucle** : cooldown VOSK (1 déclenchement max / 20 s).
- **OTA réparé** : l'app se met à jour en 1 tap (clé de signature `d12e81d`, versionCode bien bumpé).
- **Compte à rebours d'annulation 15 s** rétabli (avant, l'urgence vocale envoyait direct).
- **Mots-clés resserrés+élargis** : fragments ambigus retirés, mais vraies détresses (« j'ai du mal à respirer », « je saigne »…) captées ; « à l'aide de… » filtré (usage instrumental).

## 🔒 Sécurité en cours (IMPORTANT)
La prod tourne en **`LUNA_TEST_MODE=1`** → **tous les envois SMS/appels sont SIMULÉS** (0 vrai SMS aux contacts) tant que le panneau d'annulation n'est pas 100% validé. Révision prod servie : **`luna-beta-00816-vrn`**.
➡️ **NE PAS rebrancher les vrais envois** (`gcloud run services update luna-beta --region=europe-west1 --update-env-vars LUNA_TEST_MODE=... / remove`) tant que Ludo n'a pas confirmé que le compte à rebours s'affiche + est annulable.

## ⏳ CE QUI RESTE À VALIDER / FAIRE
1. **Le panneau compte à rebours s'affiche-t-il bien + est-il annulable** quand VOSK détecte (surtout app en arrière-plan) ? Diagnostic déjà en place : `_dbgSR()` dans `static/guardian.html` (`lunaEmergencyVoiceDetected`) → chercher dans les logs `web_emergency_received` / `web_bail_no_session` / `web_bail_sos_in_progress` / `web_opening_countdown`. Hypothèse à vérifier : bail si pas de session Guardian active (`SID` = besoin d'≥1 contact d'urgence).
2. **Permission overlay** (« afficher par-dessus les apps ») : Android la refuse par défaut pour un APK sideloadé (ce n'est PAS Ludo qui refuse). Sans elle, le panneau ne peut pas s'afficher app en arrière-plan. Accordée à la main via adb pour les tests. **À FAIRE** : l'app doit la DEMANDER elle-même à l'activation de Guardian (sinon inutilisable pour les autres users / sur un tél non branché).
3. Une fois le panneau validé → **retirer `LUNA_TEST_MODE`** et repasser en réel (garder d'abord un cran d'observation si possible).
4. Nettoyage : mots-clés Android alignés, `all-clear` (« tout va bien » aux proches) et « zone safe » à exposer en UI (existent déjà côté backend).

## 🔧 Détails techniques pour reprendre vite
- **APK actuel : v3.6 / versionCode 27**, signé `d12e81d`. Build : `cd /home/ludo/luna-prod/android-app && cp luna.keystore.bak luna.keystore && KEYSTORE_PASS=$(grep ^KEYSTORE_PASS= ../.env|cut -d= -f2-) bash build.sh`.
- **Déploiement** : `cd /home/ludo/luna-prod && bash deploy.sh --no-traffic` puis `gcloud run services update-traffic luna-beta --region=europe-west1 --to-revisions=<NEW>=100`. `deploy.sh` préserve `LUNA_TEST_MODE` via le template.
- **Debug ADB** (très utile) : `~/Android/Sdk/platform-tools/adb`. Tél = Redmi `24115RA8EG`. `adb install -r <apk>` (garde données/modèle/perms, même clé), `adb logcat`, `adb shell dumpsys activity services | grep GuardianService`, `adb shell appops set fr.yawatch.luna SYSTEM_ALERT_WINDOW allow`, force-stop / relance via `monkey`. ⚠️ Le câble se débranche facilement → « no devices » → repasser par OTA.
- **Télémétrie** : le natif envoie `srEvent → /api/debug/log` (tag `GUARDIAN_SR`). Voir : `gcloud run services logs read luna-beta --region=europe-west1 --limit=200 | grep GUARDIAN_SR`. Events : `vosk_listening / vosk_partial / vosk_final:<texte> / vosk_match / sr_emergency`.
- **Code clé** :
  - `android-app/java/fr/yawatch/luna/VoskGuardian.java` — moteur VOSK (reconnaissance libre, `normalizeKw`, cooldown, télémétrie, download modèle FR au 1er lancement).
  - `GuardianService.java` — `startListening()` lance VOSK (pref `vosk_enabled` défaut true) ; `setGuardianSession` NE registre plus la chute.
  - `core/guardian/engine.py` — flag `_GUARDIAN_VOICE_ONLY` (défaut true) coupe immobilité/geofence/checkin.
  - `static/guardian.html` — `setGuardianProtection(true,false)` lance VOSK ; `_vocalStart` no-op dans l'APK ; `_setVoskActiveUI()` (statut « actif ») ; `_dbgSR` diagnostic.
  - VOSK libs : `android-app/libs/{vosk,jna}.jar` + `android-app/jni/{arm64-v8a,armeabi-v7a}/*.so` ; `build.sh` les empaquette ; manifest `extractNativeLibs="true"`.
- **Audits GitHub** : branche `audit/voice-guardian-01juil` → `docs/audits/CODEX_AUDIT_VOICE_GUARDIAN_01JUIL.md` + `AVIS_CLAUDE_*`. Conclusion partagée : SpeechRecognizer Google = impasse pour l'écoute permanente, VOSK = la bonne voie.

## ▶️ Pour reprendre
« Reprends la session Guardian voix — on en était à valider que le panneau compte à rebours s'affiche + est annulable quand VOSK détecte « à l'aide », app en arrière-plan (voir SESSION_HANDOFF). Le tél est peut-être rebranché en adb. »
