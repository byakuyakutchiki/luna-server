# Kimi — Méthode pour Canaliser Iris — Objectif 025

Date : 2026-06-04
Agent : Kimi
Type : réflexion UX / produit / méthode
Niveau : 0 — pas de code, pas de déploiement

---

## Résumé de ma méthode

**La solution n'est pas de demander poliment au LLM de bien se comporter.**

Le LLM (OpenAI Realtime) est entraîné comme assistant conversationnel généraliste. Quand on lui dit "Prépare-moi un tableau", son réflexe naturel est :
1. Dire "Je vais préparer un tableau pour vous" — conversation
2. Oublier d'appeler l'outil — pas d'action
3. Répondre en texte long — pas de rendu visuel

**Ma méthode : superposition de 4 couches de contrôle.**

---

## Couche 1 — Mode explicite obligatoire (Méthode A/B)

### Principe
L'utilisateur DOIT choisir un mode avant de demander quoi que ce soit à Iris. Pas de mode = pas de rendu. Le mode "Discussion" est le seul où Iris peut bavarder librement.

### Pourquoi ça marche
Le mode cadrant le contexte AVANT la demande, le LLM reçoit un prompt ciblé :
```
Mode : Tableau / Graphique
Tu es Iris, secrétaire opérationnelle. Tu structures TOUJOURS les données visuellement.
Tu ne réponds JAMAIS en texte seul.
Outils autorisés : iris_render (data_board, chart, kpi_cards, timeline)
```

### UX proposée
- **5 modes principaux** en barre fixe : 📊 Tableau, 📄 Analyse, 👥 Réunion, ✏️ Rédaction, 💬 Discussion
- **5 modes secondaires** dans un menu déroulant compact : 🔍 Recherche, ⚡ Actions, 🧑‍🤝‍🧑 Équipe, 🗺️ Carte, 🛡️ Conformité
- **Badge mode courant** toujours visible dans le header (couleur violette)
- **Animation subtile** au changement de mode (fade 200ms) pour marquer la transition

### Risque atténué
L'interface peut sembler lourde. Solution :
- Barre compacte (hauteur 36px, chips de 11px)
- Scroll horizontal fluide
- Un seul clic pour changer
- Mode mémorisé par session

---

## Couche 2 — Pré-classification côté serveur (Méthode C affinée)

### Principe
**AVANT** d'envoyer la requête à OpenAI, le serveur analyse la demande utilisateur et prépare le payload.

### Pourquoi c'est la couche critique
Au lieu de laisser le LLM "choisir" l'outil, le serveur détermine :
- Mode = Tableau + demande contient des chiffres → `render_type = chart`
- Mode = Analyse + fichier ZIP uploadé → `render_type = document_insight`
- Mode = Réunion → `render_type = meeting_board`

Le serveur envoie au LLM :
```
L'utilisateur a demandé un graphique.
Tu DOIS appeler iris_render avec :
- render_type = chart
- payload = {title: "...", type: "bar", labels: [...], datasets: [...]}
Ensuite tu dis : "C'est affiché."
```

Le LLM n'a **plus le choix**. Il reçoit l'instruction et l'outil à exécuter.

### Avantage
- Zero aléatoire sur le choix de l'outil
- Temps de réponse divisé par 2 (pas de "réflexion" du LLM)
- Testable unitairement

### Risque atténué
Table d'intents à maintenir. Solution : table simple (10 modes × 5 patterns = 50 règles max), versionnée, extensible.

---

## Couche 3 — Forçage structurel (Méthode D affinée)

### Principe
Pour les actions productives, Iris ne répond pas librement. Elle remplit un formulaire structuré côté serveur.

### Exemple
**Demande :** "Rédige un courrier à mon client pour le retard"

**Serveur :**
1. Détecte mode = Rédaction
2. Prépare payload `document_draft` avec :
   - title: "Courrier — retard de livraison"
   - recipient: "[Nom du client]"
   - body: "[Corps du courrier]"
   - placeholders: ["[Nom du client]", "[Date du retard]", "[Référence commande]"]
3. Envoie à OpenAI : "Appelle iris_render avec ce payload. Dis 'Voici le brouillon, complétez les placeholders.'"

**Résultat :**
- Iris n'a pas "rédigé" — elle a exécuté un template préparé
- Le document apparaît immédiatement
- Les placeholders sont visibles et cliquables
- L'utilisateur modifie, puis valide

