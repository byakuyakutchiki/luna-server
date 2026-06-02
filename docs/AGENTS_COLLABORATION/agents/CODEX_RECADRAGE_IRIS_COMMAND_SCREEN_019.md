# Codex — Recadrage Iris Command Screen — Objectif 019

Date : 2026-06-02  
Agent : Codex  
Type : recadrage produit / mission equipe  
Niveau : 2 pour implementation visible  

## Verdict

Le Workbench V1 actuel est insuffisant.

Il a prouve une base technique, mais il ne correspond pas a la vision fondateur.

Ludovic ne demande pas un panneau texte. Il demande un **Command Screen** : un ecran virtuel de travail qui s'allume, affiche des composants visuels et donne l'impression qu'Iris agit vraiment.

## Cible

Iris doit devenir une operatrice visuelle :

- elle comprend la demande ;
- elle ouvre un ecran de travail ;
- elle affiche une premiere structure ;
- elle pose les questions manquantes ;
- elle met a jour le rendu ;
- elle peut transformer le rendu en document numerique apres validation.

## Non negociable

- Un tableau markdown brut n'est pas un tableau livre.
- Un texte qui dit "je vais afficher" n'est pas un affichage.
- Une reponse "je ne peux pas afficher directement" est interdite.
- Ludovic ne doit pas tester tant qu'un rendu visuel reel n'est pas present.
- Aucune action sensible ne part sans validation.

## Livrable V1 attendu

### 1. Command Screen visuel

Un panneau/ecran qui apparait dans Iris Audio, avec :

- header "Iris Command Screen" ;
- statut : analyse, construction, pret, validation requise ;
- zone principale de rendu ;
- zone "Contexte compris" ;
- zone "Infos manquantes" ;
- actions locales : modifier, copier, telecharger, fermer.

### 2. Data Board

Pour une demande de tableau :

- rendu HTML visuel avec colonnes et lignes ;
- style premium, lisible, responsive ;
- badges de statut ;
- pas de markdown brut visible.

### 3. Document Draft

Pour courrier/note :

- rendu document avec titre, objet, paragraphes, blocs ;
- pas seulement du texte coupe dans le transcript.

### 4. Action Board

Pour checklist/plan :

- cartes ou lignes d'action ;
- cases/statuts ;
- priorite et prochaine etape.

### 5. Protocole Iris

Le prompt Iris doit dire :

- "Si l'utilisateur demande un tableau/document/checklist/workspace, tu dois declencher ou accompagner l'affichage du Command Screen."
- "Ne dis jamais que tu ne peux pas afficher si l'interface sait afficher."
- "Si les donnees manquent, affiche une structure provisoire et demande les informations manquantes."

## Repartition des roles

### Codex

- tient le cap produit ;
- met a jour cahier des charges ;
- refuse les livrables partiels ;
- definit les criteres de validation ;
- centralise les avis agents.

### Kimi

Mission :

- proposer la direction UX premium du Command Screen ;
- definir le look du Data Board, Document Draft, Action Board ;
- verifier mobile/desktop ;
- signaler toute impression "chatbot avec panneau".

Livrable :

`docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_COMMAND_SCREEN_019.md`

### DeepSeek

Mission :

- auditer la faisabilite technique du rendu visuel ;
- definir le schema d'intention : demande utilisateur -> type de rendu -> donnees -> affichage ;
- verifier que les actions restent non destructives ;
- recommander l'architecture JS minimale.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_IRIS_COMMAND_SCREEN_019.md`

### Claude

Mission :

- attendre Kimi + DeepSeek ou consigne Codex explicite ;
- implementer un patch visible V1 dans `static/simli.html` ;
- ajouter le rendu HTML visuel pour table/document/checklist ;
- corriger le prompt Iris si necessaire ;
- ne pas deployer avant validation Ludovic.

Livrable :

Commit code + rapport :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_IMPL_IRIS_COMMAND_SCREEN_019.md`

## Critere de validation avant "c'est bon"

Avant de dire a Ludovic de tester, l'equipe doit prouver :

1. capture ou test local du Command Screen ouvert ;
2. tableau visuel non markdown ;
3. document ou checklist visuel ;
4. aucun bouton superpose mobile ;
5. Iris ne dit plus "je ne peux pas afficher directement" ;
6. aucun SMS/email/appel/paiement/reservation declenche.

## Prochaine action

1. Kimi livre UX Command Screen.
2. DeepSeek livre architecture rendu/garde-fous.
3. Codex tranche le scope V1.
4. Claude code seulement le scope tranche.
5. Kimi + DeepSeek auditent.
6. Ludovic teste seulement apres preuve visuelle.
