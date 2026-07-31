# Services d'accessibilité Android : `AccessibilityService`, capacités et limites

## Objectif

Ce chapitre décrit le fonctionnement officiel d'`AccessibilityService` : son cycle de vie, les capacités qu'il expose, les déclarations obligatoires et les limites système qui en font un outil d'assistance et non un mécanisme généraliste d'automation. Il vise à fournir aux agents Luna/Guardian une base factuelle pour décider si, quand et comment utiliser un service d'accessibilité dans l'APK.

## Concepts clés

### 1. Rôle officiel d'un service d'accessibilité

Un service d'accessibilité est une application qui s'exécute en arrière-plan et qui assiste des utilisateurs en situation de handicap (ou temporairement limités) en inspectant le contenu de l'écran et en interagissant avec les applications à leur place. Selon la documentation officielle :

> « Accessibility services should only be used to assist users with disabilities in using Android devices and apps. »

Le guide de développement précise :

> « Only build an accessibility service if you are creating a general-purpose assistive tool. »

Les exemples cités sont les lecteurs d'écran (TalkBack), les outils de commutation (Switch Access) et les systèmes de contrôle vocal. `AccessibilityService` n'est donc pas conçu comme une API d'automation, de scraping ou de pilotage distant d'interface générique.

### 2. Cycle de vie et activation

`AccessibilityService` hérite de `Service`, mais son cycle de vie est géré exclusivement par le système :

- Le service ne démarre que lorsque l'utilisateur l'active explicitement dans **Paramètres > Accessibilité**.
- Après le binding système, `onServiceConnected()` est appelé.
- Le service s'arrête lorsque l'utilisateur le désactive ou lorsque le service appelle `disableSelf()` (API 24).
- Il n'existe aucune API officielle pour activer un service d'accessibilité par programmation à l'insu de l'utilisateur.

La déclaration dans `AndroidManifest.xml` est obligatoire et doit respecter les deux contraintes suivantes :

- déclarer l'intent `android.accessibilityservice.AccessibilityService` ;
- exiger la permission `android.permission.BIND_ACCESSIBILITY_SERVICE` afin que seul le système puisse se lier au service.

```xml
<service android:name=".accessibility.MyAccessibilityService"
    android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
    android:exported="true"
    android:label="@string/accessibility_service_label">
    <intent-filter>
        <action android:name="android.accessibilityservice.AccessibilityService" />
    </intent-filter>
    <meta-data
        android:name="android.accessibilityservice"
        android:resource="@xml/accessibility_service_config" />
</service>
```

### 3. Configuration et capacités déclaratives

La configuration statique se fait dans un fichier XML référencé par `SERVICE_META_DATA`, par exemple `res/xml/accessibility_service_config.xml` :

```xml
<accessibility-service xmlns:android="http://schemas.android.com/apk/res/android"
    android:description="@string/accessibility_service_description"
    android:accessibilityEventTypes="typeAllMask"
    android:accessibilityFlags="flagDefault|flagRequestAccessibilityButton"
    android:accessibilityFeedbackType="feedbackSpoken"
    android:notificationTimeout="100"
    android:canRetrieveWindowContent="true"
    android:canPerformGestures="true"
    android:settingsActivity="com.example.android.apis.accessibility.ServiceSettingsActivity" />
```

Les capacités (`capabilities`) déclarables dans ce fichier incluent notamment :

- `canRetrieveWindowContent` : lecture de la hiérarchie de la fenêtre active.
- `canPerformGestures` : injection de gestes tactiles via `dispatchGesture()`.
- `canTakeScreenshot` : capture d'écran via `takeScreenshot()` / `takeScreenshotOfWindow()`.
- `canRequestTouchExplorationMode` : exploration tactile parlée.
- `canControlMagnification` : contrôle de la loupe d'écran.
- `canRequestFilterKeyEvents` : filtrage des événements clavier.
- `canRequestFingerprintGestures` : gestes sur le capteur d'empreintes (API 29+).

Les principaux flags disponibles incluent :

- `FLAG_RETRIEVE_INTERACTIVE_WINDOWS` : accès aux fenêtres interactives (nécessaire pour `getWindows()` et `findFocus()` sur plusieurs fenêtres).
- `FLAG_REQUEST_ACCESSIBILITY_BUTTON` : bouton d'accessibilité dans la barre de navigation.
- `FLAG_ENABLE_ACCESSIBILITY_VOLUME` : flux audio `STREAM_ACCESSIBILITY` indépendant.
- `FLAG_REQUEST_TOUCH_EXPLORATION_MODE` : mode exploration tactile.
- `FLAG_INPUT_METHOD_EDITOR` : transformation du service en clavier (API 33+).
- `FLAG_REPORT_VIEW_IDS` : inclusion des identifiants de vue dans `AccessibilityNodeInfo`.

