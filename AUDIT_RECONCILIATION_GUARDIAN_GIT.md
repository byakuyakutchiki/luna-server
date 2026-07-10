# 🚨 AUDIT DE RÉCONCILIATION GIT — Guardian natif Android

**Date :** 2026-07-10  
**Branche actuelle :** `feature/phase-a-auth-apk`  
**Commit historique de référence :** `1df57fd` — `feat(guardian): protection systeme Android`  
**Commits intermédiaires importants :** `6638062` — `fix(guardian): restaure capture contexte vocal + anti-doublon sur UI stable`

**Règle :** aucun fichier modifié pendant cet audit. Seulement de la lecture et de la comparaison.

---

## 1. Méthode de comparaison

Commandes utilisées :

```bash
git ls-tree -r --name-only 1df57fd | grep android-app
git diff 1df57fd -- android-app/java/fr/yawatch/luna/MainActivity.java
git diff 1df57fd -- android-app/AndroidManifest.xml
git show 1df57fd:android-app/java/fr/yawatch/luna/GuardianService.java
git show 1df57fd:android-app/java/fr/yawatch/luna/BootReceiver.java
git show a1c7cb6:android-app/java/fr/yawatch/luna/SosReceiver.java
git show 1df57fd:static/index.html | grep -i guardian
grep -n "LunaBridge\|lunaEmergencyVoiceDetected" static/guardian.html
```

---

## 2. Tableau de réconciliation fichier par fichier

| Fichier | État actuel | État historique (1df57fd) | Compatible avec l'actuel | Action recommandée | Risque de régression |
|---|---|---|---|---|---|
| `android-app/AndroidManifest.xml` | Version 24, permissions de base, `usesCleartextTraffic="true"`, PAS de service Guardian | Version 21, permissions Guardian (FGS micro, overlay, boot), service + receivers déclarés | ⚠️ Partiellement : les permissions et déclarations de service doivent être fusionnées avec la version actuelle (versionCode 24, cleartext=true) | **Fusionner** : ajouter les permissions et déclarations Guardian à la version actuelle | Moyen : si on oublie `usesCleartextTraffic="true"` ou qu'on écrase la versionCode/versionName |
| `android-app/java/fr/yawatch/luna/MainActivity.java` | WebView allégée, auto-update backend, bridge minimal (notification, version, foreground) | WebView avec Guardian natif : détection de chute, SR natif in-app, bridge complet Guardian | ⚠️ Partiellement : le code actuel a des fonctionnalités utiles (auto-update) qui ne doivent pas être perdues | **Fusionner** : réintégrer les méthodes LunaBridge Guardian et le handleGuardianIntent dans MainActivity actuel | Élevé si on copie-colle l'ancien fichier : perte de l'URL locale, de l'auto-update, du cleartext |
| `android-app/java/fr/yawatch/luna/GuardianService.java` | **Absent** | Foreground service avec écoute mot-clé SpeechRecognizer, notification permanente, bulle overlay | ✅ Oui, à adapter | **Restaurer** tel quel, avec mise à jour de l'URL locale dans l'intent | Moyen : Android 14+ impose des contraintes FGS strictes ; tests nécessaires |
| `android-app/java/fr/yawatch/luna/BootReceiver.java` | **Absent** | Relance la notification Guardian au boot (sans micro) | ✅ Oui | **Restaurer** tel quel | Faible |
| `android-app/java/fr/yawatch/luna/SosReceiver.java` | **Absent** | Bouton SOS dans la notification Guardian | ✅ Oui | **Restaurer** tel quel | Faible |
| `android-app/res/drawable/ic_guardian_shield.xml` | **Absent** | Icône de notification Guardian | ✅ Oui | **Restaurer** | Néant |
| `android-app/res/drawable/ic_notif_luna.xml` | Présent | Présent | ✅ Oui | Conserver tel quel | Néant |
| `android-app/res/values/styles.xml` | Présent | Présent | ✅ Oui | Conserver tel quel | Néant |
| `android-app/res/xml/network_security_config.xml` | `cleartextTrafficPermitted="true"` | `cleartextTrafficPermitted="false"` (historique) / `true` (diag) | ✅ Oui, version actuelle à conserver | **Conserver** la version actuelle | Néant |
| `static/guardian.html` | UI stable avec corrections vocales du commit `6638062` (capture contexte, anti-doublon) | Version plus ancienne sans les corrections vocales récentes | ⚠️ Partiellement : le JS appelle des méthodes LunaBridge qui n'existent plus | **Conserver** la version actuelle, compléter le bridge côté Java | Élevé si on écrase : perte de la capture de contexte et des anti-doublons terrain |
| `static/index.html` | Pas de toggle "Protection permanente" | Toggle "Protection permanente" + "Mini-bulle" dans l'onglet Réglages | ❓ À évaluer : le toggle était dans `index.html` mais Guardian est maintenant sur `/guardian` | **Ne pas restaurer tel quel** ; évaluer si `guardian.html` a besoin d'un toggle équivalent | Moyen : risque de confusion entre index.html et guardian.html |
| `core/safety/voice_emergency.py` | Modifié (non audité ici) | — | — | **À vérifier** pour l'endpoint `/api/guardian/voice/simulate` et la fonction `_get_guardian_engine` | — |
| `luna_web.py` | URL locale, `/api/app/version` incohérent | URL Cloud Run | — | Corriger `/api/app/version` après restauration (versionCode, SHA-256, URL) | Faible |

