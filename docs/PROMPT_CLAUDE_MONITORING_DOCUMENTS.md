# Prompt Claude — Monitoring Objectif Documents / Vault IA

Contexte : Claude travaille peut-être déjà sur `Services / Concierge`. Ne touche pas à son chantier. Ce document prépare l'objectif suivant : **Documents / Vault IA**.

Repo :

https://github.com/byakuyakutchiki/luna-server

Source de vérité :

- `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Section `## 6. Documents — Vault IA`
- Méthode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`

## Objectif utilisateur

L'utilisateur doit pouvoir scanner, classer, retrouver et exploiter ses documents importants sans perdre le contrôle de ses données.

L'objectif est atteint seulement si :

- le consentement RGPD est vérifiable ;
- un document peut être scanné après consentement ;
- Luna extrait des métadonnées utiles ;
- le document est classé ;
- il est visible dans le dashboard ;
- les rappels d'expiration sont détectables ;
- les données extraites peuvent alimenter le profil/formulaire quand c'est autorisé ;
- la suppression et la révocation du consentement fonctionnent.

## Surfaces code à lire

- `core/vault/routes.py`
- `core/vault/redis_ops.py`
- `core/vault/classifier.py`
- `core/documents/actions_engine.py`
- `static/documents.html`
- `luna_web.py`

Routes importantes :

- `GET /api/vault/consent`
- `POST /api/vault/consent`
- `DELETE /api/vault/consent`
- `POST /api/vault/scan`
- `GET /api/vault/docs`
- `GET /api/vault/doc/{doc_id}`
- `DELETE /api/vault/doc/{doc_id}`
- `GET /api/vault/reminders`
- `GET /api/vault/types`
- `GET /api/vault/profile-data`
- `POST /api/vault/apply-to-profile`
- `GET /api/documents/v2/dashboard`
- `GET /api/documents/v2/timeline`
- `GET /api/documents/v2/categories`
- `GET /api/documents/v2/actions/{doc_id}`
- `POST /api/documents/v2/actions/execute`

## Monitoring attendu

Quand `/api/admin/objectives` sera prêt à recevoir ce bloc, ajouter :

```json
{
  "documents": {
    "status": "warning",
    "goal": "L'utilisateur scanne, classe, retrouve et exploite ses documents importants avec consentement RGPD.",
    "checks": [],
    "subservices": {},
    "metrics": {},
    "auto_heal": []
  }
}
```

## Checks globaux

Vérifier sans déclencher de scan réel :

- module `core.vault` importable ;
- router Vault monté ;
- Redis disponible ;
- `VaultRedisOps` importable ;
- `classify_document` importable ;
- `DOC_TYPES` non vide ;
- routes documents v2 présentes ;
- `core.documents.actions_engine` importable ;
- client IA disponible pour scan (`openai_client`) ;
- dashboard `static/documents.html` présent ;
- aucun crash si consentement absent.

## Sous-services

### Consentement RGPD

Objectif : aucun scan sans consentement.

Checks :

- `GET /api/vault/consent` répond ;
- `has_consent()` lisible ;
- si consentement absent, status `warning`, pas `critical` ;
- `DELETE /api/vault/consent` doit supprimer documents + consentement.

Statuts :

- `ok` : consentement lisible ;
- `warning` : consentement absent ;
- `critical` : consentement impossible à lire ou révocation cassée.

### Scan / OCR / classification

Objectif : transformer une image/PDF en document classé avec métadonnées.

Checks :

- `POST /api/vault/scan` existe ;
- `classify_document` existe ;
- `DOC_TYPES` contient les catégories attendues ;
- limite taille image en place ;
- refus propre si image absente ;
- refus propre si IA indisponible.

Ne pas lancer de vrai scan dans le monitoring.

Statuts :

- `ok` : pipeline disponible ;
- `degraded` : IA absente ou modèle indisponible ;
- `critical` : scan route/module cassé.

### Index Redis / liste documents

Objectif : les documents scannés sont retrouvables.

Checks :

- `list_docs()` fonctionne ;
- `get_doc()` fonctionne ;
- index par type disponible ;
- TTL document connu ;
- erreurs Redis capturées proprement.

Statuts :

- `ok` : lecture possible ;
- `warning` : 0 document ;
- `critical` : lecture Redis impossible.

### Dashboard documents v2

Objectif : l'utilisateur voit ses documents et les actions prioritaires.

Checks :

- `/api/documents/v2/dashboard` présent ;
- `/api/documents/v2/timeline` présent ;
- `/api/documents/v2/categories` présent ;
- `static/documents.html` appelle les bons endpoints ;
- dashboard vide affiche un état propre.

Statuts :

- `ok` : routes + page présentes ;
- `degraded` : routes présentes mais actions engine absent ;
- `critical` : dashboard impossible à charger.

### Rappels d'expiration

Objectif : Luna repère les documents expirés ou proches expiration.

Checks :

- `get_upcoming_reminders()` disponible ;
- `get_due_reminders()` disponible ;
- `expires_in_days` et `expiry_status` calculables ;
- rappel créé lors de `save_doc()` si métadonnées contiennent `reminders`.

Statuts :

- `ok` : rappels lisibles ;
- `warning` : aucun rappel/document ;
- `degraded` : dates présentes mais rappels absents ;
- `critical` : lecture rappels cassée.

### Profil unifié / pont formulaires

Objectif : les données extraites du Vault peuvent aider à remplir les formulaires.

Checks :

- `/api/vault/profile-data` présent ;
- `get_profile_data()` disponible ;
- `completeness` calculée ;
- sources tracées par catégorie ;
- `/api/vault/apply-to-profile` existe ;
- seuls les documents éligibles alimentent le profil.

Statuts :

- `ok` : pont disponible ;
- `warning` : profil vide ;
- `degraded` : données extraites mais pas applicables ;
- `critical` : pont cassé.

### Suppression / droit à l'effacement

Objectif : l'utilisateur peut supprimer un document ou tout révoquer.

Checks :

- `DELETE /api/vault/doc/{doc_id}` présent ;
- `delete_doc()` supprime aussi les rappels ;
- `revoke_consent()` supprime tout ;
- images non stockées, seulement métadonnées.

Statuts :

- `ok` : suppression disponible ;
- `critical` : suppression impossible ou révocation incomplète.

## Exemple JSON attendu

```json
{
  "status": "warning",
  "goal": "L'utilisateur scanne, classe, retrouve et exploite ses documents importants avec consentement RGPD.",
  "checks": [
    {"name": "vault_module_importable", "status": "ok"},
    {"name": "vault_routes_available", "status": "ok"},
    {"name": "redis_available", "status": "ok"},
    {"name": "doc_types_available", "status": "ok"},
    {"name": "documents_v2_dashboard_available", "status": "ok"}
  ],
  "subservices": {
    "consent": {"status": "warning", "critical": true, "message": "Consentement absent mais lisible"},
    "scan_classification": {"status": "ok", "critical": true},
    "document_index": {"status": "warning", "critical": true, "metrics": {"documents": 0}},
    "dashboard_v2": {"status": "ok", "critical": false},
    "reminders": {"status": "warning", "critical": false, "metrics": {"upcoming": 0}},
    "profile_bridge": {"status": "warning", "critical": false, "metrics": {"completeness": 0}},
    "deletion_rgpd": {"status": "ok", "critical": true}
  },
  "metrics": {
    "documents_count": 0,
    "doc_types_count": 0,
    "upcoming_reminders": 0,
    "expired_documents": 0,
    "urgent_documents": 0,
    "profile_completeness": null
  },
  "auto_heal": [
    {"condition": "unknown_doc_type", "action": "reclassify_with_ai", "available": true},
    {"condition": "empty_ocr_result", "action": "retry_scan_or_request_better_photo", "available": true},
    {"condition": "missing_reminders_for_expiring_doc", "action": "rebuild_reminders_from_metadata", "available": true}
  ]
}
```

## Auto-heal à prévoir

Sans action destructive automatique :

- document `unknown` → proposer reclassement IA ;
- OCR vide → demander nouvelle photo ou relance contrôlée ;
- document expirant sans rappel → reconstruire rappel depuis `date_expiration` ;
- index type manquant → reconstruire `vault:docs_by_type:*` depuis `vault:docs` ;
- dashboard v2 KO mais Vault OK → fallback vers `/api/vault/docs`.

## Contraintes fortes

- Ne jamais scanner un vrai document pendant un check de monitoring.
- Ne jamais afficher de données sensibles dans les logs admin.
- Ne jamais stocker l'image brute du document.
- Ne pas traiter l'absence de consentement comme un bug critique : c'est un état utilisateur normal.
- Ne pas casser `Services / Concierge` si Claude travaille dessus.
- Ne pas modifier `luna_web.py` tant que le chantier Services n'est pas stabilisé, sauf demande explicite.

## Procédure de test manuelle

1. Vérifier `/api/admin/objectives` après ajout du bloc documents.
2. Vérifier que `objectives.documents.status` existe.
3. Avec un utilisateur sans consentement, vérifier que le statut est `warning`.
4. Donner le consentement via `/api/vault/consent`.
5. Vérifier que le statut consentement passe `ok`.
6. Scanner un document de test non sensible.
7. Vérifier `/api/vault/docs`.
8. Vérifier `/api/documents/v2/dashboard`.
9. Vérifier qu'une suppression retire document + rappels.
10. Révoquer le consentement et vérifier que les documents sont supprimés.
