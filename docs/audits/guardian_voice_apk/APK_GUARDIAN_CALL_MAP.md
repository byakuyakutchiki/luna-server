.md
# Cartographie des appels APK → WebView → Guardian → Backend

## Date
2026-07-06

## Branche
`docs/audit-guardian-voice-apk-2026-07-06`

## Méthode
Analyse des fichiers sources **sans modification**. Les numéros de ligne proviennent de la branche `audit/guardian-voice-apk-chain` (commit `bd849e6`) qui reflète le code actuellement déployé sur `trace---...`.

---

## Tableau récapitulatif

| Fichier | Fonction/Classe | Rôle exact | Appel fait | Endpoint / JS appelé | Risque | Preuve ligne |
|---|---|---|---|---|---|---|
| `MainActivity.java` | `MainActivity` | Conteneur WebView de l’APK. | Crée `WebView`, charge `LUNA_URL`. | `https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian` | Pointe vers la révision `trace` (ancienne). | L.55, L.417 |
| `MainActivity.java` | `LunaBridge` | Pont JS ↔ Android exposé à la WebView. | Expose des méthodes appelables par `guardian.html`. | `window.LunaBridge.*` | Si `setGuardianProtection` existait, elle bloquerait Web Speech. | L.613-824 |
| `MainActivity.java` | `onPermissionRequest()` | Gère les demandes de permission WebView (micro, caméra). | `request.grant(...)` si permission Android accordée. | `PermissionRequest.RESOURCE_AUDIO_CAPTURE` | Si RECORD_AUDIO refusée, le micro WebView est bloqué. | L.297-337 |
| `MainActivity.java` | `startGuardianService()` | Démarre le service foreground Android. | `startForegroundService(intent)` | `GuardianService.class` | Service de notification uniquement ; ne déclenche pas de SOS. | L.732-751 |
| `MainActivity.java` | `setGuardianProtection()` | **Commentée.** Devrait activer VOSK natif en Phase 2. | — | — | Si décommentée par erreur, `guardian.html` désactiverait Web Speech. | L.786-788 |
| `MainActivity.java` | `evaluateJavascript` | **Non utilisé actuellement** pour `lunaEmergencyVoiceDetected`. | — | — | L’APK n’injecte jamais `window.lunaEmergencyVoiceDetected(...)` car VOSK n’est pas actif. | Absent |
| `GuardianService.java` | `GuardianService` | Service foreground notification. | `startForeground(NOTIFICATION_ID, ...)` | Aucun | Ne fait pas d’écoute vocale native. | L.38-46 |
| `AndroidManifest.xml` | `<uses-permission>` | Déclare les permissions requises. | — | `RECORD_AUDIO`, `ACCESS_FINE_LOCATION`, etc. | Permissions nécessaires mais pas suffisantes ; l’utilisateur doit accepter à l’exécution. | L.10, L.17 |
| `auth.js` | `LunaAuth` | Module auth générique. | `authFetch()` ajoute le token JWT. | `localStorage`, `LunaBridge.getTokens()` | Si token absent/invalidé, toutes les API Guardian retournent 401. | L.27-152 |
| `auth.js` | `LunaAuth.refreshAccessToken()` | Renouvelle le token sur 401. | `POST /api/auth/refresh` | `/api/auth/refresh` | Si refresh échoue, redirige vers `/login`. | L.89-109 |
| `guardian.html` | `LunaAuth.init()` | Vérifie le token au chargement. | `syncFromNative()` puis présence token. | `LunaBridge.getTokens()` | Si pas de token → redirection `/login`. | L.793-801 |
| `guardian.html` | `checkSession()` | Récupère une session Guardian existante. | `GET /api/guardian/sessions` | `/api/guardian/sessions` | Si 401 ou pas de session → bouton Démarrer affiché. | L.2320-2365 |
| `guardian.html` | `guardianStart()` | Crée une nouvelle session Guardian. | `POST /api/guardian/start` | `/api/guardian/start` | Si aucun contact d’urgence → 422, SID reste null. | L.1142-1210 |
| `guardian.html` | `guardianStart()` | Après création SID, choisit la branche vocale. | Teste `window.LunaBridge.setGuardianProtection`. | `_setVoskActiveUI()` ou `_vocalStartWithWatchdog()` | En Phase 1, `setGuardianProtection` est absent → branche Web Speech. | L.1183-1193 |
| `guardian.html` | `_vocalStartWithWatchdog()` | Lance `_vocalStart()` et surveille son état. | `_vocalStart()` toutes les 30s si nécessaire. | `_vocalStart()` | Si `_vocalStart()` échoue silencieusement, le watchdog tente de relancer. | L.1845-1862 |
| `guardian.html` | `_vocalStart()` | Initialise et démarre `SpeechRecognition`. | `new SR()`, `rec.start()`. | API Web Speech du navigateur/WebView | Bloquée si `setGuardianProtection` présent, SR absent, ou `_vocalRec` déjà actif. | L.1763-1843 |
| `guardian.html` | `rec.onstart` | Confirmation que le micro est actif. | `_setMicState('listening')` | UI mic-dot / mic-label | Si jamais appelé, le micro ne fonctionne vraiment pas. | L.1794 |
| `guardian.html` | `rec.onerror` | Gère les erreurs de SpeechRecognition. | `_setMicState('error')`, planifie retry. | — | `not-allowed` = permission refusée. `aborted` = coupure. | L.1810-1824 |
| `guardian.html` | `rec.onresult` | Reçoit le transcript. | Reconstruit `t`, appelle `_vocalMatch(t)`. | `_vocalMatch()` | Bug de reconstruction corrigé par `event.resultIndex`. | L.1798-1808 |
| `guardian.html` | `_vocalMatch()` | Détecte les mots-clés d’urgence. | Parcourt `EMERGENCY_KW`, filtre instrumental. | `openVocalCountdown()` si hit | Si le transcript est répété ou le mot-clé absent → pas de countdown. | L.1678-1753 |
| `guardian.html` | `openVocalCountdown()` | Affiche le compte à rebours d’annulation. | Timer 15s, puis `_triggerSOSVocal()`. | `_triggerSOSVocal()` | Bloqué si `_vocalActive` ou `_sosInProgress` déjà vrai. | L.1857-1926 |
| `guardian.html` | `window.lunaEmergencyVoiceDetected()` | Point d’entrée VOSK natif (Phase 2). | Appelle `openVocalCountdown()`. | `openVocalCountdown()` | **Jamais appelé par l’APK actuel** car VOSK natif n’existe pas. | L.1928-1968 |
| `guardian.html` | `_triggerSOSVocal()` | Envoie l’alerte au backend. | `POST /api/guardian/sos/{SID}` | `/api/guardian/sos/{session_id}` | Bloqué si `SID` null ou `_sosInProgress` vrai. | L.1988-2058 |
| `guardian.html` | `_enrichVoiceContext()` | Enrichit le contexte vocal via LLM. | `POST /api/guardian/voice-context` | `/api/guardian/voice-context` | Best-effort, non bloquant. | L.1958-1968 |
| `luna_web.py` | `guardian_start()` | Crée la session côté backend. | Vérifie contacts, appelle `engine.create_session()`. | — | Retourne 422 si aucun contact d’urgence. | L.15187-15225 |
| `luna_web.py` | `guardian_sos()` | Déclenche l’alerte SOS. | `engine.trigger_sos()`, envoie SMS/appels. | Twilio + SMS | Retourne 409 si déjà déclenché (dedup). | L.15400-15560 |
| `speech_test.html` | `runTest()` | Page de diagnostic isolée. | `new SpeechRecognition()`, `rec.start()`. | API Web Speech | Ne dépend pas de `SID`, `LunaBridge`, `_vocalActive`. | L.58-104 |

