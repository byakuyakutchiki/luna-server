> Spec

# Spécification du workflow n8n — Codex ↔ Kimi 2 ↔ DeepSeek

## 1. Objectif

Automatiser la transmission des rapports d'audit entre Codex, Kimi 2 et DeepSeek via le système de fichiers et l'API DeepSeek, avec :

- détection des nouveaux rapports ;
- validation du format JSON ;
- sanitisation des secrets ;
- copie contrôlée vers l'inbox de destination ;
- limitation à 3 échanges par incident ;
- blocage des actions non autorisées ;
- attente de validation humaine avant toute action sensible.

## 2. Déclencheurs (Triggers)

### 2.1 Trigger Codex → Kimi 2

- **Type** : `Local File` trigger (ou `Schedule` toutes les 2 minutes)
- **Chemin** : `/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_codex/`
- **Pattern** : `*.json`
- **Mode** : détecter les nouveaux fichiers uniquement

### 2.2 Trigger Kimi 2 → Codex

- **Type** : `Local File` trigger (ou `Schedule` toutes les 2 minutes)
- **Chemin** : `/home/ludo/luna-server/docs/AGENT_EXCHANGE/reports_kimi/`
- **Pattern** : `*.json`
- **Mode** : détecter les nouveaux fichiers uniquement

### 2.3 Trigger optionnel DeepSeek

- **Type** : `Local File` trigger ou appel manuel
- **Chemin** : `/home/ludo/luna-server/docs/AGENT_EXCHANGE/inbox_deepseek/`
- **Pattern** : `*.json`
- **Usage** : permettre à n8n de réécrire un rapport DeepSeek reçu par webhook ou API dans `reports_deepseek/`

## 3. Flux de traitement

### 3.1 Branche Codex → Kimi 2

```text
[Trigger reports_codex/*.json]
    ↓
[Read Binary File]
    ↓
[Validate JSON Schema]
    ↓
[Sanitize Secrets]
    ↓
[Check conversation iteration < 3]
    ↓
[Check lock: allowed?]
    ↓
[Write sanitized file to inbox_kimi/]
    ↓
[Log exchange in archive/]
    ↓
[Send notification (optional)]
```

### 3.2 Branche Kimi 2 → Codex

```text
[Trigger reports_kimi/*.json]
    ↓
[Read Binary File]
    ↓
[Validate JSON Schema]
    ↓
[Sanitize Secrets]
    ↓
[Check conversation iteration < 3]
    ↓
[Write sanitized file to inbox_codex/]
    ↓
[Log exchange in archive/]
    ↓
[Send notification (optional)]
```

### 3.3 Branche DeepSeek (déclenchée par n8n)

```text
[Trigger: nouveau rapport Codex ou Kimi avec severity >= P1]
    ↓
[Build audit package]
    ↓
[Sanitize Secrets]
    ↓
[HTTP Request → DeepSeek API]
    ↓
[Parse DeepSeek response]
    ↓
[Validate JSON output]
    ↓
[Write to reports_deepseek/]
    ↓
[Copy sanitized version to inbox_codex/ and inbox_kimi/]
    ↓
[Log exchange in archive/]
```

Le **paquet d'audit** envoyé à DeepSeek contient :

- contexte du projet (objectif, stack, branche active) ;
- diff Git limité aux fichiers pertinents ;
- rapports Codex et Kimi 2 déjà sanitiser ;
- extraits de logs filtrés ;
- question précise à résoudre.

