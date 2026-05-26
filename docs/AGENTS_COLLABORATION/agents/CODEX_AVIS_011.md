# Codex - Avis Objectif 011

**Date** : 2026-05-26  
**Objectif** : Audit complet onglet Services / Conciergerie  
**Statut** : cadrage initial publie  

## Avis court

L'onglet Services est un chantier transversal. Il ne faut pas commencer par du
code. Il faut d'abord auditer la chaine complete :

```text
carte APK -> handler JavaScript -> /api/concierge/action -> tool Python -> service externe -> rendu utilisateur -> journal/diagnostic
```

Le risque principal n'est pas seulement qu'un bouton ne marche pas. Le risque est
qu'un bouton donne l'impression que Luna a agi alors que l'action a echoue, ou
qu'une action sensible parte sans garde-fou suffisant.

## Inventaire initial observe

Dans `static/index.html`, l'onglet visible **Services** correspond au panneau
`tab-conciergerie`.

Groupes reperes :

- Recherche & Voyage : vols, hotels, restaurants, recherche web, autour de moi.
- Infos en temps reel : meteo, actualites.
- Communication : SMS, email, appel, visio, alerte urgence.
- Organisation : rappel, note, document, contacts, formulaires.
- Mon Monde Luna : stats, missions, badges, amis en ligne.

Backend central repere :

```text
POST /api/concierge/action
```

## Garde-fous Codex

1. Ne pas deployer pendant l'audit.
2. Ne pas tester d'action reelle sensible sans validation Ludovic.
3. Ne pas melanger bug UI, API externe, paiement, appel, et gamification dans une seule correction.
4. Chaque agent doit produire une table claire : service / etat / risque / correction minimale.
5. Claude doit coder seulement apres synthese et validation.

## Priorite de test proposee

Tester d'abord les actions non destructives :

1. meteo ;
2. actualites ;
3. recherche web ;
4. autour de moi ;
5. stats ;
6. missions ;
7. badges ;
8. amis en ligne.

Puis isoler les actions sensibles :

- SMS ;
- email ;
- appel ;
- visio ;
- alerte urgence ;
- reservation ;
- paiement.

## Decision recommandee

Ouvrir l'objectif 011 en mode audit uniquement.

Claude ne doit pas coder avant d'avoir :

- avis DeepSeek technique ;
- avis Kimi UX/promesse ;
- avis Cursor mobile ;
- validation Ludovic sur le premier lot a corriger.
