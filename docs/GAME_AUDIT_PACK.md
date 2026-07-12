# GAME_AUDIT_PACK — Audit des jeux Luna (pour DeepSeek)

> Préparé par Claude Code avec **accès local direct** au code source
> (`/home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/`). DeepSeek n'a pas accès à GitHub :
> ce document + le zip `game_audit_pack.zip` contiennent **tout le code réel** nécessaire.
> **Aucune modification n'a été faite au code** — c'est un pack d'audit en lecture seule.

---

## 0. À LIRE EN PREMIER — 3 corrections de cadrage

L'audit préliminaire de DeepSeek raisonnait « à l'aveugle » sur des noms qui **n'existent pas dans le code**. Voici la réalité :

### 0.1 Les noms des jeux
`grep -rniE "morpheus|tweak|tarot"` sur **tout** le serveur = **0 résultat**. Les 3 vrais jeux sont :

| Nom demandé | Jeu réel dans le code | `game_type` | Statut |
|---|---|---|---|
| Quiz | **Quiz** (QCM 5 questions) | `"quiz"` | ✅ existe |
| Morpheus | **Morpion** (tic-tac-toe 3×3) | `"morpion"` | ✅ existe |
| Tweak | **Memory** (8 paires d'emojis) | `"memory"` | ✅ existe |
| Taroté | — | — | ❌ n'existe pas (jamais codé) |

→ **Auditer les 3 : Quiz, Morpion, Memory.** Il n'y a rien à exclure (Taroté n'existe pas).

### 0.2 Les jeux ne sont PAS des routes `/quiz` `/morpheus` `/tweak`
Il n'y a aucune route HTTP par jeu. Les 3 jeux sont des **modes à l'intérieur du système de SALONS (rooms)**. Tout passe par **un seul WebSocket** : `/api/rooms/{room_id}/ws`, avec des messages typés (`game_start`, `game_action`, `game_update`). La logique de jeu est centralisée serveur dans `core/rooms/manager.py`.

### 0.3 Le frontend des jeux est dans `salon.html`, PAS `index.html`
- `static/salon.html` (4669 lignes) = **la salle** : chat de salle, participants, jeux (Quiz/Morpion/Memory), cinéma YouTube, karaoké. **C'est ici qu'il faut auditer les jeux.**
- `static/index.html` (9638 lignes) = l'app Luna principale : chat avec l'IA Luna, **vocal Luna** (`/ws/luna-voice`), messagerie/DM sociale (`/ws/dm/`). Pertinent pour « vocal / chat texte » et « salle de discussion sociale » au sens DM, mais **pas** pour les jeux.

---

## 1. INVENTAIRE DES FICHIERS DU PACK

| # | Fichier | Lignes | Rôle |
|---|---|---|---|
| 1 | `core/rooms/manager.py` | 439 | **★ CŒUR** — `RoomManager` : connexions WS par salon, broadcast, et **toute la logique des 3 jeux** (`_process_quiz/_morpion/_memory`). |
| 2 | `core/rooms/models.py` | 177 | **★** Données quiz (`QUIZ_SETS`), états initiaux (`new_quiz_state` etc.), `check_morpion_winner`, tokens membres HMAC. |
| 3 | `core/rooms/redis_ops.py` | 119 | Persistance Redis des salons (create/get/update room, join/leave, messages, participants, TTL). |
| 4 | `luna_web.py` (extraits) | — | Routes `/salon`, `/api/rooms*` + **le WebSocket** `/api/rooms/{id}/ws` (21748-21858) + DM social `/ws/dm/` (11342) + helper `_gamify`. Voir `luna_web_GAMES_sections.py` dans le zip. |
| 5 | `static/salon.html` | 4669 | **★** Frontend des jeux : WS client, `startGame/updateGame/renderQuiz/renderMorpion/renderMemory`, chat de salle, participants, reconnexion. |
| 6 | `static/index.html` | 9638 | App Luna (chat IA, vocal Luna, DM social). Contexte pour vocal/chat texte. |
| 7 | `core/gamification/engine.py` | 835 | XP/niveaux/badges. **Lien aux jeux = uniquement** `award_xp("game_played")` et `award_xp("game_won")`. Aucune logique de jeu ici. |
| 8 | `core/gamification/constants.py` | 1004 | Tables XP/niveaux/badges/boutique. `game_played`=5 XP (cap 5/j), `game_won`=10 XP (cap 3/j). **Aucun badge ni mission spécifique aux jeux.** |

