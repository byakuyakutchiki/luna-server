# Restrictions Google Play : permissions sensibles et API d'accessibilité

## Objectif

Ce chapitre recense les politiques Google Play qui conditionnent l'usage des permissions sensibles et de l'API `AccessibilityService`. Il vise à ce que **Guardian** et l'APK **Luna** ne déclarent que des permissions strictement justifiées par une fonctionnalité centrale, documentée dans le listing Play Store, et à ce que chaque déclaration Play Console requise soit anticipée.

## Concepts clés

### 1. Exigence de `targetSdkVersion`

Google Play impose un niveau d'API cible minimal qui augmente à chaque version majeure d'Android.

- À partir du **31 août 2025**, les **nouvelles applications** et les **mises à jour** doivent cibler **Android 15 (API level 35)** ou supérieur.
- Les applications **Wear OS**, **Android Automotive OS** et **Android TV** doivent cibler **Android 14 (API level 34)** ou supérieur.
- Les applications **existantes** doivent cibler **Android 14 (API level 34)** ou supérieur pour rester distribuables aux nouveaux utilisateurs dont l'appareil exécute une version d'Android supérieure à l'API cible de l'application.
- L'attribut `targetSdkVersion` du manifeste indique comment l'application est censée s'exécuter sur les différentes versions d'Android.

### 2. Typologie des permissions Android

La documentation Android distingue trois grandes catégories de permissions :

| Type | Protection level | Comportement |
|---|---|---|
| **Install-time** | `normal`, `signature` | Accordées automatiquement à l'installation. |
| **Runtime** | `dangerous` | Nécessitent une demande explicite à l'exécution à partir d'**Android 6.0 (API level 23)**. |
| **Spéciales** | `appop` | Accordées depuis les **Paramètres** système (ex. `SYSTEM_ALERT_WINDOW`, `MANAGE_EXTERNAL_STORAGE`). |

Points techniques importants :

- Les permissions dangereuses donnent accès à des données privées (localisation, contacts, appareil photo, micro, etc.).
- Depuis **Android 11 (API level 30)**, les dialogues de localisation, micro et caméra proposent une option **"Une seule fois"**.
- Toujours vérifier l'état de la permission avec `ContextCompat.checkSelfPermission()` avant d'accéder à une ressource protégée.
- Les groupes de permissions peuvent changer ; il ne faut pas présumer qu'une permission appartient à un groupe donné.

### 3. Permissions sensibles et restreintes

Google Play classe certaines permissions comme **restreintes** (`dangerous`, `special`, `signature` ou explicitement listées). Les données qu'elles donnent à voir sont considérées comme des données personnelles et sensibles, soumises à la **User Data policy**. Elles ne peuvent être demandées que pour une fonctionnalité centrale (*core functionality*) documentée et promue dans le listing Play Store.

#### 3.1 SMS et journaux d'appels

- Seule une application désignée comme **gestionnaire SMS, Téléphone ou Assistant** par défaut peut demander les permissions du groupe SMS (`READ_SMS`, `SEND_SMS`, `RECEIVE_SMS`, etc.) ou du groupe Call Log (`READ_CALL_LOG`, `WRITE_CALL_LOG`, `PROCESS_OUTGOING_CALLS`).
- L'application ne peut pas déclarer ces permissions dans son manifeste si elle n'est pas capable d'être ce gestionnaire par défaut.
- Les données SMS/Call Log ne peuvent servir qu'à la fonctionnalité centrale ; la publicité ou l'analyse marketing sont interdites.

#### 3.2 Localisation en arrière-plan

- `ACCESS_BACKGROUND_LOCATION` est disponible à partir d'**Android 10 (API level 29)**.
- Elle ne peut être utilisée que si elle apporte un bénéfice significatif à l'utilisateur et est directement liée à la fonctionnalité centrale de l'application.
- Jamais à des seules fins de publicité ou d'analyse.
- Nécessite :
  - un **Permissions Declaration Form** dans Play Console,
  - une **vidéo de démonstration**,
  - une **divulgation in-app visible** avant la demande runtime,
  - une **politique de confidentialité** dans l'app et sur le listing.
