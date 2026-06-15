# LUNA_UI_BUGS.md
## Audit QA — Interface Utilisateur

**Rôle** : Responsable QA / UX / Frontend  
**Date** : 15 juin 2026  
**Méthode** : Playwright E2E, mobile 390×844 + desktop 1440×900  
**URL** : `https://luna-beta-674304336025.europe-west1.run.app`  
**Captures** : 29 screenshots (copies dans `C:\Users\saint\Downloads\BUG_*.png`)

**Question directrice** : *Qu'est-ce qui empêche l'utilisateur de vivre une expérience fluide ?*

---

## BUG-01 — Activités capture la navigation entière

**Priorité : 🔴 CRITIQUE**

### Reproduction

1. Se connecter
2. Cliquer sur l'onglet **Activités**
3. Observer la page qui s'ouvre
4. Essayer de cliquer sur **Chat**, **Services**, n'importe quel onglet

### Comportement observé

L'onglet Activités navigue vers `/salon` — une page **séparée** avec sa propre navigation.  
Contenu : "Activites Niv.3 · 114 etoiles", "Créer une activite", "Aucune activite en cours. Creez-en une !"

Après cet écran, **tous les boutons de la nav principale (Chat, Services, etc.) cessent de répondre**. L'utilisateur est piégé.

La seule sortie visible : un bouton **← Retour** en haut à droite. Aucun utilisateur ne cherche là.

### Capture

`BUG_C3_activites_salon_trap.png`

### Impact utilisateur

L'utilisateur clique sur Activités par curiosité.  
Il arrive sur une page vide ("Aucune activite").  
Il essaie de revenir au Chat — rien ne répond.  
Il ferme l'app.

### Ce qui aggrave le bug

Le texte "114 etoiles" s'affiche (données persistantes réelles). L'utilisateur pense qu'il a fait quelque chose de grave en "accédant" à une zone qu'il ne comprend pas.

---

## BUG-02 — Workspace affiche une session fantôme : "EN SESSION · 4 participants"

**Priorité : 🔴 CRITIQUE**

### Reproduction

1. Se connecter
2. Naviguer vers `/team` (Iris Workspace)
3. Observer l'état AVANT d'entrer

### Comportement observé

La modal d'entrée s'affiche, mais en arrière-plan on distingue :
- Badge **"EN SESSION"** actif
- Compteur **"4 participants"**
- La phase **Brief est déjà cochée** ✓ (session précédente non nettoyée)
- Après avoir entré son prénom : l'app affiche "QA a rejoint la session" et la phase **Collecte** est déjà active (2/5)

L'utilisateur entre dans la session de quelqu'un d'autre — ou dans sa propre session d'il y a plusieurs jours, sans en avoir conscience.

### Captures

`BUG_C6_workspace_initial.png` — état avant entrée (4 participants visible)  
`BUG_C6b_workspace_canvas.png` — canvas : Brief coché, Collecte active, session en cours

### Impact utilisateur

- Il pense que d'autres personnes sont dans "son" espace
- Il voit un Brief qu'il n'a pas créé
- Il ne comprend pas pourquoi il est à l'étape 2/5 sans avoir rien fait
- Doute sur la confidentialité de ses données

---

## BUG-03 — Chips contextuelles basées sur l'heure, pas la conversation

**Priorité : 🟠 HAUTE**

### Reproduction

1. Se connecter → Chat
2. Envoyer : *"Vol Paris Rome jeudi prochain"*
3. Attendre la réponse de Luna
4. Observer les chips de suggestion affichées

### Comportement observé

Quelle que soit la conversation, les chips affichées sont :

```
🌙 Bonne nuit   😌 Relaxation   📝 Gratitude   🎤 Parler
```

Ces chips sont **identiques après "Vol Paris Rome"** et après **"Médecin Dr Martin"**.  
Elles changent selon l'heure du jour, pas selon ce que l'utilisateur vient de dire.

Testé également en début de session (état initial) : chips vides, puis chips nocturnes après premier message.

### Captures

`BUG_chips_apres_vol.png` — chips nuit après demande de vol

### Impact utilisateur

L'utilisateur comprend immédiatement que Luna ne l'écoute pas.  
Il n'a pas besoin de comprendre l'IA pour le ressentir — les boutons proposés n'ont aucun lien avec sa demande.  
C'est le signal le plus lisible qu'il s'agit d'une IA générique, pas d'un compagnon.

---

## BUG-04 — Bouton micro absent de la zone de saisie

**Priorité : 🟠 HAUTE**

### Reproduction

1. Se connecter → Chat
2. Observer la zone de saisie en bas d'écran

