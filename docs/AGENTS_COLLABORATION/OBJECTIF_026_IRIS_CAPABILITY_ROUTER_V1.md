# Objectif 026 — Iris Capability Router V1

Date ouverture : 2026-06-04
Pilote coordination : Codex
Statut : ouvert — code V1 autorisé dans le scope ci-dessous
Décision fondateur : Ludovic donne le feu vert pour ouvrir l'objectif 026.

## 1. But

Transformer Iris en secrétaire opérationnelle canalisée.

Iris ne doit plus choisir librement entre bavarder, promettre ou agir.

Elle doit passer par une chaîne contrôlée :

```text
demande utilisateur
-> mode actif
-> intent détecté
-> niveau de risque
-> outil autorisé
-> rendu Command Screen
-> preuve Target Cell
```

## 2. Méthode retenue

Méthode hybride 3 niveaux.

### Niveau 1 — automatique

Lecture, recherche simple, structuration, tableau, graphique, checklist, documents listés.

Iris agit directement.

```text
comprendre -> afficher -> expliquer brièvement
```

### Niveau 2 — guidé

Analyse document, rédaction, business plan, compte-rendu, comparaison, livrable.

Iris cadre la mission, affiche les informations manquantes, produit un brouillon ou un rendu.

```text
cadrer -> afficher -> demander manque -> produire
```

### Niveau 3 — validation obligatoire

SMS, appel, email, invitation, exclusion, partage, suppression, paiement, réservation.

Iris ne fait rien de réel sans validation explicite.

```text
préparer -> action_board -> validation -> exécution si autorisée
```

## 3. Scope V1 autorisé

### Autorisé

- ajouter `active_mode` par session Iris ;
- ajouter `RISK_LEVELS` par outil ;
- ajouter `VOICE_TOOLS_BY_MODE` ;
- ajouter prompts spécialisés par mode ;
- ajouter un routeur serveur simple `intent -> mode -> risk -> render/tool` ;
- brancher les modes non sensibles au Command Screen ;
- afficher les erreurs utiles : mode ambigu, infos manquantes, action sensible bloquée ;
- ajouter logs de preuve : `mode_detected`, `intent_detected`, `risk_level`, `tool_allowed`, `render_type`, `render_done`.

### Interdit en V1

- aucun SMS réel ;
- aucun appel réel ;
- aucun email réel ;
- aucune suppression de document ;
- aucun paiement ;
- aucune réservation ;
- aucune clé API côté frontend ;
- aucun nouveau secret dans GitHub ;
- aucun faux rendu statique présenté comme résultat ;
- aucun déploiement si les Target Cells minimales ne sont pas documentées.

## 4. Modes V1

| Mode | Niveau principal | Tools attendus | Rendus |
|---|---:|---|---|
| Discussion | 1 | chat court | aucun ou context_panel léger |
| Tableau / Graphique | 1 | iris_render | table, chart, kpi_cards, missing_info |
| Recherche web | 1 | search_web | research_board, source_cards |
| Analyse documents | 2 | list_documents, analyze_document | document_insight |
| Réunion | 2 | create_note, start_meeting, organize_kanban | meeting_board, kanban_board |
| Rédaction | 2 | generate_document | document_draft |
| Actions | 3 | send_sms, send_email, call_contact | action_board |
| Équipe | 3 | invite_to_session, manage_team | status_rail, action_board |
| Carte | 2 | search_places | map_board |
| Conformité | 2 | compliance_check | compliance_panel |

## 5. Target Cells obligatoires

Chaque capacité livrée doit remplir :

| Champ | Obligatoire |
|---|---|
| Phrase test | oui |
| Mode actif | oui |
| Intent détecté | oui |
| Niveau de risque | oui |
| Outil attendu | oui |
| Endpoint appelé | oui si applicable |
| Render attendu | oui |
| Garde-fou | oui |
| Logs de preuve | oui |
| Résultat visible | oui |
| Latence cible | oui |

## 6. Target Cells V1 minimales

### TC-026-01 — Graphique simple

```text
Phrase : "Prépare un graphique avec janvier 10, février 20, mars 30"
Mode : Tableau / Graphique
Intent : chart_from_values
Risque : 1
Outil : iris_render
Render : chart
Garde-fou : aucun, lecture/rendu local
Preuve : mode_detected -> intent_detected -> tool_allowed -> render_type=chart -> render_done
Latence cible : < 3s
```

### TC-026-02 — Graphique sans données

```text
Phrase : "Prépare un graphique business plan"
Mode : Tableau / Graphique
Intent : chart_missing_values
Risque : 1
Outil : iris_render
Render : missing_info
Garde-fou : ne pas inventer de chiffres
Preuve : render_type=missing_info
Latence cible : < 2s
```

### TC-026-03 — Recherche web

```text
Phrase : "Cherche Base Legacy sur le web et affiche les sources"
Mode : Recherche web
Intent : web_research
Risque : 1
Outil : search_web
Render : research_board
Garde-fou : citer les sources, ne pas prétendre sans résultat
Preuve : tool_call=search_web -> sources visibles -> render_done
Latence cible : < 6s
```

### TC-026-04 — Rédaction brouillon

```text
Phrase : "Rédige un courrier professionnel pour un exploitant"
Mode : Rédaction
Intent : document_draft
Risque : 2
Outil : generate_document ou iris_render
Render : document_draft
Garde-fou : brouillon seulement, pas d'envoi
Preuve : render_type=document_draft -> placeholders si données manquantes
Latence cible : < 6s
```

### TC-026-05 — SMS bloqué

```text
Phrase : "Envoie un SMS à Lucas"
Mode : Actions
Intent : prepare_sms
Risque : 3
Outil : send_sms préparé ou action_board
Render : action_board
Garde-fou : aucun SMS réel, validation obligatoire
Preuve : risk_level=3 -> validation_required=true -> no_external_send
Latence cible : < 3s
```

## 7. Rôles agents

### Claude

Implémentation backend V1.

À coder :

- `active_mode` dans la session Iris ;
- `VOICE_TOOLS_BY_MODE` ;
- `_MODE_SYSTEM_PROMPTS` ;
- `RISK_LEVELS` ;
- pré-classification serveur minimale ;
- logs de preuve ;
- blocage niveau 3 en `action_board`.

Interdits :

- pas d'action réelle ;
- pas de clé frontend ;
- pas de refonte UI ;
- pas de déploiement sans message GitHub clair.

### Kimi

UX et éventuellement code frontend selon contexte.

À livrer :

- mode selector propre ;
- badge mode actif ;
- rendu Command Screen lisible ;
- erreurs utiles ;
- pas de surcharge de boutons ;
- vérification clair/sombre mobile.

### DeepSeek

Audit technique et garde-fous.

À livrer :

- triggers par mode ;
- endpoints existants/manquants ;
- contrôle `RISK_LEVELS` ;
- contre-audit du code Claude/Kimi ;
- tests d'acceptation par Target Cell.

### Codex

Coordination et validation.

À livrer :

- vérifier que la chaîne respecte la méthode ;
- bloquer les actions sensibles ;
- refuser les "c'est bon" sans Target Cell ;
- produire verdict après tests.

## 8. Définition de "livré"

Objectif 026 n'est pas livré quand le code compile.

Il est livré quand au moins les 5 Target Cells V1 prouvent :

```text
mode -> intent -> risk -> tool/render -> visible result
```

Et que le niveau 3 ne déclenche aucune action réelle.

