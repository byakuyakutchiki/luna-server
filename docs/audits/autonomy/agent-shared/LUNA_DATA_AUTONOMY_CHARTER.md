# LUNA_DATA_AUTONOMY_CHARTER

Date : 2026-07-14
Statut : charte de direction produit pour les agents Kimi / Codex / superviseur Luna.

## Vision de Ludovic

L'objectif n'est pas seulement de corriger des bugs dans une APK.

L'objectif est de construire progressivement une plateforme Luna exploitable commercialement :

- Luna fonctionne completement cote utilisateur final.
- Guardian, Iris, chat, documents, profil, alertes, voix, UX et backend restent coherents.
- Le systeme avance sans regression graphique, architecturale ou fonctionnelle.
- Les preuves/logs permettent de savoir ce qui marche, ce qui ne marche pas, et ce qui reste a faire.
- Le code sensible reste dans une boite noire controlee par Ludovic.
- Un exploitant/commercialisateur externe pourra consommer des API, services ou outputs sous licence, sans posseder toute la boite noire ni le code source complet.
- Les couts API, cloud, serveurs et exploitation doivent pouvoir etre portes par l'exploitant, pas par Ludovic, selon le modele cible.

## Direction produit : Luna Data / AlphaCare / boite noire

Les missions doivent contribuer a :

1. Stabiliser l'application Luna.
2. Stabiliser Guardian et la securite utilisateur.
3. Stabiliser les flux de donnees, preuves, logs et audit.
4. Construire une base exploitable : APIs, deepcode, services, rapports, automatisations.
5. Proteger l'architecture proprietaire et eviter l'exposition inutile du code source.
6. Prouver les progres par tests, captures, logs, rapports et checklist.

## Regle anti-regression

Aucune mission ne doit etre consideree comme reussie si elle :

- degrade l'UI validee ;
- remplace une bonne version par une ancienne ;
- casse Guardian, auth, messages, alertes, voix ou navigation ;
- melange des branches ou des workspaces sales ;
- modifie l'architecture sans validation ;
- contourne les garde-fous ;
- produit un rapport sans preuves.

## Role des agents

### Kimi

Kimi est implementateur / operateur.
Il peut :
- auditer ;
- proposer des patchs ;
- modifier sur branche dediee ;
- executer des tests ;
- produire des rapports.

Il ne doit pas :
- deployer en production ;
- pousser/merge sans validation ;
- installer APK ou supprimer donnees sans validation ;
- changer Guardian/securite sans mission explicite ;
- travailler hors objectif produit.

### Codex

Codex est garde-fou / architecte de coherence.
Il doit :
- lire les rapports ;
- verifier les diffs ;
- bloquer les regressions ;
- verifier l'alignement avec la vision Luna Data ;
- refuser les patchs trop larges ;
- maintenir la checklist et la roadmap.

### Superviseur Luna

Le superviseur est l'orchestrateur.
Il doit :
- creer les missions ;
- suivre budgets et statuts ;
- collecter preuves ;
- produire rapports ;
- mettre a jour la checklist ;
- proposer la prochaine mission logique ;
- bloquer les actions dangereuses.

## Definition d'une mission utile

Une mission utile doit avoir :

- un objectif lie a Luna Data / app Luna / Guardian / exploitation ;
- un budget ;
- un role ;
- des actions autorisees ;
- des actions interdites ;
- un statut final attendu ;
- des preuves obligatoires ;
- un rapport AGENT_SHARED ;
- une conclusion : progres, blocage, regression, ou prochaine etape.

## Ce que Ludovic veut en fin de journee

Quand Ludovic revient, il doit voir :

- ce qui a ete audite ;
- ce qui a ete corrige ;
- ce qui n'a pas ete touche ;
- les preuves ;
- les risques ;
- les patchs proposes ;
- les tests passes/echoues ;
- la prochaine decision a prendre.

Il ne doit pas decouvrir :

- une regression visuelle ;
- un deploy surprise ;
- une APK remplacee sans validation ;
- des donnees effacees ;
- une branche melangee ;
- des missions parties dans une direction differente.

## Prochaine mission prioritaire

Avant de lancer des reparations Guardian/APK :

1. Auditer le hardening superviseur.
2. Nettoyer la strategie Git/workspace.
3. Creer la commande utilisateur `luna-mission`.
4. Ajouter le planner de prochaines missions a partir de cette charte + checklist.
5. Lancer ensuite les audits app Luna/Guardian non destructifs.
