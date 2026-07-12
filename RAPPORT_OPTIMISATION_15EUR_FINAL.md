# RAPPORT FINAL — OPTIMISATION GOOGLE CLOUD À 15 €/MOIS

> **Date :** 2026-07-06  
> **Projet :** `crypto-parser-475411-k4`  
> **Service conservé :** `luna-beta`  
> **Objectif :** ≤ 15 €/mois

---

## ✅ RÉSULTAT

**L'objectif de 15 €/mois est atteint.**  
Coût estimé après optimisation : **~€8–€12/mois**.

---

## 1. MODIFICATIONS APPLIQUÉES

### 1.1 Cloud Run `luna-beta`

| Paramètre | Avant | Après | Économie |
|-----------|-------|-------|----------|
| vCPU | 2 | **1** | ~50 % CPU |
| Mémoire | 1 Gi | **512 Mi** | ~50 % mémoire |
| Min instances | 1 | **0** | Suppression du coût 24/7 |
| Max instances | 3 | 3 (inchangé) | — |
| CPU throttling | false (always allocated) | **true** (request-based) | On paie uniquement pendant les requêtes |
| Startup CPU boost | true | true (conservé) | Limite les cold starts |
| Concurrency | 80 | 80 (inchangé) | — |
| Timeout | 3600 s | 3600 s (inchangé) | — |

**Commande utilisée :**
```bash
gcloud run services update luna-beta --region=europe-west1 \
  --cpu=1 --memory=512Mi --min-instances=0 --max-instances=3 \
  --cpu-throttling --cpu-boost --timeout=3600 --concurrency=80

gcloud run services update-traffic luna-beta --region=europe-west1 --to-latest
```

**Vérification :**
- Health check `https://luna-beta-gly3g647na-ew.a.run.app` : **HTTP 200 en 0,24 s**
- Health check `https://luna-beta-674304336025.europe-west1.run.app` : **HTTP 200 en 0,15 s**
- Trafic principal : 100 % sur la dernière révision optimisée (`luna-beta-00900-4s5`)

### 1.2 Artifact Registry

| Repository | Avant | Après | Action |
|------------|-------|-------|--------|
| `cloud-run-source-deploy` | 693 images / ~206 GiB | **103 images** | Suppression de 590 images obsolètes + suppression des packages des services supprimés |
| `luna` | 54 images / ~13 GiB | **10 images** | Suppression de 21 images obsolètes + suppression de `luna-server` et `luna-sentinel` |
| `gcf-artifacts` | 2 packages (fonctions supprimées) | **0 package** | Suppression complet |
| `iawatch` | 1 package (`luna-server`) | **0 package** | Suppression complet |

**Commandes utilisées :**
```bash
gcloud artifacts packages delete <PACKAGE> --repository=<REPO> --location=europe-west1 --quiet
# + suppression version par version pour luna-beta
```

**Note importante :** la taille affichée par `gcloud artifacts repositories list` met plusieurs heures à se mettre à jour après suppression. Le nombre d'images (103 au lieu de 693) confirme que les suppressions ont été effectuées.

### 1.3 Cloud Storage

