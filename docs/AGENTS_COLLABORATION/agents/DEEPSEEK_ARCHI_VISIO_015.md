# DeepSeek — Audit architecture visio temps réel — Objectif 015

Agent : DeepSeek (transcrit par Claude — fichier jamais livré directement)  
Date : 2026-05-31  
Référence : `OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`

---

## Contexte

L'architecture actuelle Simli `auto/start/configurable + Daily.js iframe` produit :
- une sortie audio (ElevenLabs fonctionne depuis le fix clé)
- mais pas de boucle conversationnelle fiable (STT non confirmé, latence inconnue)
- un avatar distordu
- une voix à accent anglais

Ce document compare 4 options architecturales pour atteindre les targets P0/P1 de l'Objectif 015.

---

## Option A — Garder Simli `auto/start/configurable` (architecture actuelle)

### Description

`POST https://api.simli.ai/auto/start/configurable` → roomUrl Daily.js → iframe frontend.  
Simli gère en boîte noire : STT (inconnu), LLM (via `customLLMConfig`), TTS (ElevenLabs configuré), avatar lip-sync.

### Avantages

- Déjà en place, fonctionnel partiellement
- Zéro infrastructure supplémentaire
- Coût opérationnel faible (Simli facture à la session)

### Inconvénients

| Point | Problème |
|---|---|
| STT | Non contrôlé — on ne sait pas quel STT Simli utilise, ni si il capte le micro Daily iframe |
| Latence | Opaque — impossible de mesurer ou d'optimiser |
| Logs | Pas d'événements STT natifs Simli (seulement `conversation.utterance` via Daily si branché) |
| Dépréciation | Simli marque plusieurs endpoints `auto/*` comme deprecated dans sa doc actuelle |
| Voix | ElevenLabs intégré mais accent anglais avec voix Alice |
| Avatar | Ratio vidéo non documenté → distorsion côté client |

### Faisabilité

✅ Déjà en prod. Risque : Simli peut déprécier l'endpoint sans préavis.

### Décision Ludovic requise

Oui si STT non prouvé après instrumentation — passer à Option B ou D.

---

## Option B — Simli SDK / WebRTC avec pipeline contrôlé

### Description

Utiliser le SDK JavaScript Simli officiel (`@simli-ai/simli-client`) ou l'API WebRTC directe.  
Pipeline : STT côté navigateur (Web Speech API ou Whisper) → envoi texte à Simli via SDK → Simli génère avatar + audio lip-sync → Daily/WebRTC reçoit le flux.

Sources : `https://docs.simli.com/api-reference/javascript`, `https://docs.simli.com/api-reference/simli-webrtc`

### Avantages

- Contrôle total sur STT (navigateur ou serveur)
- Logs STT côté client disponibles
- Latence mesurable
- Pas de dépendance à l'endpoint `auto/start/configurable`
- Voix et modèle LLM entièrement maîtrisés

### Inconvénients

| Point | Problème |
|---|---|
| Implémentation | Refonte du frontend `simli.html` — 2 à 4 jours de travail |
| STT navigateur | Web Speech API non supportée sur tous les Android WebView |
| STT Whisper | Nécessite appel serveur → latence +500ms à +1500ms |
| Coût | Simli SDK peut avoir une tarification différente |
| Complexité | Pipeline à gérer côté client : capture audio → STT → LLM → TTS → lip-sync |

### Faisabilité

✅ Faisable. Délai estimé : 3–5 jours. Nécessite validation architecture avant code.

### Décision Ludovic requise

Oui — refonte partielle frontend + choix STT.

---

## Option C — LiveKit / Pipecat + Simli avatar

### Description

Remplacer Daily.js par LiveKit pour le transport WebRTC.  
Utiliser Pipecat (framework voice bot open source) côté serveur : Pipecat orchestre STT (Deepgram/Whisper) → LLM (GPT-4o) → TTS (ElevenLabs) → Simli pour le lip-sync avatar.

### Avantages

- Pipeline 100% contrôlé et observable
- Latence optimisée (Pipecat pipeline ~1-2s)
- STT Deepgram = meilleur du marché pour FR (~95% précision)
- Logs complets à chaque étage
- Avatar Simli conservé pour le lip-sync