- Un **foreground service** de localisation doit être lancé comme prolongement d'une action initiée par l'utilisateur dans l'application et s'arrêter immédiatement après la réalisation du cas d'usage.

#### 3.3 Accès à tous les fichiers (`MANAGE_EXTERNAL_STORAGE`)

- Restreint aux applications ciblant **Android 11 (API level 30)** ou supérieur et dont la fonctionnalité centrale l'exige (gestionnaire de fichiers, sauvegarde/restauration, antivirus, gestion documentaire, recherche de fichiers, chiffrement, migration de données, etc.).
- Il faut privilégier les alternatives plus respectueuses de la vie privée : **Storage Access Framework**, **MediaStore API**, sélecteurs système.
- L'accès est accordé manuellement par l'utilisateur dans **Paramètres > Accès spécial aux applications > Accéder à tous les fichiers**.

#### 3.4 Photos et vidéos

- À partir d'**Android 13 (API level 33)**, `READ_MEDIA_IMAGES` et `READ_MEDIA_VIDEO` ne peuvent être demandés que si le **sélecteur de photos Android** ou un sélecteur système équivalent ne suffit pas à la fonctionnalité centrale.
- Une déclaration dans Play Console est alors requise.

#### 3.5 Visibilité des applications installées (`QUERY_ALL_PACKAGES`)

- À partir d'**Android 11 (API level 30)**, le système filtre par défaut la visibilité des packages installés.
- `QUERY_ALL_PACKAGES` n'est autorisé que si la fonctionnalité centrale de l'application requiert une visibilité large sur toutes les applications (lanceur, interopérabilité globale, etc.).
- Il faut privilégier des requêtes ciblées via l'élément `<queries>`.
- L'inventaire des applications installées est considéré comme une donnée personnelle et sensible.

#### 3.6 Autres permissions restreintes notables

| Permission | Contrainte principale |
|---|---|
| `REQUEST_INSTALL_PACKAGES` | Réservé aux applications dont la fonctionnalité centrale implique l'envoi, la réception ou l'installation d'APK initiée par l'utilisateur. Pas de mise à jour silencieuse/auto-bundling. |
| `USE_EXACT_ALARM` (**Android 13+, API 33**) | Auto-accordée uniquement pour les applications réveil/minuteur/calendrier avec notifications. Sinon utiliser `SCHEDULE_EXACT_ALARM`. |
| `USE_FULL_SCREEN_INTENT` (**Android 14+, API 34**) | Auto-accordée uniquement pour les applications réveil ou appels téléphoniques/vidéo. Sinon consentement explicite. |
| Capteurs corporels | À partir d'**Android 16**, remplacement progressif de `BODY_SENSORS` par des permissions granulaires `android.permission.health.*` (`READ_HEART_RATE`, etc.). Soumis à la Health apps policy. |

### 4. Foreground services et types de service

Depuis **Android 14 (API level 34)**, chaque **foreground service** doit déclarer un type de service approprié dans le manifeste et demander la permission `FOREGROUND_SERVICE_*` correspondante, en plus de `FOREGROUND_SERVICE`. Selon le type, des permissions runtime peuvent également être requises avant le lancement du service.

Exemple de déclaration pour un service de localisation :

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />

<service
    android:name=".MyLocationService"
    android:foregroundServiceType="location"
    android:exported="false" />
