# Guide DeepSeek — Travailler sur Luna depuis VS Code

## Setup initial (une seule fois)

1. Cloner le repo luna-server dans VS Code :
   ```
   git clone https://github.com/byakuyakutchiki/luna-server.git
   cd luna-server
   ```

2. Configurer ton identité git :
   ```
   git config user.name "DeepSeek"
   git config user.email "deepseek@luna-agents"
   ```

## Workflow pour chaque objectif

### 1. Lire l'état actuel avant de toucher quoi que ce soit

```
docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md
docs/AGENTS_COLLABORATION/OBJECTIFS_ACTIFS.md
docs/AGENTS_COLLABORATION/REGLES_DE_COORDINATION.md
```

### 2. Créer une branche dédiée

```bash
git checkout main
git pull origin main
git checkout -b ds/objectif-001-voix
```

### 3. Analyser + écrire ton avis

Remplir `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS.md` avec :
- Fichiers analysés
- Problème identifié (fichier + ligne)
- Solution proposée (minimale)
- Risques de régression

### 4. Coder si nécessaire

Faire les modifications **uniquement sur la branche `ds/objectif-xxx`**.
Ne jamais modifier directement `main`.

### 5. Pusher et créer une PR

```bash
git add .
git commit -m "ds: objectif-001 — [description courte]"
git push origin ds/objectif-001-voix
```

Puis créer une PR sur GitHub → Claude review → merge si validé.

## Ce que Claude fait avec tes propositions

1. Claude lit ta PR et ton avis dans `DEEPSEEK_AVIS.md`
2. Claude synthétise avec les avis des autres agents
3. Claude décide : merge / modifications / refus
4. Si merge : Claude déploie sur Cloud Run après validation Ludovic

## Interdictions absolues

- Ne jamais pusher sur `main` directement
- Ne jamais déployer sur Cloud Run
- Ne jamais supprimer un module existant sans validation Claude
- Ne jamais faire de refactor massif sur une seule PR

## Fichiers sensibles — NE PAS MODIFIER sans avis Claude

- `luna_web.py` (backend principal)
- `static/index.html` (frontend APK)
- `android-app/java/fr/yawatch/luna/MainActivity.java`
- `deploy.sh`
- `Dockerfile`
- tout ce qui touche à l'auth JWT, Redis, Stripe, PV de recette
