# Claude - retour Ludovic objectif 010 UI sidebar

**Date** : 2026-05-27  
**Source** : test reel Ludovic sur APK Android  
**Statut** : information de coordination obligatoire avant suite de l'objectif 010

## Retour principal

Ludovic confirme que la sidebar fonctionne maintenant tres bien sur telephone.

La solution de mode focus / meilleure lisibilite, attribuee a Kimi dans le retour utilisateur, est consideree comme la bonne direction UX.

Point a retenir pour Claude :

- la correction validee doit etre preservee ;
- ne pas refaire la sidebar ;
- ne pas degrader le graphisme premium ;
- ne pas appliquer une correction rapide qui ramene les superpositions ;
- tenir compte de l'avis Kimi comme reference sur cette partie UI.

Formulation exacte a garder en tete :

> Kimi a reussi sur cette partie sidebar la ou les corrections precedentes n'avaient pas suffi.

Ce n'est pas une consigne de conflit entre agents. C'est une trace de decision produit : l'intuition UX retenue est celle qui a marche sur le telephone de Ludovic.

## Ce qui reste a traiter

### Titres et recherche des anciennes conversations

Probleme reel :

- les nouveaux titres sont meilleurs ;
- mais certaines anciennes conversations ne sont pas retrouvees par sujet ;
- exemple Ludovic : conversations parlant de chocolat non retrouvees.

Claude doit instruire avant de coder :

1. ou sont stockees les anciennes conversations ;
2. si leurs titres peuvent etre regeneres ;
3. si la recherche sidebar interroge seulement les titres ou aussi le contenu ;
4. si une migration est possible sans perdre de messages ;
5. si la recherche doit etre locale, serveur, ou hybride.

## Decision attendue

Ne pas coder directement une refonte.

Proposer a Ludovic une decision simple :

- repartir proprement seulement sur les nouvelles conversations ;
- ou migrer/indexer les anciennes conversations ;
- ou ajouter une recherche plein texte qui retrouve les anciennes conversations meme avec de mauvais titres.

