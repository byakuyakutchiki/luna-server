# Rapport de mission : SUPERVISOR-COMMAND-ENTRYPOINT-002-FIX

- **Mission ID** : SUPERVISOR-COMMAND-ENTRYPOINT-002-FIX
- **Objectif** : Durcir la commande `luna-mission` pour refuser avant envoi à n8n les prompts/fichiers contenant des demandes dangereuses, et ajouter le support `--prompt-file`.
- **Date** : 2026-07-17T14:45:00+02:00
- **Branche** : `automation/guardian-autonomous-001`
- **Commit** : `641e376` — `fix(autonomy): durcit luna-mission (mots interdits + prompt-file)`
- **Agent appelé** : kimi
- **Action exécutée** : ajout de `safety.py` + durcissement de `cmd_create`
- **Statut final** : needs_audit

---

## Modifications effectuées

### `tools/luna_supervisor/safety.py` (nouveau)

Module de validation côté client avec :

- `validate_prompt(prompt)` : détecte les mots/expressions interdits.
- `validate_prompt_file(path)` : vérifie extension, taille, encodage UTF-8, puis appelle `validate_prompt`.

### `tools/luna_supervisor/cli.py`

- Ajout de `--prompt-file` (mutuellement exclusif avec le `prompt` positionnel).
- Appel systématique de `safety.validate_prompt` avant construction du payload.
- Refus immédiat avec message explicite si validation échoue.

---

## Mots et expressions interdits (non exhaustif)

| Catégorie | Exemples |
|-----------|----------|
| Git | `push`, `merge`, `reset`, `reset_hard`, `reset --hard` |
| Deploy | `deploy`, `production_deploy`, `mise en production` |
| APK / build | `installer apk`, `install debug`, `build debug apk`, `compile debug apk` |
| Communications réelles | `real_sms`, `real_call`, `sms reel`, `appel reel`, `envoyer sms` |
| Secrets | `.env`, `secret`, `cle api`, `api key`, `token`, `password`, `credential` |
| Données / cloud | `supprimer donnees`, `user_data_deletion`, `cloud_modification` |

La détection est **case-insensitive** et tolère espaces, tirets et underscores.

---

## Tests effectués

### Prompts dangereux (refusés avant n8n)

| Commande | Résultat |
|----------|----------|
| `luna-mission "Faire un push production"` | ✅ refusé (`push`) |
| `luna-mission "Deployer en production"` | ✅ refusé (`deploy`) |
| `luna-mission "Installer l'APK debug"` | ✅ refusé (`installer l'apk`) |
| `luna-mission "Envoyer un SMS reel"` | ✅ refusé (`sms reel`) |
| `luna-mission "Lire le fichier .env"` | ✅ refusé (`.env`) |

### Prompts acceptés

| Commande | Résultat |
|----------|----------|
| `luna-mission "Auditer l etat du telephone en lecture seule" --expected-final-status needs_audit` | ✅ `status=queued` |
| `luna-mission "Auditer l APK installe sans le modifier"` | ✅ `status=queued` |

### Fichiers

| Fichier | Contenu | Résultat |
|---------|---------|----------|
| `/tmp/mission_dangereuse.md` | "reset --hard" + "push force" | ✅ refusé (`push`) |
| `/tmp/mission_ok.md` | audit non destructif | ✅ `status=queued` |
| `/tmp/mission.bin` | vide | ✅ refusé (extension `.bin`) |

### Missions tests dangereuses bloquées

Les missions tests créées avant la correction ont été passées en `blocked` dans `data/luna_missions.db` :

- `TEST-1784291917` ("Faire un push production") -> `blocked`
- `TEST-1784293110` ("Installer l APK debug") -> `blocked`

---

## État Git

```
Branche : automation/guardian-autonomous-001
Commit  : 641e376 fix(autonomy): durcit luna-mission (mots interdits + prompt-file)
Status  : 6 fichiers non suivis (secrets, docs agents, agent_bridge, script utilitaire)
```

Aucun push. Aucun secret/DB/APK/build versionné.

---

## Limites connues

- La liste de mots interdits est une première ligne de défense côté client. Elle peut être contournée par des reformulations indirectes. Le superviseur reste le garde-fou final d'exécution.
- Les missions d'audit APK doivent utiliser des formulations non ambiguës ("auditer sans modifier", "lire l'état") pour éviter les faux positifs.

---

## Prochaine action recommandée

Revue humaine / audit requis avant poursuite.

La commande `luna-mission` est maintenant durcie et supporte `--prompt-file`. Elle peut être validée pour continuer vers `SUPERVISOR-NEXT-MISSION-PLANNER-001`.
