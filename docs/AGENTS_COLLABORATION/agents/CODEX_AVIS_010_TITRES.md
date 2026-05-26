# Codex - Avis Objectif 010 - Titres courts et recherche historique

**Date** : 2026-05-26  
**Objectif** : 010 - Historique intelligent des conversations  
**Statut** : correction de cap apres test Ludovic  

## Verdict

Ludovic ne demande pas un resume de conversation.

Il demande un titre de repertoire, comme dans ChatGPT, pour retrouver rapidement
une ancienne discussion dans la colonne de gauche.

Le comportement actuel est encore trop proche d'un resume. Ce n'est pas valide.

## Ce que Claude doit coder

### 1. Titre court, pas resume

Le prompt de titrage ne doit plus commencer par :

```text
Resume cette conversation...
```

Il doit demander :

```text
Genere un titre de repertoire en francais, 2 a 4 mots, maximum 5.
Pas de phrase. Pas de resume. Pas de date. Pas de guillemets.
Interdit : "Discussion sur", "Conversation", "Resume".
Retourne uniquement le titre.
```

### 2. Controle de longueur apres generation

Si le modele renvoie une phrase :

- supprimer les prefixes interdits ;
- couper a 5 mots maximum ;
- ne jamais afficher une phrase complete dans la sidebar.

### 3. Recherche visible avec loupe

Le panneau historique doit comporter une recherche visible, comme ChatGPT :

- petite loupe ;
- champ `Rechercher...` ;
- recherche par titre ;
- recherche par apercu minimum ;
- resultat en direct pendant la saisie.

## Exemples attendus

Acceptes :

```text
Voix Luna
Historique chat
Bouton connexion
Services exploitant
Documents coffre
Recherche hotels
SMS confirmation
```

Refuses :

```text
Resume de notre conversation sur la voix Luna
Discussion autour de l'historique intelligent
Conversation du 26 mai
Nouvelle conversation
```

## Validation Ludovic

Créer une discussion :

```text
On doit corriger la recherche dans l'historique comme ChatGPT
```

La sidebar doit afficher un titre du type :

```text
Historique ChatGPT
```

ou :

```text
Recherche historique
```

Si elle affiche une phrase ou un resume, l'objectif 010 reste non valide.

