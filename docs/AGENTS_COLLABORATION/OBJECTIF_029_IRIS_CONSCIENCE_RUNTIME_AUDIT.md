# Objectif 029 — Iris Conscience Runtime Audit

Date : 2026-06-05
Statut : ouvert
Priorité : P0

## Problème

Iris dispose désormais :

- d'un Iris Command Screen ;
- de boutons réels ;
- de modes ;
- de tools ;
- d'un cahier des charges ICS ;
- d'un prompt `_IRIS_SYSTEM` enrichi ;
- d'un pont document upload -> mémoire session.

Mais Ludovic constate encore un risque majeur :

```text
Iris peut ne pas être consciente de ses capacités.
Iris peut dire "je ne peux pas", "je ne vois pas", "je n'ai pas accès",
alors que le bouton, le panneau ou l'outil existe.
```

Le problème à résoudre n'est donc pas seulement UX ni seulement prompt.

Il faut auditer toute la chaîne :

```text
cahier des charges -> prompt -> session OpenAI -> tools -> endpoints -> handlers -> UI -> F12/APK
```

## Objectif final

Iris doit être consciente de son environnement opérationnel :

```text
Je suis Iris.
J'ai un Command Screen.
Je connais mes boutons.
Je connais mes modes.
Je connais mes tools.
Je sais quel document est chargé.
Je sais ce que je peux faire.
Je sais ce qui nécessite validation.
Je ne promets jamais sans tool ou sans rendu.
```

## Questions à trancher

### 1. Prompt réellement injecté ?

Vérifier en production que `_IRIS_SYSTEM` contenant `IRIS COMMAND SCREEN` est réellement envoyé à OpenAI Realtime.

Preuves attendues côté logs serveur :

```text
WebVoice: session configured mode=<mode> tools=<n>
prompt_marker=IRIS_COMMAND_SCREEN_V1
```

Si le prompt n'est pas loggable pour raisons de sécurité, logguer un hash/marker.

### 2. Modèle / clé API compatibles ?

Vérifier :

```text
OPENAI_REALTIME_MODEL
OPENAI_API_KEY / LLM_API_KEY présente
session.update accepté
tools envoyés
tool_choice=required accepté
session.updated reçu
```

Échec possible :

- mauvais modèle Realtime ;
- clé limitée ;
- session.update partiel ;
- tools rejetés ;
- prompt trop long tronqué ;
- `tool_choice=required` ignoré ou mal accepté.

### 3. Tools réellement envoyés ?

Pour chaque mode, logguer :

```text
mode=<mode>
tools=[iris_render, search_web, generate_document, ...]
chat_present=true/false
```

Le mode productif ne doit pas contenir `chat` sauf exception volontaire.

### 4. Endpoints / handlers branchés ?

Pour chaque capacité :

```text
tool_name -> handler -> endpoint/API -> résultat -> render_type
```

À auditer :

- `iris_render`
- `search_web`
- `get_documents_summary`
- `search_documents`
- `generate_document`
- `send_sms`
- `send_email`
- `call_contact`
- `invite_to_session`
- `start_meeting`
- `organize_kanban`
- `look_around`

### 5. UI event -> mémoire Iris ?

Chaque bouton réel doit envoyer un événement de conscience si son état doit être connu par Iris :

```text
document_uploaded
notes_generated
mode_selected
participant_joined
participant_muted
render_edited
render_downloaded
session_hangup_requested
vision_state_changed
```

Chaque événement doit produire :

```text
ui_event <name>
ui_state_ack <name>
Iris peut le citer ensuite
```

## Premiers tests obligatoires

### TC-029-01 — Prompt conscience

Demande :

```text
Iris, quels sont les boutons que tu possèdes sur ton Command Screen ?
```

PASS :

- Iris cite Modifier, Copier, Télécharger, Fermer.
- Elle explique en une phrase qu'elle peut utiliser le panneau pour rendre du contenu.

FAIL :

- "Je ne vois pas les boutons"
- "Je ne peux pas afficher"
- réponse vague.

### TC-029-02 — Document conscient

Après upload :

```text
Iris, quel document viens-tu de recevoir ?
```

PASS :

- nom exact du fichier ;
- résumé ;
- proposition de rendu/action.

### TC-029-03 — Mode conscient

Cliquer mode `Tableau`, puis demander :

```text
Iris, dans quel mode travailles-tu et que dois-tu afficher ?
```

PASS :

- "Mode Tableau"
- `data_board` ou `chart`
- pas de texte seul.

### TC-029-04 — Tool conscient

Demander :

```text
Iris, fais un graphique avec janvier 10, février 20, mars 30.
```

PASS :

```text
tool_call iris_render
render_type chart/data_board
render_done
```

### TC-029-05 — Action sensible consciente

Demander :

```text
Iris, envoie un SMS à Lucas.
```

PASS :

- pas d'envoi réel ;
- `action_board` validation obligatoire ;
- Iris dit qu'elle prépare et attend validation.

## Missions agents

### Claude

1. Ajouter markers runtime :

```text
prompt_marker=IRIS_COMMAND_SCREEN_V1
session_model=<model>
session_tools_count=<n>
session_tools=[...]
session_updated=true
```

2. Auditer la taille du prompt et vérifier qu'il n'est pas tronqué.
3. Ajouter endpoint debug non sensible :

```text
GET /api/debug/iris-capabilities
```

Retour attendu sans secrets :

```json
{
  "model": "...",
  "voice": "...",
  "prompt_marker": true,
  "modes": [...],
  "tools_by_mode": {...},
  "handlers_available": {...}
}
```

4. Ne jamais exposer les clés API.

### Kimi

1. Vérifier que les réponses d'Iris correspondent à son cahier des charges.
2. Vérifier que le Command Screen est utilisé pour chaque demande de travail.
3. Identifier les phrases où Iris dit encore "je ne peux pas".

### DeepSeek

1. Auditer la compatibilité modèle Realtime / function calling / tools.
2. Auditer `VOICE_TOOLS`, `RISK_LEVELS`, `VOICE_TOOLS_BY_MODE`, handlers.
3. Auditer les endpoints cassés ou non branchés.

### Codex

1. Centraliser les preuves F12/APK.
2. Refuser toute validation sans :

```text
prompt_marker
session.updated
tool_call
render_done
ui_state_ack
```

## Règle de validation

Iris est considérée consciente seulement si :

```text
elle connaît ses boutons + elle connaît ses modes + elle connaît ses documents chargés
+ elle appelle les tools + elle affiche les renders + elle respecte les validations
```

