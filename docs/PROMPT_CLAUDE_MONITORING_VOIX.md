# Prompt Claude — Monitoring Objectif Voix / Appel Vocal IA

Contexte : Services, Documents, Formulaires, Cartes et Amis ont déjà un premier monitoring riche dans `/api/admin/objectives`. Ne les refais pas sauf bug explicite.

Repo :

https://github.com/byakuyakutchiki/luna-server

Source de vérité :

- `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Section `## 12. Voix — Appel Vocal IA`
- Méthode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`

## Vision produit

Voix doit permettre à l'utilisateur de parler naturellement à Luna.

Deux usages sont à distinguer :

1. **Voix directe navigateur / APK**
   - WebSocket `/ws/luna-voice` ;
   - OpenAI Realtime ;
   - réponse vocale naturelle ;
   - contexte utilisateur autorisé ;
   - outils vocaux disponibles avec garde-fous ;
   - transcription sauvegardée.

2. **Appel téléphonique assisté**
   - Twilio Voice ;
   - `/api/voice-call` ;
   - `/api/voice-call/media-stream` ;
   - OpenAI RealtimeBridge ;
   - rapport et compte-rendu après appel ;
   - coût/forfait voix suivi.

L'objectif n'est pas atteint si OpenAI est seulement configuré. Il faut vérifier le parcours vocal exploitable.

## Objectif utilisateur

L'utilisateur doit pouvoir parler à Luna en temps réel, obtenir une réponse vocale, utiliser les outils autorisés, puis retrouver une trace utile de l'échange.

```text
OpenAI Realtime → WebSocket voix → budget/quota → contexte → outils autorisés → transcription → mémoire/rapport → cleanup
```

## Checks techniques suggérés

Ajouter ou compléter un check `_check_objective_voix()` dans `luna_web.py`, puis l'exposer dans `GET /api/admin/objectives` sous la clé :

```json
{
  "voix": {
    "status": "warning",
    "goal": "...",
    "checks": [],
    "subservices": {},
    "metrics": {},
    "auto_heal": []
  }
}
```

Vérifier au minimum :

- `openai_client` disponible ;
- variable `OPENAI_API_KEY` présente ;
- `OPENAI_VOICE_NAME` ou fallback `coral` ;
- WebSocket `/ws/luna-voice` présent ;
- route `/api/voice-call` présente ;
- route `/api/voice-call/media-stream` présente ;
- route `/api/voice-call/twiml` présente ;
- `integrations.openai.web_voice_bridge.WebVoiceBridge` importable ;
- `integrations.openai.realtime_bridge.RealtimeBridge` importable ;
- `build_voice_context` importable ;
- `_build_realtime_context` disponible ;
- `_save_voice_transcript` disponible ;
- `_openai_realtime_semaphore` disponible ;
- tracker coût voix disponible si Cortex/cost_tracker présent ;
- `voice_client` configuré ou warning si Twilio optionnel ;
- budget/quota vérifié avant démarrage.

## Sous-services attendus

| Sous-service | Ce qui doit être vérifié |
|---|---|
| openai_realtime | client + clé + bridge |
| browser_voice_ws | `/ws/luna-voice` |
| twilio_voice | Twilio configuré ou optionnel |
| media_stream | `/api/voice-call/media-stream` |
| voice_context | contexte vocal construit |
| voice_tools | outils vocaux disponibles avec garde-fous |
| budget_quota | vérification forfait/budget |
| transcription | sauvegarde mémoire |
| call_report | compte-rendu appel générable |
| cost_tracking | minutes voix suivies |
| cleanup | sessions orphelines nettoyées |
| fallback | repli texte/chat si voix KO |

## Checks fonctionnels suggérés

Le monitoring ne doit pas ouvrir un vrai appel téléphonique et ne doit pas connecter un vrai media stream externe.

Il doit prouver structurellement :

1. Les routes et WebSockets voix existent.
2. OpenAI Realtime est disponible.
3. Les bridges Realtime/WebVoice sont importables.
4. Le contexte vocal peut être construit.
5. Le budget/quota est vérifié avant usage.
6. La transcription est sauvegardable en cas de fin normale ou coupure.
7. Les appels Twilio sont `warning` si optionnels/non configurés, pas `critical` pour la voix directe.
8. Aucun outil vocal engageant ne peut agir sans confirmation.

## Statuts attendus

```text
ok
```

Voix directe prête, transcription/mémoire disponibles, quota vérifiable, Twilio prêt ou optionnel selon plan.

```text
warning
```

Twilio absent mais voix directe OK, quota bas, aucun appel actif, ou transcription non testée réellement.

```text
degraded
```

Voix directe indisponible mais fallback texte possible, ou Twilio disponible sans rapport/track coût.

```text
critical
```

OpenAI/Realtime absent, WebSocket voix absent, quota bloquant non géré, ou transcription impossible.

## Auto-heal attendu

| Problème | Auto-heal / réponse attendue |
|---|---|
| OpenAI Realtime KO | fallback chat texte |
| WebSocket coupé | reconnexion x3 |
| micro refusé | message clair permission micro |
| quota bas | alerte + blocage propre |
| Twilio absent | désactiver appels téléphone, garder voix directe |
| transcription échoue | retry sauvegarde mémoire |
| session orpheline | cleanup TTL |

## Limites à respecter

- Ne jamais passer un vrai appel pendant le monitoring.
- Ne jamais démarrer un vrai stream externe pendant le monitoring.
- Ne jamais consommer du quota sans confirmation utilisateur.
- Ne jamais déclencher SMS/appel/DM via outil vocal sans garde-fou.
- Ne pas toucher à `static/index.html` dans ce chantier.

## Sortie souhaitée

Merci de produire :

1. Le code du check monitoring Voix.
2. Les champs JSON retournés par `/api/admin/objectives`.
3. Les statuts `ok/warning/degraded/critical`.
4. Les auto-heal proposés.
5. Un résumé des fichiers modifiés.
6. Comment tester sans vrai appel, sans micro réel obligatoire, et sans consommer de quota inutile.

