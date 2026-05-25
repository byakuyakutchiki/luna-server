# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 (ouverture objectif 006 — validation cerveau voix)

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

| Agent | Statut | Objectif en cours | Dernier commit |
|---|---|---|---|
| Claude | **lead final 006** | Synthèse finale, correction minimale, déploiement après validation Ludovic | a3545a1 |
| Codex | **cadrage 006** | Rôles, garde-fous, critères de validation cerveau voix | — |
| DeepSeek | **à solliciter 006** | Audit local VS Code : `startVoice()`, `sendApkEvent()`, timer silence, WebSocket | — |
| Kimi Code CLI | **à solliciter 006** | Audit humain : textes cockpit, diagnostic non trompeur, journal fondateur | — |
| Cursor | **à solliciter 006** | Vérification UI mobile, assets graphiques, non-régression frontend | — |

## Objectif actif prioritaire

**Objectif 006 — Validation du cerveau Luna sur panne vocale réelle**

Question à résoudre : quand Ludovic appuie sur le bouton vocal et n'entend rien,
est-ce que Luna voit la panne, sait où elle bloque, l'explique dans le cockpit
fondateur, et garde une trace exploitable ?

Document : `docs/AGENTS_COLLABORATION/OBJECTIF_006_VALIDATION_CERVEAU_VOIX.md`

Claude intervient en dernier : il lit les avis, vérifie les logs/endpoints, propose
la correction minimale, puis déploie seulement après validation Ludovic.

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
