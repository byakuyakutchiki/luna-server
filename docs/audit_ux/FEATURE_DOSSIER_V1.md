# FEATURE — Phase 11 : Dossier Final Automatique
**Date** : 2026-06-09  
**Source** : Décision architecture produit (ChatGPT) + validation PO (Ludovic)  
**Destinataire** : Claude (Implémentation)  
**Priorité** : HAUTE  
**Scope** : Phase 11 — Dernière phase de la feature Décision & Traçabilité

---

## CONTEXTE

Les Phases 8 (Décision), 9 (Actions) et 10 (Réserves) sont déployées et auditées avec succès.

Le workflow actuel :
```
Setup → Brief → Collecte → Propositions → Dossier actif → Décision → Actions → Réserves
```

La Phase 11 clôture la boucle avec le **Dossier final** : le jumeau documentaire du raisonnement collectif.

> "Quand quelqu'un ouvre le dossier 6 mois plus tard, il doit comprendre ce qui était étudié, quelles options existaient, pourquoi un choix a été retenu, quelles réserves existaient, quelles actions ont suivi — sans devoir relire toute la mission."

---

## PHILOSOPHIE PRODUIT (Non négociable)

### Ce que le Dossier final N'EST PAS
- Un export PDF
- Un résumé LLM générique et flou
- Un document modifiable a posteriori

### Ce que le Dossier final EST
- Un **snapshot figé** du raisonnement au moment de la génération
- Un **actif réutilisable** des mois plus tard
- La **traçabilité complète** de la mission
- Un **jumeau documentaire** du raisonnement collectif

---

## STRUCTURE DU DOSSIER FINAL

### 1. En-tête

```
═══════════════════════════════════════
  COMPTE-RENDU IRIS
═══════════════════════════════════════

Mission      : [titre de la session]
Owner        : [nom du owner]
Date         : [date de génération]
Version      : 1.0 (snapshot)
Participants : Iris · IQ · Luna · [humains]
```

### 2. Question

```
❓ QUESTION
[Texte de la question / titre de la session]
```

### 3. Propositions étudiées

```
💡 PROPOSITIONS ÉTUDIÉES

Proposition A
[titre]

Proposition B
[titre]

Proposition C
[titre]
```

### 4. Proposition retenue

```
⚡ PROPOSITION RETENUE
[titre de la proposition active]
```

### 5. Sources

```
📚 SOURCES ANALYSÉES

Résumé : [N] sources analysées

1. [Titre source 1]
2. [Titre source 2]
...

[Afficher les détails au clic ou en mode étendu]
```

### 6. Décision

```
🎯 DÉCISION
[Texte de la décision]

Date   : [date]
Owner  : [nom]
```

### 7. Actions

```
📋 ACTIONS

☑ [Action terminée]        [Responsable]
☐ [Action en cours]        [Responsable]
☐ [Action à faire]         [Responsable]
```

### 8. Réserves

```
⚠️ RÉSERVES

🟥 [Titre réserve critique]
Auteur : [IQ / IRIS / LUNA / Humain]
Statut : [Continuer malgré la réserve / Résolue]

🟧 [Titre réserve]
...
```

### 9. Synthèse Iris

```
🧠 SYNTHÈSE IRIS

Après analyse de [N] propositions et [M] sources, la proposition
[proposition retenue] a été retenue pour [raison concise].

Une réserve [niveau] concernant [sujet] a été signalée par [auteur]
et [statut traitement]. [K] actions opérationnelles ont été définies
pour l'exécution.
```

**Règle** : La synthèse n'est pas un résumé LLM générique. Elle est **structurée** et **factice** (template avec variables remplacées par les données réelles de la session).

---

## INTERFACE UTILISATEUR

### Bouton de génération

- **Visibilité** : Owner uniquement, étape 11+
- **Emplacement** : Barre d'actions en bas (à côté de "+ ACTION" et "⚠️ OUVRIR UNE RÉSERVE")
- **Texte** : "📄 Générer le dossier final"
- **Condition** : Une décision doit avoir été validée

