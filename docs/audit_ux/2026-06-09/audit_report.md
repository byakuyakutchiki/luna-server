# Rapport UX — Iris Workspace
**Date** : 2026-06-09T12:23:53.468625
**Screenshots** : `/tmp/iris_audit/20260609_121007`
**Modèle** : gpt-4o

---

## CRITIQUE

**Doublon de concept : Proposition active**
- La proposition active apparaît à la fois dans le header L2, la carte `twActiveCard`, et la section PROPOSITIONS.
- Capture concernée : 05_proposition_active.png
- Zone UI exacte : Header L2, `twActiveCard`, section PROPOSITIONS

**Empty state incorrect**
- Le message "Utilisez le bouton 'Proposition'" est affiché alors que ce bouton n'est pas visible dans la barre d'actions.
- Capture concernée : 02_workspace_empty.png
- Zone UI exacte : Canvas central

---

## MAJEUR

**Hiérarchie visuelle incohérente**
- Le contenu principal (propositions) est souvent caché ou peu visible par rapport aux éléments secondaires.
- Capture concernée : 04_proposition_submitted.png
- Zone UI exacte : Canvas central

**Stepper illisible**
- Le stepper affiche 13 étapes sous forme de points minuscules, rendant la lecture difficile.
- Capture concernée : 02_workspace_empty.png
- Zone UI exacte : Stepper en haut

---

## MINEUR

**Bouton sans rôle clair**
- Le bouton "Importer Source" n'indique pas clairement son rôle dans le contexte actuel.
- Capture concernée : 06_source_added.png
- Zone UI exacte : Barre d'actions en bas

---

## RECOMMANDATIONS

1. **Éliminer les doublons de concept**
   - Comportement attendu : La proposition active ne devrait apparaître qu'à un seul endroit pour éviter la confusion.
   - Comportement actuel : La proposition active est visible dans plusieurs zones.
   - Zone exacte à modifier : Header L2, `twActiveCard`, section PROPOSITIONS
   - Priorité : CRITIQUE

2. **Corriger l'empty state du canvas**
   - Comportement attendu : Le message devrait refléter les actions réellement disponibles.
   - Comportement actuel : Le message indique un bouton inexistant.
   - Zone exacte à modifier : Canvas central
   - Priorité : CRITIQUE

3. **Améliorer la hiérarchie visuelle**
   - Comportement attendu : Les propositions doivent être clairement visibles et prioritaires.
   - Comportement actuel : Les propositions sont souvent cachées ou peu visibles.
   - Zone exacte à modifier : Canvas central
   - Priorité : MAJEUR

4. **Rendre le stepper lisible**
   - Comportement attendu : Les étapes doivent être clairement identifiables.
   - Comportement actuel : Les étapes sont représentées par des points minuscules.
   - Zone exacte à modifier : Stepper en haut
   - Priorité : MAJEUR

5. **Clarifier le rôle des boutons**
   - Comportement attendu : Chaque bouton doit indiquer clairement son rôle et son utilité.
   - Comportement actuel : Le bouton "Importer Source" manque de clarté.
   - Zone exacte à modifier : Barre d'actions en bas
   - Priorité : MINEUR

---

## CONTEXTE TECHNIQUE POUR CLAUDE (enrichissement Kimi)

Fichier clé : `static/team_workspace.html`

| Problème | Zone exacte dans le code | Indication |
|---|---|---|
| Doublon `twActiveCard` | Lignes ~432-499 | `#twActiveCard` affiche la proposition active dans le canvas. Supprimer car L2 (`#twCtxL2`) suffit. |
| Empty state menteur | Ligne ~1002 | `twEmptyMsg` dit `"Utilisez le bouton 'Proposition'"` mais le bouton a été supprimé de la barre d'actions (commit `69d3e05`). Remplacer par `"Soumettez une piste dans la section PROPOSITIONS ci-dessous"`. |
| Propositions dans canvas + section PROPOSITIONS | `renderObjects()` ligne ~992 et `renderProposals()` ligne ~2248 | En mode exploration, `renderObjects()` affiche les propositions dans le canvas. `renderProposals()` les affiche aussi en bas. Choisir UN SEUL endroit. |
| Stepper 13 étapes | `STEPS` ligne ~704, `CANVAS_STATE` ligne ~813 | Le tableau `STEPS` a 13 items. Le stepper les affiche comme des points. Réduire à 5-6 étapes ou changer le rendu. |
| Canvas = grille d'objets | `CANVAS_STATE` lignes ~813-850 | Le canvas est encore un conteneur d'objets génériques (`prop`, `source`, `decision`, `action`, `synthesis`). Transformer en dossier structuré avec des sections fixes. |
| `BRIEF MISSION` persistant | Ligne ~461 | `#twBriefBtn` reste visible après validation du brief. Ajouter `style.display='none'` ou le remplacer par un indicateur discret dans `applyBrief()`. |
| `IRIS AUDIO` distraction | Ligne ~461 | Bouton de navigation externe dans le header. À masquer en session active. |
