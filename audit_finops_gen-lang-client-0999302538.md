# Rapport d'audit FinOps GCP — Projet `gen-lang-client-0999302538`

> **Mode :** LECTURE SEULE  
> **Date d'audit :** 2026-07-06  
> **Auditeur :** Agent FinOps via gcloud CLI  
> **Compte d'authentification :** `saintlouis.ludovic@gmail.com`  
> **Aucune ressource n'a été modifiée, redémarrée ou supprimée.**

---

## 1. Résumé exécutif

| Indicateur | Valeur |
|------------|--------|
| Projet audité | `gen-lang-client-0999302538` |
| Nom affiché | **Default Gemini Project** |
| Numéro de projet | `23790578045` |
| État | `ACTIVE` |
| Facturation activée | **Oui** |
| Compte de facturation | `billingAccounts/01C217-F83E98-3C12CF` (`Mon compte de facturation`) |
| Services/API activés | **3** seulement |
| Ressources déployées | **Quasi nulles** (0 bucket, 0 VM, 0 Cloud Run, 0 SQL, etc.) |
| Risque FinOps principal | Projet minimal créé pour Gemini ; coûts probablement très faibles, mais la facturation est active. |

**Constat principal :** ce projet est un projet "Default Gemini Project" créé automatiquement par Google. Il ne contient quasiment aucune ressource facturable classique (Compute, Cloud Run, Cloud SQL, Cloud Storage, etc.). Seules les API liées à Gemini / AI Companion et Telemetry sont activées. La facturation est active sur un compte de facturation ouvert.

---

## 2. Informations générales du projet

### Commandes utilisées

```bash
gcloud projects describe gen-lang-client-0999302538 --format="table(projectId, name, projectNumber, lifecycleState, createTime)"
gcloud billing projects describe gen-lang-client-0999302538 --format="table(billingAccountName, billingEnabled)"
gcloud billing accounts describe 01C217-F83E98-3C12CF --format="table(name, displayName, open)"
```

### Résultat

| Attribut | Valeur |
|----------|--------|
| `projectId` | `gen-lang-client-0999302538` |
| `name` | `Default Gemini Project` |
| `projectNumber` | `23790578045` |
| `lifecycleState` | `ACTIVE` |
| `createTime` | `2025-10-21T10:02:44.507439Z` |
| `billingEnabled` | `True` |
| `billingAccountName` | `billingAccounts/01C217-F83E98-3C12CF` |
| Nom du compte de facturation | `Mon compte de facturation` |
| Compte ouvert | `True` |

---

## 3. Services / APIs activés

### Commande utilisée

```bash
gcloud services list --enabled --project=gen-lang-client-0999302538 --format="value(NAME)" | sort
```

### Résultat

| API activée | Description indicative |
|-------------|------------------------|
| `cloudaicompanion.googleapis.com` | AI Companion (Gemini dans Cloud Console) |
| `generativelanguage.googleapis.com` | Gemini / Generative Language API |
| `telemetry.googleapis.com` | Télémétrie Google Cloud |

**Note :** contrairement à une première impression (obtenue sans `--project`), les API BigQuery, Storage, Cloud Logging, Monitoring, etc. **ne sont PAS activées** sur ce projet. La première commande sans `--project` ciblait implicitement un autre projet (`ceremonial-rush-405313`).

---

## 4. Cloud Run

### Commande utilisée

```bash
gcloud run services list --project=gen-lang-client-0999302538 --platform managed
```

### Résultat

| Service | Région | Statut | Mémoire | CPU | Image | Révisions |
|---------|--------|--------|---------|-----|-------|-----------|
| **N/A** | — | — | — | — | — | — |

**Statut :** ❌ **API non activée** (`run.googleapis.com` désactivée). Aucun service Cloud Run ne peut exister.  
**Message d'erreur :** `PERMISSION_DENIED: Cloud Run Admin API has not been used in project gen-lang-client-0999302538 before or it is disabled.`

---

## 5. Compute Engine

### Commandes utilisées

