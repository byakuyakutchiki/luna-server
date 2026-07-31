# Rapport de mission : SUPERVISOR-COMMAND-ENTRYPOINT-002

- **Mission ID** : SUPERVISOR-COMMAND-ENTRYPOINT-002
- **Objectif** : Créer une commande utilisateur simple `luna-mission` pour injecter une mission autonome depuis le terminal.
- **Date** : 2026-07-17T14:38:00+02:00
- **Branche** : `automation/guardian-autonomous-001`
- **Commit** : `74441ad` — `feat(autonomy): ajoute commande luna-mission`
- **Agent appelé** : kimi
- **Action exécutée** : ajout sous-commande `create` dans `cli.py` + wrapper shell `luna-mission`
- **Statut final** : needs_audit

---

## Modifications effectuées

### `tools/luna_supervisor/cli.py`

Ajout de la sous-commande `create` avec les paramètres suivants :

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `prompt` | obligatoire | Objectif texte de la mission |
| `--project-path` | `.` | Chemin racine du projet Luna |
| `--role` | `operator` | Rôle agent (`operator`, `auditor`, `coordinator`, `reviewer`) |
| `--max-iterations` | `1` | Nombre maximum d'itérations |
| `--expected-final-status` | `None` | Statut final attendu (`needs_audit`, etc.) |
| `--priority` | `normal` | Priorité (`low`, `normal`, `high`, `critical`) |
| `--prefix` | `None` | Préfixe de l'ID mission |
| `--mission-id` | `None` | ID mission explicite |

La sous-commande réutilise `mission_queue.build_mission_payload` et `mission_queue.submit_mission` pour construire et envoyer la mission au webhook n8n.

### `tools/luna_supervisor/bin/luna-mission`

Wrapper shell exécutable installé dans le PATH via symlink `~/.local/bin/luna-mission`.

```bash
#!/usr/bin/env bash
PROJECT_PATH="/home/ludo/luna-server"
export PYTHONPATH="${PROJECT_PATH}/tools"
exec python3 -m luna_supervisor create "$@"
```

---

## Tests effectués

### 1. Aide

```bash
luna-mission --help
```

Résultat : ✅ aide affichée correctement.

### 2. Injection mission non destructive

```bash
luna-mission "Auditer l etat du telephone Android en lecture seule" \
  --role operator \
  --expected-final-status needs_audit \
  --max-iterations 1 \
  --prefix AUDIT
```

Résultat : ✅
```
mission_id=AUDIT-1784291881
status=queued
```

La mission est bien présente dans `data/luna_missions.db` avec `status=queued`.

### 3. Injection mission avec mot "push" (test de garde-fou n8n)

```bash
luna-mission "Faire un push production" --role operator --prefix TEST
```

Résultat : ⚠️ acceptée par n8n (`status=queued`).  
**Observation** : le workflow n8n local exporté (`luna_mission_create.json`) ne filtre que les expressions exactes `git_push`, `merge_main`, `production_deploy`, `real_sms`, `real_calls`, `secret_changes`. Le mot seul "push" n'est pas bloqué. Le garde-fou final reste le superviseur qui bloquera l'action destructive au moment de l'exécution.

---

## État Git après commit

```
Branche : automation/guardian-autonomous-001
Commit  : 74441ad feat(autonomy): ajoute commande luna-mission
Status  : 6 fichiers non suivis (secrets, docs agents, agent_bridge, script utilitaire)
```

Aucun secret, DB, APK ou artefact build versionné.

---

## Garde-fous respectés

- ✅ Aucun push GitHub.
- ✅ Aucun déploiement.
- ✅ Aucune action Guardian/APK/Cloud/SMS/appel.
- ✅ Aucun secret exposé.
- ✅ La commande ne fait qu'injecter une mission ; le superviseur applique ensuite ses propres garde-fous.

---

## Prochaine action recommandée

Revue humaine / audit requis avant poursuite.

La commande `luna-mission` est fonctionnelle. Elle permet à Ludovic de lancer une mission depuis le terminal. L'autonomie complète nécessite encore le planificateur de prochaine mission (`SUPERVISOR-NEXT-MISSION-PLANNER-001`) et le workflow d'approbation humaine (`N8N-HUMAN-APPROVAL-WORKFLOW-001`).
