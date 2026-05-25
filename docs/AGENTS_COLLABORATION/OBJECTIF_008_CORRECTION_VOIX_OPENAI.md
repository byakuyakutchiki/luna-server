# Objectif 008 — Correction voix OpenAI Realtime : modèle + bridge

**Statut** : ouvert — cadrage multi-agents  
**Priorité** : critique  
**Lead** : Claude  
**Date ouverture** : 2026-05-25  
**Dépendance** : Objectif 007 validé (télémétrie vocale prouve que le blocage est côté serveur)

---

## Cause racine identifiée (logs Cloud Run 16:47 UTC)

Séquence observée :
```
16:47:22  WebVoiceBridge démarré
16:47:23  OpenAI Realtime connecté
16:47:25  WARNING: OpenAI WS closed during send   ← RUPTURE
16:47:25  "session configured" (log trompeur — après la rupture)
16:47:25  "greeting sent" (log trompeur — envoi non réel)
16:47:25  WebVoiceBridge terminé
```

**Modèle configuré** : `gpt-4o-realtime-preview-2024-12-17`

Cette version datée de décembre 2024 est soit dépréciée en mai 2026, soit
soumise à une limite de quota différente. OpenAI envoie un événement d'erreur
puis ferme le WebSocket immédiatement après réception du `session.update`.

**Bug secondaire dans le bridge** :
- `logger.info("session configured")` et `logger.info("greeting sent")` s'exécutent
  inconditionnellement après `_ws_send_openai()` — ils loguent "OK" même en cas d'échec
- Le bridge ne lit pas la réponse d'OpenAI (session.created, error) avant d'envoyer
  `session.update` — les événements d'erreur d'OpenAI sont perdus car `_relay_openai_to_client()`
  n'a pas encore démarré

**Indicateur secondaire** : `429 Too Many Requests` sur `chat/completions` (quota OpenAI global)

---

## Périmètre Objectif 008

### Correction 1 — Modèle Realtime (CRITIQUE)

Dans `.env` Cloud Run :
```
OPENAI_REALTIME_MODEL=gpt-4o-realtime-preview
```

(Alias toujours à jour, pas de version figée en 2024)

### Correction 2 — Bridge : lire la réponse initiale d'OpenAI

Après `websockets.connect()`, OpenAI envoie immédiatement un événement `session.created`.
Le bridge doit :
1. Lire le premier message (session.created ou error)
2. Si `type == "error"` → logger le message + fermer proprement + notifier le client
3. Puis envoyer `session.update`
4. Lire la réponse (session.updated ou error) avant de démarrer les relay tasks

### Correction 3 — Logs non trompeurs dans le bridge

`logger.info("session configured")` doit être conditionnel au succès de l'envoi.
Ajouter le motif réel de fermeture OpenAI (code + message) dans les logs.

### Extension — Pull-to-refresh APK (Ludovic)

À cadrer dans l'APK Java (hors périmètre serveur) :
- Swipe vers le bas → reload WebView
- Vider cache WebView si possible
- Renvoyer heartbeat immédiatement
- Afficher "Luna mise à jour" (discret)
- Événements : `apk_manual_refresh_triggered`, `apk_cache_cleared`, `apk_webview_reloaded`
- But : éviter qu'une ancienne version de `index.html` reste coincée dans la WebView

---

## Rôles

### Claude — Lead technique

- Implémenter la correction modèle dans `.env`
- Corriger le bridge : lecture `session.created` + logs conditionnels
- Déployer sur Cloud Run après validation Ludovic
- Vérifier que la voix produit un retour audio (log `response.audio.delta`)

### DeepSeek — Audit `web_voice_bridge.py`

**Branche** : `ds/objectif-008-correction-voix`

- Auditer `_configure_session()`, `_send_greeting()`, `_ws_send_openai()`
- Proposer la correction minimale pour lire `session.created` avant `session.update`
- Vérifier les autres points où OpenAI peut fermer le WS prématurément
- Identifier si le modèle est bien le seul problème ou s'il y a d'autres causes

**Livrable** : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_008.md`

### Kimi — Textes cockpit + lisibilité

**Branche** : `kimi/objectif-008-correction-voix`

- Intégrer les icônes et couleurs proposées dans KIMI_AVIS_007.md dans `fondateur.html`
- Rédiger les textes pour les nouveaux scénarios :
  - OpenAI modèle indisponible
  - Quota OpenAI Realtime épuisé
  - Bridge fermé prématurément (pendant session.update)
- Vérifier que le scénario de succès (voix OK) est bien traité

**Livrable** : `docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_008.md`

### Codex — Cadrage et garde-fous

**Branche** : `codex/objectif-008-correction-voix`

- Rappeler que la validation reste le test réel Ludovic (entendre la voix de Luna)
- Vérifier que le correctif modèle n'affecte pas d'autres routes (`/api/voice/*`)
- Rappel observation Codex-007 : `voice_token_missing` ne peut pas remonter sans JWT
- Préparer la synthèse logique pour Claude

**Livrable** : `docs/AGENTS_COLLABORATION/agents/CODEX_AVIS_008.md`

### Cursor — UI et non-régression

**Branche** : `cursor/objectif-008-correction-voix`

- Intégrer les icônes Kimi (KIMI_AVIS_007.md) dans la chronologie `fondateur.html`
- Vérifier que les labels Kimi validés sont bien dans `_VOICE_EVENT_LABELS` du serveur
- Non-régression : aucun autre bouton, onglet ou asset ne doit être affecté

**Livrable** : `docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_008.md`

### Ludovic — Testeur final

- Après déploiement : ouvrir Luna, appuyer sur le bouton vocal
- Critère de succès : entendre la voix de Luna
- Valider avant tout déploiement

---

## Critères de réussite Objectif 008

- [ ] `OPENAI_REALTIME_MODEL` mis à jour vers `gpt-4o-realtime-preview`
- [ ] Le bridge lit `session.created` avant d'envoyer `session.update`
- [ ] `WARNING: OpenAI WS closed during send` disparaît des logs
- [ ] Les logs affichent `response.audio.delta` ou équivalent (OpenAI répond)
- [ ] `voice_first_audio_chunk_received` et `voice_playback_started` apparaissent dans le cockpit
- [ ] Ludovic entend la voix de Luna sur le téléphone
- [ ] Aucune régression sur le chat, les quotas, les autres routes

---

## Interdictions

- Pas de modification de `OPENAI_API_KEY` sans validation Ludovic
- Pas de refactoring massif du bridge — correctifs minimaux
- Pas de déploiement sans validation Ludovic
- Pas de rebuild APK pour cette phase (serveur uniquement)
- Pas de suppression des logs existants — améliorer, pas supprimer

---

## Validation

- [ ] DeepSeek — `agents/DEEPSEEK_AVIS_008.md`
- [ ] Kimi — `agents/KIMI_AVIS_008.md` (intégration icônes 007 + textes 008)
- [ ] Codex — `agents/CODEX_AVIS_008.md`
- [ ] Cursor — `agents/CURSOR_AVIS_008.md`
- [ ] Claude a implémenté et déployé
- [ ] Ludovic entend la voix de Luna
- [ ] Logs Cloud Run confirment le flux complet (session.created → response.audio.delta)
