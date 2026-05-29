# Objectif 013 — Voix / Visio / Identité Utilisateur

**Statut** : ouvert — architecture analysée par Claude  
**Priorité** : haute  
**Lead technique** : Claude  
**Date ouverture** : 2026-05-29  

---

## Problème

1. La voix Simli/ElevenLabs n'est pas féminine crédible en français (voix par défaut = Rachel, anglaise).
2. Luna doit reconnaître que l'utilisateur est Ludovic.
3. Luna doit pouvoir répondre à "tu me vois ?", "est-ce que je lève la main ?".
4. Tests économes — pas de boucles longues Simli / ElevenLabs / Twilio.
5. Aucun déploiement sans validation Ludovic.

---

## Architecture actuelle (état réel — analysé luna_web.py)

```
Utilisateur (micro/caméra navigateur)
        ↓
    Simli SDK (côté client)
        ↓  [pipeline interne Simli]
    STT → LLM (gpt-4o-mini) → TTS (ElevenLabs si clé présente)
        ↓
    Avatar vidéo (SIMLI_FACE_ID)
        ↓
    Réponse audio/vidéo → navigateur/WebView
```

**Ce qui est déjà câblé :**
- `_start_simli_visio()` — `luna_web.py:6827`
- ElevenLabs déjà branché si `ELEVENLABS_API_KEY` présent — `luna_web.py:6892-6895`
- Identité : `subscriber_name` injecté dans system prompt via `_tenant_subscriber_first_name()` — `luna_web.py:6585`
- Vision caméra : mention dans le french_prefix system prompt — `luna_web.py:6858-6863` (`[Vision caméra] ...`)
- Cartesia prioritaire sur ElevenLabs si `CARTESIA_API_KEY` présent — `luna_web.py:6889-6895`

---

## Ce qui manque / ce qu'il faut corriger

### 1. Voix française féminine (impact immédiat, risque faible)

**Problème** : `ELEVENLABS_VOICE_ID` non défini → fallback `21m00Tcm4TlvDq8ikWAM` (Rachel, anglaise).  
**Fichier** : `luna_web.py:6894`  
**Correction** : ajouter `ELEVENLABS_VOICE_ID=<voix_FR_feminine>` dans `.env` local.

Voix ElevenLabs françaises recommandées (à valider par Ludovic) :
| ID | Nom | Note |
|---|---|---|
| `XB0fDUnXU5powFXDhCwa` | Charlotte | Multilingue, très bien en FR |
| `cgSgspJ2msm6clMCkdW9` | Jessica | Douce, professionnelle |
| `Xb7hH8MSUJpSbSDYk0k2` | Alice | Française native |

**À faire : Ludovic choisit la voix (test ElevenLabs gratuit possible sur le site).**

### 2. Identité Ludovic (déjà fonctionnel si profil rempli)

`subscriber_name` vient de `profile.first_name` (base de données tenant).  
Si le profil de Ludovic est `first_name = "Ludovic"`, Luna l'appellera par son prénom.  
**Vérification** : `/api/profile` → champ `first_name`.  
Aucune modification de code nécessaire.

### 3. Vision caméra (placeholder — non implémenté côté pipeline)

Le system prompt dit :  
> "Quand tu reçois un message `[Vision caméra] ...`, c'est une description automatique de l'environnement visuel."

Mais il n'existe pas de pipeline qui envoie réellement une frame caméra à un modèle de vision.  
**Pour "tu me vois ?"** : Simli voit la caméra côté SDK client (WebRTC), mais Luna (LLM) n'a pas accès aux frames.

**Option minimale (sans dev lourd)** : Ajouter dans le system prompt que Luna peut répondre honnêtement "Je te vois dans notre conversation vidéo" ou "Je vois que tu lèves la main" si le SDK Simli transmet un signal de présence.

**Option complète (dev)** : Endpoint `POST /api/vision/frame` → envoi d'une frame base64 → `gpt-4o-vision` → description → injectée dans le prochain tour Simli. Non prioritaire pour Objectif 013.

---

## Plan d'intégration minimal (sans casser l'existant)

| Étape | Action | Fichier | Risque |
|---|---|---|---|
| 1 | Ajouter `ELEVENLABS_VOICE_ID` dans `.env` local | `.env` | Nul |
| 2 | Vérifier `profile.first_name = "Ludovic"` dans la DB | `/api/profile` | Nul |
| 3 | Tester localement avec `BASE_URL=https://vbox.tailede9d6.ts.net` | — | Faible |
| 4 | Valider la voix et l'identité avec Ludovic | — | — |
| 5 | Déploiement Cloud Run uniquement après validation | — | Moyen |

---

## Garde-fous ABSOLUS

- **Twilio** : aucun SMS, aucun appel, aucun test Twilio dans cet objectif. Risque de consommer le crédit rechargé.
- **ElevenLabs** : test court uniquement (< 30 secondes). Ne pas lancer de longues sessions.
- **Simli** : ne pas boucler les appels `/auto/start/configurable`. Une session = un test.
- **Clé ElevenLabs** : ne jamais committer. Elle est dans `.env` local (non versionnée).
- **Déploiement Cloud Run** : interdit sans validation Ludovic.

---

## Répartition des rôles

| Agent | Tâche |
|---|---|
| **Claude** | Architecture (ce document) + intégration `ELEVENLABS_VOICE_ID` si Ludovic valide la voix |
| **Kimi** | Choisir la meilleure voix féminine ElevenLabs FR + wording assistante visio |
| **DeepSeek** | Audit flux micro→STT→LLM→TTS→avatar + risques coût + test plan économe |

---

## Livrables

1. ✅ Claude : architecture + fichiers/endpoints concernés (ce document)
2. Kimi : recommandation voix + wording
3. DeepSeek : audit risques + plan de test
4. Ludovic valide la voix choisie
5. Ajout `ELEVENLABS_VOICE_ID` dans `.env`
6. Test local court
7. Déploiement si validé
