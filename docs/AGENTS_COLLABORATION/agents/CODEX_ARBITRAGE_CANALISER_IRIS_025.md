# Codex — Arbitrage Canaliser Iris — Objectif 025

Date : 2026-06-04
Agent : Codex
Type : arbitrage produit / technique
Statut : méthode validable — aucun code demandé ici

## 1. État des livraisons

| Agent | Livrable GitHub | Statut |
|---|---|---|
| Claude | `CLAUDE_METHODE_CANALISER_IRIS_025.md` | livré |
| Kimi | `KIMI_METHODE_CANALISER_IRIS_025.md` | livré |
| DeepSeek | `DEEPSEEK_METHODE_CANALISER_IRIS_025.md` | non trouvé sur GitHub au moment de l'arbitrage |

L'analyse DeepSeek reçue dans le chat est pertinente, mais elle doit être poussée sur GitHub pour être considérée comme livrée officiellement.

## 2. Consensus équipe

Claude et Kimi convergent sur le même fond :

Iris ne doit pas être laissée en conversation libre.

Le problème n'est pas seulement le prompt. Le problème est que le modèle peut choisir de bavarder, de promettre ou d'appeler un outil vague. Il faut donc encadrer Iris par une architecture de mission.

Méthode retenue : hybride contrôlé.

```text
mode explicite visible
+ pré-classification serveur
+ prompt spécialisé par mode
+ outils filtrés par mode
+ niveau de risque
+ fallback déterministe
```

## 3. Décision Codex

Je valide la méthode hybride, avec une nuance importante :

Iris ne doit pas demander confirmation pour tout.

Elle doit être rapide pour les actions de lecture et de rendu, mais stricte pour les actions engageantes.

## 4. Niveaux d'action Iris

### Niveau 1 — automatique

Lecture, structuration et rendu visuel sans impact externe.

Exemples :

- afficher un tableau ;
- créer un graphique avec des données fournies ;
- montrer une checklist ;
- résumer une discussion ;
- afficher les documents accessibles ;
- chercher une information web publique avec sources.

Comportement attendu :

```text
Iris comprend -> affiche -> explique brièvement.
```

Pas de longue discussion. Pas de validation nécessaire.

### Niveau 2 — guidé

Travail productif qui demande un contexte ou des données.

Exemples :

- analyser un PDF ;
- comparer plusieurs documents ;
- rédiger un courrier ;
- préparer un business plan ;
- générer un rapport ;
- préparer une synthèse de réunion.

Comportement attendu :

```text
Iris affiche le panneau -> montre les données manquantes -> produit un brouillon -> propose export.
```

Validation requise seulement avant stockage définitif, export sensible ou partage.

### Niveau 3 — validation obligatoire

Action réelle, externe, coûteuse ou sensible.

Exemples :

- envoyer SMS ;
- envoyer email ;
- passer appel Twilio ;
- inviter/exclure quelqu'un ;
- partager un document ;
- supprimer des données ;
- paiement, réservation, action juridique.

Comportement attendu :

```text
Iris prépare -> affiche action_board -> attend validation explicite -> exécute si autorisé.
```

Aucune action réelle sans validation Ludovic/utilisateur propriétaire.

## 5. Modes V1 retenus

| Mode | Objectif | Rendus attendus | Risque |
|---|---|---|---|
| Discussion | échange court, non productif | chat léger | 1 |
| Tableau / Graphique | structurer chiffres et données | table, chart, kpi_cards | 1 |
| Analyse documents | lire, résumer, comparer | document_insight, data_board | 2 |
| Réunion | notes, décisions, tâches | meeting_board, kanban_board | 2 |
| Rédaction | courrier, rapport, brouillon | document_draft | 2 |
| Recherche web | chercher sources externes | research_board, source_cards | 1 |
| Actions | SMS/email/appel en brouillon | action_board | 3 |
| Équipe | inviter, rôles, mute/kick | status_rail, action_board | 3 |
| Carte | adresse, lieu, trajet | map_board | 2 |
| Conformité | RGPD, garde-fous, risques | compliance_panel | 2 |

## 6. Règle centrale

Iris ne décide pas librement de son rôle.

Le rôle vient de trois endroits :

1. le mode choisi par l'utilisateur ;
2. l'intent router serveur ;
3. le niveau de risque de l'action.

Si ces trois éléments ne sont pas clairs, Iris affiche un panneau "information manquante" au lieu de parler dans le vide.

## 7. Architecture à coder après validation

### 7.1 Frontend

Kimi doit préparer le mode selector :

- 5 modes principaux visibles ;
- menu compact pour les modes secondaires ;
- badge du mode actif dans le Command Screen ;
- pas de surcharge visuelle ;
- mode clair/sombre lisible ;
- boutons utiles seulement selon le mode.

### 7.2 Backend

Claude/Kimi Code devront préparer :

- `active_mode` par session ;
- `VOICE_TOOLS_BY_MODE` ;
- prompts spécialisés par mode ;
- pré-classification serveur ;
- table `RISK_LEVELS` ;
- fallback déterministe si Iris promet sans outil.

### 7.3 DeepSeek

DeepSeek doit pousser sur GitHub :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_METHODE_CANALISER_IRIS_025.md
```

Contenu attendu :

- liste des triggers par mode ;
- endpoints manquants ;
- risques par outil ;
- tests d'acceptation ;
- avis sur `VOICE_TOOLS_BY_MODE` ;
- avis sur `RISK_LEVELS`.

## 8. Target Cell minimale avant tout "c'est bon"

Chaque mode doit avoir une cellule de test :

| Champ | Obligatoire |
|---|---|
| Phrase test | oui |
| Mode actif | oui |
| Intent détecté | oui |
| Outil attendu | oui |
| Endpoint appelé | oui si applicable |
| Render attendu | oui |
| Garde-fou | oui |
| Log preuve | oui |
| Résultat visuel | oui |
| Latence cible | oui |

Exemple :

```text
Phrase : "Prépare un graphique janvier 10, février 20, mars 30"
Mode : Tableau / Graphique
Intent : chart_from_values
Outil : iris_render
Endpoint : aucun
Render : chart
Garde-fou : lecture seule
Preuve : tool_call -> render -> render_done
Latence cible : < 3s
```

## 9. Ce qu'il ne faut pas faire

- Ne pas mettre de clé API dans le panneau frontend.
- Ne pas laisser Iris choisir seule entre bavarder et agir.
- Ne pas ajouter des boutons décoratifs sans endpoint.
- Ne pas faire de faux rendu statique.
- Ne pas déployer une correction 025 sans arbitrage explicite.
- Ne pas dire à Ludovic de tester sans Target Cell.

## 10. Prochaine consigne

Tant que DeepSeek n'a pas poussé son fichier, l'équipe reste en réflexion.

Quand DeepSeek aura livré, Codex pourra ouvrir l'étape suivante :

```text
Objectif 026 — Iris Capability Router V1
```

Scope probable :

1. mode selector propre ;
2. active_mode par session ;
3. tools filtrés par mode ;
4. pré-classification serveur pour tableau/graphique/recherche/rédaction ;
5. risk levels ;
6. tests Target Cell.

Pas d'action sensible dans la V1.

