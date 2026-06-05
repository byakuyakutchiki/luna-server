# Codex — Audit onglet Amis / Social — Objectif 032

Date : 2026-06-05  
Type : audit code non destructif  
Portée : `static/index.html`, `luna_web.py`, `core/social/routes.py`, `core/social/redis_ops.py`

## Verdict court

L'onglet Amis est **déjà assez riche techniquement** : code ami, demandes, acceptation/refus, liste d'amis, présence, messages privés WebSocket avec fallback polling, amis externes, suppression ami + DM.

Mais il n'est **pas encore prêt produit** : plusieurs capacités backend ne sont pas visibles dans l'UI, certaines erreurs sont silencieuses, la présence ne démarre que lorsque l'onglet Amis est chargé, et il y a une ambiguïté technique car les routes `/api/social/*` existent à la fois dans `core/social/routes.py` et dans `luna_web.py`.

## Carte réelle de l'onglet

| Zone visible | Élément UI | Handler front | Endpoint | Statut | Risque / manque |
|---|---|---|---|---|---|
| Code ami | `amisMyCode` | `loadAmis()` | `GET /api/social/friend-code` | Atteint | Pas de bouton copier/partager visible |
| Ajouter par code | `amisCodeBtn` | click + Enter | `POST /api/social/friend-code/use` | Atteint | Erreurs simples, pas d'explication si limite/bloqué |
| Demandes reçues | `amisRequestsSection` | `loadAmisRequests()` | `GET /api/social/friends/requests` | Atteint | Section cachée si vide, OK |
| Accepter | bouton inline | `_amisAccept()` | `POST /api/social/friends/accept` | Atteint | Pas de détail si limite amis atteinte |
| Refuser | bouton inline | `_amisDecline()` | `POST /api/social/friends/decline` | Atteint | Pas de message de confirmation/refus traité |
| Activités | `amisSalonBtn` | `loadActivities()` | navigation `/salon` | Partiel | Cible produit floue : salon social séparé |
| Liste amis | `amisFriendsList` | `loadAmisList()` | `GET /api/social/friends` + `GET /api/social/dm/rooms` | Atteint | Vide si aucun ami ; pas d'appel à discover |
| Présence | point online/offline | `loadAmisList()` + heartbeat | `POST /api/social/heartbeat` | Partiel | Heartbeat démarre seulement après ouverture onglet Amis |
| DM | bouton `Message` | `openDm()` | `POST /api/social/dm/create` | Atteint | UX basique ; pas d'horodatage visible |
| DM temps réel | modal | `_connectDmWs()` | `WS /ws/dm/{room_id}` | Atteint techniquement | Fallback polling prévu ; erreurs WS silencieuses |
| Envoyer DM | `dmSendBtn` | WS ou REST fallback | `POST /api/social/dm/{room_id}/send` | Atteint | Pas d'état "envoyé / lu", pas de modération visible |
| Typing | keydown | WS typing | `WS /ws/dm/{room_id}` | Atteint | Texte "ecrit..." sans accent, temporaire |
| Fermer DM | `dmCloseBtn` | close WS/polling | client only | Atteint | OK |
| Supprimer ami | icône poubelle | `_openDfm()` puis `_confirmDeleteFriend()` | `DELETE /api/social/friends/{friend_tid}` | Atteint | Bon avertissement, mais pas de blocage/signaler visible |
| Amis externes | section dédiée | `loadExternFriends()` | `GET /api/social/friends-extern` | Atteint | Stocke téléphone/email ; consentement RGPD à renforcer |
| Ajouter ami externe | modal | `_saveExternFriend()` | `POST /api/social/friend-extern` | Partiel | Pas d'invitation envoyée ; juste stockage contact |
| Retirer ami externe | bouton retirer | `_removeExternFriend()` | `DELETE /api/social/friend-extern/{phone}` | Atteint | Confirmation présente |

## Backend réel

Routes vues dans `core/social/routes.py` :

- profil social : `GET/POST /api/social/profile`
- profil public : `GET /api/social/profile/{target_tid}`
- découverte : `GET /api/social/discover`
- code ami : `GET /api/social/friend-code`
- ajout par code : `POST /api/social/friend-code/use`
- amis : `GET /api/social/friends`
- demande directe : `POST /api/social/friends/request`
- demandes reçues : `GET /api/social/friends/requests`
- accepter/refuser/supprimer : `POST accept`, `POST decline`, `DELETE /friends/{friend_tid}`
- amis externes : `GET/POST/DELETE`
- blocage / déblocage / signalement : `POST /api/social/block`, `/unblock`, `/report`
- DM rooms/messages/send avec rate-limit

Routes dupliquées dans `luna_web.py` :

- `GET /api/social/friend-code`
- `POST /api/social/friend-code/use`
- `GET /api/social/friends`
- `GET /api/social/friends/requests`
- `POST /api/social/friends/accept`
- `POST /api/social/friends/decline`
- `DELETE /api/social/friends/{friend_tid}`
- `POST /api/social/heartbeat`
- `GET/POST /api/social/dm/*`
- `GET/POST/DELETE /api/social/friend-extern*`
- `WS /ws/dm/{room_id}`

Point d'attention : `app.include_router(social_router)` est appelé avant les routes sociales locales de `luna_web.py`. En FastAPI, la première route correspondante peut être servie avant les doublons. Il faut vérifier en production quelle implémentation répond réellement, car les garde-fous ne sont pas strictement identiques entre `core/social/routes.py` et `luna_web.py`.

## Ce qui fonctionne probablement

