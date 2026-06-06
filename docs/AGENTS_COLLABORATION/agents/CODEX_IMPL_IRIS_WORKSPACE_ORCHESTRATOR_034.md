# Codex — Implementation Iris Workspace Orchestrator — Objectif 034

Date : 2026-06-06
Agent : Codex
Type : implementation
Niveau : 1

## Ce qui a ete implemente

Ajout d'une couche serveur :

```text
integrations/iris/workspace_orchestrator.py
```

Cette couche transforme une phrase utilisateur en `WorkspacePlan` :

- `mode`
- `render_type`
- `payload`
- `speech_instruction`
- `source`

Le bridge vocal appelle maintenant cet orchestrateur avant de laisser OpenAI parler.

## Pourquoi

Iris ne doit plus improviser :

```text
je pourrais...
je vais...
je ne peux pas...
```

Le serveur doit afficher le panneau et ensuite demander a Iris de confirmer.

## Flux apres patch

```text
transcription utilisateur
-> detection mode
-> workspace_orchestrator
-> render Command Screen
-> OpenAI parle en une phrase avec tools=[]
```

## Exemples couverts

### Graphique

Demande :

```text
fais un graphique avec janvier 1200, fevrier 1800, mars 2400
```

Rendu serveur :

```text
render_type=chart
labels=[Jan, Fev, Mar]
data=[1200, 1800, 2400]
```

### Action sensible

Demande :

```text
envoie un SMS a Lucas
```

Rendu serveur :

```text
render_type=action_board
requires_confirmation=true
```

Aucune action externe n'est executee.

### Recherche externe

Demande :

```text
cherche Base Legacy sur le web
```

Rendu serveur :

```text
render_type=research_board
sources=[]
missing=[brancher/verifier search_web]
```

Cela evite qu'Iris dise faussement qu'elle a cherche.

## Fichiers touches

- `integrations/iris/workspace_orchestrator.py`
- `integrations/openai/web_voice_bridge.py`
- `docs/AGENTS_COLLABORATION/OBJECTIF_034_IRIS_WORKSPACE_ORCHESTRATOR.md`

## Tests a faire sur VM

```bash
python3 -m py_compile integrations/iris/workspace_orchestrator.py integrations/openai/web_voice_bridge.py
```

Puis deploiement et test F12.

## Logs attendus

```text
workspace_orchestrator render_type=<type> mode=<mode> render_done=true
response_created_after_orchestrator mode=<mode> render_type=<type>
ics_render <type>
```

## V2 ajoutee — Mission Brief admin

Le bridge accepte maintenant :

```json
{
  "type": "ui_event",
  "name": "mission_brief_update",
  "brief": {
    "title": "Analyse banque 2026",
    "domain": "banque",
    "objective": "Produire un comparatif exploitable",
    "context": "Equipe business developpement",
    "inputs": [{"type": "document", "label": "dossier.pdf"}],
    "deliverables": ["tableau", "graphique", "PDF"],
    "constraints": ["RGPD"],
    "external_research": false
  }
}
```

Effets :

- le brief est stocke dans la session vocale ;
- le Command Screen affiche le brief actif ;
- les documents uploades sont ajoutes comme sources du brief ;
- `orchestrate_workspace_request(...)` recoit le brief et cadre les rendus ;
- si `external_research=false`, une demande web affiche `missing_info` au lieu d'inventer une recherche.

Mission UI pour Kimi :

- creer un panneau owner/admin "Brief mission" ;
- champs : titre, domaine, objectif, contexte, sources, livrables, contraintes ;
- toggle : recherche externe autorisee ;
- bouton : appliquer le brief ;
- afficher clairement le brief actif dans le Command Screen.
