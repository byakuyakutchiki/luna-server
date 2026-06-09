# FEATURE — Système de Décision & Traçabilité du Raisonnement Collectif
**Date** : 2026-06-09  
**Source** : Décision architecture produit (ChatGPT) + PO (Ludovic)  
**Destinataire** : Claude (Implémentation)  
**Priorité** : HAUTE  
**Scope** : 4 phases (8 → 9 → 10 → 11)

---

## CONTEXTE

Le workspace Iris atteint maintenant une stabilité UX (7/7 problèmes résolus). La prochaine étape est de transformer le workspace d'un outil de collaboration en un **système de traçabilité du raisonnement collectif**.

> "Non pas une visioconférence IA, mais un système de traçabilité du raisonnement collectif."

Le workflow actuel s'arrête à la proposition active + sources. Il manque la clôture du raisonnement : la décision, les actions consécutives, les réserves, et le dossier final auto-généré.

---

## VISION PRODUIT

Le workspace doit produire un **actif réutilisable** des mois plus tard :

```
Question
├── Propositions
├── Sources
├── Décision (enregistrée avec contexte)
├── Actions (découlant de la décision)
├── Réserves (journal des objections/alertes)
└── Compte-rendu Iris (dossier final auto)
```

---

## PHASE 8 — Décision

### Bouton "Valider une décision"

- **Visibilité** : Owner uniquement, étapes 10-11 du stepper
- **Style** : Bouton primaire, visible dans le header ou la zone de contrôle owner
- **Condition** : Une proposition doit être active + au moins une source attachée (optionnel mais recommandé)

### Modal de validation

```
┌─────────────────────────────┐
│  Valider une décision       │
├─────────────────────────────┤
│                             │
│  Décision retenue :         │
│  [_____________________]    │
│                             │
│         [Valider]           │
└─────────────────────────────┘
```

- **Champ** : Textarea (pas juste input, une décision peut être longue)
- **Placeholder** : "Résumer la décision collective en une phrase..."
- **Bouton** : "Valider" (désactivé si champ vide)

### Capture automatique du contexte

Au moment de la validation, le système capture automatiquement :

| Métadonnée | Source |
|---|---|
| Question | Titre de la session |
| Proposition active | Titre de la proposition active |
| Nombre de sources | Compteur sources du dossier actif |
| Réserves ouvertes | Compteur réserves (0 si phase 10 non implémentée) |
| Étape | Étape actuelle du stepper |
| Date | Timestamp ISO |
| Auteur | Nom de l'owner |

### Affichage de la décision

- **Zone** : Dans le canvas (mode travail) ou dans une zone dédiée sous le header L2
- **Style** : Carte distincte, visuellement marquante (bordure ou fond différent)
- **Contenu** :
  ```
  🎯 DÉCISION RETENUE
  "Adopter OpenAI comme moteur principal de Luna"

  Contexte : 5 sources · 2 réserves · Proposition : OpenAI principal
  Étape 11 · Owner : Ludovic · 2026-06-09
  ```

### Effet sur le workflow

- La session passe à l'étape 11 (Décision) ou reste en étape 11
- Le stepper indique visuellement que la décision est validée
- Le canvas passe en mode "Dossier clos" ou reste en mode travail selon la phase suivante

---

## PHASE 9 — Actions

### Description

Liste d'actions à réaliser suite à la décision. Chaque action est une tâche concrète.

### Interface

- **Zone** : Sous la décision dans le canvas, ou dans un panneau latéral
- **Style** : Liste type todo, avec checkbox
- **Champs** :
  - Intitulé de l'action
  - Responsable (optionnel)
  - Échéance (optionnel)

### Exemple

```
📋 ACTIONS CONSÉCUTIVES
☐ Tester charge 100 users
☐ Audit juridique fournisseur
☐ Fallback fournisseur secondaire
```

### Soumission

