# Prompt de collaboration — Codex CLI (Windows) + Kimi (Linux VM)

## Contexte

Tu es Codex CLI, un assistant IA opérant sur la machine Windows de Ludovic. Tu travailles sur le même dépôt local que Kimi, qui tourne sur la VM Linux (`/home/ludo/luna-server`).

Ludovic développe l’APK Android **Luna / Guardian** depuis plus d’un an. L’objectif immédiat est de stabiliser une **cellule de développement autonome** capable de faire avancer Guardian sans session interactive permanente.

## Architecture en place

- **n8n** tourne sur la VM Linux (`http://<ip-vm>:5678`) comme gouvernance centrale.
- **Luna Agent Supervisor** est un service systemd utilisateur sur la VM.
- **Luna Local Runner Gateway** et **Luna Agent Dispatcher** existent.
- **Budget Governor**, **Morning Report**, **Routing**, **Agent Caller** existent dans `tools/luna_supervisor/`.
- **mission_store.py** a été créé comme stockage technique local SQLite (`data/luna_missions.db`) car le nœud n8n "Data Table" n’est pas disponible dans l’installation locale n8n 1.97.1.
- Les workflows n8n suivants ont été recréés dans `tools/luna_supervisor/n8n_workflows/` :
  - `Luna Runner Next Job` → webhook `POST /webhook/luna-runner-next-job`
  - `Luna Runner Report` → webhook `POST /webhook/luna-runner-report`
  - `Luna Mission Create` → webhook `POST /webhook/luna-mission-create`
- L’authentification des webhooks utilise le Header Auth déjà présent dans `.env.supervisor` et `.env.runner`.

## Problème actuel

Les workflows n8n sont importés, activés et démarrés, mais les webhooks retournent une réponse vide (`HTTP 200` sans body) pour les cas valides :

- `POST /webhook/luna-runner-next-job` → vide
- `POST /webhook/luna-mission-create` (payload valide) → vide
- `POST /webhook/luna-mission-create` (payload invalide) → retourne correctement `{"status":"error","error":"missing_mission_id"}`

Le service local `mission_store.py` est accessible sur `http://127.0.0.1:9876` depuis la VM. Il répond correctement quand on l’appelle directement avec `curl`.

## Ce que tu dois faire

1. Lire les fichiers suivants sur la machine Windows (même repo, chemin relatif) :
   - `tools/luna_supervisor/n8n_workflows/luna_runner_next_job.json`
   - `tools/luna_supervisor/n8n_workflows/luna_runner_report.json`
   - `tools/luna_supervisor/n8n_workflows/luna_mission_create.json`
   - `tools/luna_supervisor/mission_store.py`
   - `tools/luna_supervisor/mission_queue.py`
   - `tools/luna_runner/n8n_client.py`

2. Identifier pourquoi les webhooks n8n retournent une réponse vide pour les cas valides.

3. Corriger les workflows JSON pour que :
   - `luna-runner-next-job` retourne `{"status":"idle"}` ou `{"status":"assigned","mission":{...}}`
   - `luna-runner-report` retourne `{"status":"ok","mission_id":"..."}`
   - `luna-mission-create` retourne `{"status":"queued","mission_id":"..."}` pour un payload valide
   - `luna-mission-create` retourne `{"status":"error","error":"..."}` pour un payload invalide

4. Les workflows doivent continuer à utiliser `mission_store.py` comme stockage technique. Ils ne doivent pas implémenter eux-mêmes la logique métier (routage, budget, etc.).

5. Une fois corrigés, expliquer à Kimi les modifications faites et pourquoi.

## Contraintes absolues

- Ne modifier **aucun** code Guardian / APK Android.
- Ne pas exécuter ADB, Git, Gradle ou compilation Android depuis ce prompt.
- Ne pas créer de nouvelle mission dans n8n sans accord de Kimi.
- Ne pas afficher ni versionner les secrets (Header Auth, clés API).
- Ne pas supprimer `mission_store.py` ni remplacer n8n par un stockage local.
- Ne pas pousser sur Git, ne pas merger.
- Garder l’architecture multi-agents : `operator → Kimi`, `auditor → DeepSeek`, `coordinator → Codex/OpenAI`, `reviewer → Review Worker`.

## Comment tester depuis la VM Linux

Les commandes suivantes peuvent être exécutées par Kimi sur demande :

```bash
cd /home/ludo/luna-server

# Test next-job
curl -s -X POST -H "Authorization: <HEADER_VALUE>" -H "Content-Type: application/json" \
  -d '{"runner_id":"luna-vm-01","device_status":"available"}' \
  http://localhost:5678/webhook/luna-runner-next-job

# Test mission-create valide
cat > /tmp/mission.json <<'EOF'
{
  "mission_id": "TEST-CODEX-001",
  "task_id": "TEST-CODEX-001",
  "role": "operator",
  "priority": "high",
  "objective": "Mission de test créée par Codex",
  "max_iterations": 3
}
EOF
curl -s -X POST -H "Authorization: <HEADER_VALUE>" -H "Content-Type: application/json" \
  -d @/tmp/mission.json \
  http://localhost:5678/webhook/luna-mission-create

# Test mission-create invalide
curl -s -X POST -H "Authorization: <HEADER_VALUE>" -H "Content-Type: application/json" \
  -d '{"mission_id":"","objective":"test","role":"operator","max_iterations":3}' \
  http://localhost:5678/webhook/luna-mission-create
```

> Remplace `<HEADER_VALUE>` par la valeur de `N8N_HEADER_VALUE` dans `.env.supervisor`.

## Livrable attendu

- Fichiers JSON des workflows corrigés dans `tools/luna_supervisor/n8n_workflows/`.
- Explication concise du bug et de la correction.
- Confirmation que les trois webhooks retournent les réponses attendues.
