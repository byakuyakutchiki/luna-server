# Architecture de collaboration automatisée Codex ↔ Kimi ↔ DeepSeek ↔ n8n

## 1. Objectif

Cette architecture vise à éliminer le copier-coller manuel des diagnostics entre :

- **Codex** sur Windows (poste de développement principal)
- **Kimi 1** dans la VM Debian (opérateur principal APK / Guardian)
- **Kimi 2** dans la VM Debian (auditeur indépendant)
- **DeepSeek** via API distante (auditeur lourd à gros contexte)
- **n8n** dans la VM Debian (orchestrateur de rapports et gardien des tokens)
- **Ludovic** (validateur humain final)

## 2. État actuel constaté

| Élément | État | Détail |
|---------|------|--------|
| VM Debian | ✅ Active | `vbox`, IP locale `192.168.1.45`, Tailscale `100.91.29.87` |
| SSH sur VM | ✅ Actif | Écoute `0.0.0.0:22`, service `sshd` running |
| n8n | ✅ Actif | Port interne `5678`, exposé via `http://100.91.29.87:5680` |
| Partage Windows | ✅ Monté | `/media/windows/` → `C:\` via VirtualBox shared folder |
| Pont Linux→Windows | ✅ Existant | `C:\Users\saint\Desktop\PONT_LINUX_WINDOWS\` avec `commandes/` et `resultats/` |
| Pont Claude | ✅ Existant | `pont_claude.ps1` déjà utilisé pour exécuter des commandes Windows depuis Linux |
| ADB | ✅ Device détecté | `c7750037 device`, `fr.yawatch.luna` actif (PID 29649) |
| Worktrees Git | ⚠️ Partiels | Worktree `luna-server-pwa-base-5b2fc0f-v3` existe, mais pas de worktree dédié Kimi2/Codex |

## 3. Architecture cible

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           Windows (Codex)                               │
│  ┌─────────────────┐         ┌──────────────────────────────────────┐  │
│  │ VS Code / CLI   │         │ Pont Windows existant                │  │
│  │ ssh ludo@VM     │         │ C:\Users\saint\Desktop\PONT_LINUX_...│  │
│  └────────┬────────┘         └──────────────────────────────────────┘  │
│           │                                                             │
│           │ SSH sécurisé                                                │
│           ▼                                                             │
└─────────────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        VM Debian (Luna)                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │ Kimi 1      │  │ Kimi 2      │  │ n8n         │  │ SSH (sshd)   │   │
│  │ Opérateur   │  │ Auditeur    │  │ Orchestrateur│  │ Accès Codex  │   │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘   │
│         │                │                │                │           │
│         │         ┌──────┴──────┐         │                │           │
│         │         │ DeepSeek    │         │                │           │
│         │         │ API distante│◄────────┘                │           │
│         │         │ Auditeur    │  (appelé par n8n)        │           │
│         │         └─────────────┘                          │           │
│         │                │                │                │           │
│         └────────────────┴────────────────┴────────────────┘           │
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ /home/ludo/luna-server                                          │   │
│  │ ├── docs/AGENT_EXCHANGE/   ← boîte d'échange                  │   │
│  │ ├── tools/agent_bridge/    ← scripts audit en lecture seule   │   │
│  │ ├── /home/ludo/luna-server       ← Kimi 1 (opérateur)         │   │
│  │ ├── /home/ludo/luna-kimi2-audit  ← Kimi 2 (auditeur)          │   │
│  │ ├── /home/ludo/luna-codex-audit  ← Codex (propositions)       │   │
│  │ └── DeepSeek via API distante   ← Auditeur lourd              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                          │                                              │
│                          ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ADB + téléphone Android (fr.yawatch.luna)                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4. Flux de collaboration

### 4.1 Audit par Codex depuis Windows

1. Codex exécute en SSH :
   ```powershell
   ssh ludo@192.168.1.45 "/home/ludo/luna-server/tools/agent_bridge/audit_git.sh"
   ssh ludo@192.168.1.45 "/home/ludo/luna-server/tools/agent_bridge/audit_android_state.sh"
   ```
2. Les rapports sont générés dans `docs/AGENT_EXCHANGE/reports_codex/`.
3. Codex rédige un rapport JSON dans `reports_codex/` ou dans `inbox_kimi/`.

### 4.2 Transmission par n8n

1. n8n surveille `reports_codex/*.json` (trigger File → Local).
2. Vérifie le schéma JSON et sanitise les secrets.
3. Copie le rapport dans `inbox_kimi/`.
4. Déclenche (si possible) l'analyse Kimi 2 ; sinon enregistre le fichier pour lecture manuelle.

### 4.3 Analyse par Kimi 2

1. Kimi 2 lit `inbox_kimi/`.
2. Effectue un audit indépendant dans son worktree `/home/ludo/luna-kimi2-audit`.
3. Rédige un rapport JSON dans `reports_kimi/`.

### 4.4 Analyse par DeepSeek (optionnelle, déclenchée par n8n)

1. n8n prépare un **paquet d'audit** : contexte + rapports Codex/Kimi + logs filtrés + diff Git.
2. n8n appelle l'API DeepSeek (`https://api.deepseek.com`) avec ce paquet.
3. DeepSeek renvoie une contre-analyse structurée.
4. n8n écrit le rapport dans `inbox_deepseek/` et `reports_deepseek/`.
5. Kimi 2 et Codex peuvent lire la contre-analyse de DeepSeek.

**Sécurité** : le token `DEEPSEEK_API_KEY` vit dans les credentials n8n ou un `.env` local non versionné. DeepSeek ne reçoit jamais le token, ni les secrets bruts.

### 4.5 Retour vers Codex

1. n8n détecte `reports_kimi/*.json` et/ou `reports_deepseek/*.json`.
2. Copie dans `inbox_codex/`.
3. Codex lit le rapport au prochain cycle.

### 4.6 Limite d'échanges

- **Maximum 3 échanges automatiques** par incident entre agents humains (Codex ↔ Kimi 2) :
  1. Codex diagnostic
  2. Kimi 2 contre-analyse
  3. Codex conclusion
- DeepSeek peut être consulté à chaque itération sans compter dans la limite, car c'est un appel API sans boucle.
- Après le 3ème échange humain, le workflow attend validation de Ludovic.

## 5. Ce qui est immédiatement réalisable

| Capacité | Réalisabilité | Commentaire |
|----------|---------------|-------------|
| SSH Codex → VM | ✅ Immédiat | SSH actif, authentification par mot de passe ou clé à confirmer |
| Scripts audit en lecture seule | ✅ Immédiat | Créés dans `tools/agent_bridge/` |
| Boîte d'échange fichiers | ✅ Immédiat | Répertoire `docs/AGENT_EXCHANGE/` créé |
| n8n copie fichiers inbox | ✅ Immédiat | Trigger `Local File` + `Move File` |
| Pont VM → Windows | ✅ Immédiat | Partage VirtualBox + `pont_claude.ps1` existant |
| Worktrees Git séparés | ⚠️ 1 commande | `git worktree add` à exécuter |
| Fichier de verrou | ⚠️ 1 fichier JSON | À créer et surveiller |
| SSH Codex sans mot de passe | ⚠️ À configurer | Clé publique à déployer |
| Appel automatique de Kimi par n8n | ❌ Non natif | Kimi n'expose pas d'API/CLI programmable |
| Appel automatique de Codex par n8n | ❌ Non natif | Codex n'expose pas d'API/CLI programmable |
| Appel API DeepSeek par n8n | ✅ Immédiat | Nécessite une `DEEPSEEK_API_KEY` dans n8n Credentials |

## 6. Ce qui nécessite une intervention manuelle

- **Validation de Ludovic** avant toute modification, compilation, installation ou redémarrage.
- **Lecture des rapports** par Kimi 2 et Codex, car aucun agent n'a d'API ouverte.
- **Exécution des commandes modifiant l'état** (adb install, build, deploy) par l'agent détenteur du verrou.
- **Configuration de la clé DeepSeek** (`DEEPSEEK_API_KEY`) dans n8n Credentials ou `.env` local.
- **Validation du prompt système** envoyé à DeepSeek pour éviter les fuites de contexte.

## 7. Ce qui est impossible avec les outils actuels

- Une conversation entièrement autonome Codex ↔ Kimi sans intervention humaine.
- Un déclenchement automatique d'un agent Kimi ou Codex depuis n8n (pas d'endpoint).
- L'exécution directe de commandes Windows par Codex sans lancer le pont PowerShell côté Windows.
- Donner à DeepSeek un accès direct à la VM, à ADB ou au système de fichiers. DeepSeek reste un appel API lecture/écriture de rapports.

## 8. Points de vigilance

- **Ne jamais** donner à Codex un accès sudo ou shell interactif non contrôlé.
- **Ne jamais** fusionner automatiquement les worktrees.
- **Toujours** maintenir le fichier de verrou `locks/android_operator.lock` à jour.
- **Toujours** redacter les secrets dans les rapports (API keys, tokens, passwords).
- **Ne jamais** inclure `DEEPSEEK_API_KEY` dans Git, dans les rapports, ou dans les prompts envoyés à DeepSeek.
- **Toujours** filtrer le contexte envoyé à DeepSeek pour ne partager que les informations nécessaires à l'audit.

## 9. Prochaines étapes validées par Ludovic

1. Valider l'accès SSH depuis Windows (`ssh ludo@192.168.1.45`).
2. ✅ Confirmer la détection ADB du téléphone (fait : `c7750037 device`, `fr.yawatch.luna` PID 29649).
3. Créer les worktrees Kimi2 et Codex.
4. Configurer le workflow n8n minimal (copie reports → inbox).
5. Configurer la clé `DEEPSEEK_API_KEY` dans n8n Credentials.
6. Tester un cycle complet Codex → n8n → Kimi 2 → n8n → Codex.
7. Tester un appel DeepSeek via n8n sur un paquet d'audit réel.
