# 17 — Ce qu'une IA peut/ne peut pas faire sur Android sans que l'app le prévoie

## Objectif

Clarifier les bornes systémiques d'une IA embarquée ou distante dans une application Android. Une IA ne dispose d'aucune capacité magique : elle hérite strictement du périmètre technique, des permissions et des composants que l'APK déclare et implémente. Ce chapitre sert de garde-fou pour concevoir Guardian / Kimi sans sur-estimer ce qu'un modèle peut déclencher seul.

## Concepts clés

### 1. L'IA vit dans le sandbox de l'application

Chaque application Android s'exécute dans son propre sandbox de sécurité :

- un UID Linux unique par application ;
- un processus dédié avec sa propre machine virtuelle ;
- un espace de stockage privé (`/data/data/<package>`) inaccessible aux autres applications ;
- un principe de moindre privilège par défaut.

**Conséquence** : que le modèle soit local (ONNX / LiteRT / MediaPipe) ou distant (API cloud), ses "actions" passent obligatoirement par le code, les permissions et les composants de l'APK. L'IA ne peut pas sortir de ce sandbox par elle-même.

> Référence : [Application Fundamentals](https://developer.android.com/guide/components/fundamentals)

### 2. Permissions : le verrou principal

Android classe les permissions en trois familles :

| Type | Exemples | Mécanisme d'attribution |
|------|----------|------------------------|
| Install-time (`normal`) | `INTERNET`, `ACCESS_NETWORK_STATE` | Accordée automatiquement à l'installation. |
| Runtime (`dangerous`) | `RECORD_AUDIO`, `CAMERA`, `ACCESS_FINE_LOCATION` | Déclarées dans le manifeste, demandées explicitement à l'utilisateur à l'exécution. |
| Spéciales (`appop`) | `SYSTEM_ALERT_WINDOW`, `REQUEST_INSTALL_PACKAGES`, `WRITE_SETTINGS` | Activées manuellement dans les paramètres système ou via un intent dédié. |

**Conséquence** : si l'application n'a pas déclaré et obtenu une permission, l'IA ne peut pas :

- écouter le micro ;
- accéder à la caméra ;
- lire la localisation ;
- consulter les contacts, les SMS, les journaux d'appels ;
- voir la liste des applications installées (sauf API dédiées restreintes selon les versions).

> Référence : [Permissions overview](https://developer.android.com/guide/topics/permissions/overview)

### 3. IA distante = aucun accès direct au terminal

Un LLM distant reçoit un prompt et renvoie du texte (ou un structured output). Il ne peut pas :

- ouvrir une application sur le téléphone ;
- appuyer sur un bouton dans l'interface ;
- accéder aux capteurs ;
- lire un fichier local.

Pour que ces actions se produisent, l'APK doit :

1. parser la réponse du modèle ;
2. vérifier qu'elle correspond à une action autorisée ;
3. exécuter cette action via une API Android explicite (intent, service, etc.).

### 4. IA locale = inférence dans le sandbox, pas de super-pouvoirs

Un modèle exécuté localement (TFLite, ONNX Runtime, MediaPipe LLM Inference API, etc.) reste soumis aux mêmes limites :

- il s'exécute dans le processus de l'application ;
- il consomme la mémoire et le CPU alloués à ce processus ;
- il n'a pas accès aux ressources protégées sans les permissions requises.

### 5. Accessibilité : une API puissante mais fortement réglementée

`AccessibilityService` permet de lire l'écran, d'intercepter des événements et d'injecter des actions. Cependant :

- elle est réservée aux outils d'accessibilité réels (lecteurs d'écran, systèmes de saisie vocale ou basés sur des commutateurs, afficheurs Braille) ;
- Google Play interdit l'utilisation autonome de l'API pour initier, planifier ou exécuter des actions de manière non déterministe ;
- l'automation déterministe de type "si déclencheur X, alors action Y" reste autorisée pour les usages non-accessibilité, à condition de fournir une divulgation explicite et un consentement utilisateur ;
- à partir du ciblage d'Android 12 (API 31), une déclaration dans Play Console est obligatoire.

> Référence : [Use of the AccessibilityService API — Google Play](https://support.google.com/googleplay/android-developer/answer/10964491)
> Référence non récupérée directement : [AccessibilityService](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService) [Source non récupérée directement — URL de référence]

### 6. Actions système interdites sans privilèges élevés

Une application classique (y compris une application dotée d'une IA) ne peut pas :

- installer silencieusement un APK (nécessite `REQUEST_INSTALL_PACKAGES` + interaction utilisateur) ;
- modifier des paramètres système critiques (nécessite `WRITE_SETTINGS` ou `WRITE_SECURE_SETTINGS`, rarement accordé aux apps utilisateur) ;
- désinstaller d'autres applications ;
- lire les données d'autres applications (scoped storage, API 29+) ;
- accéder au stockage partagé sans les permissions adaptées ;
- exécuter du code natif arbitraire en dehors du sandbox.

### 7. Cycle de vie et exécution en arrière-plan

- Une IA qui tourne en arrière-plan doit généralement s'appuyer sur un `ForegroundService` (avec type de service explicite depuis Android 14, API 34) ;
- Doze mode et App Standby limitent les réveils et l'accès réseau ;
- Alarmes exactes nécessitent `SCHEDULE_EXACT_ALARM` (API 31+) ou `USE_EXACT_ALARM` (API 33+, réservé aux cas éligibles).

**Conséquence** : une IA ne peut pas rester active en permanence ni réagir instantanément à tout événement sans que l'application implante explicitement un service, une alarme ou un écouteur adapté.

> Référence non récupérée directement : [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services) [Source non récupérée directement — URL de référence]

## Références officielles

- [Application Fundamentals](https://developer.android.com/guide/components/fundamentals) — Android Developers
- [Permissions overview](https://developer.android.com/guide/topics/permissions/overview) — Android Developers
- [Use of the AccessibilityService API](https://support.google.com/googleplay/android-developer/answer/10964491) — Google Play Policy Center
- [AccessibilityService](https://developer.android.com/reference/android/accessibilityservice/AccessibilityService) — Android Developers [Source non récupérée directement — URL de référence]
- [Foreground services overview](https://developer.android.com/develop/background-work/services/foreground-services) — Android Developers [Source non récupérée directement — URL de référence]
- [Google Play Policy Center](https://support.google.com/googleplay/android-developer/topic/9858052) — Google Play

## Implications pour Guardian / Kimi

### Architecture

- Guardian doit considérer le LLM comme un générateur d'intentions, jamais comme un exécuteur direct. Toute action matérielle (micro, caméra, GPS, appel, SMS, intent vers une autre app) doit transiter par une couche d'orchestration métier dans l'APK.
- Les réponses du modèle doivent être validées contre une liste blanche d'actions autorisées avant exécution.

### Permissions

- Chaque capacité métier (écoute vocale, géolocalisation, lecture de notifications, affichage d'overlay) doit être mappée explicitement à une permission Android et à un flux de demande utilisateur.
- Ne pas supposer qu'une fonctionnalité est disponible parce que le modèle la "suggère" : vérifier `ContextCompat.checkSelfPermission()` avant tout accès sensible.

### Accessibilité

- Si Guardian utilise `AccessibilityService` pour piloter l'interface, il doit :
  - soit se qualifier comme outil d'accessibilité (`isAccessibilityTool="true"`) avec une justification réelle et une vidéo de démonstration pour Play Console ;
  - soit rester dans le cadre d'une automation déterministe, avec divulgation explicite et consentement utilisateur, sans prise de décision autonome non prévisible.
- Une interface pilotée par LLM de manière "autonome" via `AccessibilityService` serait en infraction avec la politique Google Play.

### Stockage et confidentialité

- Les données sensibles traitées par le modèle (transcriptions vocales, contexte de conversation, localisation) doivent rester dans l'espace privé de l'application ou être partagées explicitement via un `ContentProvider` contrôlé.
- Le modèle distant ne doit pas recevoir de données sensibles sans consentement documenté.

### Tests et validation

- Les tests doivent couvrir le cas où une permission est refusée : l'IA ne doit pas planter ni contourner le refus.
- Les tests doivent vérifier qu'une réponse malveillante ou hallucinée du LLM ne peut pas déclencher d'action non autorisée (injection de prompt vers action système).
