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

L'objectif n'est pas seulement la carte Guardian privée. Ludo veut une expérience proche de Waze :

- un utilisateur Luna peut voir qu'il y a d'autres utilisateurs Luna autour ;
- les autres utilisateurs sont anonymes par défaut ;
- leur position peut être arrondie/floutée par zone ;
- leur identité n'est révélée que s'ils l'autorisent ;
- un utilisateur opt-out n'apparaît jamais ;
- les utilisateurs ont des niveaux visuels, légendes, badges ou skins selon leur progression et leurs achats ;
- en cas d'urgence, Luna peut partager une position précise aux contacts de confiance.

Il y a donc deux couches :

1. **Carte communautaire consentie/anonyme**
   - présence Luna approximative ;
   - opt-in obligatoire ;
   - identité masquée par défaut ;
   - demande de révélation/contact soumise à accord ;
   - légende de niveau visible : nouveau, actif, avancé, premium, légende, etc. ;
   - skins/badges visuels issus de la gamification ou des achats.

2. **Carte Guardian urgence**
   - position précise ;
   - session Guardian ;
   - lien temporaire vers contacts de confiance ;
   - expiration propre.

L'objectif Guardian existant reste nécessaire :

- l'utilisateur lance une session Guardian ;
- son téléphone envoie une position GPS ;
- Luna stocke une position fraîche ;
- un contact de confiance peut ouvrir un lien temporaire ;
- le contact voit la position sur une carte ;
- le partage expire proprement.

## Objectif utilisateur

L'utilisateur doit pouvoir utiliser la carte de deux façons :

- **Mode communauté** : voir des présences Luna anonymes autour de lui, avec une différence visuelle de niveau/badge/skin, sans exposer les identités ni les positions exactes sans consentement.
- **Mode urgence/Guardian** : partager sa position précise avec ses contacts de confiance, sans donner accès à tout son compte Luna.

Le design économique est assumé : les niveaux, skins, badges, étoiles, streaks, forfaits ou achats peuvent rendre la présence plus valorisante sur la carte, afin d'inciter l'utilisateur à progresser et à consommer. Mais cette incitation ne doit jamais casser l'anonymat, exposer les revenus, ni humilier les petits forfaits.

L'objectif est atteint seulement si :

- un consentement opt-in contrôle l'apparition sur la carte communautaire ;
- l'identité et la position exacte sont masquées par défaut ;
- un autre utilisateur ne peut révéler/contacter quelqu'un qu'avec accord ;
- la couche communautaire peut lister des présences anonymes proches ;
- la légende de carte peut distinguer les niveaux/skins/badges de façon lisible ;
- les données gamification sont récupérables : XP, niveau, badges, étoiles, ancienneté/streak si disponible ;
- les données économiques visuelles sont contrôlées : forfait, skin acheté/débloqué, badge premium ;
- les skins/badges ne révèlent aucune donnée personnelle sensible ;
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
- une structure de consentement/présence communautaire existe, ou le check signale `warning` si la feature n'est pas encore codée ;
- la position communautaire est anonymisée/floutée et ne réutilise pas la position exacte Guardian ;
- un utilisateur opt-out ne peut pas apparaître ;
- une demande de contact/révélation nécessite un accord explicite ;
- `core.gamification.redis_ops.GamificationRedisOps` importable ;
- niveau/XP/badges/étoiles lisibles pour le tenant courant, ou fallback marqueur neutre ;
- une légende de carte existe côté config ou UI, ou le check signale `warning` ;
- les skins/forfaits ne sont exposés que sous forme visuelle non sensible ;
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
| community_opt_in | opt-in/opt-out pour apparaître sur la carte |
| anonymized_presence | position approximative, pas position exacte |
| nearby_users | listing de présences anonymes proches |
| reveal_request | demande de révélation/contact protégée par consentement |
| opt_out_privacy | utilisateur opt-out jamais visible |
| map_legend | légende niveaux/badges/skins disponible |
| gamification_bridge | XP, niveau, badges, étoiles lisibles |
| skins_badges | skins achetés/débloqués ou fallback neutre |
| monetization_visuals | forfait/premium traduit en avantage visuel non sensible |
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

