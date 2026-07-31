# Device Admin, Android Enterprise, DPC et appareils gérés

## Objectif

Ce chapitre distingue l'ancienne API *Device Administration*, aujourd'hui dépréciée, du framework moderne **Android Enterprise** et de son composant central, le *Device Policy Controller* (DPC). Il présente les modes de gestion des appareils, les mécanismes d'enrôlement et les contraintes concrètes pour le développement de l'APK Luna/Guardian.

## Concepts clés

### Device Administration API (legacy)

L'API *Device Administration* a été introduite pour permettre à une application de jouer un rôle d'administrateur de l'appareil via `DevicePolicyManager` et `DeviceAdminReceiver`. Elle offrait des capacités comme le verrouillage de l'écran, la réinitialisation du mot de passe ou l'effacement des données.

- Disponible depuis Android 2.2 (niveau API 8).
- Cette API est officiellement dépréciée au profit d'Android Enterprise. Google recommande de ne plus l'utiliser pour de nouvelles fonctionnalités et de migrer les implémentations existantes vers les solutions Android Enterprise.
- Sur les versions récentes d'Android, de nombreuses méthodes `DevicePolicyManager` liées à Device Admin sont obsolètes ou limitées ; leur comportement exact dépend du niveau API cible et du rôle de l'application (DPC, application dans un profil professionnel, etc.).

> **Note de source :** les pages `developer.android.com/guide/topics/admin/device-admin`, `developer.android.com/work/dpc` et `developer.android.com/work/overview` n'ont pas pu être récupérées directement lors de la rédaction. Les faits ci-dessus sont fondés sur la documentation officielle Android connue ; les niveaux API exacts des restrictions récentes doivent être vérifiés sur la source officielle avant toute décision de production.

### Android Enterprise

Android Enterprise est le programme et l'ensemble d'APIs destinés à la gestion des appareils Android en environnement professionnel. Il repose sur :

- un **DPC** (*Device Policy Controller*) pour appliquer les politiques sur l'appareil ;
- des **profils utilisateur Android** pour isoler les données professionnelles et personnelles ;
- des outils cloud tels que l'**Android Management API** ou la **Play EMM API** pour les fournisseurs de solutions EMM.

Principaux modes de gestion documentés par l'Android Management API :

| Mode | Description | Version minimale |
|---|---|---|
| **Work profile on personally-owned device** | Profil professionnel créé à l'intérieur du profil personnel de l'utilisateur. Seules les apps et données du profil professionnel sont gérées. | Android 5.1+ (API 22+) |
| **Work profile on company-owned device** | Appareil appartenant à l'entreprise, autorisant un usage personnel. L'entreprise peut appliquer certaines politiques à l'échelle de l'appareil. | Android 8.0+ (API 26+) |
| **Fully managed device** | Appareil appartenant à l'entreprise et entièrement géré, sans usage personnel. | Android 5.1+ (API 22+) |
| **Dedicated device** | Sous-ensemble des appareils entièrement gérés, verrouillés sur une ou quelques applications (kiosk). | Android 5.1+ (API 22+) |

### Device Policy Controller (DPC)

Le DPC est l'application chargée de recevoir et d'appliquer les politiques de gestion sur l'appareil.

- Dans le cadre de l'**Android Management API**, Google fournit l'application **Android Device Policy** (`com.google.android.apps.work.clouddpc`) comme DPC. Elle est installée automatiquement lors de l'enrôlement et applique les politiques définies dans la console EMM.
- Un fournisseur EMM peut également développer son propre DPC. Cela implique alors d'utiliser directement `DevicePolicyManager`, de gérer le cycle de vie d'administration et de respecter les exigences du programme Android Enterprise.
- Le DPC peut configurer des restrictions d'application (*managed configurations*), restreindre l'accès au matériel, verrouiller l'appareil, etc.

### Android Management API

L'Android Management API est une API REST destinée aux fournisseurs EMM. Elle permet de gérer à distance un parc d'appareils Android Enterprise.

Ressources principales identifiées dans la documentation officielle :

- `enterprises` : représente une organisation.
- `policies` : regroupe les paramètres de gestion appliqués à un appareil.
- `enrollmentTokens` : jetons utilisés pour lier un appareil à une entreprise.
- `devices` : représente un appareil enrôlé, avec son utilisateur, sa politique et son mode de gestion.

Actions courantes : créer un jeton d'enrôlement, lier une politique à un appareil, verrouiller, redémarrer, réinitialiser le mot de passe, ou effacer l'appareil via `enterprises.devices.delete`.

### Enrôlement et provisioning

Le *provisioning* est le processus par lequel un appareil est configuré pour être géré. L'Android Management API utilise des **enrollment tokens** pour déclencher ce processus.

Principales méthodes de provisioning documentées :

- **QR code** : appuyer six fois sur l'écran d'un appareil neuf ou réinitialisé, puis scanner le QR code. Disponible à partir d'Android 7.0 (API 24).
- **NFC** : bump NFC programmé avec un appareil serveur NFC. Disponible à partir d'Android 6.0 (API 23).
- **Zero-touch enrollment** : appareils préconfigurés par un revendeur agréé, s'enrôlant automatiquement au premier démarrage. Disponible à partir d'Android 8.0 (API 26), avec une prise en charge antérieure sur certains Pixel (7.1+).
- **DPC identifier** : saisir `afw#setup` lors de la configuration initiale pour télécharger Android Device Policy.
- **Enrollment token link / sign-in URL** : lien ou URL de connexion fourni à l'utilisateur pour ajouter un profil professionnel.

Le champ `allowPersonalUsage` du jeton détermine si un Work Profile peut être créé sur l'appareil :

