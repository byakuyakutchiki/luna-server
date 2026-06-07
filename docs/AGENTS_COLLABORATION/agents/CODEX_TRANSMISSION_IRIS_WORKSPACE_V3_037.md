# Codex — Transmission Iris Workspace V3 — Objectif 037

Date : 2026-06-07
Agent : Codex
Type : transmission cahier fondateur final
Statut : source de vérité active pour `/team`

## Source de vérité active

La V3 remplace la V2 comme référence active.

Fichiers à lire obligatoirement :

- `docs/AGENTS_COLLABORATION/reference/IRIS_WORKSPACE_V3_CAHIER_FONDATEUR_IMPLEMENTATION_FINAL.docx`
- `docs/AGENTS_COLLABORATION/reference/IRIS_WORKSPACE_V3_CAHIER_FONDATEUR_IMPLEMENTATION_FINAL.md`

Le `.docx` contient les visuels intégrés, dont la référence Luna CEO Corporate et le logo YAWatch Industries.
Le `.md` est la version lisible depuis la VM/terminal.

## Instruction non négociable

Ne plus corriger `/team` comme une maquette à améliorer.
Reconstruire `/team` comme produit premium central de YAWatch Industries.

La cible n'est pas Trello, Miro, Zoom ou un CRM avec IA.
La cible est une salle stratégique augmentée, premium, séquencée, vivante et exploitable par une entreprise.

## Phrase produit

Iris Workspace est la salle stratégique de YAWatch Industries où humains, Iris, IQ et Luna collaborent pour transformer des idées en décisions traçables et en livrables professionnels.

## Points clés à respecter

- Le travail occupe la majorité de la valeur écran.
- La présence humaine doit être claire : caméras, micros, sièges, spectateurs, rôles.
- Iris, IQ et Luna doivent être visibles comme acteurs de la salle, avec des états distincts.
- Le workflow doit être séquencé : collecter, analyser, débattre, refondre, comparer, recommander, valider, produire, archiver.
- Les idées doivent être versionnées, pas écrasées.
- Les sources doivent couvrir fichier, lien et note.
- Un document importé doit aller jusqu'à preview, analyse, annotation, décision, export et stockage/session.
- Aucun bouton décoratif.
- Aucun emoji métier visible comme icône principale.
- Le résultat final doit être montrable à un dirigeant.

## Definition of Done V3

Avant de livrer, vérifier contre le document V3 :

- Screenshot final comparé à la référence Luna CEO Corporate.
- Aucun emoji métier visible.
- Les caméras/micros ont des emplacements clairs.
- `SourceImportModal` possède trois modes : fichier, lien, note.
- `MeetingStepper` affiche l'étape et limite les actions au contexte.
- `CentralCanvas` occupe la majorité de la valeur visuelle.
- Iris/IQ/Luna ont des états visuels distincts.
- Modèle de données prêt pour versions et historique.
- Le résultat est montrable à un dirigeant.

## Instruction à Claude

Claude doit lire le document V3 complet avant tout code.
Codex ne remplace pas ce document par un résumé.

Toute proposition de V3 doit être découpée en lots de qualité :

1. fondation visuelle premium ;
2. structure spatiale et présence humaine ;
3. plan central et import sources ;
4. workflow séquencé ;
5. rôles Iris/IQ/Luna ;
6. mémoire/versioning/export.

## Décision Ludovic

ChatGPT a produit la V3 avec Ludovic et sert de coach de vérité sur la vision produit.
Codex transmet et protège la fidélité de cette vision dans GitHub.