---

## 3. Méthodes LunaBridge attendues par `static/guardian.html`

Extrait des appels JS actuels :

| Méthode JS | Appelé dans guardian.html | Présent dans MainActivity actuel | Présent dans MainActivity 1df57fd | Statut |
|---|---|---|---|---|
| `LunaBridge.setAuthToken(token)` | ligne 784 | ❌ Non | ✅ Oui | **À restaurer** |
| `LunaBridge.logEvent(category, message)` | ligne 799 | ❌ Non | ❌ Non | **Était déjà absente historiquement** → créer ou ignorer silencieusement |
| `LunaBridge.setLastApiStatus(name, status)` | ligne 804 | ❌ Non | ❌ Non | **Était déjà absente historiquement** → créer ou ignorer silencieusement |
| `LunaBridge.updateGuardianNotification(status, contacts, emergency)` | ligne 946 | ❌ Non | ✅ Oui | **À restaurer** |
| `LunaBridge.setGuardianSession(SID)` | lignes 1150, 2296 | ❌ Non | ✅ Oui (chute) | **À restaurer** (sans détection de chute si non demandée) |
| `LunaBridge.setGuardianProtection(listen, overlay)` | lignes 1172, 1745, 2313 | ❌ Non | ✅ Oui | **À restaurer** — c'est le cœur de la protection arrière-plan |
| `LunaBridge.startGuardianService(status, contacts)` | ligne 1184 | ❌ Non | ✅ Oui | **À restaurer** |
| `LunaBridge.clearGuardianSession()` | ligne 1201 | ❌ Non | ✅ Oui | **À restaurer** |
| `LunaBridge.stopNativeVoiceGuardian()` | ligne 1222 | ❌ Non | ✅ Oui | **À restaurer** |
| `LunaBridge.stopGuardianService()` | ligne 1223 | ❌ Non | ✅ Oui | **À restaurer** |
| `LunaBridge.updateGuardianPosition(lat, lng)` | lignes 1286, 1422 | ❌ Non | ✅ Oui | **À restaurer** |
| `window.lunaEmergencyVoiceDetected(text, confidence)` | lignes 1898+ | ✅ Oui (définie dans guardian.html) | ✅ Appelée par le SR natif | **À reconnecter** |

---

## 4. Ce qu'il ne faut PAS restaurer

