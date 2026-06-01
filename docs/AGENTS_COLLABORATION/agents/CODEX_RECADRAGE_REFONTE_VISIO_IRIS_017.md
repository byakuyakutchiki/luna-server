# Codex — Recadrage refonte visio Iris — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : risque / recadrage / proposition
Niveau : 2

## Retour fondateur Ludovic

La visio actuelle n'est pas acceptable.

Problemes identifies terrain :
- l'experience doit etre `visio avec Iris`, pas `visio Luna` ;
- des references Luna restent visibles dans la visio alors que l'interlocutrice doit etre Iris ;
- libelles incoherents : `Luna voit`, `Luna voix`, etc. ;
- un gros bouton superpose d'autres boutons ;
- le cadre graphique est juge tres moche ;
- l'organisation de l'interface visio est confuse ;
- les informations voix de Ludovic ne sont pas retransmises correctement ;
- il existe probablement une rupture cachee : endpoint, autorisation, connexion, micro, STT, ou element parasite.

Formulation produit :
> "Ce n'est pas visio avec secretaire visio avec Iris. Il y a des references Luna en visio qui ne devraient pas etre la. C'est tres moche, mal organise. Ma voix n'est pas retransmise. Il y a un vrai probleme de fond."

## Decision Codex

La visio actuelle ne doit plus etre traitee comme une suite de petits patchs.

On ouvre une refonte cadree de l'infrastructure visio Iris :
1. UX/identite ;
2. layout mobile ;
3. pipeline voix ;
4. logs/endpoints ;
5. vision camera ;
6. garde-fous cout/secrets/actions sensibles.

## Axes de refonte

### Axe A — Identite produit

La visio doit presenter Iris comme secretaire video.

A corriger :
- remplacer les references visibles `Luna` par `Iris` dans la surface visio ;
- garder Luna comme application/marque globale, mais pas comme interlocutrice visio ;
- retirer les libelles generiques `Chatbot` ;
- clarifier : `Iris ecoute`, `Iris reflechit`, `Iris repond`, `Iris voit`.

Occurrences reperees :
- `static/simli.html:632` : `Luna voit`
- `static/simli.html:636` : `Luna active`
- `static/simli.html:1882` : `Luna muette` / `Luna active`
- `static/simli.html:2057` : `Luna voit et peut en parler`
- libelle Daily visible en capture : `Chatbot`

### Axe B — UI mobile visio

La visio doit etre restructuree :
- pas de bouton qui superpose d'autres controles ;
- zone avatar propre ;
- micro/camera/status lisibles ;
- bouton raccrocher accessible sans masquer le reste ;
- orbe VAD integre sans bloquer les boutons ;
- design premium coherent Luna/Iris.

### Axe C — Pipeline voix

Le probleme voix reste P0.

Il faut prouver :
- le micro capte Ludovic ;
- VAD detecte parole ;
- MediaRecorder produit un blob non vide ;
- `/api/visio/transcribe` retourne le texte ;
- `/api/visio/chat` recoit le texte ;
- `/api/visio/tts` retourne l'audio ;
- le player joue l'audio ;
- la latence est mesuree.

### Axe D — Endpoints / connexions / autorisations

Soupcon fondateur :
un element cache peut bloquer ou parasiter la boucle.

A verifier :
- auth JWT sur `/api/visio/transcribe`, `/api/visio/chat`, `/api/visio/tts` ;
- permissions micro/camera WebView ;
- conflits Daily/Simli vs MediaRecorder ;
- mute implicite ;
- capture mauvaise cible WebView ;
- erreurs reseau silencieuses ;
- CORS / cookies / token ;
- endpoints deployes sur la bonne revision Cloud Run.

## Missions agents

Kimi :
- faire un audit UX visio Iris post-`a7af50e` ;
- proposer un layout mobile propre avec identite Iris ;
- interdire validation si superposition boutons / libelles Luna / Chatbot restent visibles.

DeepSeek :
- auditer les ruptures possibles endpoints/autorisations/micro/STT ;
- fournir une checklist technique `cause cachee` ;
- verifier conflit Daily/Simli/MediaRecorder/VAD.

Claude :
- ne pas ajouter de nouvelle fonctionnalite avant diagnostic ;
- produire une carte des libelles visio `Luna` -> `Iris` ;
- proposer un patch UI layout seulement apres validation Kimi/Codex ;
- ajouter logs non sensibles si absents.

Codex :
- capturer terrain apres deploy ;
- tenir matrice : symptome -> preuve -> cause -> patch ;
- faire respecter `Iris en visio`, `Luna application`.

## Decision Ludovic requise

Oui pour refonte visible majeure.

Les corrections de libelles mineurs peuvent etre Niveau 1, mais la refonte du cadre visio est Niveau 2.
