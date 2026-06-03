# Codex — Target Cell Iris Action Router — Objectif 023

Date : 2026-06-04
Agent : Codex
Type : cadrage technique / produit
Niveau : 0

## Verdict terrain

Les logs fournis montrent :

```text
iris_ws_open
iris_ws_ready
pipeline_audio playing
pipeline_transcript_iris ...
ics_working Iris prépare
```

Mais on ne voit pas :

```text
pipeline_tool_call
tool_call
render
ics_render
```

Conclusion : OpenAI/Iris parle, mais ne déclenche pas l'exécution. La rupture est :

```text
transcript_iris -> tool_call
```

Le panneau diagnostic fonctionne. Le maillon cassé est le déclencheur d'action.

## Décision Codex

Il ne faut pas ajouter une clé API dans le panneau visible utilisateur.

Une clé API ne doit jamais être exposée côté frontend, ni dans un panneau de configuration accessible au souscripteur. La bonne architecture est :

```text
Frontend Iris
  -> WebSocket /ws/iris-voice
  -> serveur Luna
  -> Iris Action Router
  -> endpoint/tool autorisé
  -> render WS vers Command Screen
```

Le panneau peut afficher la configuration fonctionnelle, par exemple :

- recherche web : actif/inactif ;
- documents : actif/inactif ;
- SMS : brouillon uniquement / confirmation requise ;
- appel : confirmation requise ;
- map : consentement requis ;
- budget : lecture seule.

Mais les clés restent côté serveur / Cloud Run / secrets.

## Prérogatives Iris à définir avant exécution

Iris n'est pas un chatbot. Iris est un centre de commande opérationnel.

| Famille | Prérogative | Type | Risque |
|---|---|---|---|
| Conversation | répondre simplement | lecture | faible |
| Command Screen | afficher tableau, graphique, checklist, document, kanban | rendu local | faible |
| Recherche web | chercher, sourcer, synthétiser | lecture externe | moyen |
| Documents | lister, chercher, analyser | lecture données utilisateur | moyen |
| Upload | analyser un fichier transmis | lecture fichier | moyen |
| Map | localiser une adresse | externe / consentement | moyen |
| Contacts | lister/rechercher contacts | donnée personnelle | moyen |
| SMS | préparer puis envoyer | action engageante | élevé |
| Appel | préparer puis appeler | action coûteuse | élevé |
| Email | préparer puis envoyer | action engageante | élevé |
| Réunion | prendre notes, décisions, actions | workspace | moyen |
| Equipe | inviter/mute/kick/roles | session | élevé |
| Budget | analyser, comparer, alerter | donnée sensible | élevé |
| RGPD | bloquer/alerter si donnée/action sensible | garde-fou | obligatoire |

## Mots déclencheurs à router

### Rendu visuel local

| Intent | Mots déclencheurs | render_type attendu |
|---|---|---|
| Tableau | tableau, colonnes, lignes, classe, organise en tableau | `data_board` |
| Graphique | graphique, courbe, histogramme, camembert, évolution, chiffres | `chart` |
| KPI | indicateurs, métriques, chiffres clés, résumé chiffré | `kpi_cards` |
| Checklist | checklist, étapes, à faire, tâches | `action_board` ou `kanban_board` |
| Kanban | kanban, priorités, à faire/en cours/fini | `kanban_board` |
| Document | rédige, courrier, lettre, brouillon, contrat | `document_draft` |
| Analyse document | analyse ce PDF, explique ce document, synthèse fichier | `document_insight` |
| Timeline | planning, chronologie, échéances, dates | `timeline` |
| Roadmap | roadmap, phases, plan par étapes | `roadmap` |
| Comparaison | compare, avantage, inconvénient, lequel choisir | `comparison` |
| Recherche | cherche, trouve, source, va sur le web | `research_board` |
| Carte | localise, adresse, itinéraire, carte, où est | `map_board` |
| Réunion | réunion, compte-rendu, note les décisions | `meeting_board` |

### Actions sensibles

| Intent | Mots déclencheurs | outil | garde-fou |
|---|---|---|---|
| SMS | envoie un SMS, préviens X par SMS | `send_sms` | confirmation + quota + horaire |
| Appel | appelle X, passe un appel | `call_contact` | confirmation + coût + horaire + blacklist |
| Email | envoie un mail, rédige et envoie | `send_email` | confirmation |
| Invitation | invite X, ajoute X à la session | `invite_to_session` | owner only / validation |
| Suppression | supprime, efface | à bloquer par défaut | validation niveau 3 |

