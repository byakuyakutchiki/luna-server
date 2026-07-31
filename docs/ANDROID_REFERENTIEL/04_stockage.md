# Stockage sur Android : Scoped Storage, fichiers privés, MediaStore et Storage Access Framework

## Objectif

Ce chapitre décrit les mécanismes de persistance des données sur Android, la distinction entre stockage privé applicatif et stockage partagé, ainsi que les API officielles permettant d'y accéder sous les contraintes du Scoped Storage. L'objectif est de fournir aux agents Luna/Guardian une base stable pour décider où et comment lire, écrire ou partager des fichiers sans enfreindre les règles de confidentialité imposées par le système.

## Concepts clés

### 1. Deux catégories physiques : stockage interne et externe

Android distingue deux emplacements physiques :

- **Stockage interne** : toujours disponible, isolé par application. C'est l'emplacement par défaut pour les données sensibles ou indispensables au démarrage de l'app.
- **Stockage externe** : plus grand, mais susceptible d'être amovible (carte SD). Il héberge à la fois des répertoires privés par application et des collections partagées (médias, documents).

### 2. Fichiers privés applicatifs (app-specific storage)

Les fichiers propres à l'application sont stockés dans des répertoires dédiés, sans nécessiter de permission d'exécution.

#### Stockage interne privé

- Répertoires obtenus par `getFilesDir()` et `getCacheDir()`.
- Aucune permission requise.
- Inaccessible aux autres applications (sandbox + SELinux).
- Supprimés lors de la désinstallation de l'application.
- À privilégier pour les données sensibles (logs vocaux, caches chiffrés, etc.).

#### Stockage externe privé

- Répertoires obtenus par `getExternalFilesDir()` et `getExternalCacheDir()`.
- Aucune permission requise à partir d'Android 4.4 (API niveau 19).
- Localisés sous `Android/data/<package>/` ; supprimés à la désinstallation.
- Attention : sur un appareil connecté en mode "transfert de fichiers" à un ordinateur, ces fichiers peuvent être lus par l'utilisateur ; ils ne doivent donc pas contenir de secrets en clair.

### 3. Permissions liées au stockage externe

Android définit trois permissions principales :

- `READ_EXTERNAL_STORAGE`
- `WRITE_EXTERNAL_STORAGE`
- `MANAGE_EXTERNAL_STORAGE`

À partir d'Android 11 (API niveau 30), la permission `WRITE_EXTERNAL_STORAGE` n'a plus d'effet sur l'accès au stockage externe. L'accès est désormais fondé sur l'usage du fichier plutôt que sur son chemin absolu.

`MANAGE_EXTERNAL_STORAGE`, introduite avec Android 11, donne un accès élargi à l'ensemble du stockage partagé. Son utilisation est réservée à des cas très spécifiques (gestionnaires de fichiers, antivirus, sauvegardes) et soumise à une déclaration et à une validation Google Play.

### 4. Scoped Storage

Le Scoped Storage est le modèle de stockage par défaut pour les applications ciblant Android 10 (API niveau 29) et supérieur.

Ses règles principales sont :

- L'application accède sans permission à son propre répertoire app-specific externe.
- Elle accède sans permission aux médias qu'elle a elle-même créés dans les collections partagées.
- Elle ne peut pas lister ou lire librement l'ensemble du stockage externe via des chemins de type `/sdcard/`.
- Pour lire des médias créés par d'autres applications, `READ_EXTERNAL_STORAGE` est nécessaire sur Android 11 et supérieur.
- Pour les documents et autres fichiers non média, il faut utiliser le Storage Access Framework.

Une désactivation temporaire était possible sur Android 10 via `android:requestLegacyExternalStorage="true"` dans le manifeste. Cette option est ignorée sur Android 11 et supérieur, et elle ne constitue pas une solution durable sur le Play Store.

### 5. MediaStore

`MediaStore` est l'API officielle pour accéder aux collections de médias partagées : images, vidéos, audio. Depuis Android 10 (API niveau 29), elle expose également `MediaStore.Files` pour d'autres types de fichiers partagés.

Principales caractéristiques :

- Requêtage via `ContentResolver` sur les URI publiques (`MediaStore.Images.Media.EXTERNAL_CONTENT_URI`, etc.).
- Lecture et modification des fichiers créés par l'application elle-même sans permission particulière (sauf sur Android 9 et inférieur).
- Modification ou suppression de fichiers créés par d'autres applications soumise au consentement de l'utilisateur ; sur Android 10 et supérieur, cela se traduit par une `RecoverableSecurityException` fournissant un `IntentSender` à lancer.
- L'API ne garantit pas un accès direct par chemin de fichier ; il faut privilégier les URI de contenu et les `FileDescriptor`.

Exemple minimal de requête d'images via `MediaStore` :

```kotlin
val projection = arrayOf(MediaStore.Images.Media._ID, MediaStore.Images.Media.DISPLAY_NAME)
val cursor = contentResolver.query(
    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
    projection,
    null,
    null,
    null
)
cursor?.use {
    val idColumn = it.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
    while (it.moveToNext()) {
        val id = it.getLong(idColumn)
        val contentUri = ContentUris.withAppendedId(
            MediaStore.Images.Media.EXTERNAL_CONTENT_URI, id
        )
        // Utiliser contentUri (Glide, FileDescriptor, etc.)
    }
}
```

### 6. Storage Access Framework (SAF)

