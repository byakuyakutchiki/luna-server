# Objectif 012 - Canal de decision agents Luna

## But

Creer un canal de travail leger entre Kimi, Codex, DeepSeek et Claude, sans cout supplementaire, pour que les agents puissent avancer ensemble quand Ludovic n'est pas disponible.

## Principe V1

GitHub sert de salle de decision gratuite.

Structure :

- `docs/AGENTS_COLLABORATION/AGENT_CHANNEL.md` : fil court des messages importants entre agents.
- `docs/AGENTS_COLLABORATION/DECISIONS_PENDING.md` : decisions en attente Ludovic.
- `docs/AGENTS_COLLABORATION/DECISIONS_VALIDATED.md` : decisions validees.
- `docs/AGENTS_COLLABORATION/AGENT_RULES_LIGHT.md` : regles courtes de communication.

## Objectif produit

Luna doit pouvoir etre livree a un exploitant comme une application SaaS exploitable, tout en preservant le code et le modele fondateur.

Le travail prioritaire reste le test bouton par bouton :

- chaque bouton visible doit fonctionner ;
- chaque clic doit arriver a la cible attendue ;
- chaque action sensible doit etre bloquee ou simulee sans validation ;
- chaque amelioration doit renforcer l'UI, la fluidite ou la fonctionnalite ;
- aucune regression graphique n'est acceptable.

## Methode d'entreprise

Les agents doivent fonctionner comme une mini-equipe :

- Kimi protege l'experience, le graphisme et les textes.
- Codex trie, structure, coordonne et prepare les decisions.
- DeepSeek audite la faisabilite technique et les risques code.
- Claude integre et deploie seulement quand le niveau de decision le permet.

## Garde-fous

- Pas d'endpoint serveur en V1.
- Pas de cout supplementaire.
- Pas de logs geants.
- Pas de longs rapports.
- Pas de fork ou branche sauvage sans objectif clair.
- Pas de modification majeure sans validation Ludovic.
- Pas de production, paiement, reservation, SMS, email, appel reel, secret, Google Cloud, base de donnees ou suppression de donnees sans niveau 3.

## V2 possible

Si la V1 fonctionne, creer ensuite un vrai canal dans le cockpit fondateur :

`/api/agents/channel`

Cette V2 devra etre validee par Ludovic avant implementation.