- Champ input + bouton "Ajouter" dans la zone PROPOSITIONS (renommée ou nouvelle zone)
- Owner peut ajouter/modifier/supprimer

---

## PHASE 10 — Journal des Réserves

### Description

Système de réserves permettant aux participants de signaler des objections, alertes ou points critiques pendant le débat.

### Niveaux

| Icône | Niveau | Signification |
|---|---|---|
| 🟨 | Attention | Point à surveiller |
| 🟧 | Réserve | Objection partielle |
| 🟥 | Critique | Objection bloquante |

### Interface

- **Bouton** : "Ouvrir une réserve" visible pour tous les participants (pas seulement owner)
- **Modal** :
  ```
  ┌─────────────────────────────┐
  │  Ouvrir une réserve         │
  ├─────────────────────────────┤
  │  Niveau : [🟨 🟧 🟥]        │
  │                             │
  │  Description :              │
  │  [_____________________]    │
  │                             │
  │         [Valider]           │
  └─────────────────────────────┘
  ```
- **Affichage** : Liste des réserves dans une zone dédiée (sidebar ou panneau), triées par niveau
- **Effet** : Le nombre de réserves est intégré dans le contexte de la décision (Phase 8)

---

## PHASE 11 — Dossier Final Automatique

### Description

Génération automatique d'un compte-rendu complet à partir de tous les éléments de la session.

### Contenu auto-généré

```
═══════════════════════════════════════
  COMPTE-RENDU IRIS
═══════════════════════════════════════

Question
  Comment rendre Luna rentable ?

Propositions
  1. Licence SaaS
  2. Abonnement premium
  3. Licences régionales

Sources
  1. Étude utilisateurs Q2 2026
  2. Benchmark concurrentiel
  3. Analyse juridique
  ...

Décision
  Adopter OpenAI comme moteur principal de Luna

Actions
  ☐ Tester charge 100 users
  ☐ Audit juridique
  ☐ Fallback fournisseur

Réserves
  🟧 Inquiétude sur la dépendance unique
  🟨 Vérifier SLA garanti

Métadonnées
  Session : audit-20260609
  Owner : Ludovic
  Date : 2026-06-09
  Durée : 45 min
  Participants : 4

═══════════════════════════════════════
```

### Interface

- **Bouton** : "Générer le compte-rendu" (owner uniquement, étape 11)
- **Affichage** : Le compte-rendu s'affiche dans le canvas en mode lecture seule
- **Export** : Bouton "Copier" ou "Télécharger" (format texte/Markdown)

---

## SCOPING RECOMMANDÉ POUR CLAUDE

### Itération 1 (Priorité MAX)
- Phase 8 uniquement : bouton décision + modal + capture contexte + affichage

### Itération 2
- Phase 9 : système d'actions todo

### Itération 3
- Phase 10 : système de réserves

### Itération 4
- Phase 11 : dossier final auto

---

## NON-RÉGRESSIONS À VÉRIFIER

| Élément | État attendu |
|---|---|
| Setup + titre | ✅ Conservé |
| Brief auto-généré | ✅ Conservé |
| Stepper 5 phases | ✅ Conservé |
| Canvas exploration | ✅ Conservé |
| Canvas travail | ✅ Conservé |
| Propositions | ✅ Conservé |
| Sources | ✅ Conservé |
| Empty state | ✅ Conservé |

---

## DÉFINITION DE FAIT (Phase 8)

- [ ] Bouton "Valider une décision" visible uniquement owner + étape 10-11
- [ ] Modal avec champ "Décision retenue" + bouton Valider
- [ ] Capture auto du contexte (question, proposition, sources, étape, date, auteur)
- [ ] Affichage de la décision dans le canvas avec métadonnées
- [ ] Audit terrain Kimi validé

---

## LIENS

- Rapport audit #4 : `docs/audit_ux/2026-06-09-post-fix-v3/audit_report_v4.md`
- Mission status : `docs/audit_ux/MISSION_STATUS.md`
