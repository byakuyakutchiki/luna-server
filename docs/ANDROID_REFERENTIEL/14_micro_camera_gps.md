# 14 — Micro, caméra, localisation : permissions et bonnes pratiques

## Objectif

Définir les règles officielles d'accès aux capteurs sensibles (microphone, caméra, localisation) pour l'APK Luna/Guardian. Ce chapitre précise les permissions à déclarer, les niveaux API impliqués, les restrictions d'accès en arrière-plan et les mécanismes de transparence introduits par Android 12+.

## Concepts clés

### 1. Permissions sensibles et runtime

Les permissions `RECORD_AUDIO`, `CAMERA`, `ACCESS_FINE_LOCATION` et `ACCESS_COARSE_LOCATION` sont classées comme dangereuses (*dangerous permissions*). À partir d'Android 6.0 (API level 23), elles doivent être demandées à l'exécution, en plus de leur déclaration dans le manifeste.

### 2. Microphone

**Permission requise :**

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

Points clés :
- `RECORD_AUDIO` est une permission dangereuse : demande runtime obligatoire sur Android 6.0+.
- L'enregistrement se fait classiquement via `MediaRecorder` ou `AudioRecord`.
- À partir d'Android 9 (API level 28), une application en arrière-plan ne peut plus accéder au microphone. L'accès doit donc se faire au premier plan ou via un *foreground service* contenant l'instance `MediaRecorder`.
- Pour un signal brut sans traitement, utiliser `UNPROCESSED` après avoir vérifié `AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED`. Si ce n'est pas supporté, `VOICE_RECOGNITION` est une alternative sans AGC ni suppression de bruit.
- Toujours appeler `release()` sur l'instance `MediaRecorder` dès qu'elle n'est plus utilisée.

### 3. Caméra

**Permission requise :**

```xml
<uses-permission android:name="android.permission.CAMERA" />
```

Points clés :
- `CAMERA` est une permission dangereuse : demande runtime obligatoire sur Android 6.0+.
- La documentation officielle recommande **CameraX** pour les nouvelles applications. CameraX est une bibliothèque Jetpack compatible avec Android 5.0 (API level 21) et supérieur.
- Camera2 est l'API bas niveau, destinée aux cas d'usage complexes nécessitant un contrôle fin du pipeline caméra.
- L'utilisation de la caméra en arrière-plan est fortement restreinte ; l'accès s'effectue généralement avec une activité visible ou un service au premier plan.

### 4. Localisation

**Permissions requises selon le cas d'usage :**

```xml
<!-- Toujours inclure si l'app utilise la localisation. -->
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />

<!-- Uniquement si le produit a besoin d'une localisation précise. -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />

<!-- Uniquement pour la localisation en arrière-plan sur Android 10+. -->
<uses-permission android:name="android.permission.ACCESS_BACKGROUND_LOCATION" />
```

**Catégories d'accès :**

| Type | Conditions | Permissions |
|------|------------|-------------|
| **Foreground** | Activité visible OU *foreground service* en cours | `ACCESS_COARSE_LOCATION` et/ou `ACCESS_FINE_LOCATION` |
| **Background** | Tout autre accès à la position | `ACCESS_BACKGROUND_LOCATION` en plus (API 29+) |

Précisions :
- Sur Android 10 (API level 29) et plus, un service de localisation au premier plan doit déclarer `android:foregroundServiceType="location"`.
- Sur Android 10 (API level 29) et plus, `ACCESS_BACKGROUND_LOCATION` doit être déclarée dans le manifeste et demandée à l'exécution. Sur les versions antérieures, l'octroi de la permission de premier plan donne automatiquement l'accès en arrière-plan.
- **Précision approximative** (`ACCESS_COARSE_LOCATION`) : estimation à environ 3 km².
- **Précision fine** (`ACCESS_FINE_LOCATION`) : estimation généralement à 50 mètres près, parfois quelques mètres.
- L'utilisateur peut choisir d'accorder uniquement la localisation approximative même si l'application demande la précision fine. L'application doit continuer à fonctionner dans ce cas.
- Sur Android 10+, le système affiche une notification de rappel la première fois qu'une fonctionnalité accède à la localisation en arrière-plan après l'octroi de la permission.

