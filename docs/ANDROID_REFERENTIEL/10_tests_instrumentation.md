# 10 — Tests d'instrumentation : Espresso, UI Automator et instrumentation tests

## Objectif

Définir les stratégies et outils officiels de test d'interface sur Android pour l'APK Luna/Guardian. Le document distingue les tests intra-application (Espresso) des tests cross-application/système (UI Automator) et précise leurs conditions d'exécution et leurs limites.

## Concepts clés

### 1. Tests d'instrumentation (instrumentation tests)

Les tests d'instrumentation s'exécutent sur un appareil physique ou un émulateur Android. Ils sont placés dans `src/androidTest/` et utilisent un runner de test capable d'injecter du code dans le processus cible. Le runner historique et toujours référencé par la documentation officielle est `AndroidJUnitRunner`.

Caractéristiques vérifiées :
- Exécution sur JVM Android (ART) et non sur la JVM de la station de développement.
- Accès au contexte de l'application (`ApplicationProvider.getApplicationContext()`).
- Nécessitent un appareil/émulateur avec un niveau API compatible.
- Dépendances typiques : bibliothèques AndroidX Test (`androidx.test.runner.AndroidJUnitRunner`, `androidx.test.ext:junit`, etc.).

### 2. Espresso

Espresso est un framework de test UI officiel pour les tests synchronisés au sein d'une seule application. Il attend que l'interface soit inactive avant d'interagir, ce qui réduit les échecs liés à la latence.

Points clés :
- API minimum : Android 2.3.3 (API level 10) selon la documentation officielle.
- Portée : application sous test uniquement ; il ne pilote pas d'autres applications.
- API centrale : `onView()`, `ViewMatcher`, `ViewAction`, `ViewAssertion`.
- Gestion de l'asynchronisme via `IdlingResource` pour attendre les opérations longues (réseau, base de données, etc.).
- Extension `espresso-intents` pour valider et boucher les intents lancés par l'application.
- Extension `espresso-web` pour interagir avec des composants `WebView`.

Exemple officiel minimal :

```kotlin
@Test
fun greeter_saysHello() {
    onView(withId(R.id.name_field)).perform(typeText("Steve"))
    onView(withId(R.id.greet_button)).perform(click())
    onView(withText("Hello Steve!")).check(matches(isDisplayed()))
}
```

### 3. UI Automator

UI Automator est un framework de test UI pour les interactions cross-application et avec le système Android. Il permet de simuler des actions utilisateur en dehors de l'application sous test (notifications, paramètres système, applications tierces).

