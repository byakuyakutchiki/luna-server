# Prompt Claude — Monitoring Objectif Services / Concierge

Tu travailles sur le repo GitHub :

https://github.com/byakuyakutchiki/luna-server

Objectif :
Implémenter le monitoring fonctionnel de l'objectif **Services / Concierge** dans `/api/admin/objectives`, en suivant le cahier des charges :

`docs/CAHIER_DES_CHARGES_MONITORING.md`

Section concernée :

`## 4. Services / Concierge — Actions Déléguées`

Ne traite pas encore les autres onglets. Le but est de valider d'abord Services / Concierge.

## Contexte code

Fichiers importants :

- `luna_web.py`
- `GUIDE_DEV.md`
- `docs/duffel_terms.md`

Dans `luna_web.py`, les outils concierge principaux sont :

- `_SIMLI_TOOLS`
- `_handle_tavus_tool_call`
- `_tool_get_weather`
- `_tool_get_news`
- `_tool_search_web`
- `_tool_search_places`
- `_tool_get_page_info`
- `_tool_search_flights`
- `_tool_search_hotels`
- `_tool_book_restaurant`
- `_tool_send_sms`
- `_tool_send_email`
- `_tool_call_contact`
- `_tool_invite_visio`
- `_tool_send_conclusions`
- `_tool_create_note`
- `_tool_generate_document`
- outils `secretary_*`

Endpoint admin existant :

- `GET /api/admin/health`

Le nouvel objectif doit être exposé via :

- `GET /api/admin/objectives`

Si `/api/admin/objectives` existe déjà après le travail sur Instructions, ajoute simplement le bloc `services`. Sinon crée l'endpoint avec une structure extensible.

## Travail demandé

Ajouter un helper :

```python
async def _check_objective_services() -> dict:
    ...
```

Ce helper doit retourner un bloc JSON de ce type :

```json
{
  "status": "degraded",
  "goal": "Luna agit pour l'utilisateur via les services de conciergerie.",
  "checks": [
    {"name": "tools_catalog_loaded", "status": "ok", "message": "_SIMLI_TOOLS charge"},
    {"name": "tool_dispatcher_available", "status": "ok", "message": "Dispatcher Tavus/Simli disponible"},
    {"name": "memory_manager_available", "status": "ok", "message": "Memory Manager disponible"},
    {"name": "redis_available", "status": "ok", "message": "Redis disponible"}
  ],
  "subservices": {
    "weather": {"status": "ok", "critical": false},
    "news": {"status": "ok", "critical": false},
    "web_search": {"status": "warning", "critical": false, "missing": ["SERPER_API_KEY"]},
    "places_restaurants": {"status": "warning", "critical": false, "missing": ["SERPER_API_KEY"]},
    "sms": {"status": "ok", "critical": true},
    "voice_call": {"status": "ok", "critical": true},
    "email": {"status": "warning", "critical": false, "mode": "draft_only"},
    "payments": {"status": "warning", "critical": false, "mode": "founder_optional"},
    "flights": {"status": "degraded", "critical": false, "missing": ["DUFFEL_ACCESS_TOKEN"]},
    "hotels": {"status": "degraded", "critical": false, "missing": ["DUFFEL_ACCESS_TOKEN"]},
    "secretary": {"status": "ok", "critical": false}
  },
  "metrics": {
    "tools_declared": 0,
    "tools_available": 0,
    "missing_env": [],
    "optional_missing_env": [],
    "last_tool_error": null
  },
  "auto_heal": [
    {"condition": "weather_primary_down", "action": "fallback_open_meteo", "available": true},
    {"condition": "twilio_transient_failure", "action": "queue_sms_in_redis", "available": true},
    {"condition": "missing_location", "action": "fallback_profile_city", "available": true}
  ]
}
```

## Checks minimum à implémenter

### Globaux

- `_SIMLI_TOOLS` existe et contient des outils.
- Les outils essentiels attendus sont déclarés :
  - `get_weather`
  - `get_news`
  - `search_web`
  - `search_places`
  - `search_flights`
  - `search_hotels`
  - `book_restaurant`
  - `send_sms`
  - `call_contact`
  - `send_email`
  - `create_note`
  - `generate_document`
