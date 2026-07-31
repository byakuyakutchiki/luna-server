# Cycle de vie des applications Android

## Objectif

Ce chapitre décrit les quatre composants applicatifs fondamentaux d'Android, leurs cycles de vie respectifs et les règles de gestion des ressources qui en découlent. L'objectif est de fournir une base stable pour concevoir l'application Guardian/Luna sans inventer de comportements système.

## Concepts clés

### Les quatre composants applicatifs

Une application Android est constituée de quatre types de composants, chacun étant un point d'entrée distinct avec son propre cycle de vie :

- **Activity** : point d'entrée d'interaction avec l'utilisateur, associée à une interface.
- **Service** : composant sans interface, exécutant des opérations en arrière-plan ou fournissant une API à d'autres processus.
- **BroadcastReceiver** : composant qui reçoit des messages diffusés par le système ou par d'autres applications.
- **ContentProvider** : composant qui gère un ensemble de données partagées et contrôle leur accès.

Contrairement à de nombreux modèles applicatifs, Android ne dispose pas d'un unique point d'entrée `main()`. Le système lance chaque composant déclaré dans le fichier `AndroidManifest.xml` en fonction des intents reçus ou des événements survenus.

### Cycle de vie d'une Activity

La classe `Activity` expose six callbacks principaux qui correspondent aux transitions entre les états du cycle de vie :

| Callback | Moment d'appel |
|---|---|
| `onCreate()` | Création initiale de l'Activity. Reçoit éventuellement un `Bundle` d'état sauvegardé (`savedInstanceState`). |
| `onStart()` | L'Activity devient visible pour l'utilisateur. |
| `onResume()` | L'Activity est au premier plan et peut interagir avec l'utilisateur. |
| `onPause()` | L'Activity perd le focus (appel entrant, dialog translucent, navigation partielle). Elle peut rester visible en mode multi-fenêtre. |
| `onStop()` | L'Activity n'est plus visible. |
| `onDestroy()` | L'Activity est sur le point d'être détruite (fermeture par l'utilisateur, `finish()`, ou changement de configuration). |

Règles essentielles issues de la documentation officielle :

- `onCreate()` doit contenir l'initialisation unique de l'Activity (inflater la vue, instancier le `ViewModel`, etc.).
- Les ressources lourdes ou les opérations coûteuses doivent être libérées ou arrêtées dans `onStop()`, plutôt que dans `onPause()`, pour supporter le multi-fenêtre.
- `onPause()` ne doit pas être utilisé pour sauvegarder des données utilisateur, effectuer des appels réseau ou des transactions de base de données, car il doit s'exécuter rapidement.
- `onDestroy()` libère les ressources non encore libérées. `isFinishing()` permet de distinguer une fermeture définitive d'une destruction temporaire due à un changement de configuration.

#### Sauvegarde et restauration de l'état

Lors d'un changement de configuration (rotation, mode multi-fenêtre) ou d'une destruction de processus par le système sous pression mémoire, l'instance de l'Activity peut être recréée. La documentation recommande de combiner :

- **`ViewModel`** pour conserver l'état métier complexe pendant les changements de configuration.
- **`rememberSaveable`** (Jetpack Compose) pour l'état d'interface léger, sérialisable automatiquement dans l'état d'instance.
- **Stockage persistant** (base de données, DataStore, fichiers) pour les données utilisateur devant survivre au-delà du cycle de vie de l'Activity.

### Service

Un `Service` est un composant exécuté en arrière-plan, sans interface utilisateur. Il existe deux catégories principales :

- **Started service** : lancé par `startService()`. Le système le maintient en cours d'exécution jusqu'à ce que le service se termine lui-même (`stopSelf()`) ou qu'une autre composante l'arrête (`stopService()`).
- **Bound service** : lié par `bindService()`. Il fournit une interface de programmation (`IBinder`) à d'autres composants ou processus. Le système le maintient tant qu'au moins un client reste lié.

Points de vigilance :

- Dès Android 5.0 (API 21), la documentation recommande d'utiliser `JobScheduler` pour planifier des tâches différées de manière économe en énergie.
- Android 8.0 (API 26) a renforcé les restrictions sur les services démarrés en arrière-plan.
- Un **foreground service** doit être utilisé pour les tâches perceptibles par l'utilisateur (lecture audio, suivi d'activité physique). Il doit afficher une notification en barre d'état et déclarer le type de service correspondant.

> [Source non récupérée directement — URL de référence] pour l'overview générale des services : https://developer.android.com/guide/components/services. Les éléments ci-dessus sont confirmés par la page *Application Fundamentals* et la page *Foreground services overview*.

### BroadcastReceiver

Un `BroadcastReceiver` reçoit des messages diffusés (`Intent`) par le système ou d'autres applications. Deux modes d'enregistrement coexistent :