1. La couche communautaire est soit disponible, soit clairement `warning` si non codée.
2. L'opt-in/opt-out est vérifiable.
3. La position communautaire n'expose pas la latitude/longitude exacte d'un utilisateur sans consentement.
4. La demande de révélation/contact passe par un garde consentement.
5. La légende de niveaux/badges/skins est disponible ou fallback neutre.
6. La gamification est lisible sans casser la carte si elle est indisponible.
7. Les informations économiques visibles ne révèlent pas une donnée financière sensible.
8. Les routes Guardian live existent.
9. Redis peut stocker une clé de partage avec TTL.
10. La page live sait interroger `/api/guardian/live-position/{token}`.
11. Une position trop ancienne déclenche un statut `warning/degraded`.
12. L'absence de session active n'est pas critique si l'infrastructure est complète.

## Statuts attendus

```text
ok
```

Carte communautaire consentie/anonyme disponible + légende niveaux/skins/badges disponible + Guardian live prêt. Si aucune session active existe, ce n'est pas une panne.

```text
warning
```

Carte communautaire pas encore activée mais Guardian live complet, gamification/skins indisponibles avec fallback neutre, aucune session active, aucune position récente, ou dépendance Leaflet CDN sans fallback local.

```text
degraded
```

Couche communautaire désactivée par sécurité, légende désactivée pour éviter une fuite, WebSocket indisponible mais polling HTTP possible, ou Leaflet indisponible mais fallback lien carte possible.

```text
critical
```

GuardianEngine, Redis, routes live, endpoint position ou protection anonymat/consentement indisponibles avec risque de fuite ou service inutilisable.

## Auto-heal attendu

| Problème | Auto-heal / réponse attendue |
|---|---|
| Token expiré pendant session active | régénérer un token |
| WebSocket KO | fallback polling HTTP |
| Leaflet/CDN KO | fallback lien Google Maps |
| GPS refusé | message clair + mode adresse/position manuelle si disponible |
| Position trop ancienne | afficher "dernière position connue" |
| Opt-in absent | masquer l'utilisateur de la carte communautaire |
| Anonymisation indisponible | désactiver la couche communautaire |
| Demande révélation sans consentement | bloquer et demander accord |
| Gamification indisponible | marqueur neutre |
| Skin invalide ou supprimé | skin par défaut |
| Forfait absent/inconnu | ne pas afficher de badge commercial |
| Redis KO | statut `critical`, pas de faux live |

## Limites à respecter

- Ne jamais envoyer de SMS réel pendant le monitoring.
- Ne jamais déclencher de SOS réel.
- Ne jamais créer une fausse session qui alerte quelqu'un.
- Ne pas exposer les contacts, documents, profil, historique ou identité complète via token public.
- Ne jamais exposer une identité ou une position exacte dans la carte communautaire sans consentement explicite.
- Ne jamais afficher un utilisateur opt-out.
- Ne jamais utiliser un skin, badge ou niveau pour rendre une personne identifiable dans une zone trop précise.
- Ne jamais afficher une information de paiement, revenu ou prix payé.
- Ne pas faire de pression agressive : la progression doit donner envie, pas rabaisser.
- Ne pas toucher à `static/index.html` dans ce chantier.

## Sortie souhaitée

Merci de produire :

1. Le code du check monitoring Cartes.
2. Les champs JSON retournés par `/api/admin/objectives`.
3. Les statuts `ok/warning/degraded/critical`.
4. Les auto-heal proposés.
5. Un résumé des fichiers modifiés.
6. Comment tester sans SMS, sans SOS réel, sans contact réel, et sans exposer une vraie position précise.
