# Retour reel APK - Objectif 010 non valide

**Date** : 2026-05-26  
**Source** : Ludovic, test telephone Android reel  
**Statut** : bloquant produit  

## Verdict Ludovic

Objectif 010 n'est pas valide dans l'APK reelle.

Les corrections annoncees ne sont pas visibles ou ne produisent pas l'effet attendu.

## Observations reelles

### 1. Sidebar visible, mais loupe absente

Ludovic voit bien la sidebar de conversations.

Probleme :

- la petite loupe attendue dans la recherche n'apparait pas ;
- il faut tenir compte du contexte Android WebView ;
- l'application devra aussi etre compatible iPhone plus tard.

Hypotheses a verifier :

- CSS `::before` non rendu dans Android WebView ;
- loupe ajoutee en pseudo-element mais pas en vrai element DOM ;
- cache WebView / service worker sert une ancienne version ;
- modification non deployee ou APK non mise a jour ;
- selecteur CSS ecrase par une regle plus specifique.

Attendu :

- loupe visible comme element reel ou icone fiable ;
- champ de recherche clairement identifiable ;
- compatible Android WebView et iPhone.

### 2. Titres encore trop longs

Probleme :

- la sidebar affiche encore des phrases avec points de suspension ;
- ce n'est pas un titre facon ChatGPT ;
- ce n'est pas exploitable comme repertoire intelligent.

Attendu :

- 2 a 4 mots ;
- 5 mots maximum ;
- jamais une phrase ;
- jamais un resume ;
- pas de `...` sauf cas exceptionnel, mais l'objectif est d'eviter ce cas.

Exemples attendus :

```text
Voix Luna
Services exploitant
Bouton connexion
Historique chat
```

Refuse :

```text
Discussion autour de...
Je veux verifier que...
On doit corriger...
```

### 3. Chat trop robotique et trop verbeux

Probleme :

- Luna repond trop long ;
- elle affiche un bloc d'un coup ;
- elle donne l'impression d'une machine, pas d'un compagnon ;
- meme pour une phrase simple comme "coucou", elle ne doit pas produire un pavé.

Attendu :

- ton naturel ;
- reponses courtes par defaut ;
- sensation de conversation ;
- developpement seulement si l'utilisateur demande du detail ;
- pas de bloc massif inutile.

Reference produit :

Ludovic compare l'experience attendue a ChatGPT : une presence conversationnelle,
pas un robot qui vide un rapport.

### 4. Bouton Deconnexion toujours mange

Probleme :

- sur le telephone de Ludovic, rien n'a change ;
- le bouton reste coupe / le rendu n'est pas corrige.

Hypotheses a verifier :

- changement pas deployee ;
- APK/WebView cache une ancienne version ;
- service worker conserve ancien `static/index.html`;
- correction appliquee au mauvais fichier ou mauvais breakpoint ;
- version Android utilise encore un asset local/ancien bundle.

Attendu :

- bouton lisible ou icone claire ;
- pas de texte mange ;
- style premium conserve ;
- compatible Android maintenant et iPhone plus tard.

## Questions techniques obligatoires

Claude / DeepSeek / Cursor doivent repondre :

1. Quelle version de `static/index.html` est servie a l'APK reelle ?
2. Le service worker purge-t-il bien le cache ?
3. Le commit `0d030c5` est-il deployee sur Cloud Run ?
4. Le commit `2452edc` est-il deployee sur Cloud Run ?
5. L'APK charge-t-elle l'URL Cloud Run ou un asset local/cache ?
6. Quelle preuve visuelle ou log montre que l'APK utilise la derniere version ?

## Decision Codex

Ne pas valider l'objectif 010.

Avant toute nouvelle promesse, l'equipe doit prouver sur telephone reel :

- loupe visible ;
- titre court reel ;
- bouton Deconnexion corrige ;
- reponses chat plus naturelles et moins verbeuses.

