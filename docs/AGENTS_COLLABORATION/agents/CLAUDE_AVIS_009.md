# Claude — Avis Objectif 009

**Date** : 2026-05-25  
**Objectif** : Stabilité voix — coupures spontanées de Luna  
**Statut** : diagnostic préliminaire — en attente test téléphone Ludovic

---

## Suspect principal : VAD barge-in sur écho acoustique

### Ce que j'ai vu dans le code

Dans `web_voice_bridge.py`, `_configure_session()` (ligne 373) :
```python
"turn_detection": {
    "type": "server_vad",
    "threshold": 0.5,
    "silence_duration_ms": 500,
    "create_response": True,
}
```

Dans `_relay_openai_to_client()` (ligne 474) :
```python
elif event_type == "input_audio_buffer.speech_started":
    await self._ws_send_openai({"type": "response.cancel"}, ...)
    await self._ws_send_client({"type": "interrupt"})
```

### Scénario de coupure

1. Luna génère de l'audio (TTS) → le haut-parleur du téléphone joue la voix
2. Le micro reste actif (AudioWorklet envoie des chunks en continu)
3. Le micro capte l'écho de la voix de Luna (ou bruit ambiant)
4. OpenAI VAD détecte ce son → `input_audio_buffer.speech_started`
5. Le bridge envoie `response.cancel` → **Luna s'arrête**
6. L'APK reçoit `{"type": "interrupt"}` → playback coupé

Sur téléphone Android sans annulation d'écho hardware, ce cycle se déclenche
facilement, surtout avec haut-parleur (vs écouteurs).

### Bug secondaire : vad_eagerness ignoré

`WebVoiceBridge.__init__` accepte `vad_eagerness="low"` (ligne 58) et le stocke.
Mais `_configure_session()` ne l'utilise jamais dans `session.update`.
Le paramètre est mort. OpenAI utilise donc sa valeur par défaut (probablement "auto").

---

## Ce que je veux vérifier dans les logs du test

Après le test téléphone de Ludovic (heure exacte nécessaire), je cherche :

1. `input_audio_buffer.speech_started` → confirme le barge-in VAD
2. `response.cancel` → confirme que le bridge a bien interrompu
3. `response_cancel_not_active` → indique que ça a cancel une réponse déjà finie
4. `WebVoice: user speaking — interrupt` dans les logs DEBUG
5. Durée entre `response.audio.delta` (premier chunk audio) et la coupure

---

## Propositions de correction (une seule à la fois)

### Option A — Augmenter le seuil VAD (MINIMALE, RISQUE FAIBLE)

Changer `threshold: 0.5` → `threshold: 0.8` dans `_configure_session()`.
Un seuil plus élevé = VAD moins sensible = moins de faux barge-ins.

Risque : l'utilisateur doit parler plus fort pour interrompre Luna.

### Option B — Pause du micro pendant le playback (PLUS ROBUSTE)

Dans `_relay_client_to_openai()`, ne pas relayer les chunks audio pendant que
Luna parle (détecter via flag `_luna_speaking` positionné sur `response.audio.delta`
et remis à 0 sur `response.audio.done`).

Risque moyen : si le flag n'est pas bien réinitialisé, le micro ne reprend pas.

### Option C — Activer vad_eagerness correctement

Passer `"eagerness": self.vad_eagerness` dans `session.update` (valeur `"low"`).
OpenAI décrira moins agressivement les pauses comme du barge-in.

Risque : faible si OpenAI supporte bien le paramètre sur gpt-realtime-mini.

---

## Ma recommandation

Tester Option A d'abord (1 ligne, risque minimal) après confirmation VAD dans les logs.
Si insuffisant, combiner A + C.
Option B en dernier recours (logique plus complexe).

---

## Je n'agis pas avant

1. Test réel Ludovic avec heure exacte
2. Confirmation dans les logs que `speech_started` → `response.cancel` est la cause
3. Validation Ludovic sur la correction choisie
