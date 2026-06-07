# Iris Workspace V3 — Schéma de flux par étape

> Document de cadrage à valider par Ludovic avant toute implémentation.
> Source : IRIS_WORKSPACE_V3_CAHIER_FONDATEUR_IMPLEMENTATION_FINAL.md
> Auteur : Claude — 2026-06-07

---

## Principe absolu

**Le workspace est piloté par l'étape courante.**
Une étape n'affiche que les éléments autorisés pour cette étape.
Aucun objet d'une étape future n'est visible ou accessible.

---

## Couches permanentes (présentes à toutes les étapes)

Ces éléments ne changent jamais :

| Couche | Contenu |
|---|---|
| Header | YAWatch Industries / Iris Workspace / Titre session / Étape courante |
| Stepper | 13 étapes, étape active mise en avant, passées = done, futures = locked |
| Orbite haute | Tiles participants humains (caméra / avatar / micro / halo orateur) |
| Orbite basse | Owner + Iris (vert émeraude) + IQ (cyan) + Luna (violet) |
| Spectateurs | Rail compact séparé |
| Barre actions | Actions **contextuelles uniquement** selon l'étape — rien d'autre |

---

## Flux des 13 étapes

### Étape 1 — Entrée

**Objectif :** Configurer la présence avant de commencer.

| Zone | Contenu visible |
|---|---|
| Plan central | Message d'accueil Iris + invitation à activer caméra/micro |
| Orbite | Tiles participants avec statut : caméra off, micro off, en attente |
| Barre actions | Activer caméra · Activer micro · Confirmer rôle |

**Interdit :** Aucune carte. Aucun brief. Aucun objet de travail.

---

### Étape 2 — Brief mission

**Objectif :** Définir le sujet, le contexte et le livrable attendu.

| Zone | Contenu visible |
|---|---|
| Plan central | Formulaire brief (titre, domaine, objectif, contexte, livrable) + carte résumé brief quand validé |
| Orbite | Participants présents · Iris en statut "Prépare la salle" |
| Barre actions | Définir le brief · Valider le brief |

**Interdit :** Propositions. Sources. Décisions. Synthèses. Analyses.

---

### Étape 3 — Collecte des propositions

**Objectif :** Rassembler les idées et notes brutes.

| Zone | Contenu visible |
|---|---|
| Plan central | Cartes PROPOSITION uniquement (ajoutées par les participants) |
| Plan central | Zone note rapide : texte libre non catégorisé |
| Orbite | Participants · Qui parle (halo) · Qui ajoute une carte |
| Panneau sources | Rail latéral réduit : accès aux sources (fichier/lien/note) sans analyse |
| Barre actions | + Proposition · + Note · Ajouter source (panneau latéral) |

**Interdit :** Décisions. Synthèses. Recommandation Luna. Analyse IQ. Vote.

**Règle :** Les sources sont importées et stockées mais pas encore analysées ni affichées sur le plan central.

---

### Étape 4 — Organisation Iris

**Objectif :** Iris classe et regroupe les propositions en thèmes.

| Zone | Contenu visible |
|---|---|
| Plan central | Propositions regroupées par thèmes (Iris les déplace et les nomme) |
| Plan central | Cartes thème créées par Iris avec les propositions sous-jacentes |
| Plan central | Animation de classement (cartes qui se regroupent — subtile) |
| Orbite | Iris en statut "Active — Organisation" (halo vert émeraude) |
| Barre actions | Déclencher Iris · Valider l'organisation · Modifier un groupe |

**Interdit :** Décisions. Synthèses. Vote. Analyse IQ.

---

### Étape 5 — Vote de priorité

**Objectif :** L'équipe choisit l'axe prioritaire à approfondir.

| Zone | Contenu visible |
|---|---|
| Plan central | Groupes thématiques avec bouton vote par groupe |
| Plan central | Compteur de votes en temps réel par groupe |
| Plan central | Résultat : groupe gagnant mis en avant à la fin |
| Barre actions | Voter · Clôturer le vote (owner) |

**Interdit :** Sources affichées. Analyse. Décision. Synthèse.

---

### Étape 6 — Analyse IQ des sources

**Objectif :** IQ lit les sources et produit un rapport d'analyse.

