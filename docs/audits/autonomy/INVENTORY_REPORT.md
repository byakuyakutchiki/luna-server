# INVENTORY_REPORT — Reprise de session autonomie Luna

Date de l'audit : 2026-07-15T19:30:00+02:00  
Auditeur : Kimi (session nouvelle, aucun contexte mémoire initial)  
Dépôt principal : `/home/ludo/luna-server`  
Contrainte : aucune modification de composant effectuée pendant l'audit.

---

## 1. Dépôt Git courant

| Élément | Valeur |
|---------|--------|
| Chemin | `/home/ludo/luna-server` |
| Branche active | `automation/guardian-autonomous-001` |
| Commit HEAD | `6d9796b` — `feat(runner): Luna Local Runner minimal pour n8n` |
| Remote | `origin` présent, HEAD -> `origin/main` |
| Worktrees | `/home/ludo/luna-server` (HEAD actuel) ; `/home/ludo/luna-server-pwa-base-5b2fc0f-v3` (`feature/pwa-guardian-minimal-v2`, commit `24dc53f`) |
| Stash | Aucun stash listé |

### Branches locales significatives
- `automation/guardian-autonomous-001` *(active)*
- `automation/guardian-runner`
- `feature/pwa`, `feature/pwa-guardian-minimal-v2`
- `feature/phase-a-auth-apk`, `feature/sprint-a-ux`
- `fix/guardian-voice-context-on-stable-ui`
- `audit/autonomy-supervisor-pack-2026-07-14`
- `main`, `stable/frontend-reference-2026-07-05`

### Modifications locales (git status --short)
12 fichiers/répertoires non suivis, **aucun fichier modifié-tracké** :

```
?? ..env.runner.swp
?? .env.bak.20260709-105127
?? .env.bak.iristest
?? .env.supervisor
?? config/
?? data/luna_missions.db
?? docs/AGENT_EXCHANGE/
?? docs/ANDROID_REFERENTIEL/
?? docs/audits/
?? tools/agent_bridge/
?? tools/luna_runner/adb_wifi_reconnect.sh
?? tools/luna_supervisor/
```

**Observations critiques :**
- `tools/luna_supervisor/` est **entièrement non versionné** (code autonomie non commit).
- `tools/luna_runner/config.py` est tracké modifié dans le worktree mais apparaît dans le `git status` comme modifié (présent dans les rapports AGENT_SHARED comme fichier workspace_dirty).
- `android-app/build/` contient des artefacts build non suivis mais physiquement présents.

---

## 2. Dossiers AGENT_SHARED et docs/audits

### AGENT_SHARED externe (partagé Windows/Linux)
Chemin : `/media/windows/Users/saint/Documents/Codex/AGENT_SHARED`
- Monté et accessible (vboxsf, root:vboxsf).
- Contient 38 fichiers de rapports, checklist, roadmap, inbox/outbox.
- Rapports récents : `TEST-AUDIT-NEEDS-AUDIT-001_REPORT.md`, `SUPERVISOR-AUDIT-DECISION-FIX-001_REPORT.md`, `SUPERVISOR-GIT-CLEANUP-PLAN-001_REPORT.md`, etc.

### docs/audits/autonomy (interne au dépôt)
Chemin : `/home/ludo/luna-server/docs/audits/autonomy/`
- `README.md` — pack audit externe.
- `agent-shared/` — rapports de missions, roadmap, checklist, état courant (13 fichiers).

### docs/AGENT_EXCHANGE
- `inbox_codex/`, `inbox_deepseek/`, `inbox_kimi/`
- `reports_codex/`, `reports_deepseek/`, `reports_kimi/`
- `locks/`, `shared_context/`

---

## 3. Outils et scripts

### Luna Supervisor (`tools/luna_supervisor/`)
Fichiers source (~3 772 lignes Python) :

| Fichier | Rôle |
|---------|------|
| `supervisor.py` | Orchestration complète poll → agent → exécution → rapport |
| `mission_store.py` | API Flask SQLite de stockage des missions (remplace n8n Data Table) |
| `mission_queue.py` | Injection de missions via webhook n8n (`create-from-prompt`, `submit`) |
| `budget.py` | Gouverneur de budget journalier/mission |
| `routing.py` | Décision de routage agent selon contexte/budget |
| `agent_caller.py` | Appels Kimi CLI, DeepSeek API, OpenAI API |
| `action_executor.py` | Exécution contrôlée des actions (read/edit/tests/build/adb/commit/report) |
| `context_builder.py` | Construction du contexte minimal envoyé aux agents |
| `cli.py` | Commandes `health`, `poll-once`, `run-once`, `dry-run`, `daemon`, `status`, `stop`, `morning-report` |
| `config.py` | Chargement `.env.supervisor` + `.runner_config.json` |
| `morning_report.py` | Rapport matinal sans appel IA |
| `tests_audit_decision_mapping.py` | Tests unitaires mapping `decision=audit` |
| `tests_budget_governor.py` | Tests unitaires budget |
| `systemd/luna-agent-supervisor.service` | Unité systemd du superviseur |

