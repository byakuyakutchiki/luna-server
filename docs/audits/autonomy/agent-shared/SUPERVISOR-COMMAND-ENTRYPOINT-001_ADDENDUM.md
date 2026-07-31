# Addendum — SUPERVISOR-COMMAND-ENTRYPOINT-001

Ce document complète le rapport automatique généré par le superviseur. L’agent Kimi a répondu `audit` avec `requires_human_validation: true`, ce qui a fait basculer la mission en `waiting_human_approval` au lieu du `needs_audit` attendu. Les informations manquantes dans le rapport automatique sont rassemblées ici.

## 1. Résultat du point d’entrée de commande

La mission a été créée manuellement puis injectée avec succès :

```bash
cd /home/ludo/luna-server
PYTHONPATH=tools python3 -m luna_supervisor.mission_queue submit \
  runs/missions/SUPERVISOR-COMMAND-ENTRYPOINT-001.json
```

Résultat :
- `mission_id=SUPERVISOR-COMMAND-ENTRYPOINT-001`
- `status=queued`

Le superviseur l’a récupérée immédiatement après redémarrage et l’a traitée.

## 2. État des services systemd

| Service | État | Enabled | PID | Notes |
|---|---|---|---|---|
| `luna-agent-supervisor.service` | active (running) | yes | 543650 | daemon Python en boucle |
| `luna-mission-store.service` | active (running) | yes | 500646 | mission store local Flask |

## 3. Dernières missions traitées (data/luna_missions.db)

| mission_id | status | role | iteration | max_iterations | updated_at |
|---|---|---|---|---|---|
| SUPERVISOR-COMMAND-ENTRYPOINT-001 | waiting_human_approval | operator | 0 | 1 | 2026-07-14T11:27:54 |
| SUPERVISOR-GIT-CLEANUP-PLAN-001 | needs_audit | operator | 0 | 1 | 2026-07-14T10:55:10 |
| SUPERVISOR-HARDENING-FIXES-002 | needs_audit | auditor | 0 | 1 | 2026-07-14T10:33:27 |
| PHONE-ADB-SMOKE-001 | needs_audit | operator | 1 | 1 | 2026-07-13T23:15:25 |
| GUARDIAN-DIAGNOSTIC-001 | success | operator | 0 | 3 | 2026-07-13T19:51:40 |

## 4. Budget restant

- Date : 2026-07-14
- Kimi consommés aujourd’hui : 3 / 4
- Kimi restants aujourd’hui : 1
- Total journalier : 3 / 6
- Missions consommées : SUPERVISOR-HARDENING-FIXES-002 (1), SUPERVISOR-GIT-CLEANUP-PLAN-001 (1), SUPERVISOR-COMMAND-ENTRYPOINT-001 (1)

## 5. Validation des garde-fous create-from-prompt

Tests effectués :

| Cas | Commande / entrée | Résultat attendu | Résultat observé |
|---|---|---|---|
| Objective vide | `--prompt ""` | refus | ✅ refusé : `objective obligatoire` |
| Rôle invalide | `--role hacker` | refus | ✅ refusé : `role invalide` |
| max_iterations > 3 | `--max-iterations 4` | refus | ✅ refusé : `max_iterations hors limites` |
| Mission valide | prompt non vide, rôle operator, max_iterations=1 | queued | ✅ `status=queued` |

Note : un test de mission valide a créé accidentellement `PROMPT-1784028675`. Elle a été immédiatement annulée dans `luna_missions.db` et son fichier local supprimé.

## 6. Interdits par défaut

`tools/luna_supervisor/mission_queue.py` inclut par défaut dans `mission_context_json.forbidden_actions` :
- `push`
- `merge`
- `reset_hard`
- `real_sms`
- `real_call`
- `production_deploy`
- `secret_modification`
- `cloud_modification`
- `user_data_deletion`

Aucune action interdite n’a été demandée ni exécutée.

## 7. Anomalie constatée

Le superviseur mappe la décision `audit` de l’agent vers `waiting_human_approval` dès que `requires_human_validation: true`. Or l’objectif de la mission attendait `needs_audit`. De plus, l’agent n’a pas demandé d’action `read_files` pour collecter les preuves, il s’est arrêté à `audit`/`none`.

Conséquence :
- le statut final n’est pas celui attendu par la checklist (`needs_audit`) ;
- le rapport automatique est minimal (pas de données services/missions/budget) ;
- la mission ne peut pas reboucler automatiquement.

## 8. Recommandation

Deux pistes :
1. **Court terme** : accepter le résultat comme preuve que le pipeline `fichier JSON → submit → n8n → superviseur → Kimi → rapport AGENT_SHARED` fonctionne, mais marquer le module comme `NEEDS_AUDIT`.
2. **Suite logique** : lancer une mission `SUPERVISOR-AUDIT-DECISION-FIX-001` pour corriger le superviseur afin que `decision=audit` produise `status=needs_audit` et incite l’agent à exécuter des actions d’inspection (`read_files`, `collect_adb`, etc.) avant de conclure.
