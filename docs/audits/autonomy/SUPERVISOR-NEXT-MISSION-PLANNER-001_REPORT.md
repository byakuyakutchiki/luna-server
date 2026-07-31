# Rapport de mission : SUPERVISOR-NEXT-MISSION-PLANNER-001

- **Mission ID** : SUPERVISOR-NEXT-MISSION-PLANNER-001
- **Objectif** : Permettre au superviseur de proposer ou créer automatiquement la prochaine mission sûre après une mission terminée.
- **Date** : 2026-07-17T17:45:00+02:00
- **Branche** : `automation/guardian-autonomous-001`
- **Commit** : `ec805be` — `feat(autonomy): planificateur de prochaine mission sure (SUPERVISOR-NEXT-MISSION-PLANNER-001)`
- **Agent appelé** : kimi
- **Action exécutée** : ajout du module `next_mission_planner.py` + intégration superviseur/CLI
- **Statut final** : needs_audit

## Changements apportés

### Nouveaux fichiers

- `tools/luna_supervisor/next_mission_planner.py` : planificateur autonome de prochaine mission.
  - Lit `AGENT_SHARED/AUTONOMY_COMPLETE_ROADMAP.md`.
  - Parse les blocs `### N. MISSION_ID` pour extraire objectif et statut attendu.
  - Classe chaque mission en `safe`, `guarded` ou `forbidden`.
  - Ignore les missions contenant des mots interdits (`push`, `deploy`, `install apk`, etc.).
  - Propose mais ne crée pas automatiquement les missions `guarded` (Guardian/APK/Cloud/Production).
  - Crée la mission dans `mission_store` uniquement si `auto_next=true` et `risk_level=safe`.
  - Écrit un rapport `AGENT_SHARED/<MISSION_ID>_PLAN.md`.

- `tools/luna_supervisor/tests_next_mission_planner.py` : tests unitaires sans appel IA.
  - Parsing de la roadmap.
  - Classification safe/guarded/forbidden.
  - Saut des missions interdites.
  - Création automatique mockée.
  - Refus de créer une mission guarded même avec `auto_next=true`.

### Fichiers modifiés

- `tools/luna_supervisor/supervisor.py` :
  - Import de `NextMissionPlanner`.
  - Méthode `_maybe_plan_next_mission()` appelée après chaque statut terminal si `auto_next=true`.
  - Le résultat du planificateur est ajouté au rapport final (`next_mission_plan`).

- `tools/luna_supervisor/cli.py` :
  - Nouvelle sous-commande `plan-next` (`luna_supervisor plan-next [--auto-next]`).
  - Flag `--auto-next` ajouté à `luna-mission create`.

- `tools/luna_supervisor/mission_queue.py` :
  - Propagation du champ `auto_next` dans `mission_context_json`.

## Tests réalisés

### Tests unitaires

```bash
cd /home/ludo/luna-server
python3 tools/luna_supervisor/tests_next_mission_planner.py
```

Résultat : 9/9 tests OK.

### Test fonctionnel en chaîne (2 missions)

Le service `luna-agent-supervisor.service` a été temporairement arrêté pour le test, puis redémarré.

**Mission 1** : `TEST-NEXT-PLANNER-001`
- Commande : `luna-mission "Lire le fichier README.md du projet et retourner un résumé de son contenu" --auto-next --role operator --max-iterations 1 --expected-final-status needs_audit --mission-id TEST-NEXT-PLANNER-001`
- Statut initial : `queued`
- Exécution : `PYTHONPATH=tools python3 -m luna_supervisor run-once`
- Statut final : `complete`
- Rapport généré : `AGENT_SHARED/TEST-NEXT-PLANNER-001_REPORT.md`
- Planification suivante déclenchée : `auto_next=true`
- Mission suivante créée automatiquement : `CODEX-REVIEW-SUPERVISOR-HARDENING-001`
- Rapport planificateur : `AGENT_SHARED/CODEX-REVIEW-SUPERVISOR-HARDENING-001_PLAN.md`

**Mission 2** : `CODEX-REVIEW-SUPERVISOR-HARDENING-001`
- Source : créée automatiquement par le planificateur.
- Exécution : `PYTHONPATH=tools python3 -m luna_supervisor run-once`
- Statut final : `needs_audit`
- Rapport généré : `AGENT_SHARED/CODEX-REVIEW-SUPERVISOR-HARDENING-001_REPORT.md`
- Planification suivante ignorée : `auto_next=false` (le planificateur force `auto_next=false` sur les missions créées pour éviter la boucle infinie).

## Vérifications post-test

- `mission_store` accessible : `curl http://127.0.0.1:9876/health` → OK.
- `luna-agent-supervisor.service` redémarré et actif.
- Base de données mise à jour :
  - `TEST-NEXT-PLANNER-001` → `complete`
  - `CODEX-REVIEW-SUPERVISOR-HARDENING-001` → `needs_audit`

## Garde-fous respectés

- Aucune action destructive automatique.
- Pas de push, merge, reset, deploy.
- Pas d'installation d'APK.
- Pas de SMS/appels.
- Pas de modification de secrets, Cloud, base de données.
- Les missions `guarded` (Guardian/APK/Cloud) restent en proposition, non créées automatiquement.
- Les missions `forbidden` sont ignorées.

## Limites connues

- Le planificateur lit uniquement `AUTONOMY_COMPLETE_ROADMAP.md` ; il ne synchronise pas encore `YAWATCH_AUTONOMY_CHECKLIST.md`.
- La classification du risque repose sur des mots-clés ; une mission ambiguë pourrait être classée `guarded` par excès de prudence.
- Le planificateur ne vérifie pas encore le budget restant avant création (le superviseur le fera au moment du routage).

## Prochaine action recommandée

Validation par Codex/Ludovic. Une fois validé, poursuivre avec `N8N-HUMAN-APPROVAL-WORKFLOW-001` ou `SUPERVISOR-BUDGET-POLICY-001` selon la roadmap.
