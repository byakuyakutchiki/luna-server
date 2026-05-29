# Recommandations Voix + Avatar Luna — Décision niveau 2

> Agent : Kimi  
> Date : 2026-05-28  
> Niveau : 2 (validation Ludovic requise)  
> Contexte : Objectif 013 — Luna est "silencieuse" / voix masculine / avatar générique

---

## 1. Diagnostic voix actuelle

Le code backend (`luna_web.py` l.6888-6895) configure le TTS Simli ainsi :

```python
if cartesia_key:
    payload["ttsProvider"] = "Cartesia"
    payload["voiceId"] = os.getenv("CARTESIA_VOICE_ID", "65b25c5d-ff07-4687-a04c-da2f43ef6fa9")
elif elevenlabs_key:
    payload["ttsProvider"] = "ElevenLabs"
    payload["voiceId"] = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
```

- **ElevenLabs ID par défaut** : `21m00Tcm4TlvDq8ikWAM` = **Rachel** (voix féminine anglaise, pas française)
- **Cartesia ID par défaut** : `65b25c5d-ff07-4687-a04c-da2f43ef6fa9` — voix inconnue, potentiellement masculine
- **Si aucune clé TTS n'est configurée** : Simli utilise son TTS natif par défaut, signalé comme **masculin** par le test terrain de Ludovic

**Hypothèse** : Aucune clé `CARTESIA_API_KEY` ou `ELEVENLABS_API_KEY` n'est configurée sur Cloud Run, donc Simli utilise sa voix native masculine.

---

## 2. Options voix féminine française

### Option A — ElevenLabs (recommandée pour la qualité française)

ElevenLabs a plusieurs voix féminines françaises natives dans sa galerie publique :

| Voice ID | Nom | Description | Usage |
|----------|-----|-------------|-------|
| `Z9ZHGvFZ90R0h0x1prsJ` | **Camille** | "Warm, expressive, unmistakably French. Ideal for storytelling, ads." | Luna chaleureuse |
| `hFgOzpmS0CMtL2to8sAl` | **Camille Martin** | "Calm and deep. Ideal for corporate, audiobooks." | Luna mature/soignée |
| `5OnMHwgTFgvPVwE8jP6B` | **Anaïs** | "Middle aged French. Warm and clear. Podcast, e-learning, news." | Luna professionnelle |
| `sEk5ftjVl91hHjtOlmK1` | **Lise** | "Calm storyteller. Clear, smooth, soothing French." | Luna douce/méditative |
| `CKfuQaJKfvUG2Wtrda3Y` | **Lison** | "Soft French accent, warm, intimate, naturally seductive." | Luna séductrice |
| `FvmvwvObRqIHojkEGh5N` | **Adina** | "Young professional French woman. Social media." | Luna jeune/dynamique |

**Recommandation Kimi** : `Z9ZHGvFZ90R0h0x1prsJ` (Camille) ou `hFgOzpmS0CMtL2to8sAl` (Camille Martin). Les deux sont chaleureuses, françaises, et adaptées à un compagnon IA.

**Prérequis** : Configurer `ELEVENLABS_API_KEY` et `ELEVENLABS_VOICE_ID` sur Cloud Run.

### Option B — Cartesia (recommandée pour la latence)

Cartesia est spécialisée en TTS ultra-low-latency (<100ms), idéal pour conversation temps réel.

Voix françaises listées sur leur site (IDs exacts à vérifier dans le dashboard Cartesia) :
- **Calm French Woman** — douce, apaisante
- **Helpful French Lady** — joyeuse, amicale
- **French Narrator Lady** — veloutée, neutre

**Recommandation Kimi** : "Helpful French Lady" ou "Calm French Woman" selon le ton souhaité pour Luna.

**Prérequis** : Configurer `CARTESIA_API_KEY` et `CARTESIA_VOICE_ID` sur Cloud Run.

### Option C — Voix Simli native (pas recommandée)

Simli a une galerie d'avatars avec des voix associées. Mais le contrôle est limité et la qualité TTS dépend de Simli.

---

## 3. Décision à prendre

| Question | Choix |
|----------|-------|
| **Provider TTS** | ElevenLabs (qualité) vs Cartesia (latence) |
| **Voice ID** | Voir table ci-dessus |
| **Test avant prod** | Oui — session Simli 30s pour valider le rendu |

---

## 4. Configuration Cloud Run (procédure)

Une fois le choix fait, exécuter sur VM :

```bash
gcloud run services update luna-beta \
  --set-env-vars "ELEVENLABS_VOICE_ID=Z9ZHGvFZ90R0h0x1prsJ" \
  --region europe-west1 \
  --project crypto-parser-475411-k4
```

Ou pour Cartesia :
```bash
gcloud run services update luna-beta \
  --set-env-vars "CARTESIA_VOICE_ID=<id_choisi>" \
  --region europe-west1 \
  --project crypto-parser-475411-k4
```

**Note** : Vérifier que la clé API correspondante (`ELEVENLABS_API_KEY` ou `CARTESIA_API_KEY`) est déjà configurée sur Cloud Run. Si non, l'ajouter aussi.

---

## 5. Avatar Luna

### Option A — Choisir un avatar féminin existant dans la galerie Simli
- Accéder à https://www.simli.com/ → Dashboard → Faces
- Filtrer "Female"
- Noter le `faceId` correspondant

### Option B — Créer un avatar personnalisé Luna
- Utiliser les photos de référence centralisées par Codex dans `docs/assets/luna_avatar_sources/`
- Simli permet d'uploader des photos pour générer un avatar personnalisé (coût potentiel)
- Ou utiliser un service externe (HeyGen, D-ID) puis importer dans Simli

### Option C — Garder l'avatar actuel (temporaire)
- Pas de changement visuel immédiat
- Focus sur la voix d'abord

**Recommandation Kimi** : Option A (galerie Simli) pour un résultat rapide, puis Option B quand le temps le permet.

---

## 6. Checklist mise en place

- [ ] Ludovic choisit provider TTS (ElevenLabs / Cartesia)
- [ ] Ludovic choisit Voice ID (test audio si possible)
- [ ] Ludovic choisit avatar (faceId Simli)
- [ ] Kimi configure les env vars sur Cloud Run
- [ ] Kimi déploie
- [ ] Test terrain 30s visio pour valider voix + avatar

---

*Document préparé pour décision Ludovic — Objectif 013.*
