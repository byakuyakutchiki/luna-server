# RAPPORT D'AUDIT — REPRISE DU DÉVELOPPEMENT LOCAL

> Date : 2026-07-08  
> Projet : `/home/ludo/luna-server`  
> Mode : LECTURE SEULE (aucune modification effectuée)

---

## VERDICT FINAL

🔴 **ENVIRONNEMENT NON PRÊT À REPRENDRE LE DÉVELOPPEMENT**

Le serveur démarre et répond localement, mais plusieurs blocquants doivent être corrigés avant de reprendre les tests/développements.

---

## 1. SAUVEGARDES

| Élément | État | Détail |
|---------|------|--------|
| Dépôt Git | ⚠️ **À NETTOYER** | 92 fichiers modifiés/non suivis ; branche `feature/phase-a-auth-apk` |
| Branche actuelle | ✅ | `feature/phase-a-auth-apk` |
| GitHub | ✅ | Remote configuré : `https://github.com/byakuyakutchiki/luna-server.git` |
| Diff avec origin | ✅ | Aucun commit en retard détecté (branche non trackée) |
| `.env` | ✅ | Présent (`/home/ludo/luna-server/.env`) |
| `migration_backup/` | ✅ | Présent avec secrets, env, images digests, assets |
| Snapshot VirtualBox | 🔴 **NON VÉRIFIABLE / PROBABLEMENT ABSENT** | `VBoxManage` non disponible dans la VM |

**Recommandation immédiate :** créer un snapshot VirtualBox **depuis Windows** avant toute modification.

---

## 2. SÉCURITÉ DE LA VM

- **Aucun snapshot détectable** depuis l'intérieur de la VM.
- `VBoxManage` n'est pas accessible depuis la VM Debian.
- **Action requise :** créer un snapshot via l'interface VirtualBox sur Windows.

---

## 3. VÉRIFICATION DE LUNA

### 3.1 Redis

| Test | Résultat |
|------|----------|
| `redis-cli ping` | **PONG** ✅ |
| Service `redis-server` | **active** ✅ |

### 3.2 Python

| Élément | Résultat |
|---------|----------|
| Version | **3.11.2** ✅ |
| Virtual env | **Aucun** ⚠️ (installation globale) |

### 3.3 Dépendances principales

| Module | État |
|--------|------|
| fastapi | ✅ |
| uvicorn | ✅ |
| redis | ✅ |
| pydantic | ✅ |
| requests | ✅ |
| twilio | ✅ |
| openai | ✅ |
| httpx | ✅ |
| jinja2 | ✅ |
| passlib | ✅ |
| bcrypt | ✅ |
| **elevenlabs** | 🔴 **MANQUANT** |
| **python-multipart** | 🔴 **MANQUANT** |
| **python-jose** | 🔴 **MANQUANT** |

**Action requise :**
```bash
pip install elevenlabs python-multipart python-jose
```

### 3.4 Démarrage de `luna_web.py`

| Test | Résultat |
|------|----------|
| Import de `luna_web` | ✅ Succès |
| Connexion Redis | ✅ OK |
| Démarrage Uvicorn | ✅ OK |
| Health check `http://localhost:8000/` | ✅ **HTTP 200** |

Le serveur démarre donc correctement en local.

### 3.5 Guardian

| Élément | État |
|---------|------|
| Fichiers Guardian | ✅ Présents (`core/guardian/`) |
| APK | ✅ Plusieurs APK présents (`base.apk`, `luna.apk`, `luna-proprio-diag.apk`) |

---

## 4. DÉPENDANCES GOOGLE CLOUD RESTANTES

### 4.1 Variables d'environnement problématiques

| Variable | Valeur actuelle | Problème |
|----------|-----------------|----------|
| `IAWATCH_BACKEND_URL` | `https://iawatch-backend-674304336025.europe-west1.run.app` | Service Cloud Run supprimé ❌ |
| `CLOUD_RUN_URL` | `https://luna-beta-gly3g647na-ew.a.run.app` | Service Cloud Run supprimé ❌ |
| `REDIS_URL` | `rediss://...upstash.io:6379` | Redis externe payant (Upstash) ❌ |
| `GOOGLE_OAUTH_CLIENT_ID` | `674304336025-...apps.googleusercontent.com` | Projet GCP supprimé ❌ |
| `GOOGLE_OAUTH_CLIENT_SECRET` | présent | Projet GCP supprimé ❌ |

### 4.2 Code avec dépendances GCS actives

| Fichier | Dépendance | Risque |
|---------|------------|--------|
| `luna_web.py` | `google.cloud.storage` (bucket `luna-karaoke-drafts-674304336025`) | Échec si fonctionnalité Karaoke utilisée |
| `core/vault/originals.py` | `google.cloud.storage` (bucket `luna-vault-originals-674304336025`) | Échec si fonctionnalité Vault utilisée |