---

## Analyse : pourquoi `speech_test.html` fonctionne et Guardian affiche « Luna écoute : inactive/veille » ?

### `speech_test.html` fonctionne car :

1. Il crée directement `new SpeechRecognition()` (L.74).
2. Il appelle `rec.start()` sans condition (L.99).
3. Il n’interagit **pas** avec :
   - `LunaBridge` ;
   - `SID` / session Guardian ;
   - `_vocalActive` / `_sosInProgress` ;
   - `setGuardianProtection` ;
   - les contacts d’urgence.
4. Il est une page de test autonome.

### `guardian.html` affiche « inactive/veille » car :

Le flux pour arriver à `rec.start()` est conditionné par plusieurs gardes :

```
Utilisateur ouvre Guardian
    ↓
LunaAuth.init() → token OK ?
    ↓
checkSession() → session existante ?
    ↓
Utilisateur clique "Démarrer Guardian"
    ↓
guardianStart() → POST /api/guardian/start
    ↓
SID reçu ? (peut échouer avec 422 si pas de contact)
    ↓
guardianStart() teste window.LunaBridge.setGuardianProtection
    ↓
Si absent (Phase 1) → _vocalStartWithWatchdog()
    ↓
_vocalStartWithWatchdog() → _vocalStart()
    ↓
_vocalStart() teste SpeechRecognition, _vocalRec, puis rec.start()
    ↓
rec.onstart → UI "écoute"
```

