# 06 — Foreground services : types, restrictions et notifications persistantes

## Objectif

Ce chapitre définit ce qu'est un *foreground service* (FGS) sur Android, quand l'utiliser, comment le déclarer, quels types de service existent et quelles restrictions de démarrage s'appliquent selon le niveau d'API. Il sert de base technique pour maintenir la protection Guardian active en arrière-plan de façon conforme.

## Concepts clés

### 1. Qu'est-ce qu'un foreground service ?

Un FGS est un `Service` qui exécute une opération *visible par l'utilisateur*. Il doit afficher une notification dans la barre d'état et indiquer que l'application consomme des ressources système. C'est le mécanisme Android pour exécuter du travail prioritaire en arrière-plan sans que l'application soit au premier plan.

Contrairement à un service d'arrière-plan simple, un FGS n'est pas tué par le système en cas de pression mémoire, tant qu'il reste associé à une notification.

### 2. Lancer et arrêter un FGS

Depuis Android 8.0 (API 26), pour démarrer un service qui va devenir un FGS, on utilise :

```java
Context.startForegroundService(Intent)
```

Le service doit ensuite appeler `startForeground(int id, Notification)` dans les 5 secondes (timeout système), sinon il est arrêté avec une `ANR`/`RemoteServiceException`.

Arrêt d'un FGS :

```java
stopForeground(int notificationBehavior); // API 24+
stopForeground(boolean removeNotification); // avant API 24
stopSelf();
```

Sur Android 7.0 (API 24) et ultérieur, `stopForeground(STOP_FOREGROUND_REMOVE)` retire la notification. Sur les versions antérieures, `stopForeground(true)` est utilisé.

### 3. Notification obligatoire

Un FGS doit fournir une notification dès son démarrage via `startForeground(id, notification)`. Cette notification est généralement persistante (`setOngoing(true)`), n'est pas dismissible par l'utilisateur et reste visible tant que le service tourne.

Depuis Android 8.0 (API 26), la notification doit être associée à un `NotificationChannel`. L'importance du canal détermine si la notification est silencieuse ou audible. Pour un service de protection en continu, un canal d'importance `LOW` est habituellement suffisant.

### 4. Déclaration dans le manifeste

Un FGS doit déclarer :

- la permission générale `FOREGROUND_SERVICE` (obligatoire depuis Android 9 / API 28) ;
- les permissions spécifiques au(x) type(s) de service utilisé(s), par exemple `FOREGROUND_SERVICE_DATA_SYNC`, `FOREGROUND_SERVICE_MICROPHONE`, etc. (API 29+) ;
- l'attribut `android:foregroundServiceType` sur la balise `<service>` (API 29+).

Exemple pour le service Guardian :

```xml
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />

<service
    android:name=".GuardianService"
    android:foregroundServiceType="microphone|dataSync"
    android:exported="false" />
```

### 5. Types de foreground service

Les types de FGS ont été introduits avec Android 10 (API 29). Ils précisent la nature de l'opération exécutée et déterminent les permissions et restrictions applicables.

| Type | Usage typique | Niveau API |
|------|---------------|------------|
| `dataSync` | Transfert de données, synchronisation, tâche utilisateur noticeable | 29+ |
| `mediaPlayback` | Lecture audio/vidéo continue | 29+ |
| `mediaProjection` | Capture d'écran / projection | 29+ |
| `phoneCall` | Appel vocal en cours | 29+ |
| `location` | Suivi de position en arrière-plan | 29+ |
| `camera` | Accès caméra en arrière-plan | 29+ |
| `microphone` | Accès micro en arrière-plan | 29+ |
| `health` | Suivi santé / fitness | 33+ |
| `remoteMessaging` | Relai de messages vers un appareil distant | 34+ |
| `systemExempted` | Cas très spécifiques exemptés par le système | 30+ |
| `shortService` | Tâche de moins de 3 minutes ne correspondant pas à un autre type | 31+ |
| `specialUse` | Cas particuliers nécessitant une justification au Play Store | 31+ |

Un service peut combiner plusieurs types avec le caractère pipe (`|`).

[Interprétation partielle — source non récupérée directement] : à partir d'Android 14 (API 34), l'utilisation de certains types sensibles (`microphone`, `camera`, `location`) est davantage restreinte : le système peut exiger que l'application ait déjà une session active correspondante ou que l'utilisateur ait explicitement lancé l'action avant que l'application passe en arrière-plan.

### 6. Restrictions au démarrage depuis l'arrière-plan

Plusieurs versions d'Android ont progressivement restreint le démarrage des FGS :