1. **Context-registered receiver** : enregistré dynamiquement par `registerReceiver()` et valide tant que le contexte l'est. Il faut impérativement appeler `unregisterReceiver()` pour éviter les fuites mémoire.
2. **Manifest-declared receiver** : déclaré dans `AndroidManifest.xml` par une balise `<receiver>`. Le système peut démarrer l'application pour délivrer le broadcast, même si elle n'était pas en cours d'exécution.

Restrictions et bonnes pratiques :

- À partir d'Android 8.0 (API 26), la plupart des broadcasts implicites ne peuvent plus être déclarés dans le manifeste. Ils doivent être enregistrés dans un contexte valide.
- La méthode `onReceive(Context, Intent)` s'exécute sur le thread principal et doit être rapide.
- Pour un travail long, ne pas créer de thread directement (le processus peut être tué après le retour de `onReceive()`). Les approches recommandées sont `goAsync()` avec achèvement rapide, ou le `JobScheduler` via un `JobService`.
- Depuis les versions récentes d'AndroidX, `ContextCompat.registerReceiver()` exige de préciser le flag `RECEIVER_EXPORTED` ou `RECEIVER_NOT_EXPORTED` selon que le receiver doit écouter des broadcasts externes ou internes uniquement.
- Il est déconseillé de lancer une Activity depuis un `BroadcastReceiver` ; privilégier une notification.

### ContentProvider

Un `ContentProvider` gère l'accès à un ensemble structuré de données. Il offre une interface standard entre un processus fournisseur et des processus consommateurs, en s'appuyant sur des URI de type `content://`.

Rôles principaux :

- Encapsuler le stockage sous-jacent (SQLite, fichiers, réseau, etc.) et permettre de le modifier sans impacter les consommateurs.
- Partager des données entre applications de manière sécurisée via un modèle de permissions fin, incluant des autorisations URI temporaires.
- Fournir une abstraction utilisée par des composants comme `CursorLoader` ou `AbstractThreadedSyncAdapter`.

Contrairement aux Activity, Service et BroadcastReceiver, un `ContentProvider` n'est pas activé par un `Intent` mais par des appels à un `ContentResolver` (`query()`, `insert()`, `update()`, `delete()`).

### Gestion des ressources et états de processus

Le système tue les processus pour libérer de la mémoire. La probabilité de destruction dépend de l'état du processus :

| Probabilité de destruction | État du processus | État de l'Activity |
|---|---|---|
| Minimale | Foreground (a ou va avoir le focus) | Resumed |
| Faible | Visible (sans focus) | Started / Paused |
| Élevée | Background (invisible) | Stopped |
| Maximale | Vide | Destroyed |

Bonnes pratiques :

- Libérer les ressources capteurs (micro, caméra, GPS) dès que l'application n'est plus active.
- Utiliser des composants *lifecycle-aware* pour éviter de placer la logique métier directement dans les callbacks de l'Activity.
- Sauvegarder l'état au bon niveau (UI, ViewModel, stockage persistant) en fonction de sa durée de vie attendue.

## Références officielles

- [Application Fundamentals](https://developer.android.com/guide/components/fundamentals)
- [Activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle)
- [Service overview](https://developer.android.com/guide/components/services) — [Source non récupérée directement — URL de référence]
- [Broadcasts overview](https://developer.android.com/guide/components/broadcasts)
- [Content providers overview](https://developer.android.com/guide/topics/providers/content-providers)
- [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services)

## Implications pour Guardian / Kimi

- **Veille et assistant en arrière-plan** : Guardian aura probablement recours à un foreground service pour maintenir une veille vocale ou une écoute contextuelle, car un simple service en arrière-plan serait tué ou restreint à partir d'Android 8.0 (API 26). Une notification pérenne est requise.
- **Accessibilité** : `AccessibilityService` est un cas particulier de service lié au système. Son cycle de vie est géré par le framework d'accessibilité, mais il reste soumis aux règles de foreground service et aux politiques Google Play associées.
- **Gestion des capteurs** : micro, caméra et GPS doivent être libérés dans `onPause()` ou `onStop()` selon le besoin de multi-fenêtre, afin d'éviter la consommation de batterie et les conflits avec d'autres applications.
- **État de l'interface** : utiliser `ViewModel` et `rememberSaveable` pour conserver l'état de l'UI de Guardian lors des rotations ou des interruptions (appels, notifications).
- **Réception d'événements système** : privilégier l'enregistrement contextuel des `BroadcastReceiver` (batterie, écran, connectivité) plutôt que la déclaration dans le manifeste, compte tenu des restrictions d'Android 8.0+. Préciser correctement les flags d'exportation.
- **Partage de données** : si Luna/Guardian doit partager des données entre plusieurs applications ou composants du même écosystème, un `ContentProvider` avec un modèle de permissions strict est la voie officielle. Si les données restent internes à l'application, un `ContentProvider` n'est pas obligatoire mais peut servir d'abstraction de stockage.
- **Tâches différées** : pour les synchronisations, uploads ou traitements périodiques, utiliser `WorkManager`/`JobScheduler` plutôt qu'un service démarré persistant, conformément aux recommandations officielles dès API 21.
