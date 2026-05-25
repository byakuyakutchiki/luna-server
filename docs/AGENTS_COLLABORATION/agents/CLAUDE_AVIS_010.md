# Claude — Avis Objectif 010 — Historique + Mémoire Luna

**Date** : 2026-05-25  
**Objectif** : 010 — Historique intelligent + mémoire utile Luna  
**Rôle** : Lead backend, intégration, décisions architecture  

---

## Mission Claude

Auditer le stockage chat actuel, proposer l'architecture backend pour conversations
et mémoire utile, définir les endpoints, et arbitrer les décisions d'intégration.

---

## Phase 1 — Audit de l'existant

### À investiguer

1. **Stockage chat actuel** :
   - Où sont stockés les messages ? (Redis, base de données, localStorage, mémoire)
   - Format du message actuel ? (JSON schema, champs, taille moyenne)
   - Durée de rétention ? (24h, 30j, infini)
   - Y a-t-il déjà une notion de "conversation" ou tout est linear ?

2. **API existante** :
   - Endpoint `/api/chat` ou équivalent ?
   - Méthode GET/POST ?
   - Paramètres (limit, offset, timestamp range, etc.) ?
   - Rate limit ?

3. **Frontend chat actuel** (`static/index.html`) :
   - Où est stockée la liste des messages ?
   - Comment le chat affiche-t-il les messages ?
   - Y a-t-il déjà un localStorage pour persistance ?
   - Comment gère-t-il la reconnexion ?

### Livrables Phase 1

- Fichier : `CLAUDE_AUDIT_010_CHAT_EXISTANT.md`
- Contenu :
  - Schéma stockage actuel
  - API endpoints existantes
  - Limitations identifiées
  - Points d'intégration proposés

---

## Phase 2 — Proposer le modèle backend

### Architecture conversations proposée

Créer trois structures :

#### 1. Conversations (header)

```python
class Conversation(BaseModel):
    conversation_id: str  # UUID
    tenant_id: int
    user_id: int
    title: str  # Titre automatique ou utilisateur
    description: Optional[str]  # Résumé court
    created_at: datetime
    updated_at: datetime
    messages_count: int
    is_active: bool
    tags: List[str]  # ex: ["voix", "memoire", "objectif-010"]
```

Stockage : Redis ou base durable (PostgreSQL si dispo)

#### 2. Messages (contenu)

```python
class Message(BaseModel):
    message_id: str  # UUID
    conversation_id: str
    sender: str  # "user" ou "luna"
    content: str  # Texte du message
    timestamp: datetime
    metadata: Dict  # ex: {"audio": false, "tool_used": "..."}
```

Stockage : Même système que Conversation

#### 3. Mémoire utile

```python
class LunaMemory(BaseModel):
    memory_id: str  # UUID
    tenant_id: int
    memory_type: str  # "project" | "user" | "conversation"
    key: str  # Clé de recherche
    value: str  # Contenu (court, 500 chars max)
    created_at: datetime
    updated_at: datetime
    is_active: bool
```

Stockage : Redis (cache rapide) + base de secours

---

## Phase 3 — Endpoints backend à créer

### Conversations

```
GET /api/chat/conversations?limit=20&offset=0
  → Retourne liste conversations, triée par updated_at DESC
  
POST /api/chat/conversations
  → Crée une nouvelle conversation
  → Body: {"title": "Titre optionnel", "description": ""}
  → Retourne: {conversation_id, created_at}

GET /api/chat/conversations/{conversation_id}
  → Retourne une conversation + ses messages (limit 50)
  
PUT /api/chat/conversations/{conversation_id}
  → Met à jour titre/description
  
DELETE /api/chat/conversations/{conversation_id}
  → Soft-delete (marquer is_active=false)
```

### Messages

```
GET /api/chat/conversations/{conversation_id}/messages?limit=50&offset=0
  → Messages de la conversation
  
POST /api/chat/conversations/{conversation_id}/messages
  → Ajoute un message
  → Body: {"sender": "user", "content": "..."}
  → Retourne: {message_id, timestamp}
```

### Mémoire

```
GET /api/luna/memory?type=project&limit=20
  → Retourne mémoire utile par type
  
POST /api/luna/memory
  → Ajoute un élément mémoire (admin/founder seulement)
  → Body: {"memory_type": "project", "key": "architecture", "value": "..."}
```

---

## Phase 4 — Décisions d'intégration

### localStorage vs serveur vs Redis

**localStorage (client)** :
- ✅ Rapide, pas de sync
- ❌ Limité (~5MB)
- ❌ Perte si cache cleared
- Usage : liste conversations cache, tags locaux

**Redis (serveur, cache court terme)** :
- ✅ Très rapide
- ✅ Partagé entre sessions
- ❌ Volatile (data perdues si redis crash)
- Usage : mémoire projet, tags chauds, sessions actives

