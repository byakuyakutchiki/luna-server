# Prompt Claude — Monitoring Objectif Cartes / Localisation Live

Contexte : Services, Documents et Formulaires ont déjà un premier monitoring riche dans `/api/admin/objectives`. Ne les refais pas sauf bug explicite.

Repo :

https://github.com/byakuyakutchiki/luna-server

Source de vérité :

- `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Section `## 10. Cartes — Localisation Temps Réel`
- Méthode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`

## Clarification importante

Ici, **Cartes** ne veut pas dire carte bancaire.

L'objectif est la **carte de localisation temps réel Guardian** :

- l'utilisateur lance une session Guardian ;
- son téléphone envoie une position GPS ;
- Luna stocke une position fraîche ;
- un contact de confiance peut ouvrir un lien temporaire ;
- le contact voit la position sur une carte ;
- le partage expire proprement.

## Objectif utilisateur

L'utilisateur doit pouvoir partager sa position en direct avec un contact de confiance, sans donner accès à tout son compte Luna.

L'objectif est atteint seulement si :

- GuardianEngine est disponible ;
- une session peut exister ;
- la position peut être envoyée par HTTP ou WebSocket ;
- la dernière position est stockée avec horodatage ;
- un token public temporaire peut être généré ;
- `/guardian-live/{token}` fonctionne ;
- `/api/guardian/live-position/{token}` ne retourne que le nécessaire ;
- une position ancienne n'est pas présentée comme du live ;
- le partage peut être arrêté ou expirer.

## Checks techniques suggérés

Ajouter ou compléter un check `_check_objective_cartes()` dans `luna_web.py`, puis l'exposer dans `GET /api/admin/objectives` sous la clé :

```json
{
  "cartes": {
    "status": "warning",
    "goal": "...",
    "checks": [],
    "subservices": {},
    "metrics": {},
    "auto_heal": []
  }
}
```

Vérifier au minimum :

- `_get_guardian()` disponible ;
- `core.guardian.engine.GuardianEngine` importable ;
- Redis accessible ;
- routes présentes :
  - `/guardian`
  - `/api/guardian/start`
  - `/api/guardian/location/{session_id}`
  - `/api/guardian/status/{session_id}`
  - `/api/guardian/ws/{session_id}`
  - `/api/guardian/share/{session_id}`
  - `/api/guardian/live-position/{token}`
  - `/guardian-live/{token}`
  - `/api/guardian/stop/{session_id}`
- page `static/guardian.html` présente ;
- page live contient Leaflet ou un fallback carte/lien ;
- token de partage stocké avec TTL Redis ;
- index des sessions actif pour le tenant ;
- dernière position horodatée si une session active existe.

## Sous-services attendus

| Sous-service | Ce qui doit être vérifié |
|---|---|
| guardian_engine | moteur disponible |
| session_lifecycle | start/status/stop présents |
| gps_ingest | endpoint location + validation lat/lng |
| websocket_live | WS Guardian présent |
| redis_sessions | sessions et token lisibles dans Redis |
| public_share_token | token temporaire, limité et expirant |
| live_position_api | position publique minimale |
| map_page | `/guardian-live/{token}` disponible |
| leaflet_or_fallback | carte visuelle ou lien fallback |
| freshness | position non présentée comme live si trop ancienne |
| privacy | pas d'exposition compte complet/contact/documents |

## Checks fonctionnels suggérés

Ne pas déclencher de vrai SOS, de vrai SMS, ni de vraie alerte contact.

Le test monitoring peut rester structurel, mais il doit pouvoir prouver :

1. Les routes live existent.
2. Redis peut stocker une clé de partage avec TTL.
3. La page live sait interroger `/api/guardian/live-position/{token}`.
4. Une position trop ancienne déclenche un statut `warning/degraded`.
5. L'absence de session active n'est pas critique si l'infrastructure est complète.

## Statuts attendus

```text
ok
```

Infrastructure complète. Si aucune session active existe, ce n'est pas une panne.

```text
warning
```

Aucune session active, aucune position récente, ou dépendance Leaflet CDN sans fallback local.

```text
degraded
```

WebSocket indisponible mais polling HTTP possible, ou Leaflet indisponible mais fallback lien carte possible.

```text
critical
```

GuardianEngine, Redis, routes live ou endpoint position indisponibles.

## Auto-heal attendu

| Problème | Auto-heal / réponse attendue |
|---|---|
| Token expiré pendant session active | régénérer un token |
| WebSocket KO | fallback polling HTTP |
| Leaflet/CDN KO | fallback lien Google Maps |
| GPS refusé | message clair + mode adresse/position manuelle si disponible |
| Position trop ancienne | afficher "dernière position connue" |
| Redis KO | statut `critical`, pas de faux live |

## Limites à respecter

- Ne jamais envoyer de SMS réel pendant le monitoring.
- Ne jamais déclencher de SOS réel.
- Ne jamais créer une fausse session qui alerte quelqu'un.
- Ne pas exposer les contacts, documents, profil, historique ou identité complète via token public.
- Ne pas toucher à `static/index.html` dans ce chantier.

## Sortie souhaitée

Merci de produire :

1. Le code du check monitoring Cartes.
2. Les champs JSON retournés par `/api/admin/objectives`.
3. Les statuts `ok/warning/degraded/critical`.
4. Les auto-heal proposés.
5. Un résumé des fichiers modifiés.
6. Comment tester sans SMS, sans SOS réel, et sans contact réel.

