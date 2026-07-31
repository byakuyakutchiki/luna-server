# Modèle de permissions Android

## Objectif

Ce chapitre décrit le modèle de permissions officiel d'Android : types de permissions, mécanisme runtime, permissions personnalisées et bonnes pratiques. Il vise à guider les décisions d'implémentation de l'APK Luna / Guardian pour minimiser les privilèges requis tout en assurant les fonctionnalités nécessaires.

## Concepts clés

### Types de permissions

Android distingue plusieurs catégories de permissions, selon le niveau de risque pour l'utilisateur et le mode d'octroi.

#### Permissions normales

Les permissions normales couvrent des ressources ou des actions à faible risque pour la vie privée ou la sécurité de l'utilisateur. Elles sont accordées automatiquement au moment de l'installation de l'application, sans boîte de dialogue runtime.

Elles restent déclarées dans le fichier `AndroidManifest.xml` :

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
```

[Source non récupérée directement — URL de référence : https://developer.android.com/guide/topics/permissions/overview]

#### Permissions dangereuses (runtime permissions)

Les permissions dangereuses donnent accès à des données sensibles ou à des fonctionnalités potentiellement invasives (microphone, caméra, localisation, contacts, etc.). Depuis Android 6.0 (niveau d'API 23), elles doivent être demandées à l'exécution, en plus d'être déclarées dans le manifeste.

Caractéristiques officielles :

- L'application doit vérifier l'état de la permission avant chaque utilisation d'une API protégée.
- La demande s'effectue via `requestPermissions()` ou l'API Activity Result moderne (`ActivityResultContracts.RequestPermission`).
- L'utilisateur peut révoquer une permission dangereuse à tout moment via les paramètres système.
- À partir d'Android 11 (niveau d'API 30), si l'utilisateur refuse la permission deux fois (ou choisit "Ne plus demander"), l'application ne peut plus afficher la boîte de dialogue système pour cette permission.

Exemple de permissions dangereuses :

- `RECORD_AUDIO`
- `CAMERA`
- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION`
- `READ_CONTACTS`
- `READ_EXTERNAL_STORAGE` (comportement modifié par Scoped Storage)

