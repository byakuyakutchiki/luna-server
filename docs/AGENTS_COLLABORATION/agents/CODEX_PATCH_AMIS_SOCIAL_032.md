# Codex — Patch onglet Amis / Social — Objectif 032

Date : 2026-06-05  
Type : patch niveau 1, non destructif par defaut  
Fichiers : `static/index.html`, `luna_web.py`

## Ce qui a ete code

### 1. Presence Amis globale

Avant : le heartbeat social ne demarrait que lorsque l'utilisateur ouvrait l'onglet Amis via `loadAmis()`.

Apres : `showApp()` appelle `_startAmisHeartbeat()` apres authentification. La presence et les compteurs demandes/DM peuvent donc se mettre a jour meme si l'utilisateur ne va pas tout de suite dans l'onglet Amis.

### 2. Boutons Bloquer / Signaler visibles

Avant : le backend contenait deja des capacites `block_user` et `report_user`, mais l'onglet Amis ne les exposait pas.

Apres : chaque carte ami affiche maintenant :

- `Message`
- `Signaler`
- `Bloquer`
- `Supprimer`

`Bloquer` utilise `/api/social/block` avec confirmation.

`Signaler` utilise `/api/social/report` avec raison obligatoire, min 5 caracteres.

Aucun SMS, email, appel, paiement, invitation ou reservation n'est declenche.

### 3. Endpoint debug social non sensible

Ajout :

`GET /api/debug/social-capabilities`

Retourne :

- disponibilite Redis ;
- presence SocialRedisOps ;
- routes `/api/social/*` et `/ws/dm/*` detectees ;
- doublons de routes ;
- rate limits declares ;
- constantes sociales (`MAX_FRIENDS`, `MAX_BLOCKED`, TTL presence, TTL DM) ;
- capacites UI attendues.

Ne retourne aucun secret, aucun token, aucun DM, aucun numero de telephone, aucun email.

## Risques

- Les boutons `Bloquer` et `Signaler` modifient des donnees seulement si l'utilisateur clique et confirme. Ils ne sont pas lances automatiquement.
- L'UI peut devenir dense sur mobile avec quatre actions sur une carte ami. Kimi doit auditer la presentation mobile.
- L'environnement Windows n'a pas permis de lancer `python -m py_compile` ni `node --check` : Python absent, Node shell bloque. Verification syntaxique complete a faire par Claude/Kimi sur VM.

## Tests a faire

1. Ouvrir l'app, rester sur Chat : verifier que le badge Amis peut se mettre a jour via heartbeat.
2. Ouvrir Amis : verifier code ami, liste amis, demandes.
3. Sur un ami de test uniquement : cliquer `Signaler`, entrer une raison factice, verifier toast succes.
4. Sur un ami de test uniquement : cliquer `Bloquer`, annuler d'abord, puis confirmer seulement si Ludovic accepte.
5. Appeler `/api/debug/social-capabilities` et verifier `route_duplicates`.

## Prochaines actions

- Claude : verifier syntaxe sur VM et deploy seulement sur validation Ludovic.
- Kimi : auditer la densite mobile des cartes amis.
- DeepSeek : contre-auditer l'ordre des routes sociales et la securite WS DM.

