# Claude — Architecture Iris Teams (2 juin 2026)

> Objectif 020 — Iris comme membre d'équipe avec collaboration multi-participants
> **Domaine Claude : backend exclusivement**
> **Domaine Kimi : UX/UI exclusivement — ne pas dupliquer**
> Status : ARCHITECTURE — pas encore implémenté

---

## 0. Principe fondateur

```
Iris appartient à UN souscripteur.
Lui seul invite. Lui seul révoque. Lui seul signe.
Les invités parlent, voient, demandent. Rien de plus.
```

---

## 1. Modèle de données — Ce qu'il faut stocker

### 1.1 Session Iris

Une session = une instance de conversation partagée. Toujours propriété d'un souscripteur.

```python
IrisSession:
    session_id: str          # UUID — identifiant de la session
    tenant_id: int           # souscripteur propriétaire
    name: str                # "Session VoltAI", "Réunion BESS"
    created_at: datetime
    expires_at: datetime     # durée max configurable (défaut 8h)
    status: "active" | "ended"
    invite_token: str        # token court-vécu pour rejoindre (UUID, 1h)
    participants: List[Participant]
```

### 1.2 Participant

```python
Participant:
    participant_id: str      # UUID local à la session
    session_id: str
    name: str                # "Marie", "M. Dupont"
    role: "owner" | "trusted" | "guest"
    ws_connection_id: str    # WebSocket actif (None si déconnecté)
    joined_at: datetime
    projects_allowed: List[str]  # filtre projets visibles (vide = aucun filtre pour owner)
    can_trigger_actions: bool    # True seulement pour owner
    invite_confirmed_by: str     # tenant_id du souscripteur qui a invité
```

### 1.3 Action en attente de validation

```python
PendingAction:
    action_id: str
    session_id: str
    requested_by: str        # participant_id
    action_type: str         # "send_sms", "send_email", "call_contact"
    payload: dict
    status: "pending" | "approved" | "rejected"
    created_at: datetime
    expires_at: datetime     # auto-reject après 10 min
```

**Stockage : Redis** (TTL = durée de session). Pas de persistance longue durée.

---

## 2. API endpoints à ajouter dans `luna_web.py`

### Session management

```
POST   /api/iris/session/create          → crée une session, retourne session_id + invite_token
POST   /api/iris/session/{id}/invite     → génère un lien d'invitation pour un invité nommé
POST   /api/iris/session/{id}/revoke     → exclut un participant
GET    /api/iris/session/{id}/status     → liste des participants actuels + statuts
DELETE /api/iris/session/{id}            → ferme la session
```

### Actions en attente

```
GET    /api/iris/session/{id}/pending    → liste actions en attente de validation
POST   /api/iris/session/{id}/approve/{action_id}   → souscripteur approuve
POST   /api/iris/session/{id}/reject/{action_id}    → souscripteur rejette
```

### Rejoindre une session (pour les invités)

```
GET    /join/{invite_token}              → page HTML d'accueil invité
WS     /ws/iris-voice?session={id}&participant={pid}&token={jwt}
```

**Auth** : les invités reçoivent un JWT court-vécu signé avec `JWT_SECRET_KEY`.
Ce JWT contient : `session_id`, `participant_id`, `role`, `exp`.

---

## 3. Modifications `web_voice_bridge.py`

Le bridge reçoit déjà un `context` string. Il faut ajouter :

```python
class WebVoiceBridge:
    def __init__(
        self,
        ...
        session_id: Optional[str] = None,          # NOUVEAU
        participant_id: Optional[str] = None,      # NOUVEAU
        participant_role: str = "owner",           # NOUVEAU
        session_manager: Optional[IrisSessionManager] = None,  # NOUVEAU
    ):
```

### 3.1 Filtrage du contexte selon le rôle

```python
def _build_context_for_role(self, base_context: str, role: str, allowed_projects: List[str]) -> str:
    if role == "owner":
        return base_context  # accès complet
    if role == "trusted":
        # retire les données financières personnelles, les autres projets non listés
        return _filter_context(base_context, allowed_projects)
    if role == "guest":
        # ne garde que les données du projet autorisé
        return _minimal_context(base_context, allowed_projects)
```

### 3.2 Gating des actions engageantes

Dans `_handle_tool_call`, avant d'exécuter une action sensible :

```python
SENSITIVE_TOOLS = {"send_sms", "send_email", "call_contact", "alert_contacts", "request_payment"}

if function_name in SENSITIVE_TOOLS and self.participant_role != "owner":
    # Créer une PendingAction dans Redis
    pending = PendingAction(
        action_type=function_name,
        payload=args,
        requested_by=self.participant_id,
        session_id=self.session_id,
    )
    await self.session_manager.create_pending_action(pending)
    
    # Notifier le souscripteur (push WS)
    await self.session_manager.notify_owner(
        self.session_id,
        {"type": "action_pending", "action_id": pending.action_id,
         "requested_by": participant_name, "action": function_name}
    )
    
    # Répondre à Iris : action en attente
    return {"status": "pending_owner_approval", 
            "message": f"Action en attente de validation de {owner_name}."}
```

### 3.3 Broadcast du render à tous les participants

Quand `iris_render` est appelé (ou fallback transcript), broadcaster à tous :

```python
async def _broadcast_render(self, render_payload: dict):
    if self.session_manager and self.session_id:
        await self.session_manager.broadcast(self.session_id, render_payload)
    else:
        await self._ws_send_client(render_payload)  # mode solo
```

---

## 4. `IrisSessionManager` — Classe à créer

