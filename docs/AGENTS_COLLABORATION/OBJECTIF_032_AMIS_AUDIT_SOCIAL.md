# Objectif 032 — Audit onglet Amis / Social

## Contexte

Ludovic demande un audit de l'onglet **Amis** : ce qui fonctionne, ce qui ne fonctionne pas, ce qui manque, et les risques avant de laisser des utilisateurs ou des exploitants s'en servir.

Lien terrain : https://luna-beta-674304336025.europe-west1.run.app/

Chemin utilisateur : connexion -> onglet `Amis`.

Chemins code principaux :

- `static/index.html` : bouton `data-tab="amis"`, panneau `#tab-amis`, fonctions `loadAmis`, `loadAmisList`, `loadAmisRequests`, DM modal
- `luna_web.py` : routes `/api/social/*`, WebSocket `/ws/dm/{room_id}`, monitoring `_check_objective_amis`
- `core/social/routes.py` : router social principal inclus dans FastAPI
- `core/social/redis_ops.py` : stockage Redis social, codes amis, demandes, amis, DM, blocage, amis externes

## Target

L'onglet Amis doit permettre une relation sociale consentie, lisible et sûre :

```text
profil -> code ami -> demande -> acceptation/refus -> liste amis -> presence -> DM -> suppression/blocage -> amis externes
```

L'utilisateur doit toujours comprendre :

- qui peut le contacter ;
- si une demande a vraiment été envoyée ;
- si un ami est en ligne ou non ;
- si un message est envoyé en temps réel ou en fallback ;
- si une suppression efface les messages ;
- quelles données personnelles sont stockées ;
- comment bloquer/signaler une personne.

## Interdictions audit

- Ne pas créer de vrais comptes utilisateurs sans validation.
- Ne pas envoyer de DM réel à un tiers.
- Ne pas inviter par SMS.
- Ne pas supprimer de vraie relation sociale.
- Ne pas modifier Redis/base de données en production sans validation.
- Ne pas déployer sans validation Ludovic.

## Validation attendue

L'objectif est validé uniquement si l'équipe peut produire :

1. carte complète des boutons et routes ;
2. statut par fonctionnalité : atteint, partiel, non visible, à risque ;
3. preuves de garde-fous : auth, mineurs, blocage, rate-limit, suppression RGPD ;
4. liste des corrections P0/P1 ;
5. tests non destructifs à faire sur téléphone et navigateur.

