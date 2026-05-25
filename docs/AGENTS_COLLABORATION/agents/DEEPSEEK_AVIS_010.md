# DeepSeek — Avis Objectif 010 — Frontend Chat + Structure conversations

**Date** : 2026-05-25
**Objectif** : 010 — Historique intelligent + mémoire utile Luna
**Rôle** : Audit technique frontend, séparation conversations, structure minimale

---

## Mission DeepSeek

Auditer le chat actuel dans `static/index.html`, proposer la structure frontend pour
conversations, vérifier comment séparer les messages sans casser la mémoire, et
proposer un modèle minimal conversation/message/titre.

---

## Phase 1 — Audit frontend chat existant

### Points à investiguer dans `static/index.html`

1. **Zone chat actuelle** :
   - ID/classe du conteneur chat principal (ex: `#chatMessages`, `.chat-container`)
   - Comment sont ajoutés les messages ? (appendChild, innerHTML, templating ?)
   - Format du message DOM (ex: `<div class="message user">...`)
   - Scrolling automatique en bas ? (scroll-to-bottom)

2. **Menu trois traits** :
   - Existe-t-il déjà ? (hamburger button)
   - Si oui, où et quels menus sont dedans actuellement ?
   - Si non, proposer l'endroit le meilleur (haut gauche mobile-first)

3. **Stockage messages actuel** :
   - Où vit la liste des messages ? (variable globale, `localStorage`, fetch serveur)
   - Comment persiste-t-elle entre rechargement de page ?
   - Y a-t-il déjà des messages persistants ou c'est éphémère ?

4. **Mémoire Luna dans le prompt** :
   - Où est défini le contexte systèmes de Luna ?
   - Est-ce dans `static/index.html` ou dans `luna_web.py` ?
   - Taille du contexte actuel ?

### Livrables Phase 1

