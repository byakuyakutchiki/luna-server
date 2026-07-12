# Rapport d'audit FinOps GCP — Projet `crypto-parser-475411-k4`

> **Mode : LECTURE SEULE** — Aucune ressource n'a été créée, modifiée, redémarrée ou supprimée durant cet audit.  
> **Date de l'audit :** 2026-07-06  
> **Compte d'exécution :** `saintlouis.ludovic@gmail.com` (Owner du projet)  
> **Outil :** `gcloud` CLI (version 548.0.0)

---

## 1. Résumé exécutif

| Indicateur | Valeur |
|------------|--------|
| Projet | `crypto-parser-475411-k4` (My First Project) |
| Numéro de projet | `674304336025` |
| Facturation | Activée — `billingAccounts/01C217-F83E98-3C12CF` |
| Région principale | `europe-west1` |
| Services Cloud Run actifs | **8 / 10** (2 services en erreur) |
| Stockage GCS | **~107 GiB** répartis sur 9 buckets |
| Artifact Registry | **~211 GiB** répartis sur 5 repositories |
| Snapshots Compute | **2 snapshots = 56,4 GiB** de données historiques |
| Fonctions Cloud | **2** (dont 1 orpheline — service Cloud Run manquant) |
| Secrets exposés | **7** dans Secret Manager + secrets en variables d'environnement |

**Principaux risques FinOps & sécurité :**
- `luna-beta` possède **986 générations / révisions** accumulées, ce qui alourdit Artifact Registry et le stockage source Cloud Run.
- Deux services Cloud Run sont en échec (`dayslegacy-ai`, `luna-staging`) : ils ne servent pas de trafic mais consomment du stockage d'images et de logs.
- Des clés API, tokens et mots de passe sont exposés en **variables d'environnement non chiffrées** dans les services Cloud Run.
- Le bucket `run-sources-crypto-parser-475411-k4-europe-west1` représente **91,64 GiB** de sources déployées — à nettoyer.
- Le bucket `crypto-parser-475411-k4_cloudbuild` contient **15,39 GiB** d'artefacts de build anciens.

---

## 2. Identité du projet

| Champ | Valeur |
|-------|--------|
| Project ID | `crypto-parser-475411-k4` |
| Nom | `My First Project` |
| Project Number | `674304336025` |
| État | `ACTIVE` |
| Créé le | `2025-10-17T11:41:50Z` |
| Facturation activée | `True` |
| Compte de facturation | `billingAccounts/01C217-F83E98-3C12CF` ("Mon compte de facturation") |

**Commandes utilisées :**
```bash
gcloud config set project crypto-parser-475411-k4
gcloud projects describe crypto-parser-475411-k4
gcloud billing projects describe crypto-parser-475411-k4
gcloud billing accounts list
```

---

## 3. Services/APIs activés

| API | Description |
|-----|-------------|
| `bigquery.googleapis.com` | BigQuery API |
| `bigquerymigration.googleapis.com` | BigQuery Migration API |
| `bigquerystorage.googleapis.com` | BigQuery Storage API |
| `cloudapis.googleapis.com` | Google Cloud APIs |
| `cloudtrace.googleapis.com` | Cloud Trace API |
| `datastore.googleapis.com` | Cloud Datastore API |
| `drive.googleapis.com` | Google Drive API |
| `logging.googleapis.com` | Cloud Logging API |
| `monitoring.googleapis.com` | Cloud Monitoring API |
| `servicemanagement.googleapis.com` | Service Management API |
| `serviceusage.googleapis.com` | Service Usage API |
| `sheets.googleapis.com` | Google Sheets API |
| `sql-component.googleapis.com` | Cloud SQL |
| `storage-api.googleapis.com` | Google Cloud Storage JSON API |
| `storage-component.googleapis.com` | Cloud Storage |
| `storage.googleapis.com` | Cloud Storage API |
| `telemetry.googleapis.com` | Telemetry API |

