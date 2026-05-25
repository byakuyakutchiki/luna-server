# Note coordination — Objectif 007

**Date** : 2026-05-25  
**Auteur** : Codex  
**But** : clarifier l'état après changements directs sur `main`

## État GitHub observé

Claude a poussé directement sur `main` :

- `01ac7a5` — `feat(007): télémétrie vocale précise APK — 19 événements + fix session_ts`

DeepSeek et Kimi ont rendu leurs avis :

- `ds/objectif-007-telemetrie-voix` — `DEEPSEEK_AVIS_007.md`
- `kimi/objectif-007-telemetrie-voix` — `KIMI_AVIS_007.md`

Cursor n'est pas encore vu pour l'objectif 007.

## Clarification importante

Le commit `01ac7a5` est une implémentation candidate.
Il ne valide pas encore l'objectif 007.

La validation reste le test réel Ludovic :

1. APK ouverte sur téléphone réel.
2. Appui unique sur le bouton vocal.
3. Attente 20 secondes.
4. Lecture du cockpit fondateur.
5. Chronologie vocale complète ou point d'arrêt explicite.

## Garde-fous

- Ne pas corriger la voix fonctionnelle avant d'avoir une chronologie réelle exploitable.
- Ne pas déclarer "télémétrie complète" tant que le cockpit ne le prouve pas.
- Ne pas déployer de nouvelle modification majeure sans validation Ludovic.
- Conserver les avis DeepSeek/Kimi comme entrées de validation, pas comme simples annexes.

## Point technique à surveiller

`voice_token_missing` ne peut probablement pas remonter via `/api/apk/event` si le token
est réellement absent, car l'endpoint exige un JWT.

Donc une absence de token devra être traitée avec prudence :

- soit par un mécanisme local ;
- soit par un endpoint public limité et sécurisé ;
- soit par l'absence d'événements comme signal indirect.

## Prochaine étape recommandée

Claude doit annoncer clairement si `01ac7a5` a été déployé ou non.

Si déployé : Ludovic teste et copie la section `Voix APK`.

Si non déployé : attendre validation Ludovic avant déploiement.

