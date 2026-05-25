# Rapport Cloud Run — Objectif 008 — Test 19:27 CEST

**Date** : 2026-05-25  
**Révision** : `luna-beta-00440-gbz`  
**Test** : Ludovic, téléphone réel, bouton vocal APK Fondateur  
**Résultat** : échec — pas de voix, régression télémétrie visible  

---

## Séquence complète (logs UTC → CEST = +2h)

```
17:27:28.116 UTC  WebSocket /ws/luna-voice [accepted]  ← tentative 1 (Ludovic)
17:27:28.481      WebVoiceBridge started (active: 1)
17:27:30.363      WebVoice: OpenAI Realtime connected
17:27:30.363      ERROR: code=model_not_found
                  "The model `gpt-4o-realtime-preview` does not exist
                   or you do not have access to it."
17:27:30.369      WebVoiceBridge ended (active: 0)
17:27:32.503      WebVoiceBridge cleanup (0 entries)

17:27:56.578 UTC  WebSocket /ws/luna-voice [accepted]  ← tentative 2
17:27:55-57       10 × POST /api/apk/event [200]       ← événements APK reçus
17:27:56.900      WebVoiceBridge started (active: 1)
17:27:57.731      WebVoice: OpenAI Realtime connected
17:27:57.731      ERROR: code=model_not_found
                  "The model `gpt-4o-realtime-preview` does not exist
                   or you do not have access to it."
17:27:57.737      WebVoiceBridge ended (active: 0)
17:27:59.859      WebVoiceBridge cleanup (0 entries)
17:28:00-02       2 × POST /api/apk/event [200]        ← voice_ws_closed + session_ended
```

---

## Réponses aux questions Ludovic

### Événement initial OpenAI reçu ?
**OUI** — la correction B fonctionne. Le bridge lit l'événement initial avant session.update.
Cet événement était un `error` (pas un `session.created`).

### Erreur OpenAI exacte ?
```
code    : model_not_found
message : The model `gpt-4o-realtime-preview` does not exist
          or you do not have access to it.
```

### Modèle réellement utilisé ?
`gpt-4o-realtime-preview` (alias mis en correction A).

### Résultat session.update ?
**Jamais envoyé.** La correction B a détecté l'erreur avant et arrêté proprement.

### Code de fermeture WS côté OpenAI ?
Non loggué — le bridge s'est arrêté proprement avant d'atteindre les relay tasks.

### Pourquoi seulement voice_ws_closed dans le cockpit ?

Les **10 événements APK sont bien arrivés au serveur** (10 × POST [200]).
Mais le cockpit n'en affiche qu'un seul. Cause : régression session_ts.

Explication : la correction B envoie `{"type":"error"}` au client WS.
- Le handler JS d'erreur appelle `stopVoice()`
- `stopVoice()` envoie `voice_session_ended` avec `session_ts = click_timestamp` ✓
- `stopVoice()` remet ensuite `_voiceSessionStartTs = 0`
- Puis le WS se ferme → `onclose` fire → `voice_ws_closed` envoyé avec `session_ts = 0`
- `session_ts = 0` → micro-session orpheline identifiée par son `ts` individuel
- Le cockpit affiche la "dernière session" = cette micro-session = 1 seul événement

À 18:47 (révision 00439, ancien bridge) : le bridge ne send jamais d'`error` au client.
Le WS se ferme côté OpenAI → `onclose` se déclenche avec `_voiceSessionStartTs` encore valide
→ `voice_ws_closed` reçoit le bon `session_ts` → tous les 11 événements dans la même session.

---

## Deux problèmes distincts à corriger

### Problème 1 — Modèle Realtime inaccessible (BLOQUANT voix)

Ni `gpt-4o-realtime-preview-2024-12-17` (session.update → WS fermé, révision 00439)
ni `gpt-4o-realtime-preview` (model_not_found immédiat, révision 00440) ne fonctionnent.

Ce compte OpenAI a visiblement un accès Realtime limité.

Options à valider par Ludovic :
| Modèle | Hypothèse |
|---|---|
| `gpt-4o-realtime-preview-2024-10-01` | Version plus ancienne, peut-être accessible |
| `gpt-4o-mini-realtime-preview` | Tier inférieur, souvent plus accessible |
| Vérifier le quota Realtime OpenAI | Le 429 sur chat/completions suggère une tension de quota |

### Problème 2 — Régression session_ts (BLOQUANT cockpit)

Fix dans `index.html` : `_voiceSessionStartTs = 0` doit être remis à 0 APRÈS
que `voice_ws_closed` est envoyé depuis `onclose`, pas avant.

Solution minimale : dans `onclose`, envoyer `voice_ws_closed` en premier,
PUIS appeler `stopVoice()`.

---

## Ce qui n'est PAS un problème

- Le token JWT fondateur est valide (WS accepté)
- Les 10 événements APK arrivent bien au serveur (REST fonctionnel)
- Le bridge s'arrête proprement (plus de "session configured" trompeur)
- La détection d'erreur OpenAI fonctionne (correction B opérationnelle)

---

## Décisions à valider par Ludovic

1. Quel modèle Realtime tester en priorité ?
2. Corriger la régression session_ts dans `index.html` en même temps ou séparément ?
3. Investiguer le quota OpenAI Realtime (vérifier le dashboard OpenAI) ?

Pas de déploiement sans validation Ludovic.