## Endpoints/outils à vérifier

| Capacité | Outil/endpoint attendu | Statut à vérifier |
|---|---|---|
| Command Screen | `iris_render` via `VOICE_TOOLS` | présent, mais pas toujours déclenché |
| Chat simple | `chat` | présent ; ne doit pas capter les rendus visuels |
| Recherche web | `search_web` / handler serveur | vérifier exécution réelle |
| Documents | `get_documents_summary`, `search_documents`, `list_folders` | vérifier filtrage propriétaire |
| Map | `search_places` ou route map dédiée | consentement à ajouter/valider |
| Contacts | `get_contacts` | vérifier RGPD |
| SMS | `send_sms` | rester validation_required avant réel |
| Appel | `call_contact` | rester validation_required avant réel |
| Email | `send_email` | rester validation_required avant réel |
| Réunion | `start_meeting` | présent |
| Kanban | `organize_kanban` | présent |

## Cas d'erreur à faire ressortir dans le panneau

Le panneau doit afficher le vrai blocage, pas un message vague.

| Dernier maillon | Message panneau | Cause probable |
|---|---|---|
| `ws_ready` | Iris connectée, aucune parole reçue | micro / VAD / permission |
| `transcript_user` | Demande reçue, Iris n'a pas répondu | OpenAI / latency |
| `transcript_iris` | Iris a parlé sans déclencher d'outil | action router manquant |
| `chat_fallback` | Iris a utilisé chat au lieu d'un outil | mauvaise classification intent |
| `tool_call` | Outil déclenché, attente résultat | handler/endpoint lent |
| `tool_error` | Outil en erreur | endpoint/garde-fou/secret manquant |
| `render` | Rendu envoyé, affichage attendu | frontend renderer |
| `ics_render` | Rendu affiché | OK |

## Patch recommandé

Ne plus dépendre uniquement du choix spontané du modèle.

Ajouter un `Iris Action Router` déterministe côté serveur :

```text
entrée :
  - transcript_user
  - transcript_iris
  - dernier état pipeline

sortie :
  - action = chat / force_render / safe_tool / sensitive_draft / blocked
  - render_type
  - tool_name
  - missing_fields
  - guardrail_reason
```

Règle clé :

Si `transcript_iris` contient une promesse du type :

```text
je vais préparer
je vais créer
je vais générer
je vais faire
je m'en occupe
je vais afficher
je vais rédiger
```

et qu'aucun `tool_call` ni `render` n'arrive dans un délai court, alors le serveur ou le frontend doit forcer un rendu :

```text
last_user_request -> infer intent -> build render payload -> send render
```

## Exemple attendu

Demande :

```text
Prépare-moi un tableau avec les chiffres de vente : janvier 10, février 20, mars 30.
```

Résultat attendu :

```text
transcript_user
intent_detected: chart/table
tool_call: iris_render
render: chart ou data_board
ics_render
audio court : "C'est affiché."
```

Résultat interdit :

```text
transcript_iris: "Je vais préparer..."
audio playing...
timeout diagnostic
```

## Consigne Kimi

Kimi doit vérifier si le patch `391573b` suffit à provoquer `tool_call`.

Si le diagnostic reste sur `transcript_iris`, Kimi doit coder le fallback déterministe, sans action sensible :

1. détecter les promesses Iris ;
2. relire la dernière demande utilisateur ;
3. produire un rendu local ou serveur ;
4. afficher le vrai dernier maillon ;
5. ne jamais envoyer SMS/appel/email réel.

## Consigne DeepSeek

DeepSeek doit auditer :

1. la présence réelle de chaque outil dans `VOICE_TOOLS` ;
2. le routage `chat` vs `iris_render` ;
3. la liste des endpoints manquants ;
4. les garde-fous par action ;
5. les cas d'erreur non affichés.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_IRIS_ACTION_ROUTER_023.md
```

## Décision finale

Le problème n'est pas une clé API manquante dans l'interface.

Le problème est l'absence d'un routeur d'intentions fiable entre :

```text
ce que l'utilisateur demande
ce que OpenAI répond
ce que Iris doit réellement faire
ce que le Command Screen doit afficher
```

L'équipe doit maintenant construire ce routeur et prouver chaque capacité par une target cell.
