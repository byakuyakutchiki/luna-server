# Objectif 025 — Canaliser Iris

Date : 2026-06-04
Pilote : Codex
Statut : réflexion collective — aucun code

## Décision immédiate

Pause implémentation.

Aucun agent ne doit coder, déployer, modifier l'APK, activer une action réelle ou changer le comportement production pour cet objectif tant que Ludovic/Codex n'ont pas arbitré une méthode.

Objectif : réfléchir à la meilleure façon de canaliser Iris pour qu'elle reste dans ses prérogatives de secrétaire opérationnelle.

## Problème

Iris utilise une clé/API conversationnelle qui tend naturellement à répondre comme une IA généraliste.

Résultat :

- elle parle parfois comme un compagnon ;
- elle promet de faire sans déclencher l'outil ;
- elle se détache de ses prérogatives ;
- elle mélange discussion, conseil, action et rendu ;
- elle ne sait pas toujours quand entrer en mode fonctionnalité ;
- le décalage entre bouton, contexte, action et rendu nuit à la productivité.

Le problème n'est pas seulement technique. C'est un problème de cadrage produit, d'architecture d'intentions et d'expérience utilisateur.

## Identité cible

Iris est une secrétaire opérationnelle.

Iris doit :

- cadrer une mission ;
- comprendre un contexte de travail ;
- utiliser ses outils ;
- afficher ce qu'elle fait ;
- produire des livrables ;
- demander les informations manquantes ;
- préparer les actions sensibles sans les exécuter sans validation.

Iris ne doit pas :

- bavarder comme Luna ;
- partir en discussion libre hors mission ;
- donner de longues réponses molles ;
- promettre une action sans outil ;
- inventer une capacité non branchée ;
- masquer les erreurs.

## Fonctionnalités à inventorier

Chaque agent doit partir de cette base et la compléter.

| Famille | Exemples de fonctionnalités |
|---|---|
| Upload | charger PDF, image, document, tableur |
| Analyse | résumer, extraire, comparer, détecter risques |
| Notes | prendre notes de réunion, décisions, tâches |
| Tableaux | structurer données, colonnes, lignes |
| Graphiques | barres, courbes, camembert, KPI |
| Rédaction | courrier, compte-rendu, rapport, proposition |
| Export | TXT, PDF, document propre |
| Recherche | web, sources, fiabilité, synthèse |
| Documents | porte-documents, recherche interne, classement |
| Contacts | retrouver contact, préparer message |
| Communication | SMS/email/appel en validation |
| Équipe | invitation, rôles, mute/kick, réunion |
| Carte | lieu, adresse, trajet, consentement |
| Conformité | RGPD, action sensible, données personnelles |

## Méthodes possibles à comparer

Les agents doivent proposer et comparer plusieurs méthodes.

### Méthode A — Boutons / modes explicites

L'utilisateur choisit :

- Analyse document ;
- Réunion ;
- Tableau ;
- Graphique ;
- Rédaction ;
- Recherche ;
- Actions.

Avantage : très cadré, moins d'aléatoire.

Risque : interface trop lourde si mal designée.

### Méthode B — Mode selector + contexte injecté

Un menu compact définit le contexte courant. Iris reçoit des instructions différentes selon le mode.

Avantage : bon équilibre entre liberté et contrôle.

Risque : le modèle peut encore ignorer le contexte si le routeur ne force pas.

### Méthode C — Intent router déterministe

Le serveur lit la demande utilisateur, détecte les mots déclencheurs et route vers l'outil/rendu avant de laisser Iris parler.

Avantage : robuste, testable.

Risque : demande une table d'intents bien maintenue.

### Méthode D — Workflow par formulaire guidé

Pour les actions productives, Iris pose des questions courtes et remplit un panneau.

Avantage : fiable pour documents/actions.

Risque : moins naturel si trop rigide.

### Méthode E — Hybride recommandé

Combiner :

```text
mode explicite visible
+ routeur d'intentions
+ boutons contextuels
+ Command Screen
+ garde-fous
```

Objectif : Iris reste naturelle mais n'est jamais libre de partir hors mission.

## Questions à trancher

Chaque agent doit répondre :

1. Quelles fonctionnalités Iris doit-elle absolument maîtriser en V1 ?
2. Quelles fonctionnalités doivent rester en brouillon/validation ?
3. Quelle méthode canalise le mieux Iris sans casser l'expérience ?
4. Quels boutons ou modes doivent être visibles ?
5. Quels mots déclencheurs doivent forcer un outil ?
6. Où placer les garde-fous ?
7. Comment prouver qu'une fonctionnalité atteint sa target ?
8. Comment éviter qu'Iris dise "je vais faire" sans faire ?
9. Comment gérer les documents et exports proprement ?
10. Quels endpoints manquent ou sont risqués ?

## Livrables attendus

### Kimi

Fichier attendu :

```text
docs/AGENTS_COLLABORATION/agents/KIMI_METHODE_CANALISER_IRIS_025.md
```

Mission :

- proposer UX/modes/boutons ;
- éviter surcharge visuelle ;
- définir le comportement humain et professionnel d'Iris ;
- dire comment rendre le travail visible et premium.

### DeepSeek

Fichier attendu :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_METHODE_CANALISER_IRIS_025.md
```

Mission :

- proposer architecture intent/router/tools/endpoints ;
- lister les endpoints manquants ;
- auditer les risques ;
- proposer une méthode testable.

### Claude

Fichier attendu :

```text
docs/AGENTS_COLLABORATION/agents/CLAUDE_METHODE_CANALISER_IRIS_025.md
```

Mission :

- proposer architecture d'implémentation ;
- expliquer où brancher le routeur ;
- définir un plan sans coder ;
- estimer complexité et risques.

### Codex

Fichier attendu :

```text
docs/AGENTS_COLLABORATION/agents/CODEX_ARBITRAGE_CANALISER_IRIS_025.md
```

Mission :

- synthétiser les méthodes ;
- choisir une V1 ;
- créer la target cell finale ;
- donner la consigne de code seulement après arbitrage.

## Règle de livraison

Interdit de dire "c'est bon" sans :

- mode défini ;
- target définie ;
- outil ou rendu attendu ;
- garde-fou listé ;
- test d'acceptation.

Pour l'instant :

```text
audit / réflexion / proposition uniquement
pas de code
pas de déploiement
pas d'APK
pas d'action réelle
```

## But final

Faire d'Iris une secrétaire de mission fiable :

```text
je choisis le contexte
Iris comprend son rôle
Iris utilise l'outil adapté
Iris affiche son travail
Iris produit un livrable propre
Iris demande validation avant action sensible
```

Pas une IA libre qui improvise.
