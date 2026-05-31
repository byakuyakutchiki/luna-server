# DeepSeek — Guide autonomie GitHub

Ce fichier est ton point d'entrée. Suis-le à chaque livrable.

---

## Ton repo

```
/media/windows/Users/saint/Documents/Codex/2026-05-25/luna-server/
```

Sur Windows : `C:\Users\saint\Documents\Codex\2026-05-25\luna-server\`

---

## Workflow obligatoire — dans cet ordre exact

### Étape 1 — Sync

```bash
cd /media/windows/Users/saint/Documents/Codex/2026-05-25/luna-server
git checkout main
git pull origin main
```

### Étape 2 — Créer le fichier (OBLIGATOIRE avant git add)

Écris ton contenu dans le fichier. Vérifie qu'il existe :

```bash
ls docs/AGENTS_COLLABORATION/agents/TON_FICHIER.md
```

Si le fichier est absent → `ls: cannot access` → **le fichier n'existe pas, git add échouera**.

### Étape 3 — Vérifier avant de committer

```bash
git status
```

Le fichier doit apparaître en `Untracked files` ou `Changes not staged`.  
S'il n'apparaît pas → il n'a pas été créé → **refaire l'étape 2**.

### Étape 4 — Commit et push

```bash
git add docs/AGENTS_COLLABORATION/agents/TON_FICHIER.md
git commit -m "agent(DeepSeek): description courte"
git push origin main
```

### Étape 5 — Vérifier le push

```bash
git log --oneline -1
```

Ce hash doit apparaître sur `https://github.com/byakuyakutchiki/luna-server/commits/main`.  
**Pas de hash visible = pas livré.**

---

## Script raccourci (si le fichier existe déjà)

```bash
./push_agent.sh docs/AGENTS_COLLABORATION/agents/TON_FICHIER.md "message"
```

---

## Règles non-négociables

1. **Créer le fichier avant `git add`** — git ne peut pas ajouter un fichier qui n'existe pas
2. **Toujours depuis `main`** — ne jamais pousser sur une autre branche
3. **Toujours `git pull` avant `git push`** — évite les conflits
4. **Vérifier le hash sur GitHub** — c'est la seule preuve de livraison
5. **Ne pas simuler les commandes** — les exécuter réellement dans le terminal

---

## Si le push est refusé (rejected)

```bash
git pull --rebase origin main
git push origin main
```

---

## Livrables attendus Objectif 015

| Fichier | Statut |
|---|---|
| `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_VISIO_015.md` | ✅ Livré par Claude (22663d1) |
| `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_STT_SIMLI_COUNTER_AUDIT_014.md` | ❌ Manquant |

---

## Contact si bloqué

Indiquer à Ludovic : "Je suis bloqué à l'étape X — voici l'erreur exacte : [coller l'erreur]"  
Ne pas simuler une réussite.
