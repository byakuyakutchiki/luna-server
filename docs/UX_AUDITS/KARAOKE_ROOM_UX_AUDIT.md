# Analyse UX/UI – Salle Karaoké

## Constat général

L'écran est visuellement agréable et cohérent avec l'univers Luna (ambiance sombre, halo lumineux, effet premium), mais il souffre d'un problème important de hiérarchie visuelle et d'organisation.

Quand un utilisateur entre dans la salle, il voit principalement :

- un micro au centre ;
- le texte "En attente..." ;
- un bouton "Retour au Chat" ;
- quelques éléments dispersés.

Mais il ne comprend pas immédiatement :

- qu'il peut chanter ;
- qu'il peut ajouter une chanson ;
- qu'il peut regarder les autres chanter ;
- qu'il y a des spectateurs ;
- qu'il peut interagir ;
- combien de personnes sont présentes ;
- ce qui se passe dans la salle.

La salle paraît vide alors qu'elle possède déjà des fonctionnalités.

---

## Problème n°1 : Superposition des éléments du bas

Actuellement, le bouton "Retour au Chat" est affiché au-dessus d'une autre barre située en bas de l'écran.

**Conséquences** :
- impression de superposition ;
- impression d'interface inachevée ;
- certains éléments semblent cachés ;
- perte d'espace utile ;
- confusion visuelle.

On a l'impression qu'une couche d'interface masque une autre couche.

**Solution souhaitée** :
- fusionner les zones basses ;
- ou intégrer "Retour au Chat" directement dans la navigation ;
- ou utiliser un bouton flottant discret.

---

## Problème n°2 : L'espace central est sous-exploité

La majorité de l'écran est vide. Pourtant un karaoké est avant tout une expérience sociale.

L'espace disponible devrait servir à afficher :
- les spectateurs ;
- les chanteurs ;
- les personnes en attente ;
- les réactions ;
- la vie de la salle.

---

## Vision recherchée (inspiration StarMaker)

Lorsque l'utilisateur entre dans une salle, il doit immédiatement comprendre :
- qui chante ;
- qui regarde ;
- qui attend son tour ;
- quelles interactions sont possibles.

La salle doit paraître **vivante**, pas un écran d'attente.

---

## Organisation souhaitée

### Zone haute
- Nom de la salle
- Nombre de participants
- Lien ami
- Quitter

### Zone centrale
- Grand avatar ou micro du chanteur actuel.
- Informations visibles : chanson en cours, statut, progression éventuelle.

### Zone spectateurs
Afficher visuellement les spectateurs (ex: avatars positionnés autour de la scène).
L'utilisateur doit immédiatement voir qu'il n'est pas seul.

### Zone file d'attente
Afficher clairement :
🎤 Prochains chanteurs
1. Utilisateur A
2. Utilisateur B
3. Utilisateur C

### Zone interactions
Réactions rapides : ❤️ 👏 🔥 🎉
Messages rapides.
Effets visuels légers.

### Zone basse (UNE SEULE BARRE, sans superposition)
- Retour au chat
- Ajouter une chanson YouTube
- Réagir
- Lever la main
- Inviter un ami

---

## Fonctionnalité importante à mettre en avant

Le système permet déjà d'ajouter des liens YouTube pour le karaoké. Mais actuellement cette possibilité n'est pas mise en avant.

L'utilisateur doit comprendre immédiatement :
1. qu'il peut coller un lien YouTube ;
2. qu'il peut chanter ;
3. qu'il peut simplement regarder ;
4. qu'il peut interagir avec les autres.

---

## Objectif UX final

**En moins de 3 secondes**, un nouvel utilisateur doit comprendre :
- où il se trouve ;
- ce qu'il peut faire ;
- qui est présent ;
- comment participer.

L'interface est jolie mais ne montre pas suffisamment la vie de la salle. L'objectif est de transformer cet écran en **véritable salle de karaoké sociale**, inspirée de StarMaker, où l'activité, les spectateurs et les interactions sont immédiatement visibles.
