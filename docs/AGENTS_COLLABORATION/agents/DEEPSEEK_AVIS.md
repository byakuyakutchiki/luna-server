# Avis DeepSeek

Agent : DeepSeek
Rôle : Analyse alternative, détection risques, propositions d'optimisation

---

## MISSION ACTIVE — Objectif 001 voix

**Assigné le** : 2026-05-25
**Branche à créer** : `ds/objectif-001-voix`

### Contexte

Luna utilise OpenAI Realtime API via WebSocket (`/ws/luna-voice`) pour la voix.
Le frontend (`static/index.html`) capture le micro, envoie l'audio via WebSocket,
reçoit l'audio de Luna et le lit.

**Problème observé** : bouton vocal silencieux, arrêt après ~20 secondes.

**Dernier fix déployé** (commit `e699ae6`) :
- Détection `LunaApp/` dans User-Agent → utiliser `ScriptProcessorNode` au lieu de AudioWorklet
- `OPENAI_VOICE_NAME=coral` (voix féminine) ajouté dans `.env` et Cloud Run

**Ce fix est déployé mais pas encore validé sur appareil réel.**

### Fichiers à analyser

| Fichier | Ce qu'il fait |
|---|---|
| `integrations/openai/web_voice_bridge.py` | Pont WebSocket → OpenAI Realtime API |
| `integrations/openai/realtime_bridge.py` | Bridge Realtime (Twilio voice) |
| `static/index.html` | Frontend — `startVoice()`, gestion audio, détection WebView |
| `luna_web.py` | Route `/ws/luna-voice`, endpoint `/api/voice/*` |

### Questions précises à répondre

**1. web_voice_bridge.py**
- Quelle voix est configurée par défaut ? (`alloy` → bug, `coral` → ok)
- Quel est le timeout de session ? (valeur en secondes)
- Que se passe-t-il quand OpenAI coupe la session après ~20s ? Est-ce géré ?
- Y a-t-il une reconnexion automatique ?
- Le format audio envoyé (`pcm16` / `g711_ulaw`) est-il compatible avec ce que produit ScriptProcessorNode ?

**2. static/index.html — fonction `startVoice()`**
- Le bloc `if (!_isWebView && ...)` existe-t-il ? (ligne approx ?)
- En mode WebView : `ScriptProcessorNode` avec quel `bufferSize` ?
- L'audio est-il correctement encodé en PCM16 / base64 avant envoi ?
- Y a-t-il un `onaudioprocess` qui envoie bien les chunks audio ?
- Quelle est la logique de reconnexion en cas d'erreur WebSocket ?

**3. luna_web.py — route `/ws/luna-voice`**
- Le WebSocket est-il bien enregistré ?
- Y a-t-il une limite de durée côté serveur ?
- Les erreurs OpenAI sont-elles propagées au client ?

### Ce que tu dois poster ici

Remplir les sections ci-dessous avec tes trouvailles réelles (fichier + ligne).

#### Analyse web_voice_bridge.py

Voix par défaut : 
Timeout session : 
Reconnexion auto : oui / non
Format audio attendu : 
Problème identifié : 

#### Analyse index.html startVoice()

Fix AudioWorklet présent : oui / non (ligne : )
bufferSize ScriptProcessorNode : 
Encodage PCM16 correct : oui / non
Reconnexion WebSocket : oui / non
Problème identifié : 

#### Analyse luna_web.py /ws/luna-voice

Route enregistrée : oui / non
Limite durée côté serveur : oui / non (valeur : )
Erreurs propagées au client : oui / non
Problème identifié : 

#### Verdict DeepSeek

Cause probable du bug (fichier + ligne) :

Correction minimale proposée :

Risque de régression si on applique la correction :

Validation Ludovic nécessaire avant déploiement : oui / non

---

### Interdictions

- Ne pas modifier `luna_web.py` ni `index.html` directement sur `main`
- Ne pas déployer sur Cloud Run
- Ne pas appeler l'API OpenAI pour tester (vérification statique du code uniquement)
- Branche `ds/objectif-001-voix` uniquement
- Toute proposition de modification → PR → review Claude → validation Ludovic
