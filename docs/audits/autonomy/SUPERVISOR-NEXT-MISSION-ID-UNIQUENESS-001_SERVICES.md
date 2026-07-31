# Preuve d'état des services — SUPERVISOR-NEXT-MISSION-ID-UNIQUENESS-001

Date de vérification : 2026-07-17T18:16:00+02:00 (après redémarrage du test)

## Services systemd user

```
active
active
```

---

● luna-agent-supervisor.service - Luna Agent Supervisor - cellule autonome multi-agents
     Loaded: loaded (/home/ludo/.config/systemd/user/luna-agent-supervisor.service; enabled; preset: enabled)
     Active: active (running) since Fri 2026-07-17 18:15:05 CEST; 29s ago
   Main PID: 418874 (python3)
      Tasks: 26 (limit: 31187)
     Memory: 223.1M
        CPU: 6.934s
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/luna-agent-supervisor.service
             ├─418874 /usr/bin/python3 -m luna_supervisor daemon
             └─418893 kimi-code

Jul 17 18:15:05 vbox luna-supervisor[418874]: mission_id: SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898
Jul 17 18:15:05 vbox luna-supervisor[418874]: task_id: SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898
Jul 17 18:15:05 vbox luna-supervisor[418874]: role: operator
Jul 17 18:15:05 vbox luna-supervisor[418874]: objectif: separer fichiers a versionner / a ignorer / a ne jamais commit.
Jul 17 18:15:05 vbox luna-supervisor[418874]: === CONTEXTE ===
Jul 17 18:15:05 vbox luna-supervisor[418874]: {'mission_id': 'SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898', 'task_id': 'SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898', 'objective': 'separer fichiers a versionner / a ignorer / a ne jamais commit.', 'acceptance_criteria': [], 'iteration': 0, 'max_iterations': 1, 'history_summary': [], 'git': {'branch': 'automation/guardian-autonomous-001', 'status': ' M tools/luna_supervisor/next_mission_planner.py\n M tools/luna_supervisor/tests_next_mission_planner.py\n?? .env.supervisor\n?? docs/AGENT_EXCHANGE/\n?? docs/ANDROID_REFERENTIEL/\n?? docs/audits/\n?? tools/agent_bridge/\n?? tools/luna_runner/adb_wifi_reconnect.sh\n', 'diff': ' tools/luna_supervisor/next_mission_planner.py      | 75 ++++++++++++++++++----\n .../luna_supervisor/tests_next_mission_planner.py  | 33 ++++++++++\n 2 files changed, 96 insertions(+), 12 deletions(-)\n'}, 'adb': {'available': True, 'device_id': '192.168.1.62:5555', 'model': 'LLY-NX1', 'android_version': '16', 'state': 'device'}, 'tests': {'available': False}, 'last_result': {}, 'changed': {'files': ['tools/luna_supervisor/next_mission_planner.py', 'tools/luna_supervisor/tests_next_mission_planner.py'], 'new_errors_since_last': [], 'last_status': None, 'last_iteration': None}, 'errors_new': [], 'log_tail': [], 'evidence_paths': {'screenshot': None, 'ui_hierarchy': None, 'logcat': None, 'adb_devices': None}, 'requested_decision': 'final_decision_or_complete'}
Jul 17 18:15:05 vbox luna-supervisor[418874]: === INSTRUCTIONS ===
Jul 17 18:15:05 vbox luna-supervisor[418874]: Tu ne dois PAS modifier directement de fichiers ni exécuter de commandes. Tu dois analyser le contexte et retourner UNIQUEMENT un JSON valide au format suivant:
Jul 17 18:15:05 vbox luna-supervisor[418874]: {"summary": "résumé de l'analyse", "decision": "execute|review|audit|complete|blocked", "requested_action": {"type": "read_files|edit_files|run_tests|build_debug|install_debug|collect_adb|commit_local|none", "parameters": {}}, "files_relevant": ["..."], "expected_result": "...", "requires_human_validation": false}
Jul 17 18:15:05 vbox luna-supervisor[418874]: Réponds uniquement par ce JSON, sans texte avant ou après. ...

---

● luna-mission-store.service - Luna Mission Store - service local de stockage des missions
     Loaded: loaded (/home/ludo/.config/systemd/user/luna-mission-store.service; enabled; preset: enabled)
     Active: active (running) since Wed 2026-07-15 18:46:55 CEST; 1 day 23h ago
   Main PID: 1143 (python3)
      Tasks: 1 (limit: 31187)
     Memory: 29.8M
        CPU: 22.775s
     CGroup: /user.slice/user-1000.slice/user@1000.service/app.slice/luna-mission-store.service
             └─1143 /usr/bin/python3 -m luna_supervisor.mission_store

Jul 17 18:14:46 vbox luna-mission-store[1143]: 2026-07-17 18:14:46,159 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 18:14:46] "POST /create HTTP/1.1" 200 -
Jul 17 18:14:49 vbox luna-mission-store[1143]: 2026-07-17 18:14:49,842 [INFO] __main__: Mission assigned: TEST-ID-UNIQUENESS-001 -> runner luna-vm-01
Jul 17 18:14:49 vbox luna-mission-store[1143]: 2026-07-17 18:14:49,842 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 18:14:49] "POST /next-job HTTP/1.1" 200 -
Jul 17 18:14:58 vbox luna-mission-store[1143]: 2026-07-17 18:14:58,905 [INFO] __main__: Mission report: TEST-ID-UNIQUENESS-001 -> needs_audit
Jul 17 18:14:58 vbox luna-mission-store[1143]: 2026-07-17 18:14:58,905 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 18:14:58] "POST /report HTTP/1.1" 200 -
Jul 17 18:14:58 vbox luna-mission-store[1143]: 2026-07-17 18:14:58,921 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 18:14:58] "GET /mission/SUPERVISOR-GIT-CLEANUP-PLAN-001 HTTP/1.1" 200 -
Jul 17 18:14:58 vbox luna-mission-store[1143]: 2026-07-17 18:14:58,950 [INFO] __main__: Mission upsert: SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898
Jul 17 18:14:58 vbox luna-mission-store[1143]: 2026-07-17 18:14:58,951 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 18:14:58] "POST /create HTTP/1.1" 200 -
Jul 17 18:15:05 vbox luna-mission-store[1143]: 2026-07-17 18:15:05,374 [INFO] __main__: Mission assigned: SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898 -> runner luna-vm-01
Jul 17 18:15:05 vbox luna-mission-store[1143]: 2026-07-17 18:15:05,374 [INFO] werkzeug: 127.0.0.1 - - [17/Jul/2026 18:15:05] "POST /next-job HTTP/1.1" 200 -
