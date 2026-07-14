# Inventaire runtime des agents Luna

> Date : 2026-07-12  
> Branche : `automation/guardian-runner`  
> Débuté par : Luna Agent Supervisor  

## Objectif de ce document

Lister les outils d'IA réellement installés sur la VM de développement, leurs modes non interactifs disponibles, leurs limitations, et comment le superviseur peut les appeler en toute sécurité.

---

## 1. Kimi Code CLI

### Chemin

```text
/home/ludo/.kimi-code/bin/kimi
```

### Version

```text
0.23.5
```

### Commandes utiles

| Commande | Description |
|----------|-------------|
| `kimi -p "..."` | Exécute un prompt unique en mode non interactif. |
| `kimi -p "..." --output-format stream-json` | Retourne un flux JSON structuré (tool_calls + content + meta). |
| `kimi --add-dir <dir>` | Ajoute un répertoire au workspace de la session. |
| `kimi --model <alias>` | Choix du modèle. |
| `kimi --plan` | Démarre en mode planification. |

### Limitations constatées

- **Impossible de combiner `-p` avec `-y` / `--auto` / `--yolo`.**
- En mode `-p`, Kimi peut tout de même exécuter des outils internes (`Read`, `Edit`, etc.) sans demande d'approbation interactive visible.
- Il retourne généralement le résultat final dans un bloc `content` JSON ou Markdown.

### Mode non interactif recommandé

```bash
cd /home/ludo/luna-server
/home/ludo/.kimi-code/bin/kimi \
  -p "<prompt structuré demandant un JSON de décision>" \
  --output-format stream-json
```

### Stratégie de sécurité

- Le superviseur doit parser la sortie et extraire le JSON de décision.
- Aucune action directe de Kimi ne doit être appliquée sans validation du `action_executor`.
- Le prompt doit explicitement interdire les modifications directes et demander un JSON de décision.
- Si Kimi modifie des fichiers malgré tout, le superviseur doit détecter le changement (`git diff`) et bloquer la mission.

---

## 2. DeepSeek

### Chemin du wrapper

```text
/home/ludo/.local/bin/deepseek
```

### Nature

C'est un script Bash qui lance un terminal interactif Python :

```text
/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/tools/agents/deepseek_chat.py
```

### Problème constaté

Le wrapper est codé en dur vers un ancien dépôt :

```text
/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur
```

Le `.env` de ce dépôt contient une ligne mal formée qui fait échouer le chargement :

```text
/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/.env: line 126: Luna: command not found
```

### Mode disponible

Le script `deepseek_chat.py` est **uniquement interactif**. Il attend `input("Ludovic > ")` en boucle.

### Stratégie recommandée

Ne pas utiliser le wrapper pour le superviseur.  
Utiliser directement l'API DeepSeek via Python `requests` ou `urllib`, avec la clé présente dans l'environnement (`DEEPSEEK_API_KEY`).

Modèle cible : `deepseek-chat`  
Endpoint : `https://api.deepseek.com/chat/completions`

---

## 3. Codex

### Recherche effectuée

```bash
find /home/ludo -maxdepth 5 -type f -name "codex*" 2>/dev/null
which -a codex codex-cli 2>/dev/null
ls -la /home/ludo/.local/bin/ | grep -i codex
```

### Résultat

Aucun binaire `codex` ou `codex-cli` n'a été trouvé sur la VM.

### Interprétation

Dans le runner historique `tools/agents/agent_loop.sh`, "Codex" était un **rôle conceptuel** dans la file partagée `QUEUE.md`, pas un outil installé. Il était probablement exécuté manuellement ou via un autre environnement.

### Stratégie recommandée

Implémenter le rôle Codex via l'API OpenAI avec un modèle de raisonnement (o3-mini, gpt-4o, etc.) si `OPENAI_API_KEY` est disponible. Sinon, marquer Codex comme `unavailable` et utiliser Kimi pour la coordination.

---

## 4. OpenAI CLI

### Chemin

```text
/home/ludo/.local/bin/openai
```

### Commandes utiles

| Commande | Description |
|----------|-------------|
| `openai api chat.completions.create` | Appel direct à l'API. |
| `openai api` | Sous-commandes API diverses. |

### Stratégie recommandée

Utiliser la bibliothèque Python `openai` ou des appels HTTP directs plutôt que la CLI pour un mode non interactif fiable.

---

## 5. Claude

### Recherche effectuée

```bash
/home/ludo/.local/bin/claude --help
```

Pas de test effectué dans cet inventaire, mais un binaire `claude` existe dans `/home/ludo/.local/bin/`.

### Stratégie recommandée

Tester ultérieurement si besoin. Pour l'instant, le rôle `Review` peut être assuré par Kimi ou par des règles locales.

---

## 6. Runner historique `tools/agents`

### Fichiers présents

- `agent_loop.sh` : boucle GitHub-based pour Kimi, DeepSeek, Codex, Claude.
- `agent_loop.ps1` : équivalent Windows.
- `deepseek_chat.py` : terminal DeepSeek interactif.
- `deepseek_chat.sh` / `deepseek_runner.sh` : wrappers.
- `github_poller.sh` : poll GitHub.
- `phone_snapshot.sh` : capture ADB.

### Principe historique

GitHub servait de salle de coordination via :

- `docs/AGENTS_COLLABORATION/QUEUE.md`
- `docs/AGENTS_COLLABORATION/AGENT_CHANNEL.md`

Ce n'était pas une automatisation complète : chaque agent travaillait dans son propre environnement et poussait ses résultats.

---

## 7. Tableau récapitulatif

| Agent | Outil réel | Mode non interactif | Sécurité | Utilisation dans le superviseur |
|-------|-----------|---------------------|----------|---------------------------------|
| Kimi / operator | `kimi` CLI | `-p` + `stream-json` | Peut exécuter des outils internes | Agent principal, parsing JSON obligatoire |
| DeepSeek / auditor | API DeepSeek | `requests` Python | Direct API | Audit après échecs, besoin de `DEEPSEEK_API_KEY` |
| Codex / coordinator | Aucun binaire | API OpenAI si clé disponible | Direct API | Coordination si `OPENAI_API_KEY` |
| Review / reviewer | Kimi ou règles locales | `-p` + prompt reviewer | Même contraintes que Kimi | Vérification finale avant rapport |

---

## 8. Recommandations pour le superviseur

1. **Ne jamais passer une commande shell arbitraire** issue d'une réponse d'agent.
2. **Toujours parser un JSON structuré** avec `summary`, `decision`, `requested_action`.
3. **Valider `requested_action` contre une liste blanche** avant exécution.
4. **Détecter les modifications de fichiers** non autorisées via `git diff`.
5. **Préférer les API HTTP** (DeepSeek, OpenAI) aux wrappers interactifs.
6. **Kimi CLI reste le seul agent natif non interactif** disponible immédiatement.
