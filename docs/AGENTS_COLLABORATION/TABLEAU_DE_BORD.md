# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 18:50 (007 validé en test réel · ouverture objectif 008 — DeepSeek temps réel APK)

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
| Claude | **lead 008** | Investigation lecture seule : logs Cloud Run, web_voice_bridge.py, OpenAI Realtime state | 59f72b6 |
| Codex | **à solliciter 008** | Garde-fous : clé DeepSeek côté serveur, rate limiting, pas de secrets dans APK | — |
| DeepSeek | **à solliciter 008** | Format événement minimal, seuils incident, diagnostics type voix + cache + boutons | — |
| Kimi Code CLI | **à solliciter 008** | Textes cockpit : "DeepSeek observe / suppose / recommande / ne peut pas" | — |
| Cursor | **à solliciter 008** | Intégration icônes/UX cockpit, vérifier non-régression frontend | — |

## Objectif actif prioritaire

**Objectif 008 — DeepSeek temps réel dans l'expérience APK**

Ludovic a désigné DeepSeek comme IA "dans le téléphone" :
- recevoir signaux APK en temps réel
- déclenché automatiquement sur incident (WebSocket fermé, no audio, erreur JS)
- produire diagnostic structuré exploitable
- clé DeepSeek côté serveur Luna uniquement (jamais APK)

**Architecture** : APK → serveur Luna (clé protégée) → DeepSeek API → diagnostic JSON → cockpit fondateur

Document : `docs/AGENTS_COLLABORATION/OBJECTIF_008_DEEPSEEK_TEMPS_REEL_APK.md`

**Status Objective 007** : ✅ Terminé — 11 événements validés en test réel Ludovic
```
Chronologie complète capturée : clic → token OK → micro OK → capture active
→ WS ouvert → audio envoyé → WS fermé après ~5s (aucune réponse audio)
Diagnostic : blocage serveur voix / OpenAI Realtime
```
**Voir** : `docs/AGENTS_COLLABORATION/OBJECTIF_007_RESULTAT_TEST.md`

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
