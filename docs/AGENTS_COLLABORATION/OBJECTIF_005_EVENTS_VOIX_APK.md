# Objectif 005 — Événements voix APK : prouver ce qui se passe quand Ludovic appuie sur le bouton vocal

**Statut** : cadré — en attente validation heartbeat réel (objectif 003/004)
**Priorité** : haute
**Lead** : Claude
**Date ouverture** : 2026-05-25
**Dépendance** : Objectif 003 Phase 1 (heartbeat APK) doit avoir reçu un premier signal réel avant d'implémenter.

---

## Problème

Le heartbeat APK (Objectif 003) sait que le téléphone respire.
Le diagnostic APK (Objectif 004) sait interpréter ce signal.

Mais aucun des deux ne sait ce qui se passe quand Ludovic appuie sur le bouton vocal.

**Cas réel observé** : bouton vocal appuyé → aucune voix après 15-20 secondes → silence.

Le cockpit fondateur doit pouvoir afficher exactement où ça bloque, avec une chronologie réelle.

---

## But

Quand Ludovic appuie sur le bouton vocal dans l'APK, Luna doit savoir exactement à quelle étape ça bloque.

### Chronologie attendue (cas succès)

```
voice_button_clicked         → bouton appuyé
microphone_permission_granted → micro autorisé
voice_ws_opened              → WebSocket serveur ouvert
voice_audio_sent             → audio envoyé vers serveur
voice_audio_received         → audio reçu depuis serveur (Luna parle)
```

### Chronologie attendue (cas échec — Ludovic n'entend rien)

```
voice_button_clicked         → bouton appuyé
microphone_permission_granted → micro autorisé
voice_ws_opened              → WebSocket serveur ouvert
voice_audio_sent             → audio envoyé vers serveur
voice_no_audio_after_timeout → aucun audio reçu après 20 secondes ← bloc identifié
voice_ws_closed              → WebSocket fermé
```

---

## Livrable principal

### Endpoint serveur

```
POST /api/apk/event
```

Payload JSON :

```json
{
  "event": "voice_no_audio_after_timeout",
  "ts": 1690000000,
  "elapsed_ms": 20000,
  "apk_version": "2.8",
  "screen": "home",
  "ws_connected": true,
  "audio_sent": true,
  "audio_received": false,
  "ws_close_code": null,
  "error_msg": ""
}
```

Règles :
- Pas d'audio brut, pas de transcript, pas de position exacte, pas de secrets
- Auth : `Authorization: Bearer <luna_token>` (JWT disponible dans localStorage JS)
- Rate limit : max 10 événements voix par session

### Événements à capturer (priorité décroissante)

| Événement | Source | Priorité |
|---|---|---|
| `voice_button_clicked` | JS — `startVoice()` | critique |
| `microphone_permission_granted` | JS — `getUserMedia` success | critique |
| `microphone_permission_denied` | JS — `NotAllowedError` | critique |
| `voice_ws_opened` | JS — WebSocket `onopen` | critique |
| `voice_audio_sent` | JS — premier chunk audio envoyé | haute |
| `voice_audio_received` | JS — premier message audio reçu | haute |
| `voice_no_audio_after_timeout` | JS — timer 20s après clic | haute |
| `voice_ws_closed` | JS — WebSocket `onclose` | haute |
| `voice_ws_error` | JS — WebSocket `onerror` | haute |
| `voice_session_ended` | JS — `stopVoice()` | normale |

### Affichage dans GET /api/admin/apk-diagnosis

Nouveau champ `voice_events` avec le dernier parcours voix :

```json
{
  "voice_status": "no_audio_timeout",
  "voice_summary": "Bouton appuyé, micro OK, WebSocket ouvert — mais aucun audio reçu après 20s",
  "voice_events": [...],
  "voice_last_session_ts": "2026-05-25 13:00:00"
}
```

### Affichage fondateur.html

```
Voix APK — Problème important
Luna sait : le bouton vocal a été appuyé, le micro est autorisé, le WebSocket s'est ouvert,
            mais aucun audio n'a été reçu après 20 secondes.
Luna suppose : la réponse OpenAI ou le playback WebView ne revient pas jusqu'au téléphone.
Luna recommande : vérifier la chaîne WebSocket → OpenAI → audio client.
Luna ne peut pas : corriger automatiquement le flux audio.
```

