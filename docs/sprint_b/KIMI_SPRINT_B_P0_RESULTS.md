# Sprint B — Phase P0 : Résultats Backend

**Rôle :** Kimi — Lead Backend  
**Date :** 2026-06-14  
**Branche :** `sprint-b-backend-fixes`  
**Commit :** `5e693ac`

---

## Objectif de la phase P0

Réparer les liaisons backend critiques qui bloquent l'expérience utilisateur et détruisent la confiance.

---

## Corrections apportées

### 1. Configuration `.env.example`

**Problème :** `JWT_SECRET_KEY` manquant → erreur fatale au démarrage. Compte fondateur non documenté.

**Fichier :** `.env.example`

**Correctif :**
- Ajout de `JWT_SECRET_KEY=change-me-to-a-very-long-random-secret-min-32-characters`
- Ajout de `PROPRIO_EMAIL` et `PROPRIO_PASSWORD`

---

### 2. SMS — ActionDispatcher

**Problème :** `ActionDispatcher._execute_sms` appelait `self.sms.send_sms(...)` mais `TwilioSMSClient` ne possède que `send(to, body)`.

**Fichier :** `core/actions/dispatcher.py`

**Correctif :**
```python
success, result = await asyncio.to_thread(self.sms.send, phone, body)
```

---

### 3. SMS — Vault reminders

**Problème :** `_vault_reminders_loop` appelait `sms_client.send_sms(phone, msg)`.

**Fichier :** `luna_web.py:4410`

**Correctif :**
```python
sms_client.send(phone, f"Luna 📄 {msg}")
```

---

### 4. Instructions planifiées — Confirmation

**Problème :** `InstructionExecutor` appelait `self.action_service.create_action_request(...)` (méthode inexistante) et `action_service` n'était jamais injecté.

**Fichiers :** `core/instructions/executor.py`, `luna_web.py`

**Correctif :**
- Import de `ConfirmationManager`
- Injection dans `create_instruction_executor(..., action_service=_confirmation_manager)`
- Remplacement de `create_action_request` par `propose_action`
- Mapping des types d'actions internes vers `core.actions.models.ActionType`

---

### 5. OpenAI — Vérification au démarrage

**Problème :** Aucune vérification de la clé OpenAI au démarrage. Erreur 401 masquée par "Luna a un souci technique".

**Fichier :** `luna_web.py`

**Correctif :**
- Ajout de `_verify_openai_key_sync(client)` appelé après la création du client
- Variable globale `_openai_key_valid`
- `/health` retourne `{"openai": "ok" | "unconfigured"}`
- `/ready` retourne `degraded` si la clé est invalide
- `/api/chat` retourne un message explicite si OpenAI n'est pas configuré

---

## Tests de validation

| Test | Résultat attendu | Résultat obtenu |
|------|------------------|-----------------|
| `GET /health` | `openai: unconfigured` avec clé fausse | ✅ |
| `GET /ready` | `status: degraded`, `OPENAI_API_KEY: invalid_or_missing` | ✅ |
| `POST /api/chat` | Message explicite | ✅ |
| `POST /api/instructions` (SMS) | Confirmation proposée | ✅ |
| `POST /api/contacts` | Contact créé | ✅ |

---

## Fichiers modifiés

```
 .env.example                  |  7 +++++++
 core/actions/dispatcher.py    |  5 +----
 core/instructions/executor.py | 23 ++++++++++++++++++++---
 luna_web.py                   | 46 ++++++++++++++++++++++++++++++++++-----
 4 files changed, 71 insertions(+), 10 deletions(-)
```

---

## Prochaine phase : P1 — Robustesse

1. Persistance Redis fallback (SQLite ou Redis obligatoire)
2. Sessions Guardian persistantes dans Redis
3. Gestion du refus de géolocalisation
4. Confirmations d'actions persistantes
5. `PROPRIO_PASSWORD` hashé

---

*Aucun code modifié en dehors des corrections P0. Aucun push effectué.*