### Affichage du dossier

- **Zone** : Canvas en mode plein écran (remplace le contenu actuel)
- **Style** : Document structuré, fond légèrement différent pour marquer le caractère "final"
- **Lecture seule** : Aucun champ éditable

### Actions sur le dossier

- **Copier** : Bouton "Copier le texte" (format Markdown)
- **Fermer** : Bouton "Retour au workspace" (revient à la vue normale)
- **Pas de modification** : Le dossier est un snapshot, pas un document de travail

---

## RÈGLES D'OR

1. **Snapshot figé** : Le contenu est figé au moment de la génération. Les changements ultérieurs dans la session ne modifient pas le dossier déjà généré.
2. **Lecture seule** : Le dossier final n'est pas modifiable manuellement.
3. **Template structuré** : La synthèse est générée par template (pas par appel LLM coûteux).
4. **Historique** : Le dossier représente l'historique. Il peut être régénéré, mais l'ancienne version est écrasée (ou conservée avec un numéro de version si implémenté).

---

## MODÈLE DE DONNÉES

### Frontend

Le dossier final est généré côté frontend à partir du state existant :
- `session.title` → Mission
- `session.owner` → Owner
- `session.brief` → Question
- `session.proposals` → Propositions
- `session.active_proposal` → Proposition retenue
- `session.sources` → Sources
- `session.decision` → Décision
- `session.actions` → Actions
- `session.reserves` → Réserves

### Backend

- **Handler WS** : `report_generate` (owner only)
- **Room state** : `_IrisTeamRoom.report` (string Markdown ou objet structuré)
- **Persistance** : Stocké dans `get_state()`, retourné aux participants

---

## WORKFLOW

```
Owner clique "📄 Générer le dossier final"
    ↓
Système collecte tous les éléments de la session
    ↓
Génération du Markdown structuré (template)
    ↓
Affichage dans le canvas (mode lecture seule)
    ↓
Owner peut copier ou fermer
```

---

## NON-RÉGRESSIONS

| Élément | État attendu |
|---|---|
| Phase 8 (Décision) | ✅ Conservée |
| Phase 9 (Actions) | ✅ Conservée |
| Phase 10 (Réserves) | ✅ Conservée |
| Setup + titre | ✅ Conservé |
| Brief auto | ✅ Conservé |
| Stepper | ✅ Conservé |
| Canvas exploration/travail | ✅ Conservé |

---

## DÉFINITION DE FAIT

- [ ] Bouton "📄 Générer le dossier final" (owner, étape 11+)
- [ ] Dossier structuré en 9 sections (En-tête, Question, Propositions, Retenue, Sources, Décision, Actions, Réserves, Synthèse)
- [ ] Contenu généré à partir du state de la session (template, pas LLM)
- [ ] Affichage lecture seule dans le canvas
- [ ] Bouton "Copier" (format Markdown)
- [ ] Snapshot figé au moment de la génération
- [ ] Persistance backend
- [ ] Audit terrain Kimi validé

---

## APRÈS LA PHASE 11

La feature **Décision & Traçabilité** sera complète.

```
Question
  ↓
Propositions
  ↓
Sources
  ↓
Décision
  ↓
Actions
  ↓
Réserves
  ↓
Dossier final
```

**Vision réalisée** : Iris Workspace n'est pas un outil de chat, mais un **système de traçabilité du raisonnement collectif**.

---

## LIENS

- Spécification globale : `docs/audit_ux/FEATURE_DECISION_V1.md`
- Brief Phase 9 : `docs/audit_ux/FEATURE_ACTIONS_V1.md`
- Brief Phase 10 : `docs/audit_ux/FEATURE_RESERVES_V1.md`
- Rapport Phase 10 : `docs/audit_ux/2026-06-09-phase10/audit_report_v7.md`
- Mission status : `docs/audit_ux/MISSION_STATUS.md`
