.md
# Schéma du flux réseau — Guardian APK → Backend

## Date
2026-07-06

## Branche
`docs/audit-guardian-voice-apk-2026-07-06`

## Légende

| Icône | Signification |
|---|---|
| 📱 | Exécuté sur le téléphone (code natif Android) |
| 🌐 | Exécuté dans la WebView (JavaScript, même si affiché dans l’APK) |
| ☁️ | Exécuté sur Cloud Run (backend Python) |
| 🔴 | Point de rupture potentiel |

---

## Flux complet d’un SOS vocal

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📱 1. L’utilisateur ouvre l’application Luna (APK)                         │
│      Fichier : android-app/java/fr/yawatch/luna/MainActivity.java           │
│      Ligne : onCreate()                                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  📱 2. MainActivity crée la WebView et expose LunaBridge                    │
│      Fichier : MainActivity.java                                            │
│      Ligne : webView.addJavascriptInterface(new LunaBridge(), "LunaBridge") │
│      → Aucun appel réseau ici.                                              │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  📱 3. La WebView charge l’URL Cloud Run                                     │
│      URL : https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian       │
│      Fichier : MainActivity.java, LUNA_URL (ligne 55, 417)                  │
│      → Requête HTTP GET vers Cloud Run.                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☁️ 4. Cloud Run sert la page guardian.html                                  │
│      Fichier : static/guardian.html                                         │
│      → Réponse HTML + JS + CSS.                                             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 5. guardian.html s’exécute dans la WebView                               │
│      Fichier : static/guardian.html                                         │
│      → Vérifie le token via LunaAuth (localStorage + LunaBridge natif).     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 6. checkSession() — cherche une session existante                        │
│      Fichier : static/guardian.html (ligne 2320)                            │
│      → GET /api/guardian/sessions                                           │
│      🔴 Rupture possible : 401 (token invalide), pas de session.             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☁️ 7. Backend répond avec la liste des sessions                             │
│      Fichier : luna_web.py, guardian_sessions()                             │
│      → Réponse JSON : { sessions: [...] }                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 8. L’utilisateur clique sur « Démarrer Guardian »                        │
│      Fichier : static/guardian.html (ligne 623)                             │
│      → onclick="guardianStart()"                                            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 9. guardianStart() crée une nouvelle session                             │
│      Fichier : static/guardian.html (ligne 1110)                            │
│      → POST /api/guardian/start                                             │
│      Payload : { profile_type, config }                                     │
│      🔴 Rupture possible : 422 si aucun contact d’urgence.                  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☁️ 10. Backend crée la session et retourne le SID                           │
│      Fichier : luna_web.py, guardian_start() (ligne 15187)                  │
│      → Réponse JSON : { success: true, session_id: "..." }                  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 11. guardian.html reçoit SID et choisit la branche vocale                │
│      Fichier : static/guardian.html (ligne 1183)                            │
│      → Teste window.LunaBridge.setGuardianProtection                        │
│      → En Phase 1 : absente → _vocalStartWithWatchdog()                     │
│      🔴 Rupture possible : si setGuardianProtection existait, Web Speech     │
│         serait désactivé.                                                   │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 12. _vocalStart() initialise SpeechRecognition                           │
│      Fichier : static/guardian.html (ligne 1763)                            │
│      → new SpeechRecognition()                                              │
│      → rec.start()                                                          │
│      🔴 Rupture possible : SpeechRecognition absent, permission refusée.     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 + 📱 13. Le navigateur/WebView demande l’accès au micro                  │
│      → WebView appelle MainActivity.onPermissionRequest()                   │
│      Fichier : MainActivity.java (ligne 297)                                 │
│      → Si RECORD_AUDIO accordée : grant()                                   │
│      🔴 Rupture possible : permission refusée → NotAllowedError.             │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 14. rec.onstart → UI « Luna écoute : écoute »                            │
│      Fichier : static/guardian.html (ligne 1794)                            │
│      → Aucun appel réseau.                                                  │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 15. L’utilisateur parle → rec.onresult reçoit le transcript              │
│      Fichier : static/guardian.html (ligne 1798)                            │
│      → Aucun appel réseau (traitement local).                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 16. _vocalMatch() détecte un mot-clé d’urgence                           │
│      Fichier : static/guardian.html (ligne 1678)                            │
│      → Aucun appel réseau (traitement local).                               │
│      🔴 Rupture possible : mot-clé non reconnu à cause du transcript.        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 17. openVocalCountdown() affiche le compte à rebours                     │
│      Fichier : static/guardian.html (ligne 1857)                            │
│      → Timer 15s local.                                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  🌐 18. À 0 seconde, _triggerSOSVocal() envoie l’alerte                      │
│      Fichier : static/guardian.html (ligne 1988)                            │
│      → POST /api/guardian/sos/{SID}                                         │
│      Payload : { incident_id, source:'vocal', context, transcript }         │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☁️ 19. Backend déclenche l’alerte                                           │
│      Fichier : luna_web.py, guardian_sos() (ligne 15400)                    │
│      → engine.trigger_sos()                                                 │
│      → envoie SMS + appel Twilio                                            │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ☁️ 20. Twilio envoie l’appel vocal et le SMS                                │
│      Fichier : integrations/twilio/voice_client.py                          │
│      → Appel : initiate_announcement_call()                                 │
│      → SMS : send_sms()                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Répartition par environnement

