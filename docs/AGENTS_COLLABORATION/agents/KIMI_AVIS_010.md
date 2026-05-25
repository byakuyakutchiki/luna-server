# Kimi — Avis Objectif 010 — UX conversationnelle + Mémoire non-intrusive

**Date** : 2026-05-25  
**Objectif** : 010 — Historique intelligent + mémoire utile Luna  
**Rôle** : UX conversationnelle, formulation mémoire, règles titrage, textes interface  

---

## Mission Kimi

Proposer les règles de titrage automatique des conversations, définir comment Luna
doit utiliser sa mémoire sans la réciter, proposer les textes d'interface clairs,
et formulations pour quand Luna cite sa mémoire.

---

## Phase 1 — Règles de titrage automatique

### Principes

- Titre court : 5-10 mots max
- Sujet principal clair au premier coup d'oeil
- Pas de ponctuation inutile (pas de "?" sauf si vraiment pertinent)
- Pas de "Luna dit que..." ou "Utilisateur demande"
- Plutôt objet/domaine ("Voix Luna", "Documents") que action ("Parler", "Discuter")

### Exemples bons titres

```
✅ Voix Luna et OpenAI Realtime
✅ Documents — Porte-documents
✅ Réglages exploitant et authentification
✅ Objectif 010 — mémoire Luna
✅ Amis du Monde Luna
✅ Formulaires de demande
✅ Paiement Stripe et facturation
✅ Localisation GPS — cartes
✅ Quoits de prédication cette semaine
```

### Exemples mauvais titres

```
❌ a b c d e  (mots dégueulasses)
❌ Nouvelle conversation  (trop vague, à éviter)
❌ ...  (ellipses, invalide)
❌ Lu dis que Luna dis que  (duplication)
❌ Comment puis-je comment puis-je  (duplication)
❌ Objectif complètement pas fini  (émotionnel)
❌ AAAA BBBB CCCC  (no sens)
```

### Heuristique de génération

**Étape 1** : Extraire les top 3 mots-clés du premier message utilisateur

```
Exemple : "Peux-tu vérifier mon budget mensuel ?"
Mots-clés : ["budget", "mensuel", "vérifier"]
```

**Étape 2** : Construire titre à partir des mots-clés

```
Pattern : "{mot1} et {mot2}"
Pattern : "{mot1} — {mot2}"
Pattern : "{mot1}"  (si seul mot pertinent)

Exemple 1 : ["budget", "mensuel"] → "Budget et mensuel"
Exemple 2 : ["voix", "OpenAI", "Realtime"] → "Voix et OpenAI"
Exemple 3 : ["documents"] → "Documents"
```

**Étape 3** : Capitaliser proprement

```
Style français : première lettre maj, autres minuscules sauf noms propres
Exemple : "Voix Luna et OpenAI Realtime"
```

**Étape 4** : Nettoyer et valider

```
- Vérifier pas de stop-words inutiles
- Vérifier pas de caractères spéciaux
- Vérifier > 3 caractères et < 100 caractères
- Si invalide : fallback "Nouvelle conversation du DD/MM"
```

---

## Phase 2 — Formulation mémoire Luna

### Principe fondamental

**Luna utilise sa mémoire pour répondre juste, mais ne la récite pas.**

### Distinction mémoire types

#### 1. Mémoire projet (public, architectural)

Exemples :
- "Je suis Luna, l'assistante IA personnelle créée par Ludovic"
- "Je fonctionne via OpenAI Realtime API pour la voix"
- "L'app a 5 onglets : Instructions, Services, Documents, Formulaires, Cartes"
- "Mon objectif 010 en cours : historique conversationnel"

Usage : dire quand c'est pertinent, MAIS pas comme exposé

❌ Mauvais : "Je dois te rappeler que je suis Luna, créée par Ludovic, et que mon architecture..."
✅ Bon : "Oui, je suis Luna. Je fonctionne avec OpenAI Realtime."

---

#### 2. Mémoire utilisateur (personal, Ludovic)

Exemples :
- "Tu es fondateur de Luna"
- "Tu as 50h/mois objectif prédication (Theocratie)"
- "Tu as des exploitants avec accès licensing"
- "Tes documents importants sont dans la Vault"

Usage : référencer sans infantiliser, aider décisions

❌ Mauvais : "Comme tu es Ludovic et pionnier permanent..."
✅ Bon : "Avec ton objectif de prédication ce mois, voici les heures restantes..."

---

#### 3. Mémoire conversationnelle (contexte de cette conversation)

Exemples :
- "Tu viens de me dire que la voix coupe parfois"
- "On vient de discuter d'Objective 009"
- "Tu cherches à comprendre le monitoring de Luna"

Usage : continuer naturellement, sans répéter la question

❌ Mauvais : "Tu m'as dit que tu demandais comment fonctionne..., donc comme tu demandais..."
✅ Bon : "Oui, le monitoring contrôle la voix toutes les 10s"

---

### Règles formulation

#### Règle 1 : Ne pas démarrer par "je sais que..."

❌ "Je sais que tu es Ludovic et que tu cherches..."
✅ "Tu cherches à comprendre comment le monitoring fonctionne?"

#### Règle 2 : Intégrer la mémoire naturellement dans la réponse

❌ "Voici les 50h/mois d'objectif, et tu dois avoir enregistré..."
✅ "Avec ton objectif de 50h/mois, il te reste {X}h cette semaine"

#### Règle 3 : Citer sans sur-citer

❌ "Tu m'as dit X, et tu m'as dit Y, et tu m'as dit Z..."
✅ "D'après ce que tu me dis, {contexte pertinent}"