**Persistance :** 100% Redis, pas de SQL. Un salon = un hash Redis avec un champ `game_state` = **JSON sérialisé en string** (toute la partie tient dans cette string). TTL salon = 2h.

---

## 2. FLUX TEMPS RÉEL (vue d'ensemble)

```
salon.html (joueur A)                  Serveur                         salon.html (joueur B)
  │  startGame('quiz')  ── ws ──▶  room_websocket (luna_web.py:21748)
  │                                     │ host only → RoomManager._start_game
  │                                     │ new_quiz_state(...) → Redis game_state
  │                                     │ broadcast {game_update, state} ──────────▶  updateGame → renderQuiz
  │◀──────────────────────────────────┘
  │  click réponse → game_action{answer} ─ ws ─▶ handle_message → _handle_game_action
  │                                     │ _process_quiz(state) muté en place
  │                                     │ Redis update + broadcast {game_update} ──▶  renderQuiz (tous)
  └─ ...
```

**Points structurels importants :**
- L'état de jeu est **autoritatif côté serveur** (bien), recalculé à chaque `game_action`, puis **rediffusé en entier** à tous via `broadcast`. Bon pour la cohérence MAIS :
- **Aucun timer côté serveur.** Rien n'avance une partie si un joueur n'agit pas. Le « timer » du quiz est purement visuel côté client (`renderQuizTimer`) et n'avance rien.
- **La déconnexion ne touche pas l'état de jeu.** `RoomManager.disconnect` retire juste la WebSocket ; le joueur reste dans `scores`/`turn` du jeu → sources de **freeze silencieux**.
- Identité des joueurs dans l'état de jeu = la **clé `phone`** (ou l'email pour les comptes Luna). Le client affiche cette clé brute dans les scores/tours.

---

## 3. GRILLE D'AUDIT — diagnostics préliminaires localisés

Reprend la grille de DeepSeek, **mappée au code réel** avec mes hypothèses (lignes exactes). À CONFIRMER/INFIRMER par DeepSeek.

### 🔴 PRIORITÉ 1 — Quiz « bugue beaucoup »

**A. Freeze silencieux si un joueur ne répond pas / se déconnecte** — `manager.py:341-352`
```python
connected = set(state.get("scores", {}).keys())   # figé au démarrage (new_quiz_state)
answered  = set(state.get("answers", {}).keys())
if connected <= answered:                          # exige que TOUS répondent
    state["current_question"] = q_idx + 1
    ...
```
`scores` est initialisé pour les joueurs **présents au lancement** (`new_quiz_state`, `models.py:163`). Si un de ces joueurs se déconnecte ou reste inactif, `connected <= answered` n'est **jamais** vrai → **la question ne passe jamais, partie figée, aucun message d'erreur**. Combiné à l'**absence de timer serveur**, c'est la cause la plus probable du « quiz bugue ».
→ Pistes : timer de fallback serveur (ex. 15s → auto-avance), recalculer `connected` sur les joueurs réellement connectés (`room_manager.get_connected_phones`), retirer un joueur qui quitte de `scores`/`answers`.

**B. Répétition des questions** — `manager.py:248` + `models.py:32-83,154-166`
```python
quiz_idx = data.get("quiz_index", random.randint(0, len(QUIZ_SETS) - 1))
```
Il n'existe que **5 quiz sets** de **5 questions fixes** (ordre fixe). Le set est tiré au hasard **sans mémoire** des sets déjà joués → un même set peut sortir deux fois de suite ; au-delà de 5 parties tout se répète. Pas de génération IA, pas d'historique.
→ Pistes : mémoriser les sets/questions déjà posés dans la session/room (Redis), mélanger l'ordre des questions, élargir la banque, ou générer via IA (gpt-4o-mini déjà utilisé ailleurs).

**C. Double réponse / course** — `manager.py:330-334` (déjà géré, à vérifier)
```python
if phone in state.get("answers", {}):
    return False                       # 2e réponse du même joueur ignorée
state.setdefault("answers", {})[phone] = answer_idx
```
Le « premier arrivé » par joueur est protégé (rejet du doublon). Comme le serveur traite les messages WS **séquentiellement** par salon, deux joueurs différents ne se corrompent pas. → Vérifier qu'il n'y a pas de re-render qui ré-arme le clic côté client (`salon.html:4427-4434`, flag `S.quizAnswered`).