### 5. Workflow de demande runtime

La documentation officielle impose un workflow en trois étapes : vérifier l'état de la permission, expliquer le besoin si nécessaire, puis demander la permission.

```kotlin
when {
    ContextCompat.checkSelfPermission(
        context,
        Manifest.permission.RECORD_AUDIO
    ) == PackageManager.PERMISSION_GRANTED -> {
        // Permission accordée : exécuter l'action.
    }
    ActivityCompat.shouldShowRequestPermissionRationale(
        activity,
        Manifest.permission.RECORD_AUDIO
    ) -> {
        // Afficher une UI éducative contextuelle.
    }
    else -> {
        // Demander la permission.
        requestPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
    }
}
```

Règles transversales :
- Demander la permission au moment où l'utilisateur déclenche la fonctionnalité concernée.
- Ne jamais bloquer l'utilisateur ; proposer une dégradation élégante si la permission est refusée.
- Ne pas supposer de regroupement stable des permissions (*permission groups*) : ils ne servent qu'à réduire le nombre de dialogues système.

### 6. Autorisations temporaires et révocation

- **Autorisation unique** : depuis Android 11 (API level 30), les dialogues de demande pour la localisation, le microphone et la caméra proposent une option **« Uniquement cette fois »**. L'application conserve l'accès tant que l'activité est visible, puis un court moment en arrière-plan, ou jusqu'à l'arrêt du service au premier plan si applicable. La révocation de cette autorisation entraîne la terminaison du processus.
- **Réinitialisation automatique** : à partir d'Android 11 (API level 30), les permissions sensibles accordées à une application non utilisée depuis plusieurs mois sont automatiquement réinitialisées par le système.
- **Révocation proactive** : à partir d'Android 13 (API level 33), l'application peut révoquer elle-même une permission devenue inutile via `revokeSelfPermissionOnKill()` ou `revokeSelfPermissionsOnKill()`.

### 7. Indicateurs de confidentialité (Android 12+)

Sur les appareils sous Android 12 (API level 31) et plus, le système expose des mécanismes de transparence pour les accès microphone, caméra et localisation :

- **Tableau de bord de confidentialité** : l'utilisateur peut consulter un historique temporel des accès à la localisation, à la caméra et au microphone par application.
- **Indicateurs visuels** : une icône apparaît dans la barre d'état lorsque le microphone ou la caméra sont utilisés.
- **Interrupteurs matériels** : depuis les paramètres rapides, l'utilisateur peut désactiver globalement l'accès au microphone et à la caméra pour toutes les applications. Dans ce cas, l'application reçoit un flux vidéo vide pour la caméra et un silence audio pour le microphone.
- L'application peut fournir une justification de ses accès en déclarant une activité avec la permission `START_VIEW_PERMISSION_USAGE` et les actions `VIEW_PERMISSION_USAGE` ou `VIEW_PERMISSION_USAGE_FOR_PERIOD`.

```kotlin
val sensorPrivacyManager = applicationContext
    .getSystemService(SensorPrivacyManager::class.java) as SensorPrivacyManager
val supportsMicrophoneToggle = sensorPrivacyManager
    .supportsSensorToggle(Sensors.MICROPHONE)
val supportsCameraToggle = sensorPrivacyManager
    .supportsSensorToggle(Sensors.CAMERA)
```

## Références officielles

