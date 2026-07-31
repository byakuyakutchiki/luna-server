# Addendum — SUPERVISOR-AUDIT-DECISION-FIX-001

Ce document complete le rapport automatique genere par le superviseur. L'agent Kimi a termine la mission en `needs_audit` mais n'a pas modifie le code source (il a demande `read_files` puis conclu `audit`). Les corrections ont ete apportees manuellement par Kimi apres la mission, puis validees par dry-run.

## 1. Resultat de la mission automatique

- **Statut final** : `needs_audit` ✅ (objectif atteint au niveau statut)
- **Action executee** : `read_files`
- **Fichiers modifies par la mission** : aucun
- **Budget consomme** : 1 appel Kimi (budget journalier passe a 4/4)

## 2. Corrections manuelles appliquees a tools/luna_supervisor/supervisor.py

### 2.1 Mapping `audit` -> `needs_audit`

Ajout d'un bloc dedie pour la decision `audit` avant la verification de `requires_human_validation` :
- Si `decision == "audit"` et l'action demandee n'est pas destructive/interdite, la mission aboutit en `needs_audit`.
- Si l'action est destructive (`edit_files`, `build_debug`, `install_debug`, `commit_local`) ou interdite par `forbidden_actions`, le blocage humain est conserve.
- Si une action d'inspection non destructive est demandee (ex: `read_files`), elle est executee avant de conclure.

### 2.2 Methode `_is_destructive_action`

Nouvelle methode statique qui liste les actions necessitant validation humaine :
- `edit_files`
- `build_debug`
- `install_debug`
- `commit_local`

### 2.3 Enrichissement automatique du rapport AGENT_SHARED

Nouvelle methode `_collect_status_report` qui collecte :
- Etat des services systemd utilisateur (`luna-agent-supervisor.service`, `luna-mission-store.service`) ;
- Les 10 dernieres missions de `data/luna_missions.db` ;
- Le budget restant (total, journalier, ratio, etat du gouverneur).

Le rapport AGENT_SHARED inclut maintenant systematiquement les sections :
- `## État des services systemd`
- `## Dernières missions`
- `## Budget restant`

## 3. Test dry-run

Commande executee :
```bash
systemctl --user restart luna-agent-supervisor.service
PYTHONPATH=tools python3 -m luna_supervisor dry-run
```

Resultat :
- Le superviseur a redemarre avec les modifications.
- Le BudgetGovernor a bloque l'appel IA (budget Kimi journalier atteint : 4/4).
- Aucune modification de fichier n'a ete detectee.
- Le rapport `DRY-RUN-001_REPORT.md` a ete genere automatiquement avec les nouvelles sections enrichies.

## 4. Limites non testees aujourd'hui

Le comportement `decision=audit -> status=needs_audit` n'a pas pu etre teste avec un vrai appel agent car le budget Kimi journalier est epuise (4/4). Le test fonctionnel complet devra etre fait demain ou apres reinitialisation du compteur.

## 5. Fichiers touches

- `tools/luna_supervisor/supervisor.py` : modifications de logique + enrichissement rapport
- `AGENT_SHARED/SUPERVISOR-AUDIT-DECISION-FIX-001_REPORT.md` : rapport auto
- `AGENT_SHARED/SUPERVISOR-AUDIT-DECISION-FIX-001_ADDENDUM.md` : ce fichier
- `AGENT_SHARED/DRY-RUN-001_REPORT.md` : preuve du rapport enrichi

Aucun autre fichier source modifie. Aucun push, merge, reset, suppression. Aucune modification Guardian/APK/Cloud.