Exemple de payload JSON :

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "Tu es un auditeur technique senior Android..."
    },
    {
      "role": "user",
      "content": "Paquet d'audit : contexte + diff + logs + rapports..."
    }
  ],
  "response_format": { "type": "json_object" }
}
```

**Important** : l'en-tête `Authorization: Bearer $DEEPSEEK_API_KEY` est injecté par n8n depuis ses credentials. La clé ne transite jamais dans les rapports.

## 4. Validation JSON minimale

Chaque rapport doit contenir :

```json
{
  "report_id": "string",
  "author": "codex" | "kimi2" | "deepseek",
  "timestamp": "string (ISO 8601)",
  "git_commit": "string",
  "device": "string",
  "severity": "P0" | "P1" | "P2" | "P3",
  "finding": "string",
  "evidence": ["string"],
  "recommended_action": "string",
  "action_applied": false,
  "requires_ludovic_approval": true
}
```

Si la validation échoue :

- le fichier est déplacé dans `archive/rejected/` ;
- un log d'erreur est écrit dans `archive/error_YYYYMMDD_HHMMSS.json`.

## 5. Sanitisation des secrets

Appliquer les remplacements suivants avant copie :

```regex
(sk-[a-zA-Z0-9]{20,}) → ***OPENAI_KEY_REDACTED***
(api[_-]?key|token|password|secret|credential)["'\s]*[:=]["'\s]*[^"'\s]+ → $1=***REDACTED***
([A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+) → ***JWT_REDACTED***
([0-9a-f]{32,}) → ***HEX_REDACTED***
```

## 6. Gestion des conversations (anti-boucle)

### 6.1 Identifiant de conversation

Le `report_id` initial définit la conversation. Les réponses utilisent `in_reply_to`.

Exemple :

- `codex-20260712-001` → rapport initial
- `kimi2-20260712-001` → réponse (`in_reply_to: codex-20260712-001`)
- `codex-20260712-002` → conclusion (`in_reply_to: kimi2-20260712-001`)

### 6.2 Compteur d'itérations

- Itération 1 : Codex diagnostic
- Itération 2 : Kimi 2 contre-analyse
- Itération 3 : Codex conclusion

DeepSeek peut être consulté à chaque itération sans incrémenter le compteur (appel API unidirectionnel, pas de boucle).

À l'itération 3, n8n :

- copie le rapport dans l'inbox adverse ;
- ajoute un flag `awaiting_ludovic_approval: true` ;
- **n'autorise plus aucun échange automatique** sur cette conversation ;
- envoie une notification à Ludovic.

## 7. Vérification du verrou

Avant de copier un rapport, n8n vérifie :

```text
docs/AGENT_EXCHANGE/locks/android_operator.lock
```

- Si le verrou existe et que l'auteur du rapport n'est pas dans `allowed_to_write` (ou `forbidden_to` contient l'auteur), le rapport est mis en attente.
- Si le rapport contient `action_applied: true`, il est rejeté immédiatement.
- Si le rapport demande une action interdite (liste `forbidden_actions`), il est rejeté.

## 8. Écriture des fichiers

### 8.1 Fichier inbox

Nom : `<original_report_id>_sanitized.json`

Exemple : `codex-20260712-001_sanitized.json`

### 8.2 Fichier d'archive

Nom : `exchange_YYYYMMDD_HHMMSS_<conversation_id>.json`

Contenu :

```json
{
  "timestamp": "2026-07-12T10:00:00+02:00",
  "conversation_id": "codex-20260712-001",
  "iteration": 1,
  "from_agent": "codex",
  "to_agent": "kimi2",
  "source_file": "reports_codex/codex-20260712-001.json",
  "destination_file": "inbox_kimi/codex-20260712-001_sanitized.json",
  "sanitized": true,
  "lock_checked": true,
  "requires_ludovic_approval": true,
  "action": "forward"
}
```

## 9. Notification (optionnel)

### 9.1 Méthodes possibles

- Webhook vers un service externe (à éviter sans validation).
- Écriture d'un fichier `notification_YYYYMMDD_HHMMSS.txt` dans `shared_context/`.
- Appel HTTP local vers une API de notification si elle existe.

### 9.2 Contenu

```text
Nouveau rapport de <author> pour <to_agent>
Incident: <conversation_id>
Severité: <severity>
Résumé: <finding>
Action requise: <requires_ludovic_approval>
Fichier: <destination_file>
```

## 10. Nœuds n8n recommandés

| Étape | Nœud n8n | Notes |
|-------|----------|-------|
| Déclenchement | Local File Trigger | Chemin absolu sur la VM |
| Lecture | Read Binary File | Lire le fichier JSON |
| Validation | Code Node (JavaScript) | Vérifier le schéma minimal |
| Sanitisation | Code Node (JavaScript) | Regex de remplacement |
| Vérification itération | Code Node | Compter via `in_reply_to` |
| Vérification verrou | Code Node | Lire le fichier JSON de lock |
| Écriture | Write Binary File | Écrire dans inbox adverse |
| Archive | Write Binary File | Écrire dans archive/ |
| DeepSeek | HTTP Request | Appel API avec credentials n8n |
| Notification | HTTP Request (optionnel) | Uniquement si approuvé |

## 11. Exemple de workflow JSON

Un squelette de workflow sera généré dans :

```text
docs/AGENT_EXCHANGE/n8n_workflow_agent_exchange.json
```

Ce squelette pourra être importé dans n8n via l'interface `http://100.91.29.87:5680`.

## 12. Procédure de test

1. Créer un fichier test dans `reports_codex/test-001.json`.
2. Vérifier qu'il apparaît dans `inbox_kimi/`.
3. Créer une réponse test dans `reports_kimi/test-reply-001.json`.
4. Vérifier qu'elle apparaît dans `inbox_codex/`.
5. Vérifier que l'archive contient les deux échanges.
6. Tester le rejet d'un JSON invalide.
7. Tester le rejet d'un rapport contenant un secret non redacté.
8. Tester le blocage à l'itération 4.
9. Tester l'appel DeepSeek avec un paquet d'audit factice (vérifier que la réponse est écrite dans `reports_deepseek/`).

## 13. Déploiement

Le workflow n8n ne doit être activé qu'après :

- validation de cette spécification par Ludovic ;
- test des scripts d'audit ;
- vérification des permissions SSH ;
- création des worktrees Kimi2 et Codex ;
- configuration de la clé `DEEPSEEK_API_KEY` dans les credentials n8n.
