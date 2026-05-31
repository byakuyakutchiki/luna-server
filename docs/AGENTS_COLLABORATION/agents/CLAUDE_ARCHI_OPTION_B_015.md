# Claude — Analyse logs + proposition Option B — Objectif 015

Agent : Claude  
Date : 2026-05-31  
Référence : `CODEX_LOG_ANALYSIS_VISIO_015.md`

---

## 1. Diagnostic définitif Option A

Les logs confirment ce que Codex a conclu :

| Étage | Preuve terrain | Verdict |
|---|---|---|
| Room Simli démarre | `createVisioCall_ok` | ✅ |
| Micro local publié | `probe_local_audio playable` | ✅ |
| Bot rejoint | `bot_joined` | ✅ |
| Bot publie audio | `probe_bot_audio playable` | ✅ |
| Browser capte Ludovic | `speech_captured est-ce que tu m'entends` | ✅ |
| Simli STT natif | `stt_user_utterance` jamais apparu | ❌ |
| `conversation.echo` → réponse | `app_msg_ {"type":""}` — aucune réponse | ❌ |
| Latence mesurée | `latency_ms` jamais apparu | ❌ |

**Conclusion** : Simli `auto/start/configurable` joue le `firstMessage` (TTS fonctionne) mais son STT natif ne traite pas l'audio Daily.js iframe dans cette configuration. `conversation.echo` ne déclenche pas de réponse conversationnelle — Simli le reçoit et ne fait rien.

Option A ne peut pas assurer la boucle STT → LLM → réponse. Elle reste utilisable comme **avatar + TTS first-message uniquement**.

---

## 2. Ce que Simli expose réellement

### Canal text → réponse

`conversation.echo` avec `modality: "text"` : **ne déclenche pas de réponse LLM** (prouvé par les logs).  
`conversation.echo` avec `modality: "audio"` : non testé, pourrait fonctionner différemment mais non documenté.

### Canal audio → STT → LLM

Simli `auto/start/configurable` devrait en théorie écouter la piste audio Daily du participant utilisateur. Mais il ne le fait pas dans notre configuration. Causes possibles non isolées : endpoint en cours de dépréciation, paramètre manquant, quota STT, bug côté Simli.

**Il n'existe pas de canal text→réponse fiable exposé par Simli auto.**

---

## 3. Ce qui fonctionne déjà dans la stack Luna

| Composant | Endpoint/outil | État |
|---|---|---|
| STT navigateur | `Web Speech API` | ✅ capte Ludovic (logs prouvés) |
| LLM | `GET /api/chat` (Luna backend) | ✅ GPT-4o-mini, production |
| TTS | ElevenLabs `v1/text-to-speech` | ✅ validé (test curl 200) |
| Avatar Simli | Bot dans la room Daily | ✅ présent, audio publié |
| Auth + profil | `luna_token` + `authFetch` | ✅ en place dans simli.html |

**Le pipeline complet existe déjà en pièces détachées. Il suffit de les brancher.**

---

## 4. Option B-lite — Turn-based avec stack Luna (1–2 jours)

### Architecture

```
Micro Ludovic
  → Web Speech API (déjà dans simli.html)
    → texte capturé
      → [Ludovic appuie sur un bouton ou silence détecté]
        → POST /api/chat  (Luna backend, GPT-4o-mini)
          → texte réponse Iris
            → POST ElevenLabs TTS (depuis frontend ou backend)
              → audio MP3
                → <audio> element joue directement
                  → Simli avatar reste visible (avatar statique ou lip-sync si possible)
```

### Avantages

- **Aucun changement backend** — `/api/chat` existe et fonctionne
- **Aucune nouvelle infrastructure** — ElevenLabs déjà validé
- **Conversation prouvable** — chaque étage loggué
- **Délai** : 1–2 jours de code frontend uniquement
- **Risque** : très faible — tous les composants sont testés

### Inconvénients

