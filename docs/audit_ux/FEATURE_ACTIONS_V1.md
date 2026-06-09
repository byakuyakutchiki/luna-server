# FEATURE — Phase 9 : Actions (Conséquences d'une Décision)
**Date** : 2026-06-09  
**Source** : Décision architecture produit (ChatGPT) + contraintes PO (Ludovic)  
**Destinataire** : Claude (Implémentation)  
**Priorité** : HAUTE  
**Scope** : Phase 9 uniquement (Actions)

---

## CONTEXTE

La Phase 8 (Décision) est déployée et auditée avec succès. Le workflow actuel :

```
Setup → Brief auto → Collecte → Propositions → Dossier actif → Décision validée
```

La Phase 9 ajoute la couche **Actions** : les conséquences concrètes de la décision.

---

## CONTRAINTES MÉTIER (Non négociables)

### 1. Traçabilité hiérarchique

```
Mission
 └─ Question (titre de session)
     └─ Décision
         └─ Actions
```

**Règle** : Une Action appartient **obligatoirement** à une Décision.  
**Interdit** : Actions orphelines, backlog libre, tâches rattachées directement à la Mission.

### 2. Statuts obligatoires

| Statut | Code | Visuel |
|---|---|---|
| À faire | `TODO` | ☐ gris |
| En cours | `IN_PROGRESS` | ◐ orange |
| Terminée | `DONE` | ☑ vert |
| Annulée | `CANCELLED` | ⊘ rouge |

**Règle** : Le statut par défaut est `TODO`.  
**Interdit** : Workflow personnalisable, statuts libres, colonnes Kanban drag-and-drop.

### 3. Assignation

**Champ** : `assigned_to` (string, nom du responsable)  
**Aujourd'hui** : Owner uniquement (valeur par défaut = nom de l'owner)  
**Demain** : Collaborateur, IA  
**Règle** : Prévoir le champ dès maintenant, même si l'UI ne propose qu'une seule option.

### 4. Lien d'origine

**Règle** : Chaque Action affiche son origine : `Decision #42` ou le texte de la décision liée.  
**Format d'affichage** :
```
📋 ACTIONS CONSÉCUTIVES
Origine : 🎯 Décision — "Adopter OpenAI comme moteur principal"

☐ Tester charge 100 users                    [Auditeur UX]
☑ Audit juridique fournisseur                [Auditeur UX]
◐ Fallback fournisseur secondaire            [Auditeur UX]
```

### 5. Iris ≠ Trello

**Ce qu'Iris n'est PAS** :
- Un gestionnaire de tâches généraliste
- Un outil de backlog libre
- Un tableau Kanban avec colonnes personnalisables
- Un système de sous-projets imbriqués

**Ce qu'Iris EST** :
- Un système de traçabilité du raisonnement collectif
- Chaque Action est une **conséquence documentée** d'une Décision documentée

**Interdit** :
- Créer des Actions sans Décision parente
- Backlog d'Actions orphelines
- Sous-tâches, sous-projets, dépendances entre Actions
- Colonnes Kanban, swimlanes, tags libres

---

## INTERFACE UTILISATEUR

### Zone d'affichage

- **Emplacement** : Dans le canvas, sous la carte Décision (mode travail, étape 11+)
- **Style** : Liste simple, pas de tableau ou de grille
- **Titre** : "📋 ACTIONS CONSÉCUTIVES"
- **Sous-titre** : "Origine : 🎯 [texte de la décision]"

### Carte Action individuelle

```
┌────────────────────────────────────────────┐
│ ☐ Créer compte OpenAI                      │
│    Responsable : Auditeur UX               │
│    [Marquer en cours] [Marquer terminée]   │
└────────────────────────────────────────────┘
```

- **Checkbox** : cliquable pour changer le statut (TODO → DONE directement, ou TODO → IN_PROGRESS → DONE)
- **Intitulé** : texte libre (input text)
- **Responsable** : affichage du `assigned_to` (readonly pour l'instant)
- **Pas de date d'échéance** en V1 (optionnel plus tard)

### Bouton d'ajout

- **Emplacement** : Barre d'actions en bas (à côté de "VALIDER UNE DÉCISION" quand celui-ci est masqué)
- **Texte** : "+ Ajouter une action"
- **Condition** : Owner uniquement, étape 11+
- **Comportement** : Ouvre un mini-modal ou un input inline :
  ```
  [Intitulé de l'action...] [Ajouter]
  ```

### Suppression

- **Condition** : Owner uniquement
- **UI** : Bouton ✕ sur la carte Action (au hover, discret)
- **Confirmation** : Non requise en V1 (la suppression est rare et l'owner est souverain)

---

## MODÈLE DE DONNÉES

### Objet Action (frontend)

```javascript
{
  id: string,           // UUID généré côté client
  text: string,         // Intitulé de l'action
  status: "TODO" | "IN_PROGRESS" | "DONE" | "CANCELLED",
  assigned_to: string,  // Nom du responsable
  decision_id: string,  // Référence à la décision parente
  created_at: string,   // ISO 8601
  created_by: string    // Nom de l'auteur
}
```

### Backend

- **Handler WS** : `action_set`, `action_update`, `action_delete`
- **Room state** : `_IrisTeamRoom.actions` (array)
- **Diffusion** : Broadcast à tous les participants sur chaque changement
- **Persistance** : Via `get_state()` comme pour les autres objets

---

## WORKFLOW

```
Décision validée (Phase 8)
    ↓
Owner clique "+ Ajouter une action"
    ↓
Saisit l'intitulé
    ↓
Action apparaît dans la liste (statut TODO, assigned_to = owner)
    ↓
Owner ou participants cliquent la checkbox pour avancer le statut
    ↓
Liste mise à jour en temps réel pour tous
```

---

## NON-RÉGRESSIONS

| Élément | État attendu |
|---|---|
| Phase 8 (Décision) | ✅ Conservée, inchangée |
| Carte décision | ✅ Toujours visible |
| Setup + titre | ✅ Conservé |
| Brief auto | ✅ Conservé |
| Stepper 5 phases | ✅ Conservé |
| Canvas exploration/travail | ✅ Conservé |
| Propositions | ✅ Conservées |
| Sources | ✅ Conservées |

---

## DÉFINITION DE FAIT

- [ ] Liste Actions affichée sous la carte Décision dans le canvas
- [ ] Champ `assigned_to` présent dans le modèle (même si UI ne montre qu'une option)
- [ ] Statuts : TODO, IN_PROGRESS, DONE, CANCELLED
- [ ] Lien d'origine visible : "Origine : 🎯 [décision]"
- [ ] Bouton "+ Ajouter une action" (owner, étape 11+)
- [ ] Checkbox cliquable pour changer le statut
- [ ] Pas de backlog libre, pas d'Actions orphelines
- [ ] Persistance backend via WS + state_sync
- [ ] Audit terrain Kimi validé

---

## LIENS

- Spécification globale : `docs/audit_ux/FEATURE_DECISION_V1.md`
- Rapport Phase 8 : `docs/audit_ux/2026-06-09-phase8/audit_report_v5.md`
- Mission status : `docs/audit_ux/MISSION_STATUS.md`
