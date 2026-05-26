# Retour reel APK - Objectif 010 : sidebar partielle, loupe absente, chat trop verbeux

**Date** : 2026-05-26  
**Source** : Ludovic, test Android reel  
**Statut** : Objectif 010 toujours non valide  

## Ce qui progresse

Ludovic confirme :

- la sidebar est visible ;
- les titres commencent a apparaitre dans la sidebar ;
- le bouton Deconnexion semble avoir recu une amelioration visuelle.

## Ce qui bloque encore

### 1. Loupe/recherche absente dans l'APK

Malgre le commit `0527b17` qui remplace le pseudo-element CSS par un vrai
`span.conv-search-icon`, Ludovic ne voit toujours pas de loupe ni de recherche
exploitable dans l'APK Android.

Conclusion produit :

- ce n'est pas valide ;
- il faut prouver ce que l'APK charge reellement ;
- si le DOM est correct sur Cloud Run mais absent dans l'APK, il faut investiguer
  cache WebView / service worker / APK non a jour / fichier non deploye.

Attendu :

- champ de recherche visible dans la sidebar ;
- icone loupe visible ;
- possibilite de taper un mot pour retrouver une conversation ;
- compatible Android maintenant, iPhone plus tard.

### 2. Chat trop verbeux, pas assez compagnon

Ludovic signale que Luna repond trop long, trop vite en bloc, et donne une
impression de machine.

Le besoin produit :

- Luna doit parler comme une personne ;
- reponses courtes par defaut ;
- si l'utilisateur dit "coucou" ou "ca va ?", Luna repond simplement ;
- elle ne doit pas faire un expose ou donner des informations non demandees ;
- elle developpe seulement quand l'utilisateur demande une explication, un plan,
  une analyse ou un detail.

Exemple attendu :

```text
Ludovic : Bonsoir Luna
Luna : Bonsoir Ludovic. Comment tu vas ce soir ?

Ludovic : Ca va, et toi ?
Luna : Ca va aussi. Je suis la avec toi.
```

Refuse :

```text
Bonsoir Ludovic. Voici ce que je peux faire pour toi aujourd'hui :
1. ...
2. ...
3. ...
```

## Hypothese technique

Le chat utilise deja OpenAI cote serveur, mais le prompt systeme et les consignes
de reponse poussent Luna a trop expliquer. Le probleme n'est pas de "choisir
OpenAI ou Claude" dans l'APK : le probleme est le comportement conversationnel
configure dans `luna_web.py`.

## Correction attendue

### Prompt / comportement chat

Ajouter une regle forte dans le prompt Luna :

```text
Par defaut, reponds comme une personne dans une conversation courte.
Si le message est simple, reponds en 1 a 2 phrases maximum.
Ne liste pas tes capacites sauf si l'utilisateur te le demande.
Ne donne pas d'explication technique non demandee.
Developpe seulement si l'utilisateur demande un plan, une analyse ou des details.
```

### Streaming / experience

Verifier aussi si l'affichage donne l'impression d'un bloc trop massif :

- streaming visible progressivement ;
- paragraphes courts ;
- pas de gros pave pour une intention simple.

## Questions obligatoires a l'equipe

1. Le commit `0527b17` est-il deployee sur Cloud Run ?
2. L'APK charge-t-elle bien la version Cloud Run de `static/index.html` ?
3. Le service worker a-t-il purge l'ancien HTML/CSS/JS ?
4. Pourquoi la loupe DOM n'est-elle pas visible dans Android WebView ?
5. Ou dans `luna_web.py` le prompt pousse-t-il Luna a repondre trop long ?
6. Quelle correction minimale rend Luna conversationnelle sans casser les fonctions ?

## Decision Codex

Objectif 010 reste ouvert.

Validation impossible tant que :

- recherche/loupe non visible dans l'APK ;
- Luna reste trop verbeuse par defaut ;
- l'equipe n'a pas prouve la version exacte chargee par l'APK.