```python
# integrations/iris/session_manager.py

class IrisSessionManager:
    """Gère les sessions Iris multi-participants via Redis."""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def create_session(self, tenant_id: int, name: str) -> IrisSession
    async def get_session(self, session_id: str) -> Optional[IrisSession]
    async def add_participant(self, session_id: str, participant: Participant) -> bool
    async def remove_participant(self, session_id: str, participant_id: str)
    async def get_participants(self, session_id: str) -> List[Participant]
    async def broadcast(self, session_id: str, message: dict)
        # envoie le message à tous les WebSockets actifs de la session
    async def notify_owner(self, session_id: str, message: dict)
    async def create_pending_action(self, action: PendingAction) -> str
    async def approve_action(self, session_id: str, action_id: str) -> PendingAction
    async def reject_action(self, session_id: str, action_id: str) -> PendingAction
    async def close_session(self, session_id: str)
```

**Clés Redis :**
```
luna:iris:session:{session_id}              → hash session
luna:iris:session:{session_id}:participants → hash participants
luna:iris:session:{session_id}:pending      → hash actions en attente
luna:iris:session:{session_id}:ws           → hash ws_connection_id → participant_id
```

---

## 5. Système d'invitation — Flux complet

```
Souscripteur : "Iris, invite M. Dupont de BESS"
      ↓
IRIS appelle : invite_to_session(name="M. Dupont", project_filter=["BESS"])
      ↓
Backend :
  1. Crée Participant(role="guest", projects_allowed=["BESS"])
  2. Génère JWT signé (exp=1h)
  3. Génère URL : https://luna.yawatch.com/join/{invite_token}
  4. Optionnel : envoie SMS/email à M. Dupont (si souscripteur confirme)
      ↓
M. Dupont ouvre le lien
  1. GET /join/{token} → valide le token → page d'accueil simple
  2. WS /ws/iris-voice?session={id}&participant={pid}&token={jwt}
  3. Bridge démarre avec role="guest", projects_allowed=["BESS"]
      ↓
Iris dit à tous : "M. Dupont a rejoint la session."
Workspace affiche la mise à jour de la liste des participants.
```

**Outil à ajouter dans `VOICE_TOOLS` :**
```python
{
    "type": "function",
    "name": "invite_to_session",
    "description": "Inviter quelqu'un à rejoindre la session Iris. Génère un lien d'invitation.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "role": {"type": "string", "enum": ["trusted", "guest"]},
            "project_filter": {"type": "array", "items": {"type": "string"}},
            "send_sms": {"type": "boolean"},
            "phone_number": {"type": "string"}
        },
        "required": ["name"]
    }
}
```

---

## 6. Modifications `_IRIS_SYSTEM` (luna_web.py)

Ajouter une section collaboration quand une session est active :

```python
if session and len(session.participants) > 1:
    context += f"""
=== IRIS SESSION COLLABORATIVE ===
Session : {session.name}
Participants :
{chr(10).join([f"- {p.name} ({p.role})" for p in session.participants])}

Règles de collaboration :
- Tu réponds à la personne qui parle, mais tu projettes pour tous.
- Tu notes les décisions importantes sur l'écran.
- Actions engageantes (SMS, email, appel) : confirmation {owner_name} OBLIGATOIRE.
- Tu ne révèles JAMAIS les données d'un projet à un invité non autorisé.
- Tu gardes un compte-rendu des décisions prises en session.
"""
```

---

## 7. Nouveau render type : `session_panel`

Pour Kimi (UX) — panneau affiché quand plusieurs participants sont présents.

**Payload :**
```json
{
  "render_type": "session_panel",
  "payload": {
    "session_name": "Session VoltAI",
    "participants": [
      { "name": "Ludovic", "role": "owner", "status": "active" },
      { "name": "Marie",   "role": "trusted", "status": "active" },
      { "name": "M. Dupont", "role": "guest", "status": "active", "project": "BESS" }
    ],
    "pending_actions": [
      { "id": "abc123", "requested_by": "Marie", "action": "send_email", "to": "client@bess.fr" }
    ]
  }
}
```

---

## 8. Ce que Kimi doit concevoir (NE PAS CODER SOI-MÊME)

- Overlay participants dans le Workspace : mini-liste en haut, icônes rôle (👑 owner, 👤 trusted, 🟢 guest)
- Notification visuelle quand un invité rejoint / quitte
- Panneau "action en attente de validation" avec bouton Approuver / Rejeter
- Badge discret sur l'écran quand des données filtrées ne sont pas montrées
- Page `/join/{token}` — accueil simple pour les invités

Kimi livre dans : `KIMI_UX_IRIS_TEAMS_020.md`
Claude implémente après validation Ludo.

---

## 9. Roadmap d'implémentation

### Étape 1 — Fondations (Redis, SessionManager, API)
```
integrations/iris/session_manager.py  (nouveau)
luna_web.py : POST /api/iris/session/*
```

### Étape 2 — Bridge collaboratif
```
web_voice_bridge.py : session_id, participant_role, action gating, broadcast render
luna_web.py : WS /ws/iris-voice route modifiée (paramètre session optionnel)
```

### Étape 3 — Invitation
```
luna_web.py : GET /join/{token} + page HTML invité
VOICE_TOOLS : invite_to_session
```

### Étape 4 — Workspace collaboratif
```
simli.html : render session_panel + affichage participants + validation actions
```

**Tout ceci se greffe sur l'existant. Le mode solo (actuel) reste intact.**
Si `session_id` absent → comportement actuel inchangé.

---

## 10. Ce qui ne change PAS

- `gpt-realtime-mini` reste le modèle (contrainte compte OpenAI)
- Mode solo fonctionne sans aucune session
- Les 12 types de projection du Workspace restent le chantier Phase 1
- `iris_render` et le fallback transcript restent le mécanisme de projection

---

*Claude — lead technique — 2 juin 2026*
*Split domaines : Claude = backend / Kimi = UX / Codex = test / DeepSeek = inférence*
