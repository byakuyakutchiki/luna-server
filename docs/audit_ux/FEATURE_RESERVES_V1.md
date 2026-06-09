# FEATURE — Phase 10 : Journal des Réserves
**Date** : 2026-06-09  
**Source** : Décision architecture produit (ChatGPT) + vision PO (Ludovic)  
**Destinataire** : Claude (Implémentation)  
**Priorité** : HAUTE  
**Scope** : Phase 10 uniquement (Réserves)

---

## CONTEXTE

Les Phases 8 (Décision) et 9 (Actions) sont déployées et auditées avec succès.

Le workflow actuel :
```
Setup → Brief → Collecte → Propositions → Dossier actif → Décision → Actions
```

La Phase 10 introduit la couche **Réserves** : la mémoire des désaccords et des avertissements.

> "La plupart des outils conservent les documents, les décisions, les tâches, mais perdent les objections, les risques signalés, les réserves ignorées."

---

## PHILOSOPHIE PRODUIT (Non négociable)

### La Réserve n'est pas…
- Une tâche
- Un commentaire
- Un bug

### La Réserve est…
Un **objet métier autonome** qui documente ce qui a été contesté **avant** la décision.

### Principe fondamental
**Le owner peut toujours continuer, même avec une réserve 🟥 Critique.**

Iris ne doit **jamais** devenir un système bureaucratique qui bloque le workflow.

Ce qui est enregistré :
- La réserve
- L'auteur
- La date
- La décision prise **malgré** la réserve

---

## MODÈLE DE DONNÉES

```javascript
{
  id: string,              // UUID
  mission_id: string,      // Référence session
  level: "YELLOW" | "ORANGE" | "RED",
  author: "IRIS" | "IQ" | "LUNA" | string,  // string = nom humain
  title: string,           // Intitulé court
  description: string,     // Détail (optionnel)
  status: "OPEN" | "ACKNOWLEDGED" | "OVERRIDDEN" | "RESOLVED",
  created_at: string,      // ISO 8601
  closed_at: string | null // ISO 8601 ou null
}
```

### Niveaux

| Icône | Code | Nom | Signification | Exemple |
|---|---|---|---|---|
| 🟨 | `YELLOW` | Attention | Information utile | "Peu de sources disponibles" |
| 🟧 | `ORANGE` | Réserve | Risque identifié | "Dépendance forte à OpenAI" |
| 🟥 | `RED` | Critique | Risque majeur | "Aucune validation juridique effectuée" |

### Statuts

| Statut | Signification |
|---|---|
| `OPEN` | Réserve ouverte, non traitée |
| `ACKNOWLEDGED` | Le owner a pris connaissance |
| `OVERRIDDEN` | Le owner a décidé de continuer malgré la réserve |
| `RESOLVED` | La réserve a été levée (action corrective) |

---

## INTERFACE UTILISATEUR

### Bouton d'ouverture d'une réserve

- **Visibilité** : Tous les participants (pas seulement owner)
- **Emplacement** : Barre d'actions en bas (à côté de "+ ACTION")
- **Texte** : "⚠️ Ouvrir une réserve"
- **Condition** : Dès qu'une proposition est active (étape 3+)

### Modal de création

```
┌─────────────────────────────────────────────┐
│  ⚠️ Ouvrir une réserve                      │
├─────────────────────────────────────────────┤
│                                             │
│  Niveau :                                   │
│  [🟨 Attention] [🟧 Réserve] [🟥 Critique]  │
│                                             │
│  Intitulé :                                 │
│  [________________________________]         │
│                                             │
│  Description (optionnel) :                  │
│  [                                ]         │
│  [                                ]         │
│                                             │
│         [Annuler]    [Ouvrir]               │
└─────────────────────────────────────────────┘
```

### Affichage des réserves

**Zone** : Dans le canvas, sous la zone Actions (ou à côté, selon l'espace disponible)

**Résumé** (compact) :
```
🟨 1 Attention    🟧 2 Réserves    🟥 1 Critique
```

**Détail** (au clic sur le résumé ou en mode étendu) :
```
┌────────────────────────────────────────────────┐
│  🟥 Dépendance fournisseur                     │
│  Auteur : IQ                                   │
│  Statut : Ouverte                              │
│  [Accuser réception]  [Continuer malgré]       │
└────────────────────────────────────────────────┘
```

### Actions sur une réserve (owner uniquement)

- **Accuser réception** → statut `ACKNOWLEDGED`
- **Continuer malgré la réserve** → statut `OVERRIDDEN` + enregistrement de la décision
- **Résoudre** → statut `RESOLVED` + `closed_at` renseigné

### Intégration dans le contexte de décision

La carte Décision (Phase 8) affiche un compteur de réserves :
```
🎯 DÉCISION RETENUE
"Adopter OpenAI..."

🟨 1  🟧 2  🟥 1     ← cliquable, ouvre le panneau réserves
```

---

## WORKFLOW

### Création (par n'importe quel participant)
```
Participant clique "⚠️ Ouvrir une réserve"
  ↓
Choisit le niveau (🟨 🟧 🟥)
  ↓
Saisit l'intitulé + description
  ↓
Clique "Ouvrir"
  ↓
Réserve apparaît dans la liste (statut OPEN)
```

### Traitement (par owner)
```
Owner voit le compteur 🟥 1 sur la carte Décision
  ↓
Clique pour ouvrir le détail
  ↓
Choix :
  → [Accuser réception]  → ACKNOWLEDGED
  → [Continuer malgré]   → OVERRIDDEN (historisé)
  → [Résoudre]           → RESOLVED
```

### Historisation

Quand le owner passe outre une réserve 🟥 :
```
17/06/2026

IQ :
🟥 Risque de dépendance fournisseur

Décision du owner :
Continuer malgré la réserve
```

Cet historique est intégré dans le dossier final (Phase 11).

---

## NON-RÉGRESSIONS

| Élément | État attendu |
|---|---|
| Phase 8 (Décision) | ✅ Conservée |
| Phase 9 (Actions) | ✅ Conservée |
| Carte décision | ✅ Toujours visible |
| Setup + titre | ✅ Conservé |
| Brief auto | ✅ Conservé |
| Stepper | ✅ Conservé |
| Canvas exploration/travail | ✅ Conservé |

---

## DÉFINITION DE FAIT

- [ ] Bouton "⚠️ Ouvrir une réserve" visible pour tous (étape 3+)
- [ ] Modal avec 3 niveaux + intitulé + description
- [ ] Liste des réserves affichée dans le canvas
- [ ] Compteur 🟨🟧🟥 sur la carte Décision
- [ ] Actions owner : Accuser réception / Continuer / Résoudre
- [ ] Statuts : OPEN, ACKNOWLEDGED, OVERRIDDEN, RESOLVED
- [ ] Historisation quand owner passe outre
- [ ] Persistance backend via WS + state_sync
- [ ] Audit terrain Kimi validé

---

## RÈGLES D'OR

1. **Les réserves ne bloquent jamais le workflow.**
2. **Toute décision prise malgré une réserve est historisée.**
3. **Les réserves sont visibles par tous, créables par tous.**
4. **Seul le owner peut changer le statut d'une réserve.**

---

## LIENS

- Spécification globale : `docs/audit_ux/FEATURE_DECISION_V1.md`
- Brief Phase 9 : `docs/audit_ux/FEATURE_ACTIONS_V1.md`
- Rapport Phase 9 : `docs/audit_ux/2026-06-09-phase9/audit_report_v6.md`
- Mission status : `docs/audit_ux/MISSION_STATUS.md`
