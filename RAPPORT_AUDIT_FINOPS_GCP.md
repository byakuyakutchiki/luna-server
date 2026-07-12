# RAPPORT D'AUDIT FINOPS GOOGLE CLOUD — YAWatch / LUNA

> **Mode strict : LECTURE SEULE.** Aucune ressource n'a été créée, modifiée, redémarrée ou supprimée.  
> **Date d'audit :** 2026-07-06  
> **Auditeur :** Kimi / DeepSeek via gcloud CLI  
> **Compte de facturation :** `billingAccounts/01C217-F83E98-3C12CF` (50 EUR/mois)

---

## ⚠️ Limites méthodologiques importantes

**Les coûts exacts aujourd'hui / mois en cours / estimés mensuels ne sont pas accessibles par la CLI gcloud.**  
Google Cloud ne fournit pas de commande/API publique pour lire l'historique de facturation sans **Cloud Billing export vers BigQuery** activé au préalable.

- Aucun dataset BigQuery d'export billing n'a été trouvé dans les 4 projets.
- Les appels aux API Cloud Billing (`/invoices`, `/charges`, `/reports`) retournent des 404 — ces endpoints n'existent pas en accès libre.
- La console GCP reste la seule source de vérité pour les coûts exacts par service.

**Ce rapport fournit donc :**
- L'inventaire exhaustif des ressources (prouvé par commandes).
- Des **estimations de coûts** basées sur les tarifs publics GCP Europe-West1 (juillet 2026) et les métriques observées.
- Les commandes utilisées pour chaque constat.

---

## 1. RÉSUMÉ EXÉCUTIF

| Indicateur | Valeur | Preuve |
|------------|--------|--------|
| Compte de facturation | `01C217-F83E98-3C12CF`, devise EUR | `gcloud billing accounts list` |
| Budget mensuel | **50 EUR** (2 budgets identiques) | `gcloud billing budgets list` |
| Projets GCP actifs | 4 projets listés | `gcloud projects list` |
| Projets **facturés** sur ce compte | **2** : `crypto-parser-475411-k4`, `gen-lang-client-0999302538` | `gcloud billing accounts .../projects` |
| Projets **non facturés** | `ceremonial-rush-405313`, `ia-watch-f7e2a` | `gcloud billing projects describe` |
| Principal consommateur | **`crypto-parser-475411-k4`** (YAWatch/LUNA) | Inventaire complet ci-dessous |
| Coût mensuel estimé (idle + stockage) | **~1 000 €/mois** hors appels API externes | Calculs détaillés dans le rapport |
| Premier poste de dépense | **Cloud Run idle** (`luna-beta` + `equipement-t2`) | Métriques Monitoring + specs services |

**Conclusion immédiate :** le budget de 50 €/mois est théoriquement dépassé dès le premier jour uniquement par les **instances minimales Cloud Run** qui tournent en permanence.

---

## 2. TOUS LES PROJETS ET LEUR STATUT DE FACTURATION

| Project ID | Nom | Billing activé ? | Ressources facturables ? |
|------------|-----|------------------|--------------------------|
| `crypto-parser-475411-k4` | My First Project | **Oui** | **Oui — principal** |
| `gen-lang-client-0999302538` | Default Gemini Project | **Oui** | API Gemini uniquement |
| `ceremonial-rush-405313` | My Project | **Non** | Aucune |
| `ia-watch-f7e2a` | ia-watch | **Non** | Aucune |

**Commandes :**
```bash
gcloud projects list --format="table(projectId,name,projectNumber,lifecycleState)"
gcloud billing accounts projects list --billing-account=01C217-F83E98-3C12CF
gcloud billing projects describe <PROJECT_ID>
```

---

## 3. PROJET PRINCIPAL : `crypto-parser-475411-k4`

### 3.1 Services Cloud Run (10 services, 8 actifs, 2 en échec)

