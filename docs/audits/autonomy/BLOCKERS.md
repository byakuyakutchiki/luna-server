# BLOCKERS — Éléments empêchant l'autonomie complète

Date : 2026-07-15T19:30:00+02:00

---

## P0 — Bloquants critiques (arrêtent l'autonomie complète)

### P0-1 : Aucun code superviseur versionné
- **Description** : L'intégralité de `tools/luna_supervisor/` (3 772 lignes) est non suivie par Git. Les fichiers de configuration locale (`.env.supervisor`, `.env.bak.*`, DB, swap) polluent le workspace.
- **Impact** : En cas de crash, reset ou erreur humaine, le code autonomie disparaît. Impossible de revenir en arrière proprement.
- **Risque** : ÉLEVÉ — perte de travail.
- **Difficulté** : Moyenne.
- **Temps estimé** : 2 à 4 heures (inventaire, `.gitignore`, commit sélectif sur branche dédiée).
- **Mission liée** : `SUPERVISOR-GIT-CLEANUP-PLAN-001` (existe, statut `needs_audit`).

### P0-2 : Pas de commande utilisateur simple pour lancer une mission
- **Description** : Aucun exécutable `luna-mission` dans le PATH. `python3 -m luna_supervisor` pointe sur `cli.py` (health, daemon, dry-run) mais pas sur `mission_queue.py` (create-from-prompt/submit).
- **Impact** : L'utilisateur ne peut pas facilement lancer une mission autonome. Objectif "Ludovic lance une mission puis part" non atteint.
- **Risque** : ÉLEVÉ — autonomie impossible sans interface d'entrée.
- **Difficulté** : Faible.
- **Temps estimé** : 1 à 2 heures (ajouter sous-commande dans `cli.py` ou wrapper shell, mettre à jour `__main__.py`, optionnel `setup.py`/entry-point).
- **Mission liée** : `SUPERVISOR-COMMAND-ENTRYPOINT-001` (existe, ancien statut `waiting_human_approval` avant correctif `audit → needs_audit`).

### P0-3 : Pas de planificateur de prochaine mission
- **Description** : Le système ne peut pas décider seul de la mission suivante. À la fin d'une mission, il produit un rapport et s'arrête. Aucune logique ne lit la checklist/roadmap pour créer la mission suivante.
- **Impact** : L'utilisateur doit manuellement créer chaque mission. L'autonomie "partir puis revenir" n'existe pas.
- **Risque** : ÉLEVÉ — cœur de l'autonomie manquant.
- **Difficulté** : Moyenne à élevée.
- **Temps estimé** : 4 à 8 heures (parse roadmap/checklist, règles de transition, création mission via mission_store, garde-fous forts).
- **Mission liée** : `SUPERVISOR-NEXT-MISSION-PLANNER-001` (prévu dans roadmap).

### P0-4 : Pas de workflow n8n d'approbation humaine
- **Description** : Les missions aboutissant à `waiting_human_approval` ou `blocked` ne déclenchent aucune notification/file d'attente d'approbation. Le daemon s'arrête ou attend indéfiniment.
- **Impact** : Impossible de demander une validation humaine "uniquement lorsqu'elle est réellement nécessaire" de manière fiable.
- **Risque** : ÉLEVÉ — blocage silencieux ou action risquée non approuvée.
- **Difficulté** : Moyenne.
- **Temps estimé** : 3 à 6 heures (workflow n8n, notification, endpoint de reprise/approbation).
- **Mission liée** : nouvelle mission `N8N-HUMAN-APPROVAL-WORKFLOW-001`.

---

## P1 — Bloquants majeurs (dégradent l'autonomie ou créent des risques)

### P1-1 : Budget temporaire élevé sans garde-fou automatique
- **Description** : `config/agent_budget_policy.yaml` fixe `max_total_ai_calls_per_day: 10` et `kimi: 8/jour` avec une note temporaire. Aucun mécanisme empêche ce fichier d'être oublié à cette valeur.
- **Impact** : Coût imprévisible si le superviseur tourne en continu avec des limites élevées.
- **Risque** : MOYEN à ÉLEVÉ — dépassement de budget.
- **Difficulté** : Faible.
- **Temps estimé** : 1 à 2 heures (revenir à 4/6 par défaut, ajouter un garde-fou "session dev" explicite, alerte si limite > 6).
- **Mission liée** : `SUPERVISOR-BUDGET-POLICY-001` (prévu).

