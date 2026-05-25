# Guide Kimi Code — Travailler sur Luna depuis le terminal

## Installation (une seule fois)

```bash
curl -L code.kimi.com/install.sh | bash
```

Modèle actif : `kimi-for-coding` (kimi-k2.6)

## Setup initial dans le repo (une seule fois)

```bash
# Cloner le repo si pas encore fait
git clone https://github.com/byakuyakutchiki/luna-server.git
cd luna-server

# Configurer l'identité git
git config user.name "Kimi"
git config user.email "kimi@luna-agents"
```

## Lancer Kimi Code dans le repo

```bash
cd luna-server
kimi  # ou la commande installée par le script
```

Kimi Code a accès à tous les fichiers du répertoire courant, peut lancer des commandes shell,
lire le web, et créer des sous-agents.

## Workflow pour chaque objectif

### 1. Lire l'état actuel avant de toucher quoi que ce soit

```
docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md
docs/AGENTS_COLLABORATION/OBJECTIFS_ACTIFS.md
docs/AGENTS_COLLABORATION/REGLES_DE_COORDINATION.md
docs/AGENTS_COLLABORATION/agents/KIMI_AVIS.md  ← ton fichier de mission
```

### 2. Créer une branche dédiée

```bash
git checkout main
git pull origin main
git checkout -b kimi/objectif-001-voix
```

### 3. Analyser le code

Kimi Code peut lire directement les fichiers clés :
```
integrations/openai/web_voice_bridge.py
integrations/openai/realtime_bridge.py
static/index.html  (chercher startVoice)
luna_web.py        (chercher /ws/luna-voice, _check_objective_voix)
```

Et lancer des recherches :
```bash
grep -n "LunaApp\|ScriptProcessor\|AudioWorklet\|coral\|alloy" static/index.html
grep -n "voice_name\|timeout\|session" integrations/openai/web_voice_bridge.py
```

### 4. Écrire ton avis

Remplir `docs/AGENTS_COLLABORATION/agents/KIMI_AVIS.md` avec tes trouvailles.

### 5. Proposer du code si nécessaire

Modifier uniquement sur la branche `kimi/objectif-001-voix`.
Commiter et pousser :

```bash
git add .
git commit -m "kimi: objectif-001 — [description courte]"
git push origin kimi/objectif-001-voix
```

Créer une PR sur GitHub → Claude review → merge si validé.

## Ce que Claude fait avec tes propositions

1. Claude lit ton avis dans `KIMI_AVIS.md`
2. Claude synthétise avec Codex + DeepSeek
3. Claude décide : merge / modifications / refus
4. Si merge : Claude déploie après validation Ludovic

## Capacités Kimi Code disponibles pour Luna

| Capacité | Usage autorisé |
|---|---|
| Lecture fichiers | ✅ Tous les fichiers du repo |
| Shell commands | ✅ grep, git, analyse statique |
| Web search | ✅ Docs OpenAI Realtime, MDN Web Audio |
| Écriture fichiers | ✅ Sur branche `kimi/*` uniquement |
| Sous-agents | ✅ Pour analyse parallèle |
| Deploy Cloud Run | ❌ Jamais |
| Push sur `main` | ❌ Jamais directement |
| Modifier `.env` | ❌ Jamais |

## Interdictions absolues

- Ne jamais pusher sur `main` directement
- Ne jamais lancer `bash deploy.sh` ou toute commande Cloud Run
- Ne jamais lire ni modifier les secrets (`.env`, clés API)
- Ne jamais supprimer un module existant sans validation Claude
- Pas de refactor massif — corrections minimales ciblées uniquement