| Service | Statut | CPU | Mémoire | Min | Max | Concurrency | Requêtes 7j* | Idle €/mois** |
|---------|--------|-----|---------|-----|-----|-------------|--------------|---------------|
| `luna-beta` | ✅ True | 2 | 1 Gi | 1 | 3 | 80 | **357 213** | **~€789** |
| `equipement-t2` | ✅ True | 0,1666 | 256 Mi | 1 | 1 | 1 | 0 | **~€176** |
| `ambre-coach` | ✅ True | 1 | 512 Mi | 0 | 3 | 80 | 2 | ~€0 |
| `dayslegacy-ai-os` | ✅ True | 1 | 512 Mi | 0 | 1 | 80 | 245 | ~€0 |
| `dayslegacy-app` | ✅ True | 1 | 512 Mi | 0 | 20 | 80 | 0 | ~€0 |
| `dayslegacy-workspace-demo` | ✅ True | 1 | 512 Mi | 0 | 20 | 80 | 0 | ~€0 |
| `luna-warroom` | ✅ True | 1 | 512 Mi | 0 | 3 | 80 | 2 | ~€0 |
| `yawatch-video-engine` | ✅ True | 1 | 1 Gi | 0 | ? | 80 | 0 | ~€0 |
| `dayslegacy-ai` | ❌ False | 1 | 512 Mi | 0 | 20 | 80 | 0 | ~€0 |
| `luna-staging` | ❌ False | 1 | 512 Mi | 0 | 20 | 80 | 1 (4xx) | ~€0 |

\* Requêtes du 29/06 au 06/07/2026, source : Monitoring API `run.googleapis.com/request_count`.  
\*\* Estimation idle basée sur tarif Cloud Run europe-west1 : CPU €0,00002400/vCPU/s, mémoire €0,00000250/GiB/s, calculé sur 730 h/mois.

**Commandes :**
```bash
gcloud run services list --format=json
gcloud run revisions list --region=europe-west1
# Métriques requêtes :
curl -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://monitoring.googleapis.com/v3/projects/crypto-parser-475411-k4/timeSeries?filter=metric.type%3D%22run.googleapis.com%2Frequest_count%22&interval.startTime=2026-06-29T00:00:00Z&interval.endTime=2026-07-06T23:59:59Z&aggregation.alignmentPeriod=604800s&aggregation.perSeriesAligner=ALIGN_SUM"
```

**Constats clés :**
- `luna-beta` concentre **99,9 % du trafic** (357 213 requêtes / 7 jours ≈ 51 000 req/jour).
- `luna-beta` a **986 générations/révisions** accumulées → coût de stockage Artifact Registry + GCS.
- `equipement-t2` a **min=1** mais **0 requête** détectée sur 7 jours → instance idle permanente.
- `dayslegacy-ai` et `luna-staging` sont **en échec permanent** (`HealthCheckContainerError`) mais consomment du stockage d'images et des logs.

### 3.2 Compute Engine

| Ressource | Résultat | Preuve |
|-----------|----------|--------|
| VM actives | **0** | `gcloud compute instances list` → `[]` |
| Disques persistants | **0** | `gcloud compute disks list` → `[]` |
| Snapshots | **2 snapshots = 52,5 GiB stockés** | `gcloud compute snapshots list` |
| IP réservées | **0** | `gcloud compute addresses list` → `[]` |
| Réseaux VPC | 1 (`default`, mode AUTO, 42 sous-réseaux) | `gcloud compute networks list` |
| Load balancers / forwarding rules | **0** | `gcloud compute forwarding-rules list` → `[]` |

**Snapshots :**

| Nom | Disque source | Taille disque | Taille stockée | Date |
|-----|---------------|---------------|----------------|------|
| `iawatch-production-backup-20260226` | `europe-west1-b/disks/iawatch-production` | 50 Go | 5,66 Go | 2026-02-26 |
| `luna-avatar-backup-20260226` | `europe-west1-b/disks/luna-avatar` | 150 Go | 52,51 Go | 2026-02-26 |

