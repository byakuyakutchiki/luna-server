# BRIEF P2 — Hiérarchie visuelle exécutive

**Priorité** : P2 (choix PO Ludovic)  
**Responsable implémentation** : Claude  
**Responsable audit** : Kimi  
**Statut** : 🚀 EN COURS  

---

## 🎯 Objectif

Créer une **hiérarchie visuelle exécutive** dans le workspace. L'utilisateur doit comprendre en 2 secondes la structure de la session sans lire :

```
MISSION
↓
QUESTION
↓
ÉTAPE ACTUELLE
↓
DÉCISION ACTIVE (si présente)
↓
ACTIONS
↓
RÉSERVES
```

---

## 🔴 Problèmes identifiés (captures V1.3b)

### 1. Question — noyée dans le header
- **Actuel** : `Audit UX post-déploiement` en 15px dans le header top, noyé entre logo et badge
- **Référence** : "NOUVELLE SESSION STRATÉGIQUE" en très grand, centré, avec sous-titre date
- **Attendu** : La question doit être **le titre principal du workspace**, visible immédiatement

### 2. Mission — invisible
- **Actuel** : Dans la sidebar droite, petit texte, pas de mise en valeur
- **Référence** : Section "MISSION" en haut de sidebar avec icône crayon, contenu bien délimité
- **Attendu** : Mission = bandeau ou carte visible en permanence

### 3. Étape actuelle — indicible
- **Actuel** : `Étape 3 / 13 — Collecte` en 11px gris, sous le titre
- **Attendu** : Badge/stepper visible, avec indication de progression claire

### 4. Décision active — pas mise en scène
- **Actuel** : Carte standard comme les propositions
- **Attendu** : Carte **imposante**, bordure spéciale, glow, centrée — c'est le centre du canvas

### 5. Actions / Réserves — pas de distinction hiérarchique
- **Actuel** : Empilées sans séparation visuelle forte
- **Attendu** : Actions en dessous de la décision, Réserves en dessous des actions, avec séparateurs visuels

---

## ✅ Critères d'acceptation

### CA-1 — Question en titre principal
- [ ] La question de session occupe **au moins 40% de la largeur du header central**
- [ ] Taille minimale : `20px`, weight `700`
- [ ] Centrée ou alignée gauche avec marge suffisante
- [ ] Sous-titre (date/owner) en `12px` gris en dessous

### CA-2 — Mission visible en permanence
- [ ] Mission affichée dans un **bandeau ou carte** en haut du canvas
- [ ] Ou : section "MISSION" agrandie dans la sidebar droite avec icône
- [ ] Minimum : titre "Mission" en `11px` uppercase + contenu en `13px` visible sans scroll

### CA-3 — Étape actuelle mise en valeur
- [ ] Badge ou stepper visible au-dessus ou à côté du titre
- [ ] Format : "PHASE 3 — COLLECTE" en majuscules, couleur violette (active)
- [ ] Numérotation claire : `3 / 13` en chiffres gras

### CA-4 — Décision = centre visuel
- [ ] Quand une décision est validée, elle est **la plus grande carte du canvas**
- [ ] Bordure spéciale (iris/violet) avec glow subtil
- [ ] Titre "DÉCISION" en badge au-dessus de la carte
- [ ] Actions et Réserves visuellement **subordonnées** (plus petites, indentées ou séparées)

### CA-5 — Séparation Actions / Réserves
- [ ] Section "ACTIONS" avec label visible avant la liste
- [ ] Section "RÉSERVES" avec label visible avant la liste
- [ ] Couleurs distinctes : Actions = vert/iris, Réserves = orange/rouge
- [ ] Compteurs visibles : "3 actions" / "2 réserves"

### CA-6 — Aucune régression fonctionnelle
- [ ] `yawatch_audit.py` passe 6/6
- [ ] Tous les IDs préservés (`#decisionText`, `#btnPropAdd`, etc.)

---

## 🎨 Référence visuelle

**Fichier** : `docs/ChatGPT Image Jun 9, 2026, 09_17_00 PM.png`

Points de référence clés :
- Header : titre centré grand + sous-tire + badge "MODE FOCUS"
- Stepper : 1 BRIEF → 2 COLLECTE → 3 ANALYSE → 4 DÉCISION → 5 LIVRABLE
- Empty state : "Aucune proposition active" en très grand avec "proposition" en couleur
- Sidebar droite : MISSION bien délimitée avec icône crayon

---

## 🚫 Règles d'or

- ❌ Aucun nouvel objet métier
- ❌ Aucune logique métier nouvelle
- 🔴 Aucune régression fonctionnelle tolérée
- ✅ Seulement du CSS + réorganisation HTML minimale
- ✅ Cibler les classes `.tw-hdr-*`, `.tw-canvas-*`, `.tw-decision-*`, `.tw-act-*`, `.tw-rsv-*`

---

## 📋 Checklist Claude

```
□ Modifier header pour titre question principal
□ Ajouter/afficher Mission en haut du canvas ou sidebar
□ Mettre en valeur l'étape actuelle (badge/stepper)
□ Styliser la carte Décision comme centre visuel
□ Séparer visuellement Actions et Réserves
□ Vérifier yawatch_audit.py 6/6
□ Déployer
□ Notifier Kimi pour audit
```

---

**Date brief** : 2026-06-10  
**Validé par** : Ludovic (PO)  
