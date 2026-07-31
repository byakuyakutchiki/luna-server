# 12 — Notifications, canaux, runtime permission POST_NOTIFICATIONS

## Objectif

Ce chapitre formalise les règles officielles de publication de notifications sur Android : création de canaux, gestion de l'importance, demande runtime de `POST_NOTIFICATIONS` à partir d'Android 13, et obligations liées aux services premiers plans. Il vise à éviter les échecs de publication de notifications et les blocages utilisateur pour Guardian et l'APK Luna.

## Concepts clés

### Notifications et canaux (Android 8.0, API 26)

À partir d'Android 8.0 (API 26), **toute notification doit être associée à un canal** (`NotificationChannel`). Le canal définit le comportement visuel et sonore commun à toutes les notifications qui lui sont rattachées. L'utilisateur conserve le contrôle final sur chaque canal via les paramètres système.

Un canal est créé puis enregistré auprès du système :

```kotlin
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
    val name = getString(R.string.channel_name)
    val descriptionText = getString(R.string.channel_description)
    val importance = NotificationManager.IMPORTANCE_DEFAULT
    val channel = NotificationChannel(CHANNEL_ID, name, importance).apply {
        description = descriptionText
    }
    val notificationManager = getSystemService(NotificationManager::class.java)
    notificationManager.createNotificationChannel(channel)
}
```

Une fois le canal soumis au système, **l'application ne peut plus modifier son importance ni ses comportements** (vibreur, son, lumière). Seul l'utilisateur peut les changer. Recréer un canal existant avec les mêmes valeurs est sans effet, il est donc sûr d'appeler cette méthode au démarrage de l'application.

### Importance et priorité

L'importance d'un canal (`NotificationManager.IMPORTANCE_*`) détermine comment une notification interrompt l'utilisateur :

| Niveau utilisateur | Importance (API 26+) | Priorité (API ≤ 25) |
|---|---|---|
| Urgent : son + heads-up | `IMPORTANCE_HIGH` | `PRIORITY_HIGH` / `PRIORITY_MAX` |
| Haut : son | `IMPORTANCE_DEFAULT` | `PRIORITY_DEFAULT` |
| Moyen : pas de son | `IMPORTANCE_LOW` | `PRIORITY_LOW` |
| Bas : pas de son, pas dans la barre d'état | `IMPORTANCE_MIN` | `PRIORITY_MIN` |
| Aucune : complètement silencieuse | `IMPORTANCE_NONE` | N/A |

Pour supporter les appareils sous Android 7.1 (API 25) et inférieur, il faut également appeler `setPriority()` sur le `NotificationCompat.Builder`.

### Permission runtime POST_NOTIFICATIONS (Android 13, API 33)

À partir d'Android 13 (API 33), publier une notification non exemptée — y compris la notification d'un service premier plan — nécessite la permission `android.permission.POST_NOTIFICATIONS`. Elle doit être déclarée dans le manifeste :

```xml
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

Sur les appareils Android 13+, l'application doit demander cette permission à l'exécution, comme n'importe quelle permission dangereuse. Si l'utilisateur refuse, `NotificationManagerCompat.notify()` ne publie rien. La permission peut être redemandée si l'utilisateur ne l'a pas définitivement refusée (`shouldShowRequestPermissionRationale()`).

L'extrait officiel de vérification avant publication est le suivant :

```kotlin
with(NotificationManagerCompat.from(context)) {
    if (ActivityCompat.checkSelfPermission(
            context,
            Manifest.permission.POST_NOTIFICATIONS
        ) != PackageManager.PERMISSION_GRANTED
    ) {
        // Demander la permission via ActivityCompat.requestPermissions()
        return@with
    }
    notify(notificationId, builder.build())
}
```

### Notification de service premier plan

Un service premier plan (Foreground Service) doit afficher une notification visible en permanence pendant son exécution. Cette notification fait partie des notifications soumises à `POST_NOTIFICATIONS` sur Android 13+. Si l'utilisateur refuse la permission, le service ne peut pas afficher sa notification obligatoire, ce qui peut empêcher le démarrage ou le maintien du service selon les règles de la plateforme.

### Actions et PendingIntent

Une notification doit réagir au toucher. L'action principale est définie par un `PendingIntent` passé à `setContentIntent()`. Des actions secondaires (jusqu'à trois) peuvent être ajoutées via `addAction()`. Les `PendingIntent` doivent être créés avec `FLAG_IMMUTABLE` sauf cas explicite nécessitant `FLAG_MUTABLE` (par exemple réponse directe avec `RemoteInput`).

### Cycle de vie et suppression

Une notification reste visible jusqu'à ce que :
- l'utilisateur l'efface ;
- l'utilisateur appuie dessus et `setAutoCancel(true)` est activé ;
- l'application appelle `cancel(notificationId)` ou `cancelAll()` ;
- le délai `setTimeoutAfter()` est écoulé.

Pour mettre à jour une notification existante, il suffit d'appeler à nouveau `notify()` avec le même identifiant.

### Groupement de canaux

Les canaux peuvent être regroupés via `NotificationChannelGroup` afin de les organiser dans les paramètres système, notamment lorsque l'application gère plusieurs comptes ou contextes (par exemple personnel / professionnel).

## Références officielles

- [Notifications overview](https://developer.android.com/develop/ui/views/notifications) — developer.android.com
- [Create a notification](https://developer.android.com/develop/ui/views/notifications/build-notification) — developer.android.com
- [Create and manage notification channels](https://developer.android.com/develop/ui/views/notifications/channels) — developer.android.com
- [Notification runtime permission](https://developer.android.com/develop/ui/views/notifications/notification-permission) — developer.android.com [Source non récupérée directement — URL de référence]
- [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services) — developer.android.com

## Implications pour Guardian / Kimi

- **Canaux dédiés obligatoires** : Guardian doit créer des canaux distincts pour les alertes critiques (haute importance), les mises à jour de statut du service et les informations générales. Cela permet à l'utilisateur de désactiver les notifications non essentielles sans perdre les alertes de sécurité.
- **Gestion du refus de `POST_NOTIFICATIONS`** : sur Android 13+, Guardian ne peut plus supposer que les notifications seront affichées. Il faut vérifier la permission avant tout `notify()`, rediriger vers les paramètres si elle est définitivement refusée, et prévoir des mécanismes de secours (UI in-app, overlay autorisé, etc.).
- **Service premier plan** : si Guardian utilise un foreground service pour rester actif, sa notification permanente devient conditionnée à `POST_NOTIFICATIONS` sur Android 13+. Le refus de la permission peut bloquer le maintien du service ; il faut tester ce scénario sur appareil réel ou émulateur API 33+.
- **Tests terrain (Kimi)** : valider manuellement que chaque canal apparaît dans les paramètres système, que les niveaux d'importance produisent bien le comportement attendu (son, vibration, heads-up), et que le refus de permission n'engendre pas de crash ou de comportement silencieux incorrect.
- **Confidentialité** : éviter d'afficher des informations sensibles dans les notifications sur écran de verrouillage. Utiliser `VISIBILITY_PRIVATE` avec une `publicVersion` si nécessaire, sachant que l'utilisateur garde le dernier mot via les paramètres système.
