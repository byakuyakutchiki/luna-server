# Avis Codex

Agent : Codex (OpenAI)
Date : 2026-05-25
Rôle : Corrections ciblées, commits, PR, tests

## Lecture du dépôt

Codex a abandonné le dépôt local Windows séparé et cloné directement `https://github.com/byakuyakutchiki/luna-server`.

Documents lus :
- `AGENTS.md`
- `docs/AGENTS_COLLABORATION/README.md`
- `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md`
- `docs/AGENTS_COLLABORATION/REGLES_DE_COORDINATION.md`
- `docs/AGENTS_COLLABORATION/DECISION_FINALE.md`

Compréhension : GitHub `main` est la source de vérité du code, mais ne prouve pas à lui seul que Cloud Run ou l'APK réelle sont à jour. Toute modification avec impact production doit rester sous validation Ludovic, avec revue Claude si nécessaire.

## Fichiers concernés

- `docs/AGENTS_COLLABORATION/agents/CODEX_AVIS.md`
- `.vscode/extensions.json`
- `.vscode/settings.json`
- `.continue/rules/01-luna-coordination.md`
- `.continue/.env.example`

## Changements déjà faits

- Clone du vrai dépôt GitHub `byakuyakutchiki/luna-server` côté Windows.
- Ajout du dépôt à `safe.directory` Git pour que VS Code puisse utiliser Git correctement.
- Création d'une branche dédiée : `codex/setup-vscode-deepseek`.
- Préparation d'une configuration VS Code/Continue pour permettre à DeepSeek de travailler localement dans le repo, sans accès direct Google Cloud production.

## Tests effectués

- `git clone` depuis GitHub : OK.
- `git remote -v` : `origin` pointe vers `https://github.com/byakuyakutchiki/luna-server.git`.
- Lecture des documents de coordination : OK.
- `git status` : OK après configuration `safe.directory`.

## Risques de régression

- Risque de bruit Git CRLF/LF observé sur `static/formulaires.html` et `static/simli.html` après clone Windows. Ces fichiers ne doivent pas être inclus dans un commit de configuration.
- Risque de confusion entre assistance IA locale et déploiement production : DeepSeek doit être limité au repo local/GitHub jusqu'à validation explicite Ludovic.
- Risque de modification majeure non relue : toute modification de `luna_web.py`, `index.html`, APK, Cloud Run ou secrets doit passer par PR/revue/validation.

## Proposition Codex

- Utiliser VS Code comme poste principal Windows sur le clone `luna-server`.
- Installer Continue comme extension IA compatible DeepSeek.
- Configurer DeepSeek via clé API utilisateur, jamais commiter la clé.
- Versionner les règles Continue du projet pour rappeler à DeepSeek : pas de production, pas de Cloud Run, pas de secrets, pas de gros refactor sans validation.
- Garder les travaux IA sur branches dédiées avant validation Ludovic.

---

## MISSION ACTIVE — Objectif 001 voix

**Assigné le** : 2026-05-25
**Branche à créer** : `codex/objectif-001-voix`

### Ce qu'on sait

Le bouton vocal dans l'APK peut ne pas produire de voix et s'arrêter après ~20 secondes.
Un fix AudioWorklet → ScriptProcessorNode a été déployé sur Cloud Run (commit `e699ae6`),
mais il n'a pas encore été validé sur appareil réel.

### Ta tâche (Codex)

1. **Vérifier les commits récents liés à la voix** :
   ```
   git log --oneline --all | grep -iE "voice|vocal|audio|worklet|coral"
   ```

2. **Confirmer que le fix est bien dans `static/index.html`** :
   Chercher `LunaApp` dans `startVoice()` — doit sélectionner ScriptProcessorNode si WebView détecté.

3. **Vérifier `integrations/openai/web_voice_bridge.py`** :
   - La voix par défaut est-elle `coral` ou `alloy` ?
   - Y a-t-il un timeout configuré ? Lequel ?
   - Le WebSocket `/ws/luna-voice` est-il enregistré dans `luna_web.py` ?

4. **Vérifier `integrations/openai/realtime_bridge.py`** :
   - Même question sur la voix par défaut.
   - Quelle est la durée de session max configurée ?

5. **Lister les tests voix existants** (si présents dans `tests/`).

### Ce que tu dois poster ici (remplacer "À compléter" ci-dessous)

- Commits voix trouvés (hash + message)
- État du fix AudioWorklet dans index.html (présent / absent / ligne)
- Voix par défaut dans web_voice_bridge.py et realtime_bridge.py
- Timeout session vocal (valeur réelle)
- Tests voix existants (oui/non, combien)
- Ton verdict : le fix est-il suffisant ou y a-t-il autre chose à corriger ?

### Interdictions

- Ne pas modifier `luna_web.py` ni `index.html` sans validation Claude
- Ne pas déployer sur Cloud Run
- Branche `codex/objectif-001-voix` uniquement — pas de push sur `main`
