# luna-ui-orchestrator — V0 simulation

Interface d’orchestration graphique **simulée** entre Codex (Windows) et Kimi (VM Linux).

> ⚠️ **V0 uniquement** : aucun clic réel, aucun envoi réel, aucune approbation réelle.

## Objectif

Fournir l’ossature technique pour coordonner les fenêtres Codex/VM et le presse-papiers, sans jamais agir réellement sur l’interface en V0.

## Fichiers

| Fichier | Rôle |
|---------|------|
| `ui_orchestrator.py` | CLI principale et scénario de simulation |
| `state_machine.py` | Machine à états obligatoire |
| `policy.py` | Politique d’approbation simple |
| `exchange.py` | Gestion du dossier partagé `AGENT_SHARED/ui_orchestrator/` |
| `window_detector.py` | Détection/classification des fenêtres Windows (simulation sur Linux) |
| `windows_probe.ps1` | Script PowerShell de liste des fenêtres visibles côté Windows |
| `config/orchestrator_config.yaml` | Configuration (chemins, listes blanches/noires, patterns fenêtres) |
| `tests/test_state_machine.py` | Tests unitaires machine à états |
| `tests/test_policy.py` | Tests unitaires politique |
| `tests/test_window_detector.py` | Tests unitaires détection de fenêtres |

## Utilisation

```bash
cd /home/ludo/luna-server
python3 tools/ui_orchestrator/ui_orchestrator.py --simulate --mission-id TEST-UI-001
python3 tools/ui_orchestrator/ui_orchestrator.py --simulate --probe-windows --mission-id TEST-PROBE-001
```

## Arrêt d’urgence

Créer le fichier :

```text
/media/windows/Users/saint/Documents/Codex/AGENT_SHARED/ui_orchestrator/STOP
```

L’orchestrateur passe alors en état `PAUSED` sans rien simuler.

## Tests

```bash
python3 tools/ui_orchestrator/tests/test_state_machine.py
python3 tools/ui_orchestrator/tests/test_policy.py
```

## Dossier partagé

```text
/media/windows/Users/saint/Documents/Codex/AGENT_SHARED/ui_orchestrator/
├── inbox/
├── outbox/
├── state/
├── logs/
├── screenshots/
├── clipboard/
└── config/
```