### UX proposée
- **Document en direct** : l'utilisateur voit le brouillon se construire mot par mot (stream)
- **Placeholders colorés** : champs manquants en jaune clair, cliquables
- **Bouton Valider** : passe en mode "prêt à envoyer" (action_board)
- **Bouton Modifier** : retourne en mode édition

---

## Couche 4 — Garde-fou fallback (Méthode C timer)

### Principe
Si malgré les 3 couches précédentes le LLM ne déclenche pas l'outil en 1.5 seconde, le serveur injecte lui-même le render.

### Pourquoi on garde cette couche
C'est le filet de sécurité. Elle ne devrait plus se déclencher une fois les couches 1-3 opérationnelles, mais elle sauve l'expérience utilisateur si jamais.

### Paramètre
Timer réduit de 4s → **1.5s** (car le pré-classification a déjà préparé le payload).

---

## Réponse aux 10 questions de Codex

### 1. Fonctionnalités V1 absolues

| # | Fonctionnalité | Mode | Preuve |
|---|---|---|---|
| 1 | Tableau de données | 📊 Tableau | data_board affiché en < 3s |
| 2 | Graphique | 📊 Tableau | chart avec vraies données |
| 3 | Analyse document PDF | 📄 Analyse | document_insight après upload |
| 4 | Analyse ZIP (multi-fichiers) | 📄 Analyse | media_board → liste → insight |
| 5 | CR de réunion | 👥 Réunion | meeting_board avec participants |
| 6 | Kanban actions | 👥 Réunion | kanban_board avec colonnes |
| 7 | Rédaction document | ✏️ Rédaction | document_draft avec placeholders |
| 8 | Export TXT | ✏️ Rédaction | bouton télécharger actif |
| 9 | Discussion simple | 💬 Discussion | réponse courte, pas de render |
| 10 | Diagnostic pipeline | Tous | dernier maillon visible |

### 2. Fonctionnalités brouillon/validation

- ⚡ **Actions sensibles** (SMS, email, appel) → action_board + double confirmation
- 🔍 **Recherche web** → context_panel + sources citées
- 🧑‍🤝‍🧑 **Équipe/invitations** → status_rail + owner only
- 🗺️ **Carte** → map_board + consentement géoloc
- 🛡️ **Conformité** → document_insight + disclaimer juridique auto
- 📄 **Export PDF** → V2 (nécessite librairie côté serveur)

### 3. Méthode qui canalise le mieux

**Hybride E avec pré-classification serveur comme couche principale.**

Le LLM ne choisit plus — il exécute. L'utilisateur garde le contrôle via le mode. L'expérience reste naturelle car Iris parle toujours, mais elle parle APRÈS avoir affiché le travail.

### 4. Boutons/modes visibles

**Barre principale (toujours visible) :**
```
[💬 Discussion] [📊 Tableau] [📄 Analyse] [👥 Réunion] [✏️ Rédaction] [▼]
```

**Menu déroulant (▼) :**
```
🔍 Recherche web
⚡ Actions
🧑‍🤝‍🧑 Équipe
🗺️ Carte
🛡️ Conformité
```

**Badge mode courant :**
```
Session Iris  ●  0 participant  [📊 Tableau / Graphique]
```

### 5. Mots déclencheurs

**Plus besoin de mots déclencheurs** — le mode détermine l'outil.

Mots de validation (mode Actions uniquement) :
- "Valide" / "Confirme" → exécute l'action
- "Annule" / "Non" → annule
- "Modifie" / "Change" → retourne en mode édition

### 6. Garde-fous

| Garde-fou | Où | Comment |
|---|---|---|
| Mode Discussion = pas d'outil lourd | Backend | filtered_tools = [chat] |
| Actions sensibles = confirmation | Backend | requires_confirmation = true |
| Owner only pour inviter/exclure | Backend | subscriber_only = [invite_to_session] |
| Blacklist horaires 22h-7h | Backend | vérification heure avant exécution |
| Disclaimer juridique auto | Prompt | mandatory_disclaimer injecté |
| Pas d'appel numéros secours | Backend | blacklist numéros d'urgence |
| Fichier ZIP > 50 Mo refusé | Backend | taille max + message d'erreur |

### 7. Preuve target cell

Pour chaque fonctionnalité :
```
Phrase test standardisée
→ Temps de réponse < 3s
→ Dernier maillon atteint visible
→ Render correctement affiché
→ Données réelles (pas de placeholders vides)
```

