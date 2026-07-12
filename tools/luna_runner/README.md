# Luna Local Runner

Runner Python local qui exécute des missions de diagnostic Android pour n8n.

## Configuration

Copier le fichier d'exemple et renseigner les secrets :

```bash
cp tools/luna_runner/config.example.json /home/ludo/luna-server/.runner_config.json
# ou utiliser /home/ludo/luna-server/.env.runner
```

Variables requises :

- `N8N_HEADER_NAME` : nom du header d'authentification n8n
- `N8N_HEADER_VALUE` : valeur secrète du header
- `N8N_NEXT_JOB_URL` : webhook de récupération de mission
- `N8N_REPORT_URL` : webhook d'envoi de rapport
- `RUNNER_ID` : identifiant du runner (défaut : luna-vm-01)
- `ANDROID_DEVICE_ID` : identifiant ADB autorisé

## Commandes

```bash
# Vérifier l'état du runner et du téléphone
PYTHONPATH=tools python3 -m luna_runner health

# Interroger n8n une fois
PYTHONPATH=tools python3 -m luna_runner poll-once

# Exécuter un diagnostic ADB en lecture seule
PYTHONPATH=tools python3 -m luna_runner execute-diagnostic --mission-id TEST-ADB-001

# Envoyer un rapport existant à n8n
PYTHONPATH=tools python3 -m luna_runner report runs/TEST-ADB-001/<run_id>/result.json
```

## Dossiers de preuves

Chaque exécution crée :

```
runs/<mission_id>/<run_id>/
├── mission.json
├── adb-devices.txt
├── adb-state.txt
├── device-info.txt
├── git-status-before.txt
├── logcat-full.txt
├── logcat-errors.txt
├── screenshot.png
├── ui-hierarchy.xml
├── dumpsys-activity.txt
├── dumpsys-package.txt
├── result.json
└── summary.md
```

## Sécurité

- Aucune commande shell arbitraire n'est autorisée.
- Seules les commandes ADB et Git prédéfinies sont exécutées.
- Les secrets ne sont jamais versionnés (`runs/`, `.env.runner`, `.runner_config.json` sont ignorés).