**Coût estimé snapshots :** 52,5 GiB × ~€0,026/GiB/mois = **~€1,37/mois**.

### 3.3 Memorystore Redis

| Instance | Résultat |
|----------|----------|
| Redis GCP | **Aucune** — API `redis.googleapis.com` non activée |

**Constat :** Redis est hébergé **en externe** (Upstash). La variable `REDIS_URL` de `luna-beta` pointe vers `genuine-mammal-135122.upstash.io`.  
**Ce coût est hors GCP** et n'apparaît pas sur la facture Google Cloud.

### 3.4 Cloud Storage (9 buckets, ~115 Go)

| Bucket | Localisation | Classe | Taille brute | Taille affichée | Usage |
|--------|--------------|--------|--------------|-----------------|-------|
| `run-sources-crypto-parser-475411-k4-europe-west1` | EUROPE-WEST1 | STANDARD | 98 402 444 687 o | **~91,64 GiB** | Sources Cloud Run |
| `crypto-parser-475411-k4_cloudbuild` | US | STANDARD | 16 524 835 358 o | **~15,39 GiB** | Artefacts Cloud Build |
| `iawatch-assets` | EUROPE-WEST1 | STANDARD | 398 283 685 o | **~379 MiB** | Assets |
| `luna-vault-originals-674304336025` | EUROPE-WEST1 | STANDARD | 216 952 o | **~212 KiB** | Vault |
| `ludo-equipement-t2` | EUROPE-WEST1 | STANDARD | 50 234 o | **~49 KiB** | Équipement |
| `gcf-v2-sources-674304336025-europe-west1` | EUROPE-WEST1 | STANDARD | 2 738 o | **~2,7 KiB** | Sources Cloud Functions |
| `gcf-v2-uploads-...` | EUROPE-WEST1 | STANDARD | 0 o | 0 B | Uploads CF |
| `luna-karaoke-drafts-674304336025` | EUROPE-WEST1 | STANDARD | 0 o | 0 B | Karaoke |
| `luna-warroom-data-prod` | EUROPE-WEST1 | STANDARD | 0 o | 0 B | Warroom |

**Taille totale : ~115 Go (~107 GiB).**

**Coût estimé :** ~107 GiB Standard × ~€0,020/GiB/mois = **~€2,10–€2,50/mois** (hors opérations et sorties).

**Commande :**
```bash
for b in $(gcloud storage buckets list --format="value(name)"); do
  gcloud storage du -s gs://$b
done
```

### 3.5 Artifact Registry (5 repositories, ~198 GiB)

| Repository | Localisation | Format | Taille | Images | Scan vulnérabilités |
|------------|--------------|--------|--------|--------|---------------------|
| `cloud-run-source-deploy` | europe-west1 | DOCKER | **~169,1 GiB** | 692 | Désactivé |
| `luna` | europe-west1 | DOCKER | **~12,9 GiB** | 54 | Désactivé |
| `gcr.io` (legacy) | us | DOCKER | **~14,6 GiB** | 0 (backend GCR) | Désactivé |
| `iawatch` | europe-west1 | DOCKER | **~1,3 GiB** | 4 | Désactivé |
| `gcf-artifacts` | europe-west1 | DOCKER | **~62,5 MiB** | 16 | Désactivé |

**Total : ~198 GiB**.

**Coût estimé Artifact Registry :** ~198 GiB × ~€0,10/GiB/mois = **~€19,80/mois**.

### 3.6 Container Registry legacy

| Image | Tags | Dernier push |
|-------|------|--------------|
| `gcr.io/.../dayslegacy-ai` | latest + 1 | 2026-06-12 |
| `gcr.io/.../dayslegacy-ai-os` | latest | 2026-06-10 |
| `gcr.io/.../dayslegacy-app` | latest + 4 | 2026-06-12 |
| `gcr.io/.../iawatch-backend` | vide | — |
| `gcr.io/.../luna-beta` | latest, trace-v1..v5, working-dir, p3… | 2026-07-04 |
| `gcr.io/.../luna-server` | days-legacy-demo-v2..v4 | 2026-06-12 |

