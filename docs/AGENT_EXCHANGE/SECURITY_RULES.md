# Règles de sécurité — Collaboration Codex / Kimi / DeepSeek / n8n

## 1. Principe fondamental

**Aucun agent ne modifie l'état du système, du téléphone, de Git ou du serveur sans validation explicite de Ludovic.**

L'objectif est de permettre à Codex, Kimi 2 et DeepSeek de lire, auditer et recommander, tout en protégeant le travail de Kimi 1 et l'intégrité de la production.

## 1.5. DeepSeek — règles spécifiques

DeepSeek est un **auditeur distant API**. Il ne dispose jamais :

- d'un accès SSH à la VM ;
- d'un accès ADB au téléphone ;
- d'un accès au système de fichiers ;
- de la capacité à exécuter du code localement.

Il reçoit uniquement des **paquets d'audit** préparés par n8n (contexte, diff, logs filtrés, rapports d'autres agents) et renvoie un rapport JSON structuré.

### Token DeepSeek

- Stocké uniquement dans les **credentials n8n** ou un fichier `.env` local non versionné.
- **Jamais** dans Git, jamais dans un rapport, jamais dans un prompt envoyé à DeepSeek.
- Nom recommandé : `DEEPSEEK_API_KEY`.
- Scope : appel API uniquement, pas d'accès infra.

### Données envoyées à DeepSeek

- Toujours **sanitisées** avant envoi.
- Limitées au strict nécessaire pour l'audit.
- Aucune donnée personnelle d'utilisateur final sans consentement documenté.

## 2. Comptes et accès

### 2.1 Compte `ludo` (VM Debian)

- Codex se connecte depuis Windows via SSH au compte `ludo`.
- Le compte `ludo` est le propriétaire du dépôt et des outils.
- **Codex n'a pas besoin d'un compte dédié** tant qu'il n'exécute que des scripts d'audit en lecture seule.
- Si un accès plus fin est requis, créer un compte `codex-audit` membre des groupes :
  - `ludo` (lecture du dépôt)
  - `vboxsf` (lecture du partage Windows)
  - **PAS** `sudo`, `adm`, `systemd-journal` si possible.

### 2.2 Authentification SSH

- Privilégier l'authentification par **clé publique** pour Codex.
- Si un mot de passe est utilisé, il doit être stocké dans un gestionnaire de mots de passe et jamais dans un rapport.
- Désactiver l'accès root par SSH (`PermitRootLogin no` déjà recommandé par défaut).

### 2.3 Commandes interdites pour Codex (même en lecture seule)

Codex ne doit jamais exécuter automatiquement :

```bash
# Destruction / mutation d'état
sudo rm ...
git reset --hard
git checkout -- .
git clean -fd
adb install
adb uninstall
adb shell pm clear
adb shell am force-stop
adb reboot
adb logcat -c
systemctl restart ...
systemctl stop ...
systemctl disable ...

# Déploiement production
bash deploy.sh
gcloud run deploy ...
docker push ...

# Modification de fichiers sensibles
sed -i ... /home/ludo/luna-server/.env
rm -rf /home/ludo/luna-server/...
```

## 3. Scripts d'audit autorisés

Seuls les scripts suivants peuvent être exécutés par Codex sans validation préalable :

```text
tools/agent_bridge/audit_git.sh
tools/agent_bridge/audit_android_state.sh
tools/agent_bridge/audit_guardian_logs.sh
tools/agent_bridge/audit_server_logs.sh
tools/agent_bridge/audit_permissions.sh
tools/agent_bridge/audit_guardian_service.sh
```

Ces scripts sont :

- en **lecture seule** ;
- dotés d'un **timeout** (`timeout 30s`) ;
- limités en taille de sortie (`head -n 300/500`) ;
- **sanitisés** (secrets redactés) ;
- incapable de vider `logcat` ou de redémarrer des services.

## 4. Fichier de verrouillage

### 4.1 Emplacement

```text
docs/AGENT_EXCHANGE/locks/android_operator.lock
```

### 4.2 Format

```json
{
  "operator": "kimi1",
  "since": "2026-07-12T10:00:00+02:00",
  "allowed_actions": [
    "adb install",
    "adb shell input",
    "adb shell am force-stop",
    "build apk"
  ],
  "forbidden_to": ["codex", "kimi2"],
  "reason": "Test Guardian vocal sur APK v3.2"
}
```

### 4.3 Règles

