# DeepSeek — Méthode Canaliser Iris — Objectif 025

Source : texte DeepSeek transmis par Ludovic dans le fil, relayé sur GitHub par Codex.
Date : 2026-06-04
Type : méthode technique / intent router / risk levels
Statut : avis DeepSeek relayé — aucun code

## Verdict DeepSeek

Iris doit être canalisée par une méthode hybride.

Une discussion libre avec OpenAI est trop aléatoire pour une secrétaire opérationnelle. Le système doit décider en amont du niveau de contrôle nécessaire selon la demande.

## Méthode recommandée — Hybride 3 niveaux

### Niveau 1 — Router automatique

Pour les demandes simples, non sensibles et lisibles directement.

Exemples :

- "Montre-moi mes documents"
- "Fais un tableau avec janvier 10, février 20, mars 30"
- "Cherche une information publique"
- "Affiche une checklist"

Comportement :

```text
intent détecté -> outil autorisé -> rendu immédiat
```

Pas de confirmation nécessaire.

### Niveau 2 — Mode suggéré / confirmé

Pour le travail structuré qui demande un contexte clair.

Exemples :

- "Analyse ce PDF"
- "Prépare un graphique business plan"
- "Rédige un courrier"
- "Prépare un compte-rendu"
- "Compare ces documents"

Comportement :

```text
mode détecté -> Iris affiche le panneau adapté -> demande les infos manquantes -> produit un brouillon
```

Confirmation uniquement si l'utilisateur veut sauvegarder, exporter ou partager.

### Niveau 3 — Workflow guidé obligatoire

Pour les actions sensibles ou externes.

Exemples :

- SMS
- appel
- email
- invitation
- exclusion participant
- partage externe
- paiement
- réservation
- suppression de données

Comportement :

```text
préparation -> action_board -> validation explicite -> exécution si autorisée
```

Aucune action réelle sans confirmation.

## Matrice Intent -> Niveau -> Rendu

| Demande utilisateur | Niveau | Outil attendu | Rendu attendu |
|---|---:|---|---|
| "Montre-moi mes documents" | 1 | list_documents | table / kpi_cards |
| "Fais un graphique avec ces chiffres" | 1 | iris_render | chart |
| "Cherche X sur le web" | 1 | search_web | research_board |
| "Analyse ce PDF" | 2 | analyze_document | document_insight |
| "Rédige un courrier" | 2 | generate_document | document_draft |
| "Prépare un business plan" | 2 | generate_plan / iris_render | document_draft + kpi_cards |
| "Envoie un SMS" | 3 | send_sms | action_board |
| "Appelle ce contact" | 3 | make_call | action_board |
| "Invite X dans la session" | 3 | manage_team | action_board / status_rail |
| "Supprime ce document" | 3 | delete_document | action_board |

## Risk levels proposés

| Outil | Niveau | Raison |
|---|---:|---|
| iris_render | 1 | rendu local, lecture seule |
| search_web | 1 | lecture externe publique |
| get_documents | 1/2 | dépend des droits utilisateur |
| analyze_document | 2 | données personnelles possibles |
| generate_document | 2 | production de livrable |
| show_map | 2 | consentement géoloc possible |
| create_task | 2 | impact organisationnel limité |
| send_sms | 3 | coût + action externe |
| make_call | 3 | coût + action externe |
| send_email | 3 | action externe |
| manage_team | 3 | impact participant |
| payment | 3 | financier |
| delete_document | 3 | suppression de donnée |

## Architecture minimale proposée

### Session

Ajouter un état de session :

```text
active_mode
last_intent
last_render_type
risk_level
pending_action
```

### Router

Le serveur doit classifier chaque demande avant de laisser Iris parler.

```text
user_text -> detect_intent -> detect_mode -> detect_risk -> dispatch
```

Si le risque est 1 :

```text
dispatch direct
```

Si le risque est 2 :

```text
mode guidé + panneau infos manquantes si besoin
```

Si le risque est 3 :

```text
action_board + validation obligatoire
```

### Tool filtering

La liste d'outils disponibles doit dépendre du mode et du niveau de risque.

Exemple :

```text
mode=tableau -> iris_render, chart, table uniquement
mode=communication -> get_contacts, send_sms, send_email, make_call, action_board
mode=analyse -> list_documents, analyze_document, document_insight
```

## Tests d'acceptation proposés

Chaque capacité doit avoir une Target Cell.

| Test | Attendu |
|---|---|
| "Fais un graphique janvier 10 février 20" | chart affiché, pas de texte seul |
| "Montre mes documents" | table documents, pas de refus générique |
| "Analyse ce PDF" | document_insight ou panneau upload demandé |
| "Envoie un SMS à Lucas" | action_board validation, aucun SMS réel |
| "Appelle Lucas" | action_board validation, aucun appel réel |
| "Cherche Base Legacy" | research_board avec sources |
| "Rédige un courrier" | document_draft avec champs manquants |
| "Invite Lucas" | action_board owner-only |

## Avis sur la méthode Claude / Kimi

DeepSeek valide la direction hybride :

- Kimi a raison sur le besoin de modes visibles ;
- Claude a raison sur les prompts spécialisés et `VOICE_TOOLS_BY_MODE` ;
- Codex a raison de refuser une clé API dans le panneau frontend ;
- il faut ajouter un niveau de risque technique pour éviter que tout soit traité pareil.

## Prochaine action proposée

Ouvrir après validation :

```text
Objectif 026 — Iris Capability Router V1
```

Scope :

1. active_mode en session ;
2. intent router serveur ;
3. risk levels ;
4. tools filtrés par mode ;
5. Target Cell par mode ;
6. aucun SMS/appel/email réel en V1.

## Message AGENT_CHANNEL

Agent : DeepSeek
Objectif : 025
Type : méthode technique / relay Ludovic-Codex
Résumé : DeepSeek recommande une méthode hybride 3 niveaux : router automatique pour lecture/rendu simple, mode suggéré pour travail structuré, workflow guidé obligatoire pour actions sensibles. Ajout clé : risk levels par outil. Prochaine étape proposée : Objectif 026 Iris Capability Router V1 avec active_mode, intent router, tools filtrés, risk levels et Target Cell par mode.
Fichier concerné : docs/AGENTS_COLLABORATION/agents/DEEPSEEK_METHODE_CANALISER_IRIS_025.md
Risque : moyen si l'équipe traite recherche, document, SMS et appel au même niveau de risque.
Décision Ludovic requise : oui avant code Objectif 026
Action proposée : Codex met à jour l'arbitrage en tenant compte du texte DeepSeek relayé.