**APIs NON activées (observées lors des tentatives) :**
- `run.googleapis.com` (Cloud Run Admin API) — *semble avoir été activée implicitement car les services sont listables*
- `compute.googleapis.com` (Compute Engine API)
- `artifactregistry.googleapis.com` (Artifact Registry API) — *semble activée implicitement*
- `sqladmin.googleapis.com` (Cloud SQL Admin API)
- `cloudfunctions.googleapis.com` (Cloud Functions API) — *semble activée implicitement*
- `cloudbuild.googleapis.com` (Cloud Build API) — *semble activée implicitement*
- `secretmanager.googleapis.com` (Secret Manager API) — *semble activée implicitement*
- `redis.googleapis.com` (Memorystore for Redis API)
- `cloudscheduler.googleapis.com` (Cloud Scheduler API)
- `billingbudgets.googleapis.com` (Cloud Billing Budget API) — *a fonctionné pour lister les budgets*

**Commande utilisée :**
```bash
gcloud services list --enabled --sort-by='config.name'
```

---

## 4. Cloud Run

### 4.1 Services Cloud Run

| Service | Région | Statut | CPU | Mémoire | Min | Max | Timeout | Ingress | Concurrency | Image principale |
|---------|--------|--------|-----|---------|-----|-----|---------|---------|-------------|------------------|
| `ambre-coach` | europe-west1 | ✅ True | 1 | 512Mi | 0 | 3 | 300s | all | 80 | `ambre-coach@sha256:4c236eff...` |
| `dayslegacy-ai` | europe-west1 | ❌ False | 1000m | 512Mi | 0 | 20 | 300s | all | 80 | `dayslegacy-ai:latest` |
| `dayslegacy-ai-os` | europe-west1 | ✅ True | 1 | 512Mi | 0 | 1 | 300s | all | 80 | `dayslegacy-app` |
| `dayslegacy-app` | europe-west1 | ✅ True | 1 | 512Mi | 0 | 20 | 300s | all | 80 | `dayslegacy-app:latest` |
| `dayslegacy-workspace-demo` | europe-west1 | ✅ True | 1000m | 512Mi | 0 | 20 | 300s | all | 80 | `dayslegacy-workspace-demo@sha256:2111915d...` |
| `equipement-t2` | europe-west1 | ✅ True | 0.1666 | 256M | 1 | 1 | 30s | all | 1 | `crypto--parser--...__equipement--t2:version_1` |
| `luna-beta` | europe-west1 | ✅ True | 2 | 1Gi | 1 | 3 | 3600s | all | 80 | `luna-beta@sha256:96b799c4...` |
| `luna-staging` | europe-west1 | ❌ False | 1000m | 512Mi | 0 | 20 | 300s | all | 80 | `luna-beta:20260629-014055` |
| `luna-warroom` | europe-west1 | ✅ True | 1 | 512Mi | 0 | 3 | 120s | all | 80 | `luna-warroom@sha256:17f1b401...` |
| `yawatch-video-engine` | europe-west1 | ✅ True | 1 | 1Gi | 0 | *(non défini)* | 600s | all | 80 | `yawatch-video-engine@sha256:41f7eb60...` |

### 4.2 Générations et révisions par service

| Service | Génération | Dernière révision prête | Dernier modificateur | Nb révisions visibles (échantillon) | Traffic split |
|---------|------------|-------------------------|----------------------|-------------------------------------|---------------|
| `ambre-coach` | 18 | `ambre-coach-00018-kf8` | saintlouis.ludovic@gmail.com | 18 | 1 |
| `dayslegacy-ai` | 2 | *(aucune ready)* | saintlouis.ludovic@gmail.com | 2 (toutes en échec) | 0 |
| `dayslegacy-ai-os` | 10 | `dayslegacy-ai-os-00010-6z6` | saintlouis.ludovic@gmail.com | 10 | 1 |
| `dayslegacy-app` | 2 | `dayslegacy-app-00002-bmd` | saintlouis.ludovic@gmail.com | 2 | 1 |
| `dayslegacy-workspace-demo` | 11 | `dayslegacy-workspace-demo-00011-g5k` | saintlouis.ludovic@gmail.com | 11 | 1 |
| `equipement-t2` | 13 | `equipement-t2-00013-wiz` | gcf-admin-robot | 13 | 1 |
| `luna-beta` | **986** | `luna-beta-00986-kil` | saintlouis.ludovic@gmail.com | 30+ | 7 |
| `luna-staging` | 4 | *(aucune ready)* | saintlouis.ludovic@gmail.com | 4 (1 en échec) | 0 |
| `luna-warroom` | 9 | `luna-warroom-00009-774` | saintlouis.ludovic@gmail.com | 9 | 1 |
| `yawatch-video-engine` | 1 | `yawatch-video-engine-00001-xgr` | saintlouis.ludovic@gmail.com | 1 | 1 |

