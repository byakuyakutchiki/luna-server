# 15. Bluetooth, NFC, USB : permissions, APIs et restrictions

## Objectif

Ce chapitre recense les permissions, les APIs framework et les limitations officielles des trois canaux de proximité/câblé d'Android : Bluetooth, NFC et USB. Il vise à éviter les erreurs de manifeste, les demandes de permissions inutiles et les comportements supposés non vérifiés pour Guardian et l'APK Luna.

## Concepts clés

### 1. Bluetooth

Android distingue le **Bluetooth classique** (RFCOMM, streaming, données) du **Bluetooth Low Energy (BLE)**. Les deux utilisent le package `android.bluetooth`, mais des classes dédiées existent pour le BLE (`android.bluetooth.le`).

#### 1.1 Permissions

Les permissions à déclarer dépendent du `targetSdkVersion`.

**Android 12 (API 31) et supérieur**

Trois permissions de **runtime** (`dangerous`) regroupées sous la bannière *Nearby devices* :

- `BLUETOOTH_SCAN` : rechercher des appareils Bluetooth (incluant les périphériques BLE).
- `BLUETOOTH_CONNECT` : communiquer avec des appareils déjà appairés.
- `BLUETOOTH_ADVERTISE` : rendre l'appareil détectable.

Si l'application n'utilise pas les résultats de scan pour déduire une position physique, elle doit ajouter `android:usesPermissionFlags="neverForLocation"` sur `BLUETOOTH_SCAN` et peut limiter `ACCESS_FINE_LOCATION` à `android:maxSdkVersion="30"`.

Les anciennes permissions `BLUETOOTH` et `BLUETOOTH_ADMIN` doivent être conservées avec `android:maxSdkVersion="30"` pour la rétrocompatibilité.

**Android 11 (API 30) et inférieur**

- `BLUETOOTH` et `BLUETOOTH_ADMIN` (normales) pour l'activation, la découverte et les connexions.
- `ACCESS_FINE_LOCATION` (runtime) requise pour le scan Bluetooth, car ce dernier peut être utilisé pour déduire la position de l'utilisateur.
- Sur Android 10 et 11, la découverte en arrière-plan requiert `ACCESS_BACKGROUND_LOCATION`.

Exemple de manifeste pour un `targetSdkVersion` ≥ 31 :

```xml
<manifest>
    <!-- Permissions legacy, limitées aux anciennes versions -->
    <uses-permission android:name="android.permission.BLUETOOTH"
                     android:maxSdkVersion="30" />
    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN"
                     android:maxSdkVersion="30" />

    <!-- Permissions Android 12+ -->
    <uses-permission android:name="android.permission.BLUETOOTH_SCAN"
                     android:usesPermissionFlags="neverForLocation" />
    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />

    <!-- Location uniquement si le scan sert à déduire une position physique -->
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"
                     android:maxSdkVersion="30" />
</manifest>
```

#### 1.2 APIs et fonctionnement

Classes principales du package `android.bluetooth` :

- `BluetoothAdapter` : adaptateur local, point d'entrée.
- `BluetoothDevice` : appareil distant.
- `BluetoothSocket` / `BluetoothServerSocket` : canal de communication RFCOMM.
- `BluetoothProfile` et ses implémentations (`BluetoothHeadset`, `BluetoothA2dp`, etc.).

Workflow officiel :

1. Vérifier la présence du Bluetooth (`BluetoothAdapter`).
2. Activer le Bluetooth si nécessaire (`ACTION_REQUEST_ENABLE`).
3. Découvrir ou lister les appareils appairés.
4. Établir une connexion via `BluetoothSocket`.
5. Échanger des données via `InputStream` / `OutputStream`.

#### 1.3 Restrictions

- Toutes les permissions Android 12+ sont des permissions de runtime : elles doivent être demandées explicitement et peuvent être refusées.
- `BLUETOOTH_ADMIN` ne doit servir qu'à la découverte/connexion ; ne pas l'utiliser pour modifier les paramètres Bluetooth sans action utilisateur.
- Le scan classique est limité à ~12 secondes par appel à `startDiscovery()`.
- Sur Android 8.0 (API 26) et plus, le **Companion Device Manager (CDM)** offre un flux plus léger pour associer un périphérique compagnon, sans permission de localisation.

---

### 2. NFC

Le NFC (Near Field Communication) est un ensemble de technologies sans fil à très courte portée (environ 4 cm). Le package officiel est `android.nfc`.

#### 2.1 Permissions

- Permission normale obligatoire dans le manifeste :

```xml
<uses-permission android:name="android.permission.NFC" />
```