| Élément historique | Pourquoi ne pas le restaurer |
|---|---|
| URL Cloud Run dans `MainActivity.java` | Le projet est maintenant 100 % local ; l'URL actuelle est `http://192.168.1.45:8000/guardian` |
| `android:usesCleartextTraffic="false"` | La VM locale utilise du HTTP ; la valeur actuelle `true` doit être conservée |
| Détection de chute (accéléromètre) | Non demandée dans la mission actuelle ; complexité supplémentaire ; risque de faux positifs |
| Mini-bulle overlay (`SYSTEM_ALERT_WINDOW`) | Optionnelle ; peut être ajoutée plus tard si vraiment nécessaire ; demande une permission spéciale |
| Ancien `static/index.html` avec toggle Guardian | Guardian est maintenant sur `/guardian` ; le toggle devrait être dans `guardian.html` si nécessaire |
| Ancien `static/guardian.html` | Perdrait les corrections vocales critiques du commit `6638062` (capture contexte, anti-doublon) |

---

## 5. Architecture cible proposée

```
┌─────────────────────────────────────┐
│  Téléphone Android                  │
│                                     │
│  ┌─────────────────────────────┐   │
│  │  MainActivity (WebView)     │   │
│  │  - charge /guardian         │   │
│  │  - LunaBridge JS ↔ Android  │   │
│  │  - handleGuardianIntent()   │   │
│  └──────────┬──────────────────┘   │
│             │ start/bind            │
│  ┌──────────▼──────────────────┐   │
│  │  GuardianService            │   │
│  │  - foreground service       │   │
│  │  - notification permanente  │   │
│  │  - SpeechRecognizer fr-FR   │   │
│  │  - détection mot-clé        │   │
│  └──────────┬──────────────────┘   │
│             │ mot-clé détecté       │
│  ┌──────────▼──────────────────┐   │
│  │  MainActivity               │   │
│  │  → window.lunaEmergencyVoiceDetected(text, conf)
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
             │
             ▼
      http://192.168.1.45:8000
             │
             ▼
      /guardian (static/guardian.html)
             │
             ▼
      /api/guardian/... (dry-run)
             │
             ▼
           Redis
```

---

## 6. Points de vigilance avant modification

1. **Versionnage APK** : la prochaine APK doit avoir un `versionCode` et `versionName` strictement supérieurs à la fois à `luna-proprio.apk` (24 / 3.2.1) et à `luna-proprio-diag.apk` (24 / 3.2.1).  
   Proposition : `versionCode=25`, `versionName=3.3.0-guardian-restore`.

2. **Endpoint `/api/app/version`** : il annonce actuellement `version_code: 29` et un SHA-256 incorrect. Il doit être corrigé après la recompilation.

3. **Permissions Android 14+** : `FOREGROUND_SERVICE_MICROPHONE` impose de démarrer le service pendant que l'app est au premier plan. Le service ne pourra pas être démarré "à froid" depuis l'arrière-plan.

4. **Web Speech API vs SpeechRecognizer natif** : `guardian.html` utilise déjà `window.lunaEmergencyVoiceDetected` pour la détection Web Speech au premier plan. Le SR natif du service doit appeler le **même** callback, en veillant à l'anti-doublon (`_vocalActive`, `_sosInProgress`).

5. **Localisation** : `guardian.html` appelle `LunaBridge.updateGuardianPosition(lat, lng)`. Cette méthode doit être restaurée et, idéalement, enrichie pour récupérer la position native si la WebView ne peut pas la fournir (HTTP non sécurisé).

---

## 7. Conclusion de l'audit

Le code natif Guardian existe historiquement et est largement réutilisable. La stratégie la plus sûre est :

1. **Conserver** `MainActivity.java` actuel (URL locale, auto-update, permissions actuelles).
2. **Fusionner** dans `MainActivity.java` les méthodes LunaBridge Guardian et le `handleGuardianIntent`.
3. **Restaurer** `GuardianService.java`, `BootReceiver.java`, `SosReceiver.java`, `ic_guardian_shield.xml`.
4. **Mettre à jour** `AndroidManifest.xml` pour déclarer le service, les receivers et les permissions, sans perdre `usesCleartextTraffic="true"`.
5. **Conserver** `static/guardian.html` actuel (corrections vocales du commit 6638062).
6. **Ne pas restaurer** la détection de chute ni la bulle overlay dans un premier temps.
7. **Corriger** `/api/app/version` et supprimer/renommer `luna-proprio-diag.apk`.
8. **Augmenter** `versionCode`/`versionName` pour éviter toute confusion.

Aucun fichier n'a été modifié pendant cet audit.
