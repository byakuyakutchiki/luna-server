# Objectif 006 — Validation du cerveau Luna sur panne vocale réelle

**Date ouverture** : 2026-05-25  
**Statut** : ouvert — test réel Ludovic en cours  
**Priorité** : critique  
**Lead final** : Claude  
**Décideur** : Ludovic  

## Contexte

Les objectifs 003, 004 et 005 ont posé la base du cerveau Luna :

- heartbeat APK pour savoir si le téléphone fondateur est vivant ;
- diagnostic fondateur pour interpréter les signaux APK ;
- événements voix APK pour comprendre ce qui se passe quand Ludovic appuie sur le bouton vocal.

Ludovic teste maintenant l'APK réelle. Le constat utilisateur reste : le bouton vocal peut ne rien produire après 15 à 20 secondes.

L'objectif 006 ne consiste pas d'abord à recoder la voix. Il consiste à vérifier si le cerveau Luna voit, explique et trace correctement cette panne réelle.

## But précis

Répondre à une seule question :

> Quand Ludovic reproduit la panne vocale sur son téléphone, est-ce que Luna sait exactement à quelle étape le flux échoue ?

Si oui, l'équipe corrige la cause précise.  
Si non, l'équipe corrige d'abord l'instrumentation du cerveau.

## Pipeline attendu

1. Ludovic ouvre l'APK installée.
2. Le heartbeat APK confirme que le téléphone fondateur est vu récemment.
3. Ludovic appuie sur le bouton vocal.
4. L'APK ou le frontend envoie les événements voix à `POST /api/apk/event`.
5. Le serveur conserve la chronologie.
6. Le cockpit fondateur affiche un diagnostic humain :
   - ce que Luna sait ;
   - ce que Luna suppose ;
   - ce que Luna recommande ;
   - ce que Luna ne peut pas faire seule.
7. Le journal fondateur garde la trace du test, de la conclusion et de la correction proposée.

## Rôles par agent

| Agent | Rôle objectif 006 | Livrable attendu | Autorisation |
|---|---|---|---|
| **Ludovic** | Testeur réel et validateur final | Reproduire la panne, confirmer ce qu'il voit dans l'APK et le cockpit | Peut valider ou refuser une correction |
| **Claude** | Lead final, intégrateur, déploiement | Lire les avis, trancher, corriger au minimum, déployer seulement après validation | Peut modifier `main` et Cloud Run avec accord Ludovic |
| **Codex** | Orchestration GitHub, garde-fous, cadrage | Définir l'objectif, rôles, critères de validation, points de contrôle | Pas de déploiement production |
| **DeepSeek** | Analyse technique locale VS Code | Vérifier `startVoice()`, injections `sendApkEvent()`, timers, WebSocket, erreurs JS | Branche `ds/objectif-006-*`, pas de push direct main |
| **Kimi** | Audit humain et logique diagnostic | Vérifier que les textes cockpit sont compréhensibles et non trompeurs | Avis documentaire / code review, pas de déploiement |
| **Cursor** | Cohérence UI et non-régression frontend | Vérifier que la section voix et les assets restent propres, sans casser l'expérience mobile | Branche `cursor/objectif-006-*`, pas de main |

## Mission de DeepSeek

DeepSeek doit travailler localement dans VS Code et répondre clairement :

1. Est-ce que `sendApkEvent()` est bien appelé quand le bouton vocal est pressé ?
2. Est-ce que le timer silence 15/20 secondes déclenche bien `voice_no_audio_after_timeout` ?
3. Est-ce que les erreurs WebSocket et micro remontent réellement ?
4. Est-ce qu'un événement peut être perdu si `startVoice()` échoue tôt ?
5. Quelle correction minimale proposer si les événements ne partent pas ?

DeepSeek ne doit pas déployer et ne doit pas modifier l'accès Google Cloud.

## Mission de Kimi

Kimi doit vérifier le sens humain du diagnostic :

1. Est-ce que le cockpit explique la panne sans accuser Ludovic ?
2. Est-ce que `luna_sait`, `luna_suppose`, `luna_recommande`, `luna_ne_peut_pas` sont cohérents ?
3. Est-ce que les messages distinguent bien absence de heartbeat, absence d'événement voix, et silence audio réel ?
4. Est-ce que le journal fondateur raconte l'histoire de manière lisible ?

## Mission de Cursor

Cursor doit vérifier l'expérience visuelle et mobile :

1. Aucun logo, image ou asset ne doit disparaître.
2. La section voix du cockpit doit rester lisible sur mobile.
3. Les événements JS ne doivent pas casser `startVoice()`.
4. Aucun bouton existant ne doit changer de comportement.

## Mission de Codex

Codex tient le cadre :

1. Maintenir les documents GitHub de coordination.
2. Séparer diagnostic, correction, déploiement et validation.
3. Empêcher que plusieurs agents corrigent la même zone en même temps.
4. Vérifier que les livrables sont traçables dans GitHub.

## Mission finale de Claude

Claude intervient en dernier pour intégrer :

1. Lire les avis DeepSeek, Kimi, Cursor et Codex.
2. Vérifier les faits dans les logs, Redis, endpoints admin et code.
3. Identifier le cas exact :
   - aucun heartbeat ;
   - heartbeat OK mais aucun événement voix ;
   - événements voix présents mais pas d'audio reçu ;
   - audio reçu côté serveur mais pas joué côté WebView ;
   - erreur permission/micro/WebSocket.
4. Proposer une correction minimale.
5. Demander validation Ludovic si changement majeur, rebuild APK ou déploiement.
6. Déployer uniquement après validation explicite.
7. Mettre à jour le journal fondateur avec résultat et commit.

## Critères de réussite

- [ ] Heartbeat APK réel visible dans le cockpit.
- [ ] Test vocal Ludovic produit une chronologie d'événements.
- [ ] Le cockpit indique clairement si la panne est côté APK, frontend, WebSocket, serveur voix ou playback.
- [ ] Une action recommandée est affichée.
- [ ] Le journal fondateur contient le test et la conclusion.
- [ ] Aucun asset graphique n'a disparu.
- [ ] Ludovic valide que le diagnostic correspond à ce qu'il vit sur le téléphone.

## Interdictions

- Pas de déploiement Cloud Run sans validation Ludovic.
- Pas de rebuild APK sans validation Ludovic.
- Pas de correction massive de `startVoice()` sans diagnostic.
- Pas de collecte d'audio brut, transcript privé, géolocalisation ou secret.
- Pas de modification directe de `main` par DeepSeek, Kimi, Cursor ou Codex.
- Pas de validation technique si l'interface visuelle a régressé.

## Message court à l'équipe

Objectif 006 = prouver que le cerveau Luna voit la panne voix réelle de Ludovic.

Avant de corriger, chaque agent doit répondre : quel signal est reçu, quel signal manque, et quelle conclusion Luna peut afficher au fondateur.

Claude tranche en dernier, corrige au minimum, et ne déploie qu'après validation Ludovic.