**Base de données durable** (PostgreSQL, Cloud Firestore) :
- ✅ Persistance garantie
- ✅ Requêtes complexes
- ❌ Plus lent que Redis
- Usage : conversations history, messages, mémoire importante

**Recommandation** :
- Redis pour mémoire projet (cohérence rapide)
- Base durable pour conversations/messages (garantie)
- localStorage pour cache conversations liste uniquement

---

## Phase 5 — Sécurité mémoire

### Garde-fous critiques

```python
# NE JAMAIS stocker en mémoire durable :
- Clés API (OpenAI, Stripe, Twilio)
- Tokens JWT / secrets
- Mots de passe
- Numéros de CB / données privées
- Transcripts vocaux bruts (audio)
- Logs techniques détaillés

# OK à stocker :
- Résumé conversation (ex: "Discussion voix Luna")
- État objectifs validés (ex: "Objectif 008 — voix stable")
- Architecture Luna (ex: "Pipeline APK → serveur → OpenAI")
- Décisions Ludovic (ex: "Objectif 009 en cours")
- Méta-informations publiques
```

### Audit mémoire

- [ ] Aucune clé API en mémoire
- [ ] Aucun token JWT en mémoire
- [ ] Aucun transcript vocal brut
- [ ] Aucune donnée utilisateur privée inutile
- [ ] Chiffrement des données sensibles si présent

---

## Phase 6 — Titre automatique

### Stratégie minimale

Après 2-4 messages, générer un titre :

**Option A** (simple local) :
- Extraire les mots-clés des 3-4 premiers messages
- Construire titre : "Voix Luna" + "et" + "OpenAI Realtime"
- Template : `{subject1} et {subject2}` ou `{subject1} — {detail}`

**Option B** (LLM serveur) :
- Envoyer 3-4 premiers messages à Claude/GPT
- Demander : "Propose un titre court (5-8 mots max) pour cette conversation"
- Retour : titre via prompt system

**Recommandation** :
- Commencer avec Option A (local, rapide)
- Passer à Option B si nécessaire (meilleure qualité)
- Ne jamais bloquer l'envoi du message si titre échoue

### Fallback

Si titre auto échoue :
```
"Nouvelle conversation" (défaut)
"Conversation du 25 mai" (avec date)
```

---

## Phase 7 — Intégration côté serveur

### Modification `luna_web.py`

Ajouter endpoints conversationnels :

```python
# Dans luna_web.py

@app.get("/api/chat/conversations")
async def list_conversations(request: Request):
    """Retourne les conversations de l'utilisateur."""
    jwt_payload = _decode_client_token(...)
    tenant_id = jwt_payload.get("tenant_id")
    
    # Récupérer Redis ou base de données
    conversations = _redis_client.lrange(f"luna:{tenant_id}:conversations", 0, 20)
    return {"conversations": conversations}

@app.post("/api/chat/conversations")
async def create_conversation(request: Request, body: Dict):
    """Crée une nouvelle conversation."""
    conversation_id = str(uuid4())
    # Ajouter à Redis + base durable
    return {"conversation_id": conversation_id, "created_at": datetime.now()}

# ... autres endpoints
```

---

## Points clés pour Claude

1. **Ne pas refactor le chat existant**
   - Ajouter structure conversations par-dessus
   - Garder messages existants fonctionnels
   - Migration progressive, pas big-bang

2. **Mémoire utile doit être **discrète**
   - Luna ne récite pas sa mémoire
   - Elle l'utilise quand c'est pertinent
   - Pas de "je sais que..." inutile

3. **Sécurité d'abord**
   - Zéro secrets en mémoire
   - Audit stricte avant déploiement
   - Validation Ludovic sur le modèle

4. **Performance**
   - Conversations list < 100ms
   - Messages load < 200ms
   - Titre auto ne doit pas bloquer

---

## Livrables Claude Objective 010

1. **CLAUDE_AUDIT_010_CHAT_EXISTANT.md** (Phase 1)
   - Schéma stockage actuel
   - API endpoints détaillés
   - Limitations proposées

2. **Code backend conversations** (Phase 6-7)
   - Endpoints `/api/chat/conversations*`
   - Modèles Pydantic
   - Redis/DB storage

3. **Intégration mémoire utile** (Phase 4-5)
   - Endpoint `/api/luna/memory`
   - Garde-fous sécurité
   - Audit document

4. **Tests intégration** (avant déploiement)
   - Créer conversation → lister → ouvrir → nouvelle message
   - Retirer une conversation
   - Mémoire projet chargée sans secret

---

## Validation Ludovic attendue

- [ ] Modèle backend approuvé
- [ ] Endpoints performants
- [ ] Mémoire utile sans secret
- [ ] Titre automatique fonctionnel
- [ ] Test sur téléphone avant déploiement

---

## Prochaines étapes après Claude

Attendre les audits de DeepSeek (frontend) et Kimi (UX) pour proposition finale.

**Status** : ⏳ Audit de l'existant commençant

