# IRIS WORKSPACE — Architecture Collaboration Multi-Participants

> **Date** : 26 mai 2026
> **Auteur** : Ludovic (fondateur) + Kimi
> **Statut** : Architecture + squelette backend
> **Scope** : Propriété, invités, cercles de confiance, filtrage données

---

## 1. Vision — Iris est un membre de l'équipe

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│   Iris n'est pas un chatbot.                                  │
│   Iris n'est pas un panneau de texte.                         │
│   Iris n'est pas un écran de dashboard.                       │
│                                                               │
│   Iris est un MEMBRE DE L'ÉQUIPE.                             │
│                                                               │
│   Elle est dans la salle.                                     │
│   Elle écoute tout le monde.                                  │
│   Elle projette sur l'écran central.                          │
│   N'importe qui peut lui parler.                              │
│   Elle répond à tous.                                         │
│   Elle appartient à UN souscripteur.                          │
│   Lui seul invite. Lui seul valide les actions engageantes.   │
│                                                               │
│   L'écran n'est pas une interface.                            │
│   L'écran est une SURFACE DE PROJECTION INTELLIGENTE.         │
│   Iris choisit ce qu'elle projette, quand, pour qui.          │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Modèle de données

### 2.1 Entités

```
Tenant (1)
 └── Subscriber (1) — le propriétaire d'Iris
      └── IrisSession (N)
           ├── ParticipantOwner (1) — le subscriber lui-même
           ├── ParticipantTrusted (N) — équipe permanente
           ├── ParticipantGuest (N) — invités temporaires
           └── Projection (N) — ce qui est affiché à l'écran
```

### 2.2 Rôles

| Rôle | Code | Description |
|---|---|---|
| **Owner** | `owner` | Le souscripteur. Tous les droits. |
| **Trusted** | `trusted` | Équipe permanente. Parle, voit, crée des tâches. Actions engageantes → validation owner. |
| **Guest** | `guest` | Invité temporaire. Parle, voit (filtré). Aucune action. Aucune donnée hors scope. |
| **Observer** | `observer` | Spectateur silencieux. Voir uniquement. Ne parle pas. |

### 2.3 Invitation

```python
class IrisInvitation(BaseModel):
    id: str                      # UUID
    session_id: str              # Session cible
    invited_by: str              # Participant ID (must be owner)
    email: Optional[str]         # Email de l'invité
    phone: Optional[str]        # SMS de l'invité
    role: Literal["trusted","guest","observer"]
    scope_project: Optional[str] # Projet auquel l'invité est lié (filtre données)
    expires_at: datetime         # 24h par défaut
    used_at: Optional[datetime]
    status: Literal["pending","accepted","expired","revoked"]
```

### 2.4 Participant en session

```python
class IrisParticipant(BaseModel):
    id: str
    session_id: str
    user_type: Literal["owner","trusted","guest","observer"]
    display_name: str
    avatar_url: Optional[str]
    joined_at: datetime
    last_seen_at: datetime
    scope_project: Optional[str]   # Filtrage : None = tout, sinon projet isolé
    can_speak: bool = True         # Guest/Trusted/Owner
    can_project: bool = True       # Tous sauf observer
    can_act: bool = False          # Uniquement owner
    can_invite: bool = False       # Uniquement owner
```

---

## 3. Matrice de permission (code source de vérité)

