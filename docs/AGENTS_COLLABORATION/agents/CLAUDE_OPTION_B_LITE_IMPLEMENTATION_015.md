# Claude — Implémentation Option B-lite — Objectif 015

Agent : Claude  
Date : 2026-05-31  
Statut : code livré + déployé  

---

## Définition conversation fluide — Codex/Ludovic

| Seuil | Valeur | Verdict |
|---|---|---|
| Excellent | < 1 500 ms | Idéal |
| Acceptable V1 | 1 500 – 3 000 ms | OK produit |
| Limite tolérable | 3 000 – 4 000 ms | Acceptable si réponse utile |
| Échec produit | > 4 000 ms régulièrement | KO |
| Échec total | > 6 000 ms | Bug perçu |

Règle produit : si "tu m'entends ?" prend > 4s → visio non exploitable.  
Règle vocale : 1 à 2 phrases max pour une question simple.

---

## Architecture Option B-lite

```
Micro Ludovic
  → Web Speech API (fr-FR, continu)
    → speech_start loggué
      → [_irisReplying = false ? sinon ignoré]
        → POST /api/visio/chat  ← LLM GPT-4o-mini, max 150 tokens
          → llm_done (latence loggée)
            → POST /api/visio/tts  ← proxy ElevenLabs côté serveur
              → tts_done (latence loggée)
                → <Audio> play
                  → audio_play_start / audio_play_end
                    → total_latency_ms loggué
                      → _irisReplying = false (micro réactivé)
```

---

## Logs de latence (F12 → Console)

Chaque tour produit ces logs dans cet ordre :

```
[INFO][simli] speech_start      = "tu m'entends ?"
[INFO][simli] speech_end        = "tu m'entends ?"
[INFO][simli] stt_done          = "tu m'entends ?"
[INFO][simli] llm_start
[INFO][simli] llm_done          = 823ms
[INFO][simli] tts_start         = "Oui, je vous entends parfaitement..."
[INFO][simli] tts_done          = 612ms
[INFO][simli] audio_play_start
[INFO][simli] audio_play_end
[INFO][simli] total_latency_ms  = 1847ms
```

Latence attendue par composant :
- STT Web Speech : ~0ms (résultat final après fin de phrase)
- LLM GPT-4o-mini (max 150 tokens) : ~600–900ms
- ElevenLabs TTS (Camille, 1-2 phrases) : ~500–800ms
- **Total estimé : 1 100 – 1 700ms** → Excellent à Acceptable V1

---

## Anti-boucle écho

Variable `_irisReplying` :
- `true` dès que `_irisReply()` démarre
- Tout résultat `SpeechRecognition` pendant `_irisReplying = true` est ignoré (`speech_ignored_iris_busy` loggué)
- `false` dès que l'audio a fini de jouer (`onended`)
- `false` aussi sur toute erreur (LLM, TTS, audio) → ne jamais bloquer le micro

---

## Sécurité clé ElevenLabs

- Clé JAMAIS dans le frontend
- `/api/visio/tts` lit `ELEVENLABS_API_KEY` depuis l'environnement serveur
- Le frontend appelle `authFetch('/api/visio/tts', ...)` avec le token JWT Luna
- La clé n'apparaît ni dans les logs, ni dans le réseau, ni dans le HTML

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `luna_web.py` | +`POST /api/visio/chat` (LLM court, max 150 tokens) |
| `luna_web.py` | +`POST /api/visio/tts` (proxy ElevenLabs sécurisé) |
| `static/simli.html` | Pipeline `_irisReply()` complet avec 9 logs latence |
| `static/simli.html` | `_irisReplying` anti-boucle écho |
| `.env` + Cloud Run | `ELEVENLABS_VOICE_ID` → Camille `Z9ZHGvFZ90R0h0x1prsJ` |

---

## Voix

- Alice `6BlZrFdruL4hpXFHmHUC` : abandonnée (accent anglais, "Riff")
- **Camille `Z9ZHGvFZ90R0h0x1prsJ`** : validée (test curl HTTP 200, 37 ko audio)
- Validée avec la clé `sk_7745...` (permissions TTS confirmées)

---

## Test terrain demandé à Ludovic (< 45s)

1. Lancer la visio
2. Attendre la salutation
3. Dire **"tu m'entends ?"**
4. Attendre la réponse
5. Regarder la console F12 → chercher `total_latency_ms`
6. Critère : réponse française en < 4s, 1-2 phrases

---

## Ce que Simli fait encore

- Affiche l'avatar visuellement
- Joue le `firstMessage` (salutation initiale)
- L'avatar ne lip-synce pas sur les réponses Iris (V1 acceptable)
- La room Daily est maintenue pour l'avatar

---

## Ce qui reste à faire (V2)

- Lip-sync Simli sur les réponses générées (Option B-proper, SDK Simli)
- Vision caméra (camera track hors iframe Daily)
- Voix finale FR (validation Kimi en cours)
