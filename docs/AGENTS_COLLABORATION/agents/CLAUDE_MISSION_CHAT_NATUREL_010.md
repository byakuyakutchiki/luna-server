# Claude - Mission Objectif 010 : chat naturel et recherche visible

**Date** : 2026-05-26  
**Source** : retour reel Ludovic  
**Priorite** : haute  

## Contexte

Ludovic confirme que les titres commencent a apparaitre dans la sidebar.

Mais deux blocages restent :

1. la loupe/recherche n'apparait toujours pas dans l'APK Android ;
2. Luna repond trop long et trop robotique par defaut.

Lire :

```text
docs/AGENTS_COLLABORATION/RETOUR_REEL_APK_010_CHAT_NATUREL_2026-05-26.md
```

## Mission 1 - Prouver la version chargee par l'APK

Avant toute nouvelle correction, prouver :

- revision Cloud Run active ;
- hash/version de `static/index.html` servie ;
- si service worker cache encore l'ancien fichier ;
- si l'APK doit etre rebuild ou si purge cache suffit.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/CLAUDE_AVIS_VERSION_APK_010.md
```

## Mission 2 - Recherche/loupe vraiment visible

Le commit `0527b17` ajoute un vrai element DOM :

```html
<span class="conv-search-icon">🔍</span>
```

Si Ludovic ne le voit pas, verifier :

- est-il dans le DOM reel de l'APK ?
- est-il cache par CSS ?
- est-il hors viewport ?
- le champ recherche est-il focusable ?
- le clavier Android s'ouvre-t-il ?

## Mission 3 - Rendre Luna conversationnelle

Le chat doit etre plus humain :

- reponses courtes par defaut ;
- 1 a 2 phrases pour une salutation ou un message simple ;
- pas de liste de capacites non demandee ;
- pas d'explication technique spontanee ;
- developper seulement si Ludovic demande du detail.

Correction minimale attendue :

- ajuster le prompt systeme Luna dans `luna_web.py` ;
- ne pas changer les tools ;
- ne pas casser les actions ;
- garder les reponses detaillees pour les demandes complexes.

## Test produit

Test 1 :

```text
Ludovic : Bonsoir Luna
Luna attendu : Bonsoir Ludovic. Comment tu vas ce soir ?
```

Test 2 :

```text
Ludovic : Ca va et toi ?
Luna attendu : Ca va aussi. Je suis la avec toi.
```

Test 3 :

```text
Ludovic : Explique-moi l'objectif 011
Luna peut repondre plus long, mais structure clairement.
```

## Interdits

- Ne pas faire une refonte du chat.
- Ne pas changer de fournisseur sans decision Ludovic.
- Ne pas deployer une nouvelle correction sans expliquer ce qui change.