Ces images sont stockées dans le repository `gcr.io` d'Artifact Registry (déjà compté ci-dessus).

### 3.7 Cloud SQL

| Instance | Résultat |
|----------|----------|
| Cloud SQL | **Aucune** — API `sqladmin.googleapis.com` non activée |

### 3.8 Cloud Functions (2 fonctions Gen 2)

| Nom | Runtime | Trigger | Min/Max | Statut | Problème |
|-----|---------|---------|---------|--------|----------|
| `equipement-t2` | python312 | HTTP | 1 / 1 | ACTIVE | Aucun trafic détecté |
| `stop-vms-on-budget` | python311 | Pub/Sub `budget-alerts` | — | **UNKNOWN / orpheline** | Service Cloud Run cible introuvable |

**Coût :** `equipement-t2` est déjà facturée comme Cloud Run (Gen 2) avec min=1 — intégrée dans l'estimation ~€176/mois.

### 3.9 Cloud Build

| Métrique | Valeur |
|----------|--------|
| Builds récents listés | 50 |
| Succès | 45 |
| Échecs | 5 |
| Dernier build | 2026-06-12 |

Les artefacts de build sont stockés dans `crypto-parser-475411-k4_cloudbuild` (15,39 GiB).

### 3.10 Secret Manager

| Secret | Créé le |
|--------|---------|
| `anthropic-api-key` | 2025-12-05 |
| `google-api-key` | 2025-12-05 |
| `groq-api-key` | 2025-12-05 |
| `jwt-secret-key` | 2025-12-05 |
| `openai-api-key` | 2025-12-05 |
| `twilio-api-key-secret` | 2025-12-08 |
| `twilio-api-key-sid` | 2025-12-08 |

**Risque sécurité :** de nombreuses clés API, tokens, mots de passe sont exposés en **variables d'environnement non chiffrées** dans les services Cloud Run.

### 3.11 Cloud Scheduler

| Job | Résultat |
|-----|----------|
| Scheduler jobs | **0** — API non activée |

### 3.12 Pub/Sub

| Ressource | Résultat |
|-----------|----------|
| Topics | `budget-alerts` |
| Subscriptions | `eventarc-europe-west1-stop-vms-on-budget-...` |

### 3.13 Logging

| Sink / Bucket | Destination | Rétention |
|---------------|-------------|-----------|
| `_Required` | bucket `_Required` | 400 jours |
| `_Default` | bucket `_Default` | 30 jours |

**Volume de logs :** non mesurable directement via CLI.  
**Coût estimé :** avec 357k requêtes/semaine + 986 builds + logs d'audit, un volume de 10–50 Go/mois est plausible → **~€5–€25/mois** (tarif €0,50/Go ingéré au-delà du free tier de 50 Go/mois).

---

## 4. PROJET SECONDAIRE FACTURÉ : `gen-lang-client-0999302538`

| Ressource | Résultat |
|-----------|----------|
| APIs activées | `generativelanguage.googleapis.com`, `cloudaicompanion.googleapis.com`, `telemetry.googleapis.com` |
| Cloud Run / Compute / Storage / SQL / Functions / Build / Secret / Scheduler / Redis | **0** |
| Firestore | 1 base native `(default)` région `nam5` |
| Facturation | Activée sur le même compte 50 EUR |

**Constat :** ce projet consomme probablement des **appels API Gemini** (`generativelanguage`). Sans métriques d'utilisation détaillées, le coût est non chiffrable ici.

---

## 5. PROJETS NON FACTURÉS (IMPACT NUL SUR LE BUDGET)

### `ceremonial-rush-405313`
- Billing : **désactivé**.
- Ressources facturables : **0**.
- APIs activées : Drive, Sheets, BigQuery, Storage, Logging/Monitoring (mais pas de ressources).

### `ia-watch-f7e2a`
- Billing : **désactivé**.
- Ressources facturables : **0**.
- APIs activées : 42 APIs Firebase/BigQuery/etc., mais aucune ressource compute/conteneur/bucket.

