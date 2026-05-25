# Cursor — Avis Objectif 010 — UI Mobile + Menu conversationnel

**Date** : 2026-05-25  
**Objectif** : 010 — Historique intelligent + mémoire utile Luna  
**Rôle** : UI/UX mobile, responsive, correction bug Connexion/Déconnexion  

---

## Mission Cursor

Auditer et implémenter le menu trois traits pour conversations, corriger le bouton
`Connexion/Déconnexion` coupé sur mobile, et vérifier responsivité sur petits écrans.

---

## Phase 1 — Audit UI mobile actuelle

### Points à vérifier

1. **Chat actuel sur petit écran** :
   - Quels éléments sont coupés ? (texte, boutons, etc.)
   - Padding/margin cohérents ?
   - Font size lisible (min 14px sur mobile) ?
   - Safe-area utilisée (notch, bottom bar) ?

2. **Bouton Connexion/Déconnexion** :
   - Où se trouve-t-il actuellement ? (haut-droit, footer ?)
   - Est-il vraiment coupé ? (`overflow: hidden` ?)
   - Qu'est-ce qui le coupe ? (parent container trop small ?)
   - Y a-t-il un menu compte/profile déjà présent ?

3. **Zone chat input** :
   - Input texte adapté à la largeur mobile ?
   - Bouton "Envoyer" accessible et cliquable ?
   - Clavier virtuel ne cache-t-il pas trop l'écran ?
   - Bottom padding pour ne pas être caché par keyboard (iOS) ?

### Livrables Phase 1

- Fichier : `CURSOR_AUDIT_010_UI_MOBILE.md`
- Contenu :
  - Screenshots petit écran (< 400px)
  - Éléments coupés identifiés
  - Safe-area zones
  - Propositions corrections

---

## Phase 2 — Menu trois traits (hamburger)

### Structure DOM proposée

```html
<!-- En haut, avant le titre "Chat" -->
<header class="chat-header">
  <button id="chatMenuToggle" class="chat-menu-toggle" aria-label="Conversations">
    <svg class="hamburger-icon" viewBox="0 0 24 24">
      <path d="M3 6h18M3 12h18M3 18h18"/>
    </svg>
  </button>
  
  <h1 class="chat-title">Chat</h1>
</header>

<!-- Panneau latéral conversations (hidden par défaut) -->
<aside id="chatSidebar" class="chat-sidebar is-hidden">
  <div class="chat-sidebar-header">
    <h2>Conversations</h2>
    <button id="closeSidebarBtn" class="close-btn" aria-label="Fermer">✕</button>
  </div>
  
  <button id="newConversationBtn" class="btn-new-conversation">
    + Nouvelle conversation
  </button>
  
  <div id="conversationsList" class="conversations-list">
    <!-- Rempli dynamiquement par JavaScript -->
  </div>
</aside>

<!-- Fond semi-transparent quand sidebar ouvert (mobile) -->
<div id="sidebarBackdrop" class="sidebar-backdrop is-hidden"></div>
```

---

## Phase 3 — CSS pour le menu

### Styling mobile-first