Certaines propriétés sont aussi modifiables à l'exécution via `setServiceInfo()` : `eventTypes`, `feedbackType`, `flags`, `notificationTimeout` et `packageNames`.

### 4. Capacités opérationnelles

Lorsqu'un événement correspondant à la configuration est déclenché, le système appelle `onAccessibilityEvent(AccessibilityEvent)`. Le service peut ensuite explorer l'arbre d'accessibilité via `AccessibilityNodeInfo` :

```kotlin
override fun onAccessibilityEvent(event: AccessibilityEvent) {
    val sourceNode: AccessibilityNodeInfo? = event.source
    // inspection des propriétés
    sourceNode?.recycle()
}
```

Les principales capacités opérationnelles sont :

- **Lecture du contenu** : `event.source`, `getRootInActiveWindow()`, `getWindows()` (API 21), `getWindowsOnAllDisplays()` (API 30), `findFocus()`.
- **Actions sur les nœuds** : `performAction()` avec `ACTION_CLICK`, `ACTION_SCROLL_FORWARD`, `ACTION_ACCESSIBILITY_FOCUS`, etc.
- **Actions globales** : `performGlobalAction()` pour `GLOBAL_ACTION_BACK`, `GLOBAL_ACTION_HOME`, `GLOBAL_ACTION_RECENTS`, etc. La disponibilité exacte peut être vérifiée via `getSystemActions()` (API 30).
- **Injection de gestes** : `dispatchGesture()` (API 24), avec construction d'un `GestureDescription` et d'un `Path`.
- **Captures d'écran** : `takeScreenshot()` (API 30) sur un affichage, `takeScreenshotOfWindow()` (API 34) sur une fenêtre. Le résultat est fourni sous forme de `ScreenshotResult` convertible en `Bitmap` via `Bitmap.wrapHardwareBuffer`.
- **Overlays d'accessibilité** : `attachAccessibilityOverlayToDisplay()` et `attachAccessibilityOverlayToWindow()` (API 34) via un `SurfaceControl`.
- **Audio** : utilisation du flux `STREAM_ACCESSIBILITY` (avec `FLAG_ENABLE_ACCESSIBILITY_VOLUME`).
- **Capteurs d'empreintes** : `FingerprintGestureController` (API 29+).
- **Afficheurs Braille** : `BrailleDisplayController` (API 35+).

### 5. Limites et contraintes système

`AccessibilityService` est puissant, mais soumis à des limites strictes :

