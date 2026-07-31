# Work Profile : profil professionnel et séparation des données

## Objectif

Ce chapitre décrit le mécanisme *Work Profile* (profil professionnel géré) d'Android Enterprise et ses conséquences sur le développement de l'APK Luna/Guardian. Il vise à identifier les comportements système, les restrictions de sécurité et les bonnes pratiques indispensables pour qu'une application d'assistant IA fonctionne de manière fiable sur un appareil doté d'un profil professionnel.

## Concepts clés

### Définition et périmètre

Un *Work Profile* est un profil utilisateur secondaire, géré par l'administrateur IT de l'organisation, créé au sein du profil personnel de l'utilisateur. Il permet d'isoler les applications et les données professionnelles des données personnelles tout en utilisant un seul appareil physique.

- Introduit avec Android 5.0 (niveau API 21).
- Le profil professionnel dispose de son propre espace de stockage, de ses propres applications et de ses propres paramètres de sécurité.
- L'administrateur IT contrôle quelles applications sont disponibles dans le profil professionnel et quelles fonctionnalités de l'appareil sont accessibles.
- Les applications du profil professionnel affichent généralement un badge visuel distinct.

### Séparation des données

Le système maintient une isolation stricte entre le profil personnel et le profil professionnel :

- Chaque profil possède son propre répertoire de stockage privé (`/data/user/<userId>/<package>`).
- Une URI de fichier (`file://`) valide dans un profil n'est pas résolvable dans l'autre profil.
- Les préférences partagées, les bases de données et les fichiers internes d'une application ne sont pas accessibles depuis l'autre profil, même si le même package est installé dans les deux.

### Comportement des intents

Par défaut, la plupart des intents ne traversent pas la frontière entre profil personnel et profil professionnel :

- Un intent déclenché dans un profil est normalement résolu et traité dans ce même profil.
- Si aucun gestionnaire n'existe dans le profil d'origine, l'intent n'est pas automatiquement redirigé vers l'autre profil.
- L'administrateur IT peut configurer des règles autorisant certains intents à traverser la frontière ; cette politique peut changer à tout moment et n'est pas connue à l'avance par l'application.

Avant de lancer un `Activity`, un service ou toute action externe, l'application doit vérifier qu'un gestionnaire existe :

```kotlin
val timerIntent = Intent(AlarmClock.ACTION_SET_TIMER).apply {
    putExtra(AlarmClock.EXTRA_MESSAGE, message)
    putExtra(AlarmClock.EXTRA_LENGTH, seconds)
    putExtra(AlarmClock.EXTRA_SKIP_UI, true)
}

if (timerIntent.resolveActivity(packageManager) != null) {
    startActivity(timerIntent)
} else {
    // Gestion propre de l'absence de gestionnaire dans le profil courant
}
```

### Partage de fichiers entre profils

Pour partager des fichiers avec d'autres applications, y compris celles situées dans l'autre profil, il faut utiliser des URI de contenu (`content://`) et non des URI de fichier (`file://`) :

- Les URI de contenu incluent l'autorité du `FileProvider` et un identifiant de fichier, sans exposer de chemin absolu.
- Le récepteur obtient une autorisation temporaire via l'intent et peut lire le fichier via le `ContentProvider`.

Exemple officiel avec `FileProvider` :

```kotlin
val fileToShare = File(fileUriToShare)
val contentUriToShare: Uri = FileProvider.getUriForFile(
    context,
    "com.example.myapp.fileprovider",
    fileToShare
)
```

L'autorité (`com.example.myapp.fileprovider`) doit être déclarée dans le fichier manifeste dans un élément `<provider>` avec l'attribut `android:authorities`.

### Notifications et NotificationListenerService

Le comportement des écouteurs de notification diffère selon le profil :