```bash
gcloud compute instances list --project=gen-lang-client-0999302538
gcloud compute disks list --project=gen-lang-client-0999302538
gcloud compute snapshots list --project=gen-lang-client-0999302538
gcloud compute addresses list --project=gen-lang-client-0999302538
gcloud compute networks list --project=gen-lang-client-0999302538
gcloud compute forwarding-rules list --project=gen-lang-client-0999302538
```

### Résultat

| Ressource | Nombre | Statut |
|-----------|--------|--------|
| VM (instances) | 0 | ❌ API `compute.googleapis.com` non activée |
| Disques persistants | 0 | ❌ API non activée |
| Snapshots | 0 | ❌ API non activée |
| Adresses IP | 0 | ❌ API non activée |
| Réseaux VPC | 0 | ❌ API non activée |
| Forwarding rules / Load balancers | 0 | ❌ API non activée |

**Coût estimé Compute Engine :** **0 €** (aucune ressource, API inactive).

---

## 6. Memorystore Redis

### Commande utilisée

```bash
gcloud redis instances list --project=gen-lang-client-0999302538 --region=us-central1
```

### Résultat

| Instance | Tier | Mémoire (Gb) | Région | Statut | Version |
|----------|------|--------------|--------|--------|---------|
| **N/A** | — | — | — | — | — |

**Statut :** ❌ **API non activée** (`redis.googleapis.com` désactivée).  
**Coût estimé :** **0 €**.

---

## 7. Cloud Storage

### Commandes utilisées

```bash
gcloud storage buckets list --project=gen-lang-client-0999302538 --format="table(name, location, storage_class, time_created)"
gcloud storage ls --project=gen-lang-client-0999302538
```

### Résultat

| Bucket | Localisation | Classe | Date de création |
|--------|--------------|--------|------------------|
| **Aucun** | — | — | — |

**Statut :** ✅ Commande exécutée avec succès, mais **aucun bucket** n'est présent dans le projet.  
`gcloud storage ls` retourne : `One or more URLs matched no objects.`  
**Coût estimé :** **0 €**.

---

## 8. Artifact Registry & Container Registry

### Commandes utilisées

```bash
gcloud artifacts repositories list --project=gen-lang-client-0999302538
gcloud container images list --repository=gcr.io/gen-lang-client-0999302538 --project=gen-lang-client-0999302538
```

### Résultat

| Repository / Image | Format | Localisation | Taille |
|--------------------|--------|--------------|--------|
| **N/A** | — | — | — |

