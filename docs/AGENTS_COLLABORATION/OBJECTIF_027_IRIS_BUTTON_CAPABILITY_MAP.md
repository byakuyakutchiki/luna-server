# Objectif 027 — Iris Button / Capability Map

Date : 2026-06-04
Statut : ouvert
Priorité : P0

## Problème fondateur

Iris a une interface réelle avec des boutons, des modes, des uploads, des notes, un Command Screen, une équipe, des actions et des documents.

Mais Iris ne semble pas avoir conscience de cet environnement.

Exemple terrain :

```text
upload_start CV LUDOVIC SAINT-LOUIS.docx ...
upload_ok Le contenu que vous avez partagé semble être...
pipeline_transcript_iris Pas encore, je n'ai pas encore reçu le document.
pipeline_transcript_iris Je ne vois pas directement les boutons...
```

Le bouton upload fonctionne côté UI/API, mais le cerveau Iris ne reçoit pas ou ne conserve pas correctement cet état.

## Cible

Créer une cartographie exhaustive du réel :

```text
bouton visible -> handler JS -> endpoint/API/tool -> état produit -> mémoire Iris -> rendu attendu -> preuve F12/APK
```

Chaque bouton doit avoir une trajectoire connue.

Chaque trajectoire doit dire si Iris en a conscience ou non.

## Boutons / contrôles à inventorier

### Entrée session

| Élément | ID / source | Cible attendue |
|---|---|---|
| Démarrer | `btnStartBig` | lancer prétest puis session |
| Durée | `durationSelect` | durée session |
| Démarrer prétest | `btnPretestStart` | lancer Iris après micro/caméra |
| Annuler prétest | `btnPretestBack` | retour |

### Barre actions Iris

| Bouton | ID | Handler / route détectée | Question à résoudre |
|---|---|---|---|
| Iris active / mute | `btnMuteLuna` | mute/unmute local | Iris sait-elle qu'elle est muette/active ? |
| Analyser | `btnUpload` + `uploadInput` | `/api/visio/upload` | L'analyse est-elle injectée au WS Iris ? |
| Inviter | `btnInvite` | masqué en audio-first | remplacé par Teams ? |
| Partager | `btnShare` | masqué en audio-first | route encore utile ? |
| Notes | `btnNotes` | `/api/visio/notes`, `/api/visio/notes/save` | Iris sait-elle que les notes existent ? |
| Raccrocher | `btnHangup` / `afHangup` | fermeture session | fin propre + sauvegarde ? |

### Command Screen

| Bouton | ID / classe | Cible attendue |
|---|---|---|
| Modifier | `icsEdit` | rendre le contenu éditable |
| Copier | `icsCopy` | copier le rendu |
| Télécharger | `icsDl` | télécharger le contenu |
| Fermer | `icsClose` | fermer le panneau |
| Relancer | diag action | renvoyer / relancer le rendu |
| Simplifier | diag action | demander un rendu plus simple |
| Données manquantes | diag action | lister ce qui bloque |

### Texte / conversation

| Élément | ID | Cible attendue |
|---|---|---|
| Input texte | `afTextInput` | envoyer un message texte à Iris |
| Envoyer | `afTextForm` submit | WS `{type:'text'}` |
| PTT / micro | `btnPTT` | parole utilisateur |

### Modes Iris

| Mode | data-mode | Cible attendue |
|---|---|---|
| Discussion | `discussion` | conversation courte |
| Analyse | `analyse` | documents / synthèses |
| Réunion | `reunion` | CR, décisions, tâches |
| Tableau | `tableau` | tableaux, graphiques, KPI |
| Rédaction | `redaction` | courrier, rapport, brouillon |
| Recherche | `recherche` | web + sources |
| Actions | `actions` | SMS/email/appel avec validation |
| Équipe | `equipe` | participants, invitations, rôles |
| Carte | `carte` | localisation / carte |
| Conformité | `conformite` | RGPD, garde-fous |

### Teams / collaboration

