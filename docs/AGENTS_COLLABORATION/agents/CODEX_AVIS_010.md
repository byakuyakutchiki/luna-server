# Codex — Avis Objectif 010

**Date** : 2026-05-25  
**Objectif** : Historique intelligent des conversations + mémoire Luna  
**Rôle** : coordination, garde-fous mémoire, séparation architecture / UI mobile  

## Verdict

L'objectif 010 est pertinent et prioritaire pour rendre Luna utilisable au quotidien.

Le besoin se divise en trois chantiers qui doivent rester séparés :

1. historique de conversations ;
2. mémoire utile Luna ;
3. bug UI mobile `Connexion` / `Déconnexion` coupé.

## Recommandation d'architecture

### Conversations

Créer un modèle logique :

```json
{
  "conversation_id": "uuid",
  "tenant_id": 1,
  "user_id": 1,
  "title": "Voix Luna et OpenAI Realtime",
  "created_at": "2026-05-25T20:00:00+02:00",
  "updated_at": "2026-05-25T20:12:00+02:00",
  "messages_count": 42,
  "last_summary": "Discussion sur la stabilité voix Luna"
}
```

Les messages peuvent rester dans le stockage actuel au début, mais il faut préparer
une séparation claire entre conversations.

### Titres automatiques

Première version simple :

- générer un titre après 2 à 4 messages ;
- utiliser une heuristique locale ou un appel LLM serveur ;
- ne jamais bloquer l'envoi du message si le titre échoue ;
- permettre un titre temporaire : `Nouvelle conversation`.

### Mémoire utile

Séparer :

- mémoire globale projet Luna ;
- mémoire utilisateur/fondateur ;
- mémoire conversationnelle ;
- état objectifs GitHub / cockpit.

Luna doit utiliser cette mémoire pour répondre juste, mais ne doit pas la réciter.

## Garde-fous

- Pas de clés API, tokens, secrets ou données privées inutiles dans la mémoire.
- Pas de transcript vocal privé stocké comme mémoire durable sans validation.
- Pas de refactor complet du chat en une seule fois.
- Pas de suppression des historiques existants.
- Pas de mélange entre correction UI mobile et modèle backend.

## Plan de livraison minimal

1. Auditer l'existant.
2. Ajouter structure conversation côté frontend.
3. Ajouter stockage conversation minimal.
4. Ajouter menu liste conversations.
5. Ajouter génération titre automatique.
6. Ajouter mémoire utile projet en lecture contrôlée.
7. Corriger le bouton mobile coupé dans une petite correction CSS isolée.

## Critère de validation Ludovic

Sur téléphone :

- Ludovic voit le menu trois traits.
- Il peut démarrer une nouvelle conversation.
- Il peut revenir à une ancienne conversation.
- Les conversations ont un titre lisible.
- Le bouton `Connexion` / `Déconnexion` n'est plus coupé.
- Luna sait répondre sur son architecture quand c'est pertinent, sans faire un exposé inutile.

