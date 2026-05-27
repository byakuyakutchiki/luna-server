# Synthese Codex - Objectif 010 recherche historique

**Date** : 2026-05-27  
**Role** : selectionner les apports utiles de Kimi, DeepSeek, Cursor et Claude  
**Statut** : synthese pour decision Ludovic puis implementation Claude

## Etat GitHub constate

`main` contient deja :

- `a33e150` - recherche plein texte locale dans `static/index.html` ;
- troncature d'affichage des titres a 4 mots ;
- avis Kimi integre dans `KIMI_AVIS_010_RECHERCHE_HISTORIQUE.md` ;
- avis Claude integre dans `CLAUDE_AVIS_010_RECHERCHE_HISTORIQUE.md`.

Cette implementation ne change pas le backend, ne change pas la sidebar UI, et ne
touche pas au design valide sur telephone.

## Ce qu'il faut garder de Kimi

Kimi apporte la meilleure direction UX pour cette phase :

- un titre est un label de repertoire, pas un resume ;
- affichage court : 4 mots environ, lisible en un coup d'oeil ;
- recherche utile = titre + contenu des messages ;
- ne pas regenerer massivement les anciennes conversations maintenant ;
- conserver la sidebar telle que validee par Ludovic.

Decision Codex : **retenir Kimi comme reference UX pour titres et recherche**.

## Ce qu'il faut garder de Claude

Claude apporte la realite technique du stockage :

- Redis serveur = source de verite active ;
- `localStorage` APK = cache local sans TTL ;
- Redis garde les conversations environ 30 jours ;
- `/api/conversations` ne descend pas les messages complets ;
- si une ancienne conversation n'est plus dans `localStorage`, la recherche locale ne peut pas retrouver son contenu.

Decision Codex : **retenir le diagnostic stockage de Claude**. Il explique
pourquoi `chocolat` peut rester introuvable malgre le patch client.

## Ce qu'il faut garder de DeepSeek

DeepSeek insiste sur :

- ne pas refondre le chat ;
- garder une structure minimale conversation/message/titre ;
- verifier la coherence `localStorage` ;
- prevoir une recherche serveur plus tard sans l'imposer tout de suite ;
- eviter cache stale / WebView incoherent.

Decision Codex : **retenir DeepSeek pour les garde-fous techniques**, mais ne pas
reprendre une grosse migration de schema maintenant.

## Ce qu'il faut garder de Cursor

Cursor rappelle :

- sidebar mobile responsive ;
- champ recherche lisible et touch-friendly ;
- pas de debordement petit ecran ;
- safe-area Android/iPhone ;
- pas de regression du mode focus.

Decision Codex : **retenir Cursor uniquement comme verification UI**, pas comme
pretexte a refaire la sidebar.

## Analyse Codex

Le patch actuel sur `main` est bon pour une V1 :

- il retrouve les conversations si le mot est dans le titre ;
- il retrouve les conversations si le mot est dans le preview ;
- il retrouve les conversations si les messages complets sont encore dans le `localStorage` de l'APK ;
- il n'abime pas l'UI validee.

Mais il ne suffit pas pour tous les anciens cas :

- si l'APK a ete reinstallee, le `localStorage` peut etre vide ;
- si le cache WebView a ete vide, les messages locaux peuvent etre absents ;
- si les messages ne sont plus dans Redis, aucune recherche serveur ne pourra les retrouver ;
- si les messages sont dans Redis mais pas localement, il faut un fallback serveur.

## Recommandation a Claude

### Phase 1 - tester le patch actuel

Faire tester a Ludovic :

- taper `chocolat` dans la sidebar ;
- verifier si une conversation ancienne ressort ;
- tester aussi un mot recent : `voix`, `APK`, `documents`.

Si ca marche : ne rien coder de plus pour l'instant.

### Phase 2 - si `chocolat` ne ressort pas

Implementer une correction minimale :

1. ajouter `GET /api/conversations/search?q=...` cote serveur ;
2. chercher dans Redis sur les conversations actives uniquement ;
3. limiter a 50 conversations max et timeout court ;
4. retourner `id`, `title`, `last_activity`, `match_excerpt`, `match_source` ;
5. cote frontend : utiliser ce fallback uniquement si la recherche locale ne trouve rien.

Cette phase permet de retrouver les conversations presentes dans Redis meme si le
`localStorage` de l'APK ne contient plus les messages.

### Phase 3 - seulement si Ludovic valide

Ajouter un endpoint admin de retitrage :

- dry-run obligatoire d'abord ;
- ne modifier que les conversations Redis actives ;
- ne jamais supprimer l'ancien titre sans trace ;
- ne pas envoyer tout l'historique a OpenAI sans limite ;
- ne pas traiter les conversations expirees ou absentes.

## Ce qu'il ne faut pas faire

- Ne pas refaire la sidebar.
- Ne pas toucher au mode focus valide.
- Ne pas supprimer les anciennes conversations.
- Ne pas promettre de retrouver une conversation qui n'existe plus ni dans Redis ni dans le telephone.
- Ne pas lancer une migration OpenAI massive des titres sans validation.
- Ne pas melanger objectif 010 avec objectif 011 Services.

## Decision recommandee a Ludovic

Choix recommande : **Option C progressive**.

1. Garder le patch local deja sur `main`.
2. Tester sur telephone.
3. Si les anciens sujets ne ressortent pas, ajouter le fallback serveur Redis.
4. Reporter le retitrage automatique a une phase separee.

Cette solution prend le meilleur de chaque agent :

- Kimi pour l'UX ;
- Claude pour la realite Redis/localStorage ;
- DeepSeek pour les garde-fous techniques ;
- Cursor pour la verification mobile ;
- Codex pour le tri et la sequence.

