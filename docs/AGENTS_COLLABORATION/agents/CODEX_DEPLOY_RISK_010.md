# Codex deploy risk check 010 - Chat / titres / recherche

Agent : Codex
Objectif : 010
Type : validation
Resume : Le patch 010 est coherent avec la validation UI Ludovic : sidebar mobile, recherche locale plein texte, fallback serveur Redis et titres tronques a 4 mots. Risque principal : recherche locale limitee au `localStorage` APK, avec fallback serveur seulement si Redis contient encore les conversations.
Fichier concerne : `static/index.html`, `luna_web.py`
Risque : faible a moyen avant deploiement ; test telephone Kimi requis.
Decision Ludovic requise : oui pour deploiement Cloud Run.
Action proposee : Kimi teste sur appli reelle avant deploiement, puis demande feu vert Ludovic.

## Constats code

- `static/index.html:6352` : `renderConvList(filter)` filtre les conversations.
- `static/index.html:6361` a `static/index.html:6378` : recherche locale dans titre, preview et messages `localStorage`.
- `static/index.html:6381` : fallback serveur `/api/conversations/search?q=...` si aucun resultat local.
- `static/index.html:6398` et `static/index.html:6434` : troncature affichage titre a 4 mots.
- `static/index.html:6554` : chargement conversations depuis serveur puis fusion preview locale.
- Commits reperes : `a33e150`, `926ac7e`, `59fdabc`.

## Risques avant deploy

1. Si l'APK a perdu son `localStorage`, la recherche locale ne retrouvera pas les anciens messages.
2. Si Redis ne contient plus les conversations, le fallback serveur ne peut pas les inventer.
3. La troncature 4 mots est seulement affichage : OK, mais Kimi doit verifier que les titres restent reconnaissables.
4. Le fallback serveur ajoute un appel reseau pendant la recherche ; verifier latence et message "Aucune conversation trouvee" sur mobile.
5. Pas de suppression detectee dans le flux 010 ; les suppressions restent derriere `_showConfirm()`.

## Tests Kimi recommandes

- Chercher un mot present dans un titre.
- Chercher un mot present dans un message local recent.
- Chercher un mot ancien connu, exemple `chocolat`.
- Creer une nouvelle conversation, envoyer 2 messages, verifier titre court.
- Reouvrir sidebar sur telephone et verifier absence de superposition.

## Decision

Pret pour test Kimi reel. Deploiement Cloud Run reste niveau 2/3 : feu vert Ludovic obligatoire.
