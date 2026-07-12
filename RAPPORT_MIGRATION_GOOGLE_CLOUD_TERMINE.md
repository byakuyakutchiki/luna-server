# RAPPORT FINAL — FERMETURE GOOGLE CLOUD TERMINÉE

> Date : 2026-07-06  
> Projets concernés : `crypto-parser-475411-k4`, `gen-lang-client-0999302538`

---

## 1. POURQUOI LA FACTURE ÉTAIT MONTEE À 94,85 €

L'augmentation de ~50 € à ~95 € s'explique par :

1. **Cloud Run `luna-beta` avant optimisation** : 2 vCPU, 1 Gi, min=1, CPU always allocated.  
   Le service a scalé fortement fin juin / début juillet :
   - 21–28 juin : ~24 h d'instance/jour (1 instance permanente)
   - 29 juin : 29 h (début de surcharge)
   - 30 juin : 49 h
   - 3 juillet : 108 h
   - 4 juillet : 157 h
   - 5 juillet : 168 h
   
   Cela correspond à **7 instances simultanées** en moyenne le 5 juillet.

2. **Artifact Registry** : ~206 GiB d'images Docker accumulées.

3. **Cloud Storage** : ~115 Go de sources et builds.

4. **Logging** : ~0,8 GiB/7 jours, resté dans le free tier.

La facture affichée correspond à **des consommations déjà effectuées**. Les optimisations du 6 juillet n'auraient affecté que les jours suivants.

---

## 2. SAUVEGARDES EFFECTUÉES AVANT SUPPRESSION

| Fichier | Contenu | Localisation |
|---------|---------|--------------|
| `migration_backup/secrets.env` | 7 secrets API (OpenAI, Anthropic, Twilio, etc.) | `/home/ludo/luna-server/migration_backup/` |
| `migration_backup/luna-beta-env.txt` | 24 variables d'environnement Cloud Run | `/home/ludo/luna-server/migration_backup/` |
| `migration_backup/luna-beta-images.txt` | Digests des images Docker luna-beta | `/home/ludo/luna-server/migration_backup/` |
| `migration_backup/storage_assets/` | Assets vidéo + fichiers vault (~381 Mo) | `/home/ludo/luna-server/migration_backup/storage_assets/` |

⚠️ Ces fichiers contiennent des secrets. Ils ont été créés avec `chmod 600`.

---

## 3. RESSOURCES SUPPRIMÉES

### Projet `crypto-parser-475411-k4`

| Ressource | Quantité supprimée |
|-----------|-------------------|
| Cloud Run services | 1 (`luna-beta`) |
| Cloud Functions | 1 (`stop-vms-on-budget`) |
| Artifact Registry repositories | 5 (`cloud-run-source-deploy`, `luna`, `gcr.io`, `iawatch`, `gcf-artifacts`) |
| Docker images supprimées | ~640 images |
| Cloud Storage buckets | 9 buckets |
| Données Storage libérées | ~115 Go |
| Compute snapshots | 2 snapshots |
| Secret Manager secrets | 7 secrets |
| Pub/Sub topics | 1 (`budget-alerts`) |

### Projet `gen-lang-client-0999302538`

- Aucune ressource facturable détectée.
- Facturation désactivée.

---

## 4. ÉTAT FINAL

### Facturation

| Projet | Facturation activée ? |
|--------|----------------------|
| `crypto-parser-475411-k4` | **False** |
| `gen-lang-client-0999302538` | **False** |
| `ceremonial-rush-405313` | False |
| `ia-watch-f7e2a` | False |

### Ressources restantes dans `crypto-parser-475411-k4`

| Type | Restant |
|------|---------|
| Cloud Run | 0 |
| Cloud Functions | 0 |
| Compute Engine VMs | 0 |
| Disques persistants | 0 |
| Snapshots | 0 |
| IP publiques | 0 |
| Cloud Storage buckets | 0 |
| Artifact Registry repositories | 0 |
| Secrets | 0 |
| Pub/Sub topics | 0 |
| Cloud SQL | 0 |

**Il ne reste plus aucune ressource facturable.**

---

## 5. PROCHAINES ÉTAPES — MIGRATION VERS PC LOCAL

### 5.1 Préparer la VM Debian

1. Installer les dépendances :
   ```bash
   sudo apt update
   sudo apt install -y python3-pip python3-venv redis-server git
   ```

2. Cloner le dépôt :
   ```bash
   git clone <URL_GITHUB> luna-server
   cd luna-server
   ```

3. Recréer le fichier `.env` à partir de :
   - `migration_backup/secrets.env`
   - `migration_backup/luna-beta-env.txt`

4. Installer les dépendances Python :
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. Lancer Redis :
   ```bash
   sudo systemctl enable redis-server
   sudo systemctl start redis-server
   ```

6. Lancer le backend :
   ```bash
   uvicorn luna_web:app --host 0.0.0.0 --port 8000
   ```

### 5.2 Tester en local

- `curl http://localhost:8000/`
- Tester Guardian depuis le téléphone sur le même Wi-Fi (utiliser l'IP locale de la VM).
- Vérifier les WebSocket.

### 5.3 Accès depuis l'extérieur (optionnel)

- **Cloudflare Tunnel** : gratuit, temporaire.
- **Tailscale** : VPN maillé gratuit.
- À éviter : exposition directe de ports sur Internet.

---

## 6. SURVEILLANCE POST-MIGRATION

- Vérifier la prochaine facture Google Cloud : elle devrait être à **0 €** (ou n'afficher que les 94,85 € déjà consommés).
- Si des frais résiduels apparaissent malgré tout, vérifier le compte de facturation dans la console GCP.
- Surveiller l'utilisation CPU/RAM de la VM Debian.

---

## 7. IMPORTANT

- Les **94,85 €** restent dus à Google Cloud (consommations antérieures).
- Aucune nouvelle facturation ne devrait avoir lieu.
- Si tu souhaites revenir sur Google Cloud plus tard, il faudra recréer toutes les ressources (le code source est sur GitHub, les secrets sont dans `migration_backup/`).

---

*Migration terminée. Luna est prêt à être hébergé sur ton PC local.*
