# Avis Claude — Guardian / écoute silencieuse (30 juin 2026)

Branche : `audit/guardian-live-30juin` · Révision observée : `a4d7827`
Complément à l'audit Codex (`CODEX_GUARDIAN_LIVE_30JUIN_SILENT_LISTENING_AUDIT.md`).
Mode : avis + état des correctifs déjà appliqués. Ce document ne contient pas de changement de code.

## Position

Je confirme l'audit Codex point par point. Sa conclusion est la bonne : **le bruit permanent n'est pas un bug TTS isolé, il est architectural** — Guardian écoute ET parle en même temps, avec deux détecteurs vocaux parallèles (Web Speech + Android natif) et des mots-clés trop larges qui s'auto-déclenchent (larsen).

La règle produit fixée par Ludo est **non négociable** :

> **Écouter ≠ faire du bruit. L'écoute permanente doit être MUETTE par défaut ; le TTS devient opt-in.**
> Une personne en danger peut devoir rester discrète — un device qui émet du son en permanence la met en danger.

**Précision importante (rassurante).** La migration d'Iris Realtime vers l'API **GA (PCM 24 kHz)** est correcte — Codex le confirme (§8), et je l'ai validée contre l'API réelle (`session.updated` + 39 outils acceptés). **Le bruit permanent ne vient PAS de cette migration.** Donc le correctif voix peut être livré ; le bruit est un sujet distinct (TTS Guardian « parlant » + larsen + mots-clés larges).

## Ce que j'ai déjà corrigé (testé, NON déployé en trafic réel)

1. **Compte à rebours d'annulation rétabli** pour le chemin vocal Iris. Il avait été court-circuité par `_trigger_voice_emergency`, qui envoyait SMS+appels **immédiatement** (commit `b4befc2`, « voix pure + détection d'urgence »). Désormais : détection → **modale 5 s** « J'alerte tes proches dans 5 secondes » → annulable **à la voix** (« annule » / « je vais bien » / « ça va ») **ET au bouton** → **aucun envoi sans cette fenêtre**.
   - `integrations/openai/web_voice_bridge.py` : `_start_emergency_countdown()` / `_cancel_emergency_countdown()` ; `match_immediate_sos` et la confirmation « oui » passent par le countdown (plus d'appel direct à `_fire_and_reassure`) ; annulation voix + message client `emergency_cancel`.
   - `static/simli.html` : modale `#emgCountdown` (overlay, décompte, bouton « ✋ ANNULER »).
   - `core/safety/voice_emergency.py` : `is_cancel()`.
   - **Testé** (méthodes directes) : décompte complet → 1 envoi ; annulation → 0 envoi ; « au secours » → 0 envoi immédiat puis « annule » → 0 envoi.
2. **Migration GA Realtime** (la voix ne se connectait plus : OpenAI a coupé l'API Realtime Beta). Confirmée correcte par Codex §8.
3. **Mitigation faux positifs serveur** : un verdict LLM ne déclenche plus jamais sans confirmation ; retrait de « aide-moi / aidez-moi / à l'aide » des déclencheurs immédiats serveur ; correction d'un bug où `/api/test/scenario` remettait `_test_mode` global à `False` (désarmait la simulation → vrais envois).

## Plan de correction priorisé (aligné vision + audit Codex)

### P0 — Rendre l'écoute permanente MUETTE (cause directe du bruit)
- `static/guardian.html` : retirer le TTS `force:true` par défaut (annonces de countdown, chiffres égrenés, démarrage, SOS, vérification, all-clear). Remplacer par **UI visuelle + vibration discrète + notification système**. Le son devient un **réglage explicite, OFF par défaut**.
- Retirer `_ttsTest` au démarrage et le message vocal de démarrage.
- `static/simli.html` : désactiver les **sons décoratifs** en contexte Guardian.

### P0 — Casser la boucle larsen
- Bridge Android `pauseNativeVoiceGuardian()` / `resumeNativeVoiceGuardian()` autour de **tout** playback audio. Tant que l'écoute est muette par défaut le risque disparaît, mais ce garde-fou reste obligatoire dès qu'une annonce opt-in est rejouée (sinon le micro réentend la voix → re-déclenche).

### P1 — Aligner les mots-clés sur la politique serveur
- Web (`guardian.html`) + Android (`GuardianService.java`) : **immédiat UNIQUEMENT** pour formulations fortes et explicites (« au secours », « je suis en danger »…). Retirer les fragments (« aide », « secours », « urgence », « help »). Ambigu → **confirmation silencieuse** (countdown visuel) avant alerte. = même politique que `core/safety/voice_emergency.py`.

### P1 — Exposer l'all-clear (existe déjà côté backend — Codex §6)
- Après une alerte : bouton clair **« ✅ Tout va bien — prévenir mes proches »** → route existante `POST /api/guardian/incident/{id}/resolve` + `register_verification_response(ok=True)` (repasse en LOW, grace period, SMS d'annulation déjà construit dans `core/guardian/alerts.py`). Il reste à **câbler l'UI**, la mécanique backend est là.

### P1 — Zone safe (existe déjà — Codex §7)
- Utiliser la géofence (`core/guardian/engine.py`) pour **réduire/contextualiser les alertes AMBIGUËS** et faciliter l'all-clear. **Ne JAMAIS bloquer un SOS explicite** sous prétexte de zone safe.

## Séquencement proposé
1. **P0** silence + larsen → corrige le bruit (bloquant pour réactiver le widget always-on).
2. Tester en **révision sans trafic** (déjà en place : tag `test-voix`, URL `https://test-voix---luna-beta-gly3g647na-ew.a.run.app`) → valider **0 bruit** + countdown + voix.
3. **P1** mots-clés + all-clear + zone safe.
4. Bascule du trafic + urgence en **observation** (`VOICE_EMERGENCY_DRY_RUN=true`) avant tout passage en réel.

## Accord avec Codex
Mon avis et celui de Codex convergent entièrement. Division du travail proposée : Codex audite/cadre (lecture seule), j'implémente + teste, Ludo valide avant tout déploiement (gouvernance `CLAUDE.md`).

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>
