# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 19:35 (008 voix validée partiellement · ouverture 008-stabilité — diagnostiquer coupures audio)

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
| Claude | **lead 008-stabilité** | Investigation lecture seule : logs Cloud Run, web_voice_bridge.py, OpenAI session timeouts | — |
| Codex | **à solliciter 008-stabilité** | Garde-fous, correction minimale, pas de gros refactor voix | — |
| DeepSeek | **à solliciter 008-stabilité** | Audit startVoice(), timer 20s, playback queue, détection arrêt prématuré | — |
| Kimi Code CLI | **à solliciter 008-stabilité** | Textes cockpit coupures audio : observation et recommandations | — |
| Cursor | **à solliciter 008-stabilité** | Intégration UI cockpit, vérifier non-régression frontend | — |

## Objectif actif prioritaire

**Objectif 008-stabilité — Corriger les coupures audio Luna**

**Status Objective 008 (voix)** : ✅ Validée partiellement
```
Cause identifiée : OpenAI quota insuffisant (insufficient_quota)
Solution appliquée : Recharge compte OpenAI
Résultat : Voix fonctionne maintenant ✅
Problème restant : Luna coupe/s'arrête pendant la parole
```

**Mission 008-stabilité** : Diagnostiquer et corriger les arrêts audio prématurés

Points à investiguer :
1. Durée session OpenAI Realtime — timeout ?
2. WebSocket fermé prématurément — qui et pourquoi ?
3. Timer 20s silence — interfère-t-il avec le playback ?
4. Buffer playback Apollo — vide-t-il trop tôt ?
5. Logs serveur — erreurs OpenAI entre audio reçu et réponse ?
6. Télémétrie — ajouter `voice_audio_cut` pour tracer les coupures

Document : `docs/AGENTS_COLLABORATION/OBJECTIF_008_VOIX_VALIDATION_PARTIELLE.md`

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
