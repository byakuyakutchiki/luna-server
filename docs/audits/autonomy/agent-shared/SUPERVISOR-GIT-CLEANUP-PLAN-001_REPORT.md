# Rapport de mission : SUPERVISOR-GIT-CLEANUP-PLAN-001

- **Mission ID** : SUPERVISOR-GIT-CLEANUP-PLAN-001
- **Objectif** : Auditer le workspace Git du projet Luna et produire un plan de nettoyage sans rien modifier. Lister : 1) les fichiers sources a versionner, 2) les artefacts build/APK a ignorer, 3) les fichiers de secrets/env/DB/logs a exclure du versionnement, 4) les fichiers non suivis a evaluer, 5) une proposition de .gitignore si necessaire. Ne pas executer git reset, stash, rm, ou toute action destructive. Produire uniquement un rapport dans AGENT_SHARED/SUPERVISOR-GIT-CLEANUP-PLAN-001_REPORT.md avec l'inventaire et les recommandations.
- **Date** : 2026-07-14T10:55:10.089559+00:00
- **Agent appelé** : kimi
- **Action exécutée** : read_files
- **Statut final** : needs_audit

## Fichiers modifiés par cette mission
- Aucun fichier modifié par cette mission

## Fichiers du workspace deja modifies avant la mission
- .gitignore
- android-app/build/apk/base.apk
- android-app/build/classes.dex
- android-app/build/compiled_res.zip
- android-app/build/gen/fr/yawatch/luna/R.java
- android-app/build/obj/fr/yawatch/luna/MainActivity$1$1.class
- android-app/build/obj/fr/yawatch/luna/MainActivity$1.class
- android-app/build/obj/fr/yawatch/luna/MainActivity$2.class
- android-app/build/obj/fr/yawatch/luna/MainActivity$3.class
- android-app/build/obj/fr/yawatch/luna/MainActivity$LunaBridge.class
- android-app/build/obj/fr/yawatch/luna/MainActivity.class
- android-app/build/obj/fr/yawatch/luna/R$drawable.class
- android-app/build/obj/fr/yawatch/luna/R$mipmap.class
- android-app/build/obj/fr/yawatch/luna/R$style.class
- android-app/build/obj/fr/yawatch/luna/R$xml.class
- android-app/build/sources.txt
- tools/luna_runner/config.py

## Chemins des preuves locales
- Run directory : /home/ludo/luna-server/runs/SUPERVISOR-GIT-CLEANUP-PLAN-001/1784026478

## Budget consommé
- Appels mission : {'kimi': 1}
- Total journalier : 2

## Inventaire du workspace (complement d'analyse)

### Fichiers modifies (preexistants au workspace)

- `.gitignore` — deja partiellement ignore, a verifier
- `android-app/build/apk/base.apk` — artefact build, a ignorer
- `android-app/build/classes.dex` — artefact build, a ignorer
- `android-app/build/compiled_res.zip` — artefact build, a ignorer
- `android-app/build/gen/fr/yawatch/luna/R.java` — genere, a ignorer
- `android-app/build/obj/fr/yawatch/luna/*.class` — compiles Java, a ignorer
- `android-app/build/sources.txt` — build output, a ignorer
- `tools/luna_runner/config.py` — fichier source potentiellement modifie intentionnellement

### Fichiers non suivis (a evaluer)

**A versionner probablement :**
- `tools/luna_supervisor/` — code source du superviseur
- `config/luna_mission_charter.yaml` — charte produit
- `docs/AGENT_EXCHANGE/`, `docs/ANDROID_REFERENTIEL/`, `docs/agents-runtime-inventory.md` — documentation
- `tools/agent_bridge/` — code source
- `tools/luna_runner/adb_wifi_reconnect.sh` — script utilitaire

**A ignorer / ne pas versionner :**
- `..env.runner.swp` — fichier swap
- `.env.bak.*` — backups de secrets
- `data/luna_missions.db` — base SQLite locale

### Proposition .gitignore

```gitignore
# Backups et fichiers temporaires
*.swp
*.bak
*.bak-*
.env.bak*

# Base de donnees locale
data/*.db

# Fichiers de swap
*.swp
```

### Recommandations

1. Ne pas faire de `git add -A`.
2. Versionner `tools/luna_supervisor/` dans une branche dediee apres audit Codex.
3. Ignorer les artefacts `android-app/build/` (deja dans .gitignore, mais presents car modifies avant l'ignore).
4. Supprimer manuellement ou ignorer `..env.runner.swp` et `.env.bak.*`.
5. Garder `tools/luna_runner/config.py` sous surveillance : verifier s'il doit etre versionne ou reste local.

## Prochaine action recommandee
Revue humaine / audit requis avant poursuite.
