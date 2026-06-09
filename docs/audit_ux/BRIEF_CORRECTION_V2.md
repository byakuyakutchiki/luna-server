# BRIEF DE CORRECTION V2 — IRIS WORKSPACE
**Source** : Audit terrain #2 post-correctif (Kimi)  
**Date** : 2026-06-09  
**Fichier concerné** : `static/team_workspace.html`  
**Rôle Claude** : Implémentation uniquement. Aucune redéfinition produit.

---

## CONTEXTE

Claude a déployé un premier patch de correctifs (rev 00628).  
L'audit terrain #2 a été exécuté sur `https://luna-beta-gly3g647na-ew.a.run.app/team`.

**Résultat** :
- ✅ 3 problèmes corrigés (empty state, `twActiveCard`, IRIS AUDIO)
- ⚠️ 1 nouveau problème CRITIQUE introduit (contradiction header/canvas)
- ❌ 3 problèmes non corrigés (stepper, BRIEF MISSION, canvas sous-utilisé)

**Preuves visuelles** : `docs/audit_ux/2026-06-09-post-fix/screenshots/`

---

## 🔴 CRITIQUE — Contradiction header / canvas en mode travail

### Problème
Quand une proposition est activée, il y a une contradiction directe à l'écran :

| Zone | Message | Interprétation |
|---|---|---|
| **Header L2** | *"Refondre le canvas pour afficher le dossier de décision"* | Proposition active |
| **Canvas central** | *"1 piste en attente d'activation. Activez la meilleure piste... pour démarrer le dossier."* | Aucune proposition active |
| **Section PROPOSITIONS** | Badge "ACTIVE" + proposition listée | Proposition active |

L'utilisateur ne sait pas dans quel état il est.

### Cause probable
Le canvas n'a pas de logique de basculement entre **Mode Exploration** et **Mode Travail**.  
Quand `TW.activeProposalId` est défini, le canvas continue d'afficher le même empty state que quand aucune proposition n'est active.

### Action attendue
Dans `renderObjects()` ou `applyCanvasState()`, ajouter une branche conditionnelle :

```
SI TW.activeProposalId est défini :
  → Canvas affiche le dossier de la proposition active
  OU à minima un indicateur clair "Dossier actif : [titre proposition]"
  → L'empty state "piste en attente d'activation" disparaît
SINON :
  → Canvas affiche le message actuel d'exploration
```

**Zone exacte** : logique `renderObjects()` dans `static/team_workspace.html` (~ligne 992) + `applyCanvasState()` (~ligne 1326).

**Capture preuve** : `05_proposition_active.png`

---

## 🟠 MAJEUR — Stepper 13 étapes illisible

### Problème
Le stepper affiche toujours 13 points minuscules (`< • COLLECTE • • • ... >`).  
Impossible de comprendre la progression.

### Action attendue
Réduire le nombre d'étapes affichées ou changer le rendu.

**Option minimale** : Afficher 5-6 étapes clés (Brief → Collecte → Analyse → Décision → Livrable) au lieu de 13 points.  
**Zone exacte** : `STEPS` (~ligne 704) et `renderStepper()`.

**Capture preuve** : `02_workspace_empty.png`, `03_after_brief.png`

---

## 🟠 MAJEUR — Canvas sous-utilisé en mode exploration

### Problème
En mode exploration (`!TW.activeProposalId`), les propositions sont affichées uniquement dans la section PROPOSITIONS en bas. Le canvas reste un grand espace vide avec un simple message.

### Action attendue
Le canvas doit devenir la grille principale des propositions en mode exploration.  
La section PROPOSITIONS en bas peut rester comme catalogue secondaire, mais le contenu principal doit être dans le canvas.

**Zone exacte** : `renderObjects()` en mode exploration + `renderProposals()`.

**Capture preuve** : `04_proposition_submitted.png`

---

## 🟡 MINEUR — "BRIEF MISSION" persistant après validation

### Problème
Le bouton "BRIEF MISSION" reste visible en haut à droite après que le brief soit défini.

### Action attendue
Masquer `#twBriefBtn` dans `applyBrief()` ou le remplacer par un indicateur discret.

**Zone exacte** : `applyBrief()` (~ligne 1221).

**Capture preuve** : `03_after_brief.png`

---

## LIVRABLE ATTENDU

Un patch propre sur `static/team_workspace.html` qui :
1. **CRITIQUE** : Bascule le canvas en mode travail quand une proposition est active
2. **MAJEUR** : Rend le stepper lisible (≤6 étapes ou nouveau rendu)
3. **MAJEUR** : Affiche les propositions dans le canvas en mode exploration
4. **MINEUR** : Masque "BRIEF MISSION" après validation du brief

**Pas de modification backend.**  
**Pas de redéfinition du workflow produit.**  
**Pas de nouvelles fonctionnalités.**

---

## RAPPORTS COMPLÉMENTAIRES

- `docs/audit_ux/2026-06-09-post-fix/audit_report_post_fix.md` — Analyse Kimi détaillée
- `docs/audit_ux/MISSION_STATUS.md` — État global de la mission
- `docs/audit_ux/2026-06-09-post-fix/screenshots/` — Captures du workflow post-correctif
