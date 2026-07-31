# Architecture de sécurité Android : sandbox, UID Linux, SELinux, isolation et moindre privilège

## Objectif

Ce chapitre décrit les mécanismes fondamentaux d'isolation applicative sur Android : le sandbox, l'identité Linux (UID/GID), le contrôle d'accès SELinux et le principe du moindre privilège. Il vise à fournir aux agents de développement Luna/Guardian une base factuelle pour concevoir, auditer et déboguer l'APK sans sur-estimer ses capacités système.

## Concepts clés

### Le sandbox applicatif

Android est un système Linux multi-utilisateur. Chaque application s'exécute dans son propre sandbox de sécurité. Par défaut, le système attribue à chaque application un **UID Linux unique**, inconnu des autres applications, et isole ses fichiers par des permissions Unix standard. Seul le processus possédant cet UID peut accéder au répertoire privé de l'application (`/data/data/<package>` sur les versions historiques, ou son équivalent dans le profil utilisateur).

Selon la documentation officielle, le sandbox repose sur quatre piliers :

- chaque application est un utilisateur Linux distinct ;
- le système assigne un UID unique propre à chaque application ;
- chaque processus dispose de sa propre machine virtuelle (VM Dalvik/ART) ;
- chaque application s'exécute dans son propre processus Linux.

[Source non récupérée directement — URL de référence] : la page Android Sandbox (AOSP) n'a pas pu être consultée lors de la rédaction.

### UID/GID Linux et isolation des processus

L'attribution d'un UID unique par application constitue la base de l'isolation. L'identité de l'application est déterminée à l'installation ; elle n'est pas modifiable par l'application elle-même. Les GID complètent ce mécanisme : certaines permissions système sont matérialisées par l'appartenance à un groupe Linux (accès réseau, SD card, etc.).

Lorsqu'un composant est démarré, Android lance le processus de l'application cible (s'il n'est pas déjà actif) et y instancie la classe du composant. Cela signifie qu'une activité invoquée dans une autre application s'exécute dans **le processus de cette autre application**, pas dans celui de l'appelante. C'est le système qui agit comme intermédiaire, via les `Intent`.

### SELinux (Security-Enhanced Linux)

Android utilise SELinux pour appliquer un **contrôle d'accès obligatoire (MAC)** à tous les processus, y compris ceux s'exécutant avec les capacités root. SELinux fonctionne selon le principe du **refus par défaut** : toute action non explicitement autorisée est rejetée.

Deux modes globaux existent :

- **Permissive** : les violations sont journalisées mais pas bloquées.
- **Enforcing** : les violations sont journalisées et bloquées.

Historiquement :

- Android 4.3 (API 18) : SELinux introduit en mode permissif pour le sandbox applicatif.
- Android 4.4 (API 19) : passage partiel au mode enforcing.
- Android 5.0 (API 21) et supérieur : SELinux est **intégralement enforcing** pour tous les domaines.
- Android 6.0 (API 23) : durcissement des politiques, filtrage `ioctl`, restriction de `/proc`.
- Android 7.0 (API 24) : verrouillage accru du sandbox applicatif, division de `mediaserver` en plusieurs processus pour réduire la surface d'attaque.
- Android 8.0 (API 26) : adaptation de SELinux à Project Treble pour séparer les politiques fournisseur (`vendor.img`) et plate-forme (`system.img`).

SELinux attribue à chaque processus un **domaine** (label de sécurité) et contrôle finement les interactions entre domaines, les fichiers, les sockets et les services. En mode enforcing, une tentative non autorisée est enregistrée dans `dmesg` et `logcat`.

### Principe du moindre privilège

Par défaut, une application Android ne dispose que des droits strictement nécessaires à son fonctionnement de base. Elle ne peut pas lire les données d'une autre application, accéder au matériel sensible ou interagir avec des services système sans déclaration explicite dans le manifeste et, pour les permissions dangereuses, sans accord de l'utilisateur. Ce modèle repose sur la déclaration de permissions dans `AndroidManifest.xml` et, depuis Android 6.0 (API 23), sur la demande à l'exécution pour les permissions dites "dangereuses".

### Exceptions : partage d'UID et de processus

Deux applications signées avec **le même certificat** peuvent déclarer le même `android:sharedUserId` dans leur manifeste. Dans ce cas, le système leur attribue le même UID Linux, ce qui leur permet de partager leurs données et éventuellement leur processus. Cette pratique est **dépréciée à partir d'Android 10 (API 29)** et ne doit pas être utilisée pour les nouvelles applications.

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.example.guardian"
    android:sharedUserId="com.example.shared">
    ...
</manifest>
```

À noter : le partage d'UID n'est pas une faille de sécurité en soi, mais il réduit l'isolation. Google recommande de l'éviter.

## Références officielles

- [Application Fundamentals](https://developer.android.com/guide/components/fundamentals) — Android Developers.
- [Android Sandbox](https://source.android.com/docs/core/architecture/android_sandbox) — AOSP. [Source non récupérée directement — URL de référence]
- [Application Security](https://developer.android.com/topic/security) — Android Developers. [Source non récupérée directement — URL de référence]
- [Security-Enhanced Linux (SELinux)](https://source.android.com/docs/security/features/selinux) — AOSP.

## Implications pour Guardian / Kimi

- **L'APK Luna/Guardian est un processus isolé**. Il ne peut pas lire directement la mémoire ou le stockage privé d'une autre application, ni être lu par elle. Toute donnée sensible collectée par Guardian doit être traitée dans ce périmètre ou transmise via des canaux explicitement autorisés.

- **Le modèle "assistant IA" ne supprime pas le sandbox**. Guardian ne peut pas contourner SELinux ou les UID Linux par simple volonté applicative. Les fonctionnalités comme l'accessibilité, l'overlay ou les services foreground ne donnent pas un accès root ; elles élargissent des périmètres déclaratifs, toujours soumis au système et aux politiques Google Play.

- **Les permissions doivent être justifiées**. Chaque permission ajoutée dans `AndroidManifest.xml` doit correspondre à un besoin réel et documenté. Le moindre privilège limite la surface d'attaque et réduit le risque de rejet par Google Play lors des révisions.

- **SELinux peut bloquer des opérations légitimes**. En cas de comportement anormal sur un appareil rooté, custom ROM ou version AOSP modifiée, consulter `logcat` et `dmesg` pour détecter des refus SELinux (`avc: denied`). Sur un appareil stock en mode enforcing, ces refus sont normalement le résultat d'une tentative hors politique.

- **Ne pas compter sur `sharedUserId`**. Si Luna et Guardian (ou d'autres modules) doivent communiquer, privilégier les mécanismes officiels : `Service` lié avec AIDL, `ContentProvider` avec URI permissions, ou `PendingIntent`. Le partage d'UID est déprécié et inadapté aux nouvelles versions d'Android.

- **Tester l'isolation sur plusieurs niveaux d'API**. Les comportements SELinux et les restrictions de sandbox évoluent significativement entre API 21, 23, 26, 29 et les versions ultérieures. Les tests doivent couvrir au minimum `minSdkVersion` et `targetSdkVersion` du projet.