- `_memory_manager` disponible.
- `_redis_client` disponible ou erreur propre.
- Les fonctions Python correspondant aux outils existent.

### Sous-services

Météo :
- `ok` si `_tool_get_weather` existe.
- Pas besoin de clé API, car wttr.in + Open-Meteo fallback.

Actualités :
- `ok` si `_tool_get_news` existe.
- Flux RSS gratuits, donc pas de clé obligatoire.

Recherche web :
- `ok` si `SERPER_API_KEY` est présente.
- `warning` si absente.

Lieux / restaurants :
- `ok` si `SERPER_API_KEY` est présente.
- `warning` si absente.
- Vérifier aussi que `_tool_search_places` et `_tool_book_restaurant` existent.

SMS :
- `ok` si Twilio est configuré (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, numéro).
- `critical` si SMS attendu mais Twilio absent.
- Ne pas envoyer de vrai SMS dans le monitoring.

Appel vocal :
- `ok` si Twilio est configuré.
- Vérifier que `_tool_call_contact` existe.
- Mentionner que les numéros d'urgence doivent rester bloqués.

Email :
- `ok` si SMTP/API réellement configuré.
- `warning` si seulement mode brouillon.
- Ne pas envoyer de vrai email dans le monitoring.

Paiements :
- `warning` sur serveur fondateur si Stripe absent.
- `critical` seulement si environnement exploitant/client exige Stripe.
- Ne pas créer de PaymentIntent dans le monitoring.

Vols / hôtels :
- `ok` si `DUFFEL_ACCESS_TOKEN` présent et fonctions présentes.
- `degraded` si fonctions présentes mais Duffel absent.
- Ne jamais inventer de prix ou d'offres.
- Ne pas faire de réservation réelle dans le monitoring.

Secrétariat :
- `ok` si les modules secretary sont importables et Redis disponible.
- `warning` si Redis absent.

## Règles de statut global

- `critical` si le catalogue d'outils est absent, le dispatcher est indisponible, ou Redis/Memory Manager rendent les actions impossibles.
- `degraded` si plusieurs sous-services optionnels sont absents mais les actions critiques restent possibles.
- `warning` si un seul service optionnel manque.
- `ok` si tout ce qui est attendu dans l'environnement courant est disponible.

## Contraintes

- Ne pas envoyer de SMS, email, appel, paiement, réservation, ni vraie commande Duffel pendant un check.
- Ne pas refactorer massivement `luna_web.py`.
- Ne pas modifier `.env`.
- Ne pas committer de secret.
- Ne pas rendre Stripe critique sur le serveur fondateur si le cahier des charges le marque optionnel.
- Toujours retourner un JSON propre même en cas d'exception.
- Les erreurs doivent être explicables : `missing`, `message`, `recommended_fix`.

## Endpoint

Si `/api/admin/objectives` existe :

```python
objectives["services"] = await _check_objective_services()
```

Sinon créer :

```python
@app.get("/api/admin/objectives")
async def admin_objectives(request: Request):
    if not _verify_admin(request):
        return JSONResponse(status_code=401, content={"error": "Non autorise"})
    objectives = {
        "services": await _check_objective_services()
    }
    return {
        "status": _aggregate_objective_status(objectives),
        "objectives": objectives,
        "checked_at": datetime.utcnow().isoformat()
    }
```

Si une fonction d'agrégation existe déjà depuis le travail Instructions, la réutiliser.

## Réponse attendue

Dans ta réponse finale :

- Liste les fichiers modifiés.
- Montre un exemple JSON de `/api/admin/objectives`.
- Explique comment tester sans déclencher d'action réelle.
- Signale les dépendances absentes possibles (`SERPER_API_KEY`, `DUFFEL_ACCESS_TOKEN`, Stripe, SMTP, Twilio).
- Ne travaille pas encore sur Documents, Formulaires ou Cartes.
