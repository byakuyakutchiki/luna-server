# Intégration frontend des confirmations Redis

> Document de suivi du wiring frontend ↔ backend pour le `ConfirmationManager` de YAWatch-Luna (Sprint B).

## Objectif

S'assurer que les actions proposées par Luna (SMS, appel, alerte, visio, email, paiement) et stockées dans Redis via `ConfirmationManager` sont :

1. Listées en temps réel dans l'interface principale (`/`).
2. Confirmables ou refusables par l'utilisateur d'un clic.
3. Persistantes après rechargement de page ou redémarrage du serveur.

## Architecture

```text
┌─────────────────┐      GET /api/actions/pending      ┌─────────────────────┐
│  static/index   │ ─────────────────────────────────> │   luna_web.py       │
│   (frontend)    │                                     │   /api/actions/*    │
│                 │ <───────────────────────────────── │                     │
└─────────────────┘      JSON [{action_id, type, ...}] └─────────────────────┘
         │                                                        │
         │ POST /api/actions/{id}/confirm                         │
         │ POST /api/actions/{id}/reject                          ▼
         │                                               ┌─────────────────┐
         └─────────────────────────────────────────────> │ ConfirmationManager
                                                         │   (Redis)       │
                                                         └─────────────────┘
```

## Routes backend

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/api/actions/pending` | Liste les actions en attente du tenant courant. |
| `POST` | `/api/actions/{action_id}/confirm` | Confirme une action (`method="button"`). |
| `POST` | `/api/actions/{action_id}/reject` | Refuse une action (body optionnel `{reason}`). |

### Exemple de réponse `GET /api/actions/pending`

```json
{
  "actions": [
    {
      "action_id": "6be50fa5-dcf1-4cac-b4b5-a94734b0b0e0",
      "tenant_id": 16,
      "action_type": "send_sms",
      "target": "Marie",
      "description": "envoyer un SMS à Marie",
      "message_body": "Salut Marie, c'est Luna.",
      "status": "awaiting_confirmation",
      "created_at": "2026-06-15T17:04:13.608246",
      "expires_at": "2026-06-15T17:14:13.608206"
    }
  ]
}
```

## Changements frontend (`static/index.html`)

### 1. Polling

Un polling dédié est démarré dans `showApp()` et arrêté dans `doLogout()` :

```javascript
startPendingActionsPolling();   // toutes les 15 secondes
```

### 2. Panneau UI

Un bandeau s'affiche sous le header quand des actions sont en attente (`#pendingActionsPanel`).

Pour chaque action, il affiche :
- Le type d'action (SMS, appel, alerte, visio, email, paiement).
- La description et le message si applicable.
- Deux boutons : **Confirmer** (vert) et **Refuser** (rouge).

### 3. Résolution

Au clic :

```javascript
authFetch("/api/actions/" + actionId + "/confirm", {method: "POST"});
// ou
authFetch("/api/actions/" + actionId + "/reject", {method: "POST", body: JSON.stringify({reason: "refused_by_user"})});
```

La liste est rafraîchie immédiatement après la réponse.

## Tests locaux validés

1. Créer une action pending via `ConfirmationManager` (script Python) → clé Redis créée.
2. Appeler `GET /api/actions/pending` → l'action est retournée.
3. Cliquer sur **Confirmer** (ou `POST /confirm`) → statut `confirmed`, disparition de la liste.
4. Créer une nouvelle action, cliquer sur **Refuser** (ou `POST /reject`) → statut `rejected`.
5. Rafraîchir la page → les actions pending restent visibles (persistance Redis).

## Délai d'expiration

Par défaut, une action expire après 10 minutes (`DEFAULT_EXPIRATION_MINUTES`).
Une fois expirée, elle n'apparaît plus dans le panneau et son statut Redis passe à `expired`.

## Intégrations liées

- Les actions confirmées par l'utilisateur sont ensuite exécutées par `InstructionExecutor`.
- Pour les SMS/appels, l'exécution passe par Twilio (voir `TEST_TWILIO_OPENAI.md`).
- Le panneau n'interfère pas avec le flux Iris/Simli qui a ses propres routes `/api/iris/session/{id}/pending`.

## Fichiers concernés

- `luna_web.py` — routes `/api/actions/*`.
- `static/index.html` — panneau, polling, résolution.
- `core/actions/models.py` — ajout de `ActionRequest.to_dict()` pour la sérialisation API.
- `core/actions/confirmation.py` — moteur de confirmation (inchangé, déjà fonctionnel).
