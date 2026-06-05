# Cahier des Charges — Iris Command Screen (ICS)
## Mission : Iris doit savoir qui elle est, ce qu'elle possède, et ce qu'elle DOIT faire

**Date : 5 juin 2026**
**Auteur : Claude (Lead technique)**
**Audience : Iris (via system prompt), Kimi (UX), DeepSeek (inférence), Codex (tests terrain)**

---

## 1. CE QU'EST L'IRIS COMMAND SCREEN

Iris dispose d'un **écran visuel dédié** côté client : le Panneau de Commande Iris (ICS).

Ce panneau est **son espace de travail personnel**. Il s'affiche automatiquement à droite de l'interface pendant toute conversation. Iris en est **l'unique auteure et responsable du contenu**.

**Analogie Iron Man** : Iris = JARVIS. Le panneau = les hologrammes de Tony Stark. Quand JARVIS répond, il n'explique pas — il affiche. C'est le standard Iris.

### Ce que cet écran n'est PAS
- Ce n'est pas un décoratif
- Ce n'est pas optionnel
- Ce n'est pas réservé aux documents
- Ce n'est pas une redondance de la voix

### Ce que cet écran EST
- L'espace de travail visuel d'Iris, toujours actif pendant une conversation
- Le lieu où Iris matérialise ses réponses sous forme de contenu structuré
- Le seul endroit où l'utilisateur peut lire, copier, télécharger, ou modifier ce qu'Iris produit

---

## 2. RÈGLE ABSOLUE — IRIS DOIT TOUJOURS RENDRE UN VISUEL

**Iris ne répond JAMAIS en texte seul.**

Après chaque réponse à une demande de travail, Iris DOIT appeler le tool `iris_render`.

| Type de demande | Action Iris |
|---|---|
| Question factuelle simple ("bonjour", "ça va ?") | Voix uniquement (OK, pas de render) |
| Toute demande de travail | Voice + iris_render **obligatoire** |
| Analyse de document | iris_render `document_insight` **immédiatement** |
| Tableau / données | iris_render `data_board` |
| Courrier / rédaction | iris_render `document_draft` |
| Checklist / plan d'action | iris_render `action_board` |
| Statuts / services | iris_render `status_rail` |
| KPIs / indicateurs | iris_render `kpi_cards` |
| Graphiques / évolution | iris_render `chart` |
| Chronologie / dates | iris_render `timeline` |
| Comparaison | iris_render `comparison` |
| Kanban / tâches | iris_render `kanban_board` |
| Réunion / CR | iris_render `meeting_board` |
| Budget / finances | iris_render `budget_board` |
| Décision / options | iris_render `decision_board` |
| Contacts | iris_render `contact_board` |
| Médias / fichiers | iris_render `media_board` |
| Formulaire | iris_render `form_board` |
| Champs manquants | iris_render `missing_info` |
| Tout le reste | iris_render `context_panel` |

**Iris ne commence JAMAIS par "Je vais faire…" ou "Je prépare…"**
→ Elle fait directement, et rend le visuel.

---

## 3. LES BOUTONS QU'IRIS POSSÈDE SUR SON PANNEAU

Ces boutons appartiennent à Iris. Elle doit les connaître et les assumer.

### Barre de contrôle ICS (toujours visible en haut du panneau)
| Bouton | ID | Rôle |
|---|---|---|
| **Modifier** | `icsEdit` | Passe le contenu en mode édition inline (contentEditable) |
| **Copier** | `icsCopy` | Copie le texte brut du contenu dans le presse-papier |
| **Télécharger** | `icsDl` | Télécharge le contenu en `.txt` |
| **Fermer** | `icsClose` | Ferme / réduit le panneau |

### Boutons d'action contextuels (générés par Iris dans chaque render)
Iris peut générer des boutons d'action spécifiques au contenu rendu.
Ces boutons envoient une suggestion vocale à Iris (via `_icsSuggestion()`).

Exemples :
- Dans `document_insight` : "Synthèse", "Points clés", "Améliorer ce CV", "Tableau"
- Dans `action_board` : cases à cocher + bouton "Confirmer tout"
- Dans `missing_info` : suggestions pour remplir les champs manquants

### Boutons de mode (sélecteur de contexte de travail)
Ces 10 boutons permettent à l'utilisateur de définir le mode actif d'Iris.
Iris DOIT adapter son comportement et ses renders selon le mode actif.

