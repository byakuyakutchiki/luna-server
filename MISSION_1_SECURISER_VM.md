# MISSION 1 — SÉCURISER LA VM AVANT TOUTE MODIFICATION

> Date : 2026-07-08  
> Objectif : sécuriser le travail actuel (Git + snapshot VirtualBox) avant de reprendre le développement.

---

## ⚠️ RÈGLE STRICTE

**Aucune modification de code ne sera faite tant que le snapshot VirtualBox n'est pas créé.**

---

## 1. ÉTAT DU DÉPÔT GIT

### Branche actuelle
- **Branche locale :** `feature/phase-a-auth-apk`
- **Commit actuel :** `5fd1322` — `docs(audit): validation terrain Guardian vocale + appel Twilio`
- **Branche trackée sur origin :** **NON** (branche purement locale)

### Fichiers non sauvegardés sur GitHub

| Type | Quantité | Détail |
|------|----------|--------|
| Fichiers modifiés (modified) | **47** | Code source, configs, builds Android |
| Fichiers ajoutés non suivis (untracked) | **45** | Nouveaux fichiers, rapports, backups |
| Fichiers supprimés | **1** | `static/luna-proprio.apk` |

### Commits non poussés
- La branche `feature/phase-a-auth-apk` n'a **pas de remote**.
- La branche `feature/pwa` (proche) est **5 commits en avance** sur `origin/feature/pwa`.
- Cela signifie qu'il y a du **travail local important non sauvegardé sur GitHub**.

---

## 2. CE QUI DOIT ÊTRE SAUVEGARDÉ

### 🔴 Modifications critiques à ne pas perdre

Ces fichiers contiennent du vrai travail de développement :

- `core/actions/confirmation.py`
- `core/actions/dispatcher.py`
- `core/actions/models.py`
- `core/actions/quota_guard.py`
- `core/exploitant/routes.py`
- `core/form_filler/engine.py`
- `core/form_filler/routes.py`
- `core/guardian/profiles.py`
- `core/instructions/executor.py`
- `core/memory/memory_manager.py`
- `core/memory/redis_client.py`
- `core/perception/detector.py`
- `core/rooms/manager.py`
- `core/safety/voice_emergency.py`
- `core/social/redis_ops.py`
- `core/social/routes.py`
- `core/vault/redis_ops.py`
- `core/vault/routes.py`
- `core/world/redis_ops.py`
- `core/world/routes.py`
- `integrations/email/email_client.py`
- `integrations/email/gmail_client.py`
- `integrations/openai/realtime_bridge.py`
- `integrations/openai/web_voice_bridge.py`
- `static/guardian.html`
- `deploy.sh`
- `docker-entrypoint.sh`
- `requirements.txt`
- `requirements-cloudrun.txt`

### ⚠️ Fichiers à ignorer / ne pas commiter

Ces fichiers sont des artefacts de build ou des backups locaux :

- `android-app/build/apk/base.apk`
- `android-app/build/classes.dex`
- `android-app/build/compiled_res.zip`
- `android-app/build/obj/.../*.class`
- `android-app/build/sources.txt`
- `static/luna-proprio.apk` (supprimé)
- `static/index.html.bak-guardian-voice`
- `luna_web.py.bak-voice-emergency`
- `migration_backup/` (déjà un backup local)
- Tous les rapports d'audit (`RAPPORT_*.md`, `PLAN_*.md`, `audit_*.md`)

### ❓ Fichiers à décider

- `.env.example`, `.dockerignore`, `.gitignore`, `Dockerfile`, `CLAUDE.md` : vérifier s'ils contiennent des modifications intentionnelles.
- Nouveaux fichiers comme `core/vault/originals.py`, `Dockerfile.exploitant`, `docker-compose.exploitant.yml`, `build-exploitant.sh` : sont-ils intentionnels ?

---

## 3. OPTIONS DE SAUVEGARDE GIT

### Option A — Commit + push sur une branche dédiée (recommandé)

Avantages :
- Travail sécurisé sur GitHub
- Historique propre
- Facile de revenir en arrière

Commandes proposées (à exécuter après le snapshot VM) :

```bash
# 1. Vérifier le .gitignore actuel
 cat .gitignore

# 2. S'assurer que les fichiers de build Android sont ignorés
# Si ce n'est pas le cas, ajouter :
# android-app/build/
# *.apk
# *.bak-*
# migration_backup/
# *.bak

# 3. Ajouter les fichiers intentionnels
 git add -A

# 4. Faire un commit explicite
 git commit -m "WIP: reprise developpement local avant migration GCP"

# 5. Créer une branche sur GitHub
 git push -u origin feature/phase-a-auth-apk
```

### Option B — Stash complet

Avantages :
- Rapide
- Pas besoin de décider maintenant ce qui est important

Inconvénient :
- Moins visible, risque d'oubli

Commandes proposées :

```bash
# Stash tout (modifiés + untracked)
 git stash push -u -m "Sauvegarde avant reprise developpement local"

# Plus tard, pour restaurer :
# git stash pop
```

### Option C — Commit sur une branche temporaire + push

Le plus sûr si tu ne veux pas polluer la branche actuelle :

```bash
 git checkout -b backup/avant-reprise-local
 git add -A
 git commit -m "backup: etat avant reprise developpement local"
 git push -u origin backup/avant-reprise-local
 git checkout feature/phase-a-auth-apk
```

---

## 4. CRÉATION DU SNAPSHOT VIRTUALBOX (À FAIRE SUR WINDOWS)

### Étape 1 — Ouvrir VirtualBox sur Windows

1. Lancer **Oracle VM VirtualBox Manager** depuis Windows.
2. Identifier la VM Debian (probablement nommée "Debian").

### Étape 2 — Créer le snapshot

1. Cliquer sur la VM Debian.
2. Cliquer sur l'onglet **Snapshots** (en haut à droite).
3. Cliquer sur le bouton **Take** (ou **Prendre un instantané**).
4. Nommer le snapshot :  
   `snap-2026-07-08-avant-reprise-dev-local`
5. Ajouter une description :  
   `Snapshot avant migration Luna vers environnement 100% local. Google Cloud vide, facturation désactivée.`
6. Cliquer sur **OK**.

### Étape 3 — Vérifier le snapshot

1. Attendre que la création soit terminée.
2. Confirmer que le snapshot apparaît dans la liste.

---

## 5. PLAN D'ACTION IMMÉDIAT

### ✅ À faire maintenant (sur Windows)

1. Ouvrir VirtualBox.
2. Créer le snapshot `snap-2026-07-08-avant-reprise-dev-local`.
3. Confirmer que le snapshot est bien créé.

### ⏳ À faire ensuite (dans la VM, après validation du snapshot)

1. Choisir une option Git (A, B ou C ci-dessus).
2. Exécuter les commandes correspondantes.
3. Vérifier sur GitHub que les commits/push sont bien arrivés.

### 🚫 À NE PAS FAIRE AVANT

- Modifier `.env`
- Installer des dépendances Python
- Modifier le code
- Supprimer des fichiers
- Lancer des tests destructeurs

---

## 6. RÉCAPITULATIF

| Étape | Statut |
|-------|--------|
| Vérifier GitHub | ✅ Fait — branche non trackée, travail local non sauvegardé |
| Identifier fichiers critiques | ✅ Fait |
| Proposer stratégie Git | ✅ Fait |
| Créer snapshot VirtualBox | 🔴 **À faire sur Windows** |
| Commit/push ou stash | ⏳ Après snapshot |

---

**Prochaine action requise :** créer le snapshot VirtualBox depuis Windows, puis revenir ici pour exécuter la sauvegarde Git choisie.