### Inconvénients

| Point | Problème |
|---|---|
| Complexité | Architecture serveur complète à refaire |
| Coût infrastructure | LiveKit self-hosted ou cloud (~0.01$/min), Deepgram (~0.007$/min FR) |
| Délai | 1 à 3 semaines de développement |
| Cloud Run | LiveKit serveur nécessite une instance séparée (pas juste Cloud Run) |
| Dépendances | Pipecat, LiveKit SDK, Deepgram — 3 nouvelles dépendances |

### Faisabilité

✅ Techniquement la meilleure architecture long terme. Trop complexe pour un P0 immédiat.

### Décision Ludovic requise

Oui — décision stratégique majeure. Recommandé pour V2 si Option A/B ne suffisent pas.

---

## Option D — Secours temporaire : STT navigateur → LLM → TTS direct

### Description

Contournement sans Simli STT : le navigateur capte l'audio (Web Speech API), envoie le texte au backend Luna (`/api/chat`), Luna répond via GPT-4o, le texte est lu par ElevenLabs TTS direct (sans Simli), et Simli n'est utilisé que pour l'avatar lip-sync ou est retiré temporairement.

### Avantages

- Implémentation rapide (1–2 jours)
- Preuve de concept conversationnelle immédiate
- Logs complets côté serveur
- Voix ElevenLabs contrôlée directement
- Pas de dépendance au STT opaque de Simli

### Inconvénients

| Point | Problème |
|---|---|
| Web Speech API | Non disponible sur Android WebView (APK) → bloquant pour mobile |
| Avatar | Lip-sync perdu si Simli n'est pas dans la boucle audio |
| Latence | TTS ElevenLabs + LLM = 2–4s, acceptable mais pas temps réel |
| Régression | Perd l'avatar lip-sync si Simli est coupé du flux audio |

### Faisabilité

⚠️ Partielle — valide sur Chrome desktop, bloquante sur Android WebView APK.

### Décision Ludovic requise

Oui si test desktop uniquement acceptable. Non si APK est requis immédiatement.

---

## Synthèse comparative

| Critère | A — Simli auto | B — Simli SDK | C — LiveKit/Pipecat | D — Secours STT |
|---|---|---|---|---|
| **STT contrôlé** | ❌ Opaque | ✅ Oui | ✅ Oui | ⚠️ Partiel |
| **Latence connue** | ❌ Non | ✅ Oui | ✅ Oui | ✅ Oui |
| **Logs exploitables** | ⚠️ Partiels | ✅ Oui | ✅ Oui | ✅ Oui |
| **Voix FR native** | ⚠️ ElevenLabs (à changer) | ✅ ElevenLabs direct | ✅ ElevenLabs direct | ✅ ElevenLabs direct |
| **Avatar lip-sync** | ✅ Simli natif | ✅ Simli SDK | ✅ Simli | ❌ Perdu |
| **Délai implémentation** | 0j (déjà en prod) | 3–5j | 2–3 sem | 1–2j |
| **Coût** | Faible | Moyen | Élevé | Faible |
| **Risque dépréciation** | ⚠️ Élevé | Faible | Faible | Faible |
| **Android WebView** | ✅ | ✅ | ✅ | ❌ |

---

## Recommandation DeepSeek

**Court terme (P0 immédiat)** :
1. Déployer l'instrumentation Claude (sondes rLog) → prouver ou infirmer STT Option A
2. Si STT Option A confirmé → corriger voix + latence dans Option A
3. Si STT Option A non prouvé après 1 test terrain → passer directement à Option B

**Moyen terme (P1)** :
- Option B si on veut contrôle STT + logs + même infrastructure
- Option C si Ludovic décide d'une refonte complète V2

**Option D** : secours desktop uniquement, non viable pour APK — ne pas prioriser.

---

## Décision Ludovic requise

| Question | Impact |
|---|---|
| Option A suffisante si STT prouvé ? | Rester sur l'architecture actuelle |
| Passer Option B si STT non prouvé ? | Refonte frontend 3–5 jours |
| Option C en V2 ? | Décision stratégique 2–3 semaines |
| APK Android = priorité ? | Élimine Option D |
