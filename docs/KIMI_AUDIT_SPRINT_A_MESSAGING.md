# Prompt Kimi — Audit Sprint A : Messagerie amis + Guardian DM

## Contexte

Luna est une application compagnon IA multi-tenant (FastAPI + Redis, Cloud Run).
Le sprint A vient d'implémenter la messagerie entre amis (DM) et les alertes Guardian via DM.

### Fichiers modifiés
- `luna_web.py` — backend principal (~22 000 lignes)
- `core/guardian/alerts.py` — module alertes Guardian
- `static/index.html` — frontend SPA
- `core/social/routes.py` — routes API social (non modifié dans ce sprint)
- `core/social/redis_ops.py` — opérations Redis sociales (non modifié)

---

## Ce qui existe (infra déjà présente)

### DM entre amis
- `GET /api/social/dm/rooms` — liste les conversations DM de l'utilisateur connecté
- `POST /api/social/dm/create` — crée ou ouvre un DM avec un ami (`friend_tid`)
- `GET /api/social/dm/{room_id}/messages` — historique des messages (50 derniers)
- `POST /api/social/dm/{room_id}/send` — envoie un message (REST fallback)
- `@app.websocket("/ws/dm/{room_id}")` — WebSocket temps réel (token JWT en param `?token=`)
- `_dm_subscribers: Dict[str, set]` — registre WS en mémoire (room_id → set de (tid, ws))

### Logique WS DM (luna_web.py ~ligne 10821)
- Auth par token JWT en query param
- Vérification accès à la room (participants tid1/tid2)
- Mark as read à la connexion
- Types de messages : `message` (envoie + broadcast) et `typing` (indicateur)
- Broadcast à tous les abonnés de la room, mark as read pour le destinataire si WS ouvert
- Cleanup automatique des WS morts

### Heartbeat social (POST /api/social/heartbeat)
- Retourne `unread_dm_count` (total non-lus)
- Utilisé pour badge rouge dans la nav

### UI DM (static/index.html)
- Modal DM (`#dmModal`) avec `openDm(friendTid, friendName)`
- Bouton "Message" sur chaque carte ami dans l'onglet Amis
- WS connecté à l'ouverture (`_connectDmWs`)
- Fallback polling 5s si WS échoue
- Indicateur "ecrit..." sur `typing`
- Enter pour envoyer
- Badge unread dans la nav (combiné friend requests + DM unread)

---

## Ce qui a été ajouté dans ce sprint

### 1. `core/guardian/alerts.py` — `send_guardian_dm_alerts()` (async)
Envoie une alerte Guardian en DM Luna à tous les amis sur la plateforme.
- Récupère les amis via `sops.get_friends(sender_tid)`
- Construit un message d'alerte (emoji niveau + description + lien Maps)
- Appelle `sops.create_dm_room(sender_tid, f_tid)` pour chaque ami
- Appelle `sops.add_dm_message(room_id, sender_tid, msg_text)`
- Push WS optionnel via `ws_push_fn(room_id, msg)`

### 2. `luna_web.py` — `_guardian_dm_broadcast(room_id, msg)` (async)
Helper qui broadcast un message à tous les WS ouverts sur une room DM.

### 3. `luna_web.py` — `guardian_alert_channel` setting
- Ajouté aux allowed fields de `POST /api/settings`
- Valeurs valides : `"sms"` (défaut) | `"luna"` | `"both"`
- Validation dans le endpoint (valeur invalide ignorée)

### 4. `luna_web.py` — Intégration dans `guardian_location` et `guardian_sos`
Les deux endpoints lisent `guardian_alert_channel` depuis Redis (`luna:{tid}:settings`).
- `sms` ou `both` → envoie SMS via `send_guardian_alerts()`
- `luna` ou `both` → envoie DM via `send_guardian_dm_alerts()`
- SOS : idem, les deux canaux selon le réglage

### 5. `static/index.html` — Sélecteur canal dans l'onglet Guardian
- `<select id="guardianAlertChannel">` avec 3 options (sms / luna / both)
- `guardianLoadChannel()` — charge depuis `/api/settings` à l'ouverture de l'onglet
- `guardianSaveChannel(val)` — sauvegarde via `POST /api/settings`

---

## Ce que Kimi doit vérifier

### A. Cohérence et complétude du flux DM

1. **WS vs REST : unicité du message**
   - Si un message est envoyé via WS (`type: message`), il est stocké dans Redis ET broadcasté. ✓
   - Si envoyé via REST (`POST .../send`), il est stocké ET broadcasté via `_dm_subscribers`. ✓
   - Y a-t-il un risque de double affichage dans le frontend si le WS est ouvert ET le REST est appelé ?

