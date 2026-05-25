# Avis Cursor

Agent : Cursor (rôle joué par Claude)
Date : 2026-05-25
Rôle : Cohérence locale — Android / WebView / frontend

---

## MISSION ACTIVE — Objectif 003 Cerveau APK

### Ce que j'ai inspecté

- `android-app/java/fr/yawatch/luna/MainActivity.java`
- `static/index.html` (startVoice, luna_token, window.onerror)
- `docs/AGENTS_COLLABORATION/OBJECTIF_003_CERVEAU_APK.md`

---

### Trouvaille critique — Infrastructure existante dans MainActivity

**Le heartbeat existe déjà à moitié.** `MainActivity.java` contient une méthode `sendLog()` qui POST vers `/api/logs/client` depuis un thread background Java :

```java
// Ligne 337-355 — MainActivity.java
private void sendLog(final String level, final String msg, final String src) {
    new Thread(() -> {
        URL url = new URL(LUNA_URL + "/api/logs/client");
        // POST JSON { level, msg, src } — pas d'auth token, timeout 4s
    }).start();
}
```

Elle est déjà appelée pour :
- `APP START v2.8 (19) — OnePlus Android 14` (ligne 327)
- Erreurs SSL WebView (ligne 303)
- Erreurs WebView (ligne 309)
- Navigation LOAD START / LOAD OK (lignes 314, 319)
- Erreurs JavaScript console (ligne 212)

**Conclusion Cursor** : on n'a pas besoin de créer `/api/apk/heartbeat` from scratch — on peut enrichir `sendLog()` ou créer `sendEvent()` avec le même pattern, en ajoutant `apk_version`, `device_model`, `android_version` déjà disponibles en Java.

---

### Points d'ancrage disponibles

| Signal | Source | Méthode |
|---|---|---|
| `apk_started` | Java — ligne 327 | `sendLog("info", "APP START...")` — déjà actif |
| `apk_version` | Java — `CURRENT_VERSION = "2.8"` | disponible |
| `device_model` | Java — `Build.MODEL` | disponible |
| `android_version` | Java — `Build.VERSION.RELEASE` | disponible |
| `cloud_url` | Java — `LUNA_URL` | disponible |
| `webview_error` | Java — onReceivedError | déjà capté par sendLog |
| `ssl_error` | Java — onReceivedSslError | déjà capté |
| `js_error` | Java — WebChromeClient console | déjà capté |
| `voice_button_clicked` | JS — index.html `startVoice()` | à ajouter |
| `mic_permission_*` | JS — getUserMedia success/error | à ajouter |
| `voice_ws_opened/closed` | JS — WebSocket onopen/onclose | à ajouter |
| `audio_received` | JS — message type "audio" | à ajouter |
| `voice_no_audio_timeout` | JS — timer après clic | à ajouter |

---

### frontend_build manquant dans index.html

Codex propose `"frontend_build": "2026-05-25-voice-fix"` dans le payload. Ce champ n'existe pas dans `index.html` actuellement. Il faut ajouter une constante en haut du script :

```javascript
var LUNA_FRONTEND_BUILD = "2026-05-25-voice-fix";
```

**Cursor recommande** de définir cette constante une fois et de la lire depuis JS pour les événements APK.

---

### Auth — deux mécanismes à prévoir

| Source | Auth disponible |
|---|---|
| Java (sendLog) | Aucune — endpoint `/api/logs/client` est libre |
| JS (fetch) | `localStorage("luna_token")` — JWT disponible |

**Cursor recommande** : heartbeat Java → `/api/apk/heartbeat` sans auth (ou avec `User-Agent: LunaApp/2.8` comme identifiant), événements voix JS → `/api/apk/event` avec header `Authorization: Bearer <luna_token>`.

---

### Ce qui change dans quels fichiers

| Fichier | Modification nécessaire |
|---|---|
| `android-app/java/fr/yawatch/luna/MainActivity.java` | Ajouter `sendEvent()` enrichi (apk_version, device, android) |
| `static/index.html` | Ajouter `LUNA_FRONTEND_BUILD` + `sendApkEvent()` dans startVoice |
| `luna_web.py` | Ajouter `POST /api/apk/heartbeat` + `POST /api/apk/event` |
| `luna_web.py` — monitoring | Lire dernier heartbeat dans `_check_objective_voix()` |

---

### Risques identifiés par Cursor

- **Rebuild APK obligatoire** pour tout changement Java → ne pas sous-estimer le délai
- **Rate limiting essentiel** sur `/api/apk/heartbeat` — le Java thread tourne à l'app start, pas en boucle continue → OK pour phase 1
- **Ne pas bloquer le thread UI** — `sendLog()` utilise déjà un thread séparé, même pattern à garder
- **Pas de token en Java** — le heartbeat Java ne peut pas utiliser `luna_token` (localStorage JS non accessible depuis Java) → implémenter un shared secret simple ou laisser l'endpoint semi-ouvert avec rate limiting

---

### Verdict Cursor

L'idée est cohérente avec l'architecture existante. Le pattern `sendLog()` prouve que c'est faisable. Phase 1 (heartbeat Java enrichi) = faible risque, fort impact diagnostic. Phase 2 (événements voix JS) = moyen risque, à faire après validation Phase 1.

**Recommandation** : commencer par enrichir `sendLog()` en `sendEvent()` côté Java pour le heartbeat — zéro nouveau concept, même pattern, rebuild APK une seule fois.

Architecture finale à valider par Claude + Ludovic avant implémentation.
