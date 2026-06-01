# Claude — Architecture visio : Tavus vs Simli vs pipeline maison — Objectif 017

Agent : Claude  
Objectif : 017  
Date : 2026-06-01  
Type : analyse architecture — aucun patch  

---

## Fait important ignoré dans le benchmark

Tavus n'est pas une option hypothétique. Il est **déjà dans Luna** :

```
TAVUS_API_KEY=70cc7318c9254a4caecb08478049162f
TAVUS_LUNA_PERSONA_ID=p10341f761ef
```

Tavus était le **système visio principal** avant le chantier Simli/B-lite.  
Un POC Tavus = revenir à ce qui existait, pas une migration nouvelle.

---

## Les 3 options réelles

### Option A — Revenir à Tavus CVI (déjà configuré)

**Ce que ça donne** :
- STT + LLM + TTS géré par Tavus (pipeline intégré, temps réel)
- Avatar vidéo Tavus (replica humain, lip-sync natif)
- Tavus gère le turn-taking, l'anti-écho, la latence
- Latence terrain mesurée précédemment : ~2-3s (vs ~10-14s pour Simli)
- Persona `p10341f761ef` déjà créée côté Tavus

**Ce qu'il faut faire** :
- Revenir sur la page visio d'avant le chantier Simli
- Appeler `POST /api/call` (endpoint existant dans `luna_web.py`)
- Brancher Daily.js sur la room Tavus (déjà dans le code)

**Risque** : coût Tavus au-delà des minutes gratuites. À mesurer.  
**Délai** : 0 jour de code — l'infrastructure existe.

---

### Option B — Continuer Simli + pipeline maison B-lite (situation actuelle)

**Ce qu'on essaie de faire** :
- Simli = affichage avatar uniquement
- Notre propre Web Speech API → `/api/visio/chat` → `/api/visio/tts` → `<audio>`

**Problème confirmé** :
- Web Speech API `window.SpeechRecognition` = **undefined dans Android WebView**
- Le STT est mort dans l'APK sans qu'aucune erreur visible ne remonte côté utilisateur
- Même si on fixe le STT : anti-écho, turn-taking, latence TTS sont à reconstruire pièce par pièce

**Pour atteindre le niveau Tavus avec cette option** :
- Remplacer Web Speech API par Whisper serveur (backend STT)
- Gérer l'anti-écho (`echoCancellation`, `noiseSuppression`, détection fin de parole)
- Gérer le turn-taking
- ElevenLabs latence ~600ms non streamée = voix "en bloc"
- Estimé : 3-4 semaines pour atteindre un niveau fonctionnel comparable

**Avantage** : contrôle total de la stack, pas de dépendance Tavus.  
**Risque** : investissement temps élevé pour un résultat encore incertain.

---

### Option C — Tavus CVI avec persona Luna personnalisée (upgrade)

**Ce que c'est** : utiliser l'API Tavus CVI pour créer une vraie secrétaire interactive avec la voix, le persona et le contexte de Luna.

**Différence avec Option A** : au lieu de juste "revenir" à l'ancien système, **configurer Tavus correctement** avec :
- Le prompt système Luna (Iris, secrétaire, profil utilisateur)
- La voix FR féminine (Tavus supporte les voix TTS configurables)
- Les tool calls Luna (notes, rappels, actions avec confirmation)
- Les instructions de contexte profil (`subscriber_name`, données utilisateur)

**Délai** : 1-2 jours pour configurer le persona Tavus + tester en terrain

---

## Comparaison froide

| Critère | Option A (retour Tavus) | Option B (Simli B-lite) | Option C (Tavus CVI configuré) |
|---|---|---|---|
| STT fonctionnel APK | ✅ (Tavus natif) | ❌ (WebView) | ✅ (Tavus natif) |
| Latence mesurée | ~2-3s | Inconnue (STT mort) | ~2-3s |
| Anti-écho | ✅ | À construire | ✅ |
| Turn-taking | ✅ | À construire | ✅ |
| Voix FR naturelle | Dépend config Tavus | Camille ElevenLabs (OK) | Configurable |
| Lip-sync avatar | ✅ | ❌ (avatar statique) | ✅ |
| Délai pour tester | 0 | 3-4 semaines | 1-2 jours |
| Coût | Tavus pricing | ElevenLabs/LLM seuls | Tavus pricing |
| Contrôle | Faible | Élevé | Moyen |
| Niveau Tavus-benchmark | = | << | = |

---

## Observation sur la capture WebView

Le `webview_console_visio.jsonl` s'est connecté à `about:blank` (Google Ads WebView),  
pas à la page Luna simli.html. Les logs JS restent invisibles.

Pour capturer le bon processus, il faut :
```powershell
# Lister TOUS les targets WebView
curl http://127.0.0.1:9222/json/list
# Identifier le target avec url contenant "simli" ou "luna-beta"
# Se connecter à ce WebSocket spécifiquement
```

---

## Ce que je propose à Codex

**Court terme** : tester Option A (retour Tavus) en 15 minutes chrono.  
`POST /api/call` existe, persona existe, clé existe. Si ça marche en terrain → preuve que Tavus-level est atteignable sans développement.

**Ensuite** : si Option A marche, Option C pour personnaliser Luna/Iris correctement.

**Si Option A échoue** : alors Option B avec Whisper STT devient la bonne direction.

---

## Ce que je ne décide pas

La décision entre Option A, B, C appartient à Ludovic.  
Je code uniquement après le feu vert.  
Pas de déploiement sans validation.
