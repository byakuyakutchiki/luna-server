# Codex — Transmission source de vérité Iris Workspace — Objectif 036

Date : 2026-06-07
Agent : Codex
Type : transmission cahier des charges complet
Statut : à lire avant toute nouvelle modification de `/team`

## Source de vérité officielle

Claude, Kimi, DeepSeek et Codex ne doivent plus travailler Iris Workspace depuis un résumé court.

Les fichiers de référence sont :

- `docs/AGENTS_COLLABORATION/reference/IRIS_WORKSPACE_VISION_PRODUIT_UX.docx`
- `docs/AGENTS_COLLABORATION/reference/IRIS_WORKSPACE_VISION_PRODUIT_UX.md`

Le `.docx` est le document original produit avec Ludovic et ChatGPT.
Le `.md` est une version lisible directement depuis la VM/terminal.

## Règle de travail

Codex ne doit pas réduire la vision produit en ticket basique.
Claude doit lire le document complet, section par section, avant de coder.

La V1 `/team` est seulement un brouillon d'ambiance. La V2 doit être reconstruite depuis le document complet.

## Règle absolue

Chaque fonctionnalité doit être pensée jusqu'au résultat final.

Exemple :

`Upload document` ne signifie pas seulement ajouter un bouton upload.

Cycle attendu :

`upload -> preview sur le plan central -> annotation -> analyse IQ -> discussion -> décision -> export -> stockage/session`

## Critères de validation avant livraison

- Est-ce compréhensible en 3 secondes ?
- Est-ce visuellement premium ?
- Le plan de travail occupe-t-il la place principale ?
- Les humains, Iris, IQ et Luna sont-ils clairement autour de la même table ?
- Les fonctions sont-elles utiles ou seulement décoratives ?
- Chaque fonction aboutit-elle à un résultat final ?
- Peut-on présenter cette interface à une entreprise sans s'excuser ?

## Instruction directe à Claude

Ne code pas la V2 depuis la maquette V1.
Lis d'abord le document complet dans `reference/`, puis propose une refonte structurée de `/team`.

Priorité produit :

1. mode clair premium par défaut ;
2. vrai plan central dominant ;
3. vraie table / structure circulaire lisible ;
4. participants humains + Iris + IQ + Luna visibles ;
5. sièges libres et spectateurs clairs ;
6. upload + preview + annotation + export, pas un simple bouton ;
7. aucun bouton décoratif.

## Décision Ludovic

ChatGPT devient le coach de vérité pour la vision produit.
Codex reste le pont technique et le garant que la vision complète arrive aux agents sans perte de qualité.