```css
/* Header */
.chat-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);
  color: white;
  gap: 12px;
}

/* Hamburger button */
.chat-menu-toggle {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hamburger-icon {
  width: 24px;
  height: 24px;
  stroke: white;
  stroke-width: 2;
  stroke-linecap: round;
}

/* Chat title */
.chat-title {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

/* Sidebar (fullscreen ou half-screen sur mobile) */
.chat-sidebar {
  position: fixed;
  top: 0;
  left: -100%;
  width: 280px;  /* Ou 100% - 60px si trop petit écran */
  height: 100vh;
  background: white;
  box-shadow: 2px 0 8px rgba(0,0,0,0.1);
  z-index: 1000;
  transition: left 0.3s ease;
  overflow-y: auto;
  padding-bottom: 20px;  /* Safe-area: bottom */
}

.chat-sidebar.is-visible {
  left: 0;
}

/* Sur écran > 768px, sidebar toujours visible */
@media (min-width: 768px) {
  .chat-sidebar {
    position: relative;
    left: 0;
    width: 250px;
    height: auto;
    box-shadow: none;
    border-right: 1px solid #e5e7eb;
  }
  
  .chat-menu-toggle {
    display: none;
  }
  
  .sidebar-backdrop {
    display: none;
  }
}

/* Sidebar header */
.chat-sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
}

.chat-sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Nouveau conversation button */
.btn-new-conversation {
  width: calc(100% - 32px);
  margin: 12px 16px;
  padding: 10px 16px;
  background: #8b5cf6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 14px;
}

/* Conversations list */
.conversations-list {
  padding: 0 8px;
}

.conversation-item {
  padding: 12px 16px;
  margin: 4px 0;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  user-select: none;
}

.conversation-item:hover {
  background: #f3f4f6;
}

.conversation-item.is-active {
  background: #ede9fe;
  border-left: 3px solid #8b5cf6;
  padding-left: 13px;
  font-weight: 600;
}

.conversation-title {
  font-size: 14px;
  font-weight: 500;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-date {
  font-size: 12px;
  color: #9ca3af;
  margin: 4px 0 0 0;
}

/* Backdrop */
.sidebar-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.3);
  z-index: 999;
  transition: opacity 0.3s;
}

.sidebar-backdrop.is-hidden {
  opacity: 0;
  pointer-events: none;
}

/* Petits écrans < 400px */
@media (max-width: 399px) {
  .chat-sidebar {
    width: 100%;  /* Fullscreen */
  }
  
  .chat-title {
    font-size: 16px;
  }
}
```

---

## Phase 4 — JavaScript interactions

```javascript
// Toggle sidebar
document.getElementById('chatMenuToggle').addEventListener('click', function() {
  const sidebar = document.getElementById('chatSidebar');
  const backdrop = document.getElementById('sidebarBackdrop');
  
  sidebar.classList.toggle('is-visible');
  backdrop.classList.toggle('is-hidden');
});

// Fermer sidebar
document.getElementById('closeSidebarBtn').addEventListener('click', function() {
  document.getElementById('chatSidebar').classList.remove('is-visible');
  document.getElementById('sidebarBackdrop').classList.add('is-hidden');
});

// Fermer sidebar quand on clique sur le backdrop
document.getElementById('sidebarBackdrop').addEventListener('click', function() {
  document.getElementById('chatSidebar').classList.remove('is-visible');
  this.classList.add('is-hidden');
});

// Nouvelle conversation
document.getElementById('newConversationBtn').addEventListener('click', function() {
  createNewConversation();
  // Fermer le sidebar sur mobile
  if (window.innerWidth < 768) {
    document.getElementById('chatSidebar').classList.remove('is-visible');
    document.getElementById('sidebarBackdrop').classList.add('is-hidden');
  }
});

// Charger conversation au click
document.addEventListener('click', function(e) {
  if (e.target.closest('.conversation-item')) {
    const item = e.target.closest('.conversation-item');
    const conversationId = item.dataset.conversationId;
    loadConversation(conversationId);
    
    // Fermer sidebar sur mobile
    if (window.innerWidth < 768) {
      document.getElementById('chatSidebar').classList.remove('is-visible');
      document.getElementById('sidebarBackdrop').classList.add('is-hidden');
    }
  }
});
```

---

## Phase 5 — Bug Connexion/Déconnexion

### Diagnostic

L'utilisateur rapporte que le bouton `Connexion` / `Déconnexion` est coupé sur mobile (le "n" est mangé).

**Causes possibles** :
- Width du bouton > largeur du container
- Padding/margin trop gros
- Parent container a `overflow: hidden`
- Font size trop gros pour le bouton

### Solution proposée

Trouver le bouton dans `static/index.html` (ex: `.auth-button`, `#loginBtn`, etc.) et ajuster CSS :

