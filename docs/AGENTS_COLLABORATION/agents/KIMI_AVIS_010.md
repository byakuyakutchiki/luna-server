# Avis Kimi — Objectif 010 Historique intelligent + mémoire Luna

Agent : Kimi Code CLI (kimi-k2.6)
Mission : UX conversationnelle, titrage automatique, mémoire non intrusive
Date : 2026-05-25
Branche : `kimi/objectif-010-historique-memoire`

---

## 1. Règles de titrage automatique

### Principe

Le titre d'une conversation doit résumer le sujet en 3 à 6 mots maximum.
Il doit être compréhensible en un coup d'œil dans la liste des conversations.

### Règles de génération

| Règle | Exemple | Contre-exemple |
|---|---|---|
| Toujours commencer par un sujet concret | "Documents — porte-documents" | "Conversation du 25/05" |
| Mentionner l'entité concernée si claire | "Voix Luna et OpenAI" | "Question à propos de ça" |
| Utiliser le verbe à l'infinitif si action | "Configurer les quotas" | "Configuration" |
| Inclure le numéro d'objectif si pertinent | "Objectif 009 — stabilité voix" | "Bug à corriger" |
| Éviter les dates (sauf si seule info) | "Réunion de mardi" | "25/05/2026 14h32" |
| Éviter les pronoms | "Profil de Ludovic" | "Mon profil" |
| Éviter les articles superflus | "Rappels médicaments" | "Les rappels de médicaments" |
| Maximum 40 caractères | "Réglages exploitant" | "Configuration des paramètres pour l'exploitant" |

### Patterns de titrage par type de conversation

| Type de début | Pattern de titre | Exemple |
|---|---|---|
| Question sur une fonctionnalité | `[Fonctionnalité] — [sujet]` | "Voix — problème micro" |
| Demande d'action | `[Action]` | "Envoyer SMS à Marie" |
| Question administrative | `[Domaine] — [sujet]` | "Documents — facture EDF" |
| Discussion technique | `Objectif [N] — [sujet]` | "Objectif 007 — télémétrie" |
| Salutation générale | "Discussion générale" | (fallback) |
| Météo / actualités | `[Service] — [lieu/sujet]` | "Météo — Paris" |
| Rappel / organisation | `[Type] — [objet]` | "Rappel — rendez-vous dentiste" |

### Exemples de titres validés

```
Voix Luna et OpenAI Realtime
Voix Luna instable
Documents — porte-documents
Objectif 010 — mémoire Luna
Objectif 010 — historique
Configurer les quotas
Connexion bouton mobile
Mémoire Luna
Météo — Bordeaux
Envoyer SMS à Marie
Rappel — médicaments 20h
Discussion générale
```

### Exemples de titres invalides (à éviter)

```
Conversation du 25/05/2026          → trop daté, pas de sujet
Salut                                → pas de sujet
Problème                             → trop vague
Comment ça marche ?                  → question, pas sujet
Ma conversation avec Luna            → redondant
Configuration des paramètres         → trop long
```

---

## 2. Textes d'interface

### Menu trois traits (hamburger)

```
☰ Conversations
```

Au clic :
```
┌─────────────────────────────┐
│  ☰ Conversations            │
│                             │
│  + Nouvelle conversation    │
│                             │
│  Aujourd'hui                │
│  • Voix Luna et OpenAI      │ ← active (surlignée)
│  • Documents — porte-docu.  │
│                             │
│  Hier                       │
│  • Configurer les quotas    │
│  • Météo — Bordeaux         │
│                             │
│  Cette semaine              │
│  • Objectif 009 — stabilité │
│  • Rappel — médicaments     │
│                             │
│  [fermer]                   │
└─────────────────────────────┘
```

### Textes du menu