```

Types de foreground service documentés (liste non exhaustive) :

- `camera` : accès caméra en arrière-plan (ex. visioconférence multitâche).
- `connectedDevice` : interactions avec des périphériques externes (Bluetooth, NFC, USB, etc.).
- `dataSync` : transfert de données, sauvegarde, import/export.
- `health` : suivi d'activité physique longue durée.
- `location` : navigation, partage de localisation.
- `mediaPlayback` / `mediaProcessing` : lecture et traitement média.
- `microphone` : capture micro en arrière-plan.
- `phoneCall` : appel via `ConnectionService`.
- `shortService` : travail critique non interruptible, limité à environ 3 minutes.
- `specialUse` : cas non couverts par les autres types ; nécessite de documenter le cas d'usage dans le manifeste via un élément `<property>`.
- `systemExempted` : réservé aux applications système, profils propriétaires, applications d'urgence, etc.

Par ailleurs, à partir d'**Android 12 (API level 31)**, une application en arrière-plan ne peut généralement plus démarrer un foreground service, sauf exceptions documentées.

Sur Google Play, les applications ciblant Android 14+ doivent déclarer leurs types de foreground service dans la page **App content** de Play Console.

### 5. API d'accessibilité (`AccessibilityService`)

L'API `AccessibilityService` est conçue pour aider les personnes en situation de handicap à utiliser l'appareil.

Déclaration minimale dans le manifeste :

```xml
<service
    android:name=".MyAccessibilityService"
    android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE">
    <intent-filter>
        <action android:name="android.accessibilityservice.AccessibilityService" />
    </intent-filter>
    <meta-data
        android:name="android.accessibilityservice"
        android:resource="@xml/accessibility_service_config" />
