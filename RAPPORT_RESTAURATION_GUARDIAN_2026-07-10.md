# 🛡 RAPPORT — Restauration Guardian vocal Android

**Date :** 2026-07-10/11  
**Mission :** Restaurer le vrai Guardian vocal Android (écoute mot-clé + arrière-plan)  
**Statut :** ✅ Build prêt — ⏳ Test téléphone en attente

---

## 1. Ce qui a été fait

### 1.1 Audit de réconciliation Git

- Comparaison entre `feature/phase-a-auth-apk` et le commit historique `1df57fd`.
- Fichier produit : `AUDIT_RECONCILIATION_GUARDIAN_GIT.md`.
- Conclusion : le code natif Guardian est réutilisable ; la stratégie est de **fusionner** dans `MainActivity.java` actuel plutôt que de remplacer.

### 1.2 Fichiers restaurés

| Fichier | Source | Statut |
|---|---|---|
| `android-app/java/fr/yawatch/luna/GuardianService.java` | commit `1df57fd` | ✅ restauré |
| `android-app/java/fr/yawatch/luna/BootReceiver.java` | commit `1df57fd` | ✅ restauré |
| `android-app/java/fr/yawatch/luna/SosReceiver.java` | historique Git | ✅ restauré |
| `android-app/res/drawable/ic_guardian_shield.xml` | commit `1df57fd` | ✅ restauré |

### 1.3 MainActivity.java fusionnée

- Toutes les méthodes actuelles conservées (URL locale, auto-update, WebView moderne).
- Méthodes LunaBridge Guardian ajoutées :
  - `setAuthToken`
  - `setGuardianSession`
  - `clearGuardianSession`
  - `updateGuardianPosition`
  - `startGuardianService`
  - `stopGuardianService`
  - `updateGuardianNotification`
  - `setGuardianProtection`
  - `isGuardianProtectionOn`
  - `startNativeVoiceGuardian`
  - `stopNativeVoiceGuardian`
- Gestion des intents Guardian ajoutée (`handleGuardianIntent`, `onNewIntent`, `fireVoiceSosJs`).
- Reconnaissance vocale native in-app ajoutée (`startNativeSR`, `stopNativeSR`, etc.).
- Détection de chute et bulle overlay **NON** restaurées (hors scope).

### 1.4 AndroidManifest.xml mis à jour

- `versionCode` : 25
- `versionName` : `3.3.0-guardian-restore`
- Permissions ajoutées : `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`, `FOREGROUND_SERVICE_MICROPHONE`, `RECEIVE_BOOT_COMPLETED`.
- `GuardianService`, `BootReceiver`, `SosReceiver` déclarés.
- `usesCleartextTraffic="true"` conservé.

### 1.5 Backend corrigé

- `luna_web.py` ligne 16511 : `_get_guardian_engine(tid)` → `_get_guardian()`.
- `/api/app/version` corrigé :
  - `version_code` : 25
  - `apk_download_url` ajouté
  - `current_apk_version_code` ajouté
  - `minimum_apk_version_code` ajouté
  - `apk_sha256` cohérent avec l'APK

### 1.6 Artefacts nettoyés

- `static/luna-proprio-diag.apk` archivée en `static/luna-proprio-diag.apk.ARCHIVE`.
- `static/download.html` mis à jour avec la version `3.3.0-guardian-restore`.

### 1.7 Build APK réussi

```text
=== APK cree avec succes ===
  Fichier: /home/ludo/luna-server/android-app/build/luna-proprio.apk
  Download: /static/luna-proprio.apk
-rw-r--r-- 1 ludo ludo 41K Jul 11 00:43 luna-proprio.apk
```

### 1.8 Vérifications APK

```text
package: name='fr.yawatch.luna' versionCode='25' versionName='3.3.0-guardian-restore'
```

- `usesCleartextTraffic=true` ✅
- `FOREGROUND_SERVICE` ✅
- `FOREGROUND_SERVICE_DATA_SYNC` ✅
- `FOREGROUND_SERVICE_MICROPHONE` ✅
- `RECEIVE_BOOT_COMPLETED` ✅
- `GuardianService` déclaré ✅
- `BootReceiver` déclaré ✅
- `SosReceiver` déclaré ✅

SHA-256 : `bd740a12961c94c52f6446777e34657f56c035a5adc100901b4071a4c89d97b9`

### 1.9 Serveur redémarré

- Luna redémarré sur `0.0.0.0:8000`.
- `/guardian` répond 200 ✅
- `/api/app/version` répond avec les bonnes informations ✅

### 1.10 Sécurité vérifiée

- `GUARDIAN_SMS_ENABLED=false` ✅
- `GUARDIAN_CALL_ENABLED=false` ✅
- `VOICE_EMERGENCY_DRY_RUN=true` ✅