- **Lip-sync avatar** : Simli ne lip-synce pas sur l'audio généré par nous (le bot Simli est dans la room mais ne reçoit pas notre TTS)
- **Latence** : STT Web Speech (~300ms) + LLM GPT-4o-mini (~800ms) + ElevenLabs TTS (~600ms) = ~1.7s total — acceptable
- **Android WebView** : Web Speech API non disponible sur certains WebView — fallback bouton texte nécessaire
- **Tour par tour** : pas de vraie simultanéité (mais acceptable pour V1)

### Implémentation côté simli.html (sans déploiement new feature)

```javascript
// Après speech_captured, au lieu de _localSttBridgeEnabled :
async function _sendToLunaChat(userText) {
  rLog('info', 'simli', 'luna_chat_send', userText.substring(0, 60));
  var resp = await authFetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: userText, session_id: currentConvId })
  });
  var data = await resp.json();
  var replyText = data.response || data.message || '';
  rLog('info', 'simli', 'luna_chat_reply', replyText.substring(0, 60));
  await _playElevenLabsTTS(replyText);
}

async function _playElevenLabsTTS(text) {
  // Appel ElevenLabs depuis le frontend via un proxy backend
  // pour ne pas exposer la clé côté client
  var resp = await authFetch('/api/visio/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: text })
  });
  var blob = await resp.blob();
  var url = URL.createObjectURL(blob);
  var audio = new Audio(url);
  audio.play();
}
```

### Endpoint backend à créer : `POST /api/visio/tts`

```python
@app.post("/api/visio/tts")
async def visio_tts(request: Request):
    """Proxy TTS ElevenLabs pour la visio — évite d'exposer la clé côté client."""
    data = await request.json()
    text = data.get("text", "")[:500]
    key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "6BlZrFdruL4hpXFHmHUC")
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"}
        )
    return Response(content=resp.content, media_type="audio/mpeg")
```

**Niveau** : 2 — validation Ludovic requise avant déploiement.

---

## 5. Option B-proper — Simli SDK WebRTC (3–5 jours)

Utiliser `@simli-ai/simli-client` pour contrôler directement le pipeline audio Simli :
- Envoyer les frames PCM du micro à Simli
- Simli fait STT → LLM (notre customLLMConfig) → TTS → lip-sync avatar
- Logs complets via callbacks SDK

**Avantage** : lip-sync réel, pipeline temps réel, voix dans Simli  
**Inconvénient** : refonte partielle du frontend, 3–5 jours, validation architecture  
**Décision Ludovic requise** avant d'entreprendre

---

## 6. Cause de `vision_no_track`

Le code de vision (`_getLocalVideoTrack`) accède à `dailyCall.participants().local.tracks.video`. Dans Daily.js iframe mode, la piste vidéo locale existe dans l'iframe — mais le code parent qui fait `_getLocalVideoTrack()` tourne dans le contexte parent, pas dans l'iframe. Il n'a pas accès direct au track de la caméra de l'utilisateur.

**Fix vision** : capturer la caméra dans le contexte parent AVANT de rejoindre Daily, via `navigator.mediaDevices.getUserMedia({video:true})` et passer le stream au canvas de vision directement — sans passer par Daily.

Le pretest micro+camera le fait déjà partiellement (`_visionVideoEl.srcObject`) — mais la connexion vers Daily coupe ce flux. À réétudier après que le STT soit résolu.

---

## 7. Recommandation pour la prochaine décision Ludovic

| Question | Option |
|---|---|
| Veux-tu une conversation prouvée rapidement (1–2 jours) même sans lip-sync parfait ? | **Option B-lite** |
| Veux-tu le lip-sync réel et acceptes 3–5 jours de refonte ? | **Option B-proper** |
| Veux-tu d'abord choisir la voix FR native avant de tout recoder ? | Tester ElevenLabs voix candidates + B-lite ensuite |

**Ma recommandation** : Option B-lite d'abord. Elle prouve la boucle conversationnelle en 2 jours avec zéro risque. Si ça marche, Option B-proper pour le lip-sync peut suivre proprement.

---

## 8. Ce que je ne ferai pas sans validation

- Coder Option B-lite sans feu vert Ludovic
- Déployer le proxy TTS `/api/visio/tts` sans validation
- Supprimer la session Simli (l'avatar reste utile même statique)
- Changer la voix ElevenLabs sans test Kimi