### 4.3 Services en erreur

- **`dayslegacy-ai`** : `HealthCheckContainerError` — le conteneur n'écoute pas sur le port `8080` dans le délai imparti.
- **`luna-staging`** : `HealthCheckContainerError` — même cause probable.

### 4.4 Estimation coût Cloud Run (idle, instances minimales)

| Service | Min instances | Mémoire | CPU | Coût estimé mensuel (idle) |
|---------|---------------|---------|-----|----------------------------|
| `ambre-coach` | 0 | 512Mi | 1 | ~€0,00 |
| `dayslegacy-ai` | 0 | 512Mi | 1 | ~€0,00 |
| `dayslegacy-ai-os` | 0 | 512Mi | 1 | ~€0,00 |
| `dayslegacy-app` | 0 | 512Mi | 1 | ~€0,00 |
| `dayslegacy-workspace-demo` | 0 | 512Mi | 1 | ~€0,00 |
| `equipement-t2` | 1 | 256M | 0,1666 | ~€175,58 |
| `luna-beta` | 1 | 1Gi | 2 | ~€788,80 |
| `luna-staging` | 0 | 512Mi | 1 | ~€0,00 |
| `luna-warroom` | 0 | 512Mi | 1 | ~€0,00 |
| `yawatch-video-engine` | 0 | 1Gi | 1 | ~€0,00 |

**Total estimé (idle uniquement) : ~€964/mois** hors trafic, stockage d'images, logs, Artifact Registry et GCS.

**Commandes utilisées :**
```bash
gcloud run services list --format='json'
gcloud run revisions list --service=<service> --region=europe-west1 --format='table(metadata.name, metadata.creationTimestamp, status.conditions[0].status, status.conditions[0].reason)'
```

---

## 5. Compute Engine

### 5.1 Instances VM

**Résultat :** Aucune instance VM en cours d'exécution.

```
Commande : gcloud compute instances list
Sortie   : (vide)
```

### 5.2 Disques persistants

**Résultat :** Aucun disque persistant actif.

```
Commande : gcloud compute disks list
Sortie   : (vide)
```

### 5.3 Snapshots

| Nom | Disque source | Taille disque | Taille stockée | Statut | Date de création | Localisation |
|-----|---------------|---------------|----------------|--------|------------------|--------------|
| `iawatch-production-backup-20260226` | `europe-west1-b/disks/iawatch-production` | 50 Go | **5,66 Go** | READY | 2026-02-26 | europe-west1 |
| `luna-avatar-backup-20260226` | `europe-west1-b/disks/luna-avatar` | 150 Go | **52,51 Go** | READY | 2026-02-26 | europe-west1 |

**Coût estimé snapshots :** ~52,5 Go × ~€0,026/Go/mois = **~€1,37/mois** (règle de prix GCS Snapshot standard).

### 5.4 Adresses IP

**Résultat :** Aucune adresse IP réservée.

```
Commande : gcloud compute addresses list
Sortie   : (vide)
```

### 5.5 Réseaux VPC

| Nom | Mode de sous-réseaux | Nb de sous-réseaux | Date de création |
|-----|----------------------|--------------------|------------------|
| `default` | AUTO | 42 | 2025-10-17 |

### 5.6 Load balancers / Forwarding rules / Proxies

**Résultat :** Aucun forwarding rule, target HTTP proxy, URL map ni backend service.