- `PERSONAL_USAGE_ALLOWED` : autorise un Work Profile (obligatoire pour les appareils personnels).
- `PERSONAL_USAGE_DISALLOWED` : appareil entièrement géré, sans usage personnel.
- `PERSONAL_USAGE_DISALLOWED_USERLESS` : appareil dédié (*dedicated device*).

Exemple de contenu d'un QR code de provisioning (extrait officiel) :

```json
{
    "android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": "com.google.android.apps.work.clouddpc/.receivers.CloudDeviceAdminReceiver",
    "android.app.extra.PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": "I5YvS0O5hXY46mb01BlRjq4oJJGs2kuUcHvVkAPEXlg",
    "android.app.extra.PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": "https://play.google.com/managed/downloadManagingApp?identifier=setup",
    "android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
        "com.google.android.apps.work.clouddpc.EXTRA_ENROLLMENT_TOKEN": "{enrollment-token}"
    }
}
```

### Managed configurations (restrictions managées)

Les *managed configurations* permettent à un administrateur IT de configurer une application gérée sans modifier son code. L'EMM pousse un `Bundle` de restrictions que l'application lit au runtime.

Côté application, les restrictions sont déclarées dans `res/xml/app_restrictions.xml` :

```xml
<?xml version="1.0" encoding="utf-8"?>
<restrictions xmlns:android="http://schemas.android.com/apk/res/android">
    <restriction
        android:key="luna_server_url"
        android:title="@string/restriction_server_url_title"
        android:restrictionType="string"
        android:description="@string/restriction_server_url_desc"
        android:defaultValue="" />
</restrictions>
```

Et lues via `RestrictionsManager` :

```kotlin
val restrictionsManager = getSystemService(Context.RESTRICTIONS_SERVICE) as RestrictionsManager
val restrictions = restrictionsManager.applicationRestrictions
val serverUrl = restrictions.getString("luna_server_url", "")
```

## Références officielles

- [Device Administration](https://developer.android.com/guide/topics/admin/device-admin) — Documentation officielle Android Developers. [Source non récupérée directement — URL de référence]
- [Android Enterprise overview](https://developer.android.com/work/overview) — Documentation officielle Android Developers. [Source non récupérée directement — URL de référence]
- [Device policy controller](https://developer.android.com/work/dpc) — Documentation officielle Android Developers. [Source non récupérée directement — URL de référence]
- [Work profiles](https://developer.android.com/work/managed-profiles) — Documentation officielle Android Developers, consultée le 2026-07-12.
- [Android Management API](https://developers.google.com/android/management) — Documentation officielle Google for Developers, consultée le 2026-07-12.
- [Android Management API — Introduction](https://developers.google.com/android/management/introduction) — Documentation officielle Google for Developers, consultée le 2026-07-12.
- [Enroll and provision a device](https://developers.google.com/android/management/provision-device) — Documentation officielle Google for Developers, consultée le 2026-07-12.
- [Set up managed configurations](https://developer.android.com/work/managed-configurations) — Documentation officielle Android Developers. [Source non récupérée directement — URL de référence]

## Implications pour Guardian / Kimi

### Conception de l'APK Luna

1. **Ne pas s'appuyer sur Device Administration legacy** : si Guardian nécessite un contrôle d'appareil (verrouillage, restrictions, mode kiosk), il faut passer par Android Enterprise et un EMM/DPC officiel, et non par l'API `DeviceAdminReceiver` historique. Cette dernière est dépréciée et sera de plus en plus restrictive.

2. **Pousser la configuration via managed configurations** : pour déployer Luna à grande échelle sans rebuild, utilisez les managed configurations pour transmettre l'URL du serveur Luna, le token d'organisation, le mode de fonctionnement, etc. Cela évite d'intégrer des secrets en dur dans l'APK.

3. **Différencier les modes de gestion** :
   - En **Work Profile** (personnel ou appareil d'entreprise), les limitations du chapitre *Work Profile* s'appliquent : intents, partage de fichiers, `NotificationListenerService` restreint, etc.
   - En **fully managed device** ou **dedicated device**, Guardian peut bénéficier de plus de contrôle, mais l'application doit être installée et configurée par le DPC/EMM.

4. **Ne pas implémenter soi-même un DPC à la légère** : devenir un DPC complet implique de gérer l'enrôlement, les politiques, les mises à jour, la conformité Play et la sécurité des appareils. Pour Luna, il est préférable de s'appuyer sur Android Device Policy (via Android Management API) ou sur un EMM partenaire.

### Play Store et politiques

- Si l'APK Luna déclare `BIND_DEVICE_ADMIN` ou utilise `DeviceAdminReceiver`, elle doit fournir une justification valable liée à la gestion d'appareils enterprise. Sans cela, Google Play peut rejeter l'application.
- Les permissions et fonctionnalités liées à l'administration doivent être strictement justifiées dans la fiche Play Console.

### Tests et qualification

- Utiliser **TestDPC** pour simuler un environnement Android Enterprise et valider le comportement de Guardian dans un Work Profile ou un appareil entièrement géré.
- Tester les scénarios de provisioning via QR code ou zero-touch sur des appareils de test réels.
- Vérifier la lecture des managed configurations et le comportement de l'application quand les restrictions changent.

### Points d'attention pour Kimi

- Les parcours utilisateur doivent intégrer la possibilité que Luna soit déployée sur un appareil géré : absence de certaines actions système, impossibilité d'ouvrir des apps externes, messages d'erreur explicites.
- Prévoir un écran de diagnostic indiquant si l'appareil est géré, quel mode est actif (Work Profile, fully managed, dedicated) et quelles restrictions sont appliquées, afin de faciliter le support.
