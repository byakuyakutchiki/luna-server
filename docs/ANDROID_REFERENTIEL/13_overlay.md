# 13 — Overlay : `SYSTEM_ALERT_WINDOW`, draw over apps, permissions spéciales

## Objectif

Ce chapitre décrit le mécanisme permettant à une application Android d’afficher une fenêtre par-dessus les autres applications, ainsi que la permission spéciale `SYSTEM_ALERT_WINDOW` et son cycle d’autorisation utilisateur à partir d’Android 6.0 (API 23).

## Concepts clés

### `SYSTEM_ALERT_WINDOW`

La permission `android.permission.SYSTEM_ALERT_WINDOW` permet à une application de créer des fenêtres affichées au-dessus de toutes les autres applications. Sa protection level est `signature|setup|appop|installer|pre23|development`.

- Introduite à l’API 1.
- À partir d’Android 6.0 (API 23), si l’application cible API 23 ou supérieur, l’utilisateur doit accorder explicitement cette autorisation via un écran de gestion dédié. L’application ne peut pas l’obtenir par une simple demande runtime classique.
- L’application doit la déclarer dans le manifeste :

```xml
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
```

### `TYPE_APPLICATION_OVERLAY` (API 26)

Depuis Android 8.0 (API 26), les applications non système doivent utiliser le type de fenêtre `WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY` pour dessiner par-dessus d’autres applications. Ce type est positionné :

- au-dessus des fenêtres d’application (`FIRST_APPLICATION_WINDOW`…`LAST_APPLICATION_WINDOW`) ;
- en dessous des fenêtres système critiques (barre d’état, clavier, etc.) ;
- sujet à des ajustements de position, taille ou visibilité par le système afin de limiter l’encombrement visuel ;
- nécessite la permission `SYSTEM_ALERT_WINDOW`.

Les anciens types `TYPE_SYSTEM_ALERT` et `TYPE_SYSTEM_OVERLAY` sont dépréciés à l’API 26 pour les applications non système. Leur utilisation par une application tierce n’est plus la méthode officielle recommandée.

### Demande d’autorisation utilisateur

À partir de l’API 23, l’application doit rediriger l’utilisateur vers les paramètres système via l’action `Settings.ACTION_MANAGE_OVERLAY_PERMISSION`. Il n’existe pas de boîte de dialogue runtime standard pour cette permission. L’action est introduite à l’API 23.

Exemple officiel de demande :

```java
if (!Settings.canDrawOverlays(context)) {
    Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                               Uri.parse("package:" + getPackageName()));
    startActivityForResult(intent, REQUEST_CODE);
}
```

Précisions sur l’Intent :

- L’URI `package:` est optionnelle et, selon la documentation de référence, n’est prise en compte que sur les versions d’Android antérieures à Android 11 (API 30, `Build.VERSION_CODES.R`).
- Dans certains cas, aucune activité correspondante n’existe ; il faut donc sécuriser l’appel (par exemple avec `resolveActivity()` ou un bloc `try/catch`).

### Vérification de l’autorisation

La méthode `Settings.canDrawOverlays(Context)` est disponible à partir de l’API 23. Elle retourne `true` si l’application peut dessiner par-dessus les autres applications, `false` sinon. L’appel est sans effet de bord : il ne demande pas l’autorisation, il vérifie uniquement son état.

### Comportement et restrictions système

- Le système peut modifier à tout moment la position, la taille ou la visibilité d’une fenêtre `TYPE_APPLICATION_OVERLAY` pour réduire l’encombrement visuel ou gérer les ressources.
- Les fenêtres d’overlay appartiennent à l’utilisateur les ayant créées ; en configuration multi-utilisateur, elles ne s’affichent que sur l’écran de l’utilisateur propriétaire.
- Le fait de posséder une fenêtre overlay augmente l’importance du processus associé, ce qui diminue la probabilité qu’il soit tué par le low-memory killer.
- Cette permission ne contourne pas le sandbox applicatif : elle autorise uniquement l’affichage en surimpression, pas l’accès aux données d’autres applications.

## Références officielles

- `Manifest.permission.SYSTEM_ALERT_WINDOW` — Android Developers : https://developer.android.com/reference/android/Manifest.permission#SYSTEM_ALERT_WINDOW
- `Settings.ACTION_MANAGE_OVERLAY_PERMISSION` — Android Developers : https://developer.android.com/reference/android/provider/Settings#ACTION_MANAGE_OVERLAY_PERMISSION
- `Settings.canDrawOverlays(Context)` — Android Developers : https://developer.android.com/reference/android/provider/Settings#canDrawOverlays(android.content.Context)
- `WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY` — Android Developers : https://developer.android.com/reference/android/view/WindowManager.LayoutParams#TYPE_APPLICATION_OVERLAY
- `WindowManager.LayoutParams.TYPE_SYSTEM_ALERT` (déprécié API 26 pour les apps non système) — Android Developers : https://developer.android.com/reference/android/view/WindowManager.LayoutParams#TYPE_SYSTEM_ALERT
- `WindowManager.LayoutParams.TYPE_SYSTEM_OVERLAY` (déprécié API 26 pour les apps non système) — Android Developers : https://developer.android.com/reference/android/view/WindowManager.LayoutParams#TYPE_SYSTEM_OVERLAY

## Implications pour Guardian / Kimi

- **Assistant IA visuel** : si Guardian/Luna doit afficher une bulle, un panneau contextuel ou une alerte au-dessus d’autres applications, le mécanisme officiel est `SYSTEM_ALERT_WINDOW` combiné à `TYPE_APPLICATION_OVERLAY` sur Android 8.0+.
- **Parcours utilisateur** : l’activation ne peut pas être silencieuse. L’APK doit rediriger l’utilisateur vers `Paramètres > Afficher par-dessus les autres applications` et vérifier ensuite l’état avec `canDrawOverlays()`. Ce parcours doit être intégré à l’onboarding.
- **Compatibilité** : pour cibler Android 8.0+ (API 26+), utiliser exclusivement `TYPE_APPLICATION_OVERLAY`. Les types `TYPE_SYSTEM_ALERT` / `TYPE_SYSTEM_OVERLAY` ne doivent plus être employés pour une APK standard.
- **Tests** : vérifier le comportement sur différents niveaux API (notamment 23, 26, 30) et sur des surcouches constructeur qui peuvent restreindre ou masquer l’écran de gestion de l’overlay.
- **Risques policy** : l’usage abusif d’overlay peut être considéré comme une interférence avec l’expérience utilisateur. Se référer au chapitre 16 pour les restrictions Google Play et s’assurer que l’overlay reste justifié par une fonctionnalité réelle de l’assistant.
