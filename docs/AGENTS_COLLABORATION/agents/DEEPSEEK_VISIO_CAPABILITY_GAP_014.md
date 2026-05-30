# DeepSeek — Audit gaps capacité visio Iris — Objectif 014

Agent : DeepSeek (transcrit par Claude depuis le fil Ludovic)  
Date : 2026-05-30  
Statut : livrable  

---

## Résumé

10 targets auditées. Cause principale identifiée : `ELEVENLABS_API_KEY` absente de Cloud Run → voix masculine (fallback Simli TTS natif). Les autres gaps sont documentés par target ci-dessous.

---

## Gap 1 — Env vars Cloud Run manquantes

| Variable | Présente Cloud Run | Source vérité |
|---|---|---|
| `OPENAI_API_KEY` | ✅ Oui | `.env` local |
| `ELEVENLABS_API_KEY` | ❌ **Manquante** | `.env` local seulement |
| `ELEVENLABS_VOICE_ID` | ❌ **Manquante** | `.env` local seulement |
| `SIMLI_API_KEY` | ✅ Oui | `.env` local |
| `SIMLI_FACE_ID` | ✅ Oui | `.env` local |
| `OPENAI_VOICE_NAME` | ✅ Oui (coral) | `.env` local |
| `ADMIN_NUMBER` | ❌ Retirée volontairement | commit 91fa238 |
| `TWILIO_*` | ✅ Oui | `.env` local |

**Cause directe de la voix masculine** : `ELEVENLABS_API_KEY` absente de Cloud Run → Simli ne peut pas appeler ElevenLabs → fallback TTS Simli natif (voix générique, potentiellement masculine).

**Correction requise** : déployer `ELEVENLABS_API_KEY` et `ELEVENLABS_VOICE_ID` sur Cloud Run via `gcloud run services update --update-env-vars`. **Niveau 2 — validation Ludovic.**

---

## Gap 2 — Risques coût Simli / ElevenLabs / Twilio

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Session Simli longue non fermée | Haute | Crédits gaspillés | `maxIdleTime=60s` ✅ |
| Test Simli en boucle | Haute | Crédits gaspillés | Sessions courtes, dry-run |
| ElevenLabs appel TTS à chaque réponse | Haute | Coût par caractère | 1 appel par échange max |
| Clé ElevenLabs non déployée Cloud Run | Haute | Voix masculine en prod | Déployer var env |
| SMS/appel Twilio accidentel | Faible | 20€ perdus | Bloqué dans le code ✅ |
| Vision OpenAI frame par frame | Haute | ~0.05€ par analyse | Frame unique sur déclenchement |

---

## Target 1 — Voix féminine française

**Fichiers** : `luna_web.py:6892-6897` (`_start_simli_visio`)  
**Statut** : ❌ Cassé en production  
**Écart** : Voix masculine en prod, Alice configurée en local seulement  
**Cause** : `ELEVENLABS_API_KEY` et `ELEVENLABS_VOICE_ID` absentes de Cloud Run  
**Correction** : Déployer les deux variables sur Cloud Run  
**Test non destructif** : Vérifier `gcloud run services describe luna-beta --format="value(spec.template.spec.containers[0].env)"` (sans secret dans GitHub)  
**Niveau** : 2 — validation Ludovic  
**Risque coût** : ElevenLabs ~0.0003$/char. Session 30s ≈ 200 chars ≈ 0.06$. Acceptable.

---

## Target 2 — Identité Ludovic

**Fichiers** : `luna_web.py:6879` (`firstMessage`), `_tenant_subscriber_first_name()` ligne ~6585  
**Statut** : Supposé fonctionnel  
**Écart** : `subscriber_name` est injecté dans le `firstMessage` mais dépend de `profile.first_name` en base  
**Cause** : Non vérifié que le profil fondateur a `first_name = "Ludovic"`  
**Correction** : Vérifier via `GET /api/profile` (token fondateur)  
**Test non destructif** : `curl -H "Authorization: Bearer <token>" https://luna-beta-.../api/profile`  
**Niveau** : 1 — non destructif  
**Risque** : Faible

---

## Target 3 — Compréhension vocale (STT)

**Fichiers** : Pipeline Simli natif (côté Simli, pas côté code local)  
**Statut** : Non prouvé  
**Écart** : Simli fait STT → gpt-4o-mini nativement, mais non testé sur phrase réelle en prod  
**Cause** : Pas de test terrain enregistré  
**Correction** : Test court < 30s : "prends une note : test visio Luna"  
**Test non destructif** : Session unique < 30s, vérifier trace dans `/api/visio/notes`  
**Niveau** : 1 — test terrain Ludovic  
**Risque coût** : ~0.01$ pour 30s session Simli

