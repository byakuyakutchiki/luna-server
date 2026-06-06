# Objectif 034 — Iris Workspace Orchestrator

Date : 2026-06-06
Statut : ouvert
Priorite : P0

## Probleme

Iris peut connaitre le Command Screen dans son prompt mais continuer a parler comme un chatbot :

```text
Je vais preparer...
Je ne peux pas interagir...
Je n'ai pas acces...
Imagine un graphique...
```

Le probleme n'est pas seulement le prompt. Le modele vocal ne doit pas etre le seul decideur de l'execution.

## Regle produit

```text
Utilisateur parle/ecrit
-> serveur comprend l'intention
-> serveur choisit le mode
-> serveur affiche le panneau
-> Iris commente en une phrase
```

Interdit :

```text
Utilisateur parle
-> Iris promet
-> panneau attend
-> fallback
-> diagnostic
```

## Architecture cible

Iris est la voix et la personnalite.
Le serveur est le pilote d'execution.
Le Command Screen est la preuve visuelle.

```text
Iris Workspace Orchestrator
  - classe la demande
  - choisit le mode
  - genere un premier rendu visuel
  - bloque les actions sensibles
  - laisse ensuite Iris confirmer
```

## V1 implementee

Fichier : `integrations/iris/workspace_orchestrator.py`

Le nouvel orchestrateur gere les demandes suivantes :

- graphique avec donnees chiffrees -> `chart`
- graphique sans donnees -> `missing_info`
- tableau/liste/donnees -> `data_board`
- courrier/redaction/email -> `document_draft`
- document charge/analyse -> `document_insight`
- recherche web -> `research_board` avec sources a brancher
- reunion/compte-rendu -> `meeting_board`
- SMS/appel/email/action sensible -> `action_board` avec validation requise
- demande de travail generale -> `context_panel`

## Changement bridge vocal

Fichier : `integrations/openai/web_voice_bridge.py`

Avant :

```text
OpenAI repond
Iris promet
ActionRouter tente un fallback
```

Apres :

```text
transcript utilisateur
-> orchestrate_workspace_request(...)
-> _emit_workspace_plan(...)
-> render_done
-> response.create avec tools=[]
-> Iris confirme le panneau
```

## Validation F12 attendue

Pour :

```text
Iris, fais un graphique avec janvier 1200, fevrier 1800, mars 2400.
```

Logs attendus :

```text
mode_auto_detected=tableau
workspace_orchestrator render_type=chart mode=tableau render_done=true
response_created_after_orchestrator mode=tableau render_type=chart
ics_render chart
```

Pour :

```text
Iris, envoie un SMS a Lucas.
```

Logs attendus :

```text
workspace_orchestrator render_type=action_board mode=actions render_done=true
```

Et aucun SMS reel ne doit partir.

## Limites V1

La V1 ne remplace pas encore les vrais outils externes :

- recherche web reelle ;
- lecture porte-documents ;
- generation PDF professionnelle ;
- actions Twilio/email ;
- synchronisation workspace multi-participants.

Elle impose cependant la colonne vertebrale :

```text
serveur d'abord
panneau ensuite
Iris apres
```

## V2 — Mission Brief admin

Le serveur ne doit pas laisser Iris improviser, mais l'humain doit pouvoir cadrer la mission.

Le workspace doit accepter un brief de mission fourni par l'admin/owner :

```json
{
  "title": "Analyse banque 2026",
  "domain": "banque",
  "objective": "Comparer les offres et produire une synthese exploitable",
  "context": "Travail avec une equipe de business developpeurs",
  "inputs": [
    {"type": "document", "label": "dossier_banque.pdf"},
    {"type": "youtube", "label": "interview marche bancaire"},
    {"type": "url", "label": "https://..."}
  ],
  "deliverables": ["tableau comparatif", "graphique", "PDF final"],
  "constraints": ["RGPD", "ne pas envoyer d'action externe sans validation"],
  "external_research": false
}
```

Effet attendu :

```text
L'utilisateur choisit le contexte
-> le serveur stocke le brief
-> Iris travaille dans ce cadre
-> les documents uploades deviennent des sources
-> la recherche externe est bloquee tant que le brief ne l'autorise pas
```

Protocole WS V2 :

```json
{
  "type": "ui_event",
  "name": "mission_brief_update",
  "brief": {
    "title": "...",
    "domain": "...",
    "objective": "...",
    "context": "...",
    "inputs": [],
    "deliverables": [],
    "constraints": [],
    "external_research": false
  }
}
```

Validation attendue :

```text
WebVoice: mission_brief_updated ...
ui_state_ack mission_brief_update
workspace_orchestrator ... context=<brief>
```

Si l'utilisateur demande une recherche web alors que `external_research=false`,
Iris ne doit pas inventer : le Command Screen affiche `missing_info` avec demande de validation.