```css
/* Si le bouton est dans une navbar */
.navbar-auth {
  padding-right: 12px;  /* Safe-area pour mobile */
  margin-right: 0;
}

.auth-button {
  padding: 8px 12px;  /* Réduit sur mobile */
  font-size: 14px;    /* Lisible */
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;   /* Limite largeur */
}

/* Sur petit écran */
@media (max-width: 480px) {
  .auth-button {
    padding: 6px 8px;
    font-size: 12px;
    max-width: 90px;
  }
  
  /* Ou icone only si vraiment trop tight */
  .auth-button-text {
    display: none;  /* Cacher texte */
  }
  
  .auth-button-icon {
    display: inline;  /* Montrer icone seule */
  }
}

/* Safe-area bottom (iOS 11+) */
body {
  padding-bottom: env(safe-area-inset-bottom);
}

@media (max-width: 480px) {
  body {
    padding-bottom: max(12px, env(safe-area-inset-bottom));
  }
}
```

---

## Phase 6 — Vérification responsive petit écran

### Points de test

**Écran < 320px** (très petit) :
- [ ] Texte pas coupé ?
- [ ] Boutons cliquables (min 44x44px) ?
- [ ] Pas d'horizontal scroll ?

**Écran 320-480px** (mobile) :
- [ ] Chat input sur une ligne entière ?
- [ ] Bouton envoyer accessible (côté ou en bas) ?
- [ ] Sidebar menu fonctionne en fullscreen ?
- [ ] Bouton Connexion visible ?

**Écran 480-768px** (petite tablette) :
- [ ] Layout commence à respirer ?
- [ ] Sidebar peut rester visible ?
- [ ] Font sizes cohérentes ?

**Écran 768px+** (desktop) :
- [ ] Sidebar affiché en side panel ?
- [ ] Chat prend toute la width disponible ?
- [ ] Pas de changement brusque UI ?

---

## Phase 7 — Safe-area iOS/Android

### Utiliser les notches et zones sûres

```css
/* Haut avec notch (iPhone 12+) */
.chat-header {
  padding-top: max(12px, env(safe-area-inset-top));
}

/* Bas avec home indicator ou nav bar (tous téléphones) */
.chat-input-area {
  padding-bottom: max(12px, env(safe-area-inset-bottom));
}

/* Gauche avec notch vertical (certains Android) */
.chat-container {
  padding-left: max(12px, env(safe-area-inset-left));
  padding-right: max(12px, env(safe-area-inset-right));
}

/* Android WebView : full viewport-fit */
@supports (padding: max(0px)) {
  html {
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
}
```

---

## Livrables Cursor Objective 010

1. **CURSOR_AUDIT_010_UI_MOBILE.md** (Phase 1)
   - Screenshots petit écran
   - Éléments coupés
   - Propositions corrections

2. **Menu trois traits complet** (Phase 2-4)
   - DOM structure
   - CSS styling mobile-first
   - JavaScript interactions
   - Responsive breakpoints

3. **Correction bouton Connexion** (Phase 5)
   - Audit exact du problème
   - CSS fix minimal
   - Vérification responsive

4. **Safe-area iOS/Android** (Phase 7)
   - Notches/home indicator gérés
   - viewport-fit correct
   - Test sur vrai téléphone

5. **Tests responsivité** (avant livraison)
   - [ ] < 320px pas d'overflow
   - [ ] 320-480px mobile fluide
   - [ ] 480-768px tablette OK
   - [ ] 768px+ desktop OK
   - [ ] Safe-area bon (notch, nav bar)

---

## Validation attendue

- [ ] Menu trois traits accessible et intuitive
- [ ] Conversations listées et cliquables
- [ ] Sidebar responsive (fullscreen mobile, side panel desktop)
- [ ] Bouton Connexion/Déconnexion non coupé
- [ ] Pas d'horizontal scroll sur petit écran
- [ ] Safe-area respectées (notch, home indicator)
- [ ] Font sizes lisibles (min 14px)

---

## Prochaines étapes

Attendre DeepSeek (frontend structure) et Kimi (UX) pour intégration globale.

**Status** : ⏳ Menu trois traits implémentation commençant

