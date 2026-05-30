# Objectif 013 — Visio Luna réelle / Simli / voix / vision caméra

**Statut** : ouvert — audit multi-agents  
**Priorité** : haute  
**Lead final** : Claude  
**Date ouverture** : 2026-05-28  
**Document dédié** : ce fichier

---

## Contexte terrain

Ludovic vient de tester la visio sur l'application Luna (APK réelle).

**Résultat terrain :**
- Le bouton Visio lance bien Simli.
- L'avatar apparaît correctement en face.
- Ludovic a rechargé Simli : environ 1000 minutes disponibles.
- Problème 1 : l'avatar visible n'est pas Luna.
- Problème 2 : la voix entendue est masculine alors que l'avatar est féminin.
- Problème 3 : Luna ne répond pas au message texte envoyé.
- Problème 4 : Luna ne semble pas analyser la caméra utilisateur.
- Retour 2026-05-30 : une barre de chat "Iris" a été ajoutée en production. Ludovic considère que ce n'est pas la vocation validée de la visio et que l'expérience ne prouve toujours pas voix production, vision caméra, reconnaissance de Ludovic ni objectifs secrétaire. Voir Objectif 014.

---

## Recadrage obligatoire 2026-05-30

Objectif 013 ne doit plus avancer par patchs techniques isolés.  
La suite passe par `docs/AGENTS_COLLABORATION/OBJECTIF_014_RECADRAGE_VISIO_REELLE.md`.

Décision de coordination :
- la barre texte Iris est non validée comme expérience produit ;
- aucun nouvel élément UI visible ne doit être codé sans matrice objectif -> preuve -> risque -> validation ;
- Kimi doit regarder le rendu réel ;
- Codex définit les targets produit ;
- DeepSeek audite les gaps techniques ;
- Claude code seulement après cette séquence.

---

## Architecture visio actuelle

```
Frontend (simli.html)
  ├── Pré-test micro/caméra (getUserMedia)
  ├── Cinématique lancement
  ├── POST /api/call → Tavus (premium) ou Simli (fallback)
  ├── Daily.js iframe (WebRTC audio/vidéo)
  ├── Vision caméra : capture canvas → POST /api/visio/perception (toutes les 12s)
  ├── SpeechRecognition (notes uniquement)
  └── Hangup → nettoyage Daily.js

Backend (luna_web.py)
  ├── POST /api/call → routing Tavus/Simli + budget guard
  ├── POST /api/simli/start → appel api.simli.ai/auto/start/configurable
  │     ├── faceId = SIMLI_FACE_ID
  │     ├── LLM = gpt-4o-mini (customLLMConfig)
  │     ├── TTS = Cartesia (prio 1) ou ElevenLabs (prio 2)
  │     └── Retourne conversation_url Daily.co
  ├── POST /api/visio/perception → PerceptionDetector (OpenAI Vision)
  ├── Webhook Tavus (/api/webhook/tavus) → tool calls + transcript
  └── WebSocket Simli (/ws/simli) → DÉSACTIVÉE (_SIMLI_AVAILABLE = False)
```

---

## Problèmes identifiés par l'audit agents

### P1 — Avatar Luna manquant
**Cause** : `SIMLI_FACE_ID` pointe vers un avatar générique Simli, pas Luna.  
**Fichier** : `luna_web.py:6832`  
**Solution** : créer/configurer un avatar Simli basé sur les photos Luna adulte (sur Windows Ludovic).  
**Niveau** : 2 (changement visible majeur, nécessite validation Ludovic).

### P2 — Voix masculine ✅ RÉSOLU (2026-05-29)
**Cause** : Simli utilise TTS ElevenLabs sans voix configurée → fallback Rachel (anglaise/masculine perception).  
**Fichier** : `luna_web.py:6892-6896`  
**Solution appliquée** :
- `ELEVENLABS_VOICE_ID=6BlZrFdruL4hpXFHmHUC` ajouté dans `.env` (Alice — voix française native)
- `payload["elevenlabsLanguageCode"] = "fr"` ajouté dans `_start_simli_visio()`
- **À valider** : test local < 30 secondes. Cloud Run uniquement après validation Ludovic.

