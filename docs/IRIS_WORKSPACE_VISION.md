# IRIS WORKSPACE — Vision Architecture

> **Date** : 2 juin 2026
> **Auteur** : Ludovic (fondateur) + Kimi
> **Statut** : Architecture — non implémenté
> **Évolution de** : Iris Command Screen V1 (`eae3965`)

---

## 1. Manifeste — Le modèle mental

Aujourd'hui, l'IA répond avec du texte. L'utilisateur lit.
Demain, l'IA **pense en visuel** et **projette** ce qui aide.

```
Chatbot classique :
IA → Réponse texte → Écran rempli de paragraphes

Vision Iris Workspace :
IA → Comprend l'intention → Choisit le média idéal
                          → Projette
                          → Construit devant l'utilisateur
                          → Explique en parlant
```

**L'écran devient une extension du cerveau de l'IA.**
L'utilisateur ne demande pas "affiche-moi un tableau". Il dit "aide-moi à développer VoltAI" et Iris choisit **seule** le support visuel le plus adapté.

---

## 2. Types de projections possibles

| Projection | Quand l'utilisateur… | Exemple concret |
|---|---|---|
| **Tableau structuré** | compare, liste, classe | "Mes dépenses", "les concurrents" |
| **Graphique / Chart** | parle de chiffres, tendances, volumes | "5000€/mois → 1M", "croissance BESS" |
| **Roadmap / Timeline** | planifie, stratégie, étapes | "Développer VoltAI en 5 ans" |
| **Diagramme (flowchart)** | décrit un processus, un flux | "Le parcours client", "la chaîne de valeur" |
| **Organigramme** | parle d'équipe, de structure | "Qui fait quoi dans mon projet" |
| **Carte mentale** | explore des idées, brainstorm | "Les opportunités autour de l'IA" |
| **Synthèse document** | upload un PDF, un contrat | "Analyse ce devis", "résume cet audit" |
| **Dashboard métrique** | demande l'état, la santé | "Où en est mon business ?" |
| **Schéma d'architecture** | décrit un système technique | "L'infra Luna", "la stack VoltAI" |
| **Projection financière** | parle d'argent, d'investissement | "Scénarios optimiste/pessimiste" |
| **Comparatif visuel** | hésite entre options | "Pro A vs Pro B" |
| **To-do / Plan d'action** | organise, priorise | "Mes 3 prochaines actions" |

> **Règle d'or** : le visuel doit permettre à quelqu'un qui regarde par-dessus l'épaule de comprendre le sujet **sans lire tout le dialogue**.

---

## 3. Déclencheurs d'intention — Quand projeter ?

Iris ne projette pas à chaque phrase. Elle projette quand **le média visuel apporte plus de valeur que le texte pur**.

### 3.1 Déclencheurs explicites (demande directe)
- "Montre-moi…", "Affiche…", "Projette…", "Fais-moi un schéma de…"
- "Qu'est-ce que ça donne en chiffres ?"

### 3.2 Déclencheurs implicites (inférence IA)
- **Présence de données structurables** : liste, comparaison, statuts
- **Présence de chiffres ou de projections** : budget, CA, croissance
- **Présence de séquence temporelle** : étapes, phases, deadlines
- **Présence de hiérarchie ou de relations** : équipe, dépendances, cause-effet
- **Complexité textuelle** : réponse > 3 phrases → risque de perte d'attention → synthèse visuelle
- **Upload de document** : PDF, image, CSV → analyse → projection automatique

### 3.3 Anti-déclencheurs (quand NE PAS projeter)
- Réponse courte (< 2 phrases) et sans données
- Question rhétorique ou sociale ("Ça va ?", "Merci")
- Demande de confirmation simple ("Tu veux que je l'envoie ?")
- Contexte sensible nécessitant discrétion (données privées médicales sans consentement explicite)

---

## 4. Logique de sélection du rendu

### 4.1 Pipeline de décision

```
Texte de l'utilisateur (ou transcript Iris)
        │
        ▼
┌───────────────────┐
│ 1. Extraction     │ → Entités : chiffres, dates, noms,
│    sémantique     │   catégories, actions, relations
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 2. Scoring des    │ → Chaque type de projection reçoit
│    projections    │   un score 0-100 selon adéquation
│    candidates     │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 3. Sélection      │ → Meilleur score > seuil (ex: 60)
│    + fallback     │ → Sinon : context_panel (texte structuré)
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 4. Construction   │ → Génération du payload JSON structuré
│    du payload     │   correspondant au type choisi
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 5. Projection     │ → Envoi WS `render` → client
│    côté client    │   → animation de construction
└───────────────────┘
```

### 4.2 Matrice de scoring (exemple)