Le Storage Access Framework permet à l'utilisateur de sélectionner des fichiers ou des répertoires via le sélecteur système, sans que l'application ait besoin de permissions de stockage globales.

Mécanismes principaux :

- L'application lance un intent (`ACTION_OPEN_DOCUMENT`, `ACTION_CREATE_DOCUMENT`, `ACTION_OPEN_DOCUMENT_TREE`).
- Le système retourne une URI de contenu (`content://`) que l'application peut lire ou écrire.
- L'application peut conserver l'accès entre les sessions grâce à `takePersistableUriPermission()`.

Niveaux API à noter :

- `ACTION_OPEN_DOCUMENT` et `ACTION_CREATE_DOCUMENT` : API niveau 19 et supérieur.
- `ACTION_OPEN_DOCUMENT_TREE` : API niveau 21 et supérieur.

Exemple minimal d'ouverture d'un document :

```kotlin
val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
    addCategory(Intent.CATEGORY_OPENABLE)
    type = "application/pdf"
}
startActivityForResult(intent, REQUEST_CODE_OPEN_DOCUMENT)
```

### 7. Tableau de décision rapide

| Type de données | Emplacement recommandé | API | Permission requise |
|---|---|---|---|
| Données sensibles / critiques | Stockage interne | `getFilesDir()`, `getCacheDir()` | Aucune |
| Gros fichiers propres à l'app | Stockage externe app-specific | `getExternalFilesDir()` | Aucune (API 19+) |
| Médias partagés avec d'autres apps | Collections partagées | `MediaStore` | `READ_EXTERNAL_STORAGE` pour les fichiers d'autres apps (API 30+) |
| Documents importés/exportés par l'utilisateur | Espace utilisateur | Storage Access Framework | Aucune |
| Accès total au stockage partagé | Tout le stockage | `MANAGE_EXTERNAL_STORAGE` | Cas justifiés uniquement |

## Références officielles

- [Data and file storage overview](https://developer.android.com/guide/topics/data/data-storage) — developer.android.com
- [Scoped Storage](https://developer.android.com/training/data-storage#scoped-storage) — developer.android.com *[Source non récupérée directement — URL de référence]*
- [MediaStore API](https://developer.android.com/reference/android/provider/MediaStore) — developer.android.com *[Source non récupérée directement — URL de référence]*
- [Storage Access Framework](https://developer.android.com/guide/topics/providers/document-provider) — developer.android.com *[Source non récupérée directement — URL de référence]*
- [Manage all files on a storage device](https://developer.android.com/training/data-storage/manage-all-files) — developer.android.com *[Source non récupérée directement — URL de référence]*

## Implications pour Guardian / Kimi

### Développement de Guardian

- **Ne jamais présumer d'un accès global au stockage externe** : les chemins absolus de type `/sdcard/` ou `Environment.getExternalStorageDirectory()` ne sont plus fiables et sont interdits en écriture sous Scoped Storage. Toute logique historique reposant sur ces chemins doit être migrée.
- **Données sensibles en stockage interne** : les enregistrements vocaux, transcriptions, logs de debug ou caches d'inférence doivent résider dans `getFilesDir()` ou `getCacheDir()`. Le stockage externe app-specific n'est acceptable que pour des fichiers volumineux non sensibles.
- **Partage de médias via MediaStore** : si Guardian sauvegarde des captures d'écran, extraits audio ou vidéos destinés à être visibles par la galerie ou d'autres applications, utiliser `MediaStore` avec les collections appropriées. Ne pas tenter d'écrire directement dans un dossier public.
- **Import/export de documents via SAF** : pour permettre à l'utilisateur de charger ou d'exporter un fichier (PDF de synthèse, configuration, rapport), utiliser `ACTION_OPEN_DOCUMENT` ou `ACTION_CREATE_DOCUMENT` puis travailler avec l'URI retournée.
- **Éviter `MANAGE_EXTERNAL_STORAGE`** : cette permission n'est justifiée que pour un gestionnaire de fichiers explicite. Guardian n'en a normalement pas besoin. Si un scénario l'exigeait, il faudrait une déclaration Google Play et une validation par Ludovic.
- **Gestion des exceptions** : sur Android 10 et supérieur, toute modification d'un média créé par une autre application doit gérer `RecoverableSecurityException` en proposant une boîte de dialogue de confirmation à l'utilisateur.

### Tests et déploiement (Kimi)

- Valider le comportement sur Android 10 (API 29), 11 (API 30), 12/13 (API 31/33) et 14+ (API 34+) avec `targetSdkVersion` correspondant au niveau le plus récent supporté par le projet.
- Vérifier que `requestLegacyExternalStorage` n'est pas utilisé comme solution de contournement sur les versions récentes.
- Tester les scénarios "première installation", "mise à jour depuis une ancienne version" et "désinstallation/réinstallation" pour s'assurer que les fichiers internes sont bien purgés et que les médias partagés survivent correctement.
- Sur un appareil connecté en mode MTP/transfert de fichiers, vérifier qu'aucun fichier sensible du répertoire app-specific externe n'est lisible en clair.

*Point d'attention explicite* : ce chapitre synthétise la documentation officielle Android. Les comportements détaillés (notamment les conditions exactes de récupération des permissions et les restrictions du Play Store) évoluent à chaque version ; les liens non récupérés directement doivent être revérifiés avant toute décision de conception définitive.