[Source non récupérée directement — URL de référence : https://developer.android.com/training/permissions/requesting]

#### Permissions spéciales

Les permissions spéciales sont des permissions particulièrement sensibles qui ne peuvent généralement pas être accordées via la boîte de dialogue runtime standard. Elles nécessitent souvent une navigation vers les paramètres système ou une justification spécifique.

Exemples :

- `SYSTEM_ALERT_WINDOW` : afficher une fenêtre superposée à d'autres applications. Nécessite l'action `Settings.ACTION_MANAGE_OVERLAY_PERMISSION`.
- `WRITE_SETTINGS` : modifier les paramètres système. Nécessite l'action `Settings.ACTION_MANAGE_WRITE_SETTINGS`.
- `MANAGE_EXTERNAL_STORAGE` : accéder à l'ensemble du stockage partagé (réservé à certains cas, très restreint sur Google Play).

Ces permissions sont soumises à des politiques strictes, notamment sur Google Play.

[Source non récupérée directement — URL de référence : https://developer.android.com/reference/android/Manifest.permission]

### Cycle de vie d'une permission runtime

Le mécanisme runtime suit généralement les étapes suivantes :

1. **Déclaration dans le manifeste** : la permission doit être présente dans `AndroidManifest.xml`, sinon la demande runtime échoue silencieusement.
2. **Vérification au moment de l'utilisation** : utiliser `ContextCompat.checkSelfPermission()` pour tester si la permission est accordée.
3. **Explication si nécessaire** : si la méthode `shouldShowRequestPermissionRationale()` renvoie `true`, l'application doit expliquer à l'utilisateur pourquoi la permission est nécessaire avant de redemander.
4. **Demande** : appeler `requestPermissions()` ou l'API `ActivityResultContracts` pour afficher la boîte de dialogue système.
5. **Gestion de la réponse** : traiter le résultat dans `onRequestPermissionsResult()` ou dans le callback de l'Activity Result.

Il est recommandé de ne demander une permission qu'au moment où elle est réellement nécessaire, et non au lancement de l'application.

[Source non récupérée directement — URL de référence : https://developer.android.com/training/permissions/requesting]

### Permissions personnalisées (custom permissions)

Une application peut déclarer ses propres permissions via l'élément `<permission>` dans `AndroidManifest.xml`, avec un attribut `android:protectionLevel` défini.

```xml
<permission
    android:name="com.luna.guardian.permission.ACCESS_DATA"
    android:label="@string/permission_label"
    android:description="@string/permission_description"
    android:protectionLevel="dangerous" />
```

Valeurs principales de `protectionLevel` :

- `normal` : accord automatique à l'installation.
- `dangerous` : demande runtime requise.
- `signature` : accord automatique uniquement aux applications signées avec le même certificat.
- `signatureOrSystem` : limité aux applications système ou signées avec le même certificat (usage rare et déconseillé pour les applications standards).

Lorsqu'une application expose un composant protégé par une permission personnalisée (`android:permission` sur un `Activity`, `Service`, `BroadcastReceiver` ou `ContentProvider`), les applications clientes doivent déclarer `<uses-permission>` correspondant pour y accéder.

[Source non récupérée directement — URL de référence : https://developer.android.com/guide/topics/manifest/permission-element]

### Évolutions notables par niveau d'API

- **API 23 (Android 6.0)** : introduction du modèle runtime pour les permissions dangereuses.
- **API 29 (Android 10)** : restrictions renforcées sur l'accès à la localisation en arrière-plan ; nouvelle permission `ACCESS_BACKGROUND_LOCATION`.
- **API 30 (Android 11)** : introduction de `MANAGE_EXTERNAL_STORAGE` ; refus définitif de la permission possible après deux refus.
- **API 31 (Android 12)** : restrictions sur l'obtention de certaines informations via Bluetooth (permissions `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT`, `BLUETOOTH_ADVERTISE`).
- **API 33 (Android 13)** : introduction de la permission runtime `POST_NOTIFICATIONS`.
- **API 34 (Android 14)** : renforcement du contrôle des services de premier plan (foreground services) avec des types de service explicites et des permissions associées.

### Bonnes pratiques

- Demander uniquement les permissions strictement nécessaires.
- Demander une permission au moment de l'action, pas au lancement.
- Fournir une explication claire avant de redemander une permission refusée.
- Gérer correctement le refus définitif en proposant une redirection vers les paramètres système si la fonctionnalité est critique.
- Prévoir un dégradé gracieux (fallback UX) lorsqu'une permission est refusée.
- Tester le comportement de l'application lorsque chaque permission est refusée ou révoquée.
- Éviter les permissions spéciales (overlay, stockage global) sauf justification impérative, en raison des restrictions Google Play.

[Source non récupérée directement — URL de référence : https://developer.android.com/training/permissions/usage-notes]

## Références officielles

- Permissions overview — https://developer.android.com/guide/topics/permissions/overview
- Request runtime permissions — https://developer.android.com/training/permissions/requesting
- Best practices for permissions — https://developer.android.com/training/permissions/usage-notes
- Define custom permissions (`<permission>`) — https://developer.android.com/guide/topics/manifest/permission-element
- Permissions API reference — https://developer.android.com/reference/android/Manifest.permission

[Sources non récupérées directement — URLs de référence]

## Implications pour Guardian / Kimi

Pour l'assistant IA Guardian et l'APK Luna, les points suivants sont déterminants :

- **Microphone** : la fonctionnalité vocale de Guardian nécessite `RECORD_AUDIO`, permission dangereuse demandée à l'exécution. Elle doit être vérifiée immédiatement avant chaque session d'écoute.
- **Localisation** : si Guardian exploite la géolocalisation, il faut distinguer localisation au premier plan (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`) et localisation en arrière-plan (`ACCESS_BACKGROUND_LOCATION`), cette dernière étant très restreinte par Google Play.
- **Caméra** : tout accès à la caméra nécessite `CAMERA`, permission dangereuse.
- **Overlay / fenêtre flottante** : si l'interface de Guardian doit s'afficher par-dessus d'autres applications, cela nécessite `SYSTEM_ALERT_WINDOW`, permission spéciale avec navigation vers les paramètres système et forte probabilité de rejet sur Google Play.
- **Services d'accessibilité** : si Guardian utilise un `AccessibilityService`, aucune permission classique du modèle runtime ne suffit. Cela relève d'une déclaration de service avec l'intent-filter `android.accessibilityservice.AccessibilityService`, et est soumis à une politique Google Play très stricte.
- **Stockage** : éviter `READ_EXTERNAL_STORAGE` / `WRITE_EXTERNAL_STORAGE` au profit des APIs Scoped Storage (MediaStore, Storage Access Framework). Réserver `MANAGE_EXTERNAL_STORAGE` aux cas justifiés et acceptés par Google Play.
- **Permissions personnalisées** : si Luna expose un ContentProvider ou un Service interne à d'autres composants, utiliser des permissions `signature` pour limiter l'accès aux APKs signés par le même certificat.
- **Stratégie générale** : privilégier le principe du moindre privilège, documenter chaque permission dans la fiche Play Store, et prévoir des parcours utilisateurs cohérents en cas de refus.