- Génération du code ami 6 caractères.
- Résolution du code ami.
- Anti self-add.
- Anti doublon déjà ami / déjà envoyé.
- Amitié mutuelle après acceptation.
- Liste amis avec présence.
- DM limité à amis acceptés.
- DM bloqué si un des deux utilisateurs a bloqué l'autre.
- Suppression ami + suppression room/messages/unread.
- Présence TTL 5 minutes.
- Limites Redis : `MAX_FRIENDS=50`, `MAX_BLOCKED=50`, `MAX_DM_MESSAGES=100`.
- Monitoring `_check_objective_amis()` déjà présent dans `/api/admin/objectives`.

## Ce qui manque ou reste partiel

### P0 — Sécurité / cohérence

1. **Routes sociales dupliquées** : lever l'ambiguïté entre `core/social/routes.py` et `luna_web.py`.
2. **Blocage / signalement non visibles dans l'UI Amis** : backend existe, mais l'utilisateur ne peut pas bloquer/signaler depuis l'onglet.
3. **Présence pas globale** : heartbeat démarre seulement après `loadAmis()`. Un utilisateur peut être affiché offline s'il n'ouvre pas l'onglet Amis.
4. **Amis externes stockent téléphone/email** : ajouter notice RGPD claire + source/consentement + finalité.
5. **Erreurs silencieuses** : plusieurs `.catch(function(){})` masquent les pannes.

### P1 — UX / produit

1. Ajouter bouton copier/partager le code ami.
2. Ajouter bouton "Inviter par SMS" pour amis externes, mais uniquement avec confirmation et coût affiché.
3. Ajouter onglet ou section "Découvrir" si `/api/social/discover` est censé exister.
4. Ajouter horodatages DM, état envoyé/échec, unread plus visible.
5. Ajouter état de connexion DM : temps réel / fallback polling.
6. Ajouter microcopy sur la suppression : "DM effacés des deux côtés".
7. Harmoniser "Mes Amis" -> "Mes amis" et les textes sans accents.

### P2 — Qualité / premium

1. UI plus premium pour les cartes amis et DM.
2. Avatar social cohérent avec le monde Luna.
3. Filtres : en ligne, récents, externes, demandes.
4. Recherche dans les amis.
5. Historique d'activité sociale : demande envoyée, acceptée, refusée.

## Risques RGPD / conformité

| Donnée | Où | Risque | Correctif |
|---|---|---|---|
| Code ami | Redis `social:friend_code` | Faible, identifiant social | Bouton renouveler code si fuite |
| Téléphone ami externe | Redis `social:extern:{tid}` | Moyen | Consentement/finalité + suppression claire |
| Email ami externe | Redis `social:extern:{tid}` | Moyen | Facultatif, notice RGPD |
| DM | Redis `social:dm:*` | Moyen/élevé | Durée de conservation visible ; suppression/export |
| Présence online | Redis TTL 5 min | Moyen | Expliquer "en ligne" et possibilité cacher présence |
| Blocages/signalements | Redis | Moyen | UI + politique modération |

## Tests non destructifs recommandés

| Test | Action | Résultat attendu | Risque |
|---|---|---|---|
| TC-032-01 | Ouvrir onglet Amis | Code ami visible, compte amis, amis externes chargés | Aucun |
| TC-032-02 | Entrer code vide/court | Message "Entre un code valide" | Aucun |
| TC-032-03 | Entrer son propre code | Erreur self-add claire | Faible, pas de donnée externe |
| TC-032-04 | Ouvrir avec zéro ami | Empty state lisible + proposition partager code | Aucun |
| TC-032-05 | Ajouter ami externe factice `Test Codex +33000000000` | Ami externe ajouté, puis supprimable | Donnée factice uniquement |
| TC-032-06 | Supprimer ami externe factice | Confirmation puis retrait | Donnée factice uniquement |
| TC-032-07 | Sans ami réel, bouton DM absent | Pas de DM possible hors amitié | Aucun |
| TC-032-08 | `/api/admin/objectives` | Objectif `amis` remonte statut/metrics | Lecture seule |

## Ce que Claude peut coder ensuite

P0 minimal recommandé :

1. Ajouter une route debug non sensible `GET /api/debug/social-capabilities` ou enrichir `/api/admin/objectives` pour afficher quelle implémentation `/api/social/*` est active.
2. Supprimer ou neutraliser les routes sociales dupliquées non utilisées, ou documenter explicitement l'ordre de résolution.
3. Ajouter boutons UI `Bloquer` et `Signaler` dans la carte ami/DM, branchés sur endpoints existants avec confirmation.
4. Déclencher le heartbeat social au login/app load, pas seulement à l'ouverture de l'onglet Amis.
5. Remplacer les `.catch(function(){})` critiques par un message visible + log F12/Cloud Run.

## Ce que Kimi doit auditer

- Lisibilité mobile de l'onglet Amis.
- UX du code ami : copier, partager, inviter.
- DM modal : premium, clair, horodatage, état temps réel.
- Amis externes : doit-on les appeler "Contacts invités" plutôt que "Amis non inscrits" ?
- Distinction amis Luna vs contacts externes.

## Ce que DeepSeek doit contre-auditer

- L'ambiguïté des routes dupliquées `core/social/routes.py` vs `luna_web.py`.
- Les rate-limits réellement appliqués en production.
- La sécurité WS `/ws/dm/{room_id}` : auth, accès room, blocage, fuite de messages.
- La suppression RGPD : est-ce que `delete_friend_and_data` efface bien toutes les clés ?
- Les bugs possibles dans `sent_requests`, `friend_requests`, TTL et max friends.

## Décision Ludovic requise

Non pour l'audit.

Oui avant :

- invitation SMS réelle ;
- suppression d'un vrai ami ;
- purge de DM réels ;
- modification de stockage Redis ;
- déploiement UI visible.

