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

