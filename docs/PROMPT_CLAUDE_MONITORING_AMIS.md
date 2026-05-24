# Prompt Claude — Monitoring Objectif Amis / Réseau Social

Contexte : Services, Documents, Formulaires et Cartes ont déjà un premier monitoring riche dans `/api/admin/objectives`. Ne les refais pas sauf bug explicite.

Repo :

https://github.com/byakuyakutchiki/luna-server

Source de vérité :

- `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Section `## 11. Amis — Réseau Social`
- Méthode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`

## Vision produit

Amis est le pont social entre les utilisateurs Luna.

L'utilisateur doit pouvoir :

- avoir un profil social propre ;
- partager un code ami ;
- recevoir/envoyer une invitation ;
- accepter ou refuser ;
- voir sa liste d'amis ;
- voir si un ami est en ligne ;
- discuter en message privé ;
- bloquer ou supprimer quelqu'un ;
- rester protégé par ses réglages de confidentialité ;
- garder la cohérence avec la carte communautaire : révélation/contact seulement avec accord.

L'objectif n'est pas atteint si seul le code ami existe. Il faut vérifier la chaîne sociale complète.

## Objectif utilisateur

L'objectif est atteint si un utilisateur peut créer une relation sociale consentie et sûre dans Luna :

```text
profil social → code ami → invitation → accept/refuse → liste amis → présence → DM → blocage/suppression → privacy carte
```

## Checks techniques suggérés

Ajouter ou compléter un check `_check_objective_amis()` dans `luna_web.py`, puis l'exposer dans `GET /api/admin/objectives` sous la clé :

```json
{
  "amis": {
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

- `core.social.routes` importable ;
- `core.social.redis_ops.SocialRedisOps` importable ;
- Redis accessible ;
- routes social présentes :
  - profil social ;
  - code ami ;
  - ajout ami par code ;
  - invitations reçues/envoyées ;
  - acceptation/refus ;
  - liste amis ;
  - suppression ami ;
  - blocage/déblocage ;
  - DM room ;
  - messages DM ;
  - présence/heartbeat si disponible ;
- friend code existant ou régénérable ;
- liste amis lisible ;
- invitations lisibles ;
- DM rooms/messages lisibles ;
- limites anti-abus présentes : max amis, max bloqués, pas de self-add, pas de doublon ;
- cohérence avec `core.world` si le profil/carte utilise aussi WorldRedisOps.

## Sous-services attendus

| Sous-service | Ce qui doit être vérifié |
|---|---|
| social_module | routes + ops importables |
| profile | display name, avatar, level, friend code |
| friend_code | unique, lisible, régénérable |
| add_by_code | validation code + pas de self-add |
| invitations | sent/received, accept/refuse |
| friends_list | liste amis lisible |
| presence | online/heartbeat lisible ou fallback |
| dm_rooms | room entre amis accessible |
| dm_messages | envoi/lecture messages |
| blocking | blocage/déblocage/suppression |
| anti_abuse | limites amis/bloqués/invitations |
| privacy_world_bridge | cohérence avec carte/World consentement |

## Checks fonctionnels suggérés

Ne pas envoyer de vrai message à un utilisateur réel pendant le monitoring.

Le monitoring peut rester structurel, mais il doit prouver :

1. Redis et SocialRedisOps sont disponibles.
2. Le profil social du tenant courant est lisible.
3. Le friend code existe ou peut être généré.
4. Les listes amis/invitations sont accessibles.
5. Les méthodes accept/refuse/remove/block existent.
6. Le système empêche les doublons, self-add et contacts bloqués.
7. Les DM ne sont autorisés qu'entre amis.
8. La présence online ne casse pas si heartbeat absent.
9. La carte/World ne peut pas révéler un profil social sans consentement.

## Statuts attendus

```text
ok
```

Profil social, code ami, invitations, amis, DM, présence, blocage et privacy disponibles.

```text
warning
```

Aucun ami ou aucune invitation, profil incomplet, présence vide, mais système utilisable.

```text
degraded
```

DM temps réel indisponible mais fallback possible, ou pont World/Carte partiellement absent.

```text
critical
```

Redis, SocialRedisOps, friend code, liste amis, blocage ou DM indisponibles.

## Auto-heal attendu

| Problème | Auto-heal / réponse attendue |
|---|---|
| friend_code absent | régénérer au démarrage |
| invitation doublon | dédupliquer |
| utilisateur bloqué | refuser contact/DM |
| présence stale | marquer offline |
| DM temps réel KO | fallback polling |
| profil incomplet | fallback nom/avatar neutre |
| Redis KO | statut `critical`, pas de faux état social |

## Limites à respecter

- Ne jamais envoyer de DM réel pendant le monitoring.
- Ne jamais permettre un DM si la relation ami n'est pas établie.
- Ne jamais contourner un blocage.
- Ne jamais révéler une identité depuis la carte sans consentement.
- Ne pas toucher à `static/index.html` dans ce chantier.

## Sortie souhaitée

Merci de produire :

1. Le code du check monitoring Amis.
2. Les champs JSON retournés par `/api/admin/objectives`.
3. Les statuts `ok/warning/degraded/critical`.
4. Les auto-heal proposés.
5. Un résumé des fichiers modifiés.
6. Comment tester sans envoyer de vrai message à un utilisateur réel.

