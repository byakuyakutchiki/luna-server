# Codex — Patch Iris Workbench V1 — Objectif 019

Date : 2026-06-02  
Agent : Codex  
Type : proposition appliquee / garde-fou  
Niveau : 1 pour le socle local, niveau 2 requis avant sauvegarde/action reelle

## Decision

Iris ne doit plus seulement dire qu'elle peut afficher un panneau. Elle doit avoir un Workbench visible.

Cette V1 ajoute un panneau de travail non destructif dans `static/simli.html` :

- entree texte pour ecrire a Iris ;
- panneau `Iris Workbench` visible ;
- ouverture automatique pour note, resume, courrier, checklist, tableau, document, panneau, workspace ;
- affichage des retours d'outils serveur, notamment `validation_required` ;
- copie et telechargement local du brouillon ;
- aucune sauvegarde cloud, aucun SMS, email, appel, invitation ou action sensible.

## Fichiers touches

- `static/simli.html`
- `integrations/openai/web_voice_bridge.py`

## Ce que ca debloque

1. Ludovic peut ecrire a Iris, pas seulement parler.
2. Iris peut afficher un brouillon dans un panneau visible.
3. Les actions sensibles restent bloquees dans le Workbench tant qu'elles ne sont pas validees.
4. Claude peut deployer et tester sans toucher aux outils reels.
5. Kimi peut auditer l'UX du panneau sur mobile.
6. DeepSeek peut verifier le flux texte WebSocket et les garde-fous.

## Tests effectues par Codex

- `py_compile` sur `integrations/openai/web_voice_bridge.py` et `luna_web.py`.
- Compilation JavaScript du script inline de `static/simli.html` via Node `vm.Script`.
- `git diff --check`.

## Tests terrain attendus apres deploy

1. Ecrire : `affiche le panneau de travail`
   - attendu : Workbench visible.
2. Ecrire : `prepare un tableau avec mes objectifs`
   - attendu : panneau `Tableau de travail`.
3. Ecrire : `redige un courrier pour un exploitant`
   - attendu : panneau `Courrier brouillon`.
4. Dire ou ecrire : `envoie un SMS`
   - attendu : action bloquee, `validation_required`, aucun SMS envoye.
5. Verifier mobile :
   - pas de superposition avec `Raccrocher` ;
   - champ texte utilisable ;
   - panneau lisible.

## Limites volontaires

Cette V1 n'est pas encore le Workbench final :

- pas d'edition riche ;
- pas de sauvegarde dans le porte-documents ;
- pas de PDF ;
- pas d'invitation collaborateur ;
- pas d'action reelle.

Ces fonctions doivent rester niveau 2/3 et passer par validation Ludovic.
