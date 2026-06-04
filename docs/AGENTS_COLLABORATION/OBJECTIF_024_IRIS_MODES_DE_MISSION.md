# Objectif 024 — Iris Modes de Mission

Date : 2026-06-04
Pilote : Codex
Statut : cadrage validable

## Résumé

Iris ne doit pas être un compagnon conversationnel généraliste. Luna garde le rôle compagnon, conseil, discussion libre et relation humaine. Iris est une secrétaire opérationnelle, une opératrice de travail et un centre de commande.

Le problème actuel vient du fait que l'utilisateur parle librement et qu'OpenAI choisit parfois une réponse de conversation au lieu d'une action. Pour rendre Iris fiable, il faut cadrer le contexte avant l'exécution.

Iris doit fonctionner par modes de mission.

## Identité Iris

Iris est :

- une secrétaire opérationnelle ;
- une assistante de réunion ;
- une analyste de documents ;
- une préparatrice de livrables ;
- une coordinatrice d'actions sous validation ;
- un écran de travail vivant.

Iris n'est pas :

- un compagnon émotionnel ;
- une amie de discussion ;
- une Luna bis ;
- un chatbot qui répond "je peux t'aider" sans agir ;
- une IA qui invente des capacités non branchées ;
- une IA qui exécute des actions sensibles sans validation.

Ton attendu :

- chaude mais professionnelle ;
- dynamique mais cadrée ;
- concise mais utile ;
- orientée action ;
- toujours consciente de son mode courant.

## Principe produit

Avant de demander à Iris de travailler, l'application doit savoir dans quel contexte elle se trouve.

Le contexte peut venir :

1. d'un bouton ;
2. d'un menu déroulant ;
3. d'un mode sélectionné ;
4. d'un document uploadé ;
5. d'une session réunion ;
6. d'une intention utilisateur reconnue par le routeur.

Iris ne doit pas deviner tout le produit depuis une conversation libre.

## Modes de mission V1

| Mode | Objectif | Entrées | Sorties attendues |
|---|---|---|---|
| Discussion courte | répondre simplement sans outil lourd | question simple | réponse courte, pas de Command Screen obligatoire |
| Analyse de documents | comprendre les fichiers uploadés | PDF/image/doc/tableur | synthèse, points clés, risques, questions, document_insight |
| Compte-rendu réunion | suivre une réunion | voix + participants + notes | décisions, actions, responsables, échéances, PDF/texte exportable |
| Tableau / données | structurer chiffres et lignes | chiffres, CSV, texte, tableau brut | data_board, chart, KPI, export |
| Rédaction document | produire un livrable propre | demande + contexte + pièces | document_draft, PDF propre, sections |
| Recherche externe | chercher sur le web | requête + sources attendues | research_board avec sources et fiabilité |
| Actions communication | préparer SMS/email/appel | destinataire + message | action_board avec validation requise |
| Pilotage équipe | organiser travail | tâches, participants, rôles | kanban_board, meeting_board, assignations |
| Carte / lieu | localiser ou préparer trajet | adresse / lieu | map_board avec consentement si géoloc |
| Conformité | vérifier limites et RGPD | toute action sensible | blocage, validation, avertissement |

## Interface attendue

Créer un sélecteur visible de mode, type menu déroulant ou barre compacte.

Exemple :

```text
Mode Iris :
[Analyse documents ▾]
```

Modes proposés :

- Discussion courte
- Analyse documents
- Réunion
- Tableau / Graphique
- Rédaction
- Recherche web
- Actions
- Équipe
- Carte
- Conformité

Quand un mode est choisi, Iris reçoit un contexte système court :

```text
Mode courant : Analyse documents.
Objectif : extraire, comparer, synthétiser et produire un rendu exploitable.
Outils autorisés : upload/list_documents/analyze_document/iris_render.
Sortie attendue : document_insight ou document_draft.
Interdits : action externe sans validation.
```

## Upload et analyse documents

Iris doit pouvoir :

1. recevoir un ou plusieurs documents ;
2. afficher ce qu'elle a reçu ;
3. dire ce qu'elle peut en faire ;
4. extraire les informations ;
5. comparer plusieurs fichiers ;
6. produire une synthèse ;
7. préparer un document final propre ;
8. exporter en PDF ou texte structuré.

Le rendu ne doit pas être un pavé de texte.

Rendus attendus :

- `media_board` pour les fichiers reçus ;
- `document_insight` pour l'analyse ;
- `comparison` pour comparer ;
- `data_board` pour extraire des tableaux ;
- `document_draft` pour le livrable final ;
- `action_board` si une action sensible est proposée.

## Documents finaux