| Élément | ID / route | Cible attendue |
|---|---|---|
| Participants | `irisTeamsPanel` | afficher participants |
| Inviter | `irtInviteBtn` | `/api/iris/session/{id}/invite` |
| Exclure | `_irtKick` | `/api/iris/session/{id}/revoke/{participant}` |
| Approuver | `_irtApprove` | `/api/iris/session/{id}/approve/{action}` |
| Refuser | `_irtReject` | `/api/iris/session/{id}/reject/{action}` |

## Ruptures déjà constatées

### Upload document

Trajectoire actuelle :

```text
btnUpload -> uploadInput -> _handleUpload(file) -> /api/visio/upload -> upload_ok
```

Mais après `upload_ok`, le code injecte l'analyse via :

```js
_sendAppMessageToBot({
  message_type: 'conversation',
  event_type: 'conversation.echo',
  ...
})
```

Cette injection vise l'ancien canal Simli/Daily, pas nécessairement le WebSocket OpenAI Iris (`/ws/iris-voice`).

Conséquence :

```text
Iris peut dire : "je n'ai pas reçu le document"
```

alors que l'UI a bien reçu `upload_ok`.

Hypothèse P0 :

```text
Les actions UI ne sont pas synchronisées dans la mémoire Iris Realtime.
```

### Boutons / environnement

Iris dit :

```text
Je ne vois pas directement les boutons...
```

Cela signifie que le prompt/session Iris ne reçoit probablement pas une "capability map" runtime :

```text
Boutons visibles
Modes disponibles
Actions autorisées
Documents chargés
Derniers événements UI
État du Command Screen
```

## Travail demandé

### Codex

Créer la matrice de vérité :

```text
Bouton -> handler -> endpoint/tool -> état -> conscience Iris -> preuve
```

Ne pas valider un bouton seulement parce qu'il clique.

### Claude / Kimi code

Ajouter un canal d'état Iris :

```text
UI event -> /ws/iris-voice -> session context -> Iris sait
```

Exemple pour upload :

```js
_irisWs.send(JSON.stringify({
  type: 'ui_event',
  name: 'document_uploaded',
  filename: fname,
  analysis: analysis,
  conversation_id: currentConvId
}));
```

Puis côté serveur :

```text
injecter l'événement dans le contexte OpenAI Realtime
mettre à jour une mémoire session
confirmer au client par ui_state_ack
```

### Kimi UX

Vérifier que chaque bouton visible a :

- un label clair ;
- une cible claire ;
- un retour utilisateur ;
- un état visible ;
- aucune promesse fausse.

### DeepSeek

Auditer les ruptures :

- bouton qui appelle une ancienne route ;
- bouton qui envoie vers Daily/Simli au lieu de `/ws/iris-voice` ;
- endpoint qui répond OK mais ne nourrit pas la mémoire ;
- mode qui existe visuellement mais pas côté outil ;
- action qui produit un rendu mais pas de `render_done`.

## Règle de validation

Un bouton est validé seulement si :

```text
clic réel -> log F12 -> endpoint/tool -> état Iris -> réponse cohérente Iris -> rendu ou confirmation
```

Un bouton est échoué si :

```text
clic réel OK mais Iris dit qu'elle ne sait pas / n'a pas reçu / ne voit pas / ne peut pas
```

## Première Target Cell P0

### TC-027-01 — Upload document conscient

Test :

1. Uploader un document via `btnUpload`.
2. Vérifier F12 :

```text
upload_start
upload_ok
ui_event document_uploaded
ui_state_ack document_uploaded
```

3. Demander :

```text
Iris, quel document viens-tu de recevoir ?
```

PASS :

- Iris cite le nom du fichier.
- Iris résume le contenu.
- Iris propose une action cohérente : synthèse, tableau, courrier, comparaison, sauvegarde.

FAIL :

- Iris dit qu'elle n'a rien reçu.
- Iris demande de téléverser à nouveau.
- Aucun `ui_state_ack`.

