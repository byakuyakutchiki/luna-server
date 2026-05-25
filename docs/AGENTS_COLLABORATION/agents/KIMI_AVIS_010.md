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
Documents — porte-documents
Réglages exploitant
Objectif 010 — mémoire Luna
Configurer les quotas
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
