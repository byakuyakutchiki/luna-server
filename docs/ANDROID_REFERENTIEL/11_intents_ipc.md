# Intents explicites/implicités, PendingIntent, URI permissions, IPC

## Objectif

Ce chapitre résume les mécanismes officiels de communication inter-applications (IPC) sur Android : `Intent`, `PendingIntent`, permissions d'URI et résolution de filtres. Il vise à fournir une base stable pour décider comment Guardian et l'APK Luna peuvent déclencher, recevoir ou partager des données avec d'autres applications sans outrepasser le sandbox.

## Concepts clés

### 1. `Intent` : rôle et types

Un `Intent` est un objet de messagerie utilisé pour demander une action à un composant Android. Les trois cas d'usage officiels sont :

- **Démarrer une `Activity`** : `startActivity()`.
- **Démarrer un `Service`** : `startService()` ou `bindService()`.
- **Diffuser un message** : `sendBroadcast()` / `sendOrderedBroadcast()`.

Source : [Intents and intent filters](https://developer.android.com/guide/components/intents-filters).

Android distingue deux types d'intents :

| Type | Définition | Usage typique |
|------|------------|---------------|
| **Explicite** | Spécifie le `ComponentName` cible (package + classe). | Navigation interne, lancement de ses propres services. |
| **Implicite** | Déclare une action générique (`ACTION_VIEW`, `ACTION_SEND`, etc.) sans cible précise. | Déléguer une action à une autre application (partage, ouverture d'URL, etc.). |

### 2. Intent explicite

Un intent explicite doit définir le nom de composant via `setComponent()`, `setClass()`, `setClassName()` ou le constructeur `Intent(Context, Class)`.

**Extrait officiel — lancement explicite d'un service :**

```kotlin
val downloadIntent = Intent(this, DownloadService::class.java).apply {
    data = Uri.parse(fileUrl)
}
startService(downloadIntent)
```

**Règle de sécurité :** il faut toujours utiliser un intent **explicite** pour démarrer ou lier un `Service`, et ne pas déclarer de `<intent-filter>` pour ses propres services. À partir d'Android 5.0 (API 21), `bindService()` avec un intent implicite lève une exception.

### 3. Intent implicite et filtres (`<intent-filter>`)

Un intent implicite est résolu par le système en comparant l'action, les données (URI + MIME type) et les catégories avec les `<intent-filter>` déclarés dans le manifeste des autres applications.

**Extrait officiel — intent implicite de partage :**

```kotlin
val sendIntent = Intent().apply {
    action = Intent.ACTION_SEND
    putExtra(Intent.EXTRA_TEXT, textMessage)
    type = "text/plain"
}

try {
    startActivity(sendIntent)
} catch (e: ActivityNotFoundException) {
    // Gérer l'absence d'application susceptible de répondre
}
```

Pour recevoir un intent implicite, un composant doit déclarer un `<intent-filter>` avec, au minimum, la catégorie `CATEGORY_DEFAULT` pour les activités. Exemple :

```xml
<activity android:name="ShareActivity" android:exported="false">
    <intent-filter>
        <action android:name="android.intent.action.SEND"/>
        <category android:name="android.intent.category.DEFAULT"/>
        <data android:mimeType="text/plain"/>
    </intent-filter>
</activity>
```

**Attention :** un `<intent-filter>` ne constitue pas une mesure de sécurité. Un autre développeur peut toujours cibler le composant avec un intent explicite s'il en connaît le nom. Pour restreindre un composant à l'application elle-même, définir `android:exported="false"` et ne pas déclarer de filtre.

**Android 12 (API 31) — `android:exported` obligatoire :** tout composant possédant un `<intent-filter>` doit déclarer explicitement `android:exported`. Sans cela, l'application ne peut pas être installée sur Android 12+.

**Android 13 (API 33) — matching renforcé :** lorsqu'une application cible Android 13+, un intent provenant d'une application externe doit correspondre à la fois à l'**action** et aux **catégories** déclarées dans le `<intent-filter>` du composant exporté. Sinon, `ActivityNotFoundException` est levée. Ce comportement s'applique indépendamment du SDK de l'application émettrice.

### 4. `PendingIntent`

Un `PendingIntent` encapsule un `Intent` et permet à une autre application de l'exécuter ultérieurement avec l'identité et les permissions de l'application qui l'a créé.

Cas d'usage officiels :

- Action associée à une `Notification`.
- Action sur un `AppWidget`.
- Alarme planifiée via `AlarmManager`.

**Extrait officiel — PendingIntent immutable (recommandé) :**

```kotlin
val pendingIntent = PendingIntent.getActivity(
    applicationContext,
    REQUEST_CODE,
    intent,
    PendingIntent.FLAG_IMMUTABLE
)
```

**Mutabilité obligatoire depuis Android 12 (API 31) :** chaque `PendingIntent` doit spécifier `FLAG_IMMUTABLE` ou `FLAG_MUTABLE`. Sinon, `IllegalArgumentException`. La documentation recommande `FLAG_IMMUTABLE` par défaut. `FLAG_MUTABLE` n'est nécessaire que dans des cas précis : réponse directe dans une notification, bulles de conversation, `CarAppExtender`, mises à jour de localisation, alarmes récurrentes nécessitant `EXTRA_ALARM_COUNT`.

**Bonnes pratiques :**

- Toujours encapsuler un `PendingIntent` dans un **intent explicite**.
- Privilégier `FLAG_IMMUTABLE`.
- Ne jamais transmettre d'intents sensibles comme extras `Parcelable` / `Serializable` à des applications tierces.

### 5. URI permissions

Les permissions d'URI permettent de concéder un accès temporaire à une URI `content://` sans accorder une permission globale permanente.

Flags officiels :

- `Intent.FLAG_GRANT_READ_URI_PERMISSION`
- `Intent.FLAG_GRANT_WRITE_URI_PERMISSION`

Ces flags ne concèdent que l'accès à l'URI spécifique, pas à l'ensemble du `ContentProvider`. La durée de validité dépend du contexte : par exemple, pour une URI reçue via `startActivityForResult()`, la permission dure jusqu'à la fin de l'`Activity` receveuse.

**Exemple — accorder une permission de lecture sur une URI :**

```kotlin
val shareIntent = Intent(Intent.ACTION_SEND).apply {
    type = "image/jpeg"
    putExtra(Intent.EXTRA_STREAM, photoUri)
    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
}
startActivity(Intent.createChooser(shareIntent, "Partager"))
```

Le fournisseur doit autoriser cette délégation via `android:grantUriPermissions="true"` dans le manifeste, ou via des balises `<grant-uri-permission>` plus restrictives.

### 6. IPC et sécurité

Sur Android, l'IPC principal entre applications passe par :

- **`Intent`** : explicite (interne) ou implicite (délégation).
- **`ContentProvider`** : accès structuré aux données via `ContentResolver`, avec permissions déclaratives.
- **`PendingIntent`** : exécution différée au nom de l'application émettrice.
- **AIDL / Messenger** : hors scope de ce chapitre, réservé aux services liés de bas niveau.

**Recommandations de sécurité :**

- Ne pas exporter de composant inutilement (`android:exported="false"`).
- Nettoyer et valider les extras extraits d'un intent reçu avant de les réutiliser.
- Éviter les *nested intents* : un intent passé en extra d'un autre intent. Si nécessaire, utiliser un `PendingIntent` à la place.
- Sur Android 12+, `StrictMode.detectUnsafeIntentLaunch()` permet de détecter les lancements d'intents non sûrs en phase de debug.

## Références officielles

- [Intents and intent filters](https://developer.android.com/guide/components/intents-filters) — Android Developers
- [PendingIntent](https://developer.android.com/reference/android/app/PendingIntent) — Android Developers
- [Interacting with other apps](https://developer.android.com/training/basics/intents) — Android Developers
- [Content provider basics — Permissions](https://developer.android.com/guide/topics/providers/content-provider-basics#Permissions) — Android Developers
- [Content providers](https://developer.android.com/guide/topics/providers/content-providers) — Android Developers

[Source non récupérée directement — URL de référence] : `https://developer.android.com/training/basics/intents`

## Implications pour Guardian / Kimi

### Ce que cela change concrètement

1. **Communication avec des applications tierces** : Guardian peut déclencher des actions dans d'autres apps (appeler, ouvrir une URL, partager un fichier, ouvrir une photo, lancer la navigation) uniquement via des **intents implicites**. Il ne peut pas forcer une application spécifique à s'ouvrir si elle n'expose pas de filtre correspondant.

2. **Réception d'intents par Guardian** : si Luna/Guardian doit apparaître comme une cible de partage (`ACTION_SEND`) ou gérer des schémas d'URI personnalisés, il faut déclarer des `<intent-filter>` avec `android:exported="true"` et respecter le matching renforcé d'Android 13+.

3. **Notifications et actions à distance** : toute notification Guardian qui ouvre une activité ou déclenche une action en arrière-plan doit utiliser un `PendingIntent`. Sur Android 12+, il faut systématiquement spécifier `FLAG_IMMUTABLE` (ou `FLAG_MUTABLE` si le système doit modifier l'intent).

4. **Partage sécurisé de fichiers** : pour envoyer un enregistrement vocal, une capture d'écran ou un document à une autre application, Guardian doit utiliser `FileProvider` et accorder une **URI permission** temporaire (`FLAG_GRANT_READ_URI_PERMISSION`). Il ne doit jamais exposer ses répertoires privés via des permissions globales.

5. **Pas d'IPC magique** : Guardian ne peut pas lire les données internes d'une autre application, ni injecter du code dans le processus d'une tierce app. Les seuls canaux officiels sont les intents, les providers accessibles et les permissions d'URI accordées par l'utilisateur ou par une autre application.

6. **Stabilité des tests terrain** : Kimi doit vérifier, sur un vrai appareil, que chaque intent implicite lancé par Guardian possède au moins une cible (`resolveActivity(packageManager) != null`) et gérer les cas où l'application cible est absente, désactivée ou restreinte par le fabricant.
