# Codex — Avis Objectif 010 : Recherche historique intelligente

Agent : Codex
Date : 2026-05-27
Sujet : Recherche historique conversationnelle dans la sidebar

## Ce que j'ai lu
- `docs/AGENTS_COLLABORATION/OBJECTIF_010_HISTORIQUE_MEMOIRE_CHAT.md`
- `docs/AGENTS_COLLABORATION/NOTE_UI_PREMIUM_LOUPE_SIDEBAR_010.md`
- `static/index.html` (sidebar, recherche, conversation list)
- `luna_web.py` (`/api/conversations`, `/api/history`, auto-title generation)
- `core/memory/memory_manager.py` et `core/memory/schemas.py`

## Ce que j'ai compris
- Les conversations sont stockées en Redis : métadonnées (`Conversation` hashes) et messages (`LIST` par conversation).
- La sidebar charge la liste via `/api/conversations` et l'historique via `/api/history`.
- Le champ de recherche de la sidebar ne filtre aujourd'hui que sur `title` et `preview` locaux.
- `preview` est géré en localStorage dans le navigateur, ce qui ne couvre pas correctement les anciennes conversations.

## Problème identifié
- La recherche ne retrouve pas un mot-clé comme `chocolat` si ce mot n'est pas présent dans le titre court ou dans le preview local.
- Les anciennes conversations sont donc invisibles dès que le titre automatique est mauvais ou trop vague.

## Preuves / indices
- `static/index.html` `renderConvList(filter)` : filtre uniquement sur `c.title` et `c.preview`.
- `/api/conversations` dans `luna_web.py` renvoie uniquement `summary`, `last_activity`, `message_count`, `started_at`.
- Le backend ne possède pas de recherche conversationnelle actuelle.

## Fichiers concernés
- `static/index.html`
- `luna_web.py`
- `core/memory/memory_manager.py`

## Solution proposée
1. Ne pas toucher à la sidebar UI validée.
2. Ajouter une recherche serveur sur `/api/conversations?search=...`.
3. Implémenter côté backend une recherche par :
   - `Conversation.summary` (titre)
   - `contact_name` / `relation`
   - contenu des messages stockés en Redis
4. Mettre à jour le frontend pour que le champ de recherche interroge ce nouvel endpoint avec un léger debounce.
5. Garder la logique de sauvegarde des conversations existantes et ne rien supprimer.
6. Ne pas migrer immédiatement tous les anciens titres ; garder ce chantier pour une amélioration ultérieure si besoin.

## Risques
- Recherche sur le contenu des messages peut être un peu plus lente si le nombre de conversations est grand.
- Il faut éviter les requêtes trop fréquentes côté frontend, d'où le `debounce`.
- Aucun changement structurel de données Redis n'a été introduit.

## Tests nécessaires
- Recherche `chocolat` doit retrouver une conversation dont le texte contient ce mot mais dont le titre n'en parle pas.
- Les conversations existantes doivent toujours s'afficher et pouvoir s'ouvrir.
- Le champ de recherche doit rester fonctionnel sur téléphone sans altérer l'UI validated.
- En cas d'échec réseau, la recherche doit retomber sur le filtrage local si possible.

## Demande de validation Ludovic
- [ ] Nécessaire avant modification
- [ ] Nécessaire avant déploiement
- [x] Non nécessaire
