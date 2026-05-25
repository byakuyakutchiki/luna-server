# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 (008 VALIDÉ — voix Luna entendue · ouverture objectif 009 — stabilité voix)

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
| Claude | **lead 009** | Stabilité voix — coupures spontanées Luna | dd4a4a4 |
| Codex | **à solliciter 009** | Garde-fous stabilité, rate limit DeepSeek | — |
| DeepSeek | **à solliciter 009** | IA temps réel APK — diagnostic incidents voix | — |
| Kimi Code CLI | **à solliciter 009** | Textes cockpit DeepSeek (observe/recommande/ne peut pas) | — |
| Cursor | **à solliciter 009** | Intégration icônes Kimi + affichage diagnostic DeepSeek | — |

## Objectif actif prioritaire

**Objectif 009 — Stabilité voix Luna (coupures spontanées)**

Symptôme : Luna s'arrête parfois de parler seule en cours de session.
Pistes : VAD trop sensible, timeout session, déconnexion WebSocket silencieuse.
Modèle actif : `gpt-realtime-mini` (révision `luna-beta-00442-7gg`)

**Règle Ludovic** : diagnostic avant toute correction. Déploiement uniquement après validation.

Document à créer : `docs/AGENTS_COLLABORATION/OBJECTIF_009_STABILITE_VOIX.md`

**Note critique** : NE PAS merger les branches DeepSeek/Kimi directement.

**Objectif 007 VALIDÉ** — 11 événements reçus sur téléphone réel Ludovic.
**Objectif 008 VALIDÉ** — Voix Luna entendue sur téléphone réel Ludovic (2026-05-25 ~20h30).

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
- Sentry : source de diagnostic filtrée, voir `NOTE_SENTRY_CERVEAU_LUNA.md`
- DeepSeek temps réel APK : voir `OBJECTIF_008_DEEPSEEK_TEMPS_REEL_APK.md`
