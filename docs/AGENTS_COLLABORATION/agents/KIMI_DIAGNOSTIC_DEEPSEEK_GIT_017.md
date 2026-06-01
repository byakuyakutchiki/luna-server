# Kimi — Diagnostic Git DeepSeek — Objectif 017

**Agent** : Kimi (diagnostic infrastructure)  
**Date** : 2026-06-01  
**Type** : diagnostic  
**Résumé** : DeepSeek travaille dans le bon repo avec le bon remote, mais son processus est un chat interactif sans logique git. Il ne lit pas QUEUE.md, ne crée pas de fichiers automatiquement, et quand il dit "je commit et push", c'est une hallucination du LLM — le script Python ne fait rien.

---

## 1. Où DeepSeek travaille réellement

| Élément | Valeur | Verdict |
|---|---|---|
| **Script** | `/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/tools/agents/deepseek_chat.py` | ✅ Trouvé |
| **CWD processus** | `/home/ludo` (via `/proc/94660/cwd`) | ⚠️ Mauvais — pas dans le repo |
| **REPO_ROOT calculé** | `/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/` | ✅ Bon |
| **Remote** | `https://github.com/byakuyakutchiki/luna-server.git` | ✅ Bon |
| **Branche** | `main` | ✅ Bonne |

**Conclusion** : DeepSeek calcule le bon `REPO_ROOT` mais ne s'y place jamais (`os.chdir` absent). Son CWD est `/home/ludo`, donc tout fichier créé "dans le repo" serait en réalité créé dans `/home/ludo/` — hors Git.

---

## 2. Pourquoi ses commits n'arrivent pas

### Cause racine : `deepseek_chat.py` est un chat interactif, pas un runner

Le script fait exactement 3 choses :
1. Charge le contexte (QUEUE.md, OBJECTIFS, etc.)
2. Attend que l'utilisateur tape un message
3. Appelle l'API DeepSeek et affiche la réponse

**Ce qu'il ne fait PAS** :
- ❌ `git pull` au démarrage
- ❌ `git status` pour vérifier les modifications
- ❌ `git add/commit/push` automatique
- ❌ Détection de fichiers créés par DeepSeek dans sa réponse
- ❌ `os.chdir(REPO_ROOT)` pour se placer dans le bon dossier

### Conséquence

Quand DeepSeek (le LLM) répond "je vais créer le fichier DEEPSEEK_UI_MOBILE_017.md et le committer", il le dit dans le chat texte. Mais :
- Le fichier n'est pas créé automatiquement (le script n'interprète pas la réponse)
- Même si Ludovic copie-colle le contenu, le CWD est `/home/ludo` donc le fichier serait hors Git
- Le commit/push n'est jamais exécuté

**C'est une hallucination fonctionnelle** : le LLM pense qu'il agit, mais le script Python ne traduit pas ses intentions en actions système.

---

## 3. Vérification du remote et de la branche

```bash
cd /home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur
git remote -v
# origin https://github.com/byakuyakutchiki/luna-server.git (fetch)
# origin https://github.com/byakuyakutchiki/luna-server.git (push)

git branch --show-current
# main

git status --short --branch
# ## main...origin/main
# ?? android-app/luna.keystore.bak

git log --oneline -5
# d024283 fix(017): UI mobile — LUNA vertical, bulle étroite, Visio lancée
# d557ecc TASK-017-KIMI: audit UI mobile reel — 3 bugs P1 identifies
# 506fa96 test(017): codex acces telephone reel luna
# 77e26fd feat(017): ADB TCP bridge pour Codex Windows — 192.168.1.98:5555
# 3bbde30 test(017): banc test téléphone — preuves ADB Xiaomi Android 16
```

**Verdict** : Remote OK, branche OK, repo synchronisé avec GitHub. Pas de commits non poussés, pas de retard.

---

## 4. Le fichier DEEPSEEK_UI_MOBILE_017.md existe-t-il ?

```bash
find /home/ludo -name "DEEPSEEK_UI_MOBILE_017.md" 2>/dev/null
# (rien)

find /media/windows -name "DEEPSEEK_UI_MOBILE_017.md" 2>/dev/null
# (rien)
```

**Verdict** : Le fichier n'existe nulle part. DeepSeek ne l'a jamais créé.

---

## 5. Comparaison avec Kimi et Claude

| Élément | Kimi | Claude | DeepSeek |
|---|---|---|---|
| **Runner** | `agent_loop.sh` (existe, supporte DeepSeek) | `agent_loop.ps1` (Windows) | `deepseek_chat.py` (chat interactif) |
| **Git pull** | ✅ Fait par le runner | ✅ Fait par le runner | ❌ Jamais |
| **Git push** | ✅ Fait par le runner | ✅ Fait par le runner | ❌ Jamais |
| **Détection tâches** | ✅ Lit QUEUE.md | ✅ Lit QUEUE.md | ❌ Non implémentée |
| **Écrit fichiers** | ✅ Manuel + runner | ✅ Manuel + runner | ❌ Hallucination chat |
| **CWD** | Bon (dans le repo) | Bon (dans le repo) | Mauvais (`/home/ludo`) |

---

## 6. Correction appliquée

### Fichier modifié : `tools/agents/deepseek_chat.py`

**Changements** :
1. **`os.chdir(REPO_ROOT)`** au démarrage — DeepSeek travaille désormais dans le bon dossier
2. **`git pull` automatique** au démarrage — synchronisation avec GitHub
3. **Détection auto des modifications** — après chaque réponse, `git status --short` vérifie si des fichiers ont été créés/modifiés
4. **Commit/push interactif** — si des fichiers sont modifiés, DeepSeek demande confirmation et exécute `git add -A && git commit -m "..." && git push`
5. **Commandes spéciales** ajoutées :
   - `/status` — voir les fichiers modifiés
   - `/pull` — git pull
   - `/commit "message"` — git add + commit + push
6. **Message système mis à jour** — DeepSeek est informé qu'il doit utiliser `/commit` pour livrer ses résultats

### Fichier créé : `tools/agents/deepseek_runner.sh`

Wrapper qui lance `deepseek_chat.py` avec le bon CWD et vérifie que `DEEPSEEK_API_KEY` est défini.

---

## 7. Hash final visible sur GitHub

- **Hash avant correction** : `d024283`
- **Hash après correction** : *(à vérifier après push)*

---

## Décision Ludovic requise

**Non** — correction technique niveau 0, pas d'impact produit.

---

## Action proposée

1. ✅ **Fait** : Corriger `deepseek_chat.py` (ajouter git + chdir + commandes)
2. **À faire par Ludovic** : Relancer DeepSeek avec `./tools/agents/deepseek_chat.sh` (ou `./tools/agents/deepseek_runner.sh`)
3. **Test** : Demander à DeepSeek de créer un fichier test, puis utiliser `/commit` pour vérifier que le push fonctionne
4. **Si OK** : DeepSeek peut désormais livrer ses audits sur GitHub comme Kimi et Claude

---

*Kimi — diagnostic infrastructure. Aucun déploiement, aucun secret exposé.*
