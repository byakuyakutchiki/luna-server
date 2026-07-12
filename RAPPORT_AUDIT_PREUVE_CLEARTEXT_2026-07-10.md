# 🚨 RAPPORT D'AUDIT DE PREUVE — `ERR_CLEARTEXT_NOT_PERMITTED`

**Date :** 2026-07-10  
**Objet :** Prouver pourquoi l'APK affiche toujours `net::ERR_CLEARTEXT_NOT_PERMITTED` malgré `usesCleartextTraffic="true"`.  
**Méthode :** Aucune modification du code. Aucune recompilation. Uniquement des extractions et des comparaisons depuis la VM.

---

## 1. Résumé exécutif

L'APK actuellement **servie par le serveur** est techniquement correcte :
- elle autorise le HTTP local (`usesCleartextTraffic="true"`) ;
- elle contient un `network_security_config.xml` autorisant le cleartext ;
- elle pointe bien sur `http://192.168.1.45:8000/guardian` ;
- son SHA-256 est `2c88fbd661b59ee1ff6429b9fc800ddf2b41295dbfb8c165b92f4a1778c9a495`.

**Cependant, il existe une deuxième APK sur le serveur (`static/luna-proprio-diag.apk`) qui a exactement le même `versionCode` (24) et le même `versionName` (3.2.1), mais qui interdit le HTTP (`usesCleartextTraffic="false"`).**

Si c'est cette APK qui a été installée sur le téléphone, l'erreur `ERR_CLEARTEXT_NOT_PERMITTED` est exactement le comportement attendu.

**Verdict provisoire :** le problème ne vient probablement PAS du code source actuel, mais d'une confusion entre deux APK quasi identiques sur le serveur, ou d'un cache navigateur sur le téléphone.

---

## 2. Preuves établies

### 2.1 L'APK compilée et l'APK servie sont strictement identiques

Commandes exécutées :

```bash
sha256sum android-app/build/luna-proprio.apk
sha256sum static/luna-proprio.apk
cmp -l android-app/build/luna-proprio.apk static/luna-proprio.apk
curl -s http://192.168.1.45:8000/static/luna-proprio.apk -o /tmp/apk_served.apk
sha256sum /tmp/apk_served.apk
cmp -s /tmp/apk_served.apk static/luna-proprio.apk
```

Résultat :

```text
2c88fbd661b59ee1ff6429b9fc800ddf2b41295dbfb8c165b92f4a1778c9a495  android-app/build/luna-proprio.apk
2c88fbd661b59ee1ff6429b9fc800ddf2b41295dbfb8c165b92f4a1778c9a495  static/luna-proprio.apk
2c88fbd661b59ee1ff6429b9fc800ddf2b41295dbfb8c165b92f4a1778c9a495  /tmp/apk_served.apk
IDENTIQUE au fichier static/luna-proprio.apk
```

**Preuve :** l'APK compilée, l'APK dans `static/`, et l'APK téléchargée via le serveur sont le même fichier.

---

### 2.2 AndroidManifest de l'APK servie contient `usesCleartextTraffic=true`

Commande :

```bash
$ANDROID_HOME/build-tools/35.0.1/aapt dump xmltree /tmp/apk_served.apk AndroidManifest.xml
```

Extrait prouvé :

```text
E: application
  A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0xffffffff
  A: android:networkSecurityConfig(0x01010527)=@0x7f040000
```

`0xffffffff` = `true`.

---

### 2.3 `network_security_config.xml` est bien présent dans l'APK et autorise le cleartext

Commande :

```bash
$ANDROID_HOME/build-tools/35.0.1/aapt dump xmltree /tmp/apk_served.apk res/xml/network_security_config.xml
```

Résultat :

```text
E: network-security-config
  E: base-config
    A: cleartextTrafficPermitted=(type 0x12)0xffffffff
```

`0xffffffff` = `true`.

---

### 2.4 Toutes les URLs de l'APK pointent vers la VM locale

Commande :

```bash
unzip -p /tmp/apk_served.apk classes.dex | strings | grep -E "192\.168\.|trace---luna|run\.app|localhost"
```

Résultat :

```text
http://192.168.1.45:8000/guardian
http://192.168.1.45:8000/guardian/api/apk/heartbeat
http://192.168.1.45:8000/guardian/api/app/version
http://192.168.1.45:8000/guardian/api/logs/client
```

Aucune URL Google Cloud n'a été trouvée.

---

### 2.5 `/download/luna.apk` sert aussi la bonne APK

Commande :