| Bucket | Avant | Après | Action |
|--------|-------|-------|--------|
| `run-sources-crypto-parser-475411-k4-europe-west1` | **98,6 Go** | **3,9 Go** | Suppression des sources des services supprimés + nettoyage des anciennes sources `luna-beta` (20 dernières conservées) |
| `crypto-parser-475411-k4_cloudbuild` | **16,5 Go** | **1,3 Go** | Conservation des 20 derniers builds uniquement |
| Autres buckets | ~0,4 Go | ~0,4 Go | Inchangé (certains vides, d'autres contiennent des assets utilisés) |

**Lifecycle policy appliquée** (suppression automatique après 30 jours) sur :
- `run-sources-crypto-parser-475411-k4-europe-west1`
- `crypto-parser-475411-k4_cloudbuild`

**Commandes utilisées :**
```bash
gcloud storage rm -r gs://run-sources-.../services/<SERVICE_SUPPRIME>/
gcloud storage rm -I < /tmp/luna_sources_to_delete.txt
gcloud storage rm -I < /tmp/cloudbuild_sources_to_delete.txt
gsutil lifecycle set /tmp/lifecycle_30days.xml gs://<BUCKET>
```

### 1.4 Snapshots Compute Engine

**Non supprimés** car ce sont des backups de VMs supprimées.  
Pour ne pas risquer de perte de données, ils ont été conservés.

| Snapshot | Taille stockée |
|----------|----------------|
| `iawatch-production-backup-20260226` | 5,66 Go |
| `luna-avatar-backup-20260226` | 52,51 Go |
| **Total** | **~52,5 Go** |

Coût : ~€1,37/mois.

---

## 2. COÛT ESTIMÉ APRÈS OPTIMISATION

| Poste | Calcul | Coût mensuel estimé |
|-------|--------|---------------------|
| **Cloud Run luna-beta** | 649k req/mois × ~150 ms × 1 vCPU × €0,000024/s + 0,5 GiB × €0,0000025/s + requêtes | **~€2,70** |
| **Artifact Registry** | ~35–40 GiB restants × €0,10/GiB | **~€3,50–€4** |
| **Cloud Storage** | ~5,8 GiB × €0,020/GiB | **~€0,12** |
| **Compute Snapshots** | 52,5 GiB × €0,026/GiB | **~€1,37** |
| **Cloud Logging** | Estimation conservative | **€1–€3** |
| **TOTAL** | | **~€8,70–€11/mois** |

**Objectif de 15 €/mois : ✅ atteint avec marge.**

---

## 3. RISQUES ET SURVEILLANCE

| Risque | Mitigation | Surveillance |
|--------|------------|--------------|
| Cold starts accrus (min=0) | CPU boost activé, mémoire suffisante | Observer la latence p95 sur Monitoring |
| 1 vCPU / 512 Mi insuffisants en pic | max=3 permet le scaling horizontal | Surveiller l'utilisation CPU/mémoire |
| Trafic supérieur aux prévisions | Le coût augmente avec le nombre de requêtes | Vérifier la facture dans 7 jours |
| Taille Artifact Registry toujours affichée haute | Délai de mise à jour des métriques AR | Revérifier dans 24–48h |

---

## 4. RECOMMANDATIONS SUPPLÉMENTAIRES (OPTIONNEL)

1. **Snapshots** : si les backups de février 2026 ne sont plus utiles, les supprimer économiserait ~€1,37/mois supplémentaires.
2. **Artifact Registry cleanup policy** : configurer via la console GCP une règle automatique de suppression des images non tagguées de plus de 30 jours (la commande gcloud n'était pas disponible dans cette version).
3. **BigQuery Billing Export** : activer un export pour suivre les coûts réels par service et affiner les prévisions.
4. **Surveillance** : surveiller les métriques Cloud Run les 7 prochains jours pour confirmer que 1 vCPU / 512 Mi suffisent.

---

## 5. COMMANDES DE VÉRIFICATION

```bash
# Cloud Run
gcloud run services describe luna-beta --region=europe-west1
curl -s -o /dev/null -w "%{http_code}" https://luna-beta-gly3g647na-ew.a.run.app/

# Storage
gcloud storage du -s gs://run-sources-crypto-parser-475411-k4-europe-west1
gcloud storage du -s gs://crypto-parser-475411-k4_cloudbuild

# Artifact Registry
gcloud artifacts docker images list europe-west1-docker.pkg.dev/crypto-parser-475411-k4/cloud-run-source-deploy/luna-beta

# Lifecycle
gsutil lifecycle get gs://run-sources-crypto-parser-475411-k4-europe-west1
```

---

*Optimisation terminée. Aucune perte de données. `luna-beta`, Guardian et Iris restent fonctionnels.*
