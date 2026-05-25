# Objectif 003 — Cerveau APK / télémétrie appareil réel

## Intention fondateur

Ludovic veut que l'APK Luna ne soit pas seulement une WebView passive.
Elle doit devenir un capteur fiable de l'expérience réelle utilisateur et
communiquer son état au cerveau central.

Formule de référence :

> Cloud Run sait ce qu'il sert. L'APK sait ce que l'utilisateur vit. Luna doit comparer les deux.

## Problème à résoudre

Il existe un décalage naturel entre :

1. code modifié localement ;
2. code poussé GitHub ;
3. image Docker buildée ;
4. Cloud Run déployé ;
5. APK installée et réellement utilisée ;
6. expérience vécue sur le téléphone.

Pendant ce décalage, le téléphone peut voir une erreur que GitHub, Cloud Run
et le monitoring serveur ne voient pas : voix silencieuse, WebView bloquée,
ancienne version, mauvaise URL, permission micro refusée, WebSocket fermé,
aucun audio reçu après clic vocal.

## Principe proposé

Créer un "cerveau APK" minimal : un module d'observation embarqué qui envoie
des événements non sensibles au serveur.

Ce module ne déploie rien, ne modifie rien en production et ne possède aucun
secret d'administration. Il observe et rapporte.

## Premier niveau — heartbeat APK

Endpoint envisagé :

```text
POST /api/apk/heartbeat
```

Payload minimal envisagé :

```json
{
  "apk_version": "2.8",
  "device_role": "founder",
  "cloud_url": "https://luna-beta-674304336025.europe-west1.run.app",
  "webview_user_agent": "LunaApp/2.8 ...",
  "frontend_build": "2026-05-25-voice-fix",
  "last_screen": "home",
  "network": "online",
  "timestamp_client": "2026-05-25T12:00:00+02:00"
}
```

Objectif : savoir si le téléphone réel est vivant, quelle version il utilise
et quelle URL il charge.

## Deuxième niveau — événements critiques

Endpoint envisagé :

```text
POST /api/apk/event
```

Événements prioritaires :

- `apk_started`
- `webview_page_loaded`
- `frontend_build_seen`
- `voice_button_clicked`
- `microphone_permission_granted`
- `microphone_permission_denied`
- `voice_ws_opened`
- `voice_ws_closed`
- `voice_audio_chunk_sent`
- `voice_audio_chunk_received`
- `voice_no_audio_after_timeout`
- `javascript_error`
- `network_error`

Payload voix minimal envisagé :

```json
{
  "event": "voice_no_audio_after_timeout",
  "apk_version": "2.8",
  "frontend_build": "2026-05-25-voice-fix",
  "screen": "home",
  "elapsed_ms": 20000,
  "ws_connected": true,
  "audio_sent": true,
  "audio_received": false,
  "error_code": "NO_AUDIO_DELTA"
}
```

## Troisième niveau — visibilité admin

À terme, exposer dans `GET /api/admin/objectives` ou un dashboard admin :

- dernier téléphone vu ;
- version APK installée ;
- URL Cloud Run réellement chargée ;
- build frontend réellement vu ;
- dernier état voix ;
- dernier clic vocal ;
- dernier WebSocket voix ouvert/fermé ;
- audio reçu oui/non ;
- dernière erreur WebView ;
- décalage détecté entre version attendue et version réelle.

Exemple d'objectif :

```json
{
  "apk_real_device": {
    "status": "warning",
    "last_seen_seconds": 38,
    "apk_version": "2.8",
    "frontend_build": "2026-05-25-voice-fix",
    "voice_last_result": "no_audio_received_after_20s",
    "recommended_action": "tester voix appareil fondateur avant validation"
  }
}
```

## Rôles par agent

### Claude

- Décider l'architecture finale.
- Valider le niveau de télémétrie acceptable.
- Vérifier que l'implémentation ne fragilise pas Cloud Run, Redis, auth, monitoring ou APK.
- Décider si les données vont dans Redis, logs structurés, ou les deux.
- Préparer le déploiement uniquement après validation Ludovic.

### DeepSeek

- Travailler depuis VS Code sur branche `ds/objectif-003-apk-telemetry`.
- Proposer un schéma d'événements minimal.
- Examiner les fichiers Android/WebView et le frontend pour identifier où capter les signaux.
- Proposer une implémentation locale limitée : heartbeat + événements voix.
- Ne jamais ajouter de secret, accès Cloud ou commande de déploiement côté APK.

### Kimi

- Auditer la documentation : ce que Luna promet à l'utilisateur vs ce qui est observable réellement.
- Identifier les signaux manquants pour prouver qu'une fonctionnalité marche sur appareil réel.
- Comparer APK réelle, WebView, Cloud Run et monitoring.
- Proposer les textes de statut lisibles pour Ludovic.

### Codex

- Maintenir le cadrage GitHub.
- Préparer les PR ciblées.
- Ajouter ou proposer les tests automatisables sans action réelle.
- Vérifier que les changements restent sur branches dédiées.
- Refuser les gros refactors non validés.

### Cursor

- Vérifier la cohérence locale dans VS Code.
- Inspecter les fichiers Android, frontend et docs après propositions DeepSeek/Kimi.
- Signaler les incohérences de chemins, noms d'événements et fichiers touchés.

## Garde-fous sécurité

- Ne pas collecter audio brut.
- Ne pas collecter transcript privé.
- Ne pas collecter position exacte.
- Ne pas exposer token JWT, clé API, `.env`, cookies ou identifiants.
- Ne pas permettre à l'APK de déclencher un déploiement.
- Ne pas permettre à l'APK de modifier Cloud Run ou GitHub.
- Limiter la fréquence heartbeat pour éviter spam réseau et batterie.
- Prévoir un flag serveur pour désactiver la télémétrie APK.

## Stratégie progressive proposée

### Phase 1 — Cadrage

Créer les documents et demander avis aux agents.

### Phase 2 — Heartbeat minimal

Implémenter uniquement `POST /api/apk/heartbeat`, stockage court en Redis,
et affichage admin simple.

### Phase 3 — Voix réelle

Ajouter événements voix non sensibles : clic, permission micro, WebSocket,
audio envoyé, audio reçu, timeout.

### Phase 4 — Dashboard fondateur

Afficher l'état du téléphone fondateur dans `/api/admin/objectives` ou page admin.

### Phase 5 — Généralisation exploitants

Étendre seulement après validation : plusieurs appareils, anonymisation,
consentement, quotas et rétention.

## Décision à demander à Ludovic

Valider le principe :

- [ ] oui, créer un heartbeat APK minimal ;
- [ ] oui, inclure les événements voix non sensibles ;
- [ ] non, rester au monitoring serveur uniquement ;
- [ ] à revoir.

Commentaire Ludovic :