```bash
curl -s http://192.168.1.45:8000/download/luna.apk -o /tmp/apk_download.apk
sha256sum /tmp/apk_download.apk
cmp -s /tmp/apk_download.apk static/luna-proprio.apk
```

Résultat :

```text
2c88fbd661b59ee1ff6429b9fc800ddf2b41295dbfb8c165b92f4a1778c9a495  /tmp/apk_download.apk
IDENTIQUE a luna-proprio.apk
```

---

## 3. Divergence critique découverte

### 3.1 Une deuxième APK avec le même nom d'affichage interdit le HTTP

Fichier : `static/luna-proprio-diag.apk`

Commande :

```bash
$ANDROID_HOME/build-tools/35.0.1/aapt dump badging static/luna-proprio-diag.apk | head -5
$ANDROID_HOME/build-tools/35.0.1/aapt dump xmltree static/luna-proprio-diag.apk AndroidManifest.xml | grep -E "usesCleartextTraffic|networkSecurityConfig"
```

Résultat :

```text
package: name='fr.yawatch.luna' versionCode='24' versionName='3.2.1'
      A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
      A: android:networkSecurityConfig(0x01010527)=@0x7f040000
```

`0x0` = `false`.

Différence exacte entre les deux APK (extrait du `diff` des manifests) :

```diff
<       A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0xffffffff
---
>       A: android:usesCleartextTraffic(0x010104ec)=(type 0x12)0x0
```

Les deux APK ont :
- le même `package` (`fr.yawatch.luna`)
- le même `versionCode` (24)
- le même `versionName` (3.2.1)
- la même taille (33 587 octets)

**Seule la configuration réseau diffère.** Si l'utilisateur a installé `luna-proprio-diag.apk`, Android affichera `ERR_CLEARTEXT_NOT_PERMITTED` alors que l'interface dira "v3.2.1".

### 3.2 Troisième APK obsolète présente

Fichier : `static/download/luna.apk`

```text
package: name='fr.yawatch.luna' versionCode='21' versionName='3.0'
usesCleartextTraffic=0x0 (false)
```

Cette APK est également en HTTP interdit.

---

## 4. Incohérence dans l'endpoint `/api/app/version`

Requête :

```bash
curl -s http://192.168.1.45:8000/api/app/version | python3 -m json.tool
```

Réponse :

```json
{
    "version": "3.8",
    "version_code": 29,
    "apk_url": "/download/luna.apk",
    "apk_sha256": "487f632934f4ce201fbda7ffa09b45af109372a7c45c8e4835cc611c97c0445f",
    "changelog": "Sécurité APK renforcée, vérification intégrité mise à jour"
}
```

Problèmes :
- `version_code` annoncé : 29, alors que l'APK actuelle est en versionCode 24.
- `apk_sha256` annoncé : `487f6329...`, mais le SHA-256 réel de `/download/luna.apk` est `2c88fbd6...`.

**Conséquence :** l'auto-update intégré à l'APK actuelle ne se déclenchera pas à cause d'un champ JSON mal nommé (`apk_download_url` attendu, `apk_url` reçu), mais l'endpoint est techniquement incohérent.

---

## 5. Ce qui n'a PAS été prouvé

1. **Quelle APK est réellement installée sur le téléphone ?**  
   Je n'ai pas accès au téléphone. Je ne peux pas prouver que l'APK installée est `luna-proprio.apk` ou `luna-proprio-diag.apk`.

2. **Les logs `logcat` du téléphone.**  
   Nécessitent un accès physique + ADB ou une application de log.

3. **L'état du cache du navigateur Chrome sur le téléphone.**  
   Chrome pourrait avoir servi une ancienne APK mise en cache.

4. **Les données résiduelles d'une ancienne installation.**  
   Même après désinstallation, Android conserve parfois des données/cache si l'option "Conserver les données" a été choisie.

---

## 6. Verdict

### 🟡 Cause la plus probable (non prouvée mais fortement étayée)

L'APK installée sur le téléphone est **luna-proprio-diag.apk** (ou une ancienne version), et non **luna-proprio.apk**.

Pourquoi :
- l'erreur `ERR_CLEARTEXT_NOT_PERMITTED` correspond exactement à un manifest avec `usesCleartextTraffic="false"` ;
- l'APK correcte est bien sur le serveur et bien servie ;
- les deux APK ont le même `versionCode`/`versionName`, ce qui rend la confusion possible.

### 🟢 Ce qui fonctionne côté serveur

- Luna démarre sur `0.0.0.0:8000` ;
- `/guardian` répond ;
- `/static/luna-proprio.apk` et `/download/luna.apk` servent la bonne APK ;
- l'APK correcte contient bien les autorisation HTTP.

