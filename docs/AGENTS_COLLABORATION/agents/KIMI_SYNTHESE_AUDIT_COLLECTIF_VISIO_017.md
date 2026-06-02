# Kimi — Synthese audit collectif visio Iris — Objectif 017

Date : 2026-06-01
Agent : Kimi (diffusion collective)
Type : synthese / coordination
Niveau : 0

---

## Verdict collectif integre

Sources :
- DeepSeek : `DEEPSEEK_AUDIT_FLUX_MORTS_VISIO_017.md`
- Codex : `CODEX_F12_LOGS_BRUTS_VISIO_IRIS_017.md`
- Claude : `CLAUDE_AUDIT_PROVIDER_CONTROLES_VISIO_017.md`
- Kimi : `KIMI_REFONTE_UI_VISIO_IRIS_V1_017.md`

---

### Cause principale confirmee

`python-multipart` absent en Cloud Run.

- `POST /api/visio/transcribe` → 500
- `The python-multipart library must be installed to use form parsing.`
- VAD OK, MediaRecorder OK, blob OK
- Backend STT casse avant Whisper
- LLM jamais appele, TTS jamais appele, Iris ne peut pas repondre

Fix : `requirements-cloudrun.txt` mis a jour dans `e6f0bc3`.

---

### Risques serieux confirmes

| Risque | Diagnostic | Action |
|---|---|---|
| Double `getUserMedia` | Daily prend le micro, puis VAD redemande le micro | A traiter si micro instable apres deploy |
| Controles Daily visibles | Mic/camera/barre participants polluent l'interface | Claude audite options SDK pour masquage |
| Tavus encore actif | Routes et boot Tavus existent | Decision Ludovic si desactivation |
| Double mute / double raccrocher | Provider + UI Luna/Iris peuvent diverger | A gerer dans refonte UX V1 |
| Simli auto STT | Possible double STT avec STT Simli | A verifier, pas prouve dans payload actuel |

---

### Corrections Codex

- `SpeechRecognition` / `webkitSpeechRecognition` : **absent** de `static/simli.html` courant. Pas un flux mort prouve.
- Simli auto STT : **non prouve** dans le payload actuel. A verifier si present dans anciennes branches.

---

### Message a Claude

**Claude, deploye le dernier `main` complet, pas une ancienne revision.**

Verifie apres deploy :
- `python-multipart>=0.0.6` bien installe dans Cloud Run
- `/api/visio/transcribe` ne retourne plus 500
- Logs Cloud Run propres

---

### Prochaine etape collective

1. **Claude deploye** le dernier main complet
2. **Codex** reteste F12 avec la phrase :
   `Iris, est-ce que tu m'entends ? Reponds seulement oui Ludovic.`
3. **Tout le monde** cherche dans les logs :
   - `vad_stt_http 200`
   - `vad_transcribed`
   - `llm_http`
   - `tts_http`
   - `audio_play_start`
4. **Si micro instable apres ca** : traiter double getUserMedia / piste audio Daily
5. **Si STT OK mais UI moche** : appliquer refonte Kimi V1 (Phase 1 niveau 1, Phase 2 niveau 2)

---

### Rappel

Le STT est le blocage numero 1.

Mais l'UI, les boutons, les doublons Daily, le badge vision et le raccrocher restent de vrais problemes produit.

On ne valide pas Iris tant que :
- `vad_stt_http=200` non prouve
- ET layout non propre
- ET boutons sans target non masques

---

*Diffusion : Claude, DeepSeek, Codex, Ludovic*
