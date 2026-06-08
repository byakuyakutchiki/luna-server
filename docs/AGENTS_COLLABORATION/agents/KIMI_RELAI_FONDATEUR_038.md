# KIMI — Brief de relai fondateur (juin 2026)

> Ce fichier est écrit par Claude pour Kimi.
> Ludo (fondateur) part en déplacement. Kimi prend le relai avec Codex et ChatGPT.
> Quand Ludo rentre : Claude reprend le lead technique.

---

## Accès au projet

### Repos GitHub (compte byakuyakutchiki)

| Repo | Visibilité | URL | Rôle |
|---|---|---|---|
| `luna-server` | **PUBLIC** | https://github.com/byakuyakutchiki/luna-server | Backend + frontend Luna — repo principal |
| `luna-exploitants` | privé | — | Package exploitant clé en main |
| `luna-proprio` | privé | — | Assets fondateur |
| `luna-docs` | privé | — | Études de marché, contrats |

Pour écrire dans `luna-server` : configure git avec un Personal Access Token GitHub (repo scope).

```bash
git clone https://TOKEN@github.com/byakuyakutchiki/luna-server.git
```

### Fichiers clés dans luna-server

```
luna_web.py                        → Backend principal Flask (NE PAS MODIFIER sauf nécessité critique)
static/team_workspace.html         → Page /team — Iris Workspace — chantier actif
static/simli.html                  → Page Iris Audio + Command Screen
deploy.sh                          → Déploiement Cloud Run (NE PAS LANCER sans validation Ludo)
CLAUDE.md                          → Boussole collaboration IA — lire en premier
docs/AGENTS_COLLABORATION/         → Historique des missions par IA
```

---

## État du projet au 8 juin 2026

### Ce qui tourne en production (Cloud Run)
- Luna Audio Iris (`/simli`) — voix + command screen ✅
- Luna Visio Tavus (`/simli` → Daily.js) ✅
- Luna Chat/SMS/Voix ✅
- Iris Team Workspace (`/team`) — V3 déployée ✅

### Dernière révision déployée
`luna-beta-00614-ttc` — contient :
- Correction icône micro (synchronisation avec `audioTrack.enabled`)
- Badge main levée `✋` sur la tuile vidéo participant (overlay `.tw-seat-cam`)
- Menu modération owner par clic sur le badge (baisser main / donner parole / couper micro / passer spectateur)

---

## Chantier actif : Iris Workspace `/team`

### Fichier concerné
`static/team_workspace.html` — ~1900 lignes — **seul fichier à modifier**

### Architecture en place (V3)
- Esthétique YAWatch Corporate : fond `#050b1a`, Iris vert `#10d48e`, IQ cyan `#22d3ee`, Luna violet `#a78bfa`
- Stepper 13 étapes (navigation avant/arrière, dots done/active/locked)
- Orbite participants avec présence réelle WebRTC (caméra/micro par siège)
- Halo orateur (animation prise de parole)
- Badge main levée sur tuile vidéo + menu modération owner
- WebSocket sync : `hand_raise`, `cam_status_update`, `speaking`

### Prochaine étape validée (P0.2) — EN ATTENTE VALIDATION LUDO

Le moteur d'étape `canvasState` :
- Chaque étape du stepper filtre les objets visibles sur le canvas
- Étape 3 = cartes propositions seulement, Étape 10 = recommandation Luna au centre, etc.
- Référence : `docs/AGENTS_COLLABORATION/reference/IRIS_WORKSPACE_FLOW_ETAPES_V3.md`
- Référence : `docs/AGENTS_COLLABORATION/agents/CLAUDE_IMPL_TEAM_WORKSPACE_035.md`

**⚠️ NE PAS implémenter P0.2 avant validation explicite de Ludo sur le schéma de flux.**

---

## Règles non-négociables

1. **Pas de déploiement** (`bash deploy.sh`) sans validation explicite de Ludo
2. **Modifier uniquement** `static/team_workspace.html` pour l'Iris Workspace
3. **Ne pas toucher** `luna_web.py` sauf bug bloquant critique
4. **Pas de SMS / email / appel / paiement réel** dans aucun test
5. **Pas de secret côté frontend** (pas de clés API dans le JS)
6. **Pas de nouvelles features** avant validation du schéma de flux P0.2

---

## Ce que Kimi peut faire pendant le relai

### ✅ Autorisé sans validation
- Lire les fichiers, comprendre l'architecture
- Proposer des améliorations UI/UX dans `team_workspace.html`
- Corriger des bugs UI visibles (sans déployer)
- Rédiger des specs pour les prochaines phases
- Préparer du code prêt à appliquer

### ⏳ Nécessite validation Ludo avant implémentation
- Implémenter P0.2 (moteur d'étape canvasState)
- Modifier `luna_web.py`
- Tout déploiement Cloud Run

### ❌ Interdit
- Déployer en production
- Modifier `.env`, `pv_lock.json`, clés API
- Pusher sur `main` sans review

---

## Comment communiquer avec Claude au retour de Ludo

Laisser un fichier `KIMI_HANDOFF_038.md` dans `docs/AGENTS_COLLABORATION/agents/` avec :
1. Ce que tu as fait (commits, fichiers modifiés)
2. Ce qui reste à faire
3. Problèmes rencontrés
4. État de validation Ludo sur P0.2

Claude lira ce fichier en premier au retour.

---

## Contexte business (pour décisions architecturales)

- Luna = compagnon de lien social (PAS dispositif médical)
- Modèle 70/30 : Ludo 70% (licence techno), Exploitant 30%
- Plans : Essentiel 79€, Confort 149€, Premium 249€
- L'exploitant ne voit pas le code — il reçoit un package Docker clé en main
- Tavus = système visio principal (STT+LLM+TTS ~2-3s latence)
- TTS : OpenAI coral voice

---

> Bon courage Kimi. Claude reprend au retour de Ludo.
