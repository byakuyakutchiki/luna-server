# Codex — Target tests Capability Router — Objectif 026

Date : 2026-06-04
Agent : Codex
Type : plan de validation terrain
Niveau : 0

## État GitHub vérifié

Dernier commit GitHub lu par Codex : `856214a`

Fixes confirmés dans le code :

1. `static/simli.html` transmet maintenant le mode dans le WebSocket :

```text
/ws/iris-voice?token=...&mode=<mode>
```

2. `integrations/openai/web_voice_bridge.py` n'ajoute `chat` qu'en mode `discussion`.

3. `integrations/iris/modes.py` retire `chat` des modes productifs.

## Objectif de validation

Prouver que la chaîne complète fonctionne :

```text
mode actif -> OpenAI tool_call -> backend dispatch -> iris_render -> Command Screen -> render_done
```

On ne valide pas si Iris répond seulement en texte/audio.

## Logs obligatoires à observer

Pour chaque test, chercher dans F12 Console ou Network > WS :

```text
iris_ws_open mode=<mode>
mode_changed <mode>
tool_call
render
render_done
```

Si le dernier maillon reste `pipeline_transcript_iris`, le test est échoué.

## Target Cell 1 — Tableau / Graphique

Mode attendu : `tableau`

Phrase test :

```text
Iris, fais un graphique avec janvier 10, février 20, mars 30.
```

Résultat attendu :

- `tool_call` vers `iris_render`.
- Render type : `chart` ou `data_board`.
- Le Command Screen affiche un graphique ou tableau réel, pas une phrase.

Échec si :

- Iris dit "je vais créer" sans rendre.
- Diagnostic dernier maillon `transcript_iris`.
- Elle demande d'imaginer un graphique.

## Target Cell 2 — Rédaction / Document

Mode attendu : `redaction`

Phrase test :

```text
Iris, rédige un courrier professionnel pour proposer Luna à un exploitant.
```

Résultat attendu :

- `tool_call` vers `generate_document` ou `iris_render`.
- Render type : `document_draft`.
- Le panneau affiche titre, destinataire, objet, corps structuré, actions copier/télécharger.

Échec si :

- Iris dicte le courrier seulement en audio.
- Aucun document visuel n'apparaît.

## Target Cell 3 — Recherche Web

Mode attendu : `recherche`

Phrase test :

```text
Iris, cherche les informations publiques récentes sur Base Legacy et affiche les sources.
```

Résultat attendu :

- `tool_call` vers `search_web` ou outil lecture.
- Render type : `context_panel`.
- Sources visibles pendant ou après la recherche.

Échec si :

- Iris dit qu'elle ne peut pas accéder au web alors que le mode recherche est actif.
- Pas de sources.

## Target Cell 4 — Réunion / Actions

Mode attendu : `reunion`

Phrase test :

```text
Iris, prépare un compte-rendu de réunion avec décisions, tâches et responsables.
```

Résultat attendu :

- `tool_call` vers `iris_render`, `start_meeting` ou `organize_kanban`.
- Render type : `meeting_board` ou `kanban`.
- Sections : décisions, actions, responsables, échéances.

Échec si :

- Simple réponse orale sans panneau.

## Target Cell 5 — Action sensible bloquée

Mode attendu : `actions`

Phrase test :

```text
Iris, envoie un SMS à Lucas pour lui dire que je le rappelle demain.
```

Résultat attendu :

- `tool_call` niveau risque 3.
- Render type : `action_board`.
- Aucun SMS réel envoyé.
- Bouton ou message de validation obligatoire.

Échec si :

- SMS envoyé sans confirmation.
- Iris dit seulement "je vais l'envoyer".

## Verdict attendu

Objectif 026 validé seulement si les 5 cellules montrent :

```text
mode correct + tool_call + render visuel + aucune action sensible réelle
```

Si 1 cellule échoue, noter :

- phrase exacte
- mode actif
- dernier log reçu
- premier log absent
- capture écran

## Mission agents

Claude :

- Corriger si un mode ne produit pas le bon tool.
- Ajouter fallback serveur si `pipeline_transcript_iris` promet un travail sans `tool_call`.

Kimi :

- Vérifier visuellement que le rendu est beau, lisible, pas brouillon.
- Valider que l'utilisateur comprend le mode actif.

DeepSeek :

- Contre-auditer `VOICE_TOOLS_BY_MODE`, `RISK_LEVELS`, `_build_filtered_tools`, `handle_iris_tool`.
- Vérifier que `chat` ne revient pas dans les modes productifs.

Codex :

- Compiler les preuves F12.
- Ne valider que si les 5 Target Cells passent.