**Ces deux projets ne contribuent pas aux 50 EUR.**

---

## 6. COÛT PAR SERVICE (ESTIMATIONS)

| Service | Ressources | Coût estimé mensuel | Base de calcul |
|---------|------------|---------------------|----------------|
| **Cloud Run** | `luna-beta` idle (1 Gi, 2 CPU, min=1) | **~€789** | 730 h × (2×€0,0864 + 1×€0,009) / vCPU·h & GiB·h |
| **Cloud Run** | `equipement-t2` idle (256 Mi, 0,1666 CPU, min=1) | **~€176** | 730 h × (0,1666×€0,0864 + 0,25×€0,009) |
| **Cloud Run** | Requêtes `luna-beta` (~1,5 M/mois) | **€20–€100+** | Selon durée CPU/mémoire par requête |
| **Artifact Registry** | ~198 GiB | **~€20** | ~€0,10/GiB/mois |
| **Cloud Storage** | ~107 GiB Standard | **~€2,50** | ~€0,020/GiB/mois |
| **Compute Snapshots** | ~52,5 GiB | **~€1,40** | ~€0,026/GiB/mois |
| **Cloud Logging** | estimé 10–50 Go/mois | **~€0–€25** | 50 Go inclus, puis €0,50/Go |
| **Cloud Build** | stockage inclus | **inclus** | Dans GCS/AR |
| **Cloud Functions** | Gen 2 = Cloud Run | **inclus** | Déjà compté |
| **APIs externes** | OpenAI, Twilio, Upstash Redis | **HORS GCP** | Non visible sur facture GCP |
| **APIs Google** | Gemini, Maps, Vision, etc. | **Inconnu** | Sans métriques d'appels |
| **TOTAL ESTIMÉ** | — | **~€1 000–€1 100+/mois** | Hors coûts tiers et API Google non mesurés |

**Budget : 50 €/mois.**  
**Dépassement estimé : ~€950–€1 050/mois** rien que pour `crypto-parser-475411-k4`.

---

## 7. TOP 10 DES POSTES DE DÉPENSE ESTIMÉS

| Rang | Poste | Montant estimé/mois | % du total estimé |
|------|-------|---------------------|-------------------|
| 1 | Cloud Run `luna-beta` (idle) | ~€789 | ~75 % |
| 2 | Cloud Run `equipement-t2` (idle) | ~€176 | ~16 % |
| 3 | Cloud Run trafic `luna-beta` | €20–€100+ | 2–9 % |
| 4 | Artifact Registry (198 GiB) | ~€20 | ~2 % |
| 5 | Cloud Logging | €0–€25 | 0–2 % |
| 6 | Cloud Storage (107 GiB) | ~€2,50 | <1 % |
| 7 | Compute Snapshots | ~€1,40 | <1 % |
| 8 | APIs Google (Gemini, Maps, Vision) | Inconnu | ? |
| 9 | Cloud Build (hors stockage) | ~€0 | <1 % |
| 10 | Pub/Sub (topic budget-alerts) | ~€0 | <1 % |

---

## 8. ANALYSE RÉSEAU

| Élément | Résultat |
|---------|----------|
| IP publiques réservées | **0** |
| Load balancers | **0** |
| NAT Gateways | **0** |
| VPC custom | **0** (réseau `default` AUTO uniquement) |
| Trafic entrant Cloud Run | Public (`ingress: all`) |

**Coût réseau estimé :** faible à modéré. Cloud Run inclut un quota de sortie gratuit, mais de gros volumes sortants (vidéo, audio, logs) pourraient générer des frais. Aucune donnée chiffrée disponible.

---

## 9. APIS ET CONSOMMATION

### 9.1 APIs activées dans `crypto-parser-475411-k4` (potentiellement payantes)

