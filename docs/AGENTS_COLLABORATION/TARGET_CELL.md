# Cellule Target — Objectif / Fonctionnalite / Preuve

Date : 2026-06-02  
Statut : regle obligatoire de livraison  
Responsable : Codex coordonne, chaque agent applique

---

## 1. Regle absolue

Avant de livrer une fonctionnalite, l'equipe doit repondre a cette question :

> Est-ce que la fonctionnalite atteint reellement sa target utilisateur ?

Si la target n'est pas definie, on ne code pas encore.

Si la target est definie mais pas prouvee, on ne dit pas "c'est bon".

Si le code existe mais que le rendu reel ou l'action finale ne marche pas, la fonctionnalite n'est pas livree.

---

## 2. Definition d'une target

Une target est le resultat concret attendu par l'utilisateur.

Exemples :

| Fonctionnalite | Mauvaise definition | Bonne target |
|---|---|---|
| Recherche web Iris | Iris peut parler de recherche | Iris lance une recherche externe, affiche sources + synthese, puis propose action suivante |
| Tableau Iris | Iris affiche un tableau | Iris projette un vrai tableau visuel exploitable, modifiable, copiable/telechargeable |
| Appel Twilio | Iris sait appeler | Iris prepare l'appel, affiche validation owner, puis appelle seulement apres confirmation |
| Documents | Iris parle des documents | Iris liste/retrouve/analyse les documents du porte-documents avec consentement |
| Teams | Iris invite quelqu'un | Iris cree une session, affiche participants, roles, mute/kick, validation actions |

---

## 3. Format obligatoire avant livraison

Chaque nouvelle fonctionnalite ou bouton doit avoir cette fiche :

```text
Objectif :
Fonctionnalite :
Utilisateur cible :
Target exacte :
Capacites attendues :
Bouton / commande / entree :
Backend attendu :
Frontend attendu :
Donnees necessaires :
Garde-fous :
Preuve attendue :
Preuve obtenue :
Statut : non code / code non prouve / partiel / atteint / regression
Decision Ludovic requise : oui/non
```

---

## 4. Matrice de validation

Une fonctionnalite est validee seulement si toutes les colonnes sont OK :

| Colonne | Question | Statut attendu |
|---|---|---|
| Objectif | Pourquoi existe-t-elle ? | clair |
| Target | Quel resultat utilisateur final ? | mesurable |
| Capacite | Que doit-elle savoir faire ? | listee |
| Chemin | Comment l'utilisateur la declenche ? | bouton/voix/texte |
| Backend | Quel endpoint/tool execute ? | identifie |
| Frontend | Quel rendu affiche le resultat ? | identifie |
| Garde-fou | Que bloque-t-on ? | actif |
| Preuve | Quelle preuve terrain ? | capture/log/test |
| Verdict | Atteint ou non ? | tranche |

---

## 5. Statuts autorises

### non code

La target est claire mais rien n'est implemente.

### code non prouve

Le code existe, mais aucun test reel ne prouve que la target est atteinte.

### partiel

Une partie fonctionne, mais la target complete n'est pas atteinte.

### atteint

La target est atteinte avec preuve terrain.

### regression

La fonctionnalite existait ou etait promise, mais le rendu ou l'action s'est degrade.

---

## 6. Roles agents dans la cellule

### Codex

Definit la target, tient la matrice, refuse les validations partielles.

### Kimi

Verifie le rendu reel, la qualite UX/UI, la coherence premium et les regressions visuelles.

### DeepSeek

Verifie le chemin technique : handler, endpoint, tool, erreur, cout, risque, garde-fou.

### Claude

Implemente seulement apres target claire. Ne deploye pas si la preuve n'est pas prete ou si Ludovic doit valider.

---

## 7. Regle de livraison

Un message "c'est fait" doit toujours contenir :

1. la target ;
2. le chemin utilisateur ;
3. ce qui marche ;
4. ce qui ne marche pas encore ;
5. la preuve ;
6. le prochain agent concerne.

Sans ces 6 points, le message est incomplet.