```
Commandes : gcloud compute forwarding-rules list
            gcloud compute target-http-proxies list
            gcloud compute url-maps list
            gcloud compute backend-services list
Sortie     : (vide pour toutes)
```

**Commandes utilisées :**
```bash
gcloud compute instances list
gcloud compute disks list
gcloud compute snapshots list
gcloud compute addresses list
gcloud compute networks list
gcloud compute forwarding-rules list
gcloud compute target-http-proxies list
gcloud compute url-maps list
gcloud compute backend-services list
```

---

## 6. Memorystore Redis

**Résultat :** API Redis désactivée — aucune instance listable.

```
Commande : gcloud redis instances list --region=europe-west1
Erreur   : PERMISSION_DENIED — Google Cloud Memorystore for Redis API not enabled
```

> Néanmoins, les services Cloud Run `dayslegacy-workspace-demo` et `luna-beta` référencent une variable `REDIS_URL`. Redis est probablement hébergé ailleurs (Redis Labs, Upstash, ou une autre région/projet).

**Commandes utilisées :**
```bash
gcloud redis instances list --region=europe-west1
gcloud redis instances list --region=us-central1  # etc.
```

---

## 7. Cloud Storage (GCS)

### 7.1 Buckets

| Nom | Localisation | Type | Classe | Création | Versioning | Taille estimée | ULA | Remarque |
|-----|--------------|------|--------|----------|------------|----------------|-----|----------|
| `crypto-parser-475411-k4_cloudbuild` | US | multi-region | STANDARD | 2025-11-28 | ❌ | **15,39 GiB** | ❌ | Artefacts Cloud Build |
| `gcf-v2-sources-674304336025-europe-west1` | EUROPE-WEST1 | region | STANDARD | 2026-02-25 | ✅ | 2,67 KiB | ✅ | Sources Cloud Functions |
| `gcf-v2-uploads-674304336025.europe-west1.cloudfunctions.appspot.com` | EUROPE-WEST1 | region | STANDARD | 2026-02-25 | ❌ | 0 B | ✅ | Uploads Cloud Functions |
| `iawatch-assets` | EUROPE-WEST1 | region | STANDARD | 2025-12-21 | ❌ | **379,83 MiB** | ✅ | Assets IA_WATCH |
| `ludo-equipement-t2` | EUROPE-WEST1 | region | STANDARD | 2026-03-31 | ❌ | 49,06 KiB | ❌ | Assets équipement-t2 |
| `luna-karaoke-drafts-674304336025` | EUROPE-WEST1 | region | STANDARD | 2026-06-24 | ❌ | 0 B | ✅ | Karaoke drafts |
| `luna-vault-originals-674304336025` | EUROPE-WEST1 | region | STANDARD | 2026-06-26 | ❌ | 211,87 KiB | ✅ | **Public access enforced** |
| `luna-warroom-data-prod` | EUROPE-WEST1 | region | STANDARD | 2026-06-26 | ❌ | 0 B | ✅ | Warroom data |
| `run-sources-crypto-parser-475411-k4-europe-west1` | EUROPE-WEST1 | region | STANDARD | 2026-06-26 | ❌ | **91,64 GiB** | ✅ | Sources Cloud Run deploy |

**Taille totale estimée : ~107 GiB**

### 7.2 Coût estimé GCS

- Volume moyen : ~107 GiB Standard en `europe-west1` + US multi-region.
- Prix indicatif : ~€0,020/Go/mois (Standard régional).
- **Estimation : ~€2,20–2,50/mois** (hors opérations et sorties de données).

**Commandes utilisées :**
```bash
gcloud storage buckets list --format='json'
gsutil du -sh gs://<bucket>
```

---

## 8. Artifact Registry

### 8.1 Repositories

| Repository | Format | Localisation | Description | Taille | Scan vulnérabilités |
|------------|--------|--------------|-------------|--------|---------------------|
| `cloud-run-source-deploy` | DOCKER | europe-west1 | Cloud Run Source Deployments | **169,1 GiB** | Désactivé |
| `gcf-artifacts` | DOCKER | europe-west1 | Cloud Functions images | **62,5 MiB** | Désactivé |
| `iawatch` | DOCKER | europe-west1 | IA_WATCH Docker images | **1,3 GiB** | Désactivé |
| `luna` | DOCKER | europe-west1 | Luna Beta images | **12,9 GiB** | Désactivé |
| `gcr.io` | DOCKER | us | Container Registry legacy | **14,6 GiB** | Désactivé |

