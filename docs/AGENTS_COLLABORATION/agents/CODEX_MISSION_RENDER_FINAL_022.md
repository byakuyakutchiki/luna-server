# Codex — Mission audit Render Final Iris — Objectif 022

Date : 2026-06-03
Agent : Codex
Type : mission audit DeepSeek + Kimi

## Constat terrain Ludovic

Capture terrain après déploiement Kimi `luna-beta-00514-4wr` :

- Iris ouvre bien le Command Screen ;
- l'état "Préparation trop longue" apparaît ;
- le panneau indique : connexion toujours ouverte, rendu final non reçu ;
- Ludovic confirme : "elle affiche le panneau, mais à l'intérieur elle ne fait pas ce qu'elle dit".

Conclusion :

Le déclenchement UI fonctionne.
La rupture arrive après l'intention :

```text
demande utilisateur
-> Iris annonce/prépare
-> panneau ouvert
-> aucun rendu final utile ne revient
```

Ce n'est donc pas seulement graphique. C'est une rupture pipeline :

```text
intent -> tool_call -> tool_result -> iris_render -> render_update/render_done
```

## But produit

Iris ne doit pas décrire ce qu'elle pourrait afficher.

Iris doit :

1. comprendre l'intention ;
2. choisir un outil ou un render_type ;
3. afficher un squelette visible ;
4. remplir progressivement le panneau ;
5. afficher un rendu final exploitable ;
6. parler très brièvement pour commenter le résultat.

## Tests terrain qui échouent ou restent suspects

- "affiche le panneau" : le panneau apparaît, mais pas de contenu final utile ;
- "prépare un tableau" : Iris annonce/prépare, mais le tableau n'est pas matérialisé comme promis ;
- "prépare un business plan" : risque de discours au lieu de livrable ;
- "démarre une réunion" : doit produire `meeting_board`, à vérifier ;
- "organise mes tâches : devis MSA, appel client, facturation" : doit produire `kanban_board`, à vérifier.

## Ce que DeepSeek doit auditer

Lire :

- `integrations/openai/realtime_bridge.py`
- `integrations/openai/web_voice_bridge.py`
- `luna_web.py`
- `static/simli.html`
- `docs/AGENTS_COLLABORATION/agents/CODEX_FIX_IRIS_CHART_SOURCE_022.md`
- `docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_TEAM_TELEWORK_OS_022.md`

Questions obligatoires :

1. Est-ce que `VOICE_TOOLS` expose bien `iris_render`, `start_meeting`, `organize_kanban` ?
2. Est-ce que le modèle Realtime est réellement autorisé à appeler ces tools ?
3. Quand un tool est appelé, est-ce que `web_voice_bridge.py` renvoie bien un `function_call_output` ?
4. Est-ce qu'un `response.create` est déclenché au bon moment ?
5. Est-ce que le résultat tool est transformé en `render_type` côté `luna_web.py` ou bridge ?
6. Est-ce que `static/simli.html` reçoit bien `data.type === "render"` ?
7. Est-ce que `renderIrisCommand(data)` reçoit un payload final exploitable ?
8. Pourquoi le timeout 10s s'active alors que la connexion reste ouverte ?
9. Est-ce que l'IA parle d'un rendu au lieu d'appeler `iris_render` ?
10. Est-ce que les nouveaux tools Kimi retournent des données structurées suffisantes ?

Verdict attendu :

| Maillon | Statut | Preuve fichier/ligne |
|---|---|---|
| Intent détecté | ? | ? |
| Tool appelé | ? | ? |
| Tool result reçu | ? | ? |
| Render envoyé au client | ? | ? |
| Render affiché | ? | ? |
| Timeout déclenché | ? | ? |

## Ce que Kimi doit auditer

Kimi doit vérifier le rendu réel :

1. Le panneau est-il trop brouillon ?
2. "Préparation trop longue" est-il utile ou anxiogène ?
3. Les boutons Modifier/Copier/Télécharger/Fermer dominent-ils trop l'écran mobile ?
4. Le mode clair est-il trop pâle / faible contraste ?
5. L'état doit-il montrer une barre de progression, des étapes ou un spinner premium ?
6. Est-ce que l'utilisateur comprend ce qu'Iris attend ?
7. Le timeout doit-il proposer automatiquement : relancer, simplifier, donner les données manquantes, voir diagnostic ?

Kimi doit proposer une correction UX sans masquer le bug technique.

## Interdits

- Ne pas dire "c'est bon" sans test terrain.
- Ne pas ajouter un faux rendu statique.
- Ne pas masquer "Préparation trop longue" si le pipeline est cassé.
- Ne pas lancer SMS/appel/email/Twilio réel.
- Ne pas toucher secrets, DB, APK.

## Livrables attendus

DeepSeek :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_RENDER_FINAL_022.md`

Kimi :

`docs/AGENTS_COLLABORATION/agents/KIMI_AUDIT_RENDER_FINAL_UX_022.md`

Puis message court dans `AGENT_CHANNEL.md`.

## Définition de correction

Une correction est acceptée seulement si :

- le panneau ne reste plus bloqué sur "Préparation trop longue" pour une demande simple ;
- un vrai `render_type` final arrive ;
- le contenu affiché correspond à la demande utilisateur ;
- si données manquantes, le panneau le dit précisément ;
- les logs permettent de voir le maillon cassé.