- Fichier : `DEEPSEEK_AUDIT_010_FRONTEND.md`
- Contenu :
  - Map du chat DOM actuel
  - Structure de la liste messages
  - Localisation du menu burger (ou où l'ajouter)
  - Localisation de la mémoire/contexte Luna

---

## Phase 2 — Proposer structure frontend conversations

### Modèle données minimal (JSON)

```javascript
// Structure une conversation en mémoire
const conversation = {
  conversation_id: "uuid-v4",          // Unique
  title: "Voix Luna et OpenAI",        // Auto-générée ou user
  created_at: "2026-05-25T20:00:00Z",
  updated_at: "2026-05-25T20:12:00Z",
  messages: [
    {
      message_id: "uuid-1",
      sender: "user",
      content: "Comment fonctionne la voix Luna ?",
      timestamp: "2026-05-25T20:00:10Z"
    },
    {
      message_id: "uuid-2",
      sender: "luna",
      content: "Luna utilise OpenAI Realtime API...",
      timestamp: "2026-05-25T20:00:15Z"
    }
  ]
};
```

### Stockage frontend

```javascript
// Dans localStorage (cache local) :
// Clé: luna:conversations:list = [{id, title, updated_at, ...}]
// Clé: luna:conversation:UUID = full conversation object
// Clé: luna:current_conversation_id = UUID actif

const _lunaConversations = [];  // Liste en mémoire
let _lunaCurrentConversation = null;  // Conversation active
```

---

## Phase 3 — Implémenter le menu trois traits

### Proposer la structure DOM

```html
<!-- Haut-gauche, avant le titre principal -->
<div id="chatMenu" class="chat-menu-toggle">
  <button id="chatMenuBtn" class="hamburger-btn">
    <span></span><span></span><span></span>  <!-- Trois traits -->
  </button>

  <!-- Panneau latéral (hidden par défaut) -->
  <div id="chatSidebar" class="chat-sidebar">
    <div class="chat-sidebar-header">
      <h3>Conversations</h3>
      <button id="newConversationBtn">+ Nouvelle</button>
    </div>

    <div id="conversationsList" class="conversations-list">
      <!-- Rempli dynamiquement -->
    </div>
  </div>
</div>
```

### Comportement interactions

- Clic sur trois traits → toggle sidebar
- Clic sur conversation → charger cette conversation
- Clic "+ Nouvelle" → nouvelle conversation vide
- Clic sur conversation active → reste active (highlight)

---

## Phase 4 — Séparation conversations sans casser la mémoire

### Problème

Actuellement, il y a probablement une liste globale de messages.
Il faut la séparer par conversation, mais sans perdre les anciens messages.

### Solution proposée

```javascript
// Avant : une liste linéaire
const messages = [...];

// Après : conversations séparées
const conversations = {
  "uuid-1": { title: "Convo 1", messages: [...] },
  "uuid-2": { title: "Convo 2", messages: [...] },
};

// Migration :
// 1. Au premier chargement, tous les messages existants → une "conversation legacy"
// 2. Les nouveaux messages créent des conversations distinctes
// 3. Pas de perte de données
```

### Code clé

```javascript
function initConversations() {
  // Charger depuis localStorage ou serveur
  const stored = localStorage.getItem("luna:conversations:list");
  if (stored) {
    _lunaConversations = JSON.parse(stored);
  } else {
    // Première fois : créer une conversation legacy
    const legacyId = generateUUID();
    _lunaConversations.push({
      conversation_id: legacyId,
      title: "Conversation initiale",
      created_at: new Date().toISOString(),
      messages_count: 0
    });
  }

  // Charger la conversation courante
  const currentId = localStorage.getItem("luna:current_conversation_id");
  _lunaCurrentConversation = currentId || _lunaConversations[0].conversation_id;

  // Afficher la liste
  renderConversationsList();
}
```

---

## Phase 5 — Génération titre automatique (frontend)

### Heuristique simple locale

```javascript
function generateConversationTitle(messages) {
  if (messages.length === 0) return "Nouvelle conversation";

  // Extraire mots-clés des 3 premiers messages
  const firstMessages = messages.slice(0, 3).map(m => m.content);
  const keywords = extractKeywords(firstMessages.join(" "));

  // Construire titre court
  if (keywords.length >= 2) {
    return `${keywords[0]} et ${keywords[1]}`;
  } else if (keywords.length === 1) {
    return keywords[0];
  }
  return "Nouvelle conversation";
}

function extractKeywords(text) {
  // Heuristique basique : mots importants > 4 chars, pas stop-words
  const stopWords = ["pour", "avec", "sans", "dans", "Luna", "comment", "pourquoi"];
  const words = text.toLowerCase()
    .split(/\s+/)
    .filter(w => w.length > 4 && !stopWords.includes(w));

  // Retirer doublons, garder top 3
  return [...new Set(words)].slice(0, 3);
}
```

### Éviter les titres dégueulasses

```javascript
// NE PAS accepter :
- "a b c d e f"
- "..."
- "undefined"
- Titres vides

// ACCEPTER :
- "Voix Luna et OpenAI"
- "Documents — Porte-documents"
- "Réglages exploitant"
```

---

## Phase 6 — Vérifier cache/localStorage cohérence

### Problème potentiel

WebView Android peut garder du cache stale → anciennes conversations affichées
avec nouveau titre.

### Vérifications

```javascript
// À faire au démarrage :

// 1. Vérifier version de la structure conversations
const schemaVersion = localStorage.getItem("luna:conversations:schema");
if (schemaVersion !== "2") {
  // Nettoyer et recréer
  localStorage.removeItem("luna:conversations:list");
  localStorage.removeItem("luna:current_conversation_id");
  initConversations();
}

// 2. Vérifier que la conversation actuelle existe
const currentId = localStorage.getItem("luna:current_conversation_id");
const exists = _lunaConversations.some(c => c.conversation_id === currentId);
if (!exists) {
  // Fallback à la première
  _lunaCurrentConversation = _lunaConversations[0].conversation_id;
}

// 3. Forcer refresh depuis serveur si dernière sync > 1h
const lastSync = localStorage.getItem("luna:conversations:last_sync");
const now = Date.now();
if (now - parseInt(lastSync || 0) > 3600000) {
  // Refetch depuis serveur
  syncConversationsFromServer();
}
```

---

## Phase 7 — Fonction chargement conversation

### Quand utilisateur clique sur une conversation

```javascript
async function loadConversation(conversationId) {
  // 1. Mettre à jour la conversation courante
  _lunaCurrentConversation = conversationId;
  localStorage.setItem("luna:current_conversation_id", conversationId);

  // 2. Charger les messages (depuis localStorage ou serveur)
  const convo = _lunaConversations.find(c => c.conversation_id === conversationId);
  if (!convo) return;

  // 3. Vider la zone chat et afficher les messages de cette conversation
  clearChatMessages();

  // Charger depuis serveur (délégataire Claude)
  const messages = await fetch(`/api/chat/conversations/${conversationId}/messages`)
    .then(r => r.json())
    .then(data => data.messages || []);

  // 4. Afficher les messages
  messages.forEach(msg => renderMessage(msg));

  // 5. Scroll au bas
  scrollChatToBottom();

  // 6. Focus input pour nouveau message
  document.getElementById("chatInput").focus();
}
```

---

## Points clés pour DeepSeek

1. **Pas de gros refactor du chat**
   - Ajouter les conversations par-dessus
   - Garder le rendu messages existant fonctionnel
   - Modifications minimales du DOM

2. **Cache cohérence**
   - Vérifier localStorage propre au démarrage
   - Forcer sync serveur si doute
   - Fallback robuste si conversation manquante

3. **Performance frontend**
   - Pas de rendu tous les messages à chaque fois
   - Pagination/lazy-loading si 1000+ messages
   - Pas de freeze UI lors du chargement

4. **Compatibilité WebView**
   - localStorage fonctionne sur Android WebView
   - Éviter API non-supportées
   - Tester sur petit écran

---

## Livrables DeepSeek Objective 010

1. **DEEPSEEK_AUDIT_010_FRONTEND.md** (Phase 1)
   - Map du chat DOM actuel
   - Localisation menu burger
   - Structure messages

2. **Code conversations frontend** (Phase 2-7)
   - Structure JSON conversations
   - Menu trois traits + sidebar
   - Chargement/listing conversations
   - Génération titre auto

3. **Vérifications cohérence** (Phase 6)
   - Audit localStorage
   - Fallback robuste
   - Sync serveur si besoin

4. **Tests frontend** (avant livraison)
   - Créer conversation → voir dans liste
   - Charger ancienne conversation → messages affichés
   - Nouvelle conversation → liste mise à jour
   - Titre auto généré correctement

---

## CLARIFICATION LUDOVIC (26 mai) — Titrage intelligent + Recherche

### Nouveau besoin urgent

**Titrage** : Générer titre intelligent **localement** après 1er message
- Extraire mots-clés du message utilisateur
- Construire titre court (5-10 mots) selon règles Kimi
- Mettre à jour immédiatement dans la liste historique

**Recherche** : Barre recherche dans le panneau
- Filtrer conversations par titre + mot dans messages
- Recherche locale sur localStorage (débounce 200ms)
- Afficher résultats matching > 70%

### Nouvelles missions DeepSeek

#### 1. Heuristique titrage local (PRIORITAIRE)

```javascript
function generateConversationTitle(messages) {
  // Extraire top 3-4 mots importants du 1er message user
  // Appliquer règles Kimi (éliminer stop-words, capitaliser)
  // Construire titre court "Sujet1 et Sujet2" ou "Sujet — détail"
  // Retourner titre intelligible
}
```

Timing : doit s'exécuter en < 100ms (pas de lag)

#### 2. Recherche locale sur localStorage

```javascript
function searchConversations(query) {
  // Filter conversations :
  //   - title.includes(query)
  //   - first_message.includes(query)
  // Trier par pertinence (title match > content match)
  // Retourner top 10 résultats
}
```

Debounce 200ms pour éviter flicker.

#### 3. Architecture ready pour recherche serveur

Proposer endpoint `/api/chat/search` mais **ne pas l'implémenter** maintenant.

#### 4. Pas de refactor

- [ ] Chat existant reste intact
- [ ] Ajouter titrage par-dessus
- [ ] localStorage utilisé pour cache titres
- [ ] Fallback "Conversation du DD/MM" si génération échoue

**Livrables DeepSeek (updated)** :
1. Heuristique titrage local + tests
2. Code recherche locale (localStorage)
3. Barre recherche intégrée (avec Cursor)
4. Performance : titrage < 100ms, recherche < 100ms
5. Tests : "Voix" trouve "Voix Luna instable"

---

## Validation attendue

- [ ] Chat existant non cassé
- [ ] Conversations listées et persistantes
- [ ] **Titre auto généré immédiatement après 1er message**
- [ ] **Titre intelligible (pas "a b c d", pas "Nouvelle conversation")**
- [ ] Chargement conversation fluide
- [ ] Cache cohérent (pas d'anciennes données)
- [ ] **Recherche locale fonctionne (debounce 200ms)**
- [ ] **Performance < 100ms pour titrage et recherche**

---

## Prochaines étapes

Parallèle :
- Kimi : règles titrage + UX recherche
- Cursor : barre recherche CSS mobile
- Claude : architecture titrage (serveur vs client)

**Status** : 🔄 Titrage + recherche implémentation

