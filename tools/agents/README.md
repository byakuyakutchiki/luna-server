# Runner local agents Luna

> Objectif 012 — Canal de decision agents  
> Pas de serveur. Pas de cout. GitHub = salle de coordination.

---

## Principe

Chaque agent travaille depuis son propre environnement local.  
GitHub est la seule source de verite.  
Le runner fait une boucle simple : `pull -> lire queue -> travailler -> commit/push -> attendre`.

## Fichiers

| Fichier | Role |
|---|---|
| `agent_loop.ps1` | Script PowerShell du runner (Windows) |
| `agent_loop.sh` | Script Bash du runner (Linux/macOS) |
| `agent_loop.config.example.json` | Configuration exemple |
| `../../docs/AGENTS_COLLABORATION/QUEUE.md` | File de taches partagee |
| `../../docs/AGENTS_COLLABORATION/AGENT_CHANNEL.md` | Journal des actions agents |

## Prerequis

- **Windows** : Windows PowerShell 5.1+ ou PowerShell 7+ (`pwsh`)
- **Linux/macOS** : Bash + Python 3 + Git
- Git installe et configure (`git config user.name` / `user.email`)
- Acces en ecriture au depot `luna-server`

## Lancer le runner — Windows (PowerShell)

```powershell
# Kimi
.\agent_loop.ps1 -Agent Kimi -IntervalSeconds 120

# DeepSeek
.\agent_loop.ps1 -Agent DeepSeek

# Mode simulation (aucun commit/push)
.\agent_loop.ps1 -Agent Kimi -DryRun

# Repo personnalise
.\agent_loop.ps1 -Agent DeepSeek -RepoPath "C:\Users\moi\luna-server"
```

## Lancer le runner — Linux/macOS (Bash)

```bash
# Kimi
./agent_loop.sh --agent Kimi --interval 120

# DeepSeek
./agent_loop.sh --agent DeepSeek

# Mode simulation (aucun commit/push)
./agent_loop.sh --agent Kimi --dry-run

# Repo personnalise
./agent_loop.sh --agent Codex --repo-path /home/moi/luna-server
```

## Cycle du runner

1. `git pull --ff-only`
2. Lit `QUEUE.md` et extrait les taches `open` correspondant a l'agent
3. Filtre par niveau de decision autorise :
   - **0** = audit, avis, documentation, tests non destructifs
   - **1** = petite correction faible risque, texte, libelle
   - **2** = validation Ludovic obligatoire
   - **3** = validation Ludovic + integration finale (prod, paiement, SMS/email/appel reel, secrets, base de donnees)
4. Affiche la premiere tache eligible
5. Deplace la tache dans `IN PROGRESS`
6. L'agent execute son travail **localement** (audit, correction, test)
7. Ecrit un resultat court dans `AGENT_CHANNEL.md`
8. `git add + commit + push`
9. Attend `IntervalSeconds` (defaut 180s)
10. Recommence

## Regles absolues

- **Jamais** de deploiement Cloud Run automatique.
- **Jamais** d'action sensible reelle (SMS, email, appel, paiement, reservation).
- **Jamais** de modification de secrets, Google Cloud, base de donnees sans validation.
- **Jamais** de suppression de donnees.
- **Jamais** de refonte graphique validee sans validation.
- En cas de doute : ecrire dans `DECISIONS_PENDING.md` et attendre Ludovic.

## Niveaux autorises par agent

| Agent | Niveaux autorises |
|---|---|
| Kimi | 0, 1 |
| DeepSeek | 0 |
| Codex | 0, 1 |
| Claude | 0, 1, 2 (3 = validation Ludovic quand meme) |

## Format de sortie dans AGENT_CHANNEL.md

```
---
Agent : Kimi
Heure : 2026-05-27 14:30:00
Tache : TASK-011-KIMI-UX-REAL-TEST
Type : avis / blocage / proposition / validation / risque
Resume : 5 lignes max
Fichier concerne : static/index.html
Risque : faible
Decision Ludovic requise : non
Action proposee : Ajouter _showConfirm() avant startVoiceCall()
```

## Arreter le runner

`Ctrl+C` dans le terminal.

## V1 vs V2

**V1 (actuelle)** : semi-automatique. Le runner lit la queue, prepare le contexte, ecrit les resultats, mais l'agent execute son travail via son environnement local (Kimi CLI, VS Code, etc.).

**V2 (futur)** : automatisation complete avec :
- Kimi CLI pour audits UX/app
- Scripts Playwright pour tests boutons
- Tests backend non destructifs
- Generation automatique de rapports courts

---

*Document produit par Kimi Code CLI — 2026-05-27*
