# Claude — Architecture intégration DeepSeek temps réel APK

**Date** : 2026-05-25  
**Objectif** : Définir l'intégration serveur avant implémentation  
**Statut** : proposition — en attente de `DEEPSEEK_AVIS_008_TEMPS_REEL_APK.md`  
**Règle** : pas de déploiement sans validation Ludovic

---

## Ce que j'attends de DeepSeek avant de coder

Le contrat d'entrée exact :
- Format JSON minimal de l'événement incident
- Seuils précis de déclenchement (ex : WS fermé < 5s, 0 audio reçu après 10s)
- Fenêtre temporelle exacte à envoyer (30s ou 60s d'événements)
- Stratégie anti-gaspillage tokens (max tokens par appel, fréquence max)

---

## Architecture côté serveur (ce que j'implémenterai)

### Endpoint

```
POST /api/deepseek/diagnose
```

- Auth : JWT fondateur uniquement (pas accessible aux clients)
- Body : événements incident compacts (fournis par l'APK ou le serveur)
- Rate limit : 1 appel / 30s maximum par session (configurable)
- Pas de déclenchement si navigation normale sans anomalie

### Flux

```
1. APK détecte anomalie → POST /api/apk/event (événements existants)
2. luna_web.py détecte le pattern incident dans _analyze_voice_events()
   ou via un watcher Redis dédié
3. luna_web.py construit la fenêtre compacte (30-60s d'événements filtrés)
4. luna_web.py appelle DeepSeek API côté serveur (clé dans .env)
5. DeepSeek retourne le diagnostic structuré
6. luna_web.py stocke dans Redis : luna:deepseek:diagnoses (LPUSH, max 20)
7. luna_web.py met à jour le journal fondateur
8. L'endpoint /api/admin/apk-diagnosis retourne le dernier diagnostic
9. fondateur.html affiche le diagnostic dans la section voix APK
```

### Clé DeepSeek

```
DEEPSEEK_API_KEY=sk-...  (dans .env Cloud Run uniquement)
```

Jamais dans l'APK, jamais dans GitHub, jamais dans les logs.

### Ce que j'enverrai à DeepSeek (fenêtre filtrée)

```json
{
  "incident_type": "voice_no_audio | ws_closed_early | service_unavailable",
  "timestamp_utc": 1779734000,
  "apk_version": "2.8",
  "events": [
    {"event": "voice_click_received", "ts": 1779733990},
    {"event": "voice_ws_opened", "ts": 1779733992},
    {"event": "voice_ws_closed", "ts": 1779733995, "ws_close_code": 1006}
  ],
  "server_error": "insufficient_quota",
  "model": "gpt-realtime-mini",
  "session_duration_s": 3
}
```

### Ce que je n'enverrai jamais à DeepSeek

- Audio brut
- Transcript privé
- Token JWT
- Clé API
- Email ou données personnelles
- Contenu de conversation

### Sortie DeepSeek attendue

```json
{
  "diagnostic": "...",
  "preuve": ["..."],
  "cause_probable": "...",
  "zone": "openai | apk | serveur | cache | ui | inconnue",
  "action_recommandee": "...",
  "risque": "faible | moyen | élevé",
  "validation_ludovic_requise": true
}
```

### Redis

```
luna:deepseek:diagnoses → LPUSH, LTRIM max 20
luna:deepseek:last_call_ts → timestamp dernier appel (rate limit)
```

### Cockpit fondateur.html

Nouvelle section "Diagnostic DeepSeek" dans la page fondateur :
- Horodatage du diagnostic
- Zone concernée (badge coloré)
- Diagnostic en clair
- Action recommandée
- Bouton "Valider" / "Ignorer"

---

## Ce que je n'implémenterai pas

- Aucun appel DeepSeek depuis l'APK directement
- Aucune clé dans le frontend
- Aucun appel permanent (uniquement sur incident détecté)
- Aucune correction automatique sans validation Ludovic

---

## Ordre d'implémentation (après avis DeepSeek + validation Ludovic)

1. Ajouter `DEEPSEEK_API_KEY` dans `.env`
2. Créer `integrations/deepseek/apk_diagnostic.py` — appel API isolé
3. Ajouter `POST /api/deepseek/diagnose` dans `luna_web.py`
4. Ajouter détection pattern incident dans `_analyze_voice_events()`
5. Stocker diagnostic dans Redis
6. Exposer via `GET /api/admin/apk-diagnosis` (déjà existant — enrichir)
7. Afficher dans `fondateur.html`
8. Déployer après validation Ludovic
