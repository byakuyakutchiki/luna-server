# Tableau de bord — Orchestration Luna

Mis à jour : 2026-05-25 (008 + 009 VALIDÉS — voix Luna stable sur téléphone réel)

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

**Objectif 010 — Historique intelligent des conversations + mémoire Luna**

But : organiser le chat en conversations répertoriées, avec titres automatiques,
mémoire utile et discrète, et corriger le bouton mobile `Connexion` / `Déconnexion`
coupé.

**Règle Ludovic** : diagnostic avant toute correction. Déploiement uniquement après validation.

Document : `docs/AGENTS_COLLABORATION/OBJECTIF_010_HISTORIQUE_MEMOIRE_CHAT.md`

**Note critique** : NE PAS merger les branches DeepSeek/Kimi directement.

**Objectif 007 VALIDÉ** — 11 événements reçus sur téléphone réel Ludovic.
**Objectif 008 VALIDÉ** — Voix Luna entendue sur téléphone réel Ludovic (2026-05-25 ~20h30).
**Objectif 009** — stabilité voix à surveiller, passage à l'objectif suivant autorisé par Ludovic.

**Objectif 011** — audit complet onglet Services / Conciergerie ouvert par Ludovic.
Audit et observation uniquement avant toute correction.

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
- Objectif 010 : voir `OBJECTIF_010_HISTORIQUE_MEMOIRE_CHAT.md`
- Objectif 011 : voir `OBJECTIF_011_AUDIT_SERVICES.md`

## Objectif actif suivant

**Objectif 011 - Audit complet onglet Services / Conciergerie**

But : auditer toutes les cartes de l'onglet Services avant correction. Le travail
est volontairement separe en observation, classification du risque, puis decision
Ludovic.

**Regle Ludovic** : aucun code majeur, aucun test sensible et aucun deploiement
avant synthese multi-agents.

| Agent | Mission 011 | Livrable |
|---|---|---|
| Claude | Synthese technique finale et plan de correction | `agents/CLAUDE_AVIS_011.md` |
| DeepSeek | Audit technique cartes/handlers/actions/tools | `agents/DEEPSEEK_AVIS_011.md` |
| Kimi | Promesse UX, textes humains, actions sensibles | `agents/KIMI_AVIS_011.md` |
| Cursor | UI mobile Services, modales, resultats | `agents/CURSOR_AVIS_011.md` |
| Codex | Cadrage et garde-fous | `agents/CODEX_AVIS_011.md` |

## Retour reel 2026-05-27 - objectif 010

UI sidebar/loupe/deconnexion validee sur APK Android.

La direction UX apportee par Kimi est retenue : le mode focus sidebar corrige la
superposition et preserve la qualite visuelle. Claude doit conserver cette base
et ne pas la remplacer par une refonte rapide.

Reste a traiter : titres/recherche des conversations anciennes et nouvelles,
notamment retrouver un sujet comme `chocolat` dans l'historique.

Synthese Codex disponible : `SYNTHESE_010_RECHERCHE_HISTORIQUE_CODEX.md`.
Recommendation : tester d'abord le patch local deja sur `main`, puis ajouter un
fallback serveur Redis uniquement si la recherche locale ne retrouve pas les
anciens sujets.