### Comportement observé

Zone input visible (mobile) :
```
[ 😊 ]  [ Message pour Luna...              ]  [ ➤ ]  [ + ]
```

**Aucun bouton micro.**  
La voix est accessible uniquement via `#wakewordBtn` — un bouton sans label dans l'en-tête, invisible sur mobile.

Boutons identifiés dans le header :
- `#sidebarToggle` — pas de label
- `#newChatBtn` — pas de label
- `#wakewordBtn` — pas de label ← c'est là que se cache la voix
- `#logoutBtn` — pas de label

### Capture

`BUG_C8b_input_zone.png` — zone input : emoji, texte, send, +. Aucun micro.

### Impact utilisateur

La voix est une promesse centrale du produit.  
Un nouvel utilisateur ne découvrira jamais qu'il peut parler à Luna.  
Il utilisera uniquement le chat texte — et ratera l'expérience différenciante.

---

## BUG-05 — Guardian navigue vers /guardian (page séparée)

**Priorité : 🟡 MOYENNE**

### Reproduction

1. Se connecter
2. Cliquer sur **Guardian**

### Comportement observé

Navigation vers `/guardian` — page séparée avec :
- Carte Leaflet, GPS refusé (headless)
- "← App" en haut à gauche comme seul retour
- 0 events, 0 check-ins, 0 sessions, Niveau Bronze

**Différence avec BUG-01 (Activités)** : le lien "← App" fonctionne. Après retour, le Chat est accessible. La navigation se rétablit.

Ce bug est moins grave qu'Activités mais crée quand même une rupture de contexte.

### Capture

`BUG_C5_guardian_page.png`

### Impact utilisateur

L'utilisateur qui explore Guardian se retrouve "sorti" de l'app principale.  
Il doit chercher le lien "← App" pour revenir.  
Sur mobile, ce lien est en haut à gauche — zone difficile d'accès avec le pouce droit.

---

## BUG-06 — Iris Visio desktop : fond SVG asymétrique

**Priorité : 🟡 MOYENNE**

### Reproduction

1. Ouvrir `/simli` sur **desktop** (1440×900)

### Comportement observé