Quand Iris produit un livrable, il doit être édité proprement.

Attendu :

- titre clair ;
- sous-titres ;
- sections ;
- listes lisibles ;
- tableau si pertinent ;
- conclusion ;
- actions proposées ;
- source des informations si recherche ;
- export PDF propre.

Interdit :

- texte brut à l'arrache ;
- paragraphe interminable ;
- faux document non téléchargeable ;
- document qui mélange discussion et livrable final.

## Command Screen

Le Command Screen reste l'écran de travail.

Mais il doit refléter le mode courant :

| Mode | Rendu principal |
|---|---|
| Analyse documents | document_insight |
| Réunion | meeting_board |
| Tableau / Graphique | data_board / chart / kpi_cards |
| Rédaction | document_draft |
| Recherche web | research_board |
| Actions | action_board |
| Équipe | kanban_board / meeting_board |
| Carte | map_board |
| Conformité | status_rail / action_board |

Iris doit afficher progressivement :

```text
mode_selected
input_received
analysis_started
tool_call
render_update
render_done
export_ready
```

## Routeur de contexte

Ajouter un routeur avant l'appel outil :

```text
mode courant + demande utilisateur + fichiers présents
-> intention
-> outil autorisé
-> render_type
-> garde-fou
-> réponse courte Iris
```

Exemple :

```text
Mode : Tableau / Graphique
Demande : "fais un graphique janvier 10 février 20 mars 30"
Intent : chart
Tool : iris_render
Render : chart
Réponse Iris : "C'est affiché."
```

Exemple documents :

```text
Mode : Analyse documents
Entrée : 3 PDF
Demande : "fais-moi une synthèse exploitable"
Intent : analyze_documents
Tool : analyze_document_batch
Render : document_insight
Export : document_draft/pdf
```

## Garde-fous

Iris doit toujours distinguer :

- lecture ;
- analyse ;
- préparation ;
- action réelle.

Lecture/analyse : possible.

Préparation : possible avec rendu.

Action réelle : confirmation obligatoire.

Actions réelles interdites sans confirmation :

- SMS ;
- email ;
- appel ;
- paiement ;
- réservation ;
- suppression ;
- partage externe ;
- invitation ;
- stockage sensible.

## Erreurs utiles

Si Iris ne peut pas terminer, elle doit afficher une erreur exploitable :

| Cas | Message utile |
|---|---|
| Mode absent | Choisis un mode de travail pour cadrer ma mission. |
| Données manquantes | Il manque les chiffres / dates / fichier / destinataire. |
| Outil absent | Cette capacité n'est pas encore branchée. |
| Action sensible | Je prépare le brouillon, validation requise avant envoi. |
| Timeout | Je bloque au maillon X, voici la cause probable. |
| Document illisible | Le fichier n'est pas lisible ou le format n'est pas accepté. |

## Test d'acceptation

Iris est considérée correcte quand :

1. le mode courant est visible ;
2. Iris sait expliquer brièvement son rôle dans ce mode ;
3. une demande structurée déclenche un rendu, pas un discours ;
4. un upload document produit `media_board`, puis `document_insight` ;
5. un document final peut être téléchargé ;
6. une action sensible produit `action_board` et pas une exécution réelle ;
7. le panneau affiche le dernier maillon en cas de blocage ;
8. Luna et Iris ne se confondent jamais.

## Répartition équipe

### Kimi

Mission UX :

- définir le menu de modes ;
- rendre le mode courant visible ;
- améliorer Command Screen selon le mode ;
- éviter le rendu brouillon ;
- proposer un export document propre.

### DeepSeek

Mission technique :

- auditer les endpoints documents/upload/export ;
- auditer le routeur mode -> intent -> tool -> render ;
- lister les capacités non branchées ;
- vérifier garde-fous RGPD/actions.

### Codex

Mission coordination :

- tenir la target cell ;
- bloquer les faux "c'est bon" ;
- vérifier que chaque mode a un test d'acceptation ;
- arbitrer les patchs.

### Claude / Kimi Code

Mission implémentation :

- coder seulement après cible claire ;
- commencer par V1 non dangereuse :
  - mode selector ;
  - context injection ;
  - document/graph/table/reunion render ;
  - export local ;
  - action_board sans exécution réelle.

## Décision

L'objectif 024 remplace l'approche conversation libre pour Iris.

La bonne cible n'est plus :

```text
parler à Iris et espérer qu'elle choisisse le bon outil
```

La bonne cible est :

```text
choisir/capter un mode de mission
-> cadrer Iris
-> router la demande
-> afficher le travail
-> produire un livrable
```

Iris devient une secrétaire de mission, pas une IA de bavardage.
