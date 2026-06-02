# Codex — Patch identité / outils Iris — Objectif 019

Date : 2026-06-02
Agent : Codex
Type : correctif niveau 1 + cadrage garde-fous

## Retour terrain Ludovic

Constats sur Iris Audio :

- Iris ne sait pas toujours qu'elle s'appelle Iris.
- Elle peut se présenter comme un autre assistant.
- Elle ne dit pas clairement qu'elle est une IA.
- Elle ne connaît pas assez son environnement de travail.
- Elle ne sait pas décrire ce qu'elle peut faire.
- Les phrases d'accueil contiennent des formulations faibles ou incorrectes.
- Le panneau Iris Workbench n'est pas encore visible.

## Cause probable

`/ws/iris-voice` utilisait le contexte historique de Luna Voice via `build_voice_context()`.

Ce contexte contient encore des phrases d'identité Luna, dont :

- "Tu es Luna..."
- "Tu es Luna, point final..."

Le mode Iris était ajouté ensuite, mais sans neutraliser assez fortement l'identité Luna.

Deuxième cause :

`WebVoiceBridge` recevait la liste des tools OpenAI Realtime, mais `tool_handler=None`.

Résultat : Iris pouvait voir des outils dans la session, mais aucune exécution serveur réelle n'était branchée côté Iris.

## Patch appliqué

Fichier : `luna_web.py`

### 1. Salutations Iris

Remplacement des 15 phrases d'accueil par des phrases propres, sans faute, toutes centrées sur Iris.

Exemples :

- "Bonjour Ludovic. Je suis Iris. Comment vas-tu ? Je peux faire quelque chose pour toi ?"
- "Bonjour Ludovic. Iris à l'écoute. Quelle mission me confies-tu ?"
- "Bonjour Ludovic. Je peux t'aider à chercher, structurer ou préparer un document."

### 2. Identité Iris prioritaire

Ajout d'un bloc système fort :

- Iris est une IA.
- Iris est l'assistante opérationnelle de Luna YAWatch.
- Luna est le compagnon conversationnel / figure dirigeante.
- Iris est la secrétaire technique, administrative et documentaire.
- Iris ne doit jamais dire qu'elle s'appelle Alex ou Luna.

### 3. Neutralisation du contexte Luna

Dans `/ws/iris-voice`, le contexte issu de `build_voice_context()` est corrigé avant injection :

- "Tu es Luna..." devient "Tu es Iris..."
- la phrase "Tu es Luna, point final" devient "Tu es Iris, point final"

### 4. Tool handler Iris sécurisé

Ajout de `handle_iris_tool()`.

Outils autorisés immédiatement :

- recherche web ;
- lieux ;
- page web ;
- météo ;
- actualités ;
- contacts ;
- documents en lecture ;
- budget ;
- rappels en lecture ;
- missions / badges.

Actions mises en validation requise :

- SMS ;
- email ;
- appel ;
- alerte ;
- invitation ;
- paiement ;
- réservation ;
- génération document ;
- note / instruction / rappel persistant.

Objectif : Iris peut comprendre l'environnement et chercher, mais elle ne déclenche pas une action engageante sans Workbench + validation.

## Ce que ce patch ne fait pas

Il ne crée pas encore le panneau visible Iris Workbench.

Le panneau Workbench V1 reste niveau 2 :

- visible ;
- structurant ;
- lié aux documents ;
- nécessite validation Ludovic avant déploiement.

## Tests attendus après déploiement

Sur Iris Audio :

1. "Comment tu t'appelles ?"
   - attendu : "Je suis Iris..."

2. "Tu es quoi ?"
   - attendu : "Je suis une IA assistante de YAWatch..."

3. "Qu'est-ce que tu peux faire ?"
   - attendu : chercher, structurer, préparer brouillon, lire contexte autorisé, agir après validation.

4. "Cherche-moi une information sur Internet."
   - attendu : outil `search_web` si clé disponible, ou message clair si service absent.

5. "Envoie un SMS."
   - attendu : refus d'exécution directe + demande de validation / Workbench.

## Message agent

Agent : Codex
Objectif : 019
Type : correctif identité / outils Iris
Résumé : Retour terrain traité : Iris pouvait hériter du contexte Luna et se présenter incorrectement. Patch : salutations propres, identité Iris prioritaire, neutralisation des phrases "Tu es Luna" dans le contexte `/ws/iris-voice`, ajout d'un `handle_iris_tool()` sécurisé. Iris peut maintenant utiliser les outils de lecture/recherche, mais les actions sensibles ou persistantes répondent `validation_required` tant que Workbench V1 n'est pas validé.
Fichier concerné : `luna_web.py`
Risque : moyen-faible ; améliore identité et garde-fous sans action sensible
Décision Ludovic requise : oui pour Workbench visible V1
Action proposée : Claude déploie ce patch, Ludovic teste identité/capacités, puis Claude prépare Workbench V1 à partir de Kimi.
