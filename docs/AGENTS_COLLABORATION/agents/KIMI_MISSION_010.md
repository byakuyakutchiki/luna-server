# Kimi — Mission Objectif 010

**Date** : 2026-05-26  
**De** : Claude (lead)  
**Pour** : Kimi  
**Urgence** : normale

---

## Contexte

Le serveur génère des titres de conversation via GPT-4o-mini avec ce prompt :

> "Tu generes un titre court (4-6 mots max) pour une conversation.
>  Pas de guillemets, pas de ponctuation finale. Juste le theme principal."

Entrée : `User: {premier message}\nLuna: {première réponse}`

## Ta mission

Améliorer la qualité des titres générés et définir les règles UX.

### Amélioration du prompt de titrage

Propose un meilleur prompt système (en français, <150 chars) qui produit des titres :
- 3 à 5 mots
- Thème dominant, pas le détail
- Pas de verbe inutile ("discussion sur", "question à propos de")
- Lisibles d'un coup d'œil dans une sidebar de 200px
- Exemples attendus :
  - "Voix Luna instable" ✅
  - "Discussion sur la voix de Luna qui ne fonctionne pas" ❌
  - "Historique conversations" ✅
  - "Bouton mobile coupé" ✅
  - "Réservation restaurant Paris" ✅

### Règles UX mémoire Luna (déjà validées — confirme)

1. Luna utilise sa mémoire uniquement si la question le nécessite
2. Elle ne récite pas sa mémoire au début de chaque réponse
3. Elle n'expose jamais les noms de technologies (OpenAI, Redis, etc.)
4. La mémoire conversationnelle reste dans la session, pas entre sessions

### Textes interface sidebar

Propose les textes pour :
- Placeholder barre de recherche : "Rechercher..." → ok ou mieux ?
- Bouton nouvelle conversation : "+ Nouvelle conversation" → ok ou mieux ?
- État vide (aucune conversation) : que voir l'utilisateur ?
- État "aucun résultat de recherche" : que lire l'utilisateur ?

## Livrable attendu

`docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_010.md`

Contenu :
- Nouveau prompt de titrage (une ligne, prêt à copier-coller)
- Règles UX mémoire confirmées ou ajustées
- Textes interface (4 items ci-dessus)

## Interdit

- Ne pas proposer de refonte du système de mémoire
- Ne pas proposer de nouveaux endpoints serveur
- Ne pas dépasser 1 page de texte
