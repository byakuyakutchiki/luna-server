# Preuve d'état des services — SUPERVISOR-NEXT-MISSION-PLANNER-001-FIX

Date de vérification : 2026-07-17T17:47:00+02:00 (après redémarrage du test)

## Services systemd user

```
active
active
```

## Statut détaillé

● luna-agent-supervisor.service - Luna Agent Supervisor - cellule autonome multi-agents
     Loaded: loaded (/home/ludo/.config/systemd/user/luna-agent-supervisor.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-07-17 17:45:36 CEST; 2min 39s ago
   Main PID: 405579 (python3)
      Tasks: 1 (limit: 31187)
     Memory: 19.5M
        CPU: 4.178s
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/luna-agent-supervisor.service
             └─405579 /usr/bin/python3 -m luna_supervisor daemon

Jul 17 17:45:37 vbox luna-supervisor[405579]: === INSTRUCTIONS ===
Jul 17 17:45:37 vbox luna-supervisor[405579]: Tu ne dois PAS modifier directement de fichiers ni exécuter de commandes. Tu dois analyser le contexte et retourner UNIQUEMENT un JSON valide au format suivant:
Jul 17 17:45:37 vbox luna-supervisor[405579]: {"summary": "résumé de l'analyse", "decision": "execute|review|audit|complete|blocked", "requested_action": {"type": "read_files|edit_files|run_tests|build_debug|install_debug|collect_adb|commit_local|none", "parameters": {}}, "files_relevant": ["..."], "expected_result": "...", "requires_human_validation": false}
Jul 17 17:45:37 vbox luna-supervisor[405579]: Réponds uniquement par ce JSON, sans texte avant ou après. ...
Jul 17 17:45:58 vbox luna-supervisor[405579]: 2026-07-17 17:45:58,989 [INFO] luna_supervisor.supervisor: Décision agent: execute
Jul 17 17:45:58 vbox luna-supervisor[405579]: 2026-07-17 17:45:58,989 [INFO] luna_supervisor.supervisor: Validation humaine demandee sur action non destructive (read_files) -> needs_audit
Jul 17 17:45:58 vbox luna-supervisor[405579]: 2026-07-17 17:45:58,990 [INFO] luna_supervisor.action_executor: Exécution action: read_files
Jul 17 17:45:59 vbox luna-supervisor[405579]: 2026-07-17 17:45:59,040 [INFO] luna_supervisor.supervisor: Rapport AGENT_SHARED créé: /media/windows/Users/saint/Documents/Codex/AGENT_SHARED/SUPERVISOR-GIT-CLEANUP-PLAN-001_REPORT.md
Jul 17 17:45:59 vbox luna-supervisor[405579]: 2026-07-17 17:45:59,150 [INFO] luna_supervisor.supervisor: Planification suivante ignoree: auto_next=false
Jul 17 17:45:59 vbox luna-supervisor[405579]: 2026-07-17 17:45:59,151 [INFO] luna_supervisor.cli: Mission traitée avec succès: SUPERVISOR-GIT-CLEANUP-PLAN-001

---

● luna-mission-store.service - Luna Mission Store - service local de stockage des missions
     Loaded: loaded (/home/ludo/.config/systemd/user/luna-mission-store.service; enabled; preset: enabled)
     Active: active (running) since Wed 2026-07-15 18:46:55 CEST; 1 day 23h ago
   Main PID: 1143 (python3)
      Tasks: 1 (limit: 31187)
     Memory: 29.8M
        CPU: 21.957s
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/luna-mission-store.service
             └─1143 /usr/bin/python3 -m luna_supervisor.mission_store

Jul 17 17:44:37 vbox luna-mission-store[1143]: 2026-07-17 17:44:37,008 [INFO] __main__: Mission assigned: TEST-NEXT-PLANNER-FIX-001 -> runner luna-vm-01
Jul 17 17:44:37 vbox luna-mission-store[1143]: 2026-07-17 17:44:37,008 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 17:44:37] "POST /next-job HTTP/1.1" 200 -
Jul 17 17:44:51 vbox luna-mission-store[1143]: 2026-07-17 17:44:51,799 [INFO] __main__: Mission report: TEST-NEXT-PLANNER-FIX-001 -> needs_audit
Jul 17 17:44:51 vbox luna-mission-store[1143]: 2026-07-17 17:44:51,799 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 17:44:51] "POST /report HTTP/1.1" 200 -
Jul 17 17:44:51 vbox luna-mission-store[1143]: 2026-07-17 17:44:51,840 [INFO] __main__: Mission upsert: SUPERVISOR-GIT-CLEANUP-PLAN-001
Jul 17 17:44:51 vbox luna-mission-store[1143]: 2026-07-17 17:44:51,841 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 17:44:51] "POST /create HTTP/1.1" 200 -
Jul 17 17:45:36 vbox luna-mission-store[1143]: 2026-07-17 17:45:36,517 [INFO] __main__: Mission assigned: SUPERVISOR-GIT-CLEANUP-PLAN-001 -> runner luna-vm-01
Jul 17 17:45:36 vbox luna-mission-store[1143]: 2026-07-17 17:45:36,518 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 17:45:36] "POST /next-job HTTP/1.1" 200 -
Jul 17 17:45:59 vbox luna-mission-store[1143]: 2026-07-17 17:45:59,146 [INFO] __main__: Mission report: SUPERVISOR-GIT-CLEANUP-PLAN-001 -> needs_audit
Jul 17 17:45:59 vbox luna-mission-store[1143]: 2026-07-17 17:45:59,146 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 17:45:59] "POST /report HTTP/1.1" 200 -

## Interprétation

- `luna-agent-supervisor.service` : actif après redémarrage.
- `luna-mission-store.service` : actif en continu.