### 📱 Téléphone natif (Android Java)

- `MainActivity.onCreate()` — crée WebView.
- `MainActivity$LunaBridge` — pont JS ↔ Android.
- `MainActivity.onPermissionRequest()` — autorise/refuse le micro.
- `GuardianService` — notification permanente (pas d’écoute en Phase 1).

### 🌐 WebView (JavaScript exécuté localement dans l’APK)

- `guardian.html` — interface et logique Guardian.
- `auth.js` — authentification.
- `SpeechRecognition` — écoute vocale Web Speech API.
- `_vocalStart()`, `_vocalMatch()`, `openVocalCountdown()`, `_triggerSOSVocal()`.

### ☁️ Cloud Run (backend Python)

- Sert `guardian.html`, `auth.js`, etc.
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/guardian/sessions`
- `POST /api/guardian/start`
- `POST /api/guardian/sos/{sid}`
- `POST /api/guardian/voice-context`
- Appelle Twilio pour SMS/appels.

---

## Points de rupture et leur localisation

| Rupture | Localisation | Preuve à collecter |
|---|---|---|
| Mauvaise URL Cloud Run | 📱 MainActivity.java | Diagnostic → URL chargée |
| Token invalide/manquant | 🌐 auth.js + ☁️ backend | Diagnostic → token natif/JS ; log `SESSION` |
| Pas de session existante | ☁️ backend `/api/guardian/sessions` | Log `SESSION checkSession` |
| `guardianStart()` non appelée | 🌐 guardian.html (UI) | Bouton vert visible ? Log `SESSION ENTER guardianStart` |
| `POST /api/guardian/start` échoue | ☁️ backend | Log `SESSION RESPONSE status=...` |
| `SID` reste null | 🌐 guardian.html | Log `SESSION SID=...` ou absence |
| `setGuardianProtection` bloque Web Speech | 🌐 guardian.html | Log `AUDIO BAIL setGuardianProtection present` |
| SpeechRecognition absent | 🌐 WebView | Log `AUDIO SpeechRecognition object=ABSENT` |
| Permission micro refusée | 📱 + 🌐 | Log `AUDIO onstart` absent ; `onerror not-allowed` |
| Mot-clé non détecté | 🌐 guardian.html | Log `MATCH RESULT hit=false` |
| Countdown bloqué | 🌐 guardian.html | Log `COUNTDOWN BAIL ...` |
| SOS backend refuse | ☁️ backend | Log `SOS RESPONSE status=...` |

---

## Conclusion

La frontière la plus critique est entre **🌐 WebView** et **☁️ Cloud Run**. La plupart des ruptures observées (token, session, SID, SOS) se situent sur cette frontière. Le code natif 📱 n’est responsable que de la création de la WebView et des permissions ; il ne participe pas au flux vocal en Phase 1.
