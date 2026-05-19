# Luna — Contexte Kimi

Tu es l'IA de maintenance de l'application **Luna** (YAWatch). Lis ce fichier en entier avant d'agir.

---

## Repos GitHub (tous privés)

| Rôle | Repo | Branche |
|------|------|---------|
| Serveur principal | `byakuyakutchiki/luna-server` | `main` |
| Projet proprio (sentinel, docs) | `byakuyakutchiki/luna-proprio` | `master` |

---

## Architecture

- **Backend** : FastAPI (`luna_web.py`) + modules dans `core/`
- **Frontend** : WebView Android APK (`android-app/`) + pages HTML dans `static/`
- **Base de données** : Redis Cloud (`redis-11664.c259.us-central1-2.gce.cloud.redislabs.com:11664`)
- **Déploiement** : Google Cloud Run, région `europe-west1`, projet `crypto-parser-475411-k4`
- **Service Cloud Run** : `luna-beta` → `https://luna-beta-674304336025.europe-west1.run.app`
- **Image Docker** : `europe-west1-docker.pkg.dev/crypto-parser-475411-k4/luna/luna-server:latest`

---

## Fichiers clés

```
luna_web.py                    ← point d'entrée FastAPI, toutes les routes
core/
  secretary/
    routes.py                  ← API secrétaire (documents, budget, rappels)
    redis_ops.py               ← CRUD Redis secrétaire
    scanner.py                 ← analyse OCR documents (Claude Vision)
  memory/redis_client.py       ← client Redis partagé
  vault/                       ← module coffre-fort documents
  social/                      ← monde social Luna
  world/                       ← monde 3D
static/
  index.html                   ← app principale (WebView)
  documents.html               ← onglet Documents secrétaire
  world.html                   ← monde de Luna
  simli.html                   ← cinématique + Tavus visio
android-app/
  build/luna-proprio.apk       ← APK signé prêt à distribuer
```

---

## Luna QA Sentinel (tests automatiques)

Repo : `byakuyakutchiki/luna-proprio`, dossier `luna-qa-sentinel/`

```
run_sentinel.py      ← point d'entrée : connexion ADB → navigation → rapport
sentinel/
  device.py          ← wrapper ADB (screenshot, tap, swipe, logcat)
  analyzer.py        ← analyse screenshot via Claude Vision (claude-sonnet-4-6)
  explorer.py        ← login + navigation 5 onglets + swipes
  reporter.py        ← rapport HTML + JSON (critique/moyen/faible)
config.json          ← credentials, URL serveur, onglets
```

**Lancer le sentinel (téléphone branché en ADB) :**
```bash
cd luna-qa-sentinel
export ANTHROPIC_API_KEY=...
python3 run_sentinel.py --device <SERIAL>
```

**Credentials de test :**
- Email : `saintlouis.ludovic@gmail.com`
- Mot de passe : `Luna2026`

---

## Déployer un fix sur Cloud Run

```bash
# 1. Modifier les fichiers dans luna-server
# 2. Build + push image
gcloud builds submit --tag europe-west1-docker.pkg.dev/crypto-parser-475411-k4/luna/luna-server:latest --region europe-west1

# 3. Déployer
gcloud run services update luna-beta --region europe-west1 \
  --image europe-west1-docker.pkg.dev/crypto-parser-475411-k4/luna/luna-server:latest
```

---

## Variables d'environnement Cloud Run (principales)

| Variable | Usage |
|----------|-------|
| `REDIS_URL` | Redis Cloud (auth + mémoire) |
| `OPENAI_API_KEY` | GPT-4o-mini (chat, analyse) |
| `ANTHROPIC_API_KEY` | Claude Vision (scanner docs, sentinel) |
| `TAVUS_API_KEY` | Visio avatar Luna |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | SMS |
| `JWT_SECRET_KEY` | Auth tokens |

Pour lire les valeurs actuelles :
```bash
gcloud run services describe luna-beta --region europe-west1 \
  --format="value(spec.template.spec.containers[0].env)"
```

---

## Règles importantes

1. **Ne jamais stocker `html.escape()` dans Redis** — les entités `&#x27;` s'affichent en brut dans le WebView.
2. **Coordonnées UI ADB (device 1220×2712)** — tabs : Chat(76,552) Conciergerie(294,552) Amis(514,552) Activités(702,552) Monde(906,552) Rapports(1109,552).
3. **APK** — après toute modification de `static/`, rebuild l'APK : `cd android-app && ./build.sh` puis `cp build/luna-proprio.apk ../static/`.
4. **Redis keys** — préfixe `luna:{tenant_id}:` pour les données utilisateur. Tenant Ludo = `1`.
5. **Secrets** — ne jamais commit `.env`, clés API ou `pv_lock.json`.

---

## Tâches typiques que tu peux effectuer

- **Corriger un bug** : lire le code dans le repo, faire un commit sur `main`, déclencher le build Cloud Run.
- **Analyser un rapport sentinel** : lire le JSON dans `luna-qa-sentinel/reports/`, identifier les bugs réels vs faux positifs.
- **Ajouter une feature** : modifier `luna_web.py` + le HTML concerné, commit + deploy.
- **Vérifier Redis** : utiliser `redis-cli -u <REDIS_URL>` ou un script Python avec `redis.from_url()`.
