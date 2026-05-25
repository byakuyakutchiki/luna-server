# Objectif 010 — Historique intelligent des conversations + mémoire Luna

**Date ouverture** : 2026-05-25  
**Décideur** : Ludovic  
**Statut** : ouvert — cadrage multi-agents  
**Priorité** : haute  
**Lead final** : Claude  

## Constat

Le chat Luna peut devenir trop long et difficile à parcourir. Il manque une
organisation par conversations, comme dans ChatGPT :

- bouton trois traits en haut à gauche ;
- liste des conversations ;
- titres automatiques ;
- reprise d'une conversation passée ;
- conservation du contexte utile sans fil infini.

Ludovic rappelle aussi que Luna doit connaître son architecture, son identité, les
objectifs validés et l'état réel de l'application, sans réciter tout cela inutilement.

## But

Créer une expérience de chat organisée :

1. un historique de conversations clair ;
2. des titres automatiques par sujet ;
3. une mémoire utile et sobre ;
4. un chat plus lisible, sans devoir scroller indéfiniment ;
5. une correction UI mobile séparée pour le bouton `Connexion` / `Déconnexion` coupé.

## Fonctionnalités attendues

### Historique conversations

- Menu accessible par les trois traits en haut à gauche.
- Liste des conversations passées.
- Création d'une nouvelle conversation.
- Reprise d'une conversation existante.
- Titre automatique selon le sujet.
- Date de dernière activité.
- Conversation active mise en évidence.

Exemples de titres :

- `Voix Luna et OpenAI Realtime`
- `Documents — porte-documents`
- `Réglages exploitant`
- `Objectif 010 — mémoire Luna`

### Mémoire utile Luna

Luna doit savoir :

- qui elle est ;
- qui est Ludovic ;
- l'architecture générale de Luna ;
- les objectifs validés ;
- les décisions importantes ;
- les limites de sécurité ;
- ce qui a été implémenté ;
- ce qui reste en cours.

Mais Luna ne doit pas faire étalage de sa mémoire. Elle l'utilise seulement si la
question le nécessite.

### Bug UI mobile à traiter séparément

Symptôme :

- sur téléphone, le bouton `Connexion` / `Déconnexion` est coupé ;
- le `n` est mangé par le bord de l'écran.

Règle :

- correction CSS isolée ;
- ne pas mélanger avec l'architecture mémoire/conversations ;
- vérifier responsive petit écran et safe-area mobile.

## Rôles

### Claude — Lead final backend / intégration

Mission :

- auditer le stockage actuel des messages ;
- proposer le modèle backend conversations ;
- définir les endpoints nécessaires ;
- intégrer la mémoire utile sans fuite de données ;
- arbitrer localStorage vs serveur vs Redis/base durable ;
- implémenter uniquement après validation Ludovic.

Livrable :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_AVIS_010.md`

### DeepSeek — Audit technique frontend chat

Mission :

- auditer `static/index.html` et le chat actuel ;
- identifier le menu trois traits existant ;
- proposer la structure conversation côté frontend ;
- vérifier comment séparer les conversations sans casser la mémoire ;
- proposer le format minimal conversation/message/titre ;
- vérifier cache/localStorage/WebView pour éviter anciennes conversations incohérentes.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_010.md`

### Kimi — UX conversationnelle et mémoire non intrusive

Mission :

- proposer les règles de titrage automatique ;
- proposer les textes d'interface ;
- définir comment Luna doit se souvenir sans réciter ;
- distinguer mémoire utilisateur, mémoire projet, mémoire conversation ;
- proposer les formulations quand Luna utilise sa mémoire.

Livrable :

`docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_010.md`

### Cursor — UI mobile / responsive

Mission :

- vérifier le menu conversations sur mobile ;
- corriger le cadrage `Connexion` / `Déconnexion` ;
- vérifier petits écrans < 400px ;
- éviter texte coupé, overflow, boutons mangés ;
- produire une proposition UI sans régression graphique.

Livrable :

`docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_010.md`

### Codex — Coordination et garde-fous

Mission :

- cadrer l'objectif 010 ;
- séparer historique, mémoire, bug UI ;
- empêcher les refactors massifs ;
- vérifier que la mémoire ne stocke pas de secret ;
- préparer la synthèse de validation Ludovic.

Livrable :

`docs/AGENTS_COLLABORATION/agents/CODEX_AVIS_010.md`

## Questions à résoudre

1. Où sont stockés les messages aujourd'hui ?
2. Faut-il stocker les conversations côté serveur, localStorage ou hybride ?
3. Comment générer les titres automatiquement ?
4. Quelle mémoire doit être globale, conversationnelle, ou projet ?
5. Comment Luna sait-elle l'état des objectifs sans tout raconter ?
6. Comment éviter d'exposer des données sensibles dans la mémoire ?
7. Comment corriger le bouton mobile coupé sans casser le layout ?

## Critères de réussite

- [ ] Menu conversations accessible depuis les trois traits.
- [ ] Conversations listées et reprenables.
- [ ] Titres automatiques lisibles.
- [ ] Nouvelle conversation possible.
- [ ] Chat actif allégé.
- [ ] Luna conserve la mémoire utile.
- [ ] Luna n'étale pas inutilement son contexte.
- [ ] Bouton `Connexion` / `Déconnexion` lisible sur mobile.
- [ ] Pas de secret stocké dans la mémoire.
- [ ] Test validé par Ludovic sur téléphone.

## Interdictions

- Pas de suppression des conversations existantes sans sauvegarde.
- Pas de refactor complet du chat sans validation.
- Pas de mémoire contenant clés API, tokens, secrets, audio brut ou données privées inutiles.
- Pas de correction UI mélangée avec changement backend lourd.
- Pas de déploiement sans validation Ludovic.

## Message court

Objectif 010 = donner à Luna une organisation conversationnelle sérieuse :
historique par conversations, titres automatiques, mémoire utile et discrète,
plus correction mobile du bouton `Connexion` / `Déconnexion` coupé.

