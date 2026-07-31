# AUTONOMY_STATUS — État de l'autonomie Luna / Guardian / Supervisor

Date : 2026-07-15T19:30:00+02:00  
Statuts utilisés : `OK_PROUVE`, `A_VERIFIER`, `BUG_CONFIRME`, `EN_CORRECTION`, `NEEDS_AUDIT`, `BLOCKED`.

---

## Phase 2 — État du superviseur

### Architecture globale

Le superviseur est une cellule autonome multi-agents : `n8n → mission_store → supervisor → agent_caller → action_executor → rapport n8n + AGENT_SHARED`.

### Classification par composant

| Composant | Fichier(s) | Statut | Preuve / Justification |
|-----------|------------|--------|------------------------|
| **supervisor.py** — orchestration | `tools/luna_supervisor/supervisor.py` | **OK_PROUVE** | Cycle poll/run/rapport testé (`TEST-AUDIT-NEEDS-AUDIT-001`), mapping `audit → needs_audit` corrigé et validé. |
| **mission_store.py** — stockage local | `tools/luna_supervisor/mission_store.py` | **OK_PROUVE** | Service systemd actif, API `/health` OK, endpoints `/create`, `/next-job`, `/report` fonctionnels (logs journald 200). |
| **Scheduler / poll** — boucle daemon | `tools/luna_supervisor/cli.py::cmd_daemon` | **OK_PROUVE** | `luna-agent-supervisor.service` actif, poll toutes les 1800 s, gestion des erreurs consécutives. |
| **Dispatcher** — `decide_agent` + `routing.py` | `tools/luna_supervisor/routing.py` | **NEEDS_AUDIT** | Logique plausible mais jamais testée en condition réelle avec itérations multiples ; fallback Kimi pour tous les rôles si DeepSeek/OpenAI indisponibles. |
| **Budget manager** — `BudgetGovernor` | `tools/luna_supervisor/budget.py` | **OK_PROUVE*** | Politique YAML chargée, reset journalier fonctionnel, gouverneur d'état calculé. *Test unitaire `test_2_budget_100_percent_blocks` échoue car daté (2026-07-12 vs aujourd'hui). |
| **Mission queue / entrypoint** | `tools/luna_supervisor/mission_queue.py` | **NEEDS_AUDIT** | Le module existe (`create-from-prompt`, `submit`), mais **n'est pas exposé comme commande `luna-mission`** ; `__main__.py` pointe sur `cli.py`, pas `mission_queue.py`. |
| **Rapport automatique AGENT_SHARED** | `supervisor.py::_write_agent_shared_report` | **OK_PROUVE** | Rapports générés et enrichis (services, missions, budget) confirmés par `TEST-AUDIT-NEEDS-AUDIT-001_REPORT.md`. |
| **Agent caller — Kimi** | `tools/luna_supervisor/agent_caller.py::KimiCaller` | **OK_PROUVE** | Utilisé avec succès pour TEST-AUDIT-NEEDS-AUDIT-001. |
| **Agent caller — DeepSeek** | `agent_caller.py::DeepSeekCaller` | **A_VERIFIER** | Nécessite `DEEPSEEK_API_KEY` ; non testé dans les logs récents. |
| **Agent caller — OpenAI/Codex** | `agent_caller.py::OpenAICaller` | **A_VERIFIER** | Nécessite `OPENAI_API_KEY` ; non testé. |
| **Watchdog** — verrou + erreurs consécutives | `supervisor.py::acquire_lock/release_lock`, `cli.py::cmd_daemon` | **OK_PROUVE** | Verrou `.supervisor.lock` fonctionnel ; arrêt après 3 erreurs consécutives. |
| **Gestion NEEDS_AUDIT** | `supervisor.py::_determine_final_status` + `_process_mission` | **OK_PROUVE** | 7 tests unitaires passent ; preuve fonctionnelle avec TEST-AUDIT-NEEDS-AUDIT-001. |
| **Action executor** | `tools/luna_supervisor/action_executor.py` | **NEEDS_AUDIT** | Garde-fous présents (branche `automation/*`, zones protégées, mots interdits commit), mais `build_debug`, `install_debug`, `commit_local` n'ont pas été testés en vrai. |
| **Context builder** | `tools/luna_supervisor/context_builder.py` | **OK_PROUVE** | Fournit Git, ADB, tests, historique, evidence_paths ; utilisé avec succès. |
| **Morning report** | `tools/luna_supervisor/morning_report.py` | **A_VERIFIER** | Présent, jamais exécuté dans les logs observés. |

### Problèmes superviseur identifiés

1. **Aucun code versionné** : `tools/luna_supervisor/` est entièrement non suivi. Perte potentielle en cas de reset.
2. **Commande utilisateur manquante** : pas d'exécutable `luna-mission` dans le PATH ; `__main__.py` ne route pas vers `mission_queue.py`.
3. **Service systemd mission-store absent du repo** : le fichier unité n'existe que dans `~/.config/systemd/user/`, pas dans `tools/luna_supervisor/systemd/`.
4. **Budget temporaire élevé** : `max_total_ai_calls_per_day: 10`, `kimi: 8/jour` avec note "session dev temporaire".
5. **Service `adb-wifi-reconnect.service` référencé mais non trouvé** dans systemd --user.

---

## Phase 3 — État du téléphone Android

### Appareil

