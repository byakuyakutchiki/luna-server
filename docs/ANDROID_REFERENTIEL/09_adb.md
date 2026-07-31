# 09 — Android Debug Bridge (ADB)

## Objectif

Ce chapitre décrit l'outil officiel Android Debug Bridge (ADB), son architecture client-serveur, les commandes essentielles pour le développement et le diagnostic, ainsi que les modalités de connexion sans fil (wireless debugging). Il vise à fournir une base commune et sourcée pour les opérations de test et de débogage de l'APK Luna et des services Guardian.

## Concepts clés

### Qu'est-ce qu'ADB ?

Android Debug Bridge (ADB) est un outil en ligne de commande fourni avec Android Studio et le SDK Android. Il permet la communication entre un poste de développement et un appareil Android physique ou émulé pour installer des applications, exécuter des commandes shell, consulter les journaux système et transférer des fichiers.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb]

### Architecture

ADB repose sur une architecture client-serveur à trois composants :

- **Client** : s'exécute sur le poste de développement. Une commande `adb` lance un client.
- **Daemon (`adbd`)** : s'exécute en arrière-plan sur l'appareil Android. Il gère les connexions et exécute les commandes.
- **Serveur** : s'exécute en arrière-plan sur le poste de développement. Il gère la communication entre les clients et les daemons des appareils connectés.

Lorsqu'un client ADB est lancé, il vérifie d'abord si le serveur ADB est démarré ; sinon, il le lance. Le serveur écoute ensuite les connexions sur le port TCP 5037 par défaut.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb]

### Prérequis

- Le **débogage USB** doit être activé dans les **Options pour les développeurs** de l'appareil.
- Le SDK Platform Tools doit être installé sur le poste de développement.
- Sur Windows, un pilote USB adapté au fabricant de l'appareil est généralement nécessaire.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb]

### Commandes essentielles

Les commandes suivantes sont documentées dans la référence officielle ADB. Les extraits sont donnés à titre indicatif ; la syntaxe exacte peut être vérifiée dans la documentation officielle.

Lister les appareils connectés :

```bash
adb devices
```

Installer un APK :

```bash
adb install chemin/vers/app.apk
```

Désinstaller un package (par son nom de package) :

```bash
adb uninstall com.example.package
```

Ouvrir un shell sur l'appareil :

```bash
adb shell
```

Consulter les logs système (logcat) :

```bash
adb logcat
```

Envoyer un fichier vers l'appareil :

```bash
adb push fichier_local /chemin/destination
```

Récupérer un fichier depuis l'appareil :

```bash
adb pull /chemin/source fichier_local
```

Redémarrer l'appareil :

```bash
adb reboot
```

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb]

### Commandes shell (`adb shell`)

Une fois dans le shell, l'utilisateur dispose d'un sous-ensemble de commandes Unix/Linux. Certaines commandes sont accessibles sans privilèges élevés, d'autres nécessitent l'accès root (non disponible sur les appareils commerciaux standard).

Exemples de commandes shell courantes :

```bash
adb shell pm list packages        # Liste les packages installés
adb shell am start -n com.example.package/.Activity  # Lance une activity
adb shell dumpsys activity        # État du framework Activity
adb shell input text "hello"      # Simule une saisie clavier
```

L'interprétation exacte des commandes et leur disponibilité dépendent de la version Android et des politiques SELinux de l'appareil.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb#shellcommands]

### Sécurité et authentification

Lors de la première connexion ADB à un appareil, une boîte de dialogue s'affiche sur l'appareil pour demander l'autorisation de l'ordinateur. Cette autorisation repose sur un mécanisme de clé RSA.

Points de sécurité importants :

- **Ne jamais activer le débogage USB sur un appareil de production ou confié à un utilisateur final**, car cela expose l'appareil à des accès privilégiés depuis un poste connecté.
- L'utilisateur peut révoquer les autorisations ADB précédemment accordées depuis les options pour les développeurs (`Révoquer les autorisations de débogage USB`).
- Le canal ADB n'est pas chiffré en mode USB classique ; les données transitent par USB.
- Sur un appareil rooté ou compromis, ADB peut permettre un accès étendu au système ; sur un appareil standard, il reste soumis au sandbox applicatif et aux politiques SELinux.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb]

### Wireless debugging (débogage sans fil)

À partir d'Android 11 (niveau d'API 30), Android prend en charge le débogage sans fil natif. Cela permet de se connecter à un appareil via Wi-Fi sans câble USB.

Deux modes de couplage sont documentés :

1. **Couplage par code à usage unique** : l'appareil affiche un code de couplage et un numéro de port ; le poste de développement s'y connecte avec `adb pair`.
2. **Couplage par QR code** : l'utilisateur scanne un QR code affiché sur le poste de développement pour établir la connexion.

Exemple de flux documenté :

```bash
adb pair IP:PORT
adb connect IP:PORT
```

Le débogage sans fil nécessite que le poste de développement et l'appareil soient sur le même réseau Wi-Fi.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb#wireless]

### Limites et contraintes

- ADB ne permet pas à une application tierce de contourner le sandbox Android ou les permissions runtime sans un accès root ou un profil spécifique.
- Les commandes shell disponibles via `adb shell` sont limitées par les politiques de sécurité (UID, SELinux) de l'appareil.
- Sur un appareil non rooté, ADB n'a pas accès aux données privées d'une autre application, sauf si cette dernière les expose explicitement (ContentProvider, sauvegarde autorisée, etc.).
- Le débogage sans fil peut être désactivé par les politiques d'entreprise ou les profils managés.

[Source non récupérée directement — URL de référence : https://developer.android.com/studio/command-line/adb]

## Références officielles

- Android Debug Bridge (ADB) — Google Developers : https://developer.android.com/studio/command-line/adb
- ADB shell commands — Google Developers : https://developer.android.com/studio/command-line/adb#shellcommands
- Wireless debugging with ADB — Google Developers : https://developer.android.com/studio/command-line/adb#wireless

> **Note :** Les pages ci-dessus n'ont pas pu être récupérées directement lors de la rédaction de ce chapitre. Les faits présentés reposent sur la documentation officielle Android publiquement connue et doivent être revérifiés contre ces URLs avant toute décision critique.

## Implications pour Guardian / Kimi

- **Tests terrain** : Kimi peut utiliser ADB pour installer l'APK Luna, consulter les logs (`adb logcat`) et vérifier le comportement de Guardian sur un appareil réel, sans manipulation root.
- **Automatisation limitée** : ADB permet de simuler des interactions (touches, saisies) via `adb shell input`, mais Guardian ne doit pas dépendre d'ADB pour fonctionner chez l'utilisateur final, car le débogage USB sera désactivé.
- **Sécurité produit** : Guardian doit être conçu pour fonctionner dans le sandbox Android standard. ADB est un outil de développement et de test, pas une brique fonctionnelle du produit final.
- **Wireless debugging** : utile pour les tests sur appareils distants ou sans port USB accessible. Prévoir des procédures de test utilisant `adb pair` et `adb connect` pour les bancs de test Android 11+.
- **Diagnostic à distance** : en cas de support utilisateur, on ne peut pas compter sur ADB. Les logs applicatifs doivent être remontés par des mécanismes propres à l'application (avec consentement explicite de l'utilisateur), pas par ADB.
