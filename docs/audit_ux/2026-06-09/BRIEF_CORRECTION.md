# BRIEF DE CORRECTION — IRIS WORKSPACE
**Source** : Audit terrain Kimi (Phase 6)  
**Rapport complet** : `audit_report.md` (même dossier)  
**Fichier concerné** : `static/team_workspace.html`  
**Rôle Claude** : Implémentation uniquement. Aucune redéfinition produit.

---

## CONTEXTE

L'audit terrain a parcouru le workflow déployé :
Landing → Setup → Brief → Proposition soumise → Proposition activée → Source

Le modèle produit validé est :
```
Brief → Propositions → Proposition active → Dossier → Décision → Actions
```

L'interface déployée contient des vestiges du modèle ancien ("canvas d'objets génériques")
qui empêchent l'écran de raconter cette histoire.

**Screenshots preuves** : voir dossier `screenshots/` (6 captures du workflow complet)

---

## CORRECTIONS À APPLIQUER

### 🔴 CRITIQUE 1 — Supprimer `twActiveCard` (doublon)

**Problème** : La proposition active est affichée en 3 endroits simultanés :
- Header L2 (`#twCtxL2`)
- Carte `#twActiveCard` dans le canvas
- Section PROPOSITIONS en bas

**Règle produit** : `UN CONCEPT = UNE REPRÉSENTATION PRINCIPALE`

**Action** : Supprimer la carte `#twActiveCard` du DOM et du CSS.  
**Lignes** : HTML ~494-499, CSS ~432-434, JS ~2290-2306 (`renderProposals` met à jour `twActiveCard`).  
**Garder** : Header L2 comme seule représentation de la proposition active. La section PROPOSITIONS en bas reste le catalogue des pistes.

---

### 🔴 CRITIQUE 2 — Corriger l'empty state menteur

**Problème** : Le canvas vide affiche :  
*"Utilisez le bouton 'Proposition' pour soumettre une première piste."*  
Ce bouton a été supprimé de la barre d'actions (commit `69d3e05`). L'utilisateur cherche un bouton inexistant.

**Action** : Modifier le texte de `twEmptyMsg` pour refléter la réalité actuelle.  
**Ligne** : ~1002 (`renderObjects`)  
**Texte suggéré** : *"Aucune piste soumise. Utilisez la section PROPOSITIONS en bas pour soumettre une première piste."*

---

### 🟠 MAJEUR 1 — Canvas mode exploration = grille de propositions

**Problème** : En mode exploration (`!TW.activeProposalId`), les propositions sont affichées dans le canvas MAIS aussi dans la section PROPOSITIONS en bas. Le canvas affiche 1 carte dans un océan de vide. Le contenu principal est enterré.

**Action** : **Choisir UN SEUL endroit** pour afficher les propositions en mode exploration.

**Option recommandée par l'audit** :
- Garder la section PROPOSITIONS comme catalogue principal (elle est déjà bien faite avec statuts, boutons Activer/Archiver)
- ET déplacer les propositions du canvas vers cette section, OU rendre le canvas un véritable affichage principal en mode exploration

**Dans les deux cas** : le canvas ne doit pas être vide quand des propositions existent.

**Fichier** : `static/team_workspace.html` — logique `renderObjects()` vs `renderProposals()`

---

### 🟠 MAJEUR 2 — Stepper illisible

**Problème** : 13 étapes affichées comme des points minuscules (`< • • • COLLECTE • • • ... >`). Impossible de comprendre la progression.

**Action** : Réduire le nombre d'étapes affichées ou changer le rendu visuel.

**Option minimale** : Afficher seulement les étapes clés (Brief → Collecte → Analyse → Décision → Livrable) au lieu de 13 points.  
**Option maximale** : Remplacer le stepper par une barre de progression du dossier.

**Fichier** : `static/team_workspace.html` — `STEPS` (~704) et rendu `renderStepper()`

---

### 🟡 MINEUR 1 — Masquer "BRIEF MISSION" après validation

**Problème** : Le bouton `#twBriefBtn` reste visible en haut à droite même après que le brief soit défini.

**Action** : Masquer `#twBriefBtn` (ou le remplacer par un indicateur discret) dans `applyBrief()`.  
**Ligne** : `applyBrief()` ~1221

---

### 🟡 MINEUR 2 — Masquer "IRIS AUDIO" en session active

**Problème** : Le bouton de navigation vers Iris Audio est une distraction en pleine session workspace.

**Action** : Masquer le bouton "← Iris Audio" quand l'utilisateur est dans le workspace.  
**Ligne** : ~461 (header)

---

## LIVRABLE ATTENDU

Un patch propre sur `static/team_workspace.html` qui :
1. Supprime `twActiveCard`
2. Corrige l'empty state
3. Améliore l'affichage des propositions (sans doublon)
4. Rend le stepper lisible
5. Masque "BRIEF MISSION" après validation
6. Masque "IRIS AUDIO" en session

**Pas de modification backend.**  
**Pas de redéfinition du workflow produit.**  
**Pas d'ajout de nouvelles fonctionnalités.**

---

## RAPPORT COMPLET D'AUDIT

Voir `audit_report.md` dans ce même dossier pour le rapport détaillé avec contexte technique.
