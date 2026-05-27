# Retour reel APK 010 - validation UI sidebar

**Date** : 2026-05-27  
**Testeur** : Ludovic  
**Support** : APK Android reelle  
**Objectif** : 010 - Historique intelligent des conversations + UI mobile chat

## Verdict Ludovic

La correction UI de la sidebar fonctionne tres bien sur telephone.

Points valides :

- ouverture de la sidebar plus lisible ;
- mode focus sidebar correctement compris ;
- barres superposees mieux gerees ;
- loupe visible et utilisable ;
- bouton deconnexion corrige sur mobile ;
- experience generale plus propre.

## Point important pour l'equipe

Ludovic demande que ce retour soit note clairement :

> La solution apportee par Kimi sur la sidebar a reussi la ou les corrections precedentes n'avaient pas regle le probleme.

Ce retour ne doit pas etre lu comme une critique personnelle, mais comme une information de coordination :

- Kimi a eu la bonne intuition UX sur le mode sidebar deploye ;
- Claude doit tenir compte de cette proposition validee avant de continuer ;
- les prochaines corrections UI doivent conserver cette qualite visuelle ;
- aucune correction rapide ne doit degrader le graphisme actuel.

## Reste ouvert

Deux points restent a ameliorer avant validation complete de l'objectif 010.

### 1. Titres des conversations

Le titre court fonctionne mieux, mais la recherche/reprise par sujet reste insuffisante.

Exemple donne par Ludovic :

- certaines anciennes conversations parlaient de chocolat ;
- Luna / la sidebar ne les retrouve pas correctement ;
- il faut decider si l'on migre les anciennes conversations ou si l'on applique le nouveau titrage uniquement aux nouvelles.

Decision a instruire :

- option A : ne pas retoucher les anciennes conversations et repartir proprement pour les nouvelles ;
- option B : lancer une migration de titres/indexation sur les anciennes conversations ;
- option C : proposer une recherche plein texte locale/serveur qui retrouve les anciennes conversations meme si le titre est mauvais.

### 2. Amelioration visuelle fine

La base UI est maintenant bonne. Les futures modifications doivent etre des ameliorations fines :

- conserver le style premium ;
- ne pas casser la sidebar ;
- ne pas remettre de superposition entre header, tabs et historique ;
- verifier sur Android WebView et, si possible, anticiper iPhone/Safari.

## Consigne de suite

Avant de coder, l'equipe doit proposer :

1. comment retrouver les anciennes conversations par sujet ;
2. comment renommer ou indexer les titres deja crees ;
3. comment garder une recherche rapide dans la sidebar ;
4. quel risque existe sur cache WebView / localStorage / stockage serveur.

