#  Luna Agent Supervisor

Cellule autonome multi-agents qui orchestre les missions reçues depuis n8n.

## Objectif

Remplacer l'onglet Kimi interactif par un service qui :

1. Interroge périodiquement n8n.
2. Récupère une mission au maximum.
3. Appelle l'agent adapté (operator, coordinator, auditor, reviewer).
4. Valide la décision structurée retournée.
5. Exécute uniquement des actions autorisées.
6. Collecte les preuves ADB.
7. Renvoie le rapport à n8n.

## Configuration

```bash
cp tools/luna_supervisor/env.supervisor.example /home/ludo/luna-server/.env.supervisor
# Éditer /home/ludo/luna-server/.env.supervisor avec les secrets n8n
```

## Commandes

```bash
# Santé
cd /home/ludo/luna-server
PYTHONPATH=tools python3 -m luna_supervisor health

# Interroger n8n une fois
PYTHONPATH=tools python3 -m luna_supervisor poll-once

# Exécuter une mission simulée
PYTHONPATH=tools python3 -m luna_supervisor run-once --mission-file mission.json

# Dry-run (lecture seule, aucune modification)
PYTHONPATH=tools python3 -m luna_supervisor dry-run

# Démarrer le daemon (ne pas activer sans validation)
PYTHONPATH=tools python3 -m luna_supervisor daemon

# État et verrou
PYTHONPATH=tools python3 -m luna_supervisor status

# Libérer le verrou
PYTHONPATH=tools python3 -m luna_supervisor stop
```

## Architecture

```
n8n
  │
  ▼
Luna Agent Supervisor
  │
  ├── agent_caller.py   (Kimi CLI, DeepSeek API, OpenAI API)
  ├── action_executor.py (actions autorisées)
  ├── budget.py         (limites d'appels)
  └── evidence.py       (preuves ADB)
  │
  ▼
Luna Local Runner / ADB
```

## Sécurité

- Aucune commande shell arbitraire.
- Aucun push, merge, reset --hard automatique.
- Aucun SMS, appel, email réel.
- Les modifications de fichiers nécessitent une branche `automation/*`.
- Les secrets ne sont jamais versionnés (`.env.supervisor` est ignoré).
