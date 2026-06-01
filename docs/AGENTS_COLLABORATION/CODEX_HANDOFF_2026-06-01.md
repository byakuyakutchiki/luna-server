# Handoff Codex — 2026-06-01

Rédigé par : Claude  
Pour : Codex, Kimi, DeepSeek  

---

## État du projet au 2026-06-01

### Déployé en production

- **Cloud Run** : `luna-beta-00469-22g`
- **URL** : `https://luna-beta-674304336025.europe-west1.run.app`
- **Commit** : `6033091` — fix STT + vision caméra

### Fixes livrés (objectif 016)

| Bug | Cause | Fix |
|---|---|---|
| Iris n'entend pas | `startAudioOff: false` → Daily prenait le micro | `startAudioOff: true` |
| Caméra `vision_no_track` | Daily iframe inaccessible depuis parent | Stream conservé depuis pretest → `_visionCameraStream` |

---

## Objectif 017 — Banc de test téléphone

### Ce que Claude a fait

- Connecté ADB : téléphone `c7750037` **device** ✅
- Capturé preuves dans : `docs/AGENTS_COLLABORATION/phone_tests/2026-06-01_18-11/`
- Créé script réutilisable : `tools/agents/phone_snapshot.sh`

### Ce que Codex doit faire

1. Lire les captures pushées sur GitHub :
   - `phone_tests/2026-06-01_18-11/screen.png` — état écran téléphone
   - `phone_tests/2026-06-01_18-11/app_info.txt` — version APK + device
   - `phone_tests/2026-06-01_18-11/logcat_luna.txt` — logs Luna/WebView

2. Tester la visio sur le téléphone réel :
   - Ouvrir Luna → Visio
   - Passer le pretest
   - Dire "tu m'entends ?"
   - Noter si `speech_start` + `total_latency_ms` apparaissent en F12

3. Reporter dans : `docs/AGENTS_COLLABORATION/agents/CODEX_TERRAIN_017.md`

### Ce que Kimi doit faire

- Analyser `screen.png` : qualité UI, lisibilité, ergonomie
- Reporter dans : `docs/AGENTS_COLLABORATION/agents/KIMI_UX_017.md`

### Ce que DeepSeek doit faire

- Auditer les risques du fix `_visionCameraStream` (libération mémoire, race conditions)
- Lire : `docs/AGENTS_COLLABORATION/agents/CLAUDE_FIX_STT_VISION_016.md`
- Reporter dans : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_017.md`

---

## Infos téléphone (pour contexte)

| Champ | Valeur |
|---|---|
| Appareil | Xiaomi 24115RA8EG |
| Android | 16 (SDK 36) |
| Luna APK | v2.8 (versionCode 19) |
| Installé | 2026-05-25 |
| WebView | 148.0.7778.178 |
| Chrome | 148.0.7778.215 |

---

## Règles de travail inter-IA

- Si ce n'est pas sur GitHub, ce n'est pas livré
- Claude ne déploie pas sans validation Ludovic
- Codex coordonne le terrain
- Kimi juge le rendu UX
- DeepSeek audite les risques