- Une application s'exécutant dans le profil professionnel **ne peut pas** utiliser `NotificationListenerService` : le système ignore son service.
- Une application du profil personnel peut écouter les notifications, mais par défaut elle ne reçoit pas les notifications des applications du profil professionnel.
- À partir d'Android 8.0 (niveau API 26), le contrôleur de politique d'appareil (DPC) peut restreindre la liste des applications autorisées à écouter les notifications du profil professionnel via `DevicePolicyManager.setPermittedCrossProfileNotificationListeners()`.

### Cycle de vie et installation

- L'installation d'une APK via USB sur un appareil possédant un Work Profile installe l'application dans les deux profils.
- L'application peut être supprimée d'un profil tout en restant dans l'autre.
- Le profil professionnel peut être désactivé ou effacé à distance par l'administrateur IT sans affecter le profil personnel.

### Test et validation

Google fournit l'application de référence **TestDPC** pour simuler un environnement Android Enterprise, créer un Work Profile et configurer les politiques de gestion sur les appareils Android 5.0 (API 21) et ultérieurs.

Commandes ADB utiles pour cibler un profil spécifique :

```bash
# Lister les utilisateurs / profils actifs
adb shell pm list users

# Lancer une activité dans le profil professionnel (remplacer 10 par l'ID du profil)
adb shell am start --user 10 \
  -n "com.example.myapp/com.example.myapp.MainActivity" \
  -a android.intent.action.MAIN -c android.intent.category.LAUNCHER
```

## Références officielles

- [Work profiles](https://developer.android.com/work/managed-profiles) — Documentation officielle Android Developers, consultée le 2026-07-12.
- [Android Enterprise overview](https://developer.android.com/work/overview) — Documentation officielle Android Developers. [Source non récupérée directement — URL de référence]
- [Build for Android Enterprise](https://developer.android.com/work) — Portail officiel Android Enterprise.

## Implications pour Guardian / Kimi

### Conception de l'APK Luna

1. **Vérification systématique des intents** : avant tout lancement d'application externe (appel, SMS, navigation, calendrier, etc.), Guardian doit appeler `resolveActivity()` et prévoir un fallback explicite si aucun gestionnaire n'est disponible dans le profil courant. Cela est particulièrement critique pour un assistant vocal qui déclenche des actions par intent.

2. **Partage de fichiers par content URI** : si Guardian génère des captures d'écran, enregistrements audio, rapports ou pièces jointes destinés à être ouverts par une autre application, il doit impérativement utiliser un `FileProvider` avec des URI `content://`. Les URI `file://` échoueront silencieusement ou provoqueront une erreur lors d'un passage entre profils.

3. **Isolation des données** : les modèles, embeddings, caches et logs de Guardian résident dans le stockage du profil où l'application est exécutée. Si Luna est installée dans les deux profils, les deux instances sont indépendantes ; aucune donnée ne doit être supposée partagée par défaut.

4. **NotificationListenerService** : si Guardian repose sur l'écoute des notifications pour une fonctionnalité de résumé ou d'alerte, cette fonctionnalité ne fonctionnera pas dans le profil professionnel. Il faut soit la désactiver proprement, soit documenter qu'elle requiert le profil personnel. Dans le profil personnel, l'écoute des notifications du profil professionnel peut être bloquée par la politique IT.

### Tests et qualification

- Valider l'APK avec **TestDPC** en créant un Work Profile et en testant les scénarios : intents sans gestionnaire, intents autorisés/interdits à traverser, partage de fichiers.
- Tester les commandes ADB avec `--user` pour exécuter Guardian dans le profil personnel puis professionnel.
- Vérifier que l'application ne plante pas si un intent `ACTION_VIEW`, `ACTION_DIAL`, `ACTION_SEND` ou similaire ne trouve pas de récepteur dans le profil courant.

### Points d'attention pour Kimi

- Les maquettes et parcours utilisateur doivent intégrer la possibilité qu'une action déclenchée par Guardian (ouvrir une app, partager un document) soit indisponible à cause des restrictions du profil professionnel.
- Les messages d'erreur doivent être explicites et proposer une alternative lorsqu'une action inter-profil est bloquée.
