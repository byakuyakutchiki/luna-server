# DeepSeek - Mission retour reel APK Objectif 010

**Date** : 2026-05-26  
**Source** : Ludovic / Codex  
**Priorite** : bloquant  

## Contexte

Ludovic a teste l'APK Android reelle.

Verdict : les corrections annoncees pour l'objectif 010 ne sont pas visibles ou
ne fonctionnent pas dans l'application.

Lis d'abord :

```text
docs/AGENTS_COLLABORATION/RETOUR_REEL_APK_010_2026-05-26.md
```

## Mission DeepSeek

Produire un diagnostic technique, pas une refonte.

Livrable :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_RETOUR_REEL_APK_010.md
```

## Points a verifier

### 1. Loupe absente

Verifier si la loupe est :

- un pseudo-element CSS fragile ;
- un vrai element DOM ;
- cachee par CSS ;
- incompatible Android WebView ;
- absente parce que l'APK sert une ancienne version.

Proposer une correction minimale robuste :

- idealement une vraie icone DOM/SVG dans `.conv-search-wrap`, pas seulement `::before`.

### 2. Titres trop longs

Verifier :

- les deux chemins `auto_title` ;
- le fallback ;
- la troncature ;
- les anciens titres deja stockes ;
- si la sidebar affiche `title`, `preview` ou autre chose.

Proposer une correction minimale :

- titre max 4 mots cote serveur ;
- nettoyage des prefixes ;
- migration douce ou regeneration pour les conversations recentes si titre trop long.

### 3. Chat trop verbeux

Verifier dans `luna_web.py` / prompt systeme :

- consignes de longueur ;
- comportement par defaut ;
- pourquoi Luna repond en blocs trop longs ;
- si le mode compagnon impose une reponse courte.

Proposer une correction minimale :

- reponses courtes par defaut ;
- une question simple -> reponse simple ;
- detail seulement si demande.

### 4. Deconnexion toujours coupe

Verifier :

- breakpoint mobile ;
- cache/service worker ;
- APK charge-t-elle la derniere version ;
- correction appliquee au bon element ;
- Android WebView rend-il bien l'icone seule.

## Regles

- Ne pas deployer.
- Ne pas modifier `main` directement.
- Ne pas faire de refonte.
- Donner lignes/fichiers exacts.
- Donner une solution testable sur Android reel.