Exemple target cell Tableau :
```
Input : "Prépare un graphique : janvier 10, février 20, mars 30"
Attendu :
  1. mode_selected = tableau
  2. tool_call = iris_render
  3. render_type = chart
  4. payload.labels = ["janvier", "février", "mars"]
  5. payload.datasets[0].data = [10, 20, 30]
  6. ics_render affiché en < 3s
```

### 8. Empêcher "je vais faire" sans faire

**Solution : pré-classification serveur.**

Le payload est préparé AVANT que le LLM parle. Le LLM reçoit :
```
L'utilisateur a demandé X.
Le serveur a préparé ce render.
Tu DOIS appeler iris_render avec ce payload exact.
Ensuite tu dis : "C'est affiché."
```

Le LLM n'a pas à "décider" — il exécute une instruction. S'il refuse, le fallback (couche 4) se déclenche en 1.5s.

### 9. Documents et exports

**Flux Analyse document :**
```
Upload PDF/ZIP
→ media_board (liste des fichiers)
→ document_insight (analyse structurée)
→ action_board (actions proposées)
→ document_draft (livraison finale)
→ export TXT (bouton télécharger)
```

**Flux Rédaction :**
```
Demande rédaction
→ document_draft avec placeholders
→ Édition utilisateur (clic sur placeholders)
→ Valider → action_board "Prêt à envoyer"
→ Confirmer → exécution réelle (V2)
```

### 10. Endpoints manquants/risqués

| Endpoint | Statut | Risque |
|---|---|---|
| Upload + décompression ZIP | **Manquant** | Faible — lib zipfile Python |
| Analyse OCR image | **Manquant** | Moyen — nécessite Vision API |
| Export PDF | **Manquant** | Moyen — librairie WeasyPrint ou reportlab |
| Envoi SMS réel | **Existant mais bloqué** | Élevé — garder validation_required |
| Envoi email réel | **Existant mais bloqué** | Élevé — garder validation_required |
| Appel téléphonique | **Existant mais bloqué** | Élevé — garder validation_required |
| Stockage document | **Manquant** | Moyen — S3/Cloud Storage |

---

## Comparaison des méthodes

| Méthode | Fiabilité | Expérience | Complexité | Verdict |
|---|---|---|---|---|
| A — Boutons explicites | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | Trop rigide seul |
| B — Mode selector | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Bon mais pas suffisant |
| C — Intent router | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | Robuste mais froid |
| D — Formulaire guidé | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | Trop rigide pour conversation |
| **E — Hybride (mon choix)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **Meilleur compromis** |

---

## Ma recommandation finale

**Adopter la Méthode E — Hybride à 4 couches :**

```
┌─────────────────────────────────────────┐
│  COUCHE 1 — Mode explicite (UI)         │
│  L'utilisateur choisit le contexte      │
├─────────────────────────────────────────┤
│  COUCHE 2 — Pré-classification serveur  │
│  Le serveur prépare le payload          │
├─────────────────────────────────────────┤
│  COUCHE 3 — Forçage structurel          │
│  Le LLM exécute, ne choisit pas         │
├─────────────────────────────────────────┤
│  COUCHE 4 — Fallback 1.5s               │
│  Filet de sécurité si le LLM rate       │
└─────────────────────────────────────────┘
```

**Ce que ça change pour l'utilisateur :**
- Avant : "Iris, prépare-moi un tableau" → Iris parle 10s → rien ne s'affiche → timeout
- Après : Clique "📊 Tableau" → "Prépare un graphique" → graphique apparaît en 1s → Iris dit "C'est affiché"

**Ce que ça change pour le développement :**
- Avant : On prie pour que le LLM appelle le bon outil
- Après : Le serveur prépare tout, le LLM exécute, le fallback sauve

---

## Règle d'or

> **Iris ne décide pas. Iris exécute.**
>
> Le mode est choisi par l'utilisateur.
> Le payload est préparé par le serveur.
> Le LLM parle brièvement après avoir affiché.
> Le fallback sauve si le LLM déraille.

---

## Livrable

Fichier : `docs/AGENTS_COLLABORATION/agents/KIMI_METHODE_CANALISER_IRIS_025.md`

Aucun code. Aucun déploiement. Aucune modification de prod.

Réflexion et méthode uniquement.
