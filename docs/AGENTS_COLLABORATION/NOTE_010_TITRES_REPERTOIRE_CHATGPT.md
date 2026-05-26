# Note Objectif 010 - Titres de repertoire, pas resumes

**Date** : 2026-05-26  
**Auteur** : Codex, d'apres retour Ludovic  
**Statut** : correction produit a appliquer avant validation Objectif 010  

## Probleme signale par Ludovic

Ludovic ne demande pas un resume de conversation.

Il demande un **titre court de repertoire**, comme dans ChatGPT, pour retrouver
rapidement une ancienne discussion dans la liste de gauche.

Le probleme actuel : Luna/Claude genere parfois une phrase trop longue ou un
mini-resume. Ce n'est pas le besoin produit.

## Attendu exact

Un titre doit etre :

- tres court ;
- 2 a 4 mots idealement ;
- maximum 5 mots si necessaire ;
- lisible dans une sidebar mobile ;
- utile pour retrouver une discussion ;
- sans phrase, sans resume, sans date ;
- sans "Discussion sur", "Resume de", "Conversation a propos de".

## Exemples acceptes

```text
Voix Luna
Historique chat
Bouton connexion
Services exploitant
Documents coffre
Recherche hotels
SMS confirmation
Memoire Luna
Objectif 010
```

## Exemples refuses

```text
Resume de notre conversation sur la voix Luna
Discussion autour de l'historique intelligent des conversations
Conversation du 26 mai
Nouvelle conversation
L'utilisateur parle du bouton de connexion coupe sur mobile
```

## Correction attendue cote Claude

### Backend

Remplacer les prompts qui commencent par :

```text
Resume cette conversation...
```

par une consigne de titrage stricte :

```text
Genere un titre de repertoire en francais, 2 a 4 mots, maximum 5.
Pas de phrase. Pas de resume. Pas de date. Pas de guillemets.
Interdit : "Discussion sur", "Conversation", "Resume".
Retourne uniquement le titre.
```

Si le modele renvoie trop long :

- couper proprement a 5 mots ;
- ou regenerer ;
- ne jamais afficher une phrase complete dans la sidebar.

### Frontend

Le panneau historique doit se comporter comme ChatGPT :

- bouton trois traits ouvre la liste ;
- chaque conversation affiche un titre court ;
- une petite loupe/barre de recherche permet de retrouver une conversation ;
- recherche par titre + apercu minimum ;
- pas de titre generique si la conversation contient deja des messages.

## Validation Ludovic

Creer une conversation test :

```text
On doit corriger la recherche dans l'historique comme ChatGPT
```

Attendu dans la sidebar :

```text
Historique ChatGPT
```

ou :

```text
Recherche historique
```

Refuse :

```text
Discussion sur la recherche dans l'historique comme ChatGPT
```

## Decision

Objectif 010 n'est pas valide tant que les titres ressemblent a des resumes.
