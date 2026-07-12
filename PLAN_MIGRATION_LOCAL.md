# PLAN DE MIGRATION — LUNA VERS PC LOCAL + FERMETURE GOOGLE CLOUD

> Date : 2026-07-06  
> Projet concerné : `crypto-parser-475411-k4`

---

## ⚠️ AVERTISSEMENTS

- Les **94,85 € déjà affichés** correspondent à des consommations **déjà effectuées**. Supprimer les ressources aujourd'hui empêchera les **futures** factures, mais ne remboursera pas les frais déjà accumulés.
- Cette procédure est **destructrice**. Une ressource supprimée est perdue définitivement (sauf backups locaux).
- Après suppression, il faudra avoir un environnement local (VM Debian sur ton PC) prêt à accueillir Luna.

---

## 1. SAUVEGARDES DÉJÀ EFFECTUÉES

| Fichier | Contenu | Emplacement |
|---------|---------|-------------|
| `migration_backup/secrets.env` | 7 secrets GCP | `/home/ludo/luna-server/migration_backup/` |
| `migration_backup/luna-beta-env.txt` | 24 variables d'environnement Cloud Run | `/home/ludo/luna-server/migration_backup/` |
| `migration_backup/luna-beta-images.txt` | Digests des images Docker luna-beta | `/home/ludo/luna-server/migration_backup/` |
| `migration_backup/storage_assets/` | Assets iawatch + luna-vault (~381 Mo) | `/home/ludo/luna-server/migration_backup/storage_assets/` |

Ces fichiers contiennent des secrets. Ils ont été créés avec `chmod 600`.

---

## 2. ARCHITECTURE CIBLE SUR PC LOCAL

```
PC Windows (Ryzen 7, 32 Go RAM, RTX 4060)
│
├── VM Debian
│      ├── Docker (optionnel)
│      ├── luna-server (FastAPI/Uvicorn)
│      ├── Redis local
│      ├── Guardian
│      └── tests
│
├── Android (téléphone)
│      └── APK Guardian
│
└── GitHub
       └── code source + .env
```

Pour les tests depuis l'extérieur : Cloudflare Tunnel ou Tailscale (temporaire, gratuit).

---

## 3. RESSOURCES GOOGLE CLOUD À SUPPRIMER

### 3.1 Cloud Run
- [x] `luna-beta` (dernier service restant)

### 3.2 Cloud Functions
- [ ] `stop-vms-on-budget` (orpheline)

### 3.3 Artifact Registry
- [ ] `cloud-run-source-deploy`
- [ ] `luna`
- [ ] `gcr.io`
- [ ] `iawatch`
- [ ] `gcf-artifacts`

### 3.4 Cloud Storage
- [ ] `run-sources-crypto-parser-475411-k4-europe-west1`
- [ ] `crypto-parser-475411-k4_cloudbuild`
- [ ] `iawatch-assets`
- [ ] `ludo-equipement-t2`
- [ ] `luna-vault-originals-674304336025`
- [ ] `gcf-v2-sources-674304336025-europe-west1`
- [ ] `gcf-v2-uploads-...` (vide)
- [ ] `luna-karaoke-drafts-...` (vide)
- [ ] `luna-warroom-data-prod` (vide)

### 3.5 Compute Engine
- [ ] 2 snapshots (`iawatch-production-backup-20260226`, `luna-avatar-backup-20260226`)

### 3.6 Pub/Sub
- [ ] Topic `budget-alerts`
- [ ] Subscription `eventarc-europe-west1-stop-vms-on-budget-...`

### 3.7 Secret Manager
- [ ] `anthropic-api-key`
- [ ] `google-api-key`
- [ ] `groq-api-key`
- [ ] `jwt-secret-key`
- [ ] `openai-api-key`
- [ ] `twilio-api-key-secret`
- [ ] `twilio-api-key-sid`

### 3.8 Logging
- [ ] Sinks personnalisés (s'il y en a)

### 3.9 Billing
- [ ] Désactiver la facturation sur le projet `crypto-parser-475411-k4`
- [ ] OU supprimer complètement le projet

---

## 4. ÉTAPES DE MIGRATION

### Étape 1 — Préparer l'environnement local
1. S'assurer que la VM Debian est fonctionnelle.
2. Installer Python 3.11+, Redis, Git.
3. Cloner `luna-server` depuis GitHub.
4. Recréer le fichier `.env` à partir de `migration_backup/secrets.env` + `luna-beta-env.txt`.
5. Lancer le backend avec Uvicorn.
6. Vérifier que Redis est accessible.

### Étape 2 — Tester en local
1. Appeler une API locale (`curl http://localhost:8000/...`).
2. Tester Guardian via le Wi-Fi local.
3. Vérifier les WebSocket.

### Étape 3 — Basculer le DNS / les clients
1. Si tu utilises un nom de domaine : pointer vers ton PC (via Cloudflare Tunnel ou IP dynamique).
2. Sinon, configurer l'APK pour pointer vers l'IP locale de la VM.

### Étape 4 — Supprimer Google Cloud
Suivre la checklist de la section 3 ci-dessus.

---

## 5. POST-MIGRATION

- Surveiller la prochaine facture Google Cloud pour s'assurer qu'elle tombe à 0 €.
- Si des frais résiduels apparaissent : identifier la ressource oubliée et la supprimer.
- Activer un monitoring local basique (logs, health checks).