- *MediaRecorder overview* — [https://developer.android.com/guide/topics/media/mediarecorder](https://developer.android.com/guide/topics/media/mediarecorder)
- *Camera2 overview* — [https://developer.android.com/media/camera/camera2](https://developer.android.com/media/camera/camera2)
- *CameraX overview* — [https://developer.android.com/media/camera/camerax](https://developer.android.com/media/camera/camerax)
- *Request location permissions* — [https://developer.android.com/develop/sensors-and-location/location/permissions](https://developer.android.com/develop/sensors-and-location/location/permissions)
- *Request runtime permissions* — [https://developer.android.com/training/permissions/requesting](https://developer.android.com/training/permissions/requesting)
- *Explain access to more sensitive information* — [https://developer.android.com/training/permissions/explaining-access](https://developer.android.com/training/permissions/explaining-access)
- *Privacy on Android* — [https://developer.android.com/privacy](https://developer.android.com/privacy) [Source non récupérée directement — URL de référence]
- *Camera (ancienne page du référentiel)* — [https://developer.android.com/guide/topics/media/camera](https://developer.android.com/guide/topics/media/camera) [Source non récupérée directement — URL de référence ; la documentation actuelle redirige vers CameraX et Camera2]
- *Location overview (ancienne page du référentiel)* — [https://developer.android.com/training/location](https://developer.android.com/training/location) [Source non récupérée directement — URL de référence ; la documentation actuelle est hébergée sous `/develop/sensors-and-location/location`]

## Implications pour Guardian / Kimi

### 1. Microphone

- **Voice trigger** : Guardian dépend de la reconnaissance vocale. La permission `RECORD_AUDIO` doit être demandée explicitement au premier lancement de la fonction vocale, pas à l'ouverture de l'application.
- **Arrière-plan** : si le *hotword* doit fonctionner hors de l'application, utiliser un *foreground service* avec une notification persistante, conformément à la restriction Android 9+.
- **Flux audio** : privilégier `VOICE_RECOGNITION` ou `UNPROCESSED` selon la capacité du terminal, afin d'éviter les traitements qui dégradent la reconnaissance.
- **Libération** : s'assurer que `MediaRecorder` / `AudioRecord` est relâché à l'arrêt du service ou en cas d'appel entrant.

### 2. Caméra

- **Cas d'usage** : si Guardian utilise la caméra (scan de QR code, visioconférence, analyse d'image), privilégier **CameraX** pour réduire la dette technique et assurer la compatibilité device.
- **Déclenchement contextuel** : ne pas demander `CAMERA` au démarrage, mais au moment de l'action (ex. : appui sur le bouton scan).
- **Indicateurs** : tenir compte du point vert dans la barre d'état sur Android 12+ ; l'utilisateur peut couper la caméra depuis les paramètres rapides.

### 3. Localisation

- **Minimiser la précision** : si Guardian n'a besoin que de la zone géographique (pays, ville), demander uniquement `ACCESS_COARSE_LOCATION`.
- **Localisation en arrière-plan** : éviter autant que possible. Si elle est nécessaire (géolocalisation d'urgence, géorepérage), déclarer `ACCESS_BACKGROUND_LOCATION` et un *foreground service* de type `location` sur Android 10+.
- **Hiérarchie des demandes** : demander `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION` d'abord, puis `ACCESS_BACKGROUND_LOCATION` uniquement après, jamais simultanément.
- **Géofencing** : utiliser les APIs officielles de geofencing, qui nécessitent la permission de localisation en arrière-plan.

### 4. Conformité et transparence

- **Privacy Dashboard** : prévoir une justification claire des accès micro/caméra/localisation, car Android 12+ permet à l'utilisateur de consulter l'historique d'accès par application.
- **Tests** : valider les parcours de demande de permissions avec UI Automator (Espresso ne peut pas interagir avec les dialogues système).
- **Gracieuseté au refus** : si l'utilisateur refuse une permission, Guardian doit continuer à fonctionner sans cette fonctionnalité, sans bloquer l'interface ni afficher de message répétitif.
- **Google Play** : les accès en arrière-plan à la localisation font l'objet d'une politique stricte. Voir le chapitre `16_restrictions_google_play.md` pour les exigences de déclaration et de justification.
