# Iris Audio — Cahier des charges

**Version** : 1.0  
**Date** : 2026-06-02  
**Statut** : référence active  
**Remplace** : toute mention "Visio Luna" / "Visio Iris" dans les docs précédents

---

## 1. Vision produit

Iris est l'assistante vocale intelligente de Luna YAWatch.  
Elle n'a pas de visage, pas d'avatar, pas de caméra.  
Elle existe uniquement par la voix — présente, précise, rapide.

**Aesthetic de référence** : Jarvis (Iron Man) / K2000  
**Promesse utilisateur** : parler naturellement à Iris, obtenir une réponse utile en moins de 2 secondes, et pouvoir déléguer des actions concrètes avec confirmation.

---

## 2. Ce qu'Iris doit savoir faire

### 2.1 Conversation en temps réel

- Écouter le ou les participants via le micro (VAD automatique — silence 700ms)
- Transcrire la parole en texte (Whisper-1, langue française)
- Maintenir un historique de conversation cohérent sur toute la session
- Répondre par la voix en français naturel (OpenAI TTS tts-1, voix féminine)
- Raccrocher proprement sur demande vocale ou appui bouton
- Ne jamais laisser un tour en suspens (timeout + fallback si LLM ou TTS échoue)

### 2.2 Réponses quotidiennes à l'oral

- Donner la météo du jour avec conseil vestimentaire
- Lire les actualités personnalisées
- Répondre à des questions générales
- Faire des calculs, conversions, estimations rapides
- Résumer l'agenda du jour ("qu'est-ce que j'ai aujourd'hui ?")
- Lire un résumé de conversation précédente si demandé

### 2.3 Rappels et instructions

- Créer un rappel vocal ("rappelle-moi à 18h de rappeler Marie")
- Créer une note ou une tâche ("note que le plombier passe jeudi")
- Programmer des rappels récurrents (médicaments, rendez-vous, factures)
- Suivre un dossier dans le temps ("où en est ma demande APL ?")
- Alerter sur les échéances à venir (agenda, contrats, documents)

### 2.4 Actions avec confirmation obligatoire

Iris ne déclenche aucune action engageante sans confirmation explicite de l'utilisateur.

| Action | Confirmation | Compte-rendu |
|---|---|---|
| Envoyer un SMS | Oui — lire le message + destinataire avant envoi | Oui |
| Passer un appel Twilio | Oui — confirmer contact + objet | Oui |
| Envoyer un email | Oui — résumer l'email avant envoi | Oui |
| Créer un événement agenda | Oui — lire date + heure + titre | Oui |
| Rechercher vol/hôtel | Non (lecture seule) | Présenter options, ne pas réserver |
| Réserver un vol/hôtel | Oui — confirmer tous les détails | Oui |

### 2.5 Délégation de missions à un tiers

- Appeler un contact avec un script précis fourni par le souscripteur
- Confirmer un rendez-vous pour le souscripteur
- Prendre des nouvelles d'un proche selon les instructions
- Faire un compte-rendu après chaque mission exécutée
- Refuser toute déviation du script : recentrer poliment ou escalader vers le souscripteur
- Ne jamais relancer plus de 3 fois le même contact sur le même sujet

### 2.6 Information sans action

- Expliquer un courrier administratif reçu
- Résumer un document long
- Aider à remplir un formulaire à l'oral (expliquer les champs)
- Orienter vers les bons interlocuteurs (mairie, CAF, Sécu, préfecture)
- Expliquer des droits en langage simple (sans conseil juridique)
- Résumer une actualité, un texte de loi, un contrat

### 2.7 Sécurité et bien-être