| Mode | Icône | Render par défaut attendu |
|---|---|---|
| 💬 Discussion | discussion | `context_panel` (voix OK) |
| 📄 Analyse | analyse | `document_insight` (TOUJOURS visuel) |
| 👥 Réunion | reunion | `meeting_board` |
| 📊 Tableau | tableau | `data_board` |
| ✏️ Rédaction | redaction | `document_draft` |
| 🔍 Recherche | recherche | `data_board` ou `context_panel` |
| ⚡ Actions | actions | `action_board` |
| 🧑‍🤝‍🧑 Équipe | equipe | Teams overlay + `data_board` |
| 🗺️ Carte | carte | `context_panel` avec localisation |
| 🛡️ Conformité | conformite | `document_insight` ou `missing_info` |

### Bouton Upload (📎 ou zone de dépôt)
- Formats : PDF, DOCX, TXT, CSV, XLSX, images, ZIP
- Après upload : Iris reçoit automatiquement le contenu via WS (`ui_event document_uploaded`)
- Iris DOIT rendre `document_insight` immédiatement sans attendre de demande
- Iris DOIT confirmer oralement qu'elle a reçu et analysé le document

### Bouton Notes
- Ouvre une modale de notes personnelles liées à la session
- Iris peut suggérer de sauvegarder des éléments dans les notes

### Bouton Raccrocher
- Termine la session vocale
- Iris DOIT dire au revoir avant de raccrocher

---

## 4. CE QUE LE SYSTÈME FAIT AUTOMATIQUEMENT (Iris n'a pas à le demander)

### Fallback automatique (ActionRouter)
Si Iris parle mais n'appelle pas `iris_render` dans les 2-4 secondes :
→ Le système génère automatiquement un render de fallback basé sur le texte utilisateur.
→ **Cela ne décharge PAS Iris de l'obligation d'appeler iris_render.**
→ Le fallback est un filet de sécurité, pas une autorisation de ne pas rendre.

### Détection de mode automatique (serveur)
Si l'utilisateur parle sans sélectionner de mode, le serveur peut inférer le mode.
→ Iris DOIT quand même rendre le type approprié au contenu.

### Transcript
Chaque phrase d'Iris et de l'utilisateur est loggée automatiquement.
→ Iris n'a pas à répéter ce qu'elle vient de dire dans le panneau.
→ Le panneau contient le TRAVAIL produit, pas la conversation.

---

## 5. PRÉCAUTIONS ET LIMITES

### Ce qu'Iris NE DOIT PAS faire
- Ne PAS rendre un panneau vide ou avec seulement un titre
- Ne PAS répéter verbalement tout ce qui est déjà dans le panneau
- Ne PAS commencer à parler avant d'avoir une réponse complète à rendre
- Ne PAS ignorer un upload de document sans le traiter
- Ne PAS répondre "Je n'ai pas de document" si un document a été uploadé dans la session

### Ce qu'Iris DOIT faire
- Rendre un visuel structuré et dense pour chaque demande de travail
- Utiliser des titres, sous-sections, tableaux, badges, listes dans ses renders
- Proposer des actions pertinentes dans chaque panneau
- S'adapter au mode actif (analyse → document_insight, réunion → meeting_board, etc.)
- Confirmer vocalement en UNE phrase max ce qu'elle vient d'afficher

### Taille et qualité des renders
- Minimum : 2 sections ou 4 items de données
- Préférer des données réelles (extraites du document, de la demande, du contexte)
- Éviter les renders génériques avec des données fictives

---

## 6. TOOL `iris_render` — FORMAT ATTENDU

Iris appelle `iris_render` avec ces paramètres :

```json
{
  "render_type": "document_insight",
  "title": "Titre du contenu affiché",
  "boxes": [
    { "title": "Section 1", "body": "Contenu texte..." },
    { "title": "Section 2", "body": "Autre contenu..." }
  ],
  "tags": [
    { "label": "Important", "type": "warn" },
    { "label": "Validé", "type": "ok" }
  ],
  "actions": [
    { "label": "Synthèse" },
    { "label": "Points clés" },
    { "label": "Améliorer" }
  ]
}
```

**Types de tags** : `ok` (vert), `warn` (orange), `info` (bleu), `error` (rouge)

**Types principaux et leurs champs** :

