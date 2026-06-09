# Rapport UX — Iris Workspace
**Date** : 2026-06-09T13:03:13.503523
**Screenshots** : `/tmp/iris_audit/20260609_130107`
**Modèle** : gpt-4o

---

## CRITIQUE

**Doublon de concept : Proposition active**
- La proposition active est visible dans le header L2, la carte `twActiveCard`, et la section PROPOSITIONS.
- Capture concernée : 05_proposition_active.png
- Zone UI exacte : Header L2, `twActiveCard`, section PROPOSITIONS

**Empty state du canvas**
- Le message "Soumettez une piste dans la section PROPOSITIONS ci-dessous" est visible alors que le bouton de proposition n'est pas dans la barre d'actions.
- Capture concernée : 02_workspace_empty.png
- Zone UI exacte : Canvas central

## MAJEUR

**Hiérarchie visuelle incohérente**
- Le contenu principal (propositions) est caché tandis que le contenu secondaire (participants, étapes) est plus visible.
- Capture concernée : 02_workspace_empty.png, 03_after_brief.png
- Zone UI exacte : Sidebar gauche, canvas central

**Stepper illisible**
- Le stepper affiche 13 étapes sous forme de points minuscules, rendant la progression difficile à suivre.
- Capture concernée : 02_workspace_empty.png, 03_after_brief.png
- Zone UI exacte : Header, section étapes

## MINEUR

**Bouton sans rôle clair : "Importer Source"**
- Le bouton "Importer Source" n'indique pas clairement son rôle dans le contexte actuel.
- Capture concernée : 06_source_added.png
- Zone UI exacte : Bas de l'écran, à côté de "COLLECTE"

## RECOMMANDATIONS

1. **Éliminer le doublon de la proposition active**
   - Comportement attendu : La proposition active ne doit apparaître que dans une seule zone pour éviter la confusion.
   - Comportement actuel : Visible dans le header L2, `twActiveCard`, et section PROPOSITIONS.
   - Zone exacte à modifier : Supprimer l'affichage dans la section PROPOSITIONS.
   - Priorité : CRITIQUE

2. **Clarifier l'empty state du canvas**
   - Comportement attendu : Le message doit refléter l'action actuelle disponible.
   - Comportement actuel : Indique une action non disponible.
   - Zone exacte à modifier : Message dans le canvas central.
   - Priorité : CRITIQUE

3. **Améliorer la hiérarchie visuelle**
   - Comportement attendu : Le contenu principal doit être plus visible que le contenu secondaire.
   - Comportement actuel : Contenu secondaire plus visible.
   - Zone exacte à modifier : Taille et position des éléments dans le canvas et la sidebar.
   - Priorité : MAJEUR

4. **Rendre le stepper lisible**
   - Comportement attendu : Les étapes doivent être clairement identifiables.
   - Comportement actuel : Points minuscules et illisibles.
   - Zone exacte à modifier : Header, section étapes.
   - Priorité : MAJEUR

5. **Clarifier le rôle du bouton "Importer Source"**
   - Comportement attendu : Le bouton doit indiquer clairement son rôle et son contexte.
   - Comportement actuel : Rôle peu clair.
   - Zone exacte à modifier : Bouton dans le bas de l'écran.
   - Priorité : MINEUR