- Détecter l'inactivité prolongée → alerter les contacts de confiance
- Détecter une détresse vocale → suggérer les numéros d'urgence (pas les appeler)
- Check-in quotidien si programmé
- Compagnie conversationnelle (contre l'isolement)

### 2.8 Ce qu'Iris ne fait jamais

- Aucun paiement, virement, engagement financier sans confirmation
- Aucun appel/SMS/email sans confirmation explicite
- Aucun appel entre 22h et 7h sauf urgence vitale
- Aucun conseil médical, juridique ou financier
- Jamais se faire passer pour un humain — toujours se présenter comme Iris
- Jamais appeler le 15/17/18/112 (interdit pour une IA)
- Jamais stocker de mots de passe, codes bancaires, identifiants

---

## 3. Mode multi-participants

### 3.1 Définition

Plusieurs personnes peuvent participer à la même session Iris Audio.

**Cas d'usage principal** : 2 à 4 personnes dans la même pièce, sur le même appareil, prenant la parole à tour de rôle.

**Cas secondaire** : plusieurs appareils/navigateurs partageant le même identifiant de session (même logement / même famille).

### 3.2 Comportement attendu

**Lors d'un appel solo (1 personne)**
- Iris écoute, répond, maintient l'historique — comportement actuel.

**Lors d'un appel à plusieurs (2+ personnes)**
- Iris attend que le tour de parole soit terminé avant de répondre (VAD inchangé).
- Iris ne coupe jamais la parole — si elle parle et que quelqu'un l'interrompt, elle s'arrête et écoute (barge-in).
- L'historique de conversation est partagé : toutes les interventions sont dans le même contexte.
- Si plusieurs voix parlent simultanément, Iris répond à la dernière transcription reçue sans boucle.
- Iris peut être informée du nombre de participants (`participants_count`) pour adapter son ton ("vous tous", "l'un d'entre vous").
- Iris ne tente pas d'identifier les voix individuellement (pas de diarisation — hors scope V1).

### 3.3 Règles anti-collision

| Situation | Comportement Iris |
|---|---|
| Iris répond + quelqu'un parle | `_irisReplying = true` → audio ignoré jusqu'à fin de réponse |
| Barge-in voulu (VAD détecte voix pendant réponse Iris) | Couper audio + reprendre écoute (à implémenter en V2) |
| Double VAD trigger (deux voix simultanées) | Un seul envoi vers Whisper — le plus long des deux |
| Réponse Iris en cours + nouveau micro | Ignorer — attendre fin audio |
| Inactivité > 3 min à plusieurs | "Vous êtes encore là ?" puis timeout 30s |

### 3.4 Identifiant de session partagé

Pour partager une session entre plusieurs appareils :
- La session est identifiée par `session_id` (ex. `audio_1717350000000`)
- L'historique de conversation est stocké côté serveur (Redis, clé `iris:session:<id>`)
- Chaque appareil qui rejoint la session récupère l'historique complet
- TTL de session : 2 heures d'inactivité → nettoyage automatique

**Statut actuel** : l'historique est côté client (JS array). La migration vers Redis est une tâche V2.

### 3.5 Interface multi-participants

- Le transcript affiché (`#afTranscript`) montre tous les tours de parole dans l'ordre chronologique
- Le compteur de participants est visible dans l'en-tête (`#afParticipantCount`, à ajouter)
- Lorsqu'un participant rejoint ou quitte, un toast discret l'indique
- Le bouton raccrocher met fin à la session pour tous les participants sur cet appareil

---

## 4. Architecture technique

### 4.1 Pipeline actuel (V1 — en production)

```
getUserMedia({ echoCancellation, noiseSuppression, autoGainControl })
    ↓
AudioContext ScriptProcessor(2048)
    ↓ RMS > 0.018 → start MediaRecorder
    ↓ RMS < 0.018 pendant 700ms → stop MediaRecorder
    ↓
POST /api/visio/transcribe → Whisper-1 (fr)
    ↓
POST /api/visio/chat → GPT-4o-mini (max_tokens=45, temp=0.45)
    ↓ historique : JS array _conversationHistory (12 derniers tours)
    ↓
POST /api/visio/tts → OpenAI tts-1, voix nova
    ↓
new Audio(blob).play() → navigateur
```

**Latence mesurée** : 1750–2400ms par tour

### 4.2 Variables d'environnement

| Variable | Valeur par défaut | Description |
|---|---|---|
| `OPENAI_API_KEY` | obligatoire | Clé OpenAI pour Whisper, LLM, TTS |
| `IRIS_VOICE` | `nova` | Voix TTS (nova, alloy, shimmer, coral) |
| `IRIS_TTS_MODEL` | `tts-1` | Modèle TTS (tts-1 = vitesse, tts-1-hd = qualité) |
| `IRIS_LLM_MODEL` | `gpt-4o-mini` | Modèle LLM |
| `IRIS_MAX_TOKENS` | `45` | Tokens max par réponse |
| `IRIS_TEMPERATURE` | `0.45` | Température LLM |
| `VAD_SILENCE_MS` | `700` | Silence avant déclenchement STT (ms) |

### 4.3 Métriques loggées (F12 Console)

```
[INFO][simli] speech_end_ms              durée de la phrase utilisateur (ms)
[INFO][simli] vad_whisper_ms             STT Whisper (ms)
[INFO][simli] llm_done                   LLM response (ms)
[INFO][simli] tts_done                   TTS generation (ms)
[INFO][simli] time_to_first_audio_ms     LLM + TTS total (ms)
[INFO][simli] turn_total_from_silence_ms total depuis fin de parole → audio joué
[INFO][simli] total_latency_ms           total depuis début _irisReply → fin audio
```

### 4.4 Routes backend

| Route | Méthode | Description |
|---|---|---|
| `/api/visio/transcribe` | POST | STT Whisper-1 (audio/webm → texte) |
| `/api/visio/chat` | POST | LLM GPT-4o-mini (texte → texte) |
| `/api/visio/tts` | POST | TTS OpenAI (texte → audio/mpeg) |
| `/simli` | GET | Page Iris Audio (simli.html) |

---

## 5. Trajectoire d'évolution

### Phase 1 — Actuelle (en production)

Pipeline séquentiel STT → LLM → TTS. Latence ~1750–2400ms. Historique côté client.

### Phase 2 — Streaming TTS (gain ~300–400ms)

LLM en stream → dès 30 tokens reçus → démarrer TTS sur ce chunk → jouer pendant que le reste génère.  
Latence cible : ~1200ms. Complexité : moyenne.

### Phase 3 — OpenAI Realtime API (latence <600ms)

WebSocket Realtime : audio input streaming → STT simultané → LLM stream → TTS chunk par chunk.  
Barge-in natif. Historique côté serveur. Latence cible : ~300–600ms.  
Complexité : élevée (refonte pipeline). Coût : ~0.06$/min.

### Phase 4 — Multi-participants serveur

Session partagée Redis. Plusieurs appareils sur le même `session_id`. Diarisation optionnelle.

---

## 6. Ce qui change par rapport à l'ancien cahier des charges "Visio"

| Avant (Visio) | Maintenant (Iris Audio) |
|---|---|
| Avatar Tavus / Daily.js | Supprimé — orbe futuriste à la place |
| Caméra obligatoire | Supprimée — micro uniquement |
| Lip-sync | Supprimé |
| Lancement via `/api/call` | Supprimé |
| ElevenLabs TTS temps réel | Remplacé par OpenAI tts-1 |
| "Lancer la visio Iris" | "Lancer Iris Audio" |
| Bouton 📹 | Bouton 🔊 |
| WebRTC Daily | Aucune dépendance réseau externe |
| Historique Daily | Historique JS local (_conversationHistory) |

ElevenLabs reste actif pour les **épisodes narratifs / vidéos Domina** uniquement.  
Le code Daily/Tavus/Simli est conservé dans simli.html avec commentaires `/* [AUDIO-FIRST] */` pour réactivation future si besoin.

---

## 7. Limites non franchissables

1. Iris ne déclenche jamais d'action engageante sans confirmation explicite.
2. Iris ne stocke aucune donnée sensible (mots de passe, codes bancaires).
3. Iris ne se présente jamais comme un humain.
4. Iris ne peut pas appeler les secours.
5. Aucun SMS, email, appel entre 22h et 7h sauf urgence vitale déclarée.
6. Le quota voix est vérifié avant chaque session — blocage propre si dépassé.
7. Aucun déploiement Cloud Run sans validation explicite de Ludovic.
8. Aucune clé API dans le code source ou GitHub.

---

*Ce document est la référence active pour toute évolution du parcours Iris Audio.*  
*Mettre à jour ce fichier avant toute modification structurelle du pipeline ou de l'interface.*