| Élément | Texte | Commentaire |
|---|---|---|
| Titre du menu | "Conversations" | Pas "Historique" (trop technique) |
| Bouton nouvelle | "+ Nouvelle conversation" | Clair, action visible |
| Section aujourd'hui | "Aujourd'hui" | Standard |
| Section hier | "Hier" | Standard |
| Section semaine | "Cette semaine" | Standard |
| Section ancien | "Plus ancien" | Standard |
| Conversation active | Sur fond distinct | Pas de texte supplémentaire |
| Conversation vide | "(vide)" | Si aucun message encore |
| Date format | "12:34" (aujourd'hui) / "hier" / "lun. 12" | Pas de date complète |

### Confirmation nouvelle conversation

```
📝 Nouvelle conversation

Voulez-vous démarrer une nouvelle conversation ?
L'actuelle sera conservée dans l'historique.

[Continuer l'actuelle]  [Nouvelle conversation]
```

### Texte quand Luna reprend une conversation

```
📝 Reprise de la conversation
"Voix Luna et OpenAI Realtime"
Dernière activité : hier à 15:42

Luna se souvient de 12 messages.
```

### Texte quand une conversation est vide

```
Cette conversation est vide.
Envoyez un message pour commencer.
```

### Texte quand l'historique est vide

```
Aucune conversation pour l'instant.
Envoyez un message à Luna pour créer la première.
```

---

## 3. Comment Luna se souvient sans réciter

### Principe fondamental

> **Luna sait, mais elle ne dit pas qu'elle sait — sauf si c'est utile.**

### Ce que Luna NE doit PAS faire

```
❌ "Je me souviens que tu m'as demandé hier..."
❌ "D'après notre conversation du 25 mai..."
❌ "Comme je te l'ai déjà dit..."
❌ "Je sais que tu habites à Bordeaux et que..."
```

### Ce que Luna DOIT faire

```
✅ Utiliser silencieusement la mémoire pour personnaliser
✅ Mentionner le contexte seulement si la question l'exige
✅ Répondre directement, sans préambule mémoriel
```

### Exemples concrets

| Situation | Mauvais (récite) | Bon (utilise discrètement) |
|---|---|---|
| Ludovic demande la météo | "Je me souviens que tu habites à Bordeaux, donc la météo à Bordeaux est..." | "À Bordeaux, il fait 18°C et ensoleillé." |
| Ludovic demande un rappel | "D'après notre conversation de mardi, tu voulais un rappel pour tes médicaments." | "Rappel médicaments créé pour 20h." |
| Ludovic reprend un sujet | "Comme je te l'ai dit hier dans la conversation 'Voix Luna', le problème vient d'OpenAI." | "Le problème de voix vient du quota OpenAI." |
| Ludovic demande qui il est | "Tu es Ludovic Saint-Louis, fondateur de YAWatch, né le..." | "Tu es Ludovic, fondateur de YAWatch." |

### Règles d'or de la mémoire discrète

1. **Jamais de référence temporelle inutile** : pas "hier", "la dernière fois", "dans notre conversation précédente"
2. **Jamais de liste de souvenirs** : Luna ne fait pas l'inventaire de ce qu'elle sait
3. **Jamais de "je me souviens"** : formulation narcissique, centrée sur Luna au lieu de l'utilisateur
4. **Contexte implicite** : la mémoire sert à affiner la réponse, pas à la préfacer

---

## 4. Distinction : mémoire utilisateur / projet / conversation

### Tableau des trois mémoires

| Type | Contenu | Durée de vie | Exemples | Usage |
|---|---|---|---|---|
| **Mémoire utilisateur** | Profil, préférences, habitudes | Permanent | Nom, ville, contacts de confiance, médicaments, rendez-vous réguliers | Personnaliser silencieusement chaque réponse |
| **Mémoire projet** | Architecture, objectifs, décisions | Mis à jour à chaque objectif | Objectifs 001-009 validés, stack technique, garde-fous sécurité | Répondre aux questions sur Luna elle-même |
| **Mémoire conversation** | Messages de la session active | Durée de la conversation + reprise | Messages échangés dans cette conversation | Maintenir le contexte du dialogue en cours |

### Ce qui va dans chaque mémoire

**Mémoire utilisateur (Redis, persistant)**
```
- Prénom : Ludovic
- Ville : Bordeaux
- Plan : fondateur
- Contacts de confiance : [Marie, Jean]
- Rappels médicaments : [8h, 13h, 20h]
- Dernière localisation : Bordeaux centre
```

**Mémoire projet (Redis, mis à jour par Claude)**
```
- Stack : FastAPI + Cloud Run + Redis + OpenAI
- Voix : OpenAI Realtime, gpt-realtime-mini, voix coral
- Objectifs validés : 001-008
- Objectif en cours : 009 (stabilité voix)
- Déploiement : Cloud Run europe-west1
- Secrets : jamais stockés dans la mémoire
```

**Mémoire conversation (localStorage + serveur)**
```
- Conversation ID : conv_20260525_001
- Titre : "Voix Luna et OpenAI Realtime"
- Messages : [msg1, msg2, ...]
- Dernière activité : 2026-05-25 18:47
- Contexte actif : oui
```

### Ce qui ne va JAMAIS dans la mémoire

```
❌ OPENAI_API_KEY
❌ JWT_SECRET_KEY
❌ TWILIO_AUTH_TOKEN
❌ Numéros de carte bancaire
❌ Mots de passe
❌ Contenu de documents privés (sauf résumé anonymisé)
❌ Transcriptions vocales brutes
❌ Audio brut
```

---

## 5. Formulations quand Luna utilise sa mémoire

### Situation : Luna utilise la mémoire utilisateur

**Question :** "Quel temps fait-il ?"
**Mémoire utilisée :** ville = Bordeaux

```
✅ "À Bordeaux, il fait 18°C et ensoleillé."
❌ "Je me souviens que tu habites à Bordeaux. À Bordeaux, il fait..."
```

### Situation : Luna utilise la mémoire projet

**Question :** "Qu'est-ce qui reste à faire sur la voix ?"
**Mémoire utilisée :** objectif en cours = 009 stabilité

```
✅ "La voix fonctionne maintenant. Le point restant est la stabilité :
    Luna coupe parfois en parlant. C'est l'objectif 009 en cours."
❌ "D'après notre projet, l'objectif 009 concerne la stabilité voix.
    Comme je te l'ai dit précédemment..."
```

### Situation : Luna reprend une conversation

**Action :** Ludovic clique sur une conversation passée

```
✅ (Luna reprend le fil naturellement, sans commentaire)

Ludovic : "Tu peux m'aider avec les documents ?"
Luna : "Bien sûr. Tu veux ajouter un document, consulter
        le porte-documents, ou préparer un courrier ?"
```

```
❌ "Je reprends notre conversation 'Documents — porte-documents'
    du 24 mai. Tu m'avais demandé de t'aider avec tes factures."
```

### Situation : Luna résume une conversation passée si demandé

**Question :** "De quoi on parlait hier ?"

```
✅ "On parlait de la stabilité vocale. La voix fonctionne
    maintenant, mais elle coupe parfois en cours de réponse."
```

```
❌ "Dans notre conversation du 24 mai 2026 à 18:47, tu m'as demandé
    de t'aider avec la voix Luna. Je t'ai expliqué que..."
```

---

## 6. Textes pour le bouton Connexion / Déconnexion coupé (UI mobile)

### Problème
Sur téléphone, le bouton `Connexion` / `Déconnexion` est coupé — le `n` est mangé par le bord de l'écran.

### Correction textuelle minimale

Remplacer le texte long par un texte court + icône :

```
Avant (coupé) :
[Connexion]  ou  [Déconnexion]

Après (lisible) :
[🔑 Se connecter]  ou  [🚪 Quitter]
```

Ou plus sobre :
```
[Entrer]  ou  [Sortir]
```

### Règles pour la correction

1. **Maximum 8 caractères** sur petit écran (< 360px)
2. **Icône + texte court** : l'icône reste visible même si le texte est tronqué
3. **Ne pas changer le placement** du bouton (garder le header)
4. **Safe-area** : ajouter `padding-right: env(safe-area-inset-right)`

### Textes alternatifs validés

| Contexte | Texte court | Icône |
|---|---|---|
| Non connecté | "Entrer" | 🔑 |
| Non connecté | "Se connecter" | 🔑 (si place) |
| Connecté | "Sortir" | 🚪 |
| Connecté | "Quitter" | 🚪 |
| Fondateur connecté | "👑" | (icône seule) |

---

## 8. Diagnostic technique et corrections proposées

### Ce qui existe déjà (audit du code)

| Fonctionnalité | État | Localisation |
|---|---|---|
| Génération de titre serveur | ✅ Existe | `luna_web.py` lignes 5638 et 6302 — appel `gpt-4o-mini` avec timeout 5s |
| Fallback titre si OpenAI échoue | ⚠️ Partiel | `req.message[:40]` — peu informatif si le message est court |
| Recherche dans l'historique | ✅ Existe | `static/index.html` lignes 6310–6314 — filtre client sur `title` + `preview` |
| Affichage liste avec groupes | ✅ Existe | `renderConvList()` — groupes par date, actions renommer/vider/supprimer |
| Stockage serveur | ✅ Existe | Redis — `summary` = titre, `messages` = liste JSON |
| Stockage client | ✅ Existe | localStorage — `luna_conversations_meta`, `luna_conv_msgs_<id>` |

### Bug identifié : "Nouvelle conversation" qui persiste

**Cause racine** : Le titre est généré côté serveur par OpenAI (`gpt-4o-mini`). Si l'appel échoue (timeout, quota, erreur réseau), le fallback `req.message[:40]` est appliqué, mais :

1. Si le message est très court ("salut", "ok"), le titre reste vide ou non significatif.
2. Si la réponse au client ne contient pas le champ `auto_title` (streaming interrompu, erreur SSE), le `localStorage` conserve `title: ""`.
3. Au rechargement de page, `loadConversationList()` charge les conversations depuis le serveur via `GET /api/conversations` qui renvoie `c.summary or ""`. Si `summary` est vide, le titre reste vide → `"Nouvelle conversation"`.

**Code problématique** (client) :
```javascript
// static/index.html ligne 6331
title.textContent = conv.title || "Nouvelle conversation";

// static/index.html ligne 4380 — le titre n'est mis à jour QUE si auto_title est présent
if (data.auto_title) { _jsonConv.title = data.auto_title; }
```

**Code problématique** (serveur) :
```python
# luna_web.py ligne 5643 — dépend d'OpenAI avec timeout 5s
if not (meta or {}).get("summary"):
    title_resp = await loop.run_in_executor(None, lambda: openai_client.chat.completions.create(...))
    # Si échec : fallback req.message[:40] — pas assez robuste
```

### Corrections proposées

#### A. Côté client — fallback local immédiat

Si le serveur ne renvoie pas `auto_title` dans les 3 secondes après la réponse Luna, générer un titre local à partir du premier message utilisateur :

```javascript
function generateLocalTitle(firstMessage) {
  if (!firstMessage) return "Discussion";
  var m = firstMessage.trim();
  // Extraire les mots-clés techniques connus
  var keywords = {
    "voix": "Voix Luna", "voice": "Voix Luna", "micro": "Voix Luna",
    "objectif": "Objectif", "doc": "Documents", "document": "Documents",
    "apk": "APK", "android": "APK", "connexion": "Connexion",
    "mémoire": "Mémoire Luna", "historique": "Historique",
    "météo": "Météo", "sms": "SMS", "rappel": "Rappel"
  };
  for (var kw in keywords) {
    if (m.toLowerCase().indexOf(kw) >= 0) return keywords[kw];
  }
  // Fallback : premiers 30 caractères du message
  return m.substring(0, 30) + (m.length > 30 ? "..." : "");
}
```

#### B. Côté serveur — améliorer le prompt et le fallback

Remplacer le prompt actuel par celui défini dans la section 1 de ce document :

```python
system_prompt = (
    "Tu génères un titre court (3-6 mots max, 40 caractères max) pour une conversation. "
    "Règles : sujet concret en premier, verbe à l'infinitif si action, "
    "numéro d'objectif si pertinent, pas de dates, pas de pronoms, pas d'articles superflus. "
    "Pas de guillemets, pas de ponctuation finale."
)
```

Améliorer le fallback quand OpenAI échoue :
```python
if not auto_title or len(auto_title) < 3:
    auto_title = _generate_fallback_title(req_message)

def _generate_fallback_title(msg: str) -> str:
    if not msg or len(msg.strip()) < 3:
        return "Discussion"
    # Extraction de mots-clés
    lower = msg.lower()
    keywords = {
        "voix": "Voix Luna", "voice": "Voix Luna", "micro": "Voix Luna",
        "objectif": "Objectif", "doc": "Documents", "document": "Documents",
        "apk": "APK", "android": "APK", "connexion": "Connexion",
        "mémoire": "Mémoire Luna", "historique": "Historique",
    }
    for kw, title in keywords.items():
        if kw in lower:
            return title
    return msg.strip()[:40] + ("..." if len(msg) > 40 else "")
```

#### C. Synchronisation — forcer le titre au chargement

Dans `loadConversationList()`, si une conversation a un titre vide mais contient des messages, déclencher une génération de titre côté serveur via un endpoint dédié, ou utiliser le fallback client :

```javascript
// Après loadConversationList() — vérifier les titres vides
conversationsMeta.forEach(function(conv) {
  if (!conv.title && conv.message_count > 0) {
    var msgs = JSON.parse(localStorage.getItem("luna_conv_msgs_" + conv.id) || "[]");
    if (msgs.length > 0) {
      var firstUser = msgs.find(function(m) { return m.role === "user"; });
      conv.title = generateLocalTitle(firstUser ? firstUser.content : "");
    }
  }
});
saveConvMeta(); renderConvList();
```

#### D. Recherche — vérifier la couverture

La recherche existe déjà (filtre sur `title + preview`). Vérifier qu'elle couvre bien :
- ✅ Mots du titre
- ✅ Mots dans les messages (via `preview`)
- ⚠️ Objectifs — le preview contient-il "Objectif 010" ? Oui si Luna l'a mentionné.
- ⚠️ Sujets techniques — même réponse.

**Aucune action requise sur la recherche** — elle fonctionne déjà. S'il faut l'améliorer, DeepSeek peut proposer une indexation serveur.

### Rôles validés par Ludovic

| Rôle | Mission | Action |
|---|---|---|
| **Claude** | Vérifier la génération côté serveur et corriger le fallback | Modifier `luna_web.py` lignes 5638 et 6302 + ajouter `_generate_fallback_title` |
| **DeepSeek** | Proposer la logique de recherche avancée | Si besoin d'indexation serveur (recherche dans tous les messages, pas juste preview) |
| **Kimi** | Définir les règles de titrage humain | ✅ Ce document — sections 1, 2, 3, 5, 8 |
| **Cursor** | Intégrer la barre de recherche dans le panneau gauche | La barre existe déjà (`convSearch` ligne 1654). Vérifier le rendu mobile. |

### Validation Ludovic

- [ ] Une conversation ne reste plus nommée "Nouvelle conversation" après le premier échange.
- [ ] Le titre reflète le sujet réel (ex: "Voix Luna instable", "Objectif 010 — historique").
- [ ] La recherche retrouve une conversation par mot-clé technique ("voix", "documents", "APK").
- [ ] L'interface mobile reste utilisable (barre de recherche visible, titres tronqués proprement).

---

## 7. Synthèse Kimi pour l'objectif 010

### Livrables

1. **8 règles de titrage** automatique (sujet concret, verbe infinitif, max 40 caractères...)
2. **8 patterns de titrage** par type de conversation
3. **10 exemples validés** + 5 exemples invalides
4. **Textes d'interface** complets (menu, confirmations, sections, dates)
5. **4 règles d'or** de la mémoire discrète (jamais "je me souviens", jamais référence temporelle inutile...)
6. **3 tableaux de mémoire** (utilisateur, projet, conversation) avec contenus et durées
7. **5 formulations validées** quand Luna utilise sa mémoire
8. **Correction textuelle** pour le bouton Connexion/Déconnexion coupé

### Message à l'équipe

> Objectif 010 = donner à Luna une mémoire digne d'un compagnon, pas d'un carnet de notes. Elle sait, elle utilise, elle ne récite jamais.

---

*Document produit par Kimi Code CLI pour l'objectif 010 — branche `kimi/objectif-010-historique-memoire`*
