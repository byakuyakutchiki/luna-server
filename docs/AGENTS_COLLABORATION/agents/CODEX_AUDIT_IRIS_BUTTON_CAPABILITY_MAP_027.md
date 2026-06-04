# Codex — Audit initial Button / Capability Map — Objectif 027

Date : 2026-06-04
Agent : Codex
Type : audit initial / cadrage
Niveau : 0

## Verdict court

Ludovic a raison : Iris n'a pas encore conscience de son environnement réel.

Les boutons existent. Certains handlers fonctionnent. Mais les événements UI ne sont pas systématiquement envoyés dans la mémoire/conversation Iris Realtime.

Le cas document le prouve :

```text
upload_start -> upload_ok -> Iris dit "je n'ai pas reçu le document"
```

## Cause probable

Le bouton upload injecte l'analyse vers l'ancien canal :

```js
_sendAppMessageToBot({ event_type: 'conversation.echo', ... })
```

Mais la conversation Iris actuelle passe par :

```text
/ws/iris-voice
```

Donc l'UI sait que le document est uploadé, mais Iris Realtime ne l'intègre pas forcément dans son contexte.

## Boutons critiques à tracer

| Bouton | Handler | État |
|---|---|---|
| Analyser | `_handleUpload(file)` -> `/api/visio/upload` | rupture conscience Iris |
| Notes | `_openNotesModal()` -> `/api/visio/notes` | à vérifier |
| Modes | `selectMode(mode)` -> WS `mode_select` | partiel |
| Input texte | `_afSendTextToIris()` -> WS `text` | actif |
| Command Screen | `icsEdit/Copy/Dl/Close` | local UI |
| Teams | `_irtInvite/_irtKick/_irtApprove/_irtReject` | à vérifier |
| Raccrocher | `doHangup/_doAudioHangup` | à vérifier |

## Correction conceptuelle

Ajouter un pont d'état :

```text
UI event -> WS Iris -> mémoire session -> OpenAI context -> Iris répond en connaissance
```

Exemple :

```js
_irisWs.send(JSON.stringify({
  type: 'ui_event',
  name: 'document_uploaded',
  filename: fname,
  analysis: analysis
}));
```

Le serveur doit ensuite injecter l'événement dans OpenAI Realtime et confirmer :

```text
ui_state_ack document_uploaded
```

## Prochaine action

Ne pas continuer à ajouter des tools avant d'avoir relié :

```text
boutons visibles -> mémoire Iris
```

Premier test P0 : upload document conscient.

