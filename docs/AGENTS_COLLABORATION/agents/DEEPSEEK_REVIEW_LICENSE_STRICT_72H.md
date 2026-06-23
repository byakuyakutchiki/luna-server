# DeepSeek — Demande d'avis : grâce 72h + strict mode licence

**Demandeur :** Ludovic via Claude (lead technique)
**Date :** 2026-06-23
**Repo concerné :** `byakuyakutchiki/luna-exploitants` (package exploitant — boîte noire)
**Statut :** 🟡 Avis DeepSeek demandé
**Livrable attendu :** réponse en fin de ce fichier (ou `..._LIVRABLE.md`)

---

## Contexte

Suite à l'incohérence relevée par Claude (doc annonce « 72h de grâce » mais le code
appliquait 24h), et au trou de sécurité « pas de clé → heartbeat désactivé → instance
libre », Claude a appliqué un correctif ciblé. **Avis DeepSeek demandé avant fusion.**

> ⚠️ Le script initial (sed `s/24/72/g` global, retrait celery, ajout weasyprint) a été
> **écarté** : il aurait corrompu les fichiers (`24` matche `2024`, `1024`, ports…) et
> visait du code inexistant (aucun Celery, aucun weasyprint, PDF déjà synchrone via PyMuPDF).
> Seules les 2 intentions réelles ont été appliquées proprement.

## Liens de référence

- Commit : https://github.com/byakuyakutchiki/luna-exploitants/commit/996dc46
- Branche : https://github.com/byakuyakutchiki/luna-exploitants/tree/chore/remove-tavus
- Fichiers : `TEMPLATE/serveur/security/config.py`,
  `TEMPLATE/serveur/security/antipiracy/heartbeat.py`

## Changement appliqué (commit `996dc46`)

1. **`config.py`** — `antipiracy_heartbeat_grace_hours` : `24 → 72` (défaut + fallback
   env `ANTIPIRACY_HEARTBEAT_GRACE_HOURS`). Aligne enfin le code sur la doc exploitant.
2. **`config.py`** — nouveau flag `antipiracy_strict_license: bool = True`
   (échappatoire `ANTIPIRACY_STRICT_LICENSE=false`).
3. **`heartbeat.py`** — en strict mode, si `YAWATCH_LICENSE_SERVER`/`KEY` absent :
   `is_valid = False` + alerte CRITICAL, au lieu de désactiver le heartbeat et laisser
   l'instance tourner librement.

## Questions précises pour DeepSeek

1. **Re-test après coup** : en strict mode, `run_loop` fait `is_valid=False` puis `return`
   (sort de la boucle). Si la clé arrive après le boot, pas de re-tentative (redémarrage
   requis). Acceptable, ou préférer une boucle qui re-teste périodiquement ?
2. **Défaut `strict=True`** : risque de bloquer une instance légitime mal configurée au
   premier déploiement. Faut-il un délai de grâce au boot avant de marquer invalide ?
3. **Cohérence kill-switch** : côté serveur fondateur (`luna-server`), le middleware
   `luna_web.py:4696-4722` bloque sur `is_blocked()`/`is_degraded()`. Le template
   exploitant expose-t-il bien `is_valid=False` à un enforcement équivalent ? (à vérifier
   dans le wiring du template).
4. **Doublon possible** : la branche `fix/deepseek-and-workers` contient déjà
   `fix(security): durcir les workers de sécurité`. Y a-t-il chevauchement / conflit avec
   ce correctif licence ? Recommander l'ordre de fusion vers `master`.

## Règles

- Audit en lecture seule. Pas de déploiement. Pas de modif de secrets.
- Réponse attendue : avis Go/No-Go fusion + réponses aux 4 questions + reco ordre de merge.

---

*Brief Claude — 2026-06-23. Toute suite passe par Claude avant fusion, et Ludo avant prod.*