| Zone | Contenu visible |
|---|---|
| Plan central | Proposition gagnante (issue du vote, figée en lecture) |
| Plan central | Sources sélectionnées (preview document ou résumé URL) |
| Plan central | Rapport IQ : risques · opportunités · points clés · chiffres extraits |
| Plan central | Connexions visuelles entre la proposition et les points IQ (lignes cyan) |
| Orbite | IQ en statut "Analyse en cours" (halo cyan) |
| Barre actions | Sélectionner sources à analyser · Lancer analyse IQ · Valider le rapport |

**Interdit :** Décisions. Synthèse Iris. Recommandation Luna.

---

### Étape 7 — Débat humain

**Objectif :** Chaque participant réagit avec des objections ou arguments.

| Zone | Contenu visible |
|---|---|
| Plan central | Proposition gagnante + rapport IQ (lecture seule) |
| Plan central | Zone objections : cartes OBJECTION par participant |
| Plan central | Indicateur : objection prise en compte / en attente |
| Orbite | Participants avec halo orateur · Main levée visible |
| Barre actions | + Objection · + Argument · Valider ma contribution |

**Interdit :** Synthèse. Recommandation. Décision. Vote final.

---

### Étape 8 — Refonte Iris

**Objectif :** Iris intègre les objections et génère une proposition améliorée.

| Zone | Contenu visible |
|---|---|
| Plan central | V1 (proposition originale, affichée en lecture atténuée) |
| Plan central | V2 (nouvelle proposition générée par Iris) |
| Plan central | Diff visuel V1 → V2 : ajouts verts, suppressions barrées |
| Plan central | Objections résolues (chaque objection liée à la modification qui la couvre) |
| Orbite | Iris en statut "Refonte" |
| Barre actions | Déclencher refonte · Demander V3 · Valider la version |

**Interdit :** Décision finale. Recommandation Luna. Export.

---

### Étape 9 — Comparaison IQ

**Objectif :** IQ compare les versions et produit un tableau comparatif.

| Zone | Contenu visible |
|---|---|
| Plan central | Tableau comparatif V1 / V2 (/ V3 si disponible) |
| Plan central | Critères : pertinence, risques couverts, faisabilité, alignement brief |
| Plan central | Score IQ par version (pas un choix — une analyse) |
| Orbite | IQ en statut "Comparaison" (halo cyan) |
| Barre actions | Afficher V1 · Afficher V2 · Demander comparaison IQ |

**Interdit :** Décision. Recommandation Luna. Export.

---

### Étape 10 — Recommandation Luna

**Objectif :** Luna formule une recommandation stratégique.

| Zone | Contenu visible |
|---|---|
| Plan central | Carte recommandation Luna (violet, centrale, dominante) |
| Plan central | Brief rappelé en haut · Version recommandée mise en avant |
| Plan central | Conditions de mise en œuvre formulées par Luna |
| Plan central | Sources et objections en fond (lecture atténuée) |
| Orbite | Luna en statut "Arbitrage" (halo violet pulsant) |
| Barre actions | Demander recommandation · Voir le raisonnement |

**Interdit :** Décision finale (c'est une recommandation, pas une décision). Export.

---

### Étape 11 — Validation finale

**Objectif :** L'équipe vote pour accepter ou retourner en refonte.

| Zone | Contenu visible |
|---|---|
| Plan central | Version finale + recommandation Luna |
| Plan central | Panel vote : Valider · Retourner en refonte · Rejeter |
| Plan central | Résultats vote en temps réel |
| Plan central | Carte DÉCISION créée si vote positif |
| Barre actions | Voter · Clôturer le vote (owner) |

**Interdit :** Export avant décision validée.

---

### Étape 12 — Livrable

**Objectif :** Produire un document final exportable.

| Zone | Contenu visible |
|---|---|
| Plan central | Carte DÉCISION validée |
| Plan central | Plan d'action (items d'action avec responsable) |
| Plan central | Aperçu du livrable Iris (résumé, décisions, tâches, sources) |
| Plan central | Boutons export : PDF · Word · Plan d'action |
| Orbite | Iris en statut "Production livrable" |
| Barre actions | Générer PDF · Générer Word · Créer plan d'action |