---

## 2. Ce qui n'a pas pu être testé

### 2.1 `/api/guardian/voice/simulate`

L'endpoint nécessite une authentification. Le test direct en ligne de commande retourne :

```json
{"error": "Token invalide ou manquant", "auth_required": true}
```

Il sera testé via l'interface Guardian sur téléphone.

### 2.2 Test réel sur téléphone

Non effectué — c'est la prochaine étape.

---

## 3. Procédure de test téléphone

### Avant de commencer

1. Vérifie que le téléphone est sur le même Wi-Fi que la VM.
2. Vérifie que Luna tourne :
   ```bash
   curl -s http://192.168.1.45:8000/guardian
   ```

### Installation

1. Désinstalle l'ancienne APK :
   ```bash
   adb uninstall fr.yawatch.luna
   ```
2. Vide le cache de Chrome sur le téléphone.
3. Télécharge la nouvelle APK :
   ```
   http://192.168.1.45:8000/download/luna.apk
   ```
4. Vérifie que le fichier fait environ **41 Ko**.
5. Installe et autorise :
   - Micro
   - Position (toujours ou au moins en cours d'utilisation)
   - Notifications

### Test au premier plan

1. Ouvre Luna.
2. Va sur Guardian.
3. Vérifie que Ludovic est le seul contact protecteur.
4. Démarre la protection.
5. Vérifie que "LUNA ÉCOUTE" passe actif.
6. Dis : `"Au secours, il y a quelqu'un devant ma porte"`.
7. Vérifie que Guardian affiche le compte à rebours.
8. Vérifie que le contexte `"il y a quelqu'un devant ma porte"` est conservé.

### Test en arrière-plan

1. Retourne à l'écran d'accueil Android.
2. Vérifie la notification permanente "Luna Guardian".
3. Dis : `"À l'aide"`.
4. Vérifie que Luna revient au premier plan et affiche le compte à rebours.

### Vérifications backend

Pendant les tests, surveille les logs :

```bash
tail -f /tmp/luna_guardian_restore.log | grep -iE "guardian|sos|vosk|voice"
```

Aucun SMS ni appel réel ne doit partir.

---

## 4. Fichiers modifiés

- `android-app/java/fr/yawatch/luna/MainActivity.java`
- `android-app/java/fr/yawatch/luna/GuardianService.java` (créé)
- `android-app/java/fr/yawatch/luna/BootReceiver.java` (créé)
- `android-app/java/fr/yawatch/luna/SosReceiver.java` (créé)
- `android-app/res/drawable/ic_guardian_shield.xml` (créé)
- `android-app/AndroidManifest.xml`
- `luna_web.py`
- `static/download.html`
- `static/luna-proprio-diag.apk` → `static/luna-proprio-diag.apk.ARCHIVE`
- Fichiers générés : `static/luna-proprio.apk`, `android-app/build/*`

---

## 5. Verdict intermédiaire

🟡 **Guardian est prêt à être testé sur téléphone.**

Le build est réussi, le serveur est à jour, l'APK contient le code natif Guardian.  
La réussite définitive dépend du test terrain :
- détection du mot-clé en arrière-plan ;
- capture du contexte vocal ;
- notification permanente ;
- dry-run backend.

---

## 6. Risques restants

1. **Android 14+** peut refuser le démarrage du foreground service micro si l'app n'est pas au premier plan au moment du démarrage. Le service est démarré par `setGuardianProtection()` quand l'utilisateur active la protection dans l'interface, donc normalement l'app est au premier plan.
2. **Localisation** : `guardian.html` utilise `navigator.geolocation` qui peut poser problème en HTTP. La méthode `updateGuardianPosition` du bridge est restaurée, mais la position native n'est pas encore activement récupérée par le Java si la WebView refuse.
3. **Auto-update** : le code Java attend `apk_download_url` et `current_apk_version_code`, désormais fournis. L'auto-update devrait fonctionner si le SHA-256 est correct.

---

## 7. Prochaines étapes si le test téléphone réussit

1. Vérifier que le SOS ne part pas en vrai (dry-run).
2. Tester le redémarrage du téléphone et la relance de la notification.
3. Tester la localisation (GPS activé / refusé).
4. Documenter la procédure de test Guardian.

## 8. Prochaines étapes si le test téléphone échoue

1. Capturer `adb logcat` pendant le test.
2. Vérifier que l'APK installée est bien la version 25.
3. Vérifier que les permissions micro et position sont accordées.
4. Vérifier que le service Guardian démarre bien (log `LUNA_VERSION`, `GuardianService`).
5. Adapter le code selon les erreurs trouvées.