- Pour le mode **lecteur/écrivain**, aucune permission de runtime supplémentaire.
- Pour l'**émulation de carte hôte (HCE)**, le service doit déclarer `android:permission="android.permission.BIND_NFC_SERVICE"` (`BIND_NFC_SERVICE` est une permission système ; seul le système peut se lier au service).

#### 2.2 Modes de fonctionnement

Deux modes sont simultanément supportés sur les appareils équipés :

1. **Reader/Writer** : lire/écrire des tags NFC passifs (format NDEF ou technologies brutes).
2. **Card Emulation** : l'appareil se comporte comme une carte NFC.
   - Émulation par élément sécurisé (SE/SIM) : gérée hors de l'application Android.
   - **Host-based Card Emulation (HCE)** : introduit avec Android 4.4 (API 19), route les APDU vers le CPU hôte via un service `HostApduService`.

#### 2.3 APIs

- `NfcAdapter` : contrôle l'adaptateur NFC, active/désactive la lecture et l'émulation.
- `NdefMessage`, `NdefRecord` : manipulation des payloads NDEF.
- `HostApduService` : implémentation d'un service HCE (`processCommandApdu`, `onDeactivated`).
- `CardEmulation` : gestion des services par défaut et des groupes d'AID.

Exemple de déclaration minimale d'un service HCE :

```xml
<service android:name=".MyHostApduService"
         android:exported="true"
         android:permission="android.permission.BIND_NFC_SERVICE">
    <intent-filter>
        <action android:name="android.nfc.cardemulation.action.HOST_APDU_SERVICE" />
    </intent-filter>
    <meta-data android:name="android.nfc.cardemulation.host_apdu_service"
               android:resource="@xml/apduservice" />
</service>
```

#### 2.4 Restrictions

- La disponibilité du NFC dépend du matériel ; il faut déclarer `<uses-feature android:name="android.hardware.nfc" android:required="true" />` ou vérifier `PackageManager.hasSystemFeature(PackageManager.FEATURE_NFC)`.
- HCE n'est disponible qu'à partir d'Android 4.4 (API 19).
- Les applications de paiement HCE (`CATEGORY_PAYMENT`) ne peuvent traiter une transaction que si elles sont l'application de portefeuille par défaut ou si elles appellent `setPreferredService()` en premier plan (à partir d'Android 15, le rôle `RoleManager.ROLE_WALLET` centralise ce choix).
- Android 10 (API 29) introduit le **Secure NFC** : quand il est activé, aucun émulateur de carte ne fonctionne si l'écran est éteint, indépendamment de `requireDeviceUnlock`.
- Sur Android 9 (API 28) et inférieur, le NFC est désactivé lorsque l'écran est éteint.
- Android Beam (partage P2P via NFC) est déprécié ; ne pas le considérer comme une solution active.

---

### 3. USB