Le fond SVG nocturne (lune, fenêtres d'immeuble, étoiles) s'affiche uniquement dans le **coin supérieur droit**.  
La carte de démarrage (logo "I", IRIS VISIO, select, bouton) est centrée au milieu gauche.  
L'effet est asymétrique : la scène cinématique est visible mais ne couvre pas l'écran.

### Capture

`BUG_D2_desktop_iris_visio.png`

### Impact utilisateur

Sur mobile : correct (le fond remplit l'écran).  
Sur desktop : l'effet "scène" est cassé. Le fond se comporte comme une image mal positionnée.  
L'intention cinématique est perdue sur grand écran.

---

## BUG-07 — "Appel entrant..." présent dans le DOM de /simli

**Priorité : 🟡 MOYENNE**

### Reproduction

1. Ouvrir `/simli`
2. Inspecter `document.body.innerText`
3. Chercher "Appel entrant"

### Comportement observé

Le texte **"Appel entrant..."** est présent dans le DOM de la page de démarrage Iris Visio, avant tout appel.  
Accompagné de : `"L\nIris\n..."` — résidu d'une ancienne interface de sonnerie téléphonique.

Ces éléments ne sont pas visibles à l'écran (cachés via CSS) mais :
- Ils apparaissent dans les lecteurs d'écran
- Ils peuvent être lus par des outils d'accessibilité
- Ils indiquent un nettoyage incomplet de l'ancienne UI

### Impact utilisateur

Invisible pour l'utilisateur moyen.  
Problématique pour l'accessibilité.  
Signe d'une dette technique visible dans le DOM.

---

## BUG-08 — Workspace : placeholder développeur exposé

**Priorité : 🟡 MOYENNE**

### Reproduction

1. Naviguer vers `/team`
2. Observer le champ "Titre de la session"

### Comportement observé

Le placeholder du champ titre affiche :  
**"Comment rendre Luna rentable ?"**

C'est un placeholder de développement — une vraie question produit utilisée pour tester.  
Elle est affichée à tous les utilisateurs finals.

### Capture

`BUG_C6_workspace_initial.png` — visible dans la modal d'entrée

### Impact utilisateur

L'utilisateur lit "Comment rendre Luna rentable ?" et pense que c'est une question pour lui.  
Il peut entrer cette phrase comme titre de session.  
Déstabilisant, incohérent avec l'expérience premium visée.

---

## BUG-09 — Rapports : 31 entrées sans pagination ni recherche

**Priorité : 🟡 MOYENNE**

### Reproduction

1. Se connecter → Rapports
2. Observer la liste

### Comportement observé

**31 entrées** visibles d'un coup, chacune avec "Lire la suite ▼" et "Supprimer".  
Aucune pagination. Aucun champ de recherche opérationnel.  
Le scroll devient obligatoire pour retrouver un rapport ancien.

### Impact utilisateur

Utilisable aujourd'hui (31 entrées reste gérable).  
Inutilisable dans 3 mois (200+ entrées).  
Il n'y a aucun moyen de trouver rapidement un rapport précis.

---

## BUG-10 — Desktop chat : sidebar suggestions inutiles au premier écran

**Priorité : 🟢 FAIBLE**

### Reproduction

1. Ouvrir Luna en **desktop** (1440×900) → Chat

### Comportement observé

La sidebar gauche affiche une liste de conversations avec des entrées comme :
- "Dimanche ce qu'il vous..."
- "Les actualités d'aujourd'hui..."  
- "La météo d'aujourd'hui..."

Ces entrées semblent être des fragments de conversations précédentes non titrées.  
Aucun titre, aucune date visible. Juste des débuts de phrase tronqués.

### Capture

`BUG_D1_desktop_chat.png`

### Impact utilisateur

L'utilisateur ne peut pas identifier quelle conversation correspond à quoi.  
La sidebar est supposée aider à retrouver un contexte — elle crée de la confusion.

---

## BUG-11 — "Iris Workspace" apparaît dans les Services comme un service

**Priorité : 🟢 FAIBLE**

### Reproduction

1. Se connecter → **Services**
2. Observer le bas du menu, section COMMUNICATION

### Comportement observé

Le menu Services affiche : SMS, Email, Appel — puis **"Iris Workspace"** et **"Alerte urgence"**.

Iris Workspace est un pilier du produit, pas un service de conciergerie.  
Le placer dans Services crée une confusion sur son rôle.

### Capture

`BUG_D4_desktop_services.png`

### Impact utilisateur

L'utilisateur découvre Iris Workspace en cherchant comment envoyer un SMS.  
Ce n'est pas le bon contexte d'introduction.

---

## RÉSUMÉ

| # | Bug | Priorité | Reproduit ? | Capture |
|---|---|---|---|---|
| 01 | Activités → /salon : navigation cassée | 🔴 CRITIQUE | ✅ Oui | C3 |
| 02 | Workspace : "EN SESSION · 4 participants" fantôme | 🔴 CRITIQUE | ✅ Oui | C6, C6b |
| 03 | Chips non-contextuelles (basées heure) | 🟠 HAUTE | ✅ Oui | BUG03b |
| 04 | Bouton micro absent de la zone input | 🟠 HAUTE | ✅ Oui | C8b |
| 05 | Guardian → page séparée (navigation rupture) | 🟡 MOYENNE | ✅ Oui | C5 |
| 06 | Iris Visio desktop : fond SVG asymétrique | 🟡 MOYENNE | ✅ Oui | D2 |
| 07 | "Appel entrant..." dans DOM /simli | 🟡 MOYENNE | ✅ Oui | (DOM) |
| 08 | Workspace placeholder développeur visible | 🟡 MOYENNE | ✅ Oui | C6 |
| 09 | Rapports : 31 entrées sans pagination | 🟡 MOYENNE | ✅ Oui | (count) |
| 10 | Desktop sidebar : conversations sans titre | 🟢 FAIBLE | ✅ Oui | D1 |
| 11 | "Iris Workspace" dans menu Services | 🟢 FAIBLE | ✅ Oui | D4 |

---

## RÉPONSE À LA QUESTION DIRECTRICE

**"Qu'est-ce qui empêche l'utilisateur de vivre une expérience fluide ?"**

**Deux bugs bloquent l'exploration :** Activités et Workspace piègent l'utilisateur dans des états qu'il ne comprend pas et dont il ne sait pas sortir.

**Un bug brise la confiance :** Les chips non-contextuelles prouvent à l'utilisateur que Luna ne l'écoute pas — avant même qu'il ait eu le temps de décider s'il lui fait confiance.

**Un bug cache la fonctionnalité principale :** Il n't y a pas de bouton micro. La voix — le cœur du produit — est invisible.

Ces quatre bugs, corrigés, débloqueraient une navigation fluide du premier au dernier écran.

---

*QA : Claude — aucun code modifié, aucun commit, aucun push.*  
*Captures disponibles : `C:\Users\saint\Downloads\BUG_*.png`*