| Signal détecté | +Tableau | +Graph | +Roadmap | +Diagramme | +Synthèse doc |
|---|---|---|---|---|---|
| Nombres (> 3) | 30 | 70 | 10 | 0 | 0 |
| Dates / phases | 20 | 10 | 80 | 20 | 0 |
| "vs", "comparer" | 60 | 20 | 0 | 0 | 0 |
| "étape", "phase", "d'abord" | 10 | 0 | 70 | 40 | 0 |
| "si… alors…", "flux" | 0 | 0 | 10 | 80 | 0 |
| "équipe", "responsable" | 20 | 0 | 0 | 60 | 0 |
| Upload PDF | 0 | 0 | 0 | 0 | 90 |
| "explique", "pourquoi" | 0 | 0 | 0 | 0 | 30 |
| Longueur > 200 mots | 10 | 10 | 10 | 10 | 40 |

> Le type avec le score le plus élevé est sélectionné. En cas d'égalité, on privilégie le type le plus simple à construire rapidement (tableau > graphique > diagramme).

### 4.3 Le rôle du modèle LLM

Le LLM (OpenAI Realtime / GPT-4o) ne se contente pas de répondre.
Il est prompté pour **décider si un visuel est pertinent** et, si oui, **choisir le type** parmi une liste fermée.

```
System prompt (extrait) :
"Tu es Iris, une opératrice IA. Quand une réponse contient
 des données, des comparaisons, des étapes ou des chiffres,
 tu dois appeler l'outil iris_render avec le render_type
 le plus adapté. Tu ne réponds pas uniquement en texte
 quand un visuel serait plus clair."
```

Le LLM appelle `iris_render(render_type, payload)` automatiquement.
Le client ne fait que projeter ce qu'il reçoit.

---

## 5. APIs et capacités déjà disponibles

### 5.1 Infrastructure existante (V1)
| Composant | État | Rôle dans le Workspace |
|---|---|---|
| WebSocket `/ws/iris-voice` | ✅ Actif | Canal temps réel audio + données |
| Tool `iris_render` | ✅ Défini | Point d'entrée backend pour les projections |
| `renderIrisCommand()` | ✅ Implémenté | Renderer côté client (6 types) |
| `inferCommandRenderFromText()` | ✅ Basique | Fallback client si le serveur n'envoie pas de render |
| `_icsBuildPayload()` | ✅ Générique | Construction de payloads fallback |
| VAD + MediaRecorder | ✅ Actif | Capture vocale sans clic |
| OpenAI Realtime API | ✅ Connecté | LLM + TTS natif |

### 5.2 APIs / libs à intégrer pour les projections avancées
| Technologie | Projection visée | Complexité |
|---|---|---|
| **Chart.js / ApexCharts** | Graphiques, barres, lignes, camemberts | Basse — lib JS légère |
| **Mermaid.js** | Diagrammes, flowcharts, organigrammes, Gantt | Moyenne — DSL texte → SVG |
| **D3.js (lite)** | Visualisations custom, treemaps, timelines | Haute — courbe d'apprentissage |
| **PDF-lib / pdf2pic** | Rendu PDF côté client | Moyenne — parsing + thumbnail |
| **OpenAI Vision API** | Analyse d'image uploadée → schéma | Moyenne — appel API synchrone |
| **OpenAI Structured Outputs** | Payloads JSON validés par schéma | Basse — remplace le parsing manuel |
| **Canvas 2D / WebGL** | Animations de construction, hologrammes | Haute — direction artistique |

### 5.3 Données accessibles à Iris
- API Documents v2 (`/api/documents/v2/*`) → contenu du vault
- API Notifications → état des rappels, alertes
- API Quotas / Budget → chiffres en temps réel
- API Météo / Contexte → données extérieures
- Mémoire de session → historique de la conversation

---

## 6. Roadmap progressive

### Phase 1 — Tableaux + Graphiques (Q2 2026)
**Objectif** : 80% des cas "chiffres et listes" couverts visuellement.

- [ ] Intégrer **Chart.js** pour les graphiques simples (barres, lignes, camemberts)
- [ ] Étendre `data_board` avec types de colonnes : nombre, pourcentage, monnaie, statut
- [ ] Nouveau render_type : `metric_card` (KPIs en gros chiffres)
- [ ] Nouveau render_type : `bar_chart`, `line_chart`
- [ ] Améliorer `inferCommandRenderFromText` pour détecter les signaux numériques
- [ ] Prompt LLM : inciter à appeler `iris_render` dès qu'un chiffre apparaît

**Exemple livré** :
"J'ai 5000€/mois, je veux atteindre 1M." → Iris projette un graphique à barres avec projections annuelles et seuils critiques.

