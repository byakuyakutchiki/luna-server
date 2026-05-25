# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 19:45 (ouverture objectif 009 — diagnostic multi-agents stabilité voix)

## Rôles et outils

| Agent | Outil principal | Accès GitHub | Rôle |
|---|---|---|---|
| **Ludovic** | Voix / mobile / décision | ✅ owner | Orchestrateur, validateur final |
| **Claude** | Terminal Linux + API | ✅ push main | Lead technique, synthèse, déploiement |
| **Codex** | OpenAI API | ✅ PR sur branches | Corrections ciblées, commits, PR, tests |
| **DeepSeek** | VS Code Windows | ✅ branches `ds/*` | Codeur puissant, analyse technique |
| **Kimi** | **Kimi Code CLI** (terminal) | branches `kimi/*` | Audit documentaire + analyse code, shell, web search |
| **Cursor** | VS Code (IA intégrée) | branches `cursor/*` | Édition locale, cohérence projet |

## État actuel des agents

| Agent | Statut | Objectif en cours | Branche |
|---|---|---|---|
| Claude | **lead 009** | Investigation logs serveur, logs /ws/luna-voice, OpenAI state, cause probable | — |
| DeepSeek | **à solliciter 009** | Télémétrie APK, seuils incident, diagnostics type, avis technique | `ds/objectif-009-*` |
| Kimi Code CLI | **à solliciter 009** | Textes cockpit : observe / suppose / recommande / ne peut pas | `kimi/objectif-009-*` |
| Cursor | **à solliciter 009** | UI mobile : états vocaux, overlay, boutons, chronologie après coupure | `cursor/objectif-009-*` |
| Codex | **à solliciter 009** | Coordination, synthèse, garde-fous, checklist validation | `codex/objectif-009-*` |

## Objectif actif prioritaire

**Objectif 009 — Stabilité voix Luna : diagnostiquer et corriger les coupures audio**

**Status Objective 008** : ✅ Validée partiellement
```
Cause identifiée et corrigée : OpenAI quota insuffisant
Voix fonctionne maintenant ✅
Problème restant : Luna coupe/s'arrête sans raison
```

**Mission 009** : Diagnostic multi-agents coordonné de pourquoi la voix coupe

**Processus** :
1. Ludovic teste réel (téléphone) + note heure exacte HH:MM:SS
2. Claude lit logs Cloud Run au moment exact
3. DeepSeek analyse télémétrie APK + seuils
4. Kimi rédige diagnostics cockpit
5. Cursor vérifie UI mobile pendant/après coupure
6. Codex synthétise → prêt pour correction

**Livrables attendus** :
- Claude : cause probable + correction minimale (1-3 lignes)
- DeepSeek : seuils incident + `DEEPSEEK_AVIS_009.md`
- Kimi : textes cockpit + `KIMI_AVIS_009.md`
- Cursor : screenshots UI + `CURSOR_AVIS_009.md`
- Codex : synthèse + `DECISION_FINALE_009.md`

**Timeline** : ~2h30 total (Ludovic 15min + parallelization pour les autres)

Document : `docs/AGENTS_COLLABORATION/OBJECTIF_009_STABILITE_VOIX.md`

## Flux de travail standard

```
Ludovic définit l'objectif dans OBJECTIFS_ACTIFS.md
        ↓
Chaque agent analyse + écrit son avis dans agents/<AGENT>_AVIS.md
        ↓
Claude lit tous les avis + synthétise dans DECISION_FINALE.md
        ↓
Ludovic valide (oui / non / à revoir)
        ↓
Claude ou Codex implémente sur branche dédiée
        ↓
PR → review Claude → merge main
        ↓
Déploiement Cloud Run (bash deploy.sh)
        ↓
Validation post-déploiement (health + objectives)
```

## Règles de branches

| Branche | Qui | Usage |
|---|---|---|
| `main` | Claude uniquement | Code validé, deployable |
| `ds/objectif-xxx` | DeepSeek | Propositions de code via VS Code |
| `codex/objectif-xxx` | Codex | Corrections, PR automatiques |
| `kimi/objectif-xxx` | Kimi | Analyses, docs |
| `cursor/objectif-xxx` | Cursor | Éditions locales |

Règle absolue : **personne ne pousse directement sur `main` sauf Claude, et uniquement après validation Ludovic pour les changements importants.**

## Ce que Ludovic reçoit de chaque agent

Chaque agent doit remonter **uniquement** :
1. Ce qu'il a trouvé (fait, problème, fichier)
2. Ce qu'il propose (solution minimale)
3. Le risque (régression possible)
4. La décision à valider (oui/non suffit)

Pas de copier-coller de code brut dans les rapports — pointer vers le fichier et la ligne.

## Déploiement Cloud Run — qui fait quoi

| Étape | Responsable |
|---|---|
| Code validé sur `main` | Claude |
| `bash deploy.sh` | Claude (ou Ludovic si Claude absent) |
| Vérification post-deploy | Claude |
| Validation finale | Ludovic |

## Contacts / Ressources

- Repo : `https://github.com/byakuyakutchiki/luna-server`
- Cloud Run : `https://luna-beta-674304336025.europe-west1.run.app`
- Monitoring : `GET /api/admin/objectives` (auth admin requise)
- Health : `GET /api/admin/health`
- Déploiement : `bash /home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/deploy.sh`
