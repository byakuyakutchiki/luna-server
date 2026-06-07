# Objectif 035 — Iris Team Workspace immersif

Date : 2026-06-07
Statut : ouvert
Priorite : P0 produit / UX
Lead coordination : Codex
Implementation attendue : Claude

## Decision produit

On ne construit plus une simple visio avec une IA qui parle.

On construit :

```text
une salle de travail immersive
avec une table centrale,
des sieges participants,
un grand tableau virtuel,
des droits admin,
et Iris comme intelligence de synthese appelee au bon moment.
```

Le produit principal n'est pas la voix.

Le produit principal est :

```text
la table + le tableau + les participants + les sources + les livrables
```

Iris intervient quand le workspace est suffisamment cadre.

## Vision visuelle obligatoire

L'interface doit donner envie au premier regard.

Style attendu :

- immersif ;
- high-tech ;
- premium ;
- lisible ;
- dynamique ;
- pas fade ;
- pas administratif ;
- pas dashboard plat ;
- pas empilement de boutons sans hierarchy ;
- pas “chatbot avec panneau autour”.

Reference mentale :

```text
table ronde futuriste
participants assis autour
grand tableau collaboratif au centre
Iris comme presence intelligente / synthese
```

Le design doit donner l'impression :

```text
je rentre dans une salle de commandement d'equipe
```

## Structure d'ecran cible

### 1. Zone centrale — Tableau immersif

Le tableau est l'objet principal.

Il peut contenir :

- post-it ;
- idees ;
- cartes mentales ;
- documents ;
- graphiques ;
- tableaux ;
- schemas ;
- timeline ;
- roadmap ;
- votes ;
- decisions ;
- actions ;
- zones dessinables ;
- liens entre idees ;
- preuves / sources.

Le tableau doit etre interactif, meme en V1 simple.

V1 minimum :

- afficher des cartes d'idees ;
- afficher un graphe ou des relations simples ;
- afficher un document ou bloc source ;
- afficher un panneau synthese ;
- permettre selection / ajout / suppression locale non sensible.

### 2. Table / sieges participants

Autour du tableau :

- sieges visibles ;
- chaque siege represente une personne active ;
- avatar ou video miniature ;
- nom ;
- role ;
- statut ;
- droits.

Etats a prevoir :

```text
parle
ecoute
edite
main levee
camera on/off
micro on/off
mute par admin
absent
invite
spectateur
banni
```

### 3. Spectateurs

Toutes les personnes ne doivent pas etre autour de la table.

Il faut distinguer :

```text
participants actifs = assis autour de la table
spectateurs = voient/ecoutent mais ne modifient rien
```

Un spectateur peut :

- demander la parole ;
- etre promu participant ;
- etre mute ;
- etre retire ;
- etre banni.

### 4. Admin / owner

L'admin controle la salle.

Droits admin :

- accepter/refuser entree ;
- assigner un siege ;
- changer le role ;
- donner la parole ;
- retirer la parole ;
- mute micro ;
- reactiver micro ;
- couper camera ;
- reactiver camera ;
- retirer du tableau ;
- expulser ;
- bannir ;
- valider les actions sensibles ;
- lancer “Avis Iris”.

Toute action admin doit rester locale/UI en V1 si elle touche des personnes reelles.
Aucune action externe sensible sans validation explicite.

### 5. Mission Brief

Le workspace doit avoir un contexte impose par l'admin.

Champs :

- titre ;
- domaine ;
- objectif ;
- contexte ;
- sources ;
- livrables attendus ;
- contraintes ;
- recherche externe autorisee oui/non.

Tant que le brief est incomplet, le bouton Iris doit etre limite ou grise.

Message attendu :

```text
Ajoutez un brief, une source ou un mode de travail avant de demander l'avis Iris.
```

### 6. Sources

Sources possibles :

- documents PDF/DOCX/TXT/CSV/XLSX ;
- images ;
- captures ;
- liens web ;
- liens YouTube ;
- notes ;
- fichiers de participant ;
- tableaux de chiffres ;
- elements ajoutes au tableau.

Chaque source doit garder :

```text
qui l'a ajoutee
quand
type
statut
droit d'acces
resume
```