Ces imports sont **paresseux** : le serveur démarre, mais les appels à ces fonctionnalités échoueront.

### 4.3 URLs Cloud Run hardcodées dans le code

| Fichier | URL obsolète |
|---------|--------------|
| `luna_web.py` | `https://iawatch-backend-674304336025.europe-west1.run.app` |
| `luna_web.py` | `https://luna-beta-674304336025.europe-west1.run.app` |
| `luna_web.py` | `https://luna-beta-gly3g647na-ew.a.run.app` |
| `static/demo.html` | `luna-beta-674304336025.europe-west1.run.app/...` |
| `static/pitch.html` | `luna-beta.run.app` |
| `GUIDE_OPERATIONNEL.md` | multiples |
| `GUIDE_DEV.md` | multiples |

### 4.4 Script de déploiement GCP

| Fichier | Problème |
|---------|----------|
| `deploy.sh` | Déploie sur Cloud Run `crypto-parser-475411-k4` — ne fonctionnera plus |

---

## 5. ÉTAT DU PROJET

### ✅ Ce qui fonctionne déjà

- Redis local opérationnel
- `luna_web.py` s'importe et démarre
- Le serveur répond HTTP 200 sur `localhost:8000`
- Guardian et les fichiers de code sont présents
- Les secrets et variables d'environnement sont sauvegardés dans `migration_backup/`

### 🔴 Ce qui est cassé ou bloquant

1. **3 dépendances Python manquantes** : `elevenlabs`, `python-multipart`, `python-jose`
2. **REDIS_URL pointe vers Upstash** au lieu de `redis://localhost:6379/0`
3. **Variables `IAWATCH_BACKEND_URL` et `CLOUD_RUN_URL`** pointent vers des services supprimés
4. **Fonctions GCS** dans `luna_web.py` et `core/vault/originals.py` vont échouer
5. **OAuth Gmail** configuré avec un projet GCP supprimé
6. **92 fichiers modifiés/non suivis** dans Git — risque de confusion
7. **Aucun snapshot VirtualBox** détecté

### ⚠️ Ce qui peut empêcher les tests sur téléphone

- Les URLs Cloud Run hardcodées dans l'APK / le code frontend ne fonctionnent plus
- `REDIS_URL` externe peut poser problème de latence ou de coût
- Les appels à Vault/Karaoke peuvent planter

---

## 6. ACTIONS REQUISES AVANT REPRISE

### Priorité 1 — Sécurité VM
- [ ] Créer un snapshot VirtualBox depuis Windows

### Priorité 2 — Dépendances Python
- [ ] Installer : `pip install elevenlabs python-multipart python-jose`

### Priorité 3 — Configuration locale
- [ ] Modifier `.env` :
  - `REDIS_URL=redis://localhost:6379/0`
  - `BASE_URL=http://IP_LOCALE_VM:8000`
  - `VOICE_CALLBACK_URL=http://IP_LOCALE_VM:8000`
  - `IAWATCH_BACKEND_URL=http://IP_LOCALE_VM:8000` (ou supprimer)
  - `CLOUD_RUN_URL=http://IP_LOCALE_VM:8000` (ou supprimer)
  - Supprimer / mettre à jour `GOOGLE_OAUTH_CLIENT_ID` et `GOOGLE_OAUTH_CLIENT_SECRET`

### Priorité 4 — Code
- [ ] Désactiver/remplacer les appels GCS dans `luna_web.py` (karaoke drafts)
- [ ] Désactiver/remplacer les appels GCS dans `core/vault/originals.py`
- [ ] Mettre à jour les URLs hardcodées dans `luna_web.py`

### Priorité 5 — Git
- [ ] Nettoyer les fichiers modifiés/non suivis (commit ou stash)
- [ ] Vérifier que GitHub est bien synchronisé

### Priorité 6 — Tests
- [ ] Relancer `uvicorn luna_web:app --host 0.0.0.0 --port 8000`
- [ ] Tester Guardian depuis le téléphone via Wi-Fi
- [ ] Vérifier que Vault et Karaoke ne plantent pas

---

## 7. RÉSUMÉ

| Catégorie | État |
|-----------|------|
| Sauvegardes | Partiellement OK (snapshot VM manquant) |
| Redis | ✅ OK |
| Python / dépendances | ⚠️ 3 modules manquants |
| Démarrage serveur | ✅ OK |
| Dépendances GCP | 🔴 Présentes et actives |
| Configuration `.env` | 🔴 À corriger |
| Git | 🔴 À nettoyer |

**Verdict : 🔴 ENVIRONNEMENT NON PRÊT**

Une fois les actions Priorité 1 à 4 effectuées, l'environnement sera 🟢 prêt à reprendre le développement.