2. **Mark as read**
   - La route `GET .../messages` marque comme lu (`mark_dm_read`). ✓
   - La connexion WS marque comme lu. ✓
   - Le broadcast WS marque comme lu pour le destinataire si son WS est ouvert. ✓
   - Vérifier : si l'utilisateur A envoie via WS, est-ce que l'unread de A lui-même est incrémenté ? (Il ne devrait pas l'être.)

3. **Accès inter-tenant**
   - Les DMs sont scopés `social:dm:{room_id}` (pas par tenant). Est-ce intentionnel ?
   - La vérification d'accès dans WS et REST check que `tid` est dans `tid1` ou `tid2`. ✓
   - Risque : un utilisateur peut-il deviner un `room_id` et accéder à une conversation d'autrui ?
     (room_id = `dm_{min}_{max}` est déterministe, donc devinable. Est-ce un problème ?)

4. **Typing indicator**
   - Le typing est envoyé à tous sauf l'émetteur. ✓
   - Il n'est pas stocké en Redis. ✓
   - Y a-t-il un rate-limiting sur le typing WS ? (Le rate limit `dm_send` ne s'applique pas au typing.)

### B. Guardian DM — Sécurité et logique

5. **`send_guardian_dm_alerts` — Boucle sur les amis**
   - Si l'utilisateur n'a pas d'amis sur la plateforme, la fonction retourne `{"sent": [], "failed": [], "total_friends": 0}` sans erreur. ✓
   - Si `create_dm_room` retourne `None` (pas amis ou bloqué), l'ami est marqué en `failed`. ✓
   - Y a-t-il un risque d'infini/timeout si un utilisateur a 50 amis et que chaque appel Redis prend du temps ?

6. **`guardian_alert_channel` — Validation**
   - Valeurs invalides sont ignorées (non sauvegardées). ✓
   - Valeur par défaut si non définie = `"sms"` (canal traditionnel). ✓
   - Si le canal est `"luna"` mais qu'il n'y a pas d'amis sur la plateforme → aucune alerte envoyée. ⚠️ Signaler à l'utilisateur ?

7. **SOS en mode `luna` uniquement**
   - En mode `"luna"`, si l'utilisateur n'a pas d'amis sur la plateforme, le SOS est silencieux pour les contacts SMS. ⚠️ Est-ce acceptable ?
   - Suggestion : SOS toujours sur `"both"` indépendamment du réglage ?

8. **Isolation auth records**
   - Les changements de settings (`guardian_alert_channel`) utilisent `_redis_client._key(tid, "settings")` (Redis hash). ✓
   - Cela ne touche pas les auth records (clés `luna:{tenant_id}:auth:*`). ✓

### C. UI Guardian — Cohérence

9. **Chargement du canal**
   - `guardianLoadChannel()` est appelé à chaque ouverture de l'onglet guardian. ✓
   - Est-ce que le sélecteur est chargé avant que l'utilisateur puisse démarrer Guardian ? (Ordre des événements)

10. **Persistance**
    - `guardianSaveChannel(val)` est appelé immédiatement au `onchange`. ✓
    - Pas de debounce nécessaire (c'est un select, pas un input text). ✓

11. **Feedback utilisateur**
    - Il n'y a pas de toast de confirmation après le changement de canal. Est-ce intentionnel ?
    - Le texte explicatif sous le select est-il clair ?

### D. Social routes — Doublons potentiels

12. **Double implémentation DM**
    - `core/social/routes.py` expose `social_router` avec des routes DM (`/api/social/dm/*`).
    - `luna_web.py` expose aussi des routes DM directes (lignes ~10706-10771).
    - Ces deux sets de routes coexistent. Quelle priorité FastAPI leur donne-t-il ?
    - Y a-t-il un risque de conflit ou de comportement différent entre les deux ?

13. **Heartbeat et unread count**
    - `POST /api/social/heartbeat` (social_router) retourne `unread_dm_count`. ✓
    - Y a-t-il un autre endpoint heartbeat dans luna_web.py qui retournerait un compte différent ?

### E. Tests à effectuer manuellement

14. **Scénario complet DM entre Erwan (tid=2) et Julien (tid=3)**
    - Login Erwan : `erwan@test.com` / password depuis .env
    - Aller dans Amis → trouver Julien → cliquer "Message"
    - Vérifier que le modal s'ouvre, que la connexion WS se fait
    - Envoyer un message, vérifier qu'il apparaît dans les deux sessions
    - Vérifier le badge unread dans la nav de Julien

15. **Scénario Guardian DM**
    - Régler canal sur "Message Luna" dans l'onglet Guardian
    - Vérifier que le réglage persiste après rechargement de page
    - Si Erwan active Guardian et qu'une alerte est déclenchée → Julien devrait recevoir un DM

---

## Points d'attention critiques (à vérifier en priorité)

- **Sécurité** : room_id devinable → est-ce que la vérification tid1/tid2 est suffisante ?
- **Silencieux** : mode `"luna"` sans amis → SOS silencieux (risque vital en contexte Guardian)
- **Double DM** : `send_guardian_dm_alerts` appelle `add_dm_message` directement, pas via la route REST avec rate-limiting. Un utilisateur pourrait-il déclencher du spam si Guardian est mal configuré ?
- **Authentification préservée** : aucune des modifications ne touche aux tables auth, passwords, ou JWT. ✓

---

## Fichiers à lire pour l'audit

1. `core/guardian/alerts.py` — complet
2. `luna_web.py` — lignes 10700-10900 (DM WS + helpers)
3. `luna_web.py` — lignes 13034-13070 (settings API)
4. `luna_web.py` — lignes 14420-14610 (guardian_location + guardian_sos)
5. `core/social/redis_ops.py` — lignes 291-390 (create_dm_room, add_dm_message)
6. `static/index.html` — lignes 5266-5310 (Guardian JS)
7. `static/index.html` — lignes 2002-2015 (Guardian HTML canal selector)