Android supporte deux modes USB : **USB host** (l'appareil Android est l'hôte) et **USB accessory** (l'appareil Android est l'accessoire, l'hôte est un périphérique externe).

#### 3.1 Niveaux API

- API 12+ : USB host et USB accessory en framework (`android.hardware.usb`).
- API 10+ : USB accessory via la bibliothèque add-on `com.android.future.usb` (non garanti sur tous les appareils).
- Le support final dépend du matériel du fabricant.

#### 3.2 Permissions

Aucune permission de manifeste globale n'est requise pour utiliser USB. Le consentement est donné **par périphérique** :

- Si l'application découvre le périphérique via un `intent-filter` `USB_DEVICE_ATTACHED` / `USB_ACCESSORY_ATTACHED`, la permission est automatiquement accordée pour la durée de la connexion.
- Sinon, l'application doit appeler `UsbManager.requestPermission()` et attendre le retour utilisateur via un `BroadcastReceiver` écoutant `EXTRA_PERMISSION_GRANTED`.

#### 3.3 APIs

**Mode hôte (`android.hardware.usb`)**

- `UsbManager` : énumération et gestion des périphériques.
- `UsbDevice` : identité, interfaces, endpoints du périphérique.
- `UsbInterface`, `UsbEndpoint` : communication via endpoints.
- `UsbDeviceConnection` : transferts `bulkTransfer()` / `controlTransfer()`.
- `UsbRequest` : requêtes asynchrones.

**Mode accessoire**

- `UsbManager`, `UsbAccessory`.
- Communication par descripteur de fichier (`openAccessory()`), puis `FileInputStream` / `FileOutputStream`.

#### 3.4 Manifeste et filtrage

Pour le mode hôte, le manifeste doit déclarer la fonctionnalité et, optionnellement, un filtre d'appareil :

```xml
<manifest ...>
    <uses-feature android:name="android.hardware.usb.host" />
    <uses-sdk android:minSdkVersion="12" />

    <application>
        <activity ...>
            <intent-filter>
                <action android:name="android.hardware.usb.action.USB_DEVICE_ATTACHED" />
            </intent-filter>
            <meta-data android:name="android.hardware.usb.action.USB_DEVICE_ATTACHED"
                       android:resource="@xml/device_filter" />
        </activity>
    </application>
</manifest>
```

`res/xml/device_filter.xml` :

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <usb-device vendor-id="1234" product-id="5678" />
</resources>
```

Pour le mode accessoire, la fonctionnalité est `android.hardware.usb.accessory` et l'action est `USB_ACCESSORY_ATTACHED`.

#### 3.5 Restrictions

- Le mode hôte consomme de l'énergie pour alimenter le bus ; tous les appareils ne le supportent pas.
- L'accessoire doit respecter le **Android Open Accessory (AOA) protocol**.
- Quand un périphérique USB est connecté, `adb` via USB devient indisponible ; utiliser `adb tcpip 5555` puis `adb connect <ip>` pour le débogage sans fil.
- Les transferts USB doivent être effectués hors du thread UI.

---

### 4. Points communs aux trois canaux

- **Disponibilité matérielle** : vérifier avec `<uses-feature>` ou `PackageManager.hasSystemFeature()` (`FEATURE_BLUETOOTH`, `FEATURE_BLUETOOTH_LE`, `FEATURE_NFC`, `FEATURE_USB_HOST`, etc.).
- **Permissions de runtime** : Bluetooth (Android 12+) et localisation (Android 11-) nécessitent une demande explicite ; USB nécessite un consentement par périphérique.
- **Désactivation utilisateur** : l'utilisateur peut désactiver Bluetooth, NFC ou le débogage USB à tout moment ; l'application doit dégrader gracieusement.
- **Google Play** : une app qui déclare `ACCESS_FINE_LOCATION` pour le scan Bluetooth doit justifier l'usage de la localisation ; privilégier `neverForLocation` et le Companion Device Manager dès qu possible.

## Références officielles

- [Bluetooth overview](https://developer.android.com/guide/topics/connectivity/bluetooth)
- [Bluetooth permissions](https://developer.android.com/develop/connectivity/bluetooth/bt-permissions)
- [NFC overview](https://developer.android.com/guide/topics/connectivity/nfc)
- [NFC basics](https://developer.android.com/guide/topics/connectivity/nfc/nfc) — [Source non récupérée directement — URL de référence]
- [Host-based card emulation](https://developer.android.com/develop/connectivity/nfc/hce)
- [USB host and accessory overview](https://developer.android.com/guide/topics/connectivity/usb)
- [USB host mode](https://developer.android.com/develop/connectivity/usb/host)
- [USB accessory mode](https://developer.android.com/develop/connectivity/usb/accessory)
- [`<uses-feature>`](https://developer.android.com/guide/topics/manifest/uses-feature-element)
- [`PackageManager.hasSystemFeature()`](https://developer.android.com/reference/android/content/pm/PackageManager#hasSystemFeature(java.lang.String))

## Implications pour Guardian / Kimi

- **Bluetooth** : pour associer Guardian à un périphérique Luna (casque, bracelet, balise), privilégier le **Companion Device Manager** dès Android 8+ afin d'éviter `ACCESS_FINE_LOCATION`. Si le CDM n'est pas applicable, demander `BLUETOOTH_SCAN` + `BLUETOOTH_CONNECT` en runtime et ajouter `neverForLocation` si le scan ne sert pas à la géolocalisation.
- **NFC** : utilisable pour un *tap-to-pair* ou la lecture d'un tag de configuration Guardian. L'émulation de carte HCE est possible dès API 19, mais les cas d'usage de paiement sont verrouillés par l'application de portefeuille par défaut ; ne pas compter sur une émulation silencieuse.
- **USB** : réservé au débogage terrain ou à des accessoires locaux (par exemple lecteur spécifique). Prévoir le basculement sur `adb` Wi-Fi car une connexion USB active bloque `adb` filaire.
- **Dégradation** : chaque fonction doit vérifier la présence matérielle, l'état utilisateur et gérer le refus de permission sans planter. Guardian ne doit pas supposer que Bluetooth/NFC/USB sont disponibles ou activés.
- **Audit** : toute fonctionnalité utilisant ces canaux doit être revue au regard de la politique Google Play sur les permissions de localisation et les services financiers (NFC).