### P3 — Luna ne répond pas au texte
**Cause** : le flux visio est **audio-only** via Daily.co. Aucun champ texte n'est envoyé au LLM. Simli fait STT → GPT-4o-mini → TTS. Le texte tapé n'a pas de canal.  
**Fichier** : `static/simli.html` (pas de input texte dans l'UI visio)  
**Solution** : ajouter un input texte/chat dans simli.html qui injecte le message via `sendAppMessage` ou API Simli.  
**Niveau** : 2 (ajout UI + flux message).

### P4 — Vision caméra limitée
**Cause** : la vision existe mais est indirecte. Capture canvas toutes les 12s → POST /api/visio/perception → injection texte `[Système vision]`. Ce n'est pas de la "vision native" du LLM.  
**Fichier** : `static/simli.html:1864-2034`, `luna_web.py:7295-7387`  
**Solution V1** : améliorer l'injection du contexte vision dans la conversation (plus fréquent, plus détaillé).  
**Solution V2** : utiliser GPT-4o Vision natif côté Simli (si Simli le supporte).  
**Niveau** : 1 (amélioration injection) / 2 (vision native).

### P5 — Hangup Simli non géré
**Cause** : `doHangup()` appelle toujours `POST /api/call/end` qui ne gère que Tavus. Simli expire seul après `maxIdleTime` (300s).  
**Fichier** : `static/simli.html:2194`, `luna_web.py:7040`  
**Solution** : appeler `POST /api/simli/end` ou laisser expirer (documenter).  
**Niveau** : 1.

### P6 — WebSocket Simli désactivée
**Cause** : `_SIMLI_AVAILABLE = False` dans `luna_web.py:89`.  
**Impact** : `/ws/simli/{session_id}` retourne 4003. Heureusement, `/api/simli/start` REST fonctionne.  
**Niveau** : 0 (audit, pas d'impact immédiat sur le fallback REST).

---

## Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `static/simli.html` | Page visio complète (UI, Daily.js, vision, notes, upload) |
| `static/index.html` | Boutons lancement visio (`startCall`, `_concStartVisio`) |
| `luna_web.py` | Endpoints `/api/call`, `/api/simli/start`, `/api/visio/perception`, webhooks |
| `integrations/tavus/tavus_client.py` | Client Tavus CVI |
| `core/perception/detector.py` | Analyse frame caméra (OpenAI Vision) |
| `core/perception/analyzer.py` | Analyse temporelle scène |

---

## Répartition agents

| Agent | Tâche | Niveau |
|---|---|---|
| **Kimi** | UX visio réelle : tester le parcours, identifier frictions UI, proposer input texte, cohérence avatar/voix | 0-1 |
| **DeepSeek** | Audit technique code : flux Simli/Tavus, injection messages, vision caméra, configuration voix/avatar | 0 |
| **Codex** | Synthèse, priorisation, garde-fous, structuration des décisions Ludovic | 0 |
| **Claude** | Intégration finale et déploiement (après validation Ludovic) | 2-3 |

---

## Interdictions

- Pas de déploiement sans validation Ludovic.
- Pas de consommation inutile des crédits Simli (1000 min restantes).
- Pas de longues sessions vidéo en boucle pour tester.
- Pas de modification secrets, Cloud, base de données, paiement.
- Pas de remplacement avatar/voix sans validation Ludovic.
- Pas de refonte graphique validée.
- **ZERO Twilio** (SMS/appels) pendant tout cet objectif.

---

## Validation

- [x] Kimi a testé l'UX visio réelle et posté son avis.
- [x] DeepSeek a audité le flux technique et posté son avis.
- [x] Claude a configuré ELEVENLABS_VOICE_ID=Alice + elevenlabsLanguageCode=fr.
- [ ] Ludovic valide la voix Alice en test local (< 30s).
- [ ] Ludovic valide le plan d'action (avatar P1, texte P3, vision P4).
- [ ] Implémentation sur branche dédiée.
- [ ] Test téléphone validé.
- [ ] Déploiement Cloud Run.