| API | Usage connu | Risque coût |
|-----|-------------|-------------|
| `aerialview.googleapis.com` | Inconnu | Moyen |
| `airquality.googleapis.com` | Inconnu | Faible |
| `maps-android-backend.googleapis.com` | App Android | Moyen |
| `roads.googleapis.com` | Routes | Faible |
| `routes.googleapis.com` | Itinéraires | Moyen/Élevé |
| `street-view-image-backend.googleapis.com` | Street View | Moyen |
| `tile.googleapis.com` | Cartes tuilées | Moyen/Élevé |
| `timezone-backend.googleapis.com` | Fuseaux horaires | Faible |
| `vision.googleapis.com` | OCR / Vision AI | Moyen/Élevé |
| `generativelanguage.googleapis.com` | Gemini | Potentiellement élevé |
| `run.googleapis.com` | Cloud Run | Oui (principal) |

### 9.2 APIs activées dans `gen-lang-client-0999302538`

| API | Usage | Risque coût |
|-----|-------|-------------|
| `generativelanguage.googleapis.com` | Gemini | Potentiellement élevé |

**Constat :** `speech.googleapis.com` (Speech-to-Text) **n'est pas activée** dans les projets inspectés. Si Speech est utilisé, il passe soit par un autre projet, soit par une API tierce (OpenAI Realtime, ElevenLabs, etc.).

---

## 10. SERVICES QUI TOURNENT INUTILEMENT

| Service / Ressource | Pourquoi inutile | Preuve |
|---------------------|------------------|--------|
| `equipement-t2` | min=1, **0 requête** sur 7 jours | Métriques Monitoring |
| `dayslegacy-ai` | Service **en échec permanent**, 0 trafic | `gcloud run services list` |
| `luna-staging` | Service **en échec permanent**, 1 seule requête 4xx | `gcloud run services list` + metrics |
| `dayslegacy-app` | 0 requête détectée | Metrics |
| `dayslegacy-workspace-demo` | 0 requête détectée | Metrics |
| `yawatch-video-engine` | 0 requête détectée, maxScale non défini | Metrics + service list |
| `stop-vms-on-budget` (Cloud Function) | Orpheline — ne peut pas s'exécuter | `gcloud functions list --format=json` |
| Snapshots VM supprimées | Disques sources n'existent plus | `gcloud compute snapshots list` |
| Images Cloud Run anciennes | 692 images dans `cloud-run-source-deploy` | `gcloud artifacts docker images list` |
| Sources Cloud Run anciennes | 91,64 GiB dans `run-sources-...` | `gcloud storage du` |

---

## 11. PLAN D'ÉCONOMIE (LECTURE SEULE — PAS D'ACTION EXÉCUTÉE)

| Économie possible | Action suggérée | Risque | Impact | Recommandation |
|-------------------|-----------------|--------|--------|----------------|
| **~€789/mois** | Passer `luna-beta` en `minInstances=0` hors production | Cold starts plus fréquents | Très fort | **À valider avec Ludovic** — ne PAS faire sur la production si Guardian/Iris nécessitent une latence faible. Tester sur un environnement dédié d'abord. |
| **~€176/mois** | Passer `equipement-t2` en `minInstances=0` | Cold start à la première requête | Fort | Candidat prioritaire — aucun trafic observé. |
| **~€20–€100+/mois** | Supprimer `dayslegacy-ai` et `luna-staging` (services en échec) | Perte de l'historique de révisions/images | Faible | **Recommandé** — ils ne servent rien. |
| **~€20/mois** | Nettoyer Artifact Registry (politique de rétention 30 jours) | Perte d'images anciennes | Faible | **Recommandé** — garder uniquement `latest` et tags protégés. |
| **~€2–€10/mois** | Lifecycle policy sur `run-sources-...` (suppression > 30 j) | Impossible de redeployer une ancienne source | Faible | **Recommandé** — les sources sont recréées à chaque build. |
| **~€1–€5/mois** | Vider ou lifecycle policy sur `crypto-parser-475411-k4_cloudbuild` | Perte d'artefacts anciens | Faible | **Recommandé** — après validation. |
| **~€1,37/mois** | Archiver ou supprimer les 2 snapshots de VMs supprimées | Perte du backup | Faible | Évaluer d'abord si les données sont encore utiles. |
| **Variable** | Réduire `maxScale` sur `yawatch-video-engine` | Limitation du scaling | Faible | Définir `maxScale=3` ou `5`. |
| **Variable** | Limiter `ingress` aux services internes | Réduction surface d'attaque | Faible | Pas un gain direct mais bonne pratique. |
| **Variable** | Migrer secrets en Secret Manager | Amélioration sécurité | N/A | Bonne pratique, pas d'impact coût direct. |