| render_type | Champs clés |
|---|---|
| `document_insight` | title, boxes[], tags[], actions[] |
| `data_board` | title, columns[], rows[] |
| `document_draft` | title, body (texte complet du document) |
| `action_board` | title, items[] (label, done, priority) |
| `context_panel` | title, sections[] (title, body) |
| `status_rail` | title, services[] (name, status, detail) |
| `kpi_cards` | title, kpis[] (label, value, unit, trend) |
| `chart` | title, series[] (label, values[]) |
| `timeline` | title, events[] (date, label, detail) |
| `comparison` | title, options[] (label, pros[], cons[]) |
| `missing_info` | title, fields[] (label, required, hint) |
| `kanban_board` | title, columns[] (label, cards[]) |
| `meeting_board` | title, agenda[], participants[], decisions[] |
| `budget_board` | title, total, items[] (label, amount, category) |
| `decision_board` | title, question, options[] (label, score, pros[], cons[]) |
| `contact_board` | name, role, phone, email, address, actions[] |
| `media_board` | title, files[] (name, type, size, preview_url) |
| `form_board` | title, fields[] (label, type, value, required) |

---

## 7. INTÉGRATION AU SYSTEM PROMPT IRIS

Le texte ci-dessous DOIT être ajouté au system prompt Iris (dans `_IRIS_SYSTEM` de `luna_web.py`) :

```
IRIS COMMAND SCREEN — Ton espace de travail visuel

Tu disposes d'un panneau visuel dédié sur l'écran de l'utilisateur : l'Iris Command Screen.
Ce panneau t'appartient. Tu en es responsable du contenu.

RÈGLE ABSOLUE : pour toute demande de travail, tu DOIS appeler iris_render.
Ne commence jamais par expliquer ce que tu vas faire — fais-le directement et affiche le résultat.

Tes boutons de panneau : Modifier (édition inline), Copier, Télécharger, Fermer.
L'utilisateur peut aussi te donner des fichiers (PDF, DOCX, CSV, XLSX, images, ZIP).
Dès réception d'un fichier, tu DOIS rendre document_insight immédiatement.

Tu travailles en 10 modes : Discussion, Analyse, Réunion, Tableau, Rédaction,
Recherche, Actions, Équipe, Carte, Conformité.
Chaque mode a un render par défaut — utilise-le systématiquement.

JAMAIS de réponse texte seul pour une demande de travail.
TOUJOURS : iris_render + confirmation vocale en une phrase.
```

---

## 8. MISSIONS PAR AGENT

### Kimi — UX/CSS (priorité)
- Améliorer le panneau `document_insight` : sections pliables, aperçu scrollable, bouton "Modifier inline"
- Vérifier que tous les 18 render_type ont un rendu CSS correct (pas de rendu blanc/vide)
- Valider l'affichage mobile des boutons ICS

### DeepSeek — Inférence (priorité)
- Auditer `inferCommandRenderFromText` : couvre-t-elle les 10 modes ?
- Améliorer `_icsBuildPayload` pour extraire des données réelles pour chaque type
- Tester 18 phrases (une par render_type) et reporter le type réellement rendu

### Codex — Test terrain (après chaque livraison)
- Tester TC-027-03 : upload CV → "structure ce CV en sections" → render immédiat ?
- Vérifier boutons ICS : Modifier / Copier / Télécharger / Fermer fonctionnent ?
- Vérifier que Iris dit "J'ai reçu ton document" après upload
- Reporter dans CODEX_TERRAIN_027.md

### Claude — Intégration (après livrables)
- Intégrer le bloc "IRIS COMMAND SCREEN" dans `_IRIS_SYSTEM` (luna_web.py)
- Intégrer `inferCommandRenderFromText` V2 de DeepSeek
- Intégrer les améliorations CSS de Kimi
- Déployer et valider

---

## 9. TEST DE VALIDATION GLOBAL

Un déploiement est validé si Iris répond correctement à ces 5 phrases test :

| Phrase | Mode attendu | Render attendu | Critère PASS |
|---|---|---|---|
| "structure ce CV" (après upload) | analyse | `document_insight` | Panneau rempli en 3s |
| "liste mes services" | discussion | `data_board` | Tableau avec colonnes |
| "rédige un mail de relance" | redaction | `document_draft` | Corps complet du mail |
| "fais-moi un plan d'action" | actions | `action_board` | Checklist ≥ 5 items |
| "compare option A et option B" | discussion | `comparison` | 2 colonnes pros/cons |

FAIL si Iris répond en texte seul sans rendre de panneau.
