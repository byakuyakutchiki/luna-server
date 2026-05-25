# Règles de coordination entre agents

## Interdictions absolues

- Ne pas supprimer brutalement une fonctionnalité existante.
- Ne pas faire de refactor massif sans validation de Ludovic.
- Ne pas déployer en production sans accord de Ludovic.
- Ne pas écraser les fichiers d'avis d'un autre agent.
- Ne pas considérer GitHub comme preuve que la production est à jour.
- Ne pas déclencher d'action réelle dans les checks de monitoring (pas de SMS, appel, email, paiement, réservation réels).
- Ne pas exposer la position exacte d'un utilisateur sans consentement explicite.
- Ne pas révéler quelle IA fait quoi dans l'interface utilisateur final.

## Obligations avant toute modification importante

1. Lire `ETAT_ACTUEL.md` — comprendre l'état réel avant de toucher quoi que ce soit.
2. Identifier les fichiers touchés et leur impact.
3. Lister les risques de régression (Redis, Auth, Stripe, APK, WebView, dashboards).
4. Proposer une solution progressive (un objectif à la fois).
5. Prévoir un rollback possible.
6. Attendre validation de Ludovic si impact production.

## Niveaux de déploiement — à distinguer toujours

1. **Code modifié localement** — sur la machine de développement
2. **Code commité GitHub** — dans le repo `byakuyakutchiki/luna-server`
3. **Code mergé sur `main`** — PR acceptée et mergée
4. **Image Docker buildée** — Cloud Build terminé
5. **Image déployée Google Cloud Run** — service `luna-beta` actif
6. **APK réelle testée** — testée sur le téléphone de Ludovic

GitHub commité ≠ production. Production = Cloud Run réellement à jour + APK installée.

## Règles de commit / PR

- Chaque commit = un seul objectif clair (pas de gros commits fourre-tout).
- Message de commit : `feat:`, `fix:`, `docs:`, `chore:` selon le type.
- PR obligatoire pour toute modification de `luna_web.py` ou `index.html`.
- PR template : `.github/pull_request_template.md` à remplir complètement.

## Règle de déploiement Cloud Run

Toujours lancer `deploy.sh` depuis `/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/` (jamais depuis un sous-répertoire).

```bash
cd /home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur
bash deploy.sh
```

Après déploiement, vérifier :
- `GET /api/admin/health` → 200 OK
- `GET /api/admin/objectives` → tous les objectifs présents
- Logs Cloud Run → pas d'erreurs 500
- Redis connecté

## Décision finale

Claude peut synthétiser les avis et proposer l'implémentation finale.
La validation finale appartient toujours à Ludovic.
