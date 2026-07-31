# Rapport de mission : SUPERVISOR-NEXT-MISSION-PLANNER-001-FIX

- **Mission ID** : SUPERVISOR-NEXT-MISSION-PLANNER-001-FIX
- **Objectif** : Corriger les incohérences du planificateur de prochaine mission.
- **Date** : 2026-07-17T17:50:00+02:00
- **Branche** : `automation/guardian-autonomous-001`
- **Commit** : `7e8042b` — `fix(autonomy): corrige planificateur (no-auto-ai markers, budget, preuves services)`
- **Agent appelé** : kimi
- **Action exécutée** : durcissement du planificateur
- **Statut final** : needs_audit

## Problèmes corrigés

### 1. Mission “sans appel Kimi” créée automatiquement

**Constat** : la roadmap propose `CODEX-REVIEW-SUPERVISOR-HARDENING-001` avec objectif “audit sans appel Kimi du code de durcissement”. Le planificateur la créait avec `role=operator`, donc Kimi était appelé — incohérence.

**Correction** : ajout de marqueurs `NO_AUTO_AI_MARKERS` dans `next_mission_planner.py` :
- `sans appel kimi`
- `sans appel ia`
- `sans ia`
- `no ai`
- `no kimi`
- `codex`
- `review par codex`
- `humain`

Toute mission dont l'objectif contient l'un de ces marqueurs est classée `guarded` : elle peut être proposée, mais elle **n'est jamais créée automatiquement**.

### 2. Budget non vérifié avant création automatique

**Correction** : ajout de `_has_budget_for_next_mission()` utilisant `BudgetGovernor`. Avant de créer une mission, le planificateur vérifie :
- `governor_state != "exhausted"`
- `usage_ratio < 1.0`
- `total_today < max_total_per_day`

Si le budget est insuffisant, le statut retourné est `paused_budget` et aucune mission n'est créée.

### 3. Preuve d'état des services insuffisante

**Correction** : `_collect_status_report()` dans `supervisor.py` retourne maintenant un dictionnaire structuré par service :
- `active_state`
- `exit_code`
- `checked_at`

Le rapport AGENT_SHARED affiche ces champs explicitement, par exemple :
- `luna-agent-supervisor.service: active (exit_code=0, checked_at=...)`
- `luna-mission-store.service: active (exit_code=0, checked_at=...)`

Un fichier de preuve post-test a également été généré :
`AGENT_SHARED/SUPERVISOR-NEXT-MISSION-PLANNER-001-FIX_SERVICES.md`

## Tests réalisés

### Tests unitaires

```bash
cd /home/ludo/luna-server
python3 tools/luna_supervisor/tests_next_mission_planner.py
```

Résultat : 11/11 tests OK.

Nouveaux tests ajoutés :
- `test_assess_risk_no_ai_marker` : “sans appel Kimi” et “review par Codex” -> `guarded`.
- `test_plan_paused_budget` : création bloquée quand le budget est épuisé.

### Test fonctionnel en chaîne

**Mission 1** : `TEST-NEXT-PLANNER-FIX-001`
- Commande : `luna-mission "Lire le fichier tools/luna_supervisor/README.md et en donner un résumé" --auto-next --role operator --max-iterations 1 --expected-final-status needs_audit --mission-id TEST-NEXT-PLANNER-FIX-001`
- Exécution : `PYTHONPATH=tools python3 -m luna_supervisor run-once`
- Statut final : `needs_audit`
- Rapport généré : `AGENT_SHARED/TEST-NEXT-PLANNER-FIX-001_REPORT.md`

**Planification suivante** :
- `CODEX-REVIEW-SUPERVISOR-HARDENING-001` a été classée `guarded` et **ignorée**.
- La mission suivante créée automatiquement est `SUPERVISOR-GIT-CLEANUP-PLAN-001` (`risk_level=safe`).
- Rapport planificateur : `AGENT_SHARED/SUPERVISOR-GIT-CLEANUP-PLAN-001_PLAN.md`

## Vérifications post-test

- `luna-agent-supervisor.service` redémarré et actif.
- `luna-mission-store.service` actif.
- Preuve écrite : `AGENT_SHARED/SUPERVISOR-NEXT-MISSION-PLANNER-001-FIX_SERVICES.md`.

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
- Les missions nécessitant Codex/sans IA/humain restent en proposition, non auto-créées.
- Vérification du budget avant création automatique.

## Limites connues

- La classification repose sur des mots-clés ; une formulation inhabituelle pourrait échapper au filtre.
- Le planificateur ne lit pas encore `YAWATCH_AUTONOMY_CHECKLIST.md` pour tenir compte des statuts de modules.

## Prochaine action recommandée

Validation par Codex/Ludovic. Une fois validé, le planificateur peut être considéré comme cohérent pour l'enchaînement autonome de missions sûres.
