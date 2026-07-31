# YAWATCH_AUTONOMY_CHECKLIST

Objectif : permettre a Ludovic de partir sans rester devant le PC, pendant que le workflow avance de facon controlee sur YAWatch/Luna/Guardian.

## Principe central

Le systeme ne doit pas seulement executer des commandes. Il doit tenir un tableau d'etat vivant :

- ce qui fonctionne ;
- ce qui ne fonctionne pas ;
- ce qui manque ;
- les preuves collectees ;
- la prochaine mission logique ;
- les points qui demandent validation humaine.

## Statuts de module

Chaque module doit avoir un statut :

- `OK_PROUVE` : fonctionne avec preuve/log/rapport.
- `A_VERIFIER` : pas encore teste ou preuve insuffisante.
- `BUG_CONFIRME` : probleme reproduit avec preuve.
- `EN_CORRECTION` : correction en cours, pas encore validee.
- `NEEDS_AUDIT` : livrable produit, attend validation Codex/Ludovic.
- `BLOCKED` : impossible de continuer sans info/action externe.

## Checklist projet YAWatch 1 / Luna / Guardian

| Module | Etat actuel | Preuve requise | Prochaine action | Statut |
| --- | --- | --- | --- | --- |
| Pipeline n8n local | n8n -> mission_store -> superviseur -> Kimi fonctionne | logs + mission DB | Durcir autonomie | OK_PROUVE |
| mission_store.py | fonctionne mais tourne sous nohup | healthcheck + mode lancement | systemd user ou doc nohup | A_VERIFIER |
| Superviseur | commande luna-mission fonctionne, mapping audit corrige, rapport enrichi | SUPERVISOR-AUDIT-DECISION-FIX-001_REPORT.md + ADDENDUM + DRY-RUN-001_REPORT.md | test fonctionnel audit demain ou boucle max_iterations=3 | NEEDS_AUDIT |
| Comportement audit superviseur | mapping audit corrige dans supervisor.py, test fonctionnel en attente | ADDENDUM + DRY-RUN-001_REPORT.md | test avec vrai appel agent | EN_CORRECTION |
| AGENT_SHARED | lecture/ecriture Kimi/Codex OK | fichiers INBOX/OUTBOX/REPORT | imposer rapport automatique | OK_PROUVE |
| Telephone ADB | visible cote VM | PHONE-ADB-SMOKE-001_REPORT.md | audit app cible | OK_PROUVE |
| APK installee | fr.yawatch.luna v3.3.0 code 25 | dumpsys package | verifier coherence avec version attendue | A_VERIFIER |
| Guardian voix | historique fragile | logs/app tests | audit cible non destructif | A_VERIFIER |
| Alertes SMS/appels | ne pas tester en reel sans validation | dry-run/logs | audit dry-run seulement | A_VERIFIER |
| Git/workspace | inventaire produit, plan de nettoyage pret | SUPERVISOR-GIT-CLEANUP-PLAN-001_REPORT.md | validation humaine du plan | NEEDS_AUDIT |
| Cloud/prod | hors scope autonomie actuelle | revision/URL si besoin | aucune prod auto | BLOCKED sauf validation |

## Regles d'autonomie

Le workflow peut continuer seul si :

1. La mission est non destructive.
2. Le budget restant est suffisant.
3. Le module precedent a un statut clair.
4. Un rapport est depose dans AGENT_SHARED.
5. Les preuves/logs sont references.
6. La prochaine mission est derivee logiquement de la checklist.

Le workflow doit s'arreter si :

1. Il faut deployer, pousser Git, installer APK, supprimer donnees, envoyer SMS/appels.
2. Le budget est atteint.
3. Le telephone devient indisponible.
4. La mission toucherait Guardian/APK en ecriture sans validation.
5. Le workspace Git est trop sale pour distinguer les changements.
6. Une mission terminale devrait etre requeue sans decision explicite.

## Cycle attendu

1. Lire cette checklist.
2. Choisir le premier module `A_VERIFIER`, `BUG_CONFIRME` ou `EN_CORRECTION` prioritaire.
3. Creer une mission courte avec budget.
4. Executer.
5. Collecter preuves.
6. Ecrire un rapport `AGENT_SHARED/<MISSION_ID>_REPORT.md`.
7. Mettre a jour cette checklist.
8. Mettre le statut final : `needs_audit`, `blocked` ou `success` seulement si prouve.
9. Proposer la prochaine mission.

## Prochaine mission recommandee

MISSION_ID: TEST-AUDIT-NEEDS-AUDIT-001

Objectif : tester fonctionnellement que `decision=audit` produit bien `status=needs_audit` avec un vrai appel agent, et que le rapport AGENT_SHARED est automatiquement enrichi.

Criteres d'acceptation :
- creer une mission d'audit non destructive (lecture seule) ;
- l'agent doit repondre `decision=audit` ;
- statut final observe : `needs_audit` (pas `waiting_human_approval`) ;
- rapport AGENT_SHARED contient services, missions recentes, budget ;
- aucune modification Guardian/APK/Cloud.

Interdits : nettoyage Git reel, push, Cloud, Guardian/APK, SMS/appels, suppression.

Statut final attendu : `needs_audit`.

Alternative : si le budget est insuffisant, prioriser le test de boucle `max_iterations=3` ou le passage de `mission_store.py` sous systemd user.