- Si le verrou appartient à **Kimi 1**, Codex et Kimi 2 restent en lecture seule.
- Si le verrou appartient à **Kimi 2** (audit destructif exceptionnel), Kimi 1 et Codex restent en lecture seule.
- Si **aucun verrou** n'est actif, aucun agent ne modifie l'état du téléphone.
- n8n refuse toute commande modifiant l'état si le verrou n'autorise pas explicitement l'émetteur.

## 5. Worktrees Git et isolation

### 5.1 Worktrees

```text
/home/ludo/luna-server              → Kimi 1 (opérateur principal)
/home/ludo/luna-kimi2-audit         → Kimi 2 (auditeur indépendant)
/home/ludo/luna-codex-audit         → Codex (propositions d'audit)
```

### 5.2 Règles

- Chaque agent travaille dans son propre worktree.
- **Aucune fusion automatique** n'est autorisée.
- Kimi 1 reste sur `feature/phase-a-auth-apk` (branche actuelle).
- Kimi 2 utilise `audit/kimi2-guardian`.
- Codex utilise `audit/codex-guardian`.
- Tout merge vers `main`, `feature/phase-a-auth-apk` ou toute branche de production nécessite la validation de Ludovic.

## 6. Sanitisation des rapports

### 6.1 Secrets à redacter

- API keys (`sk-...`)
- Tokens d'accès / refresh tokens
- Mots de passe
- JWT
- Chaînes hexadécimales longues (> 32 caractères) pouvant être des secrets
- Clés de chiffrement

### 6.2 Méthode

- Utiliser `tools/agent_bridge/sanitize_report.sh` avant publication d'un rapport.
- Les scripts d'audit appellent automatiquement une regex de sanitisation.
- n8n applique une seconde passe de sanitisation avant copie vers l'inbox adverse.

## 7. Permissions des répertoires d'échange

```text
docs/AGENT_EXCHANGE/
├── inbox_codex/        # Kimi 2 / DeepSeek écrivent, Codex lit
├── inbox_kimi/         # Codex / DeepSeek écrivent, Kimi 2 lit
├── inbox_deepseek/     # n8n écrit, DeepSeek lit (si endpoint local)
├── reports_codex/      # Codex écrit
├── reports_kimi/       # Kimi 2 écrit
├── reports_deepseek/   # n8n écrit après appel API DeepSeek
├── shared_context/     # Tous les agents lisent/écrivent (contexte commun)
├── locks/              # Un seul agent écrit à la fois
└── archive/            # n8n déplace les rapports traités
```

- Les scripts d'audit écrivent dans `reports_codex/` par défaut.
- Kimi 2 écrit ses rapports dans `reports_kimi/`.
- n8n copie les rapports vers l'inbox de destination.
- Les rapports anciens sont archivés par n8n après traitement.

## 8. Règles n8n

### 8.1 Workflow autorisé

- Surveiller `reports_codex/*.json`, `reports_kimi/*.json`.
- Valider le schéma JSON.
- Sanitiser.
- Copier dans l'inbox de destination (`inbox_kimi/`, `inbox_codex/`).
- **Optionnel** : appeler l'API DeepSeek avec un paquet d'audit contrôlé (credentials n8n uniquement).
- **Ne jamais** exécuter de commande shell modifiant l'état.
- **Ne jamais** logger ou exposer `DEEPSEEK_API_KEY`.

### 8.2 Anti-boucle

- Identifiant de conversation unique (`conversation_id`).
- Compteur d'itérations (`iteration` 1 → 3 max).
- Après 3 échanges, le workflow passe en attente de validation humaine.

## 9. Journalisation

n8n conserve une trace horodatée de chaque échange dans :

```text
docs/AGENT_EXCHANGE/archive/exchange_YYYYMMDD_HHMMSS_<conversation_id>.json
```

Chaque entrée contient :

- `timestamp`
- `from_agent`
- `to_agent`
- `report_id`
- `action` (copy, sanitize, approve, reject)
- `requires_ludovic_approval`

## 10. Procédure en cas d'incident

1. **Arrêter le workflow n8n** s'il boucle ou déclenche une action non autorisée.
2. **Vérifier le fichier de verrou** pour identifier qui détient le contrôle.
3. **Révoquer la clé SSH** de Codex si nécessaire.
4. **Restaurer les worktrees** depuis Git si un fichier a été corrompu.
5. **Informer Ludovic** avant toute action corrective majeure.