- **Android 8.0 (API 26)** : introduction de `startForegroundService()`. Un service lancé avec `startService()` en arrière-plan est considéré comme service en arrière-plan et peut être tué.
- **Android 9 (API 28)** : permission `FOREGROUND_SERVICE` requise.
- **Android 12 (API 31)** : restrictions renforcées sur le démarrage d'un FGS depuis l'arrière-plan. Quelques exceptions existent : l'application reçoit un broadcast explicite, l'utilisateur interagit avec une notification, un événement d'alarme programmée, etc.
- **Android 14 (API 34)** : pour les types `microphone`, `camera` et `location`, le démarrage depuis l'arrière-plan est limité à des conditions précises (session active, interaction utilisateur récente, etc.).
- **Android 15 (API 35)** : introduction de timeouts pour certains types, notamment `dataSync`.

[Source non récupérée directement — URL de référence] Les règles exactes des exceptions et des timeouts doivent être vérifiées dans la documentation officielle (voir références ci-dessous).

### 7. Timeouts (comportement de durée limite)

Les FGS ne sont pas conçus pour tourner indéfiniment sans contrôle. À partir d'Android 15 (API 35), des timeouts sont appliqués à certains types, notamment `dataSync`. Une fois le timeout atteint, le service doit s'arrêter ou le système le forcera.

Cela signifie qu'un FGS de type `dataSync` utilisé pour maintenir une présence permanente (comme la notification Guardian) peut être arrêté par le système après une durée prolongée, selon la version Android et la politique OEM.

[Source non récupérée directement — URL de référence]

### 8. Permissions runtime complémentaires

En plus des permissions de manifeste dédiées au FGS, les fonctionnalités protégées utilisées par le service requièrent leurs propres permissions runtime :

- `RECORD_AUDIO` pour un FGS de type `microphone` ;
- `CAMERA` pour un FGS de type `camera` ;
- `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION` pour un FGS de type `location`.

Sans ces permissions accordées par l'utilisateur, l'appel à `startForeground()` peut échouer ou être ignoré selon la version.

## Références officielles

- [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services) — page récupérée partiellement.
- [Foreground service types](https://developer.android.com/develop/background-work/services/fg-service-types) — [Source non récupérée directement — URL de référence].
- [Background work overview](https://developer.android.com/develop/background-work) — [Source non récupérée directement — URL de référence].

## Implications pour Guardian / Kimi

L'APK Luna utilise un FGS unique, `GuardianService`, pour :

- afficher une notification permanente indiquant que Guardian est actif ;
- écouter le micro en arrière-plan (type `microphone`) pour détecter des mots-clés de détresse ;
- maintenir une bulle overlay (`TYPE_APPLICATION_OVERLAY`) quand l'utilisateur l'a activée ;
- survivre à la fermeture de l'application principale (`MainActivity`).

### Décisions techniques actuelles

Le manifeste déclare :

```xml
android:foregroundServiceType="microphone|dataSync"
```

`GuardianService` appelle `startForeground()` avec un type calculé dynamiquement :

- `FOREGROUND_SERVICE_TYPE_DATA_SYNC` en base ;
- ajout de `FOREGROUND_SERVICE_TYPE_MICROPHONE` quand l'écoute est activée (API 30+).

Cela reflète le double usage : présence protectrice (`dataSync`) et écoute vocale (`microphone`).

### Contraintes connues

- L'écoute micro ne peut **pas** être démarrée automatiquement au boot. Le `BootReceiver` relance le FGS sans l'écoute (`listen=false`) ; l'écoute est réactivée uniquement quand l'utilisateur rouvre l'application. C'est conforme aux restrictions Android 12+ sur le démarrage des FGS sensibles depuis l'arrière-plan.
- Le démarrage du FGS avec écoute micro doit se faire quand l'application est au premier plan (`MainActivity.startGuardianService()` / `setGuardianProtection()`).
- Sur Android 15 (API 35), le type `dataSync` peut être soumis à un timeout. Il faudra surveiller ce comportement sur les appareils cibles et, si nécessaire, étudier le type `specialUse` avec une justification Play Store, ou redémarrer le FGS de manière contrôlée.
- La notification est construite avec `setForegroundServiceBehavior(Notification.FOREGROUND_SERVICE_IMMEDIATE)` (API 31+) pour afficher la notification immédiatement.

### Points de vigilance pour les agents

- Ne pas retirer la permission `FOREGROUND_SERVICE` ni les types associés (`DATA_SYNC`, `MICROPHONE`).
- Ne pas démarrer le FGS `microphone` depuis un état d'arrière-plan sans vérifier la compatibilité avec la version Android cible.
- Maintenir l'appel à `startForeground()` dans les 5 secondes après `onStartCommand()`.
- Tester spécifiquement le comportement au boot et après une longue période d'inactivité sur Android 14+.
- Si la politique Google Play évolue ou si un rejet survient, le type `specialUse` avec justification documentée peut être une alternative à étudier.
