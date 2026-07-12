# PLAN D'OPTIMISATION — OBJECTIF 15 €/MOIS MAX

> Date : 2026-07-06  
> Projet : `crypto-parser-475411-k4`  
> Service concerné : `luna-beta`

---

## 1. ÉTAT ACTUEL MESURÉ

### luna-beta (Cloud Run)

| Paramètre | Valeur actuelle | Observation |
|-----------|-----------------|-------------|
| Mode de facturation CPU | **Always allocated** (`cpu-throttling=false`) | On paie 24/7 |
| vCPU | **2** | Surdimensionné : utilisation moyenne ~6,5 % |
| Mémoire | **1 Gi** | Utilisation p95 ~328–337 Mo : 512 Mi suffirait |
| Concurrence | 80 | Correct |
| Timeout | 3600 s | Nécessaire pour WebSocket/streaming |
| Min instances | **1** | Coûteux, oblige une instance allumée en permanence |
| Max instances | 3 | Correct |
| Autoscaling | min=1, max=3 | Réductible à min=0 |

### Trafic mesuré (30 derniers jours)

- **649 099 requêtes** sur 30 jours
- Moyenne : **~21 000 req/jour**
- Pic : 59 487 req/jour le 30/06/2026
- Latences (7 jours) :
  - p50 : ~71 ms
  - p95 : ~565 ms
  - p99 : ~974 ms

### Facturation Cloud Run actuelle estimée

- `billable_instance_time` moyen : **126 382 s/jour**
- Projection 30 jours : **3 791 470 s**
- Avec 2 vCPU + 1 Gi **always allocated** :
  - CPU : 3 791 470 × 2 × €0,000024 = **~€182**
  - Mémoire : 3 791 470 × 1 × €0,0000025 = **~€9,50**
  - Requêtes : 649k × €0,40/M = **~€0,26**
  - **Total Cloud Run : ~€192/mois**

### Stockage

| Ressource | Taille actuelle | Coût estimé/mois |
|-----------|-----------------|------------------|
| Artifact Registry `cloud-run-source-deploy` | 206,4 GiB | ~€20,60 |
| dont `luna-beta` | 200,9 GiB (657 images) | ~€20,10 |
| dont services supprimés | ~5,5 GiB | ~€0,55 |
| Bucket `run-sources-...` | 91,6 GiB | ~€1,80 |
| dont `luna-beta` | 71,9 GiB | ~€1,40 |
| dont autres services | 19,7 GiB | ~€0,40 |
| Bucket `crypto-parser-475411-k4_cloudbuild` | 15,4 GiB | ~€0,30 |
| Snapshots Compute | 52,5 GiB | ~€1,37 |
| Autres buckets | ~0,4 GiB | ~€0,01 |
| **Total stockage** | **~266 GiB** | **~€24/mois** |

### Coût total actuel estimé

| Poste | Coût/mois |
|-------|-----------|
| Cloud Run luna-beta | ~€192 |
| Artifact Registry | ~€20,60 |
| Cloud Storage | ~€2,50 |
| Snapshots | ~€1,37 |
| Logging (estimé) | €2–€10 |
| **TOTAL** | **~€218–€226/mois** |

---

## 2. PLAN D'ACTION POUR ATTEINDRE 15 €/MOIS

### Étape 1 — Optimiser Cloud Run luna-beta

| Changement | Pourquoi | Économie estimée |
|------------|----------|------------------|
| `minInstances=0` | Supprime le coût 24/7 de l'instance idle | ~€130–€180/mois |
| `cpu-throttling=true` (request-based) | Ne paie le CPU que pendant les requêtes | Complémentaire au min=0 |
| Réduire CPU de 2 à 1 | Utilisation moyenne de 6,5 % : 1 vCPU suffit largement | ~50 % du coût CPU |
| Réduire mémoire de 1 Gi à 512 Mi | p95 usage ~330 Mo : marge confortable | ~50 % du coût mémoire |

**Configuration cible :**
- CPU : 1
- Mémoire : 512Mi
- `minInstances=0`
- `maxInstances=3` (inchangé)
- `cpu-throttling=true` (par défaut si min=0)
- `concurrency=80` (inchangé)
- `timeout=3600` (inchangé)