**Taille totale Artifact Registry : ~197,9 GiB** (~212 Go)

### 8.2 Images notables dans Artifact Registry

- `cloud-run-source-deploy/ambre-coach` : 18+ versions
- `cloud-run-source-deploy/luna-beta` : plusieurs centaines de versions
- `cloud-run-source-deploy/dayslegacy-ai-os` : 4 versions
- `cloud-run-source-deploy/dayslegacy-workspace-demo` : 6 versions
- `luna/luna-beta` : 30+ versions
- `luna/luna-sentinel` : 6 versions
- `iawatch/luna-server` : 4 versions taguées (v42 à v45)
- `gcf-artifacts/.../equipement-t2` : 13 versions + cache
- `gcf-artifacts/.../stop-vms-on-budget` : 1 version + cache

**Coût estimé Artifact Registry :**
- ~197,9 GiB × ~€0,10/Go/mois (prix indicatif AR) = **~€19,80/mois**.

**Commandes utilisées :**
```bash
gcloud artifacts repositories list --format='json'
gcloud artifacts docker images list europe-west1-docker.pkg.dev/crypto-parser-475411-k4/<repo> --include-tags
```

---

## 9. Container Registry (legacy)

### 9.1 Images GCR

| Image | Tags visibles | Dernier push |
|-------|---------------|--------------|
| `gcr.io/crypto-parser-475411-k4/dayslegacy-ai` | `latest` + 1 untagged | 2026-06-12 |
| `gcr.io/crypto-parser-475411-k4/dayslegacy-ai-os` | `latest` | 2026-06-10 |
| `gcr.io/crypto-parser-475411-k4/dayslegacy-app` | `latest` + 4 untagged | 2026-06-12 |
| `gcr.io/crypto-parser-475411-k4/iawatch-backend` | *(vide)* | — |
| `gcr.io/crypto-parser-475411-k4/luna-beta` | `latest`, `trace-v1..v5`, `working-dir`, `p3`, `p3b`, `p3c`, etc. | 2026-07-04 |
| `gcr.io/crypto-parser-475411-k4/luna-server` | `days-legacy-demo-v2..v4` | 2026-06-12 |

**Remarque :** GCR est en mode legacy. Le repository `gcr.io` dans Artifact Registry (localisation `us`) fait office de backend.

**Commandes utilisées :**
```bash
gcloud container images list --repository=gcr.io/crypto-parser-475411-k4
gcloud container images list-tags gcr.io/crypto-parser-475411-k4/<image>
```

---

## 10. Cloud SQL

**Résultat :** API Cloud SQL Admin désactivée.

```
Commande : gcloud sql instances list
Erreur   : PERMISSION_DENIED — Cloud SQL Admin API not enabled
```

> Certains services Cloud Run utilisent des variables `DATABASE_URL` pointant vers des fichiers SQLite locaux (`sqlite:///./dayslegacy.db`, `sqlite:///./dayslegacy_qa.db`). Aucune base Cloud SQL n'est visible.

**Commande utilisée :**
```bash
gcloud sql instances list
```

---

## 11. Cloud Functions

| Nom | Région | Runtime | Entry point | Trigger | Mémoire/CPU | Min/Max | Statut | Problème |
|-----|--------|---------|-------------|---------|-------------|---------|--------|----------|
| `equipement-t2` | europe-west1 | python312 | `equipement` | HTTP | 256M / 0,1666 | 1 / 1 | ACTIVE | — |
| `stop-vms-on-budget` | europe-west1 | python311 | `stop_vms_on_budget` | Pub/Sub `budget-alerts` | — | — | UNKNOWN | **Cloud Run service introuvable** |

### 11.1 Fonction orpheline

