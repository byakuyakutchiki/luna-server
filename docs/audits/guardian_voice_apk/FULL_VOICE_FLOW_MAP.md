# Cartographie exhaustive — Flux SOS vocal Guardian

## Date
2026-07-06

## Branche
`docs/audit-guardian-voice-apk-2026-07-06`

## Objectif
Tracer le parcours complet d’un SOS vocal depuis `SpeechRecognition` jusqu’aux SMS/appels, sans modifier le code.

---

## 1. Fonctions réellement exécutées (ordre d’appel)

### A. Initialisation de la session

1. `LunaAuth.init()` — vérifie le token.
2. `(function checkSession(){...})()` — GET `/api/guardian/sessions`.
3. Si aucune session : l’utilisateur clique sur **Démarrer Guardian**.
4. `guardianStart()` — POST `/api/guardian/start`.

### B. Démarrage de l’écoute vocale

5. `guardianStart()` arrive au bloc écoute (ligne ~1144).
6. Condition : `if(window.LunaBridge && window.LunaBridge.setGuardianProtection)`.
7. Si **faux** (APK Phase 1 / Chrome) → `_vocalStartWithWatchdog()`.
8. `_vocalStartWithWatchdog()` appelle `_vocalStart()`.
9. `_vocalStart()` :
   - vérifie `window.LunaBridge.setGuardianProtection` (ligne 1664) ;
   - vérifie `window.SpeechRecognition || window.webkitSpeechRecognition` (ligne 1665) ;
   - vérifie `_vocalRec` (ligne 1667) ;
   - crée `rec = new SR()` ;
   - assigne `rec.onstart`, `rec.onresult`, `rec.onerror`, `rec.onend` ;
   - appelle `rec.start()`.

### C. Capture vocale

10. `rec.onstart` → `_setMicState('listening')`.
11. `rec.onresult` → reconstruit `t` depuis `e.resultIndex` ; appelle `_vocalMatch(t)`.
12. `_vocalMatch(transcript)` :
    - normalise le texte avec `_norm()` ;
    - vérifie `_vocalActive` et `_sosInProgress` ;
    - parcourt `EMERGENCY_KW` ;
    - applique le filtre anti-instrumental pour `KW_AMBIGU` ;
    - si hit → `openVocalCountdown()`.

### D. Countdown et déclenchement

13. `openVocalCountdown()` :
    - vérifie `_vocalActive||_sosInProgress` ;
    - met `_vocalActive = true` ;
    - affiche la modale ;
    - lance un timer de 15s (par défaut).
14. À `n <= 0` :
    - ferme la modale ;
    - `_vocalActive = false` ;
    - appelle `_triggerSOSVocal()`.

### E. Appel backend

15. `_triggerSOSVocal()` :
    - vérifie `!SID || _sosInProgress` ;
    - `_sosInProgress = true` ;
    - `_eemStart(iid,'vocal')` ;
    - POST `/api/guardian/sos/{SID}` avec payload `{incident_id, source:'vocal', context, transcript}`.
16. Backend `guardian_sos(session_id, request)` :
    - déduplique via `_guardian_dedup()` ;
    - `engine.trigger_sos(session_id, context)` ;
    - envoie DM Luna, SMS, appel vocal via Twilio ;
    - retourne JSON avec `success`, `event`, `sms_sent_to`, `calls_placed`, etc.

---

## 2. Fichiers concernés

| Fichier | Rôle |
|---|---|
| `static/guardian.html` | Toute la logique front Guardian, y compris Web Speech, countdown, SOS. |
| `static/auth.js` *(Phase A)* | Authentification + `authFetch`. |
| `luna_web.py` | Endpoints `/api/guardian/*`, logique backend SOS. |
| `core/guardian/engine.py` | `GuardianEngine.create_session()`, `trigger_sos()`. |
| `core/guardian/alerts.py` | `send_guardian_alerts()`, `send_guardian_dm_alerts()`, `build_sms_alert_v1()`. |
| `integrations/twilio/voice_client.py` | `initiate_announcement_call()` pour les appels vocaux. |
| `integrations/sms/*.py` | Envoi SMS. |
| `android-app/java/.../MainActivity.java` | WebView + `LunaBridge` + permissions. |
| `android-app/java/.../GuardianService.java` | Service foreground notification (pas d’écoute vocale native en Phase 1). |

---

## 3. Endpoints réellement appelés

