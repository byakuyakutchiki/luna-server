# Clarification Objective 010 — Ludovic (26 mai 2026)

**Date** : 2026-05-26
**Feedback** : Ludovic (fondateur)
**Objectif** : 010 — Historique intelligent + mémoire Luna
**Précision** : Titrage automatique intelligent + recherche dans l'historique

---

## Problème observé

Le menu historique existe, mais les conversations gardent des titres génériques :

```
❌ "Nouvelle conversation"  ← Impossible de savoir de quoi on parlait
❌ "Conversation du 25 mai"  ← Inutile, aucun contexte
```

**Impact** : L'historique existe mais n'est pas exploitable.

---

## Attendu — 2 améliorations prioritaires

### 1. Titrage automatique intelligent

**Objectif** : Chaque conversation doit avoir un titre **significatif** qui décrit le sujet réel.

**Exemples attendus** :
```
✅ "Voix Luna instable"
✅ "Objectif 010 — historique"
✅ "Documents — porte-documents"
✅ "Connexion bouton mobile"
✅ "Mémoire Luna et personnalité"
✅ "Réglages exploitant APK"
```

**Pas accepté** :
```
❌ "Nouvelle conversation"
❌ "Conversation du 25 mai"
❌ "..."  (ellipses)
```

**Timing** :
- Titrage peut se faire au 1er message ou après 2-3 messages
- Le titre doit s'afficher **immédiatement** dans la liste historique
- Pas d'attente utilisateur (générer en arrière-plan si besoin)

**Responsabilité** :
- **Claude** : Vérifier que la génération de titre **existe vraiment** côté serveur
  - Y a-t-il déjà un endpoint qui génère des titres ?
  - Pourquoi le titre "Nouvelle conversation" s'affiche si une génération existe ?
  - Proposer une correction : où générer le titre (serveur ou client) ?

- **Kimi** : Définir les **règles de titrage humain**
  - Quels mots-clés extraire des premiers messages ?
  - Format du titre (sujet ? sujet+détail ?)
  - Longueur max (5-10 mots)
  - Exemples de bonnes transformations

- **DeepSeek** : Implémenter la **génération de titre côté frontend**
  - Après 1-2 messages, extraire mots-clés du premier message utilisateur
  - Construire le titre selon les règles Kimi
  - Mettre à jour l'item conversation dans la liste

---

### 2. Recherche dans l'historique

**Objectif** : Retrouver une conversation passée par mot-clé.

**Fonctionnalité attendue** :
```
┌──────────────────────────────┐
│ 🔍 Rechercher...              │ ← Barre de recherche
├──────────────────────────────┤
│ [Voix Luna et OpenAI]        │  Filtrée en temps réel
│ [Documents — porte-documents] │  (pendant qu'on tape)
│ [Réglages exploitant APK]    │
│ (autres non matching)        │
└──────────────────────────────┘
```

**Types de recherche** :
1. **Par titre** : "Voix" → affiche "Voix Luna et OpenAI"
2. **Par mot dans messages** : "OpenAI" → affiche conversations contenant ce mot
3. **Par sujet/tag** : "voix", "documents", "APK", "objectif" → recherche intelligente

**Timing** :
- Recherche en temps réel (debounce 200ms)
- Affiche résultats > 70% match
- Liste par pertinence (titre matche mieux que contenu)

**Responsabilité** :
- **DeepSeek** : Proposer logique recherche **locale vs serveur**
  - Recherche locale : rapide mais limité (localStorage)
  - Recherche serveur : complet mais lent
  - Hybrid : local d'abord, serveur si besoin

- **Claude** : Vérifier stockage serveur
  - Messages sont-ils indexables ?
  - Faut-il créer un index de recherche ?
  - Endpoint `/api/chat/search` ou `/api/chat/conversations/search` ?

- **Kimi** : Texte et UX recherche
  - "Rechercher..." (placeholder)
  - "Aucune conversation trouvée" (vide)
  - Suggestion tags ("voix", "documents", "APK")