### 🔴 Ce qui empêche le test

L'APK installée sur le téléphone n'est probablement pas l'APK correcte.

---

## 7. Actions à effectuer (ordre de priorité)

### 7.1 Priorité 1 — Prouver l'APK installée

Sur le téléphone, exécuter via ADB (ou une app Shell) :

```bash
adb shell pm list packages -f | grep yawatch
adb shell pm dump fr.yawatch.luna | grep -E "versionCode|versionName|path"
```

Puis extraire l'APK installée :

```bash
adb shell pm path fr.yawatch.luna
adb pull <chemin_retourné> /tmp/luna_installed.apk
sha256sum /tmp/luna_installed.apk
$ANDROID_HOME/build-tools/35.0.1/aapt dump xmltree /tmp/luna_installed.apk AndroidManifest.xml | grep usesCleartextTraffic
```

Comparer le SHA-256 avec :
- `2c88fbd661b59ee1ff6429b9fc800ddf2b41295dbfb8c165b92f4a1778c9a495` (bonne APK)
- `3e611a590b61ea150a42c2354e3732975928d6b88dc510ede7115f1806d52737` (mauvaise APK diag)

### 7.2 Priorité 2 — Nettoyer complètement et réinstaller

Si le SHA-256 ne correspond pas à la bonne APK :

```bash
adb uninstall fr.yawatch.luna
adb shell pm clear fr.yawatch.luna   # si encore présent
```

Puis sur le téléphone, dans Chrome, vider le cache, et télécharger :

```
http://192.168.1.45:8000/download/luna.apk
```

Vérifier après téléchargement que le fichier fait **33 587 octets**.

### 7.3 Priorité 3 — Capturer logcat pendant l'ouverture

```bash
adb logcat -c
adb logcat | grep -iE "yawatch|luna|cleartext|err_|webview" > /tmp/luna_logcat.txt
```

Ouvrir l'APK et reproduire l'erreur.

### 7.4 Priorité 4 — Corriger l'endpoint `/api/app/version`

Une fois le problème d'installation résolu, corriger dans `luna_web.py` :
- `LUNA_APP_VERSION_CODE` doit correspondre à l'APK réelle (24, pas 29) ;
- `_APK_SHA256` est déjà correct (il calcule `static/luna-proprio.apk`) ;
- le champ `apk_url` devrait être `apk_download_url` pour correspondre au code Java, ou le code Java devrait lire `apk_url`.

---

## 8. Données brutes utiles

### Liste des APK sur le serveur

```text
-rw-r--r-- 1 ludo ludo 23014 Jul 10 21:03 ./android-app/build/luna-aligned.apk
-rw-r--r-- 1 ludo ludo 23010 Jul 10 21:03 ./android-app/build/luna-unsigned.apk
-rw-r--r-- 1 ludo ludo 33587 Jul 10 21:03 ./android-app/build/luna-proprio.apk
-rw-r--r-- 1 ludo ludo  4795 Jul 10 21:03 ./android-app/build/apk/base.apk
-rw-r--r-- 1 ludo ludo 19774 Jul  3 19:00 ./static/download/luna.apk
-rw-r--r-- 1 ludo ludo 33587 Jul 10 21:03 ./static/luna-proprio.apk
-rw-r--r-- 1 ludo ludo 33587 Jul  6 11:17 ./static/luna-proprio-diag.apk
```

### Tableau récapitulatif

| Fichier | versionCode | versionName | usesCleartextTraffic | SHA-256 |
|---|---|---|---|---|
| `static/luna-proprio.apk` | 24 | 3.2.1 | ✅ true | `2c88fbd6...` |
| `static/luna-proprio-diag.apk` | 24 | 3.2.1 | ❌ false | `3e611a59...` |
| `static/download/luna.apk` | 21 | 3.0 | ❌ false | `2136b814...` |
| APK servie par `/download/luna.apk` | 24 | 3.2.1 | ✅ true | `2c88fbd6...` |
| APK installée sur le téléphone | **inconnu** | **inconnu** | **à prouver** | **à prouver** |

---

## 9. Conclusion

Le serveur et l'APK correcte sont en place. L'erreur `ERR_CLEARTEXT_NOT_PERMITTED` persistante s'explique le plus probablement par l'installation d'une APK interdisant le HTTP (`luna-proprio-diag.apk` ou ancienne version), et non par un défaut du code source actuel.

**Prochaine étape obligatoire :** prouver, via ADB, quelle APK est réellement installée sur le téléphone.