| Méthode | Endpoint | Appelé par | Quand |
|---|---|---|---|
| GET | `/api/guardian/sessions` | `checkSession()` | Au chargement de `/guardian`. |
| POST | `/api/guardian/start` | `guardianStart()` | Quand l’utilisateur clique Démarrer. |
| POST | `/api/guardian/sos/{session_id}` | `_triggerSOSVocal()` | À la fin du countdown vocal. |
| POST | `/api/guardian/voice-context` | `_enrichVoiceContext()` | Pendant le countdown (best-effort). |
| POST | `/api/debug/log` | `_traceGuardian()`, `_dbgSR()` | Télémétrie terrain. |

---

## 4. Variables importantes

| Variable | Fichier | Rôle |
|---|---|---|
| `SID` | `guardian.html` | `session_id` Guardian actif. |
| `_vocalRec` | `guardian.html` | Instance `SpeechRecognition`. |
| `_vocalActive` | `guardian.html` | `true` pendant le countdown. |
| `_vocalListening` | `guardian.html` | `true` quand `rec.onstart` a eu lieu. |
| `_sosInProgress` | `guardian.html` | `true` pendant l’appel SOS backend. |
| `_voiceTranscript` | `guardian.html` | Phrase captée. |
| `_voiceContext` | `guardian.html` | Contexte enrichi affiché. |
| `EMERGENCY_KW` | `guardian.html` | Liste des mots-clés d’urgence. |
| `KW_AMBIGU` | `guardian.html` | Mots-clés filtrables (« à l’aide »). |
| `KW_INSTRUMENTAL_SUFFIX` | `guardian.html` | Suffixes instrumentaux à filtrer. |
| `window.LunaBridge` | `MainActivity.java` | Pont natif exposé à la WebView. |

---

## 5. Conditions permettant de passer à l’étape suivante

| Transition | Conditions requises |
|---|---|
| `guardianStart()` → `_vocalStartWithWatchdog()` | `window.LunaBridge.setGuardianProtection` doit être **falsy**. |
| `_vocalStart()` → `rec.start()` | `SpeechRecognition` existe, `_vocalRec` est null. |
| `rec.onstart` → UI écoute | Aucune condition ; événement du navigateur. |
| `rec.onresult` → `_vocalMatch()` | Aucune condition ; événement du navigateur. |
| `_vocalMatch()` → `openVocalCountdown()` | Un mot-clé de `EMERGENCY_KW` est trouvé dans le transcript normalisé ; `_vocalActive` et `_sosInProgress` sont faux. |
| `openVocalCountdown()` → `_triggerSOSVocal()` | Le countdown atteint 0 sans annulation. |
| `_triggerSOSVocal()` → POST backend | `SID` existe, `_sosInProgress` est faux. |
| Backend → SMS/appels | Contacts existants, `sms_client` / `voice_client` configurés, `_test_mode` géré. |

---

## 6. Conditions qui bloquent le passage

| Etape bloquante | Condition |
|---|---|
| Pas de token valide | `LunaAuth.init()` redirige vers `/login`. |
| Pas de session active | `SID` reste `null`. |
| `setGuardianProtection` présent | `_vocalStart()` retourne immédiatement ; pas de Web Speech. |
| `SpeechRecognition` absent | `_vocalStart()` retourne ; micro inactif. |
| `_vocalRec` déjà défini | `_vocalStart()` retourne. |
| Permission micro refusée | `rec.start()` lève `NotAllowedError` → `rec.onerror`. |
| `_vocalActive` est `true` | `_vocalMatch()` ne matche plus (countdown en cours). |
| `_sosInProgress` est `true` | `_vocalMatch()` et `_triggerSOSVocal()` sont bloqués. |
| Aucun mot-clé dans `EMERGENCY_KW` | `_vocalMatch()` ne déclenche pas le countdown. |
| Mot-clé ambigu filtré | « à l’aide de… », « à l’aide pour… » ne matchent pas. |
| Countdown annulé | `cancelVocalCountdown()` appelé par mot-clé `CANCEL_KW` ou bouton. |
| `SID` absent au moment du SOS | `_triggerSOSVocal()` retourne. |
| Dédup backend | `_guardian_dedup()` retourne 409 si même `incident_id`. |

---

## 7. Points d’interruption possibles (ordre de probabilité)

### Haute probabilité

1. **L’APK charge la mauvaise révision Cloud Run (`trace---...`)**
   - Le code de `guardian.html` sur `trace---...` peut être antérieur aux corrections.
   - Vérification : lire l’URL dans le panneau diagnostic.

2. **`_vocalStart()` n’est pas appelée ou s’arrête avant `rec.start()`**
   - Cause possible : `window.LunaBridge.setGuardianProtection` existe par erreur sur la révision chargée.
   - Vérification : logs `AUDIO ENTER _vocalStart`, `setGuardianProtection=...`, `SpeechRecognition object=...`.