### 7. Avis Iris

Iris ne parle pas en permanence.

Elle intervient quand :

- admin clique “Avis Iris” ;
- admin clique “Synthese Iris” ;
- equipe demande une analyse sur les elements presents ;
- une contradiction importante est detectee ;
- une synthese de fin est demandee.

Pendant “Avis Iris” :

- les autres micros peuvent etre reduits/mutes ;
- le tableau se verrouille temporairement ;
- Iris parle a partir des sources et du brief ;
- Iris cite les elements visibles ;
- Iris ne sort pas du contexte ;
- le panneau montre les preuves : qui a donne quoi, quelles sources, quelles decisions.

## Architecture fonctionnelle

```text
Participants construisent le workspace.
IQ / serveur structure le contenu.
Iris explique et synthetise.
Admin controle la session.
```

OpenAI vocal ne doit pas piloter le workspace.

OpenAI vocal sert a :

- oraliser une synthese ;
- repondre dans le contexte ;
- expliquer une decision ;
- commenter un rendu deja construit.

Le serveur / UI sert a :

- gerer la salle ;
- gerer les roles ;
- gerer les sources ;
- gerer le tableau ;
- produire les rendus ;
- lancer les actions.

## V1 demandee a Claude

Claude doit coder une premiere V1 visuelle, sans action sensible :

1. Une nouvelle vue ou un mode dans `simli.html` : Team Workspace.
2. Un canvas/tableau central immersif.
3. Une disposition de sieges participants autour.
4. Un rail spectateurs.
5. Un panneau admin minimal.
6. Un bouton “Avis Iris” grise si brief/sources insuffisants.
7. Un affichage Mission Brief.
8. Une zone sources.
9. Une mind map ou relation simple entre idees.
10. Des logs F12 clairs :

```text
team_workspace_loaded
seat_assigned
spectator_joined
brief_ready true/false
iris_opinion_locked
iris_opinion_requested
```

## Interdictions V1

- Pas de SMS reel.
- Pas d'email reel.
- Pas d'appel reel.
- Pas de paiement.
- Pas de reservation.
- Pas de suppression irreversible.
- Pas de secret frontend.
- Pas d'IA qui improvise la structure.
- Pas de design fade.
- Pas de gros pavé de texte comme rendu principal.

## Tests V1

### TC-035-01 — Ouverture salle

La page affiche :

- tableau central ;
- sieges ;
- spectateurs ;
- admin panel ;
- brief.

### TC-035-02 — Brief incomplet

Bouton “Avis Iris” grise.

### TC-035-03 — Brief + source

Bouton “Avis Iris” actif.

### TC-035-04 — Spectateur

Un spectateur est visible hors table et peut demander la parole.

### TC-035-05 — Admin

Admin peut visuellement :

- promouvoir ;
- muter ;
- retirer ;
- bannir ;

sans action externe reelle.

### TC-035-06 — Tableau

Le tableau affiche au moins :

- 3 cartes idees ;
- 1 source ;
- 1 relation/mind map ;
- 1 synthese provisoire.

### TC-035-07 — Avis Iris

Quand le brief est pret :

- clic Avis Iris ;
- mode intervention Iris ;
- micros visuellement en ecoute ;
- tableau verrouille temporairement ;
- panneau affiche la base de synthese.

## Mission Kimi

Kimi doit auditer l'UX :

- est-ce que c'est premium ?
- est-ce que la table est comprehensible ?
- est-ce que le tableau est l'objet principal ?
- est-ce que les roles sont lisibles ?
- est-ce que l'admin comprend qui controle quoi ?
- est-ce que le bouton Iris est correctement grise/active ?
- est-ce que l'ensemble donne envie ?

## Mission DeepSeek

DeepSeek doit auditer :

- roles/droits ;
- risques admin ;
- risques RGPD ;
- spectateurs vs participants ;
- actions sensibles ;
- coherence avec Mission Brief ;
- chemins ou OpenAI pourrait encore contourner le workspace.

## Mission Codex

Codex coordonne :

- vision produit ;
- validation des target cells ;
- non regression ;
- garde-fous ;
- messages GitHub.

