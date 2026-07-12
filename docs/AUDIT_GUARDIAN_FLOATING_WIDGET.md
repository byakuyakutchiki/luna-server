# Audit technique — Guardian Floating Protection (issue #24)

> Réponse à la demande « Audit Android — Guardian Floating Protection ».
> Objectif : un **vrai widget système Android** (bulle flottante type Messenger Chat Heads / Duolingo),
> visible par-dessus toutes les applications, même YAWATCH fermé, qui **déclenche réellement le moteur Guardian**
> lorsqu'un mot-clé est prononcé.

**Date :** 2026-06-26 · **Lead technique :** Claude · **App :** `fr.yawatch.luna` v3.0 (versionCode 21)

---

## 1. Ce qui existe déjà (état réel du code)

L'application est une **WebView native** (`MainActivity.java`, 1507 lignes) qui charge l'UI web, avec un pont
JS↔natif (`LunaBridge`). Le mode Guardian dispose **déjà** d'une bonne base native :

| Brique existante | Fichier | Rôle actuel |
|---|---|---|
| **Foreground Service** | `GuardianService.java` | Notification persistante « 🛡 Luna Guardian » (protégé / vérif / urgence) + bouton SOS. Type `dataSync`. Garde le process vivant en arrière-plan. |
| **Écoute mot-clé native** | `MainActivity.java` (« Guardian Voice Core », l.728+) | `SpeechRecognizer` natif fr-FR, normalisation accents, détection `NATIVE_EMERGENCY_KW`, redémarrage auto, cooldown, gestion d'erreurs. |
| **Bridge JS↔natif** | `LunaBridge` (l.603+) | `startGuardianService()`, `stopGuardianService()`, `updateGuardianNotification()`, `updateGuardianPosition()`. |
| **Bouton SOS notif** | `SosReceiver.java` | Broadcast `SOS_ACTION` → MainActivity. |
| **Widget web in-app** | `static/index.html` (`#guardianFloat`, PR #23) | Pastille « Protégé » **dans la WebView uniquement** (disparaît dès qu'on quitte l'app). |

**Permissions déjà déclarées :** `RECORD_AUDIO`, `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_DATA_SYNC`,
`POST_NOTIFICATIONS`, `ACCESS_FINE/COARSE_LOCATION`, `CAMERA`. minSdk 24, targetSdk 35.

### Le constat (= ce que dit l'issue #24)
Le « widget » visible aujourd'hui est l'élément web `#guardianFloat` : c'est de **l'interface in-app**, pas un
service système. Il **disparaît** dès que l'utilisateur ouvre WhatsApp/Chrome/Instagram. **Aucun overlay
système n'est implémenté** : pas de `SYSTEM_ALERT_WINDOW`, pas de `WindowManager`, pas de
`TYPE_APPLICATION_OVERLAY`. De plus, l'écoute mot-clé tourne **dans MainActivity** → elle ne fonctionne que
WebView au premier plan.

**Les 2 manques réels à combler :**
1. **Overlay flottant système** (bulle au-dessus de toutes les apps).
2. **Déplacer l'écoute mot-clé dans le Foreground Service** pour qu'elle survive app fermée.

---

## 2. Architecture Android recommandée

### 2.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│  GuardianOverlayService  (Foreground Service, type micro+...) │
│                                                               │
│  • WindowManager.addView(bubbleView, TYPE_APPLICATION_OVERLAY)│ ← la bulle, au-dessus de tout
│  • Guardian Voice Core (SpeechRecognizer on-device)           │ ← écoute mot-clé, déplacée ici
│  • Notification persistante (déjà gérée par GuardianService)  │
│  • onKeywordDetected() → déclenche le moteur Guardian réel    │
└───────────────┬───────────────────────────────┬─────────────┘
                │ mot-clé détecté                │ tap sur la bulle
                ▼                                 ▼
   Moteur Guardian (SOS, enregistrement,   Ouvre MainActivity (WebView)
   géoloc, alerte contacts) — backend       sur l'écran Guardian
   /api/guardian/* déjà existant
```

**Principe directeur (conforme CLAUDE.md — additif, non destructif) :** on **étend** `GuardianService`
existant (ou on crée `GuardianOverlayService` à côté) ; on **ne touche pas** au moteur Guardian backend
(`/api/guardian/*`) ni à l'architecture existante. La bulle et l'écoute deviennent une **couche système**
au-dessus de l'app.

### 2.2 L'overlay flottant (la bulle)

- API recommandée : **`WindowManager`** + `LayoutParams` avec `type = TYPE_APPLICATION_OVERLAY` (API 26+).
  (Sous API 26 : `TYPE_PHONE`, mais minSdk=24 → prévoir le fallback, ou relever minSdk à 26 — 24/23 sont
  marginaux en 2026.)
- `LayoutParams.FLAG_NOT_FOCUSABLE | FLAG_LAYOUT_NO_LIMITS`, format `PixelFormat.TRANSLUCENT`.
- **Déplaçable** : `OnTouchListener` (ACTION_DOWN/MOVE/UP) → `windowManager.updateViewLayout()`.
  Distinguer tap (ouvrir) vs drag (déplacer) via un seuil de déplacement (~`touchSlop`).
- **Transparence réglable** : `bubbleView.setAlpha()` (plusieurs niveaux dans Paramètres Guardian).
- **Snap au bord** + auto-collapse (la bulle se réduit/translucide après quelques secondes d'inactivité,
  comme Messenger Chat Heads).
- **Design (contrainte produit issue #20)** : ni œil, ni caméra, ni symbole de surveillance.
  Réutiliser `ic_guardian_shield` (bouclier doux) ; halo apaisant ; jamais agressif.

### 2.3 L'écoute mot-clé (déplacée dans le service)

- Réutiliser **tel quel** la logique « Guardian Voice Core » (normalisation, keywords, restart, cooldown) :
  c'est du code déjà robuste — on le **déplace** de `MainActivity` vers le service.
- **Privilégier la reconnaissance on-device** (API 31+ : `createOnDeviceSpeechRecognizer()` /
  `EXTRA_PREFER_OFFLINE=true`) : indispensable pour de l'écoute continue (sinon chaque cycle part sur les
  serveurs Google = batterie + données + latence + vie privée). Fallback réseau si on-device indisponible.
- L'écoute ne tourne **que si** l'option « écoute du mot-clé » est activée dans Paramètres Guardian
  (l'overlay peut exister sans micro actif).

### 2.4 Activation / désactivation

- Toggle **« Widget de protection permanent »** dans Paramètres > Guardian (UI web), relayé via `LunaBridge` :
  - `enableGuardianOverlay(listenKeyword: boolean)` → démarre le service + addView.
  - `disableGuardianOverlay()` → removeView + stopForeground + stopSelf (la bulle **disparaît complètement**).
- État persisté (SharedPreferences natif) → **redémarrage auto au boot** si activé
  (receiver `BOOT_COMPLETED`, voir §3).

---

## 3. Permissions nécessaires

| Permission | Type | Pourquoi | Comment l'obtenir |
|---|---|---|---|
| **`SYSTEM_ALERT_WINDOW`** | Spéciale (pas runtime) | Afficher la bulle par-dessus les autres apps | `Settings.canDrawOverlays()` → si faux, `Intent(ACTION_MANAGE_OVERLAY_PERMISSION)` qui **ouvre l'écran Réglages** (pas une popup). À expliquer à l'utilisateur. |
| **`RECORD_AUDIO`** | Runtime (déjà là) | Écoute mot-clé | Déjà demandé par l'app. |
| **`FOREGROUND_SERVICE`** | Normale (déjà là) | Service persistant | Déjà déclarée. |
| **`FOREGROUND_SERVICE_MICROPHONE`** | Normale (**à ajouter**) | Android 14+ exige un type FGS explicite pour le micro | Ajouter au manifest + `foregroundServiceType="microphone"`. |
| **`POST_NOTIFICATIONS`** | Runtime (déjà là) | Notif FGS obligatoire | Déjà géré. |
| **`RECEIVE_BOOT_COMPLETED`** | Normale (**à ajouter**) | Relancer la protection après redémarrage du téléphone | Receiver `BOOT_COMPLETED`. |
| **`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`** | Spéciale (**optionnelle**) | Éviter que Doze / OEM tue le service | À demander seulement si nécessaire — sensible côté Play Store (voir §6). |
| ~~`BIND_ACCESSIBILITY_SERVICE`~~ | — | **DÉCONSEILLÉ** | Non nécessaire pour l'overlay ni l'écoute. À éviter (risque Play Store majeur, voir §5). |

> ⚠️ Sur Android 14+ (API 34+), `foregroundServiceType="dataSync"` actuel **ne suffit pas** pour le micro.
> Il faut `android:foregroundServiceType="microphone|dataSync"` ET appeler
> `startForeground(id, notif, FOREGROUND_SERVICE_TYPE_MICROPHONE)`.

---

## 4. Limitations imposées par Android (13 → 16)

1. **Démarrage du FGS micro depuis l'arrière-plan (Android 12+/14+)** — c'est **LA** contrainte clé.
   Un service de type `microphone` **ne peut pas démarrer** pendant que l'app est en arrière-plan
   (`ForegroundServiceStartNotAllowedException` / `MissingForegroundServiceTypeException`). Donc :
   - ✅ Le widget doit être **activé alors que l'app est ouverte** (l'utilisateur active le toggle) →
     le service démarre au premier plan, **puis survit** quand l'app passe en arrière-plan. C'est le cas d'usage normal.
   - ✅ Relance au boot via `BOOT_COMPLETED` (exempté) + service déjà foreground.
   - ❌ On **ne peut pas** « réveiller » le micro depuis rien quand l'app est tuée. Une fois le service
     foreground lancé, il continue ; mais s'il est tué (OEM/utilisateur), seul le boot ou la réouverture le relance.

2. **`SYSTEM_ALERT_WINDOW`** ne se redéclenche pas par dialogue runtime : ça ouvre l'écran système
   « Afficher par-dessus les autres applications ». Parcours utilisateur à soigner.

3. **Doze / App Standby** : en veille profonde, les services peuvent être throttlés. Un FGS avec notif
   visible résiste mieux, mais OEM agressifs (voir §6) peuvent quand même tuer.

4. **Micro en arrière-plan (Android 9+)** : accès micro interdit en background **sauf** FGS type micro actif
   avec notification — c'est exactement notre architecture, donc OK.

5. **Indicateur micro/privacy (Android 12+)** : point vert obligatoire quand le micro est actif. Non
   contournable (et c'est bien : transparence pour l'utilisateur). À assumer dans le discours produit.

6. **Android 14 — notifications FGS non masquables** : la notif du service micro **ne peut pas** être masquée
   par l'utilisateur tant que le service tourne. Cohérent avec « présence protectrice permanente ».

7. **Overlay masqué sur écrans sensibles** : le système cache automatiquement les overlays au-dessus des
   écrans de permission, des réglages sensibles, etc. (anti-tapjacking). Comportement normal, à ne pas combattre.

---

## 5. Politique Play Store / distribution

> Contexte : l'APK est actuellement **distribué en direct** (`static/luna-proprio.apk`, sideload), **pas via
> le Play Store**. Cela change l'analyse de risque.

- **En sideload (aujourd'hui)** : `SYSTEM_ALERT_WINDOW`, micro continu et exemption batterie ne sont
  soumis à **aucune validation Play**. Risque réglementaire ≈ nul. **Voie recommandée pour démarrer.**
- **Si publication Play Store un jour** :
  - `SYSTEM_ALERT_WINDOW` : autorisé mais scruté — l'overlay doit être initié par l'utilisateur et
    aisément désactivable (✅ notre design).
  - **Micro en continu** : déclaration d'usage obligatoire + justification « sécurité personnelle / SOS ».
  - **`REQUEST_IGNORE_BATTERY_OPTIMIZATIONS`** : réservé aux apps dont la fonction cœur l'exige
    (alarme, sécurité) — Guardian peut se justifier, mais à argumenter.
  - **Accessibility Service** : Google **interdit** son usage hors accessibilité réelle → **ne pas l'utiliser**
    pour le mot-clé/overlay, sous peine de retrait. (L'issue le mentionnait « éventuellement » : à écarter.)

---

## 6. Risques batterie & robustesse

| Risque | Impact | Mitigation |
|---|---|---|
| **Reconnaissance vocale continue** | Le plus gros poste de conso | On-device (API 31+), pas de réseau ; cycles courts ; pause après N erreurs (déjà dans le code, l.782). |
| **Wake locks** | Batterie | Ne **pas** prendre de wakelock permanent ; laisser le FGS gérer ; accepter throttling Doze. |
| **OEM « battery killers »** (Xiaomi/MIUI, Huawei, Samsung, Oppo…) | Tuent les services en arrière-plan | Guider l'utilisateur vers « autoriser le démarrage auto » + désactiver l'optimisation batterie **pour Luna** (écran constructeur, lien `dontkillmyapp.com` comme référence). Relance au boot. |
| **Overlay qui redessine** | CPU/GPU | Vue statique légère ; pas d'animation continue ; collapse après inactivité. |
| **Perception utilisateur** | Désinstallation si « ça vide la batterie » | Mode « écoute » **opt-in** séparé de la bulle ; afficher la conso réelle ; permettre bulle-sans-micro. |

**Estimation** : bulle seule (sans micro) = conso négligeable. Avec écoute on-device continue = modéré
(comparable à un assistant « hotword »), acceptable si opt-in et bien expliqué.

---

## 7. Best practices des références (Messenger, Duolingo, apps sécurité)

- **Messenger Chat Heads** : `SYSTEM_ALERT_WINDOW` + `WindowManager`, bulle draggable, snap au bord,
  collapse en pastille translucide, tap = expand. → modèle UX direct pour notre bulle.
  *(NB : Android 11+ propose l'API **Bubbles** native — mais elle est liée aux conversations/notifs, pas
  adaptée à un garde permanent. `SYSTEM_ALERT_WINDOW` reste la bonne voie pour Guardian.)*
- **Duolingo / widgets de rappel** : présence discrète, jamais intrusive, valeur perçue claire.
- **Apps SOS / sécurité perso** (bouton panique) : FGS type micro/localisation, déclenchement par
  hotword **ou** geste matériel (ex. triple-clic power), confirmation avant alerte réelle (anti-faux-positif),
  enregistrement + géoloc + contacts de confiance. → notre moteur backend `/api/guardian/*` couvre déjà ça.
- **Anti-faux-positif** : countdown annulable avant déclenchement réel (déjà prévu côté JS via le cooldown SR).

---

## 8. Plan d'implémentation proposé (additif, par étapes)

> Aucune étape ne supprime/modifie l'existant. Chaque étape est testable seule.

**Étape 1 — Overlay seul (sans micro)**
- Manifest : `SYSTEM_ALERT_WINDOW`, `RECEIVE_BOOT_COMPLETED`, `FOREGROUND_SERVICE_MICROPHONE`,
  service `foregroundServiceType="microphone|dataSync"`.
- Étendre `GuardianService` (ou nouveau `GuardianOverlayService`) : `addView`/`removeView` de la bulle via
  `WindowManager`, draggable, alpha réglable, tap → ouvre MainActivity sur l'écran Guardian.
- `LunaBridge.enableGuardianOverlay()/disableGuardianOverlay()` + parcours permission overlay
  (`canDrawOverlays` → écran Réglages).
- Toggle « Widget de protection permanent » dans Paramètres > Guardian (web).

**Étape 2 — Déplacer l'écoute mot-clé dans le service**
- Migrer « Guardian Voice Core » de `MainActivity` vers le service ; passer en on-device (API 31+).
- `onKeywordDetected()` dans le service → appelle le moteur Guardian (via la WebView si ouverte, sinon
  déclenchement natif direct de la séquence SOS/enregistrement/géoloc/alerte contacts).

**Étape 3 — Robustesse**
- Receiver `BOOT_COMPLETED` (relance si activé), persistance SharedPreferences.
- Parcours « désactiver l'optimisation batterie pour Luna » (guide OEM).
- Anti-faux-positif (countdown annulable) avant alerte réelle.

**Étape 4 — Finitions UX**
- Niveaux de transparence, snap au bord, collapse auto, design « ange gardien » (issue #20 : pas d'œil/caméra).
- Tests sur Android 13/14/15/16 + un OEM agressif (Xiaomi/Samsung).

---

## 9. Points de vigilance / décisions à valider par Ludo

1. **minSdk** : passer de 24 → 26 pour `TYPE_APPLICATION_OVERLAY` propre ? (24/23 ≈ inexistants en 2026.)
2. **on-device SR** : API 31+ requise pour l'écoute offline → en dessous, fallback réseau (batterie/données).
3. **Distribution** : rester en sideload (zéro contrainte Play) ou viser Play Store (contraintes §5) ?
4. **Déclenchement app fermée** : assumer que le service doit avoir été activé app ouverte (ou au boot) —
   Android **interdit** de réveiller le micro depuis zéro en arrière-plan. À expliquer dans l'UX.
5. **Périmètre** : on **étend** GuardianService sans toucher au moteur `/api/guardian/*` ni à l'architecture
   existante (CLAUDE.md).

---

*Audit livré pour validation. Aucune ligne de code de production modifiée à ce stade — implémentation
sur feu vert de Ludo, étape par étape.*