### P1-2 : Service `adb-wifi-reconnect.service` manquant
- **Description** : `luna-agent-supervisor.service` déclare `Wants=adb-wifi-reconnect.service` et `After=adb-wifi-reconnect.service`, mais le service n'existe pas.
- **Impact** : Si ADB WiFi tombe, le superviseur ne tente pas de le reconnecter automatiquement.
- **Risque** : MOYEN — interruption de l'autonomie si le téléphone perd le WiFi/ADB.
- **Difficulté** : Faible.
- **Temps estimé** : 1 à 2 heures (créer l'unité systemd, script `adb_wifi_reconnect.sh` déjà présent).
- **Mission liée** : `INFRA-ADB-WIFI-RECONNECT-001`.

### P1-3 : Unité systemd `luna-mission-store.service` absente du dépôt
- **Description** : Le fichier unité n'existe que dans `~/.config/systemd/user/`. Il n'est pas versionné avec le code source.
- **Impact** : Reconstruction difficile sur une autre machine ; documentation/infrastructure désynchronisées.
- **Risque** : MOYEN.
- **Difficulté** : Faible.
- **Temps estimé** : 30 min.
- **Mission liée** : `SUPERVISOR-GIT-CLEANUP-PLAN-001`.

### P1-4 : Pas de preuve que Guardian fonctionne en arrière-plan
- **Description** : L'application n'était pas démarrée au moment de l'audit. Aucun logcat filtré récent. Le service vocal Guardian n'a pas été prouvé actif.
- **Impact** : L'autonomie sur Guardian reste théorique.
- **Risque** : MOYEN — premières missions autonomes risquent d'échouer faute de baseline.
- **Difficulté** : Moyenne.
- **Temps estimé** : 2 à 4 heures (audit non destructif : démarrage contrôlé, logcat, screenshot, dumpsys).
- **Mission liée** : `GUARDIAN-AUDIT-VOICE-002` (prévu).

### P1-5 : Workflows n8n locaux non synchronisés avec le cloud
- **Description** : Les exports JSON dans `tools/luna_supervisor/n8n_workflows/` ont `"active": false`. On ne sait pas si ils reflètent l'état cloud.
- **Impact** : Difficulté à reconstruire l'infra n8n, risque de divergence.
- **Risque** : MOYEN.
- **Difficulté** : Faible.
- **Temps estimé** : 1 à 2 heures (exporter depuis le cloud, versionner, documenter).
- **Mission liée** : `N8N-WORKFLOW-SYNC-001`.

### P1-6 : Agents DeepSeek / Codex jamais testés en autonomie
- **Description** : Les callers DeepSeek et OpenAI nécessitent des clés API non confirmées actives. Tous les rôles tombent en fallback Kimi.
- **Impact** : Pas de revue/audit externe réel ; le superviseur est monoculture Kimi.
- **Risque** : MOYEN.
- **Difficulté** : Faible à moyenne.
- **Temps estimé** : 2 à 3 heures (test de connectivité, vérification clés, dry-run).
- **Mission liée** : `AGENT-CONNECTIVITY-AUDIT-001`.

---

## P2 — Points de friction (à traiter pour robustesse)

### P2-1 : Fichier swap `..env.runner.swp` et backups `.env.bak.*`
- **Description** : Fichiers temporaires/backup dans le workspace.
- **Impact** : Pollution, risque d'exposition de secrets dans `.env.bak.*`.
- **Risque** : FAIBLE à MOYEN.
- **Difficulté** : Faible.
- **Temps estimé** : 15 min.

### P2-2 : `mission_store.py` utilise le serveur Flask de développement
- **Description** : Werkzeug warning explicite dans les logs.
- **Impact** : Non critique en local, mais pas production-grade.
- **Risque** : FAIBLE.
- **Difficulté** : Faible.
- **Temps estimé** : 1 à 2 heures (remplacer par gunicorn/uvicorn ou documenter).

### P2-3 : Tests unitaires non déterministes (date figée)
- **Description** : `tests_budget_governor.py::test_2_budget_100_percent_blocks` échoue car il simule la date 2026-07-12 alors qu'on est le 2026-07-15.
- **Impact** : Bruit dans la CI/vérification.
- **Risque** : FAIBLE.
- **Difficulté** : Faible.
- **Temps estimé** : 30 min (mocker `datetime.now`).

### P2-4 : Pas de log rotation pour `runs/supervisor.log`
- **Description** : `context_builder.py::_log_tail` lit `runs/supervisor.log`, mais le fichier n'est pas nécessairement tourné.
- **Impact** : Croissance disque potentielle.
- **Risque** : FAIBLE.
- **Difficulté** : Faible.
- **Temps estimé** : 1 heure.

### P2-5 : `routing.py` route tout vers Kimi si DeepSeek/OpenAI indisponibles
- **Description** : Fallback automatique sur Kimi pour tous les rôles.
- **Impact** : Le rôle "auditor" ou "coordinator" perd son sens ; consommation de budget Kimi accélérée.
- **Risque** : FAIBLE à MOYEN.
- **Difficulté** : Moyenne.
- **Temps estimé** : 2 à 3 heures (décider si fallback autorisé ou si on bloque avec statut `paused_routing`).

---

## Synthèse des priorités

| Priorité | Nombre | Thème principal |
|----------|--------|-----------------|
| P0 | 4 | Versionnement, commande utilisateur, planificateur, approbation humaine |
| P1 | 6 | Budget, ADB reconnect, systemd, Guardian proof, n8n sync, agents externes |
| P2 | 5 | Propreté, robustesse serveur, tests, logs, routing |

**Chemin critique vers l'autonomie complète :** P0-1 → P0-2 → P0-3 → P0-4 → P1-1 → P1-4.
