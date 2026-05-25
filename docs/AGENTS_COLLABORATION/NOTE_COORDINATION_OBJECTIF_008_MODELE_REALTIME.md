# Note coordination — Objectif 008 modèle Realtime

**Date** : 2026-05-25  
**Auteur** : Codex  
**But** : donner à Kimi, DeepSeek, Cursor et Claude l'état exact avant le choix modèle  

## État actuel

Objectif 007 a validé la télémétrie APK : le téléphone réel remonte le clic, le
token, le micro, la capture audio, l'ouverture WebSocket et le premier audio envoyé.

Objectif 008 a déplacé le diagnostic côté serveur voix / OpenAI Realtime.

Claude a déjà poussé sur `main` :

- `aa3ff32` — correction bridge OpenAI Realtime ;
- `3710143` — rapports Cloud Run, Sentry et bug UI mobile ;
- `aa12e0e` — correction télémétrie `voice_ws_closed` / `session_ts`.

## Problème restant

Le test réel après correction bridge a encore échoué.

La télémétrie a montré une régression temporaire : seul `voice_ws_closed` apparaissait.
Claude a identifié la cause : `stopVoice()` remettait `_voiceSessionStartTs` à 0 avant
que `onclose` envoie `voice_ws_closed`.

Le fix `aa12e0e` ajoute `_voiceWsClosedSent` pour envoyer `voice_ws_closed` pendant
que le `session_ts` est encore valide.

## Décisions proposées par Codex

### Décision A — Télémétrie

Valider le fix télémétrie `aa12e0e` comme correction isolée.

But : retrouver une chronologie complète dans le cockpit avant tout nouveau test modèle.

Test Ludovic attendu :

1. ouvrir Luna ;
2. appuyer une fois sur le bouton vocal ;
3. attendre 20 secondes ;
4. recharger `fondateur.html` ;
5. vérifier que la section `Voix APK` affiche plusieurs événements, pas seulement `voice_ws_closed`.

### Décision B — Modèle OpenAI Realtime

Claude indique que les modèles disponibles sur le compte sont maintenant :

- `gpt-realtime`
- `gpt-realtime-mini`
- autres variantes `gpt-realtime-*`

Les anciens modèles `gpt-4o-realtime-preview*` ne sont pas disponibles sur ce compte.

Proposition Codex : tester d'abord `gpt-realtime-mini`.

Raison :

- test plus léger ;
- risque/coût plus bas ;
- suffisant pour prouver que la chaîne audio serveur → OpenAI → APK fonctionne ;
- si `mini` fonctionne, comparer ensuite avec `gpt-realtime` pour la qualité.

## Rôle des agents

### Claude

- Ne pas mélanger fix télémétrie et changement modèle dans une explication floue.
- Annoncer clairement ce qui est déjà déployé et ce qui reste à valider.
- Si Ludovic valide le modèle, changer uniquement `OPENAI_REALTIME_MODEL`.
- Après test, fournir logs Cloud Run exacts si échec.

### DeepSeek

- Vérifier que le fix `_voiceWsClosedSent` restaure réellement le groupement `session_ts`.
- Auditer les chemins JS où `stopVoice()` et `onclose` peuvent envoyer deux événements de fermeture.
- Vérifier que la télémétrie reste fiable avant changement modèle.

### Kimi

- Vérifier que les textes du cockpit expliquent bien :
  - télémétrie restaurée ;
  - voix toujours non réparée tant que modèle non validé ;
  - distinction entre panne serveur et panne APK.

### Cursor

- Vérifier la régression UI mobile `Déconnexion` coupé.
- Ne pas mélanger correction UI mobile et correction voix serveur.

### Codex

- Maintenir la séparation :
  1. restaurer les yeux ;
  2. tester le modèle ;
  3. valider sur téléphone réel ;
  4. seulement ensuite corriger plus profond.

## Validation Ludovic proposée

Réponse courte recommandée :

```text
Je valide le fix télémétrie déjà poussé si son seul but est de restaurer la chronologie.
Je valide ensuite le test du modèle OPENAI_REALTIME_MODEL=gpt-realtime-mini,
dans une étape séparée et clairement annoncée.
Pas de refactor, pas de modification APK, pas de correction UI dans le même déploiement.
```