**Statut :** ❌ **API `artifactregistry.googleapis.com` non activée**. Artifact Registry et Container Registry (qui dépend d'Artifact Registry) sont inaccessibles.  
**Coût estimé :** **0 €**.

---

## 9. Cloud SQL

### Commande utilisée

```bash
gcloud sql instances list --project=gen-lang-client-0999302538
```

### Résultat

| Instance | Version | Région | Tier | Statut | IP | Création |
|----------|---------|--------|------|--------|----|----------|
| **N/A** | — | — | — | — | — | — |

**Statut :** ❌ **API `sqladmin.googleapis.com` non activée**. Aucune instance Cloud SQL.  
**Coût estimé :** **0 €**.

---

## 10. Cloud Functions

### Commande utilisée

```bash
gcloud functions list --project=gen-lang-client-0999302538
```

### Résultat

| Fonction | Statut | Runtime | Déclencheur |
|----------|--------|---------|-------------|
| **N/A** | — | — | — |

**Statut :** ❌ **API `cloudfunctions.googleapis.com` non activée**. Aucune fonction.  
**Coût estimé :** **0 €**.

---

## 11. Cloud Build

### Commande utilisée

```bash
gcloud builds list --project=gen-lang-client-0999302538 --limit=50
```

### Résultat

| Build ID | Statut | Repo | Branche | Date | Durée |
|----------|--------|------|---------|------|-------|
| **N/A** | — | — | — | — | — |

**Statut :** ❌ **API `cloudbuild.googleapis.com` non activée**. Aucun build.  
**Coût estimé :** **0 €**.

---

## 12. Secret Manager

### Commande utilisée

```bash
gcloud secrets list --project=gen-lang-client-0999302538
```

### Résultat

| Secret | Date de création | Réplication |
|--------|------------------|-------------|
| **N/A** | — | — |

**Statut :** ❌ **API `secretmanager.googleapis.com` non activée**. Aucun secret.  
**Coût estimé :** **0 €**.

---

## 13. Cloud Scheduler

### Commandes utilisées

```bash
gcloud scheduler jobs list --project=gen-lang-client-0999302538 --location=us-central1
gcloud scheduler jobs list --project=gen-lang-client-0999302538 --location=europe-west1
```

### Résultat

| Job | Schedule | Timezone | Statut |
|-----|----------|----------|--------|
| **N/A** | — | — | — |

**Statut :** ❌ **API `cloudscheduler.googleapis.com` non activée**. Aucun job scheduler.  
**Coût estimé :** **0 €**.

---

## 14. Pub/Sub

### Commandes utilisées

```bash
gcloud pubsub topics list --project=gen-lang-client-0999302538
gcloud pubsub subscriptions list --project=gen-lang-client-0999302538
```

### Résultat

| Type | Nombre | Liste |
|------|--------|-------|
| Topics | 0 | (aucun) |
| Subscriptions | 0 | (aucun) |

**Statut :** ✅ API accessible / aucune erreur, mais **aucun topic ni subscription** n'existe.  
**Coût estimé :** **0 €**.

---

## 15. Logging — Sinks

### Commande utilisée

```bash
gcloud logging sinks list --project=gen-lang-client-0999302538
```

### Résultat

| Sink | Destination | Filtre | Writer Identity |
|------|-------------|--------|-----------------|
| **N/A** | — | — | — |

**Statut :** ❌ **API `logging.googleapis.com` non activée**. Aucun sink listable.  
**Coût estimé :** **0 €** (pas de logs ingérés visiblement).

---

## 16. Budgets du compte de facturation

### Commande utilisée

```bash
gcloud billing budgets list --billing-account=01C217-F83E98-3C12CF --format="table(displayName, amount.specifiedAmount.units, amount.specifiedAmount.currencyCode)"
```

### Résultat

| Nom du budget | Montant | Devise |
|---------------|---------|--------|
| `budget_limite` | 50 | EUR |
| `Limite YAWatch 50EUR` | 50 | EUR |

**Statut :** ✅ **2 budgets actifs** de 50 € chacun sur le compte de facturation.  
Ces budgets ne sont pas spécifiques au projet audité ; ils s'appliquent au compte de facturation global.

---

## 17. IAM & sécurité

### Commandes utilisées

```bash
gcloud projects get-iam-policy gen-lang-client-0999302538 --format=json
gcloud iam service-accounts list --project=gen-lang-client-0999302538
```

### Résultat

| Rôle | Membre |
|------|--------|
| `roles/owner` | `user:saintlouis.ludovic@gmail.com` |

| Comptes de service | Nombre |
|--------------------|--------|
| Service accounts explicites | **0** |

**Constat :** un seul utilisateur a les droits Owner. Aucun compte de service personnalisé. Le projet est donc sous contrôle direct du propriétaire.

---

## 18. Tentatives supplémentaires

| Ressource | Commande | Résultat |
|-----------|----------|----------|
| BigQuery datasets | `bq ls --project_id=gen-lang-client-0999302538` | ❌ API BigQuery non activée sur ce projet |
| Firestore databases | `gcloud firestore databases list --project=gen-lang-client-0999302538` | ❌ API Firestore non activée |
| Monitoring dashboards | `gcloud monitoring dashboards list --project=gen-lang-client-0999302538` | ❌ API Monitoring non activée |

---

## 19. Synthèse FinOps

### Ressources facturables détectées

| Catégorie | Ressources | Coût estimé mensuel |
|-----------|------------|---------------------|
| Compute Engine | 0 | 0 € |
| Cloud Run | 0 (API off) | 0 € |
| Cloud SQL | 0 (API off) | 0 € |
| Cloud Storage | 0 bucket | 0 € |
| Memorystore Redis | 0 (API off) | 0 € |
| Artifact Registry / GCR | 0 (API off) | 0 € |
| Cloud Functions | 0 (API off) | 0 € |
| Cloud Build | 0 (API off) | 0 € |
| Secret Manager | 0 (API off) | 0 € |
| Cloud Scheduler | 0 (API off) | 0 € |
| Pub/Sub | 0 topic / 0 sub | 0 € |
| Logging / Monitoring | API off / rien | 0 € |
| **TOTAL** | — | **≈ 0 €** |

### Recommandations

1. **Vérifier la facturation effective** : bien que le projet soit quasi vide, des appels à l'API Gemini (`generativelanguage.googleapis.com`) peuvent générer des coûts. Consulter la console de facturation pour le détail des charges sur `gen-lang-client-0999302538`.
2. **Surveiller les budgets** : 2 budgets de 50 € sont configurés au niveau du compte de facturation. S'assurer que les alertes par email sont actives.
3. **Supprimer le projet si inutile** : s'il n'est utilisé que comme projet par défaut Gemini et ne contient aucune ressource, envisager sa suppression pour éliminer tout risque futur.
4. **Restreindre les API activées** : seules 3 API sont activées, ce qui est déjà minimal. Ne pas activer d'API supplémentaires sans besoin.
5. **Vérifier les quotas** : aucun quota personnalisé n'a été audité ici. Pour un audit approfondi, vérifier `gcloud compute project-info describe --project=gen-lang-client-0999302538` une fois Compute API activée (si besoin).

---

## 20. Commandes utilisées (récapitulatif)

```bash
# Configuration
gcloud config set project gen-lang-client-0999302538
gcloud auth application-default set-quota-project gen-lang-client-0999302538

# Projet & facturation
gcloud projects describe gen-lang-client-0999302538
gcloud billing projects describe gen-lang-client-0999302538
gcloud billing accounts describe 01C217-F83E98-3C12CF

# Services
gcloud services list --enabled --project=gen-lang-client-0999302538

# Cloud Run
gcloud run services list --project=gen-lang-client-0999302538 --platform managed

# Compute Engine
gcloud compute instances list --project=gen-lang-client-0999302538
gcloud compute disks list --project=gen-lang-client-0999302538
gcloud compute snapshots list --project=gen-lang-client-0999302538
gcloud compute addresses list --project=gen-lang-client-0999302538
gcloud compute networks list --project=gen-lang-client-0999302538
gcloud compute forwarding-rules list --project=gen-lang-client-0999302538

# Memorystore Redis
gcloud redis instances list --project=gen-lang-client-0999302538 --region=us-central1

# Cloud Storage
gcloud storage buckets list --project=gen-lang-client-0999302538
gcloud storage ls --project=gen-lang-client-0999302538

# Registres
gcloud artifacts repositories list --project=gen-lang-client-0999302538
gcloud container images list --repository=gcr.io/gen-lang-client-0999302538 --project=gen-lang-client-0999302538

# Cloud SQL
gcloud sql instances list --project=gen-lang-client-0999302538

# Cloud Functions
gcloud functions list --project=gen-lang-client-0999302538

# Cloud Build
gcloud builds list --project=gen-lang-client-0999302538 --limit=50

# Secret Manager
gcloud secrets list --project=gen-lang-client-0999302538

# Cloud Scheduler
gcloud scheduler jobs list --project=gen-lang-client-0999302538 --location=us-central1
gcloud scheduler jobs list --project=gen-lang-client-0999302538 --location=europe-west1

# Pub/Sub
gcloud pubsub topics list --project=gen-lang-client-0999302538
gcloud pubsub subscriptions list --project=gen-lang-client-0999302538

# Logging
gcloud logging sinks list --project=gen-lang-client-0999302538

# Budgets
gcloud billing budgets list --billing-account=01C217-F83E98-3C12CF

# IAM
gcloud projects get-iam-policy gen-lang-client-0999302538
gcloud iam service-accounts list --project=gen-lang-client-0999302538
```

---

*Fin du rapport.*
