# Rapport de mission : SUPERVISOR-NEXT-MISSION-ID-UNIQUENESS-001

- **Mission ID** : SUPERVISOR-NEXT-MISSION-ID-UNIQUENESS-001
- **Objectif** : Garantir l'unicité des mission_id créés automatiquement par le planificateur pour éviter l'upsert/écrasement de missions historiques.
- **Date** : 2026-07-17T18:20:00+02:00
- **Branche** : `automation/guardian-autonomous-001`
- **Commit** : `fa0cd05` — `fix(autonomy): unicite des mission_id auto-crees (SUPERVISOR-NEXT-MISSION-ID-UNIQUENESS-001)`
- **Agent appelé** : kimi
- **Action exécutée** : ajout de la vérification d'existence et génération d'ID unique suffixé
- **Statut final** : needs_audit

## Problème corrigé

Lors du test précédent, le planificateur avait auto-créé `SUPERVISOR-GIT-CLEANUP-PLAN-001`, un mission_id déjà présent dans `mission_store`. Le endpoint `/create` de `mission_store` faisant un `UPSERT`, cela présentait un risque d'écrasement ou de rejeu confus.

## Correction apportée

Dans `tools/luna_supervisor/next_mission_planner.py` :

1. Ajout de `_mission_store_get_url(mission_id)` pour interroger le endpoint `/mission/<mission_id>`.
2. Ajout de `_mission_exists(mission_id)` :
   - retourne `True` si la mission existe déjà ;
   - retourne `False` si elle n'existe pas ou si le endpoint est injoignable.
3. Ajout de `_unique_mission_id(base_id)` :
   - génère un ID suffixé avec un timestamp Unix, par exemple `SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898`.
4. Modification de `_create_mission(candidate)` :
   - vérifie l'existence de l'ID avant création ;
   - si l'ID existe, utilise l'ID unique ;
   - retourne l'ID effectivement créé ;
   - ajoute `original_mission_id` dans `mission_context_json` pour traçabilité.
5. Mise à jour de `plan()` pour refléter l'ID réel dans `next_mission_id` et `reason`.
6. Mise à jour de `write_report()` pour indiquer si l'ID a été renommé.

## Tests réalisés

### Tests unitaires

```bash
cd /home/ludo/luna-server
python3 tools/luna_supervisor/tests_next_mission_planner.py
```

Résultat : 12/12 tests OK.

Nouveau test ajouté :
- `test_plan_renames_existing_mission_id` : simule un mission_id existant et vérifie que le planificateur génère un ID suffixé avec `-AUTO-<timestamp>`.

### Test fonctionnel

**Mission 1** : `TEST-ID-UNIQUENESS-001`
- Commande : `luna-mission "Lire le fichier config/luna_mission_charter.yaml et lister ses grandes lignes" --auto-next --role operator --max-iterations 1 --expected-final-status needs_audit --mission-id TEST-ID-UNIQUENESS-001`
- Exécution : `PYTHONPATH=tools python3 -m luna_supervisor run-once`
- Statut final : `needs_audit`
- Rapport généré : `AGENT_SHARED/TEST-ID-UNIQUENESS-001_REPORT.md`

**Planification suivante** :
- `CODEX-REVIEW-SUPERVISOR-HARDENING-001` classée `guarded` → ignorée.
- `SUPERVISOR-GIT-CLEANUP-PLAN-001` déjà existante dans `mission_store`.
- Le planificateur a généré un ID unique : `SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898`.
- Mission créée automatiquement avec succès.
- Rapport planificateur : `AGENT_SHARED/SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898_PLAN.md`

Extrait du log :
```
Mission SUPERVISOR-GIT-CLEANUP-PLAN-001 existe deja, utilisation de l'ID unique SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898
Mission suivante creee: SUPERVISOR-GIT-CLEANUP-PLAN-001-AUTO-1784304898
```

## Vérifications post-test

- `luna-agent-supervisor.service` redémarré et actif.
- `luna-mission-store.service` actif.
- Preuve écrite : `AGENT_SHARED/SUPERVISOR-NEXT-MISSION-ID-UNIQUENESS-001_SERVICES.md`.

```bash
systemctl --user is-active luna-agent-supervisor.service luna-mission-store.service
# active
# active
```

## Garde-fous respectés

- Aucune action destructive automatique.
- Pas de push, merge, reset, deploy.
- Pas d'installation d'APK.
- Pas de SMS/appels.
- Pas de modification de secrets, Cloud, base de données.
- Pas d'écrasement de mission existante.

## Limites connues

- L'unicité repose sur le timestamp Unix à la seconde. En cas de création simultanée de plusieurs missions dans la même seconde, un conflit reste théoriquement possible. Pour l'usage actuel (une mission à la fois), c'est acceptable.

## Prochaine action recommandée

Validation par Codex/Ludovic. Une fois validé, le planificateur peut être considéré comme fiable pour l'enchaînement autonome de missions sûres en chaîne courte.