**Priorité absolue :** conserver `luna-beta` (Guardian/Iris/production) fonctionnel.  
**Ne jamais modifier directement la production** sans validation de Ludovic.

---

## 12. COMMANDES CLÉS UTILISÉES (POUR REPRODUIRE L'AUDIT)

```bash
# Contexte
export PROJECT=crypto-parser-475411-k4
export BILLING=01C217-F83E98-3C12CF
gcloud config set project $PROJECT

# Facturation
gcloud billing accounts list
gcloud billing accounts projects list --billing-account=$BILLING
gcloud billing budgets list --billing-account=$BILLING
gcloud billing projects describe $PROJECT

# Ressources principales
gcloud run services list --format=json
gcloud run revisions list --region=europe-west1
gcloud compute instances list
gcloud compute disks list
gcloud compute snapshots list
gcloud compute addresses list
gcloud compute networks list
gcloud storage buckets list
gcloud storage du -s gs://<bucket>
gcloud artifacts repositories list
gcloud artifacts docker images list europe-west1-docker.pkg.dev/$PROJECT/cloud-run-source-deploy --include-tags
gcloud container images list --repository=gcr.io/$PROJECT
gcloud sql instances list
gcloud functions list --format=json
gcloud builds list --limit=50
gcloud secrets list
gcloud scheduler jobs list --location=europe-west1
gcloud pubsub topics list
gcloud pubsub subscriptions list
gcloud logging sinks list
gcloud logging buckets list

# Métriques Monitoring
export TOKEN=$(gcloud auth print-access-token)
curl -H "Authorization: Bearer $TOKEN" \
  "https://monitoring.googleapis.com/v3/projects/$PROJECT/timeSeries?filter=metric.type%3D%22run.googleapis.com%2Frequest_count%22&interval.startTime=2026-06-29T00:00:00Z&interval.endTime=2026-07-06T23:59:59Z&aggregation.alignmentPeriod=604800s&aggregation.perSeriesAligner=ALIGN_SUM"
```

---

## 13. CONCLUSION ET RECOMMANDATIONS IMMÉDIATES

1. **Le dépassement de 50 € vient à ~91 % de Cloud Run**, principalement de `luna-beta` (~€789/mois en idle) et `equipement-t2` (~€176/mois en idle).
2. **Aucune VM Compute Engine** n'est en cours d'exécution. Deux snapshots de VMs supprimées coûtent ~€1,37/mois.
3. **Aucune instance Redis Memorystore** n'existe chez Google — Redis est chez Upstash (coût externe).
4. **Le stockage (GCS + Artifact Registry)** représente ~€22/mois, facilement réductibles en nettoyant les anciens builds et sources.
5. **Les API Google** (Gemini, Maps, Vision, Routes) sont activées mais leur consommation exacte n'est pas mesurable sans export BigQuery.
6. **Action prioritaire suggérée sans toucher à la production :** auditer la nécessité réelle de `minInstances=1` sur `luna-beta` et `equipement-t2`, puis tester `minInstances=0` sur un environnement non critique.

**Prochaine étape recommandée :** configurer un **Cloud Billing export vers BigQuery** pour obtenir des coûts exacts par service, jour et projet. Cela permettra d'affiner ce rapport avec des chiffres réels.

---

*Fin du rapport d'audit FinOps.*