**Interdit :** Nouvelles propositions. Nouvelles objections.

---

### Étape 13 — Distribution

**Objectif :** Partager le livrable et archiver la session.

| Zone | Contenu visible |
|---|---|
| Plan central | Liste des participants avec case d'envoi |
| Plan central | Aperçu du livrable distribué |
| Plan central | Confirmation d'archivage session |
| Barre actions | Envoyer aux participants · Archiver la session · Nouvelle session |

---

## Tableau récapitulatif des objets autorisés par étape

| Étape | Proposition | Source | Objection | Analyse IQ | Synthèse Iris | Reco Luna | Décision | Export |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 Entrée | — | — | — | — | — | — | — | — |
| 2 Brief | — | — | — | — | — | — | — | — |
| 3 Collecte | ✅ | stockée | — | — | — | — | — | — |
| 4 Organisation | lecture | — | — | — | groupes Iris | — | — | — |
| 5 Vote | lecture | — | — | — | groupes | — | — | — |
| 6 Analyse IQ | lecture | ✅ | — | ✅ | — | — | — | — |
| 7 Débat | lecture | lecture | ✅ | lecture | — | — | — | — |
| 8 Refonte Iris | V1 (atténué) | — | lecture | — | V2 Iris | — | — | — |
| 9 Comparaison | lecture | — | — | comparatif | V1+V2 | — | — | — |
| 10 Reco Luna | lecture | — | — | — | lecture | ✅ | — | — |
| 11 Validation | lecture | — | — | — | lecture | lecture | ✅ si voté | — |
| 12 Livrable | — | — | — | — | résumé | — | lecture | ✅ |
| 13 Distribution | — | — | — | — | — | — | — | lecture |

---

## Ce que le plan central n'est PAS

- Pas une grille de cartes statiques
- Pas un Trello
- Pas un tableau de bord

## Ce que le plan central EST

- Un espace de travail **piloté par l'étape**
- Les objets apparaissent, évoluent, se transforment et disparaissent selon la progression
- À l'étape 3 : cartes propositions en cours d'ajout (vivant)
- À l'étape 4 : les mêmes cartes se regroupent en thèmes (Iris anime)
- À l'étape 8 : la proposition V1 s'atténue, V2 apparaît à côté avec diff
- À l'étape 10 : Luna occupe le centre, tout le reste recule

---

## Ce qui n'est pas encore implémenté (phases futures)

| Fonctionnalité | Phase |
|---|---|
| Caméra réelle (SimliVideoTile / WebRTC) | P0.2 |
| Upload fichier réel + preview PDF/DOCX | P0.3 |
| Stepper avec transitions entre étapes | P0.4 |
| Vote multi-participants temps réel (WebSocket) | P0.4 |
| Mémoire vivante (IdeaVersion, diff, restauration) | P1.1 |
| Refonte Iris connectée au LLM | P1.2 |
| Analyse IQ connectée au LLM | P1.3 |
| Recommandation Luna connectée au LLM | P1.4 |
| Export PDF/Word réel | P2 |
| Distribution aux participants | P2 |

---

## Diagnostic de l'implémentation actuelle (V3 déployée)

**Problème principal :** Le plan central affiche simultanément propositions, sources, décisions et synthèses, indépendamment de l'étape. C'est une grille de cartes statique, pas un espace de travail piloté.

**Problème secondaire :** Les tiles participants montrent des initiales, pas de présence réelle (caméra, micro, halo orateur, prise de parole).

**Problème tertiaire :** Les actions de la barre changent mais les objets sur le canvas ne changent pas selon l'étape.

---

## Prochaine implémentation (après validation de ce document)

**Cible unique et prioritaire : le moteur d'étape.**

```
canvasState[étape] → objets filtrés + mode d'affichage (lecture / édition / animation)
```

Chaque transition d'étape :
1. Filtre les objets visibles
2. Change le mode de chaque objet (éditable / lecture / atténué)
3. Met à jour la barre d'actions
4. Déclenche une animation de transition (discrète)

**Ce travail ne touche pas l'esthétique.** La palette YAWatch Corporate est en place. Ce qui change : le comportement.

---

> **En attente de validation Ludovic avant toute implémentation.**