</service>
```

Attributs clés :

- `android:isAccessibilityTool` (API level 31) indique si le service est un outil d'accessibilité. La valeur par défaut est `false`.
- Seules les applications dont le but principal est d'aider les personnes handicapées (lecteurs d'écran, systèmes de saisie vocale/switch, affichage braille, etc.) peuvent légitimement définir `isAccessibilityTool="true"`.
- Les applications généralistes (assistants, outils d'automatisation, antivirus, launchers, etc.) ne sont **pas** des outils d'accessibilité.

Restrictions Google Play sur l'usage de l'API :

- Ne pas modifier les paramètres utilisateur sans permission, empêcher la désinstallation d'une application ou contourner les contrôles de sécurité/vie privée d'Android.
- Ne pas utiliser l'API de manière trompeuse.
- Ne pas enregistrer l'audio d'appels distants.
- Ne pas permettre à l'application d'initier, planifier et exécuter des actions ou décisions de manière autonome. L'automatisation déterministe à règles fixes ("si X, alors Y") est tolérée pour les usages d'automatisation non accessibilité, à condition d'être étroite et clairement comprise ; les outils d'accessibilité certifiés sont exemptés de cette interdiction pour les fonctionnalités liées à leur cœur de métier.
- Privilégier des API et permissions plus ciblées chaque fois que possible.

Obligations de déclaration Play Console :

- Depuis le **3 novembre 2021**, les applications ciblant **Android 12 (API level 31)** et incluant un `AccessibilityService` doivent remplir une déclaration d'accessibilité.
- Si `isAccessibilityTool="true"` : décrire la fonctionnalité centrale, les types de handicap ciblés, les utilisateurs concernés, et fournir une vidéo de démonstration.
- Si `isAccessibilityTool="false"` : fournir une **divulgation in-app visible** et obtenir un **consentement explicite** avant d'utiliser l'API, puis remplir le formulaire Play Console avec les données accédées et leur usage.

### 6. Données utilisateur et divulgation

La **User Data policy** impose la transparence sur l'accès, la collecte, l'utilisation et le partage des données.

Exigences principales :

- **Divulgation visible in-app** (*prominent disclosure*) lorsque la collecte de données sensibles n'est pas dans l'attente raisonnable de l'utilisateur. Elle doit :
  - apparaître dans l'application elle-même, pas seulement dans la description ou un site web,
  - être affichée dans le flux d'utilisation normal,
  - décrire les données accédées,
  - expliquer leur utilisation et éventuel leur partage,
  - être distincte de la politique de confidentialité et des autres divulgations,
  - être immédiatement suivie d'une demande de consentement explicite.
- **Politique de confidentialité** obligatoire dans Play Console et dans l'application, sur une URL active, non éditable, non PDF.
- **Section Data safety** à renseigner pour chaque application.
- **Suppression de compte** : si l'application permet de créer un compte, elle doit permettre de le supprimer, depuis l'app et en dehors.
- Les données personnelles et sensibles ne peuvent être **vendues**.

## Références officielles

- [Meet Google Play's target API level requirement](https://developer.android.com/google/play/requirements/target-sdk)
- [Target API level requirements for Google Play apps](https://support.google.com/googleplay/android-developer/answer/11926878)
- [Permissions overview](https://developer.android.com/guide/topics/permissions/overview)
- [Request runtime permissions](https://developer.android.com/training/permissions/requesting)
- [Permissions and APIs that Access Sensitive Information](https://support.google.com/googleplay/android-developer/answer/9888170)
- [User Data - Play Console Help](https://support.google.com/googleplay/android-developer/answer/10144311)
- [Understanding location in the background permissions](https://support.google.com/googleplay/android-developer/answer/9799150)
- [Manage all files on a storage device](https://developer.android.com/training/data-storage/manage-all-files)
- [Package visibility filtering on Android](https://developer.android.com/training/package-visibility)
- [Foreground service types](https://developer.android.com/develop/background-work/services/fgs/service-types)
- [AccessibilityService - Android Developers](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService)
- [AccessibilityServiceInfo - Android Developers](https://developer.android.com/reference/android/accessibilityservice/AccessibilityServiceInfo)
- [Use of the AccessibilityService API - Play Console Help](https://support.google.com/googleplay/android-developer/answer/10964491)
- [Build accessible apps](https://developer.android.com/guide/topics/ui/accessibility/apps)
- [Google Play Policy Center](https://support.google.com/googleplay/android-developer/topic/9858052)

## Implications pour Guardian / Kimi

- **Minimiser les permissions** : Guardian doit éviter les permissions à haut risque (SMS, Call Log, `MANAGE_EXTERNAL_STORAGE`, `QUERY_ALL_PACKAGES`, localisation en arrière-plan) si la fonctionnalité demandée peut être réalisée avec des API plus ciblées ou des sélecteurs système.
- **AccessibilityService** : si Guardian utilise cette API pour lire l'interface d'autres applications ou déclencher des actions, il ne s'agit probablement pas d'un outil d'accessibilité. Il faudra alors :
  - ne pas définir `isAccessibilityTool="true"`,
  - fournir une divulgation in-app visible et un consentement explicite,
  - remplir la déclaration Play Console,
  - éviter toute automatisation autonome et privilégier des déclenchements déterministes, étroitement liés à une demande utilisateur.
- **Foreground services** : si Guardian doit maintenir un service actif (écoute micro, localisation, synchronisation), prévoir dès Android 14 le bon `foregroundServiceType` et la permission `FOREGROUND_SERVICE_*` correspondante. Respecter l'interdiction de démarrage depuis l'arrière-plan introduite sous Android 12.
- **Localisation** : n'utiliser `ACCESS_BACKGROUND_LOCATION` que si une fonctionnalité centrale (sécurité, suivi d'itinéraire, etc.) l'exige et que l'on peut fournir la vidéo + formulaire + divulgation requis.
- **Stockage** : utiliser par défaut le stockage privé de l'application, MediaStore ou SAF. `MANAGE_EXTERNAL_STORAGE` ne doit être envisagé que pour un gestionnaire de fichiers / sauvegarde justifié.
- **Target SDK** : veiller à cibler Android 15 (API 35) pour les nouvelles soumissions et mises à jour de l'APK Luna, sauf exception Wear OS / TV.
- **Conformité Play Console** : maintenir à jour la section **Data safety**, la politique de confidentialité, la suppression de compte si applicable, et les formulaires de déclaration pour chaque permission sensible réellement utilisée.

---

*Document rédigé le 2026-07-12. Nombre de mots : 1962.*