---

## Target 4 — Vision caméra ("tu me vois ?")

**Fichiers** : `static/simli.html:1864-2034`, `luna_web.py:7295-7387` (`/api/visio/perception`)  
**Statut** : Branché mais non prouvé  
**Écart** : Capture canvas 320x240 toutes les 12s → OpenAI Vision → injection `[Système vision]`. Latence = 12s minimum. Non temps réel.  
**Cause** : Architecture indirecte — Iris reçoit une description textuelle de la scène, pas une vision native  
**Correction V1** : Réduire l'intervalle à 6s (niveau 1). V2 : vision native GPT-4o (niveau 2)  
**Test non destructif** : Lancer session courte, lever la main, attendre 15s, observer si Iris mentionne la main  
**Niveau** : 1 pour amélioration injection / 2 pour vision native  
**Risque coût** : ~0.05$ par frame OpenAI Vision. À 12s = ~5 appels/min = ~0.25$/min

---

## Target 5 — Prendre une note

**Fichiers** : `luna_web.py:7297+` (`/api/visio/notes`), `_visioTranscript` dans simli.html  
**Statut** : Branché  
**Écart** : Le transcript est sauvegardé automatiquement au hangup. La note manuelle via commande vocale dépend du LLM qui doit appeler l'outil `create_instruction`  
**Correction** : Test court "prends une note : test visio Luna", vérifier `/api/visio/notes` après session  
**Niveau** : 1  
**Risque** : Faible

---

## Target 6 — Résumer l'échange

**Fichiers** : `/api/visio/notes`, transcript `_visioTranscript`  
**Statut** : Branché  
**Écart** : Le résumé est généré automatiquement si le transcript contient des données. Non testé terrain.  
**Niveau** : 1  
**Risque** : Faible

---

## Target 7 — Météo / info simple

**Fichiers** : `luna_web.py` tools `get_weather`, `get_news`, contexte temps réel `_build_realtime_context()`  
**Statut** : Branché  
**Écart** : Le contexte météo est pré-fetché au démarrage de la session Simli. Non testé terrain en visio.  
**Correction** : Test court "quelle est la météo ?" en visio  
**Niveau** : 1  
**Risque** : Faible (lecture seule)

---

## Target 8 — Créer un rappel non sensible

**Fichiers** : `luna_web.py` `_tool_create_instruction()`, `/api/instructions`  
**Statut** : Branché  
**Écart** : Non testé terrain en visio  
**Niveau** : 1  
**Risque** : Faible

---

## Target 9 — Refuser SMS/appel/email (protection)

**Fichiers** : `luna_web.py:5606+` `_ACTION_TOOLS`, guard confirmation  
**Statut** : Branché  
**Écart** : Guard présent mais non testé en visio — est-ce qu'Iris demande bien confirmation avant tout SMS/appel ?  
**Niveau** : 1 (test), 3 (action réelle)  
**Risque** : Moyen — si guard défaillant, action Twilio réelle possible

---

## Target 10 — Canal texte secours

**Fichiers** : `static/simli.html` (barre retirée commit 4e1d2ba)  
**Statut** : ❌ Retiré — non déployé  
**Écart** : La barre permanente a été jugée intrusive. Pas d'alternative encore définie.  
**Correction** : Attendre proposition UX Kimi (swipe-up mini-drawer selon son rapport) + validation Ludovic  
**Niveau** : 2  
**Risque** : UI visible — validation Ludovic obligatoire

---

## Synthèse priorisation

| Priorité | Target | Niveau | Blocage |
|---|---|---|---|
| **P0 immédiat** | Voix féminine (env vars Cloud Run) | 2 | Validation Ludovic + `deploie` |
| **P1 terrain** | Identité Ludovic, STT, météo, note, rappel | 1 | Test court Ludovic |
| **P1 terrain** | Vision caméra | 1/2 | Test court Ludovic |
| **P2 produit** | Canal texte secours | 2 | Kimi UX + Ludovic |
| **P3 sécurité** | Guard SMS/appel/email | 1/3 | Test terrain avant déploiement |

**Action immédiate recommandée** : déployer `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` sur Cloud Run. Une commande, résultat immédiat sur la voix.