---

## Rôles par agent

### Claude (lead)
- Décider le schéma final des événements
- Implémenter `POST /api/apk/event` côté `luna_web.py`
- Ajouter le diagnostic voix dans `_analyze_apk_state()` et `GET /api/admin/apk-diagnosis`
- Mettre à jour `fondateur.html` (section voix)
- Déployer uniquement après validation Ludovic
- Ne pas rebuild APK si ce n'est pas nécessaire (événements JS = côté `static/index.html` uniquement)

### DeepSeek
- Analyser `startVoice()` dans `static/index.html`
- Proposer les points d'injection précis (lignes) pour chaque événement
- Définir le timeout "aucun audio après 20s" et son implémentation
- Vérifier le cas précis : bouton appuyé → WebSocket ouvert → silence → fermeture
- Ne pas modifier `luna_web.py` ni `MainActivity.java`
- Branche : `ds/objectif-005-events-voix`

### Kimi
- Écrire les textes humains du cockpit fondateur (format Luna sait / Luna suppose / Luna recommande / Luna ne peut pas)
- Éviter les phrases fausses ou culpabilisantes ("tu n'as pas testé", "erreur")
- Distinguer clairement ce que Luna observe vs ce qu'elle suppose
- Valider les 10 libellés d'événements côté UI
- Branche : `kimi/objectif-005-events-voix`

### Cursor
- Vérifier que les événements JS n'alourdissent pas ni ne cassent `startVoice()`
- Vérifier la cohérence entre noms d'événements JS, endpoint serveur et affichage fondateur.html
- Signaler tout chevauchement UI ou risque de régression voix
- Branche : `cursor/objectif-005-events-voix`

### Codex
- Cadrer la PR GitHub (branche, découpage, garde-fous)
- Relire les tests proposés
- Vérifier qu'on reste Phase 2 voix, pas auto-healing
- Branche : `codex/objectif-005-events-voix`

---

## Interdictions absolues

- Pas d'audio brut dans les événements
- Pas de transcript vocal dans les événements
- Pas de géolocalisation
- Pas de correction automatique de la voix
- Pas de déploiement Cloud Run sans validation Ludovic
- Pas de rebuild APK pour cette phase (les événements sont côté JS, pas Java)
- Pas de gros refactor de `startVoice()` — injection minimale uniquement

---

## Tests de validation

### Sans téléphone (vérification statique)
- `startVoice()` contient bien un `sendApkEvent("voice_button_clicked")`
- Timer 20s déclenche bien `sendApkEvent("voice_no_audio_after_timeout")`
- `onopen` WebSocket envoie bien `sendApkEvent("voice_ws_opened")`
- `sendApkEvent()` utilise bien `luna_token` depuis localStorage
- `POST /api/apk/event` répond 200 avec payload valide
- `POST /api/apk/event` répond 403 si pas de token ou token invalide

### Avec téléphone fondateur (test réel)
- Ouvrir APK → heartbeat vu (objectif 004 passé au vert)
- Appuyer sur bouton vocal → `voice_button_clicked` visible dans le diagnostic
- Attendre 20s sans voix → `voice_no_audio_after_timeout` visible
- Cockpit fondateur affiche : "Problème voix — aucun audio reçu après 20s"
- Clore la session voix → `voice_ws_closed` visible

---

## Validation

- [ ] Schéma événements validé par Claude
- [ ] DeepSeek a proposé les points d'injection dans `startVoice()`
- [ ] Kimi a rédigé les textes fondateur
- [ ] Cursor a vérifié la cohérence UI
- [ ] Codex a cadrée la PR
- [ ] Claude a implémenté `POST /api/apk/event`
- [ ] Claude a mis à jour `_analyze_apk_state()` avec les événements voix
- [ ] Ludovic a validé avant déploiement
- [ ] Test réel : bouton vocal → événements visibles dans cockpit

---

## Condition de succès

Ludovic appuie sur le bouton vocal, attend 20 secondes, n'entend rien.
Le cockpit fondateur affiche que la voix APK est en problème réel, avec la chronologie précise.