| Élément | Valeur |
|---------|--------|
| Connectivité | ADB WiFi `192.168.1.62:5555` |
| État | `device` |
| Modèle | `LLY-NX1` (Honor) |
| Android | 16 |
| Serial | `A6KXVB4912001918` |
| WiFi | `SFR_52AF`, 192.168.1.62/24, RSSI -59 dBm |
| Batterie | 33 %, non branché, température 32 °C |

### Package `fr.yawatch.luna`

| Élément | Valeur |
|---------|--------|
| Installé | OUI |
| versionCode | 25 |
| versionName | `3.3.0-guardian-restore` |
| firstInstallTime | 2026-07-12 17:53:08 |
| lastUpdateTime | 2026-07-12 17:55:46 |

### Permissions

| Permission | État |
|------------|------|
| `RECORD_AUDIO` | granted=true |
| `ACCESS_FINE_LOCATION` | granted=true |
| `ACCESS_COARSE_LOCATION` | granted=true |
| `POST_NOTIFICATIONS` | granted=true |
| `MODIFY_AUDIO_SETTINGS` | granted=true |
| `FOREGROUND_SERVICE` / `_MICROPHONE` / `_DATA_SYNC` | granted=true |
| `CAMERA` | granted=false |
| `READ_MEDIA_IMAGES` | granted=false |
| `READ_MEDIA_VISUAL_USER_SELECTED` | granted=false |
| `REQUEST_INSTALL_PACKAGES` | déclarée |

### Processus / logs

- `adb shell ps | grep yawatch` : **aucun processus actif en premier plan**.
- `adb logcat -d -t 200 | grep -iE 'yawatch|guardian|luna|crash|fatal|exception'` : **aucune sortie**.
- Aucune activité Luna visible dans `dumpsys activity activities`.

| Composant | Statut | Commentaire |
|-----------|--------|-------------|
| Téléphone visible ADB | **OK_PROUVE** | device connecté, state=device |
| USB/WiFi ADB | **OK_PROUVE** | TCP 5555 stable |
| Package installé | **OK_PROUVE** | fr.yawatch.luna v3.3.0 code 25 |
| Permissions critiques | **OK_PROUVE** | micro + localisation OK ; caméra/images non accordées (acceptable pour l'instant) |
| App en cours d'exécution | **A_VERIFIER** | Non démarrée au moment de l'audit ; Guardian en arrière-plan non confirmé |
| Logs Guardian | **A_VERIFIER** | Aucun log filtré récent ; nécessite un audit ciblé avec démarrage contrôlé |

---

## Phase 4 — État n8n

### Instance

- Cloud `ludo971.app.n8n.cloud`.
- Processus local `node` (pid 1119) sur les ports 5678/5679 (probablement tunnel ou worker local).

### Workflows

| Workflow | Webhook | État export local | Observé actif |
|----------|---------|-------------------|---------------|
| Luna Mission Create | `/webhook/luna-mission-create` | `active: false` | OUI (logs POST /create 200) |
| Luna Runner Next Job | `/webhook/luna-runner-next-job` | `active: false` | OUI (logs POST /next-job 200) |
| Luna Runner Report | `/webhook/luna-runner-report` | `active: false` | OUI (logs POST /report 200) |

### Workers / rôles IA

| Rôle | Worker réel | État |
|------|-------------|------|
| operator | Kimi CLI | OK_PROUVE |
| auditor | DeepSeek API (fallback Kimi) | A_VERIFIER |
| coordinator | OpenAI API (fallback Kimi) | A_VERIFIER |
| reviewer | Kimi CLI avec prompt reviewer | A_VERIFIER |

### Cohérence / points bloquants n8n

- **Aucune représentation locale à jour** : les exports JSON sont marqués inactifs.
- **Pas de workflow de validation humaine** : n8n ne gère pas explicitement `waiting_human_approval` ni de file d'approbation.
- **Pas de workflow de planification automatique** : pas de "next mission planner" dans n8n.

| Composant | Statut |
|-----------|--------|
| Webhooks cloud | **OK_PROUVE** |
| Proxy mission_store | **OK_PROUVE** |
| Workers DeepSeek/Codex | **A_VERIFIER** |
| Planificateur autonome n8n | **BLOCKED** *(manque)* |
| Workflow d'approbation humaine | **BLOCKED** *(manque)* |

---

## Phase 5 — État Git

| Élément | État |
|---------|------|
| Workspace propre | **NON** — 12 éléments non suivis |
| Branches | OK — branche autonomie active, multiples branches de référence |
| Stash | Aucun |
| Modifications non commitées | Aucune sur les fichiers trackés ; superviseur entier non tracké |
| Worktree PWA | `feature/pwa-guardian-minimal-v2`, commit `24dc53f`, hors scope autonomie |

### Synthèse Git

- Le code autonomie n'est **pas sous contrôle de version**.
- Aucun risque de conflit de merge immédiat (pas de modifications trackées non commitées).
- Action requise : `SUPERVISOR-GIT-CLEANUP-PLAN-001` (déjà proposé, statut `needs_audit`).

---

## Tableau récapitulatif global

| Domaine | OK_PROUVE | NEEDS_AUDIT | A_VERIFIER | BUG_CONFIRME | BLOCKED |
|---------|-----------|-------------|------------|--------------|---------|
| Superviseur | 9 | 3 | 3 | 0 | 0 |
| Téléphone | 4 | 0 | 2 | 0 | 0 |
| n8n | 2 | 0 | 2 | 0 | 2 |
| Git | 1 | 1 | 0 | 0 | 0 |

**Légende des bloquants n8n :** planificateur autonome + workflow d'approbation humaine absent.
