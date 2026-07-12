# Voix pure Iris — convergence des deux implémentations + greffe Urgence

Date : 28 juin 2026. **À LIRE avant de toucher au mode vocal Iris.**

## Situation
Deux sessions ont implémenté la voix pure Iris **en parallèle, différemment** :

| | Approche A (déployée prod `luna-beta-00759`) | Approche B (WIP non commité de l'autre session) |
|---|---|---|
| Activation | Voix pure = **défaut** (`command_screen=False` câblé dans `ws_iris_voice`) | Voix pure = **opt-in** via `?ics=0` (défaut `ics=1` = panneau) |
| Flag | nouveau `command_screen` | réutilise `iris_mode` (existant) |
| Prompt | `_IRIS_SYSTEM` réécrit (voix pure) | garde `_IRIS_SYSTEM` (panneau) + ajoute `_IRIS_VOICE_SYSTEM` |
| Panneau web `/simli` | retiré partout | **conservé** (sauf si `?ics=0`) |
| Urgence (SOS→SMS/appels) | ✅ incluse | ❌ absente |
| Branche | `feat/iris-voice-emergency` (commit `b4befc2`) | working tree `feat/banc-essai-services` (non commité) |

## Décision (Ludo, 28/06)
**Garder l'approche B (toggle `?ics=0` / `iris_mode`) + y greffer l'Urgence de l'approche A. Retirer le flag `command_screen` redondant.**

## Dépendance bloquante
L'approche B défaut `ics=1` → **le frontend/APK doit envoyer `?ics=0`** pour activer la voix pure.
Tant que ce n'est pas fait, déployer B = **le panneau revient par défaut** (régression voix pure).
→ On garde donc la prod sur `00759` (voix pure + urgence fonctionnelles) jusqu'à ce que :
1. l'autre session **committe** son WIP voix-pure (backend B), **et**
2. le frontend envoie bien `?ics=0`.

## Greffe Urgence sur l'approche B (100 % additif, indépendant du flag)
L'urgence doit fonctionner **quel que soit** le mode UI (la sécurité ne dépend pas du panneau).
Éléments à reporter depuis `feat/iris-voice-emergency` (commit `b4befc2`) :

1. **Module** `core/safety/voice_emergency.py` — déjà autonome, copier tel quel.
2. **Bridge** `integrations/openai/web_voice_bridge.py` :
   - constructeur : params `emergency_detect=None, emergency_fire=None` + `self._pending_emergency=None`, `self._emergency_active=False` ;
   - méthodes `_speak`, `_fire_and_reassure`, `_ask_emergency_confirmation`, `_emergency_llm_followup`, `_handle_emergency` ;
   - dans le handler `conversation.item.input_audio_transcription.completed` ET le path texte : appeler `await self._handle_emergency(text)` AVANT la réponse normale, et sauter la réponse si géré. **Gardé par `self._emergency_fire is not None`** → s'active uniquement quand les callbacks sont fournis, donc indépendant de `iris_mode`/`command_screen`.
3. **luna_web.py** :
   - fonction `_trigger_voice_emergency(tid, summary, level)` (SMS+appels+position, respecte `_test_mode` et `VOICE_EMERGENCY_DRY_RUN`) ;
   - `_test_mode` lit `LUNA_TEST_MODE` ;
   - dans `ws_iris_voice` : définir `_iris_emergency_detect`/`_iris_emergency_fire` + gate `VOICE_EMERGENCY_ENABLED`, passer `emergency_detect/emergency_fire` au bridge.
4. **deploy.sh** : `VOICE_EMERGENCY_ENABLED=true`, `VOICE_EMERGENCY_DRY_RUN=true`.

Détails comportement/tests urgence : `docs/IRIS_VOICE_EMERGENCY.md`.
Vérifié dry-run : 0 faux positif / 8 phrases banales, 5/5 urgences.

## Étapes finales (quand B est prêt côté frontend)
1. Sur la branche canonique : partir du backend B committé.
2. Greffer l'urgence (liste ci-dessus).
3. Retirer toute trace du flag `command_screen` (redondant avec `iris_mode`).
4. Tester en `LUNA_TEST_MODE=1` (voix pure silence/identité + urgence dry-run).
5. Déployer **depuis `PROPRIO/serveur`** (jamais depuis `~/luna-server`, périmé — cf incident 00758).
6. Supprimer la branche `feat/iris-voice-emergency`.

## Garde-fous env en prod (déjà posés sur le service)
`VOICE_EMERGENCY_ENABLED` (on/off), `VOICE_EMERGENCY_DRY_RUN=true` (observation, 0 envoi réel).
Passage réel : `gcloud run services update luna-beta --region=europe-west1 --update-env-vars=VOICE_EMERGENCY_DRY_RUN=false`.