- **Cursor** : Intégrer barre recherche dans le panneau
  - Position : en haut du panneau, sous "Conversations"
  - Responsive : pas de débord sur mobile
  - Clavier virtuel : pas de cachage

---

## Règles de non-régression

✅ **À faire** :
- Garder l'historique existant 100% intact
- Ajouter titrage et recherche **par-dessus** les structures existantes
- Pas de suppression ou modification de conversations anciennes
- Fallback "Nouvelle conversation du DD/MM" si titre échoue

❌ **À éviter** :
- Refondre tout le stockage conversations
- Changer le format des messages
- Migrer toutes les conversations à nouveau titre
- Casser le chat existant pendant l'implémentation

---

## Décisions d'architecture proposées

### Où générer le titre ?

**Option A** — Serveur (recommandé pour qualité)
```
Client envoie message → Serveur génère titre via LLM ou heuristique
Avantage : titre cohérent, qualité LLM Claude/GPT
Inconvénient : latence, appel API supplémentaire
```

**Option B** — Client local (recommandé pour rapidité)
```
Client reçoit message → Extrait mots-clés localement → Construit titre
Avantage : instantané, pas d'appel API
Inconvénient : qualité limitée, heuristique basique
```

**Hybride recommandé** :
- **Étape 1** (immédiate) : Client génère titre local basique
- **Étape 2** (background) : Serveur affine avec LLM
- **Étape 3** : Client reçoit titre amélioré et met à jour liste

---

### Où stocker les titres ?

```
Redis : titre + conversation_id
  → Rapide, mais volatile (perdu si restart)

Base de données durable :
  → Persistant, requêtes complexes possibles

localStorage (client) :
  → Localisé, mais cache local seulement
```

**Recommandation** : Redis pour cache chaud + DB durable pour backup

---

### Où indexer la recherche ?

**Option 1** — Recherche locale (localStorage)
```javascript
// Chercher dans les titres + premier message en mémoire
conversations.filter(c => c.title.includes(query))
```
Rapide, pas de requête serveur.

**Option 2** — Recherche serveur (requête DB)
```
GET /api/chat/conversations/search?q=voix
```
Complet, mais latence réseau.

**Recommandation** : Commencer local, passer serveur si > 100 conversations.

---

## Validation Ludovic attendue

1. ✅ Une conversation ne reste **jamais** "Nouvelle conversation" après quelques messages
2. ✅ Titres sont **intelligibles** (ex: "Voix Luna instable", pas "a b c d")
3. ✅ Recherche retrouve conversation par mot-clé (tapez "voix" → affiche toutes conversations voix)
4. ✅ Pas de régression : chat existant fonctionne toujours
5. ✅ Mobile responsive : barre recherche visible sans débord

---

## Missions mises à jour par agent

### 🔵 Claude — Audit + décisions backend

**Nouvelles questions** :
1. Y a-t-il déjà une génération de titre côté serveur ?
   - Chercher dans `luna_web.py` : fonction `generate_title()` ou similaire
   - Si oui, pourquoi n'est-elle pas appliquée ?
   - Si non, où créer cette fonction ?

2. Où stocker le titre ? (Redis + DB ?)

3. Faut-il un endpoint de recherche `/api/chat/search` ?

4. Modèle de recherche : local first, puis serveur ?

**Livrables** :
- Rapport : "Titrage existe-t-il aujourd'hui ? Pourquoi pas appliqué ?"
- Proposition : serveur vs client, où générer
- Endpoint `/api/chat/conversations/search` (si nécessaire)

---

### 🟠 DeepSeek — Heuristique titrage + recherche locale

**Tâches** :
1. Implémenter heuristique titrage **local** (1-5s après 1er message)
   - Extraire mots-clés du message utilisateur
   - Construire titre court (5-10 mots)
   - Mettre à jour l'item conversation en temps réel

2. Implémenter recherche **locale** sur localStorage
   - Filter conversations.filter() sur title + premier message
   - Debounce 200ms
   - Afficher résultats matching > 70%