**La rupture la plus probable** se situe avant `rec.start()` :
- soit `guardianStart()` n’est jamais appelée (utilisateur n’a pas cliqué Démarrer) ;
- soit `guardianStart()` échoue (422 pas de contact) → `SID` null ;
- soit `_vocalStart()` s’arrête sur une garde (`setGuardianProtection` présent par erreur, SR absent, `_vocalRec` déjà actif) ;
- soit `rec.start()` échoue silencieusement (permission refusée).

### Preuve structurale

| Condition | speech_test.html | guardian.html |
|---|---|---|
| Dépend de `SID` | Non | Oui |
| Dépend de `LunaBridge` | Non | Oui (indirectement) |
| Dépend de `setGuardianProtection` | Non | Oui |
| Dépend des contacts d’urgence | Non | Oui (pour créer SID) |
| Vérifie `_vocalActive` / `_sosInProgress` | Non | Oui |

---

## Première rupture potentielle classée par probabilité

| Rang | Rupture | Probabilité | Preuve à collecter |
|---|---|---|---|
| 1 | `guardianStart()` n’est jamais appelée (utilisateur n’a pas cliqué Démarrer) | Élevée | Voir si le bouton vert est visible. |
| 2 | `POST /api/guardian/start` retourne 422 (pas de contact d’urgence) → `SID` null | Élevée | Log `SESSION RESPONSE status=422`. |
| 3 | `_vocalStart()` s’arrête sur `setGuardianProtection` présent ou SR absent | Moyenne | Log `AUDIO ENTER _vocalStart` puis `BAIL`. |
| 4 | `rec.start()` échoue (permission refusée) | Moyenne | `AUDIO rec.start() appel` mais pas `AUDIO SpeechRecognition demarre`. |
| 5 | `_vocalMatch` ne détecte pas le mot-clé | Faible | `onresult` présent mais `MATCH RESULT hit=false`. |
| 6 | `window.lunaEmergencyVoiceDetected` jamais appelé par Android | Certitude | VOSK natif non activé. |

---

## Conclusion

Le problème ne vient **pas** de `MainActivity.java` qui ne transmettrait pas un événement à `guardian.html`. En Phase 1, `MainActivity.java` ne doit pas transmettre d’événement vocal : c’est la WebView qui gère SpeechRecognition.

Le problème vient très probablement de **l’activation de la session Guardian** (`guardianStart()` ou `checkSession()`) ou du **démarrage de `_vocalStart()`** dans `guardian.html`. `speech_test.html` contourne toutes ces gardes, c’est pourquoi il fonctionne.

**Action prioritaire :** collecter les logs `SESSION`, `LISTEN`, `MATCH`, `COUNTDOWN`, `SOS` sur le téléphone pour identifier la première garde bloquante.