### Luna Local Runner (`tools/luna_runner/`)
- `runner.py` — diagnostic ADB et collecte de preuves.
- `actions.py` — actions ADB/Git prédéfinies.
- `n8n_client.py` — client HTTP des webhooks n8n.
- `config.py`, `evidence.py`, `whitelist.py`, `cli.py`.

### Agent bridge (`tools/agent_bridge/`)
Scripts d'audit shell (non testés) :
- `audit_android_state.sh`, `audit_git.sh`, `audit_guardian_logs.sh`, `audit_guardian_service.sh`, `audit_permissions.sh`, `audit_server_logs.sh`, `sanitize_report.sh`.

---

## 4. Fichiers de configuration

### Versionnés
- `config/agent_budget_policy.yaml` — politique budget (limite temporaire `kimi=8/jour`, `total=10/jour`)
- `config/luna_mission_charter.yaml` — charte produit et garde-fous
- `tools/luna_supervisor/env.supervisor.example` — modèle de configuration
- `tools/luna_supervisor/systemd/luna-agent-supervisor.service`

### Non versionnés (locaux)
- `/home/ludo/luna-server/.env.supervisor` — secrets n8n + device ADB (configuré, `ANDROID_DEVICE_ID=192.168.1.62:5555`)
- `/home/ludo/luna-server/.runner_config.json` — probablement présent, fusionné par `config.py`
- `/home/ludo/luna-server/data/luna_missions.db` — base SQLite des missions
- `/home/ludo/luna-server/runs/supervisor-budget.json` — budget courant
- `/home/ludo/luna-server/runs/ai-budget-ledger.json` — ledger des appels IA

### Fichiers temporaires/indésirables
- `/home/ludo/luna-server/..env.runner.swp` — swap Vim/Neovim daté du 2026-07-12 19:53

---

## 5. Workflows n8n

### Cloud n8n
- Instance : `ludo971.app.n8n.cloud`
- Webhooks utilisés :
  - `POST /webhook/luna-mission-create`
  - `POST /webhook/luna-runner-next-job`
  - `POST /webhook/luna-runner-report`

### Export JSON local (`tools/luna_supervisor/n8n_workflows/`)
- `luna_mission_create.json` — validation + appel mission_store `/create`
- `luna_runner_next_job.json` — proxy vers mission_store `/next-job`
- `luna_runner_report.json` — proxy vers mission_store `/report`

**Important :** les exports locaux ont `"active": false`. Cela ne reflète pas forcément l'état cloud ; les logs journald montrent des appels cloud actifs réussis.

---

## 6. Services systemd

| Service | État | Fichier unité | PID |
|---------|------|---------------|-----|
| `luna-agent-supervisor.service` | `active (running)` | `~/.config/systemd/user/luna-agent-supervisor.service` | 1246 |
| `luna-mission-store.service` | `active (running)` | `~/.config/systemd/user/luna-mission-store.service` | 1143 |

### Dépendances
- `luna-agent-supervisor.service` référence `adb-wifi-reconnect.service` (Wants/After), mais ce service n'est pas listé comme actif.

---

## 7. Processus et nohup

### Processus Luna actifs
```
ludo  969  python3 -m uvicorn luna_web:app --host 0.0.0.0 --port 8000
ludo 1143  python3 -m luna_supervisor.mission_store
ludo 1246  python3 -m luna_supervisor daemon
```

### nohup
- Aucun processus `nohup` détecté.

---

## 8. Ports ouverts et réseau

| Port | Protocole | Processus | Usage |
|------|-----------|-----------|-------|
| 8000 | TCP | `python3` (pid 969) | Serveur web Luna (uvicorn) |
| 9876 | TCP localhost | `python3` (pid 1143) | mission_store Flask |
| 5678 / 5679 | TCP localhost | `node` (pid 1119) | n8n (webhook/API) |
| 5037 | TCP localhost | `adb` (pid 1178) | ADB server |
| 22, 80, 139, 445, 631, 3306, 5432, 6379, 3389, 5680, 8080, 8090, 8444, 9000, 9443 | — | — | Services système habituels |

---

## 9. Logs utiles

| Source | Chemin / Commande | État |
|--------|-------------------|------|
| Superviseur systemd | `journalctl --user -u luna-agent-supervisor.service` | Actif, rotation au boot |
| Mission store systemd | `journalctl --user -u luna-mission-store.service` | Actif |
| Logs Kimi Code | `~/.kimi-code/logs/kimi-code.log` | Présent |
| n8n event log | `~/.n8n/n8nEventLog*.log` | Présent mais tourné |
| ADB logcat | `adb logcat` | Accessible, pas de sortie récente filtrée |

---

## 10. Synthèse de l'inventaire

- **Superviseur** : code complet, non versionné, services actifs.
- **Mission store** : service actif, API `/health` OK, DB SQLite à `/home/ludo/luna-server/data/luna_missions.db`.
- **ADB** : device `192.168.1.62:5555` visible, WiFi, modèle `LLY-NX1`, Android 16.
- **n8n** : cloud actif, webhooks appelés avec succès.
- **Git** : branche autonomie active, **workspace non propre** (12 éléments non suivis dont tout le superviseur).
- **Risque immédiat** : perte du code superviseur si crash/reset avant commit ; budget temporaire élevé ; commande utilisateur `luna-mission` inexistante.