---

### Phase 2 — Diagrammes + Timelines (Q3 2026)
**Objectif** : Les stratégies, processus et plannings deviennent visuels.

- [ ] Intégrer **Mermaid.js** pour les diagrammes
- [ ] Nouveau render_type : `flowchart` (flux de processus)
- [ ] Nouveau render_type : `roadmap` (timeline horizontale avec phases)
- [ ] Nouveau render_type : `org_chart` (organigramme hiérarchique)
- [ ] Parser automatique : "d'abord… ensuite… enfin…" → roadmap
- [ ] Parser automatique : "si X alors Y sinon Z" → flowchart

**Exemple livré** :
"Aide-moi à développer VoltAI." → Iris projette une roadmap 5 ans (R&D → Prototype → Commercial → Scale) avec milestones et ressources.

---

### Phase 3 — Images + Synthèses visuelles (Q4 2026)
**Objectif** : L'upload de document et l'analyse visuelle deviennent natives.

- [ ] Upload PDF/image dans le chat audio/texte
- [ ] Nouveau render_type : `document_analysis` (résumé, risques, opportunités, actions)
- [ ] Nouveau render_type : `mind_map` (carte mentale radiale)
- [ ] Nouveau render_type : `image_annotation` (image + surlignages + légendes)
- [ ] Génération d'images par DALL-E / Flux pour les schémas conceptuels
- [ ] Export des projections en PDF / image partageable

**Exemple livré** :
Ludo upload un contrat PDF. Iris projette :
- Résumé en 3 points
- Clause à risque surlignée
- Timeline des échéances
- Bouton "Générer une contre-proposition"

---

### Phase 4 — Workspace intelligent complet (2027)
**Objectif** : L'écran devient une surface de travail collaborative et persistante.

- [ ] **Multi-projection** : plusieurs rendus empilés ou en onglets dans le Workspace
- [ ] **Persistance** : sauvegarde des projections dans le vault du souscripteur
- [ ] **Interaction minimale** : clic pour déplier, hover pour détail, pas de drag&drop
- [ ] **Multi-participants** : plusieurs personnes voient la même projection en visio
- [ ] **Templates métier** : modèles pré-construits (Business Model Canvas, SWOT, RACI…)
- [ ] **IA générative de templates** : "Crée-moi un dashboard pour suivre ma SaaS" → Iris génère le layout + les widgets

**Exemple livré** :
Réunion visio à 4. Iris écoute, projette un Business Model Canvas en direct, le remplit au fur et à mesure des décisions, puis exporte le PDF à tous les participants.

---

## 7. Principes directeurs

1. **L'IA choisit, l'utilisateur valide.**
   L'utilisateur ne demande pas "un tableau". Il pose une question. Iris choisit le média.

2. **Construire devant l'utilisateur.**
   Pas d'apparition brutale. Animation de construction (stagger, scan-line, fade-in) pour que l'œuil suive la logique.

3. **Texte est le fallback, pas la norme.**
   `context_panel` (texte structuré) est le plan B. Le plan A est toujours visuel quand c'est pertinent.

4. **Pas d'interaction complexe.**
   Pas de drag & drop, pas d'IDE, pas de clic obligatoire. Lire et comprendre suffit. Les actions (confirmer, copier, télécharger) restent des boutons simples.

5. **Un écran doit raconter la conversation.**
   Quelqu'un qui arrive en cours de session doit comprendre le sujet en 3 secondes en regardant le Workspace.

6. **Sécurité et consentement.**
   Projection automatique UNIQUEMENT sur des données non sensibles ou déjà validées. Aucune projection de données privées tierces sans confirmation.

---

## 8. Critères de succès

| Indicateur | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|---|---|---|---|---|
| % de réponses avec projection | 30% | 50% | 70% | 85% |
| Temps de construction visuel | < 800ms | < 800ms | < 1.2s | < 1.5s |
| Types de render disponibles | 8 | 12 | 16 | 20+ |
| Satisfaction "Je n'ai pas eu besoin de tout lire" | — | 60% | 75% | 85% |
| Retours "L'écran m'a aidé à décider" | — | — | 60% | 80% |

---

## 9. Ce que l'on ne fait PAS (garde-fous)

- ❌ Pas de drag & drop
- ❌ Pas d'édition WYSIWYG complexe
- ❌ Pas de multi-fenêtres flottantes
- ❌ Pas de code / IDE dans le Workspace (Iris ≠ copilote de code)
- ❌ Pas de projection sans consentement implicite (données sensibles)
- ❌ Pas de son/animation intrusive lors de la projection (hologramme silencieux)

---

*Document de travail. À valider par Ludovic avant passage en spécifications techniques pour Claude/Codex.*