3. **`rec.start()` échoue silencieusement**
   - Cause : permission `RECORD_AUDIO` refusée, ou WebView bloque la demande.
   - Vérification : log `rec.start() appel` présent mais pas `SpeechRecognition demarre`.

### Moyenne probabilité

4. **`onresult` est appelé mais `_vocalMatch` ne matche pas**
   - Cause : transcript répété ou mot-clé absent / filtré.
   - Vérification : logs `MATCH ENTER ... RESULT hit=...`.

5. **`openVocalCountdown` n’est pas appelé**
   - Cause : `_vocalActive` ou `_sosInProgress` bloque.
   - Vérification : log `COUNTDOWN started` absent.

### Faible probabilité

6. **`_triggerSOSVocal` ne part pas**
   - Cause : `SID` perdu ou `_sosInProgress` reste coincé.

7. **Backend refuse l’appel**
   - Cause : 401, 404, 409, ou `Guardian non disponible`.

---

## 8. Diagramme simplifié

```
[Utilisateur parle]
       │
       ▼
┌─────────────────────┐
│  _vocalStart()      │  ← bloquée si setGuardianProtection présent
│  rec.start()        │  ← bloquée si permission refusée
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  rec.onstart        │
│  _setMicState('listening')
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  rec.onresult       │
│  _vocalMatch(t)     │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  EMERGENCY_KW match │  ← bloquée si pas de mot-clé
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  openVocalCountdown │
│  countdown 15s      │  ← bloquée si annulé
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  _triggerSOSVocal() │
│  POST /api/guardian/sos/{SID}
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Backend            │
│  SMS + appel Twilio │
└─────────────────────┘
```

---

## 9. Pourquoi Speech Test fonctionne et Guardian affiche « Luna écoute : INACTIF » ?

### Hypothèse la plus probable

Le **Speech Test** est une page autonome (`speech_test.html`) qui :
- crée directement `new SpeechRecognition()` ;
- appelle `rec.start()` sans condition ;
- n’interagit pas avec `LunaBridge`, `SID`, `_vocalActive`, `_sosInProgress` ;
- ne vérifie pas `setGuardianProtection`.

**Guardian**, lui, passe par une chaîne conditionnelle :
- `guardianStart()` → `_vocalStartWithWatchdog()` → `_vocalStart()`.
- `_vocalStart()` vérifie `window.LunaBridge.setGuardianProtection`.
- Si cette méthode existe (même par erreur), `_vocalStart()` retourne immédiatement et le micro reste inactif.

### Deuxième hypothèse

L’APK charge la révision `trace---...` qui ne contient pas les corrections récentes. Sur cette révision :
- `guardian.html` peut avoir une garde différente ;
- `_vocalStart()` peut être désactivée pour l’APK ;
- les logs diagnostics ajoutés récemment ne sont pas présents.

### Troisième hypothèse

`guardianStart()` n’est jamais appelée (l’utilisateur n’a pas cliqué sur Démarrer Guardian), donc `_vocalStartWithWatchdog()` n’est jamais exécutée.

---

## 10. Première rupture potentielle classée par probabilité

| Rang | Rupture | Probabilité | Preuve demandée |
|---|---|---|---|
| 1 | L’APK charge `trace---...` au lieu de `phase-a-auth---...` | **Très haute** | URL dans le diagnostic. |
| 2 | `_vocalStart()` ne s’exécute pas (garde `setGuardianProtection` ou autre) | **Haute** | Logs `AUDIO ENTER _vocalStart` absents ou suivis d’un `BAIL`. |
| 3 | `rec.start()` échoue silencieusement (permission/WebView) | **Moyenne** | `rec.start() appel` présent mais `SpeechRecognition demarre` absent. |
| 4 | `_vocalMatch` ne matche pas à cause du transcript répété | **Moyenne** | `onresult` présent mais `MATCH RESULT hit=true` absent. |
| 5 | `openVocalCountdown` bloqué par état | **Faible** | `COUNTDOWN started` absent malgré `hit=true`. |
| 6 | `_triggerSOSVocal` bloqué par `SID` ou `_sosInProgress` | **Faible** | Countdown atteint 0 mais pas d’appel backend. |

---

## Conclusion

Le flux vocal Guardian est conditionné par une série de gardes qui peuvent chacune bloquer la chaîne. La preuve terrain actuelle montre que le matériel et la WebView supportent SpeechRecognition (Speech Test OK), mais que la page Guardian réelle n’active pas l’écoute. Les deux priorités d’audit sont :

1. Vérifier l’URL Cloud Run chargée par l’APK.
2. Vérifier si `_vocalStart()` est appelée et pourquoi elle s’arrête.