**Coût Cloud Run estimé après optimisation :**
- Hypothèse : durée moyenne de traitement ~150 ms (p50=71 ms, p95=565 ms)
- Requêtes mensuelles : 649k
- Temps de traitement total : 649 000 × 0,15 = 97 350 s/mois
- CPU : 97 350 × 1 × €0,000024 = **€2,34**
- Mémoire : 97 350 × 0,5 × €0,0000025 = **€0,12**
- Requêtes : **€0,26**
- **Total Cloud Run : ~€2,72/mois**

**Risque :** cold starts plus fréquents. Acceptable selon ta consigne.

### Étape 2 — Nettoyer Artifact Registry

| Action | Pourquoi | Économie |
|--------|----------|----------|
| Supprimer images des services supprimés | Ils ne reviendront pas | ~€0,55/mois |
| Garder seulement les 10–20 dernières images `luna-beta` + `latest` | 657 images = 200,9 GiB, la plupart obsolètes | ~€18–€19/mois |
| Mettre en place une policy de cleanup automatique | Éviter la re-croissance | Économie future |

**Cible :** ~5–10 GiB d'images utiles → ~€0,50–€1/mois

**Risque :** perte de capacité de rollback vers d'anciennes versions. Mitigation : garder les 20 dernières versions + les versions tagguées `latest`.

### Étape 3 — Nettoyer Cloud Storage

| Action | Pourquoi | Économie |
|--------|----------|----------|
| Supprimer sources des services supprimés dans `run-sources-...` | 19,7 GiB inutiles | ~€0,40/mois |
| Garder seulement les 20 dernières sources `luna-beta` | 71,9 GiB, majoritairement obsolètes | ~€1,20/mois |
| Nettoyer anciens builds `crypto-parser-475411-k4_cloudbuild` | 15,4 GiB d'artefacts anciens | ~€0,25/mois |
| Lifecycle policy automatique | Éviter la re-croissance | Économie future |

**Cible :** ~5–10 GiB de stockage utile → ~€0,10–€0,20/mois

### Étape 4 — Gérer les snapshots (optionnel)

| Action | Pourquoi | Économie |
|--------|----------|----------|
| Supprimer ou archiver les 2 snapshots | Disques sources n'existent plus | ~€1,37/mois |

**Risque :** perte définitive des backups. À valider avec toi.

---

## 3. COÛT FINAL ESTIMÉ

| Poste | Coût/mois après optimisation |
|-------|------------------------------|
| Cloud Run luna-beta | ~€2,72 |
| Artifact Registry | ~€0,50–€1 |
| Cloud Storage | ~€0,20–€0,50 |
| Snapshots | ~€1,37 (ou €0 si supprimés) |
| Logging | €1–€5 |
| **TOTAL** | **~€6–€10/mois** |

**Objectif de 15 €/mois : ATTEIGNABLE** avec une marge de sécurité.

---

## 4. RISQUES ET MITIGATIONS

| Risque | Impact | Mitigation |
|--------|--------|------------|
| Cold starts avec `min=0` | Latence accrue sur premières requêtes | Accepté explicitement ; startup probe déjà à 240s |
| 1 vCPU insuffisant en pic | Requêtes plus lentes, possible timeout | Surveiller après changement ; on peut remonter à 2 vCPU |
| 512 Mi insuffisant | OOM kill | p95 usage = 330 Mo ; marge de 180 Mo |
| Suppression d'images/sources utiles | Perte de rollback | Garder 20 dernières versions + latest |
| Trafic supérieur aux prévisions | Dépassement 15 € | Surveillance mensuelle ; scaling max=3 protège |

---

## 5. MODIFICATIONS À APPLIQUER

Dans l'ordre :

1. **Modifier luna-beta** : 1 vCPU, 512 Mi, min=0.
2. **Nettoyer Artifact Registry** : supprimer images obsolètes.
3. **Nettoyer Cloud Storage** : supprimer sources/builds obsolètes.
4. **Configurer lifecycle policies** et cleanup automatique.
5. **Vérifier** le service reste fonctionnel.

*Aucune modification n'a encore été appliquée à ce stade.*
