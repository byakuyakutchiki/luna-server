# Codex — Avis Objectif 007

**Date** : 2026-05-25  
**Branche** : `codex/objectif-007-coordination`  
**Mission** : cadrage GitHub, garde-fous, validation logique après changements directs Claude  

## Résumé

Claude a poussé directement sur `main` le commit `01ac7a5` :

> `feat(007): télémétrie vocale précise APK — 19 événements + fix session_ts`

Ce commit va dans la bonne direction technique : il corrige le problème probable de
`session_ts=0`, augmente le plafond d'événements, ajoute des événements plus précis
dans `static/index.html`, et étend l'analyse serveur dans `luna_web.py`.

Mais le processus a été raccourci : DeepSeek et Kimi avaient des rôles d'audit avant
intégration finale, et l'implémentation est déjà sur `main`. Il faut donc traiter
ce commit comme une **implémentation candidate à valider sur téléphone réel**, pas
comme une validation finale de l'objectif 007.

## Ce qui est positif

- Le heartbeat réel est validé côté objectif 006.
- Le bug `session_ts=0` est pris au sérieux : `_voiceSessionStartTs` est fixé au clic.
- Le plafond `_apkEventCount` passe de 10 à 30.
- Les événements deviennent plus précis :
  - `voice_click_received`
  - `voice_start_entered`
  - `voice_token_present`
  - `voice_micro_request_started`
  - `voice_ws_create_started`
  - `voice_capture_started`
  - `voice_first_audio_chunk_sent`
  - `voice_first_audio_chunk_received`
  - `voice_playback_started`
- Le serveur accepte les anciens et nouveaux noms d'événements, ce qui limite les
  risques de rupture.
- Kimi a fourni des textes et scénarios utiles pour le cockpit.
- DeepSeek a identifié le risque de perte silencieuse autour du token et du compteur.

## Points de vigilance

### 1. `voice_token_missing` ne peut probablement pas remonter via l'endpoint actuel

`sendApkEvent()` dépend de `getToken()` puis envoie vers `/api/apk/event` avec un
JWT. Si le token est absent, la fonction retourne avant le `fetch`.

Conséquence : un événement `voice_token_missing` appelé via `sendApkEvent()` ne peut
pas être envoyé quand le token manque vraiment.

Pour tracer ce cas, il faudrait soit :

- un endpoint public limité et sécurisé pour les événements sans token, avec garde-fous
  stricts, soit
- diagnostiquer l'absence de token localement dans l'UI, sans promettre une remontée
  serveur, soit
- s'appuyer sur l'absence totale d'événements après `voice_click_received` si ce dernier
  a pu partir avant expiration.

### 2. Le compteur est encore incrémenté avant vérification token

Dans l'intention DeepSeek, `_apkEventCount++` devait être déplacé après la vérification
du token. Le commit Claude augmente le plafond à 30, mais garde la logique où le compteur
augmente avant de savoir si l'événement est vraiment envoyé.

Ce n'est plus aussi critique qu'avec une limite à 10, mais cela reste une source de
perte silencieuse si le token est temporairement absent.

### 3. Tous les événements annoncés ne semblent pas encore instrumentés

Le serveur accepte `voice_audio_send_failed`, `voice_playback_failed` et d'autres cas,
mais le diff ne montre pas encore une instrumentation complète de tous ces chemins.

Cela peut être acceptable pour une première passe, mais il ne faut pas déclarer
l'objectif 007 terminé tant que le test réel ne montre pas une chronologie exploitable.

### 4. La validation doit rester empirique

Le critère n'est pas "le code contient 21 événements". Le critère est :

> Ludovic appuie sur le bouton vocal, puis le cockpit montre une chronologie claire
> qui explique précisément où la voix bloque.

## Avis sur les avis agents

### DeepSeek

Avis utile et techniquement pertinent. Le point le plus important est le risque
autour de `sendApkEvent()` : token absent, compteur incrémenté trop tôt, pertes
silencieuses. Ce point n'est pas entièrement résolu par le commit `01ac7a5`.

### Kimi

Avis utile pour les textes fondateur. Les scénarios proposés doivent être intégrés
progressivement, mais il faut éviter de promettre dans l'UI des états que le serveur
ne peut pas réellement observer.

### Cursor

Avis non vu à ce stade. Il reste nécessaire pour vérifier :

- lisibilité mobile de la chronologie ;
- non-régression visuelle ;
- absence de perte d'assets ;
- comportement du bouton vocal sur le téléphone réel.

## Recommandation Codex

1. Ne pas ajouter de nouvelle correction fonctionnelle voix maintenant.
2. Déployer ou tester le commit `01ac7a5` seulement si Ludovic valide explicitement.
3. Après déploiement, faire un seul test réel :
   - ouvrir Luna ;
   - appuyer une fois sur le bouton vocal ;
   - attendre 20 secondes ;
   - recharger `fondateur.html` ;
   - copier la section `Voix APK`.
4. Si la chronologie montre plusieurs événements, l'objectif 007 progresse.
5. Si la chronologie reste seulement `voice_session_ended`, il faudra corriger
   `sendApkEvent()` et/ou l'endpoint d'événements sans supposer que la voix est en cause.

## Décision proposée à Ludovic

Valider uniquement une phase de test réel du commit `01ac7a5`.

Ne pas considérer l'objectif 007 terminé tant que le cockpit ne montre pas une
chronologie vocale complète ou un point d'arrêt explicite.

