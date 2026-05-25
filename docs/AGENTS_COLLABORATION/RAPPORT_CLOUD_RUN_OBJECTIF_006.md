# Rapport Cloud Run — Objectif 006

**Auteur** : Claude  
**Date** : 2026-05-25  
**Portée** : lecture seule — aucun secret, aucun token, aucun déploiement  

---

## État Cloud Run au moment du rapport

**Révision active** : `luna-beta-00437-mbm`  
**Région** : `europe-west1`  
**URL** : `https://luna-beta-674304336025.europe-west1.run.app`  
**Statut** : serving (actif)

---

## Ce que les logs ont montré (13h20 — session de test APK)

### Heartbeat

```
POST /api/apk/heartbeat HTTP/1.1" 401  ← 3 requêtes bloquées
```

**Cause** : le middleware global `security_middleware` interceptait la requête
avant l'endpoint. `/api/apk/heartbeat` n'était pas dans `_PUBLIC_PATHS`.

**Fix appliqué** (commit `ce26b5e`) : `/api/apk/heartbeat` ajouté dans `_PUBLIC_PATHS`.
L'endpoint utilise une auth par User-Agent (`LunaApp/2.8 Android/...`) — pas de JWT.

### Événements voix

```
POST /api/apk/event HTTP/1.1" 200  ← nombreux appels OK
```

24 événements stockés dans Redis. Dernière session : `voice_session_ended` à 15:20:30.
Statut : `partial` (session incomplète — `voice_button_clicked` manquant dans cette session).

---

## État des endpoints APK au moment du rapport

| Endpoint | État observé | Note |
|---|---|---|
| `POST /api/apk/heartbeat` | 401 → **fixé** | Déploiement nécessaire pour confirmer |
| `POST /api/apk/event` | 200 OK | Fonctionnel |
| `GET /api/admin/apk-diagnosis` | `waiting_first_contact` | Attendu tant que heartbeat bloqué |
| `GET /api/admin/apk-voice-events` | 24 events, partial | Fonctionnel |

---

## Diagnostic APK — état lu via `/api/admin/apk-diagnosis`

```json
{
  "status": "waiting_first_contact",
  "heartbeat": null,
  "never_received": true,
  "last_seen": null
}
```

Attendu : après le fix + déploiement + test APK, `status` doit passer à `ok` ou `degraded`
selon l'état réel du téléphone de Ludovic.

---

## Commits depuis last stable

| Commit | Description |
|---|---|
| `a3545a1` | fix(assets): images et sons manquants — logo YAWatch, Luna, Aby |
| `268fca4` | build(apk): APK v2.8 rebuildée avec sendHeartbeat() + User-Agent fix |
| `90a428d` | docs: ouverture objectif 006 |
| `caf2706` | fix(006): deux corrections Kimi — label ws_error + journal voix |
| `ce26b5e` | **fix(heartbeat): /api/apk/heartbeat dans _PUBLIC_PATHS** ← dernier |

---

## Action requise avant validation Objectif 006

1. **Déployer** le commit `ce26b5e` sur Cloud Run — `bash deploy.sh`
2. **Tester** : Ludovic ouvre l'APK → heartbeat doit arriver en 30s
3. **Vérifier** : `GET /api/admin/apk-diagnosis` → status != `waiting_first_contact`
4. **Tester voix** : appuyer sur le bouton vocal → vérifier chronologie dans cockpit fondateur

---

## Ce que les agents peuvent vérifier sans accès Cloud

- `GET https://luna-beta-674304336025.europe-west1.run.app/api/admin/health` (public)
- `GET https://luna-beta-674304336025.europe-west1.run.app/api/app/version` (public)

**Interdits dans ce rapport** : aucun secret, aucun token, aucune commande `gcloud`.
Les agents sans accès Google Cloud ne peuvent pas lire les logs directement.

---

## À faire pour les agents

| Agent | Action |
|---|---|
| **DeepSeek** | Relire `startVoice()` sur `origin/main` (commit `7c31a2a`) — voir `CLAUDE_TO_DEEPSEEK_005_UPDATE.md` |
| **Kimi** | Vérifier textes cockpit après fix heartbeat — les textes `luna_knows/guesses/recommends/cannot` sont-ils clairs ? |
| **Cursor** | Vérifier UI fondateur.html + non-régression `startVoice()` après injections événements |
| **Codex** | Confirmer garde-fous PR — déploiement uniquement après validation Ludovic |
| **Claude** | Lead final — synthèse après heartbeat réel + validation Ludovic |

---

*Ce rapport ne contient aucune clé API, token, donnée privée, ni commande de déploiement.*
