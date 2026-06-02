# Codex — Patch Iris Work Progress — Objectif 021

Date : 2026-06-03  
Agent : Codex  
Type : correctif UX niveau 1

---

## Target Cell

Objectif : 021 — Iris Capability Gateway  
Fonctionnalité : feedback de préparation Iris  
Utilisateur cible : Ludovic / owner / utilisateur Iris  
Target exacte : quand Iris dit qu'elle prépare, crée, rédige ou génère quelque chose, l'utilisateur doit voir immédiatement un état de travail visible, puis un résultat ou une alerte claire.

Capacités attendues :

- détecter les phrases de promesse de travail : "je prépare", "je vais créer", "patiente", etc. ;
- ouvrir le Command Screen automatiquement ;
- afficher étapes de préparation ;
- annuler l'attente quand un vrai rendu arrive ;
- afficher une alerte après timeout si aucun rendu n'arrive ;
- éviter que le transcript texte remplisse l'écran à la place du rendu visuel.

Chemin utilisateur :

1. utilisateur demande un business plan / tableau / document ;
2. Iris répond "je prépare..." ;
3. Command Screen affiche "Iris prépare" ;
4. si `render` arrive : le rendu remplace l'attente ;
5. si aucun rendu après 10s : message "Préparation trop longue".

Backend attendu : aucun changement.

Frontend attendu : `static/simli.html`.

Garde-fous : aucune action sensible, aucun SMS, aucun appel, aucun email, aucun déploiement automatique.

Preuve attendue :

- capture du Command Screen en état "Iris prépare" ;
- si blocage, capture du warning "Préparation trop longue" ;
- logs `ics_working` puis `ics_work_timeout` si aucun rendu.
- vérifier que les longues réponses Iris ne remplissent plus le transcript visible.

Preuve obtenue :

- compilation JS inline OK : `scripts ok 5` ;
- `git diff --check` OK.

Statut : code non prouvé terrain.

Décision Ludovic requise : oui pour déploiement Cloud Run.

---

## Changements

Fichier : `static/simli.html`

- Ajout CSS `.ics-work-card`, `.ics-work-step`, `.ics-work-warn`.
- Ajout `_icsLooksLikeWorkPromise(text)`.
- Ajout `_icsShowWorking(label, detail)`.
- Ajout `_icsShowWorkTimeout()`.
- Annulation du timer quand un vrai `render` arrive.
- Annulation du timer à la fermeture du panneau.
- Détection sur les transcripts Iris.
- Timeout réduit à 10 secondes.
- Transcript visible réduit : une ligne de demande utilisateur, messages Iris masqués.

---

## Limite

Ce patch ne crée pas le document ou le business plan côté serveur.

Il règle le défaut UX immédiat : l'utilisateur ne reste plus dans le doute quand Iris annonce qu'elle travaille, et le visuel reprend la priorité sur le texte.