`stop-vms-on-budget` référence un service Cloud Run manquant. Elle est déclenchée par le topic `budget-alerts` mais ne pourra pas exécuter son code.

**Commandes utilisées :**
```bash
gcloud functions list --format='json'
```

---

## 12. Cloud Build

### 12.1 Builds récents (50 derniers)

| Métrique | Valeur |
|----------|--------|
| Nombre de builds listés | 50 |
| Statut global | 45 SUCCESS, 5 FAILURE |
| Dernier build | 2026-06-12T15:07:51Z (SUCCESS) |
| Plus ancien de l'échantillon | 2026-05-17T18:51:55Z |
| Nb d'étapes par build | 1 (tous) |

### 12.2 Builds en échec dans l'échantillon

| ID | Date | Statut |
|----|------|--------|
| `2c8aa985-7278-4bfb-b4ad-cc13cae39416` | 2026-05-20 | FAILURE |
| `78a69c92-38d6-4f1c-ac60-96c1d61da456` | 2026-05-18 | FAILURE |
| `f9def935-53c3-4d74-8ac6-fbf3d9ce009d` | 2026-05-18 | FAILURE |
| `0ea77f60-f5e9-405b-baea-a91c2f86e057` | 2026-05-18 | FAILURE |
| `5f34b882-f70f-4a88-83d1-bbc540231bec` | 2026-05-15 | FAILURE |

**Commandes utilisées :**
```bash
gcloud builds list --limit=50
```

---

## 13. Secret Manager

### 13.1 Secrets

| Nom | Créé le | Réplication |
|-----|---------|-------------|
| `anthropic-api-key` | 2025-12-05 | automatique |
| `google-api-key` | 2025-12-05 | automatique |
| `groq-api-key` | 2025-12-05 | automatique |
| `jwt-secret-key` | 2025-12-05 | automatique |
| `openai-api-key` | 2025-12-05 | automatique |
| `twilio-api-key-secret` | 2025-12-08 | automatique |
| `twilio-api-key-sid` | 2025-12-08 | automatique |

### 13.2 Secrets exposés en variables d'environnement

Plusieurs services Cloud Run exposent des secrets en clair dans `env` :
- Clés API OpenAI (`sk-proj-...`)
- Clés API Anthropic (`sk-ant-api03-...`)
- Tokens Twilio (Account SID, Auth Token, API Secret)
- Mots de passe administrateurs (`LunaAdmin2026!`, `DL-QA-2026!Secure#Beta`, etc.)
- JWT secrets, TOTP secrets, tokens Telegram, API keys Tavus/Simli/ElevenLabs/Duffel/MeetingBaaS

**Recommandation :** migrer ces valeurs vers Secret Manager et les monter en `secretKeyRef`.

**Commandes utilisées :**
```bash
gcloud secrets list
```

---

## 14. Cloud Scheduler

**Résultat :** API Cloud Scheduler désactivée.

```
Commande : gcloud scheduler jobs list --location=europe-west1
Erreur   : PERMISSION_DENIED — Cloud Scheduler API not enabled
```

**Commandes utilisées :**
```bash
gcloud scheduler jobs list --location=europe-west1
```

---

## 15. Pub/Sub

### 15.1 Topics

**Résultat :** Aucun topic personnalisé listé via `gcloud pubsub topics list`.

> Néanmoins, la fonction `stop-vms-on-budget` référence le topic `budget-alerts`, qui existe probablement mais n'est pas visible avec les permissions actuelles ou est masqué.

### 15.2 Subscriptions

**Résultat :** Aucune subscription listée.

**Commandes utilisées :**
```bash
gcloud pubsub topics list
gcloud pubsub subscriptions list
```

---

## 16. Logging

### 16.1 Logging sinks

| Nom | Destination | Filtre | Version |
|-----|-------------|--------|---------|
| `_Required` | `logging.googleapis.com/projects/crypto-parser-475411-k4/locations/global/buckets/_Required` | Logs d'audit obligatoires | V2 |
| `_Default` | `logging.googleapis.com/projects/crypto-parser-475411-k4/locations/global/buckets/_Default` | Tous les logs sauf audit | V2 |

