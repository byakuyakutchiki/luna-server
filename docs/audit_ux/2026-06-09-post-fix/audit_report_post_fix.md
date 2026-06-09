# Rapport UX Post-Correctif — Iris Workspace
**Date** : 2026-06-09T13:01  
**Screenshots** : `/tmp/iris_audit/20260609_130107`  
**URL auditée** : `https://luna-beta-gly3g647na-ew.a.run.app/team`  
**Modèle** : Kimi vision + GPT-4o (validation croisée)  

---

## ✅ CORRIGÉ

### 1. Empty state menteur
**Avant** : *"Utilisez le bouton 'Proposition' pour soumettre une première piste."* (bouton inexistant)  
**Après** : *"Soumettez une piste dans la section PROPOSITIONS ci-dessous."*  
**Capture** : `02_workspace_empty.png`  
**Verdict** : ✅ Correct

### 2. Suppression de `twActiveCard`
**Avant** : Carte "PROPOSITION ACTIVE" dans le canvas en plus du header L2 et de la section PROPOSITIONS  
**Après** : Plus de carte dans le canvas. Seul le header L2 affiche la proposition active  
**Capture** : `05_proposition_active.png`  
**Verdict** : ✅ Correct

### 3. Masquage de "IRIS AUDIO"
**Avant** : Bouton de navigation visible en haut à droite  
**Après** : Disparu du header  
**Capture** : `02_workspace_empty.png`  
**Verdict** : ✅ Correct

---

## ⚠️ NOUVEAU PROBLÈME INTRODUIT

### Contradiction entre header L2 et canvas en mode travail
**Capture** : `05_proposition_active.png`  
**Description** :
- Header L2 affiche : *"Refondre le canvas pour afficher le dossier de décision"* → indique qu'une proposition est active
- Canvas central affiche : *"1 piste en attente d'activation. Activez la meilleure piste dans la section PROPOSITIONS ci-dessous pour démarrer le dossier."* → indique qu'aucune proposition n'est active
- Section PROPOSITIONS en bas affiche : *"ACTIVE"* + la proposition

**Problème** : Le canvas ne se met pas à jour quand une proposition devient active. Il reste en mode "attente d'activation" alors que la proposition EST active.

**Impact** : CRITIQUE — l'utilisateur ne sait pas dans quel état il est.

---

## ❌ NON CORRIGÉ

### Stepper 13 étapes illisible
**Capture** : `02_workspace_empty.png`, `03_after_brief.png`  
**Description** : Le stepper affiche toujours 13 points minuscules (`< • COLLECTE • • • ... >`)  
**Verdict** : ❌ Non corrigé

### Bouton "BRIEF MISSION" persistant
**Capture** : `03_after_brief.png`  
**Description** : Le bouton "BRIEF MISSION" reste visible en haut à droite après validation du brief  
**Verdict** : ❌ Non corrigé

### Canvas sous-utilisé en mode exploration
**Capture** : `04_proposition_submitted.png`  
**Description** : Les propositions sont toujours affichées uniquement dans la section PROPOSITIONS en bas. Le canvas reste un grand espace vide avec un message.  
**Verdict** : ❌ Non corrigé (seul le message a changé)

---

## RECOMMANDATIONS POUR CLAUDE (2ÈME TOUR)

### 🔴 CRITIQUE — Corriger la contradiction mode travail
**Comportement attendu** : Quand une proposition est active (`TW.activeProposalId` défini), le canvas doit afficher le contenu du dossier de la proposition active, PAS un message "en attente d'activation".

**Comportement actuel** : Le canvas affiche le même empty state qu'en mode exploration, créant une contradiction avec le header L2.

**Zone exacte** : Logique `renderObjects()` / `applyCanvasState()` dans `static/team_workspace.html`. Vérifier que le canvas bascule visuellement en mode "dossier actif" quand une proposition est activée.

### 🟠 MAJEUR — Rendre le stepper lisible
**Zone exacte** : `STEPS` (~704) et `renderStepper()`.  
**Action** : Réduire à 5-6 étapes clés ou changer le rendu visuel.

### 🟡 MINEUR — Masquer "BRIEF MISSION" après validation
**Zone exacte** : `applyBrief()` (~1221).  
**Action** : `document.getElementById('twBriefBtn').style.display = 'none'` ou remplacement par un indicateur discret.

### 🟠 MAJEUR — Canvas mode exploration
**Action** : En mode exploration, le canvas doit afficher la grille des propositions (pas seulement un empty state). La section PROPOSITIONS en bas peut être conservée comme catalogue secondaire, mais le contenu principal doit être visible dans le canvas.

---

## SYNTHÈSE

| Problème initial | Statut |
|---|---|
| Empty state menteur | ✅ Corrigé |
| Doublon `twActiveCard` | ✅ Corrigé |
| "IRIS AUDIO" distraction | ✅ Corrigé |
| Contradiction header/canvas | ⚠️ Nouveau problème |
| Stepper illisible | ❌ Non corrigé |
| "BRIEF MISSION" persistant | ❌ Non corrigé |
| Canvas sous-utilisé | ❌ Non corrigé |
