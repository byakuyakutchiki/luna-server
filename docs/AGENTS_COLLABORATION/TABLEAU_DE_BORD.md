# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 (objectif 007 déployé — validation Ludovic requise)

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
| Claude | **intégrateur final 007** | Code final + déploiement réalisés, validation réelle réservée à Ludovic | 76072a9 |
| Codex | **coordination 007** | Règle validation Ludovic + garde-fous | — |
| DeepSeek | **avis 007 rendu** | Audit startVoice(), session_ts, chemins alternatifs, fetch/WebSocket Android | 7f516f3 |
| Kimi Code CLI | **avis 007 rendu** | Textes cockpit pour scénarios voix | cf33985 |
| Cursor | **à solliciter 007** | UI mobile, non-régression startVoice(), section chronologie | — |

## Objectif actif prioritaire

**Objectif 007 — Télémétrie vocale précise APK**

Question à résoudre : pourquoi seulement `voice_session_ended` remonte,
et comment faire en sorte que tous les événements de la chronologie vocale
soient visibles dans le cockpit fondateur après un appui réel.

Cause identifiée par Claude :
- Bug 1 : `session_ts = 0` pour `voice_button_clicked` → session fantôme
- Bug 2 : `_apkEventCount >= 10` trop bas pour 21 événements

Document : `docs/AGENTS_COLLABORATION/OBJECTIF_007_TELEMETRIE_VOIX_APK.md`

Claude est l'intégrateur final : il peut coder, corriger et déployer quand Ludovic
l'autorise. La validation fonctionnelle reste uniquement celle de Ludovic après test
sur téléphone réel.

État actuel : Objectif 007 déployé sur Cloud Run selon `CLAUDE_AVIS_007.md`
(`luna-beta-00439-7v9`). La simulation serveur est positive, mais elle ne remplace
pas le test réel APK.

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