### 16.2 Logging buckets

| Nom | Localisation | État | Rétention |
|-----|--------------|------|-----------|
| `_Default` | global | ACTIVE | 30 jours |
| `_Required` | global | ACTIVE | 400 jours |

**Coût estimé logs :** dépend du volume ingéré. Avec 986 générations de `luna-beta`, les logs peuvent être volumineux.

**Commandes utilisées :**
```bash
gcloud logging sinks list
gcloud logging buckets list
```

---

## 17. Budgets du compte de facturation

| Nom | Montant | Période | Seuils d'alerte | Notification |
|-----|---------|---------|-----------------|--------------|
| `budget_limite` | **50 EUR** | Mensuel | 50 %, 90 %, 100 % | *(non configuré)* |
| `Limite YAWatch 50EUR` | **50 EUR** | Mensuel | 50 %, 80 %, 100 % | Pub/Sub `budget-alerts` |

**Observations :**
- Deux budgets à 50 EUR chacun.
- Le budget `Limite YAWatch 50EUR` publie sur `budget-alerts` pour déclencher `stop-vms-on-budget`, mais cette fonction est orpheline.

**Commandes utilisées :**
```bash
gcloud billing budgets list --billing-account=01C217-F83E98-3C12CF
```

---

## 18. IAM et comptes de service

### 18.1 Rôles principaux

| Membre | Rôle | Remarque |
|--------|------|----------|
| `user:saintlouis.ludovic@gmail.com` | `roles/owner` | Propriétaire du projet |
| `serviceAccount:cursor-luna-deployer@crypto-parser-475411-k4.iam.gserviceaccount.com` | `roles/artifactregistry.writer`, `roles/cloudbuild.builds.editor`, `roles/logging.viewer`, `roles/run.developer`, `roles/storage.objectAdmin` | Compte de déploiement Cursor/Luna |
| `serviceAccount:674304336025-compute@developer.gserviceaccount.com` | `roles/compute.instanceAdmin.v1`, `roles/editor` | Compte de service Compute par défaut (risque : over-privileged) |
| `serviceAccount:674304336025@cloudservices.gserviceaccount.com` | `roles/editor` | Compte de service Google Cloud |
| `serviceAccount:crypto-parser-475411-k4@appspot.gserviceaccount.com` | `roles/editor` | Compte App Engine par défaut |
| `serviceAccount:674304336025@cloudbuild.gserviceaccount.com` | `roles/artifactregistry.writer`, `roles/cloudbuild.builds.builder` | Compte Cloud Build |
| `serviceAccount:luna-sentinel-invoker@crypto-parser-475411-k4.iam.gserviceaccount.com` | `roles/run.invoker` | Invoker Luna Sentinel |
| `serviceAccount:ocr-vehicules@crypto-parser-475411-k4.iam.gserviceaccount.com` | `roles/visionai.serviceAgent` | Vision AI |

### 18.2 Points d'attention IAM

- Le compte par défaut `674304336025-compute@developer.gserviceaccount.com` est utilisé par la plupart des services Cloud Run et possède le rôle `roles/editor` — principe du moindre privilège non appliqué.
- Le compte `cursor-luna-deployer` a des droits de build/déploiement étendus.

**Commande utilisée :**
```bash
gcloud projects get-iam-policy crypto-parser-475411-k4 --format='json'
```

---

## 19. Estimation globale des coûts mensuels

| Ressource | Coût estimé mensuel |
|-----------|---------------------|
| Cloud Run (instances minimales : `luna-beta` + `equipement-t2`) | **~€964** |
| Artifact Registry (~198 GiB) | **~€20** |
| Cloud Storage (~107 GiB Standard) | **~€2,50** |
| Snapshots Compute (~52,5 GiB) | **~€1,40** |
| Cloud Logging (estimation conservative) | **€5–50** |
| Cloud Build (hors stockage) | inclus dans stockage GCS/AR |
| Cloud Functions (Gen 2, min=1 pour `equipement-t2`) | déjà intégré dans Cloud Run |
| **Total estimé** | **~€1 000–1 040/mois** |