| Action | Owner | Trusted | Guest | Observer |
|---|---|---|---|---|
| Parler à Iris | ✅ | ✅ | ✅ | ❌ |
| Voir l'écran | ✅ Tout | ✅ Tout | ✅ Filtré | ✅ Filtré |
| Demander infos | ✅ Tout | ✅ Projet en cours | ✅ Son projet uniquement | ❌ |
| Créer une tâche | ✅ | ✅ | ❌ | ❌ |
| Assigner une tâche | ✅ | ✅ (dans l'équipe) | ❌ | ❌ |
| Envoyer email/SMS | ✅ | ⚠️ Validation owner | ❌ | ❌ |
| Passer un appel | ✅ | ⚠️ Validation owner | ❌ | ❌ |
| Signer un document | ✅ | ❌ | ❌ | ❌ |
| Paiement | ✅ | ❌ | ❌ | ❌ |
| Inviter quelqu'un | ✅ | ❌ | ❌ | ❌ |
| Exclure quelqu'un | ✅ | ❌ | ❌ | ❌ |
| Voir autres projets | ✅ | ❌ | ❌ | ❌ |
| Modifier droits | ✅ | ❌ | ❌ | ❌ |

> **⚠️ Validation owner** = Iris affiche une barre de confirmation dans le Command Screen. L'action est bloquée jusqu'à validation explicite du owner.

---

## 4. APIs Backend (FastAPI)

### 4.1 Gestion des sessions

```
POST   /api/iris/session              → Créer une session (owner)
GET    /api/iris/session/{id}         → Détails session + participants
DELETE /api/iris/session/{id}         → Fermer session (owner)
```

### 4.2 Invitations

```
POST   /api/iris/session/{id}/invite         → Créer invitation (owner)
GET    /api/iris/session/{id}/invitations    → Lister invitations
DELETE /api/iris/invitation/{token}           → Révoquer invitation (owner)
POST   /api/iris/invitation/{token}/accept    → Accepter invitation (invité)
```

### 4.3 Participants

```
GET    /api/iris/session/{id}/participants    → Lister participants
DELETE /api/iris/session/{id}/participants/{pid} → Exclure (owner)
PATCH  /api/iris/session/{id}/participants/{pid} → Modifier rôle (owner)
```

### 4.4 WebSocket — événements temps réel

Chaque événement WS contient un champ `visible_to` :

```json
{
  "type": "render",
  "render_type": "data_board",
  "payload": { ... },
  "visible_to": ["participant_id_1", "participant_id_2"]
}
```

Si `visible_to` est absent → visible par tous.

**Événements de présence** :
```json
{ "type": "presence", "participant_id": "...", "status": "joined|left|typing" }
```

---

## 5. Middleware de sécurité — `IrisSessionGuard`

### 5.1 Filtrage des données (scope_project)

```python
def filter_payload_for_participant(payload: dict, participant: IrisParticipant) -> dict:
    if participant.user_type == "owner":
        return payload
    if participant.scope_project:
        # Filtrer payload pour ne montrer que les données du projet autorisé
        return apply_project_filter(payload, participant.scope_project)
    # Trusted sans scope = voit tout sauf données sensibles owner
    return remove_sensitive_owner_data(payload)
```

### 5.2 Validation des actions engageantes

```python
def require_owner_confirmation(action_type: str, participant: IrisParticipant) -> bool:
    if participant.user_type == "owner":
        return False  # Owner n'a pas besoin de confirmation
    if action_type in {"send_email", "send_sms", "make_call", "sign_document", "payment"}:
        return True
    return False
```

Si confirmation requise :
1. Iris envoie `render_type: "action_board"` avec `requires_confirmation: true`
2. Le Command Screen affiche "Validation requise — Ludovic"
3. Owner clique "Confirmer"
4. Action exécutée

---

## 6. UX Multi-Participant (pour Kimi)

### 6.1 Ce qui change dans simli.html

**Barre de présence** (au-dessus du Command Screen) :
```
[Ludovic 👑] [Marie] [Pierre] [Sophie] [+ Inviter]
```
- Avatar rond, bordure verte si en ligne
- Tooltip au hover avec le rôle
- Owner a une couronne 👑

**Bulles de parole** :
- Quand un participant parle, son nom apparaît brièvement sous l'orb Iris
- Format : "Marie : 'Affiche les chiffres'"

**Filtrage visuel** :
- Si un guest demande des données hors scope → Iris affiche un `context_panel` rouge :
  "Ces informations sont confidentielles."

**Validation en direct** :
- Quand une action engageante est demandée par un trusted :
  - Le Command Screen passe en mode `action_board` avec `requires_confirmation`
  - Notification push au owner (bulle sur son avatar)
  - Timer : si pas de réponse en 60s → "Demande expirée"

### 6.2 Écrans à ajouter

1. **Invite Modal** — email ou lien à partager
2. **Participants Panel** — liste, rôles, exclure
3. **Permission Indicator** — icône dans le rail de statut indiquant le mode (solo / équipe / invité)

---

## 7. Prompt Claude — Implémentation Backend

```
Tu es Claude, lead technique backend.

MISSION : Implémenter le système de collaboration multi-participants pour Iris.

CONTEXTE :
- FastAPI existant (luna_web.py)
- WebSocket /ws/iris-voice existant
- JWT auth existant
- PostgreSQL via SQLAlchemy

LIVRABLES :
1. core/iris/participants.py — modèles Pydantic, enums, matrice permission
2. core/iris/session_guard.py — middleware filtrage + validation owner
3. core/iris/invitation.py — logique invitation (token JWT signé, expiration 24h)
4. Routes API dans luna_web.py :
   - POST /api/iris/session
   - POST /api/iris/session/{id}/invite
   - POST /api/iris/invitation/{token}/accept
   - GET /api/iris/session/{id}/participants
   - DELETE /api/iris/session/{id}/participants/{pid}
5. WS events : presence, visible_to filtering

RÈGLES :
- Aucun guest ne peut voir les données d'un autre projet
- Toute action engageante (SMS, email, paiement) = confirmation owner obligatoire
- Les invitations expirent après 24h
- Le token d'invitation est signé avec JWT_SECRET_KEY
- Pas de modification de schéma DB sans migration Alembic
- Tests unitaires sur la matrice de permission

NE PAS IMPLÉMENTER :
- Pas de paiement en ligne (scope hors sujet)
- Pas de visioconférence multi-stream (Daily.js reste 1-to-1 pour l'instant)
```

---

## 8. Prompt Kimi — Implémentation UX

```
Tu es Kimi, architecte UX frontend.

MISSION : Adapter simli.html pour le mode multi-participants.

CONTEXTE :
- simli.html est une page unique (~4000 lignes)
- Mode audio-first actif (OpenAI Realtime WS)
- Command Screen V1 avec 12 types de rendu
- CSS holographique existant (cyan #00D2FF, violet #8B74F7)

LIVRABLES :
1. Barre de présence (avatars + noms + rôles) au-dessus du Command Screen
2. Bulle de parole éphémère sous l'orb Iris (3s max)
3. Indicateur "mode session" dans le status rail (solo / équipe / invité)
4. Invite Modal (email + lien copiable)
5. Participants Panel (drawer latéral) — liste, exclure (owner only)
6. Filtrage visuel : message "Confidentiel" quand un guest demande hors scope

RÈGLES CSS :
- Même design system (monospace, angles vifs, verre fumé)
- Pas d'animation lourde
- Mobile first : drawer devient bottom-sheet
- Aucun emoji

NE PAS IMPLÉMENTER :
- Pas de drag & drop
- Pas de vidéo multi-participants
- Pas de chat texte séparé (la parole est le canal)
```

---

## 9. Roadmap collaboration

| Phase | Livrable | Priorité |
|---|---|---|
| P0 | Squelette backend (models + permissions) | 🔥 Urgent |
| P0 | Barre de présence dans simli.html | 🔥 Urgent |
| P1 | API invitation + token signé | Haute |
| P1 | Filtrage WS `visible_to` | Haute |
| P2 | Validation owner en temps réel | Haute |
| P2 | Invite Modal + Participants Panel | Moyenne |
| P3 | Historique des sessions persistant | Moyenne |
| P3 | Scope project automatique par contexte | Basse |

---

## 10. Principes immuables

1. **Iris est loyale à son souscripteur. Toujours.**
2. **Personne ne peut inviter à la place du souscripteur.**
3. **Les invités sont les bienvenus, mais dans le cadre défini.**
4. **L'écran raconte la conversation à tous — mais chacun ne voit que ce qu'il doit voir.**
5. **Une action engageante sans validation owner est un bug critique.**

---

*Document de travail. Squelette backend poussé en même temps que ce doc.*
