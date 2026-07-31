# Rapport de mission : SUPERVISOR-AUDIT-NONDESTRUCTIVE-FIX-002

- **Mission ID** : SUPERVISOR-AUDIT-NONDESTRUCTIVE-FIX-002
- **Objectif** : Corriger le mapping des décisions agent pour que `requires_human_validation=true` sur une action **non destructive** produise `needs_audit` au lieu de `waiting_human_approval`. Conserver `waiting_human_approval` pour les actions destructives ou interdites.
- **Date** : 2026-07-17T07:55:00+02:00
- **Branche** : `autonomy/versioning-001`
- **Commit amend** : `a421f7a` — `feat(autonomy): versionne superviseur, config et systemd`
- **Agent appelé** : kimi
- **Action exécutée** : modification de `supervisor.py` et `tests_audit_decision_mapping.py`
- **Statut final** : needs_audit

---

## Bug corrigé

Le superviseur traitait `requires_human_validation=true` de manière uniforme : toute décision avec ce drapeau retournait `waiting_human_approval`. Cela bloquait inutilement les missions d'audit/inspection non destructives (par exemple `read_files`), qui devraient aboutir à `needs_audit` pour être relues sans intervention humaine immédiate.

### Exemple problématique avant correction

| Décision | Action | `requires_human_validation` | Statut avant | Statut après |
|----------|--------|----------------------------|--------------|--------------|
| audit | read_files | true | waiting_human_approval | **needs_audit** |
| audit | edit_files | true | waiting_human_approval | waiting_human_approval |
| execute | read_files | true | waiting_human_approval | **needs_audit** |
| execute | install_debug | true | waiting_human_approval | waiting_human_approval |

---

## Modifications effectuées

### `tools/luna_supervisor/supervisor.py`

1. **Élargissement de `_is_destructive_action`** pour inclure explicitement :
   - `edit_files`, `build_debug`, `install_debug`, `commit_local`
   - `push`, `merge`, `reset_hard`
   - `real_sms`, `real_call`
   - `production_deploy`, `secret_modification`, `cloud_modification`, `user_data_deletion`

2. **Ajout de `_is_non_destructive_action`** retournant `True` pour :
   - `read_files`, `collect_adb`, `audit`, `inspect`

3. **Modification de `_determine_final_status`** :
   - Si `requires_human_validation=true` et action non destructive (ou `none`) -> `needs_audit`.
   - Si `requires_human_validation=true` et action destructive -> `waiting_human_approval`.
   - Si action non destructive sans validation -> `needs_audit`.
   - Si action `none` sans validation -> `success`.

4. **Modification du bloc "Validation humaine demandée par l'agent"** :
   - Pour les actions non destructives, l'action est exécutée et le statut final est déterminé par `_determine_final_status` (donc `needs_audit`).
   - Pour les actions destructives, on conserve `waiting_human_approval`.

### `tools/luna_supervisor/tests_audit_decision_mapping.py`

- Renommage de `test_audit_requires_human_validation_true_to_waiting` en `test_audit_requires_human_validation_true_non_destructive_to_needs_audit`.
- Mise à jour de l'assertion pour attendre `needs_audit`.
- Ajout de `test_execute_requires_human_validation_true_non_destructive_to_needs_audit`.
- Conservation des tests existants pour actions destructives/interdites -> `waiting_human_approval`.

---

## Tests exécutés

```bash
PYTHONPATH=tools python3 -m pytest tools/luna_supervisor/tests_audit_decision_mapping.py -v
```

Résultat : **8 passed**

```bash
PYTHONPATH=tools python3 -m luna_supervisor health
```

Résultat : OK — ADB disponible, device connecté, budget normal.

---

## Validation des garde-fous

- ✅ Aucune action destructive automatique n'est autorisée sans validation humaine.
- ✅ `edit_files`, `build_debug`, `install_debug`, `commit_local` conservent `waiting_human_approval`.
- ✅ Actions explicitement interdites par la mission conservent `blocked` / `waiting_human_approval`.
- ✅ Aucun push/merge/deploy.
- ✅ Aucune action Guardian/APK/Cloud/SMS/appel.

---

## État Git

```
Branche : autonomy/versioning-001
Commit  : a421f7a feat(autonomy): versionne superviseur, config et systemd
Status  : 6 fichiers non suivis (secrets, docs agents, agent_bridge, script utilitaire)
```

Aucun fichier tracké modifié non commité.

---

## Prochaine action recommandée

Revue humaine / audit requis avant poursuite.

Le mapping corrigé permet maintenant aux missions non destructives d'aboutir à `needs_audit` sans bloquer sur `waiting_human_approval`, tout en préservant le verrou humain pour les actions destructives.
