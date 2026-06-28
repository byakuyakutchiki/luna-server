# Détection d'urgence en conversation vocale Iris

Date : 28 juin 2026 · Branche : `feature/sprint-a-ux`

## Objectif
Pendant une conversation vocale avec Iris, détecter en continu une situation de
détresse / demande d'aide et déclencher le protocole d'alerte des contacts de confiance.

## Architecture (déterministe, côté serveur)
On n'attend PAS que le modèle vocal (`gpt-realtime-mini`) appelle un outil — il en est
incapable de façon fiable. On analyse directement la **transcription de l'utilisateur**.

```
transcript user (voix pure)
  ├─ match_immediate_sos()  (regex FR, instantané)  ──► ALERTE immédiate
  └─ classify_emergency()   (gpt-4o-mini, async)
        ├─ immediate ──► ALERTE immédiate
        ├─ ambiguous ──► Iris demande 1× « je préviens tes proches ? » → si oui ──► ALERTE
        └─ none      ──► conversation normale
```

## Fichiers
- `core/safety/voice_emergency.py` — détection : `match_immediate_sos`, `is_affirmative`,
  `is_negative`, `classify_emergency` (LLM intention, sortie JSON stricte).
- `integrations/openai/web_voice_bridge.py` — orchestration : `_handle_emergency`,
  `_fire_and_reassure`, `_ask_emergency_confirmation`, `_emergency_llm_followup`.
  État : `_pending_emergency`, `_emergency_active`. Messages client `{"type":"emergency","state":...}`.
- `luna_web.py` — `_trigger_voice_emergency(tid, summary, level)` : SMS à tous les contacts
  (réutilise `_tool_alert_contacts` : position + heure + n° urgence) + appels Twilio à tous
  (`_tool_call_contact`). Callbacks câblés dans `ws_iris_voice`.

## Politique (validée Ludo)
- **2 niveaux** : danger clair = alerte immédiate (0 délai, 0 confirmation) ;
  détresse ambiguë = Iris demande UNE fois avant d'alerter.
- **Canaux** : SMS + appels à TOUS les contacts de confiance, avec résumé + position.

## Garde-fous opérationnels (env, sans redéploiement)
- `VOICE_EMERGENCY_ENABLED` (défaut `true`) — coupe toute la détection si `false`.
- `VOICE_EMERGENCY_DRY_RUN` (défaut `false`) — **mode observation** : détecte, journalise,
  Iris rassure, l'UI reçoit l'état d'urgence, MAIS aucun SMS/appel réel. `_test_mode` global
  force aussi le dry-run.

## Rollout
Déployé d'abord avec `VOICE_EMERGENCY_DRY_RUN=true` (observation) pour un utilisateur de test.
Passage en réel : `gcloud run services update luna-beta --region=europe-west1 \
  --update-env-vars=VOICE_EMERGENCY_DRY_RUN=false`.

## Vérifications (dry-run, 28/06/2026)
Test bout-en-bout `/ws/iris-voice` en `LUNA_TEST_MODE=1` :
- « Au secours » → alerte déclenchée immédiate, SMS+appels simulés vers contacts, position incluse, 0 erreur.
- Détresse ambiguë → gérée (Iris demande / déclenche selon classif), confirmé après « oui ».
- Conversation normale → aucun déclenchement.
- Classifieur LLM : **0 faux positif** sur 8 phrases banales (fatigue, ras-le-bol, solitude légère…),
  **5/5 urgences** détectées (chute, douleur thoracique, intrusion, malaise, idées suicidaires).

## Reste à faire
- Suivi de localisation temps réel côté contacts (étape 2 du modus operandi) — à brancher sur l'existant.
- Appliquer le même schéma déterministe aux **rappels** vocaux (fiabilité tool-call `realtime-mini`).