> Cette estimation ne prend pas en compte le trafic réel, les sorties de données, les appels API externes (OpenAI, Twilio, etc.) ni les coûts tiers.

---

## 20. Recommandations FinOps & sécurité

### 20.1 Optimisation des coûts

1. **Nettoyer Artifact Registry**
   - `luna-beta` a généré ~986 builds : mettre en place une politique de suppression des images de plus de N jours (sauf `latest` et tags protégés).
   - Supprimer les images des services supprimés ou en échec permanent.

2. **Nettoyer GCS**
   - Vider ou configurer un lifecycle policy sur `crypto-parser-475411-k4_cloudbuild` (15,39 GiB).
   - Configurer un lifecycle policy sur `run-sources-crypto-parser-475411-k4-europe-west1` (91,64 GiB) pour supprimer les sources de builds anciens.

3. **Cloud Run**
   - Supprimer les services en échec `dayslegacy-ai` et `luna-staging` s'ils ne sont plus utiles.
   - Réduire `luna-beta` à `minInstances=0` en environnements non critiques, ou utiliser `minInstances=1` seulement en production.
   - Définir `maxScale` sur `yawatch-video-engine` (actuellement non défini).

4. **Snapshots**
   - Évaluer si les snapshots de VM supprimées (`iawatch-production`, `luna-avatar`) doivent être conservés. Archiver vers GCS Coldline/Archive si nécessaire.

### 20.2 Sécurité

1. **Secrets en variables d'environnement**
   - Migrer toutes les clés API, tokens et mots de passe vers Secret Manager.
   - Utiliser `secretKeyRef` dans les manifests Cloud Run.

2. **IAM**
   - Créer des comptes de service dédiés par service.
   - Retirer le rôle `roles/editor` du compte Compute par défaut.
   - Appliquer le principe du moindre privilège.

3. **Budgets**
   - Configurer des notifications email sur `budget_limite`.
   - Corriger ou supprimer la fonction `stop-vms-on-budget` orpheline.

4. **Network**
   - Restreindre `run.googleapis.com/ingress` à `internal-and-cloud-load-balancing` pour les services ne devant pas être publics.

---

## 21. Commandes complètes utilisées

```bash
# Configuration
gcloud config set project crypto-parser-475411-k4

# Projet & facturation
gcloud projects describe crypto-parser-475411-k4
gcloud billing projects describe crypto-parser-475411-k4
gcloud billing accounts list

# APIs
gcloud services list --enabled --sort-by='config.name'

# Cloud Run
gcloud run services list --format='json'
gcloud run revisions list --service=<service> --region=europe-west1

# Compute Engine
gcloud compute instances list
gcloud compute disks list
gcloud compute snapshots list
gcloud compute addresses list
gcloud compute networks list
gcloud compute forwarding-rules list
gcloud compute target-http-proxies list
gcloud compute url-maps list
gcloud compute backend-services list

# Memorystore Redis
gcloud redis instances list --region=europe-west1

# Cloud Storage
gcloud storage buckets list --format='json'
gsutil du -sh gs://<bucket>

# Artifact Registry
gcloud artifacts repositories list --format='json'
gcloud artifacts docker images list europe-west1-docker.pkg.dev/crypto-parser-475411-k4/<repo> --include-tags

# Container Registry
gcloud container images list --repository=gcr.io/crypto-parser-475411-k4
gcloud container images list-tags gcr.io/crypto-parser-475411-k4/<image>

# Cloud SQL
gcloud sql instances list

# Cloud Functions
gcloud functions list --format='json'

# Cloud Build
gcloud builds list --limit=50

# Secret Manager
gcloud secrets list

# Cloud Scheduler
gcloud scheduler jobs list --location=europe-west1

# Pub/Sub
gcloud pubsub topics list
gcloud pubsub subscriptions list

# Logging
gcloud logging sinks list
gcloud logging buckets list

# Budgets
gcloud billing budgets list --billing-account=01C217-F83E98-3C12CF

# IAM
gcloud projects get-iam-policy crypto-parser-475411-k4 --format='json'
```

---

*Fin du rapport.*