**D. Noms = numéros de téléphone (bug UX + fuite de données)** — `salon.html:4456-4463, 4564-4573`
Les scores/vainqueur affichent la **clé brute** (`phone`/email), pas le prénom :
```python
$("quizQuestion").innerHTML='... Vainqueur : <div class="winner-name">'+escapeHtml(best||"Personne")+'</div>';
// best = une clé de scores = un numéro de téléphone
```
Idem Morpion `Tour de "+turn` (`salon.html:4487`) et Memory `Tour de "+currentTurn` (`4527`). → Mapper `phone → nom` côté client (les noms sont connus via `S.participants`) ou stocker le nom dans l'état de jeu.

**E. Timer non fonctionnel** — `salon.html:4444-4454`
`renderQuizTimer` décrémente un affichage mais à 0 ne fait **rien** (pas d'auto-submit, pas d'avance). Décoratif. → Soit le rendre réel (auto-réponse vide / skip), soit le retirer pour ne pas induire en erreur.

### 🔴 PRIORITÉ 2 — Synchronisation multi-joueurs & freeze (tous jeux)

- **Pas de timers serveur** → Quiz (B), Morpion et Memory peuvent figer si le joueur dont c'est le tour part. Morpion : `state["turn"]` reste sur un `phone` déconnecté (`manager.py:356-389`) → blocage. Memory : `current_turn` idem (`393-435`).
- **Déconnexion non gérée au niveau jeu** — `manager.py:46-50` retire la WS mais pas le joueur du jeu. → Au `leave` (luna_web.py:21850), envisager : si la partie est en cours, passer le tour / retirer des `scores` / annuler la partie proprement avec message.
- **Reconnexion client** — `salon.html:2136-2141` : reconnexion auto (max N tentatives, 3s), barre de statut `showWsStatus`. Mais à la reconnexion, l'état de jeu **n'est pas re-demandé** explicitement (on attend le prochain `game_update`). → Vérifier qu'un joueur qui reconnecte récupère bien l'état courant (GET `/api/rooms/{id}` renvoie `game_state` parsé — l'utiliser au re-join).
- **Cohérence** — bon point : l'état complet est rediffusé à chaque action (`broadcast {game_update, state}`), donc pas de divergence d'état tant que le WS vit.

### 🟠 PRIORITÉ 3 — Gestion d'erreur visible

- Côté client salon : `showToast(msg,"error")` existe (ex. `salon.html:4296,4355,4360`) ; barre WS `showWsStatus` pour la perte de connexion. → MAIS aucun toast quand une **partie est figée** (cas A) car le serveur n'émet aucune erreur. → Ajouter des signaux : timeout client « En attente des autres joueurs… » puis « Erreur de synchronisation, réessayez ».
- Côté serveur : `room_websocket` (luna_web.py:21845-21858) capture `WebSocketDisconnect` et `Exception` (log warning) mais **ne notifie pas** les autres d'un état de jeu cassé.

### 🟡 PRIORITÉ 4 — Vocal / chat texte / salle sociale

- **Chat texte de salle** : robuste — `salon.html:2179-2256` (`addChatMessage` avec avatars/initiales/groupement/niveau, `sendChat`, typing). Serveur `manager.py:93-110`.
- **VOCAL EN SALLE : INEXISTANT.** Le WS salon ne gère aucune voix entre participants (uniquement chat/typing/réactions/jeux/karaoké). Le karaoké a un scoring micro **local** (pas de flux voix partagé). La voix temps réel n'existe que pour parler **à l'IA Luna** dans `index.html` (`/ws/luna-voice`, `index.html:~9062`), pas entre humains. → La vision « salle vocale type StarMaker » est donc un **ajout** (WebRTC/SFU ou relai), pas un branchement.
- **« Salle de discussion sociale »** : deux choses distinctes existent — (a) la **salle/room** (`salon.html`, multi-joueurs famille) et (b) la **messagerie/DM** 1-à-1 (`index.html`, `/ws/dm/`). À clarifier laquelle on fait évoluer.

---

## 4. EXTRAITS DE CODE

> Backend de jeu = petit et central → **fourni intégralement** ci-dessous. Frontend volumineux → extraits ciblés ; fichiers complets dans le zip.

### 4.1 `core/rooms/models.py` — données & états (INTÉGRAL)

```python
# TTLs
TTL_ROOM = 2 * 60 * 60          # 2 heures
MAX_ROOM_MESSAGES = 200
MAX_PARTICIPANTS = 10

ROOM_TYPES = ["chat", "cinema", "karaoke", "games", "dm"]
GAME_TYPES = ["quiz", "morpion", "memory"]
MEMORY_EMOJIS = ["🌙", "⭐", "🏠", "🌸", "🎵", "💜", "🦋", "🔮"]   # 8 paires

# --- 5 QUIZ SETS FIXES (5 questions chacun, ordre fixe) ---
QUIZ_SETS = [
  {"name": "Culture Générale", "questions": [
     {"q": "Quelle planète est la plus proche du Soleil ?", "choices": ["Venus","Mercure","Mars","Terre"], "answer": 1}, ...5],
  {"name": "Devinettes", "questions": [...5]},
  {"name": "Sciences & Nature", "questions": [...5]},
  {"name": "Animaux", "questions": [...5]},
  {"name": "Musique & Cinéma", "questions": [...5]},
]   # → Total 25 questions, jamais renouvelées, pas d'IA. (cf. fichier complet dans le zip)

def new_quiz_state(quiz_set_index=0, players=None):
    qs = QUIZ_SETS[quiz_set_index % len(QUIZ_SETS)]
    return {
        "game_type": "quiz", "quiz_name": qs["name"], "status": "waiting",
        "current_question": 0, "total_questions": len(qs["questions"]),
        "questions": qs["questions"],
        "scores": {p: 0 for p in (players or [])},   # ← FIGÉ aux joueurs présents au lancement
        "answers": {}, "timer": 15,                  # ← timer jamais appliqué côté serveur
    }

def new_morpion_state(player_x, player_o):
    return {"game_type":"morpion","board":[0]*9,"player_x":player_x,"player_o":player_o,
            "turn":player_x,"status":"playing","winner":None}

def new_memory_state(players):
    cards = list(range(8)) * 2; random.shuffle(cards)
    return {"game_type":"memory","cards":cards,"revealed":[False]*16,"matched":[False]*16,
            "current_turn": players[0] if players else "", "turn_order": players,
            "scores": {p: 0 for p in players}, "selected": [], "status": "playing"}

def check_morpion_winner(board):   # 0=aucun, 1=X, 2=O, -1=nul
    wins=[(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for a,b,c in wins:
        if board[a]==board[b]==board[c]!=0: return board[a]
    return -1 if 0 not in board else 0
```

### 4.2 `core/rooms/manager.py` — logique de jeu (EXTRAITS CLÉS)

`handle_message` route les messages WS (chat/typing/reaction/gift/youtube/karaoke/**game_start**/**game_action**/ping). Lancement & actions :

```python
async def _start_game(self, room_id, host_phone, data, room_ops, tid):
    game_type = data.get("game_type", "quiz")
    players = self.get_connected_phones(room_id)
    if game_type == "quiz":
        quiz_idx = data.get("quiz_index", random.randint(0, len(QUIZ_SETS)-1))  # ← répétition possible
        state = new_quiz_state(quiz_idx, players); state["status"] = "question"
    elif game_type == "morpion":
        if len(players) < 2:
            await self.send_to(room_id, host_phone, {"type":"system",
                "content":"Il faut au moins 2 joueurs pour le Morpion...","action":"show_invite"}); return
        random.shuffle(players); state = new_morpion_state(players[0], players[1])
    elif game_type == "memory":
        state = new_memory_state(players)
    else: return
    room_ops.update_room(tid, room_id, {"game_type":game_type,"game_state":json.dumps(state),"status":"playing"})
    await self.broadcast(room_id, {"type":"game_update","game_type":game_type,"state":state})

def _process_quiz(self, state, phone, data) -> bool:
    if state.get("status") != "question": return False
    answer_idx = data.get("action", {}).get("answer")
    if answer_idx is None: return False
    q_idx = state["current_question"]; questions = state.get("questions", [])
    if q_idx >= len(questions): return False
    if phone in state.get("answers", {}): return False        # anti double-réponse OK
    state.setdefault("answers", {})[phone] = answer_idx
    if answer_idx == questions[q_idx].get("answer", -1):
        state.setdefault("scores", {})[phone] = state["scores"].get(phone, 0) + 1
    connected = set(state.get("scores", {}).keys())           # ← FIGÉ au démarrage
    answered  = set(state.get("answers", {}).keys())
    if connected <= answered:                                  # ← FREEZE si un joueur ne répond pas
        state["current_question"] = q_idx + 1; state["answers"] = {}
        state["status"] = "finished" if state["current_question"] >= state.get("total_questions",5) else "question"
    return True

def _process_morpion(self, state, phone, data) -> bool:
    if state.get("status") != "playing" or state.get("turn") != phone: return False   # ← bloque si turn = joueur parti
    cell = data.get("action", {}).get("cell")
    if cell is None or not (0 <= cell <= 8): return False
    board = state.get("board", [0]*9)
    if board[cell] != 0: return False
    board[cell] = 1 if phone == state["player_x"] else 2; state["board"] = board
    w = check_morpion_winner(board)
    if w > 0:  state["status"]="won";  state["winner"]= state["player_x"] if w==1 else state["player_o"]
    elif w==-1:state["status"]="draw"; state["winner"]=None
    else:      state["turn"] = state["player_o"] if phone==state["player_x"] else state["player_x"]
    return True

def _process_memory(self, state, phone, data) -> bool:
    if state.get("status")!="playing" or state.get("current_turn")!=phone: return False  # ← bloque si tour = joueur parti
    card_idx = data.get("action", {}).get("card")
    if card_idx is None or not (0 <= card_idx < 16): return False
    matched = state.get("matched", [False]*16); selected = state.get("selected", [])
    if matched[card_idx] or card_idx in selected: return False
    selected.append(card_idx); state["selected"] = selected
    if len(selected) == 2:
        cards = state.get("cards", []); a, b = selected
        if cards[a] == cards[b]:
            matched[a]=matched[b]=True; state["matched"]=matched
            state["scores"][phone] = state["scores"].get(phone,0)+1
            if all(matched): state["status"]="finished"
        order = state.get("turn_order", [])
        if order:
            cur = order.index(phone) if phone in order else 0
            state["current_turn"] = order[(cur+1) % len(order)]
        state["selected"] = []
        state["_last_reveal"] = [a, b]; state["_last_matched"] = cards[a]==cards[b]   # client gère le flip 1.2s
    return True
```

Détection victoire & XP (`_handle_game_action`, `manager.py:300-312`) : `status in ("won","finished")` → event `game_won` au gagnant (meilleur score pour quiz/memory). `broadcast` rediffuse l'état complet après chaque changement.

### 4.3 `luna_web.py` — WebSocket du salon (EXTRAIT 21748-21858)

Auth (JWT client OU token HMAC membre OU anonyme), join, boucle de réception, dispatch vers `room_manager.handle_message`, et **finally** qui fait leave+broadcast. Voir `luna_web_GAMES_sections.py` dans le zip pour l'intégral (avec les routes `/api/rooms*`). Extrait du flux :
```python
@app.websocket("/api/rooms/{room_id}/ws")
async def room_websocket(websocket, room_id):
    await websocket.accept()
    ...auth (phone/token/host_tid)... room = rops.get_room(room_tid, room_id)
    rops.join_room(room_tid, room_id, phone); await room_manager.connect(room_id, phone, websocket)
    await room_manager.broadcast(room_id, {"type":"join", ...}, exclude_phone=phone)
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            current_room = rops.get_room(room_tid, room_id)         # relit la room à CHAQUE message
            events = await room_manager.handle_message(room_id, phone, name, data, rops, room_tid, current_room)
            for ev in events: _gamify(tid, ev)                      # award XP fire-and-forget
    except WebSocketDisconnect: pass
    finally:
        rops.leave_room(room_tid, room_id, phone); await room_manager.disconnect(room_id, phone)
        await room_manager.broadcast(room_id, {"type":"leave", ...})   # ← ne touche PAS game_state
```

### 4.4 `salon.html` — WebSocket client + chat de salle (EXTRAIT 2115-2256)

```javascript
function connectWS(roomId){
  disconnectWS();
  var url=(location.protocol==="https:"?"wss:":"ws:")+"//"+location.host+"/api/rooms/"+roomId+"/ws";
  var params=[]; if(S.myPhone)params.push("phone="+encodeURIComponent(S.myPhone));
  var t=getToken(); if(t)params.push("token="+encodeURIComponent(t));
  if(hostTid)params.push("host_tid="+encodeURIComponent(hostTid));
  if(params.length)url+="?"+params.join("&");
  S.ws=new WebSocket(url);
  S.ws.onopen   =function(){ S.wsReconnectAttempts=0; hideWsStatus(); startPing(); };
  S.ws.onmessage=function(e){ try{handleWsMsg(JSON.parse(e.data));}catch(err){} };  // ← err avalée
  S.ws.onclose  =function(){ stopPing(); if(S.view==="room"&&S.currentRoom===roomId) attemptReconnect(roomId); };
  S.ws.onerror  =function(){};                                                       // ← vide
}
function attemptReconnect(roomId){
  if(S.wsReconnectAttempts>=S.wsMaxReconnect){ showWsStatus("Connexion perdue. Rafraîchissez.",true); return; }
  S.wsReconnectAttempts++; showWsStatus("Reconnexion... ("+S.wsReconnectAttempts+"/"+S.wsMaxReconnect+")",false);
  S.wsReconnectTimer=setTimeout(function(){ if(S.view==="room"&&S.currentRoom===roomId) connectWS(roomId); },3000);
}
function startPing(){ stopPing(); S.wsPingTimer=setInterval(function(){ wsSend({type:"ping"}); },30000); }
function handleWsMsg(msg){ switch(msg.type){
  case "chat": addChatMessage(msg,false); ...; break;
  case "game_update": updateGame(msg); break;
  case "join": handleJoin(msg); break;  case "leave": handleLeave(msg); break;
  case "system": addSystemMsg(msg.content); if(msg.action==="show_invite"){...} break; ... }}
window.sendChat=function(){ var txt=$("chatInput").value.trim(); if(!txt)return; wsSend({type:"chat",content:txt}); ... };
```
Note : reconnexion OK, mais **aucune re-synchro explicite de l'état de jeu** après reconnexion (on attend le prochain `game_update`).

### 4.5 `salon.html` — rendu des jeux (EXTRAIT 4295-4573)

```javascript
window.startGame=function(type){ if(!S.isHost){showToast("Seul l'hôte peut lancer un jeu","error");return;} wsSend({type:"game_start",game_type:type}); };
function updateGame(msg){ var gt=msg.game_type,gs=msg.state; if(!gt||!gs)return; hide("gameSelector");
  /* active la bonne vue */ if(gt==="quiz"){$("quizView").classList.add("active");renderQuiz(gs);} else if(gt==="morpion"){...renderMorpion(gs);} else if(gt==="memory"){...renderMemory(gs);} }

function renderQuiz(gs){
  if(gs.status==="finished"){ renderQuizFinished(gs); return; }
  var qIdx=gs.current_question||0, questions=gs.questions||[], q=questions[qIdx]; if(!q)return;
  $("quizProgress").textContent="Question "+(qIdx+1)+"/"+(gs.total_questions||5);
  $("quizQuestion").textContent=q.q||"";
  renderQuizTimer(gs.timer);                                  // ← purement visuel
  var answered=S.quizAnswered || (gs.answers&&gs.answers[S.myPhone]!==undefined);
  (q.choices||[]).forEach(function(choice,idx){
    var btn=...; if(!answered){ btn.onclick=function(){ S.quizAnswered=true;
        wsSend({type:"game_action",action:{answer:idx}}); /* grise tous les choix */ }; }
  });
  renderScoreRows($("quizScoreRows"),gs.scores,"pts");        // ← clés = numéros de téléphone
}
function renderQuizTimer(seconds){ /* décrémente l'affichage ; à 0 ne fait RIEN (pas d'auto-skip) */ }
function renderQuizFinished(gs){ /* vainqueur = clé de scores = numéro brut */ }
function renderScoreRows(container,scores,unit){ for(var k in scores){ /* k = phone affiché tel quel */ } }
// Morpion: "Tour de "+turn  (turn = phone)   Memory: "Tour de "+currentTurn (phone)
```

### 4.6 Gamification (lien aux jeux uniquement)
`luna_web.py:5411 _gamify(tid, action)` → `award_xp_safe`. Events émis par les jeux : `game_played` (au `game_start`), `game_won` (à la victoire). `constants.py` : `game_played`=5 XP cap 5/j, `game_won`=10 XP cap 3/j ; **aucun badge/mission/compteur spécifique jeux** (pas de `total_games_played`). Le reste d'`engine.py`/`constants.py` (niveaux, prestige, boutique, stabilité) est hors logique de jeu.

---

## 5. PROPOSITION UX « salle vivante » type StarMaker — état des lieux

Bonne nouvelle : beaucoup de briques existent déjà dans `salon.html`. Cartographie de l'écart :

| Élément StarMaker visé | Déjà présent ? | Où / quoi faire |
|---|---|---|
| Participants visibles | ✅ liste texte + dot + badge Hôte | `renderParticipants` (2089). À transformer en **grille de sièges/avatars**. |
| Niveaux affichés | ✅ niveau dans le chat (`Niv.X`) | `manager.py:97` + chat. À remonter sur les sièges. |
| Avatars | ⚠️ initiales colorées | `getInitials/avatarColor` (2193-2196). À remplacer par vrais avatars (le système `avatar_type` existe en gamification). |
| Badges / cosmétiques | ⚠️ existent en gamification, **pas affichés en salle** | `core/gamification` (frames/outfits/avatar). À brancher sur les sièges. |
| Réactions / cadeaux animés | ✅ `reaction`, `gift` (animations) | `manager.py:117-219`, `salon.html` floating/gift. |
| Indicateur « qui parle » (halo vocal) | ❌ pas de vocal en salle | **À créer** (voir §3 vocal). Requiert d'ajouter un canal voix. |
| Barre basse 4 actions (Micro/Inviter/Jeux/Profil) | ⚠️ boutons épars | Regrouper les contrôles existants en une barre fixe. |
| Jeux lancés depuis la salle en gardant chat+participants | ✅ déjà le cas ! | `gamesSection`/`chatPanel.compact` (2081). Le jeu s'ouvre **dans** la salle. |
| Karaoké (spotlight, score live, applaudissements) | ✅ riche | `manager.py:171-206`. Bonne base d'« ambiance vivante ». |

→ La transformation est surtout **frontend (salon.html)** + branchement des cosmétiques gamification + **ajout d'un canal vocal** (le seul vrai chantier nouveau côté infra). Le « jeux dans la salle » est déjà acquis.

---

## 6. CE QUE DEEPSEEK DOIT PRODUIRE

Pour chaque priorité (Quiz d'abord), fournir :
1. **Confirmation/infirmation** de chaque hypothèse §3 (avec le n° de ligne).
2. **Correctif proposé** (diff ou bloc de code complet prêt à coller), **sans casser** l'API WS existante (mêmes types de messages). Le projet impose des changements **additifs**, anti-régression (cf. `CLAUDE.md`).
3. **Risque de régression** de chaque correctif.
4. Pour l'UX salle : un plan par étapes (sièges → cosmétiques → barre d'actions → vocal), en réutilisant l'existant.

## 7. TESTS DE VALIDATION (à exécuter après correctifs)

| Test | Attendu |
|---|---|
| Répétition | Lancer Quiz plusieurs fois → pas de set/question répété tant que la banque n'est pas épuisée. |
| Déconnexion (Quiz) | Un joueur quitte en pleine question → la partie continue/avance pour les autres (pas de freeze). |
| Déconnexion (Morpion/Memory) | Le joueur dont c'est le tour quitte → tour passé ou partie clôturée proprement. |
| Double réponse | 2 onglets, 2 clics quasi simultanés du même joueur → seule la 1re compte (déjà le cas, à confirmer). |
| Timeout sans réponse | Personne ne répond → fallback serveur fait avancer (après correctif timer). |
| Synchro scores | Après chaque tour, scores identiques sur tous les écrans, avec **prénoms** (pas numéros). |
| Erreur visible | Couper le réseau → message clair (« Reconnexion… » puis « Connexion perdue »). |
| Mobile | salon.html lisible sur téléphone, pas de superposition jeux/chat. |
| Salle | Entrer, voir les sièges/avatars/niveaux ; (après vocal) halo « qui parle ». |

---

### Annexe — commandes de vérification rapides
```bash
cd PROPRIO/serveur
grep -rniE "morpheus|tweak|tarot" --include=*.py --include=*.html .   # → vide (ces noms n'existent pas)
grep -n "game_type\|_process_quiz\|_process_morpion\|_process_memory" core/rooms/manager.py
grep -n "QUIZ_SETS\|new_quiz_state\|check_morpion_winner" core/rooms/models.py
grep -n "game_start\|game_action\|game_update\|renderQuiz\|renderMorpion\|renderMemory" static/salon.html
```