Points clés :
- API minimum : Android 4.3 (API level 18) selon la documentation officielle.
- Portée : n'importe quel élément visible à l'écran, y compris hors de l'application.
- API centrale : `UiDevice` (point d'entrée), `UiObject`, `UiSelector`, `UiScrollable`, `BySelector` / `UiObject2`.
- Accès aux propriétés système et aux gestures (swipe, pinch, rotation, pression physique simulée).
- Peut interagir avec les éléments par texte, description, classe, ressource-id, etc.
- Nécessite que l'application soit installée en mode debug et que l'appareil autorise l'instrumentation.

Exemple officiel minimal :

```kotlin
val device = UiDevice.getInstance(InstrumentationRegistry.getInstrumentation())

// Simuler un appui sur le bouton Home
device.pressHome()

// Ouvrir le launcher et lancer une application
val launcherPackage: String = device.launcherPackageName
assertThat(launcherPackage, notNullValue())
device.wait(Until.hasObject(By.pkg(launcherPackage).depth(0)), LAUNCH_TIMEOUT)
```

### 4. Choix entre Espresso et UI Automator

| Critère | Espresso | UI Automator |
|---------|----------|--------------|
| Portée | Application sous test | Système et applications tierces |
| API minimum | API 10 | API 18 |
| Synchronisation | Automatique avec la main thread | Manuelle (`wait`, `until`) |
| Vitesse | Rapide | Plus lent |
| Cas d'usage | Validation détaillée d'écrans internes | Parcours utilisateur traversant plusieurs apps |

La documentation officielle les présente comme complémentaires : Espresso pour la fiabilité des tests intra-app, UI Automator pour les scénarios cross-app et système.

### 5. Exécution et configuration

- Le runner `AndroidJUnitRunner` est déclaré dans le `build.gradle` (ou `build.gradle.kts`) du module :

```kotlin
defaultConfig {
    testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
}
```

- Lancement via Gradle : `./gradlew connectedAndroidTest` ou `./gradlew connectedCheck`.
- Nécessite un appareil/émulateur connecté avec `adb`.
- Les rapports sont générés dans `app/build/reports/androidTests/`.

## Références officielles

- *Test your app* — [https://developer.android.com/training/testing](https://developer.android.com/training/testing) [Source non récupérée directement — URL de référence]
- *Espresso* — [https://developer.android.com/training/testing/espresso](https://developer.android.com/training/testing/espresso) [Source non récupérée directement — URL de référence]
- *UI Automator* — [https://developer.android.com/training/testing/ui-automator](https://developer.android.com/training/testing/ui-automator) [Source non récupérée directement — URL de référence]
- *Jetpack Test (AndroidX Test releases)* — [https://developer.android.com/jetpack/androidx/releases/test](https://developer.android.com/jetpack/androidx/releases/test) [Source non récupérée directement — URL de référence]
- *AndroidJUnitRunner* — documentation intégrée à la page *Test your app* sur developer.android.com.

## Implications pour Guardian / Kimi

### Tests prioritaires pour Guardian

1. **Permission flows** : UI Automator est pertinent pour valider le parcours utilisateur allant jusqu'aux écrans système de demande de permissions (microphone, caméra, localisation, overlay `SYSTEM_ALERT_WINDOW`). Espresso ne peut pas interagir avec les dialogues système.

2. **Overlay et bulle flottante** : le composant overlay de Guardian traverse les applications. UI Automator est l'outil adapté pour vérifier qu'il s'affiche au-dessus d'autres apps, qu'il répond aux tap et aux gestures, et qu'il peut être fermé ou minimisé.

3. **Voice trigger / reconnaissance vocale** : les tests d'instrumentation peuvent préparer l'état du microphone et simuler des interactions UI, mais ils ne remplacent pas les tests unitaires du moteur de reconnaissance vocale (Vosk/Whisper). On testera plutôt le déclenchement de l'interface vocale et la propagation du résultat textuel vers les écrans Guardian.

4. **Foreground service et notification** : UI Automator permet d'ouvrir le panneau de notifications et de vérifier la présence de la notification de service Guardian, ainsi que ses actions (pause, arrêt).

5. **Cross-app / paramètres système** : pour valider les liens vers les paramètres d'accessibilité, de batterie (ignore battery optimizations) ou de localisation, UI Automator est nécessaire car Espresso reste confiné au package Guardian.

### Contraintes à respecter

- Cibler un niveau API cohérent avec le `minSdk` de l'APK Luna. Si `minSdk` est inférieur à 18, UI Automator ne pourra pas être utilisé pour les tests exécutés sur ces anciennes versions.
- Isoler les tests lents (UI Automator) des tests rapides (Espresso/unitaires) pour ne pas dégrader le temps d'intégration continue.
- Ne pas exécuter de tests d'instrumentation sur un appareil de production verrouillé ; utiliser un émulateur ou un appareil de test dédié.
- Éviter les assertions sur les timing fixes : privilégier `IdlingResource` (Espresso) et `UiDevice.wait` / `Until` (UI Automator).

### Recommandation opérationnelle

- **Espresso** : couverture des écrans internes de Guardian (login, historique, paramètres, chat).
- **UI Automator** : scénarios bout-en-bout incluant le launcher, les notifications système, les dialogues de permission et les interactions cross-app.
- Coupler ces tests aux tests unitaires locaux (`src/test`) et aux tests d'instrumentation ciblés (`src/androidTest`) pour former une pyramide de test équilibrée.
