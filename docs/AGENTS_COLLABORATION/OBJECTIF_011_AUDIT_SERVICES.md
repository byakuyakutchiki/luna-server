# Objectif 011 - Audit complet onglet Services / Conciergerie

**Date ouverture** : 2026-05-26  
**Decideur** : Ludovic  
**Statut** : ouvert - audit multi-agents uniquement  
**Priorite** : tres haute  
**Lead final** : Claude  

## Vision Ludovic

L'onglet **Services** est un gros chantier. Il contient beaucoup de fonctions qui
doivent devenir fiables, comprehensibles et testables une par une.

Avant toute correction, l'equipe doit auditer l'existant, comprendre le but reel
de chaque section, identifier ce qui marche, ce qui est fragile, ce qui est
simule, ce qui appelle une API externe, et ce qui peut declencher une action
reelle.

## Perimetre observe dans `static/index.html`

L'onglet visible s'appelle `Services`, mais le code utilise `conciergerie`.

Sections et cartes presentes :

| Section | Cartes | Actions techniques probables |
|---|---|---|
| Recherche & Voyage | Vols, Hotels, Restaurants, Recherche web, Autour de moi | `search_flights`, `search_hotels`, `book_restaurant`, `search_web`, `search_places` |
| Infos en temps reel | Meteo, Actualites | `weather`, `news` |
| Communication | SMS, Email, Appeler, Visio Luna, Alerte urgence | `send_sms`, `send_email`, `call_contact`, `invite_visio`, `alert_contacts` |
| Organisation | Rappel, Note, Document, Mes contacts, Formulaires | `create_instruction`, note, `generate_document`, `get_contacts`, redirection `/formulaires` |
| Mon Monde Luna | Stats, Missions, Badges, Amis en ligne | `get_player_stats`, `get_active_missions`, `get_badges`, `get_friends_online` |

Endpoint central repere :

```text
POST /api/concierge/action
```

## Probleme

Un bouton peut sembler disponible dans l'APK alors que :

- l'API externe n'est pas configuree ;
- l'action echoue sans explication claire ;
- le resultat s'affiche mal sur mobile ;
- l'action reelle est trop sensible pour etre declenchee sans confirmation ;
- le cockpit fondateur ne voit pas l'echec ;
- l'utilisateur ne comprend pas si Luna a vraiment agi ou seulement prepare une action.

## But de l'objectif 011

Produire une cartographie fiable de l'onglet Services avant de coder.

Pour chaque carte/service, l'equipe doit dire :

1. quel est le but utilisateur ;
2. quel fichier/fonction/endpoint est utilise ;
3. quelles cles/API externes sont necessaires ;
4. ce que l'utilisateur voit si tout marche ;
5. ce que l'utilisateur voit si ca echoue ;
6. si l'action est sensible et demande confirmation ;
7. si l'echec remonte au cerveau APK / cockpit fondateur ;
8. quelle correction minimale serait necessaire.

## Regle absolue

**Audit avant action.**

Personne ne doit refondre l'onglet Services, declencher des actions reelles, ni
deployer en production avant validation de Ludovic.

Clarification importante : Ludovic teste actuellement en tant que fondateur, sans
entreprise exploitante et sans carte bancaire entreprise. Les tests doivent donc
prouver que le parcours sera pret pour un exploitant futur, sans depense
personnelle fondateur et sans action irreversible pendant l'audit.

Voir aussi :

```text
docs/AGENTS_COLLABORATION/NOTE_011_MODE_FONDATEUR_EXPLOITANT.md
```

Actions sensibles interdites en test sans confirmation explicite :

- SMS reel ;
- email reel ;
- appel telephone reel ;
- alerte urgence ;
- paiement ;
- reservation ;
- invitation visio envoyee a un tiers.

## Missions par agent

### Claude - Lead technique final

Claude ne doit pas coder tout de suite. Il doit d'abord produire la synthese
technique finale apres lecture des autres agents.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/CLAUDE_AVIS_011.md
```

Contenu attendu :

- table complete carte -> handler frontend -> action backend -> tool ;
- etat des dependances externes ;
- liste des actions dangereuses a proteger ;
- proposition de plan d'implementation en phases ;
- decision a demander a Ludovic avant code.

### DeepSeek - Audit technique frontend/backend

Mission : remonter la realite du code.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_011.md
```

Questions obligatoires :

- chaque carte `conc-card` a-t-elle un handler ?
- chaque handler appelle-t-il `/api/concierge/action` avec les bons parametres ?
- chaque action existe-t-elle dans `luna_web.py` ?
- quels retours JSON sont attendus par les renderers ?
- quels cas peuvent casser l'interface mobile ?
- quelles corrections minimales proposer sans refonte ?

Interdit : coder directement sans validation.

### Kimi - Audit UX, promesse utilisateur, textes humains

Mission : dire ce que chaque service doit promettre a l'utilisateur, et ce qu'il
ne doit surtout pas promettre.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_011.md
```

Contenu attendu :

- but humain de chaque section ;
- textes de reussite/echec lisibles ;
- distinction "Luna a trouve", "Luna a prepare", "Luna a vraiment envoye/appelle" ;
- avertissements pour actions sensibles ;
- priorites UX pour Ludovic.

### Cursor - Audit UI mobile de l'onglet Services

Mission : verifier la lisibilite et l'ergonomie mobile.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_011.md
```

Contenu attendu :

- grille Services lisible sur telephone ;
- cartes trop petites ou textes coupes ;
- modales utilisables avec clavier mobile ;
- resultats inline lisibles ;
- bouton Retour visible ;
- pas de scroll horizontal ;
- proposition CSS minimale si necessaire.

### Codex - Coordination et garde-fous

Mission : cadrer l'objectif, proteger la validation Ludovic, et empecher les
melanges entre audit, code et deploiement.

Livrable attendu :

```text
docs/AGENTS_COLLABORATION/agents/CODEX_AVIS_011.md
```

## Phasage recommande

### Phase 1 - Inventaire

Lister toutes les cartes, handlers, endpoints et outils.

### Phase 2 - Classification risque

Classer les services :

- lecture seule ;
- recherche externe ;
- action preparatoire ;
- action reelle sensible ;
- redirection ;
- gamification/profil.

### Phase 3 - Tests non destructifs

Tester seulement les actions sans effet reel :

- meteo ;
- actualites ;
- recherche web ;
- recherche lieu ;
- stats ;
- missions ;
- badges ;
- amis en ligne.

### Phase 4 - Actions sensibles

Pour SMS, email, appel, urgence, paiement, reservation :

- verifier les garde-fous ;
- exiger confirmation utilisateur ;
- verifier journalisation ;
- verifier remontage cockpit/cerveau.

### Phase 5 - Decision Ludovic

Claude propose un plan de correction par priorite. Ludovic valide avant code.

## Criteres d'acceptation

- [ ] Tous les services sont inventories.
- [ ] Chaque carte a un statut : OK / fragile / incomplet / dangereux / inconnu.
- [ ] Les dependances externes sont identifiees.
- [ ] Les actions sensibles sont separees des tests simples.
- [ ] Les messages utilisateur sont comprehensibles.
- [ ] L'APK remonte les erreurs utiles.
- [ ] Ludovic sait quoi tester sur son telephone.
- [ ] Les services payants/sensibles sont testables en mode audit/sandbox.
- [ ] Le futur mode exploitant est separe du mode fondateur.
- [ ] Aucune correction majeure n'a ete faite sans validation.