3. Préparer pour recherche serveur (ne pas l'implémenter, juste architecture)

**Livrables** :
- Code titrage local + recherche
- Tests : "Voix" trouve "Voix Luna instable"
- Performance : recherche < 100ms

---

### 🟢 Kimi — Règles titrage humain + UX recherche

**Tâches** :
1. Définir règles titrage basé sur contexte :
   - "Voix" + "instable" → "Voix Luna instable"
   - "Objectif" + "010" → "Objectif 010 — historique"
   - "Bouton" + "Connexion" → "Connexion bouton mobile"

2. Proposer heuristique mots-clés
   - Top 3-4 mots importants du 1er message
   - Éliminer stop-words ("comment", "pourquoi", "peux-tu")
   - Capitaliser proprement

3. Texte UX recherche
   - Placeholder : "Rechercher conversation..."
   - Vide : "Aucune conversation trouvée"
   - Tags suggestions : "Essayez : #voix #documents #APK"

**Livrables** :
- Règles titrage + exemples
- Heuristique extraction mots-clés
- Textes et UI phrases

---

### 🟡 Cursor — Barre recherche mobile responsive

**Tâches** :
1. Intégrer barre recherche **en haut du panneau**
   ```
   ┌─────────────────────┐
   │ ☰  Conversations   │
   ├─────────────────────┤
   │ 🔍 Rechercher...    │  ← NEW
   ├─────────────────────┤
   │ [Conversation 1]   │
   │ [Conversation 2]   │
   └─────────────────────┘
   ```

2. Responsive mobile (<400px)
   - Pas de débord
   - Clavier virtuel ne doit pas cacher
   - Touch-friendly (au moins 44px haute)

3. Desktop (>768px)
   - Peut rester visible ou dans le header
   - Pas de changement brusque de layout

4. UX interactions
   - Clearable (X button après typing)
   - Focus automatique quand tape
   - Debounce résultats (pas de flicker)

**Livrables** :
- Code barre recherche
- CSS responsive (<320px, 320-480px, 480-768px, 768px+)
- Interactions fluides (pas de lag)

---

## Timeline mis à jour

| Étape | Responsable | Durée | Dépend de |
|---|---|---|---|
| Audit titrage + recherche | Claude | 30min | — |
| Heuristique titrage local | DeepSeek | 1h | Claude architecture |
| Règles titrage Kimi | Kimi | 30min | — |
| Barre recherche + CSS | Cursor | 1h | DeepSeek structure |
| Recherche locale complète | DeepSeek | 1h | Cursor UI |
| Tests intégration | Tous | 30min | — |
| Validation Ludovic | Ludovic | 15min | — |
| **Total** | **—** | **~4h30** | **—** |

---

## Critères d'acceptation final

✅ **Au lancement** :
- [ ] Aucune conversation affichée "Nouvelle conversation" après 1-2 messages
- [ ] Titres sont lisibles et décrivent le sujet réel
- [ ] Barre recherche présente dans le panneau
- [ ] Recherche par mot-clé fonctionne (locale)
- [ ] Pas de régression chat existant
- [ ] Responsive mobile OK

✅ **Après déploiement** :
- [ ] Ludovic peut retrouver une conversation en tapant "voix"
- [ ] Les anciens titres "Nouvelle conversation" restent (no migration)
- [ ] Nouvelles conversations ont titres automatiques
- [ ] Performance : recherche < 100ms

---

## Dépendances

- ✅ Menu trois traits existant (Phase 1 Objective 010)
- ✅ Stockage conversations existant
- ⏳ Architecture titrage (Claude)
- ⏳ Heuristique local (DeepSeek)

---

## Prochains pas immédiats

1. Claude lit précision Ludovic → audit titrage serveur
2. DeepSeek commence heuristique titrage
3. Kimi définit règles mots-clés + titrage
4. Cursor intègre barre recherche CSS
5. Intégration et tests

---

**Status** : 🔄 Clarification appliquée. Nouvelles missions assignées.
