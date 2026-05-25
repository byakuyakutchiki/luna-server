# Objectif 009 — Stabilité voix Luna (coupures spontanées)

**Statut** : ✅ VALIDÉ — voix stable sur téléphone réel Ludovic (2026-05-25)  
**Priorité** : haute  
**Lead** : Claude  
**Date ouverture** : 2026-05-25  
**Dépendance** : Objectif 008 validé (voix Luna entendue — gpt-realtime-mini)

---

## Décision Ludovic — Protocole de correction (2026-05-25)

1. **Ne pas corriger encore** — test réel d'abord
2. Ludovic fait un test voix sur téléphone et note l'heure exacte
3. Claude lit les logs Cloud Run autour de cette heure
4. **Si logs confirment** `input_audio_buffer.speech_started` → `response.cancel` :
   → valider **Option A** : `threshold` VAD `0.5` → `0.8`
5. Si Option A ne suffit pas → envisager **Option C** : `vad_eagerness="low"` transmis à `session.update`
6. **Option B** (pause micro pendant playback) : seulement en dernier recours

---

## Constat

La voix fonctionne avec `gpt-realtime-mini` (révision `luna-beta-00442-7gg`).
Mais Luna s'arrête parfois de parler seule / coupe sa réponse en cours de génération.

---

## But

Identifier pourquoi la session vocale se coupe prématurément.
Corriger uniquement la cause minimale.
Valider par test téléphone réel Ludovic.

---

## Pistes techniques identifiées par Claude

### Piste 1 — VAD barge-in (PROBABLE PRINCIPALE)

Le bridge configure `server_vad` avec :
```python
"threshold": 0.5,
"silence_duration_ms": 500,
"create_response": True,
```

Quand Luna parle via le haut-parleur, le micro reste actif et capte :
- la voix de Luna en retour (écho acoustique)
- le bruit ambiant

→ OpenAI VAD détecte "user speech started" → envoie `input_audio_buffer.speech_started`
→ bridge répond `response.cancel` → Luna s'arrête

Ce comportement est intentionnel pour le "barge-in" (interrompre Luna).
Mais sur téléphone sans annulation d'écho, il se déclenche faussement.

**Bug associé** : `vad_eagerness: "low"` est accepté en paramètre du bridge mais
n'est jamais transmis à `session.update` — le paramètre est stocké mais ignoré.

### Piste 2 — Timeout client 20s sans premier audio

`onopen` lance un timer de 20s. S'il expire sans `_voiceFirstAudioReceived`, un
événement `voice_no_audio_after_timeout` est envoyé (telemetrie uniquement, ne coupe pas).
Pas la cause des coupures mid-response.

### Piste 3 — Idle client 300s

`_client_keepalive` coupe la session après 300s d'inactivité. Pas la cause
pour des coupures en quelques secondes.

---

## Rôles

### Ludovic — Testeur

- Faire un test réel sur téléphone, noter l'heure exacte
- Observer : Luna coupe pendant qu'elle parle, avant de parler, ou après une phrase ?
- Y a-t-il du bruit ambiant ou silence dans la pièce ?
- Le bouton raccrocher s'active-t-il seul ?
- Valider si la correction améliore réellement la stabilité

### Claude — Lead technique serveur

- Lire les logs Cloud Run au moment exact du test
- Vérifier si `input_audio_buffer.speech_started` apparaît avant la coupure
- Vérifier le close code WebSocket
- Vérifier la présence de `response.cancel` dans les logs
- Proposer correction minimale (seuil VAD, pause mic pendant playback, ou autre)
- Pas de déploiement sans validation Ludovic

### DeepSeek — Diagnostic temps réel APK

- Vérifier les événements APK liés à la coupure :
  `voice_first_audio_chunk_received`, `voice_playback_started`,
  `voice_ws_closed`, `voice_session_ended`, `voice_no_audio_after_timeout`
- Proposer seuils incident "voice_cut_mid_response"
- Définir ce que DeepSeek doit recevoir si la voix coupe
- Ne pas modifier prod

**Livrable** : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_009.md`

### Kimi — Textes cockpit

Rédiger les textes :
- "Luna a commencé à parler puis s'est arrêtée"
- "La session a été fermée pendant la réponse"
- "Le serveur a coupé avant la fin"
- "OpenAI a arrêté la génération"
- "Le téléphone n'a pas joué toute la réponse"
- Formulation claire, non culpabilisante

**Livrable** : `docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_009.md`

### Cursor — UI mobile

- Vérifier si l'utilisateur voit encore un état "Luna parle…" quand l'audio coupe
- Vérifier que le bouton raccrocher / état vocal ne masque pas une erreur
- Vérifier affichage cockpit chronologie sur mobile

**Livrable** : `docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_009.md`

### Codex — Coordination et garde-fous

- Séparer stabilité voix de DeepSeek temps réel et des bugs UI
- Vérifier que les décisions sont tracées
- Empêcher un refactor large du vocal
- Préparer la synthèse pour validation Ludovic

**Livrable** : `docs/AGENTS_COLLABORATION/agents/CODEX_AVIS_009.md`

---

## Critères de réussite

- [ ] Une session vocale dure assez longtemps pour une réponse complète
- [ ] Si la voix coupe, le cockpit indique où :
  client playback / WebSocket / serveur bridge / OpenAI Realtime / VAD / timeout
- [ ] Logs Cloud Run confirment l'absence de `response.cancel` intempestif
- [ ] Correction minimale validée par test téléphone Ludovic

---

## Interdictions

- Pas de refactor complet du bridge vocal
- Pas de modification APK
- Pas de déploiement sans validation Ludovic
- Pas de désactivation totale du VAD sans analyse des conséquences
