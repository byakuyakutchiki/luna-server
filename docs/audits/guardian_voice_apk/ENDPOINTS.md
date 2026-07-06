# Endpoints Guardian concernés

## Backend (luna_web.py)

| Méthode | Endpoint | Rôle | Auth |
|---|---|---|---|
| POST | `/api/auth/login` | Login + retour token/refresh | Non |
| POST | `/api/auth/refresh` | Refresh token | Refresh token |
| POST | `/api/guardian/start` | Créer session Guardian | JWT |
| GET | `/api/guardian/sessions` | Lister sessions actives | JWT |
| POST | `/api/guardian/sos/{sid}` | Déclencher SOS | JWT |
| POST | `/api/guardian/location/{sid}` | Envoyer position | JWT |
| POST | `/api/guardian/voice-context` | Enrichir contexte vocal | JWT |
| POST | `/api/debug/log` | Log terrain (tag `GUARDIAN_SR`) | Non |

## Routes Twilio

| Méthode | Description |
|---|---|
| `initiate_announcement_call(phone, text)` | Appel vocal d’urgence |
| `send_sms(phone, text)` | SMS d’urgence |
| `get_call_status(call_sid)` | Statut final appel |

## URLs Cloud Run observées

| URL | Révision | Rôle |
|---|---|---|
| `https://luna-beta-gly3g647na-ew.a.run.app` | `luna-beta-00970-bad` (100%) | Production |
| `https://trace---luna-beta-gly3g647na-ew.a.run.app` | `luna-beta-00987-vif` | Révision trace (chargée par l’APK) |
| `https://phase-a-auth---luna-beta-gly3g647na-ew.a.run.app` | `luna-beta-phase-b-logs` | Révision audit/diagnostic |

## Problème identifié

L’APK pointe vers `trace---...` qui est une révision antérieure. Il est probable que cette révision ne contienne pas les derniers patches de Phase A/Phase B.

L’endpoint `/api/guardian/sos/{sid}` (ou l’ancien `/trigger`) n’est jamais atteint depuis l’APK Guardian réelle.