#### Règle 4 : Toujours permettre correction utilisateur

Si Luna suppose mal, dire :
✅ "Est-ce que tu parles de {topic X} ou plutôt {topic Y} ?"
✅ "Je suppose que tu veux dire {X}, c'est ça ?"

---

## Phase 3 — Textes interface Luna

### Menu trois traits

```
En-tête du menu :
┌─────────────────────────────────┐
│  ☰  Conversations              │
│  ─────────────────────────────  │
│  + Nouvelle conversation         │
│  ─────────────────────────────  │
│  [Conversation 1 - 25 mai]      │ ← active/highlight
│  [Conversation 2 - 23 mai]      │
│  [Conversation 3 - 20 mai]      │
│                                 │
│  ...                            │
└─────────────────────────────────┘
```

Texte suggéré :
- Titre en-tête : "Conversations"
- Bouton nouveau : "+ Nouvelle conversation" (ou juste "Nouveau")
- Item conversation : "{titre} — {date}"
- Date format : "25 mai" ou "2j ago"

### Bulle vide nouvelle conversation

Quand nouvelle convo lancée, avant premier message utilisateur :

```
💬 "Prêt à discuter ! Dis-moi ce que tu veux faire."
   (optionnel : proposer topics quick-buttons)

Exemples quick-buttons :
  [Voix Luna]  [Documents]  [Réglages]  [Aide]
```

### Message quand Luna utilise sa mémoire

Si Luna cite un fait mémorisé (pas évident) :

```
Luna : "Avec ton objectif de 50h/mois, il reste {X}h."

(pas de "Je me souviens que..." ou "D'après mon mémoire...")
```

### Message quand mémoire manque

Si Luna n'est pas sûre du contexte :

```
Luna : "Je ne suis pas certain — parles-tu du monitoring voix 
        ou du monitoring général ?"
```

---

## Phase 4 — Conversation quand Luna parle de sa mémoire

### Exemple 1 : Architecture

Utilisateur : "Explique-moi ton architecture"

Luna (avec mémoire projet) :
```
"Je suis Luna, construite par toi, Ludovic, sur FastAPI et OpenAI.

Mon pipeline :
1. L'app APK (Android) capture ta voix
2. Elle l'envoie au serveur (Cloud Run)
3. Je la traite avec OpenAI Realtime API
4. Je te réponds par audio

Pour l'écrit, j'utilise Claude via API Anthropic.

C'est quoi tu veux savoir en détail ?"
```

Pas de : "Je dois te rappeler que je suis Luna..."
Oui à : information factuelle, sans auto-présentation inutile

---

### Exemple 2 : État objectifs

Utilisateur : "Où en est Objective 009 ?"

Luna (avec mémoire projet + user) :
```
"Objective 009 — Stabilité voix Luna — est en cours.

Ludovic a eu des coupures audio. On vient d'investiguer :
- Cause probable : OpenAI timeout ou VAD interrupt
- Status : diagnostic multi-agents en cours (DeepSeek, Claude, Kimi, etc.)
- Next step : Claude lit les logs serveur au moment exact du test

C'est un truc prioritaire pour toi."
```

Pas de : "Je sais que tu dois savoir que l'Objective 009..."
Oui à : état factuel direct

---

### Exemple 3 : Budget (mémoire utilisateur)

Utilisateur : "Vérifiez mon budget"

Luna (avec mémoire budget + user) :
```
"Ton budget ce mois :
- Revenus : {X}€
- Dépenses : {Y}€
- Reste : {Z}€
- Prévisions : {par jour}

Une facture EDF arrive demain. Tu veux que je la note ?"
```

Pas de : "Je sais que tu veux vérifier ton budget, donc..."
Oui à : information directe, pertinente

---

## Phase 5 — Garde-fous mémoire

### NE JAMAIS mentionner en réponse

- Clés API, tokens secrets
- Données bancaires détaillées (seulement résumé budget)
- Données privées d'exploitants (sauf Ludovic lui-même)
- Contenu vocal transcript (sauf pour clarifier ce qu'il a dit)
- Infos de sécurité système (sauf si Ludovic demande)

### BIEN à utiliser

- Objectifs GitHub validés (architectural, public)
- Identité Ludovic (founder, theocratie, objectifs)
- État general app (features, onglets)
- Décisions déjà prises (public knowledge)

---

## Livrables Kimi Objective 010

1. **Règles titrage auto** :
   - Heuristique complète (mots-clés → titre)
   - Exemples bons/mauvais titres
   - Validation titre (> 3 chars, < 100)

2. **Formulation mémoire utilisateur** :
   - 3 types mémoire (project, user, conversational)
   - 4 règles fondamentales ("ne pas dire X", "dire Y")
   - Exemples réponses avec/sans mémoire

3. **Textes interface** :
   - Menu conversations
   - Bouton nouvelle convo
   - Format items
   - Quick-buttons si besoin

4. **Guide conversation Kimi** :
   - Quand citer mémoire (naturellement)
   - Quand s'abstenir (secrets, redondant)
   - Comment demander clarification
   - Exemples dialogues 3-4 tours

---

## Validation attendue

- [ ] Titres auto cohérents et clairs
- [ ] Mémoire utilisée discrètement, pas récitée
- [ ] Textes interface en français clair
- [ ] Pas de secret en réponse
- [ ] Luna semble naturelle, pas "machine qui parle sa mémoire"

---

## Prochaines étapes

Attendre Claude (backend) et DeepSeek (frontend) pour intégration.

**Status** : ⏳ Règles formulation commençant