- **Activation utilisateur obligatoire** : le service ne fonctionne que s'il est activé manuellement. L'application doit guider l'utilisateur vers les paramètres ; elle ne peut pas l'activer silencieusement.
- **Champ restreint** : la documentation officielle limite l'usage à l'assistance aux personnes handicapées. L'utilisation à d'autres fins n'est pas couverte par le contrat officiel de l'API.
- **Contenu partiel ou absent** : une application cible peut marquer des vues `notImportantForAccessibility`, utiliser des vues personnalisées mal exposées, ou masquer des fenêtres avec `FLAG_SECURE`. Les WebView peuvent ne pas exposer tout leur contenu.
- **Données potentiellement obsolètes** : la hiérarchie de fenêtre peut changer à tout moment. `AccessibilityEvent` et les nœuds obtenus peuvent refléter un état déjà dépassé.
- **Fenêtres sécurisées** : `takeScreenshot()` retourne `ERROR_TAKE_SCREENSHOT_SECURE_WINDOW` si la fenêtre cible est marquée sécurisée.
- **Périmètre sandbox** : le service reste un processus applicatif isolé ; il n'obtient pas de privilèges root.
- **Performance** : `typeAllMask` notifie le service de chaque événement d'accessibilité sur l'ensemble du système, ce qui peut être coûteux en ressources. `notificationTimeout` permet de limiter la fréquence.
- **Gestion du focus** : le système distingue le focus de saisie (`FOCUS_INPUT`) et le focus d'accessibilité (`FOCUS_ACCESSIBILITY`). Le service ne doit pas voler le focus sans action explicite de l'utilisateur.
- **Compatibilité API** : de nombreuses capacités (gestes, captures d'écran, overlays, contrôle du clavier, afficheurs Braille) nécessitent des niveaux d'API élevés et doivent être conditionnées avec `Build.VERSION.SDK_INT`.

### 6. Distinction avec l'accessibilité applicative standard

Améliorer l'accessibilité de sa propre application ne nécessite pas de créer un `AccessibilityService`. Il suffit d'utiliser les APIs standard d'accessibilité : `contentDescription`, `Semantics` dans Jetpack Compose, tailles de cibles tactiles d'au moins 48dp × 48dp, contrastes de couleur respectés, etc. Le guide officiel recommande de ne créer un service d'accessibilité que si l'objectif est de fournir un outil d'assistance généraliste, et non d'améliorer une application existante.

## Références officielles

- [Create an accessibility service](https://developer.android.com/guide/topics/ui/accessibility/service) — Android Developers.
- [Build accessible apps](https://developer.android.com/guide/topics/ui/accessibility/apps) — Android Developers.
- [Accessibility overview](https://developer.android.com/guide/topics/ui/accessibility) — Android Developers.
- [AccessibilityService](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService) — Android Developers.
- [AccessibilityServiceInfo](https://developer.android.com/reference/android/accessibilityservice/AccessibilityServiceInfo) — Android Developers.
- [Use of the AccessibilityService API](https://support.google.com/googleplay/android-developer/answer/10964491) — Google Play Policy Center. [Source non récupérée directement — URL de référence]

## Implications pour Guardian / Kimi

### Quand un service d'accessibilité est légitime

Guardian peut justifier un `AccessibilityService` uniquement s'il se qualifie réellement comme outil d'assistance généraliste (lecture d'écran contextuelle, navigation vocale pour personnes en situation de handicap, etc.). Dans ce cas :

- déclarer `android:isAccessibilityTool="true"` dans la configuration XML ;
- fournir une description claire et une activité de paramètres ;
- prévoir la déclaration Google Play Console requise pour les applications ciblant Android 12 (API 31) et plus ;
- documenter la valeur d'accessibilité avec des captures ou une vidéo de démonstration.

### Quand il ne faut pas utiliser `AccessibilityService`

Si Guardian utilise l'API pour piloter d'autres applications de manière autonome, scraper des écrans, cliquer à la place de l'utilisateur sans action explicite, ou exécuter des automations non déterministes, cela entre en contradiction avec la documentation officielle Android et avec les politiques de distribution. Il faut alors privilégier d'autres mécanismes :

- intents explicites vers des applications partenaires ;
- notifications pour recevoir des mises à jour contextuelles ;
- Assistant / App Actions pour une intégration vocale officielle ;
- APIs publiques des applications tierces lorsqu'elles en proposent.

### Capacités exploitables avec prudence

Dans un cadre d'assistance légitime, les capacités suivantes peuvent être utiles :

- lecture du contenu de la fenêtre active pour enrichir le contexte conversationnel ;
- actions guidées par l'utilisateur (`performAction`, `performGlobalAction`) ;
- captures d'écran pour analyse visuelle (avec `canTakeScreenshot` et gestion des erreurs sécurisées) ;
- bouton d'accessibilité pour invoquer Guardian rapidement ;
- flux audio dédié pour une restitution vocale claire.

### Contraintes de développement

- **Activation manuelle** : l'APK doit gérer gracieusement le cas où le service n'est pas activé et guider l'utilisateur vers les paramètres système.
- **Tests multi-version** : les capacités varient fortement selon les niveaux d'API. Les tests doivent couvrir `minSdkVersion` et `targetSdkVersion` du projet.
- **Gestion des contenus sécurisés** : ne pas supposer que `takeScreenshot()` ou la lecture de la fenêtre fonctionneront sur des écrans bancaires, des applications de paiement ou des fenêtres `FLAG_SECURE`.
- **Performance et batterie** : éviter `typeAllMask` systématique ; restreindre `eventTypes`, `packageNames` et ajuster `notificationTimeout` au besoin réel.
- **Validation du modèle** : si un LLM génère une intention menant à une action via `AccessibilityService`, cette action doit être validée par une couche métier, jamais exécutée directement.

### Risque de rejet Google Play

L'utilisation de `AccessibilityService` est un motif de révision renforcée sur Google Play. Une application qui ne démontre pas un usage réel d'accessibilité, ou qui automatise des actions sans consentement explicite, risque le rejet ou la suspension. Ce point dépasse la documentation Android proprement dite et relève des politiques de distribution.
