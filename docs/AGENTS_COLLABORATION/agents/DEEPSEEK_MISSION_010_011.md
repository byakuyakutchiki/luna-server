# DeepSeek - Mission ciblee Objectifs 010 / 011

**Date** : 2026-05-26  
**Demande** : Ludovic / Codex  
**Statut** : a traiter par DeepSeek avant nouvelle correction majeure  

## Contexte

Deux points restent ouverts et visibles dans l'APK :

1. **Objectif 010 - Chat / historique**
   - Les titres doivent etre des titres courts de repertoire, facon ChatGPT.
   - La loupe/recherche doit etre visible et utile dans la sidebar.
   - L'objectif 010 reste non valide tant que le test telephone n'est pas OK.

2. **Bug UI mobile - bouton Deconnexion**
   - Le bouton `Deconnexion` reste mange sur telephone chez Ludovic.
   - Les corrections precedentes (`white-space: nowrap`, safe-area) ne suffisent pas.

Objectif 011 Services/Conciergerie continue en parallele, mais ne doit pas faire
oublier ces regressions visibles.

## Regle DeepSeek

Ne pas refondre.
Ne pas coder a l'aveugle.
Observer le code reel, proposer une correction minimale, puis attendre validation.

## Mission A - Verifier les titres ChatGPT

Fichiers a auditer :

```text
luna_web.py
static/index.html
```

Questions obligatoires :

1. Les deux chemins chat (`/api/chat` streaming et non-streaming) utilisent-ils
   bien le meme prompt de titrage court ?
2. Le prompt interdit-il explicitement les resumes ?
3. Le garde-fou coupe-t-il vraiment les titres trop longs ?
4. Le fallback peut-il encore produire une phrase de 40 caracteres ?
5. `auto_title` est-il bien applique a la conversation courante dans la sidebar ?
6. Une conversation existante avec ancien resume garde-t-elle un titre trop long ?

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_010_TITRES.md
```

Contenu :

- verdict : OK / fragile / non OK ;
- lignes concernees ;
- correction minimale proposee si necessaire ;
- test exact a faire sur telephone.

## Mission B - Verifier la loupe/recherche historique

Questions obligatoires :

1. La loupe est-elle un vrai element visible ou seulement un padding ?
2. Le champ `convSearch` est-il visible sur mobile ?
3. La recherche filtre-t-elle par titre ?
4. La recherche filtre-t-elle aussi par `preview` ?
5. Que voit l'utilisateur si aucun resultat ?

Validation attendue :

```text
Taper "voix" retrouve une conversation dont le titre ou l'apercu contient voix.
Taper "services" retrouve une conversation Services exploitant.
```

## Mission C - Bouton Deconnexion mange

Fichiers a auditer :

```text
static/index.html
docs/AGENTS_COLLABORATION/BUG_UI_MOBILE_DECONNEXION.md
```

Questions obligatoires :

1. Quelle est la cause exacte ?
   - bouton trop long ?
   - header droit trop charge ?
   - logo + wakeword + MAJ + Deconnexion trop larges ?
   - safe-area insuffisante ?
   - overflow cache par parent ?
2. La correction CSS existante est-elle appliquee au bon element ?
3. Quelle solution mobile propre propose DeepSeek ?

Solutions possibles a comparer :

- garder `Deconnexion` mais reduire intelligemment le header ;
- passer a `Sortir` sous 380px ;
- icone + tooltip/aria-label ;
- menu compte/profil contenant `Deconnexion` ;
- cacher le logo sur tres petit ecran.

Contrainte Ludovic :

Le rendu doit rester premium. Pas de bricolage moche.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_UI_DECONNEXION.md
```

## Mission D - Lien avec Objectif 011 Services

DeepSeek doit garder en tete que l'objectif 011 Services/Conciergerie continue.
Mais il ne doit pas melanger :

- correction chat/historique ;
- correction header mobile ;
- audit Services.

Pour Services, DeepSeek doit produire separement :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_011.md
```

avec la table :

```text
Carte -> handler JS -> action /api/concierge/action -> tool Python -> risque -> test sans danger
```

## Interdits

- Ne pas deployer.
- Ne pas tester SMS/email/appel/visio/alerte/resevation reels.
- Ne pas modifier directement `main`.
- Ne pas proposer une refonte complete du chat.
- Ne pas exposer de secret, cle API, token ou donnees privees dans GitHub.

## Validation finale Ludovic

Objectif 010 est valide seulement si :

- titre court 2 a 4 mots ;
- recherche/loupe visible ;
- ancienne conversation retrouvable ;
- bouton `Deconnexion` lisible ou remplace proprement sur mobile.

