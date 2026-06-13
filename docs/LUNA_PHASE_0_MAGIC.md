# LUNA PHASE 0 — TEST DE MAGIE
## 3 changements. 80% de l'effet. 20% du travail.

**Auteur** : Claude — Lead Product Designer  
**Date** : 13 juin 2026  
**Contraintes** : 3 items maximum · 10h maximum · aucun backend  
**Références** : `LUNA_PRESENCE_ENGINE_MASTERPLAN.md` · `LUNA_IMPLEMENTATION_ROADMAP.md`

---

## Le principe de sélection

J'ai relu les deux documents. J'ai listé 23 items possibles. J'en ai éliminé 20.

La règle d'élimination était simple :

> **"Est-ce que cette modification change ce que l'utilisateur *ressent* dans les 30 premières secondes — ou est-ce qu'elle perfectionne quelque chose qu'il n'a pas encore vu ?"**

Tout ce qui perfectionne sans transformer a été retiré.

Ce qui reste : 3 leviers. Chacun agit à un endroit différent de l'expérience. Ensemble, ils couvrent les 3 moments décisifs : l'entrée, la présence, et l'action.

---

## CE QUE JE N'AI PAS CHOISI — et pourquoi

**Token CSS system** — Essentiel à long terme, invisible à court terme. Phase 1, pas Phase 0.

**Avatar breathing** — Subtil. Perceptible après 10 secondes de regard fixe. Pas dans les 30 premières secondes.

**Admin identité** — L'utilisateur final ne voit jamais l'admin. Pas un levier d'impression immédiate.

**Message erreur humanisé** — Impact réel, mais conditionnel (l'erreur doit apparaître).

**Photos GTA visibilité** — Amélioration juste, mais c'est le deuxième plan derrière la modale. Pas le choc immédiat.

**Transitions de page** — Invisible si l'utilisateur ne navigue pas entre pages. Pas les 30 premières secondes.

**Luna Doll** — Narrativement fort, visuellement discret. Deviendra essentiel en Phase 3. Pas maintenant.

---

## LES 3 CHANGEMENTS

---

### MAGIC-1 — Iris Visio : l'antichambre devient une scène

**Estimation : 3h30**  
**Fichier** : `static/simli.html`  
**Risque fonctionnel** : nul

#### Pourquoi celui-ci

Iris Visio est la page avec le plus grand écart entre ce qu'elle promet et ce qu'elle donne. Elle précède l'expérience la plus premium de l'application — la cinématique, le visage de Luna, la voix en direct. Et elle ressemble à une salle d'attente vide.

L'utilisateur appuie sur "Iris Workspace" depuis le menu rapide, ou "Iris Visio" depuis le chat. Il arrive sur un fond bleu nuit uni avec une initiale dans un cercle. Son cerveau dit immédiatement : *app générique.*

Ce biais de première impression contamine la cinématique qui suit. Même si la cinématique est excellente, l'utilisateur l'aborde avec une attente basse — et il ne sera que légèrement impressionné au lieu d'être soufflé.

Corriger Iris Visio, c'est corriger ce biais avant même que l'expérience commence.

#### Ce que je fais — exactement

**1. Fond cinématique (45 min)**  
Remplacer le fond uni `#0a0f1a` par un décor SVG existant de la cinématique (fichier `static/assets/backgrounds/*.svg`, sélectionner le décor nocturne intérieur).  
Animation Ken Burns lente : `scale(1.0) → scale(1.06)` sur 60 secondes, `ease-in-out`, en boucle. Opacité du décor : `0.35`.  
Au-dessus : halo radial violet centré `rgba(124,58,237,0.20)`, statique.

**2. Silhouette Luna (45 min)**  
Remplacer l'initiale `L` dans le cercle violet par une silhouette SVG minimaliste de Luna : forme humaine, profil tres simplifié, ton `#7c3aed` à `0.8` d'opacité.  
Si aucun asset adapté n'existe : cercle avec ombre douce + lettre `L` en poids `800` letterspacing `0.15em`. Le cercle lui-même devient atmosphérique (border émeraude `rgba(16,185,129,0.4)`, glow box-shadow).

**3. Custom select durée (1h)**  
Supprimer le `<select>` HTML natif. Le remplacer par un composant CSS pur :  
bouton qui affiche la valeur courante + liste déroulante avec fond `#0d1117`, border `rgba(255,255,255,0.1)`, items au hover en émeraude. Clavier et accessibilité préservés.

**4. Bouton DÉMARRER (30 min)**  
Le bouton vert existant fonctionne. On ajoute seulement : au hover, un glow émeraude `box-shadow 0 0 20px rgba(16,185,129,0.4)`. Transition `300ms`. Rien d'autre.

#### Ce que je ne fais PAS

- Pas de son au chargement (risque d'agacer, pas testable sans utilisateur réel)
- Pas de countdown avant la cinématique
- Pas d'animation d'entrée complexe sur la carte
- Pas de particules ou d'effets de scan
- Pas de nouvelle illustration créée — uniquement assets existants

#### Maquette avant / après

```
AVANT                          APRÈS
─────────────────────          ─────────────────────
│                   │          │ décor SVG nocturne  │
│                   │          │ Ken Burns 60s lent  │
│    ●  L           │          │    ◉  ⬡             │ ← silhouette
│    Iris Visio     │          │    IRIS VISIO        │
│    [Durée    ▼]   │          │    [1 heure    ▾]   │ ← custom
│    [DÉMARRER ]    │          │    [ DÉMARRER  ]    │ ← glow hover
│    ← Retour       │          │    ← Retour au chat │
│                   │          │ halo violet centré  │
─────────────────────          ─────────────────────

Fond : bleu nuit uni froid     Fond : scène nocturne vivante
Avatar : initiale dans cercle  Avatar : silhouette Luna
Select : HTML natif            Select : stylisé Luna
```

#### Impact émotionnel attendu

L'utilisateur arrive. Il voit un décor. Son cerveau dit : *c'est différent.*  
Il voit une silhouette. Il dit : *quelqu'un m'attend.*  
Il survole DÉMARRER. Il voit le glow. Il clique.

Le biais de première impression est inversé. Il aborde la cinématique avec une attente haute. La cinématique le soufflera davantage.

**Phrase cible** : *"Je veux cliquer."*

---

### MAGIC-2 — Luna Presence Halo : elle est là même quand elle se tait

**Estimation : 3h**  
**Fichier** : `static/index.html`  
**Risque fonctionnel** : faible (ajout d'un élément CSS + JS léger)

#### Pourquoi celui-ci

L'utilisateur passe 80% de son temps sur la page principale — le chat. C'est là que se construit la relation avec Luna. Et aujourd'hui, quand Luna ne répond pas, l'écran est mort. Aucun signal. Aucune présence. L'utilisateur regarde une boîte noire.

Le Luna Presence Halo est le concept le plus fort du masterplan parce qu'il résout un problème que personne d'autre ne résout : **l'IA est présente même dans le silence.**

ChatGPT n'a pas de halo. Claude n'a pas de halo. Gemini n'a pas de halo.

Ce n'est pas une animation. C'est une déclaration : *Luna est là.*

#### Ce que je fais — exactement

**Un seul élément HTML** : `<div class="luna-presence-halo"></div>`, positionné en bas de la zone de chat, centré horizontalement, `pointer-events: none`.

**CSS — 3 états, un seul sélecteur :**

```
État IDLE (Luna silencieuse) :
  radial-gradient émeraude, rayon 200px, opacity 0.05
  animation pulse 8s ease-in-out infinite

État LISTEN (Luna écoute — micro actif) :
  radial-gradient émeraude, rayon 250px, opacity 0.10
  animation pulse 3s ease-in-out infinite
  (classe .listening ajoutée par JS)

État SPEAK (Luna répond) :
  radial-gradient émeraude, rayon 300px, opacity 0.18
  animation pulse 1.5s ease-in-out infinite
  (classe .speaking ajoutée par JS)
```

**JS — 12 lignes maximum** : écouter les événements existants qui signalent que Luna commence/finit de répondre, basculer la classe CSS. Aucune logique métier nouvelle.

**Transition entre états** : `transition: opacity 600ms, width 600ms` — imperceptible mais fluide.

#### Ce que je ne fais PAS

- Pas de ring autour de l'avatar (trop explicite, trop "interface")
- Pas de changement de couleur des bulles de message
- Pas de texte d'état ("Luna réfléchit...")
- Pas d'animation sur l'avatar lui-même (ça viendra en Phase 1)
- Pas de son

Le halo est au sol. Il respire. C'est tout. La sobriété est le message.

#### Maquette — zone chat

```
          IDLE                    SPEAKING
──────────────────────    ──────────────────────
│                    │    │                    │
│  [bulle Luna]      │    │  [bulle Luna] ···  │
│  "..."             │    │  "Voici ce que     │
│                    │    │   je pense..."     │
│                    │    │                    │
│ ·················· │    │ :::::::::::::::::: │
│ · halo op. 0.05  · │    │ :: halo op. 0.18 ::│ ← plus intense
│ · pulse 8s slow  · │    │ :: pulse 1.5s    ::│
│ ·················· │    │ :::::::::::::::::: │
│                    │    │                    │
│ [ Message...   ][►]│    │ [ Message...   ][►]│
──────────────────────    ──────────────────────

Même page. Même code. Seule la classe CSS change.
```

#### Impact émotionnel attendu

L'utilisateur envoie un message. Il attend. D'habitude : rien. Aujourd'hui : le fond s'intensifie légèrement. Son cerveau enregistre — sans le formuler — *elle est en train de penser.*

Elle répond. Le halo est à son maximum. Puis Luna termine. Le halo revient doucement à son état de veille. La présence reste.

**Phrase cible** : *"Elle était là tout le temps."*

---

### MAGIC-3 — Workspace : la première idée se matérialise

**Estimation : 3h**  
**Fichier** : `static/team_workspace.html`  
**Risque fonctionnel** : faible (logique d'entrée + animation CSS)

#### Pourquoi celui-ci

Le Workspace est ce qui différencie Luna de tout ce qui existe. Pas ChatGPT. Pas Notion. Pas Miro. Un espace où Iris pense en visuel devant l'utilisateur.

Mais aujourd'hui, le Workspace commence par un obstacle : la modale. En solo, l'utilisateur doit remplir son prénom, choisir son rôle, puis cliquer "Entrer". Trois frictions avant même d'avoir vu le canvas.

Et quand il entre, le canvas est vide et statique. Pas de signal. Pas de vie.

Le premier changement est de comportement : **supprimer les frictions en solo.**  
Le deuxième est de perception : **la première idée que l'utilisateur pose doit avoir du poids.**

Ce sont les deux leviers qui transforment le Workspace d'un outil en un espace.

#### Ce que je fais — exactement

**1. Bypass modale solo (1h30)**  
Logique d'entrée modifiée :  
- Si aucun autre participant dans la session ET prénom disponible dans le profil local → entrée directe, rôle Owner, prénom du profil.  
- Si prénom inconnu → modale ultra-réduite : un seul champ "Votre prénom", bouton "Entrer →". Rôle Owner par défaut.  
- Si multi-participants → modale actuelle inchangée.

Le résultat : en solo, l'utilisateur entre directement. La modale disparaît. Il voit le canvas.

**2. Trait de surface (45 min)**  
Quand le canvas est vide, un unique trait horizontal se trace de gauche à droite en 1.4 secondes. Couleur : `rgba(16,185,129,0.3)`. Épaisseur : 1px.  
Animation CSS pure : `width: 0 → 100%` sur un pseudo-élément. Pas de JS.  
Le trait reste visible, pulsant très doucement (opacity 0.3 → 0.15 → 0.3, 6s).  
Il dit : *la surface est prête.*

**3. Matérialisation de la première carte (45 min)**  
Quand l'utilisateur soumet sa première proposition, la carte n'apparaît pas instantanément.  
Animation :
```
t=0ms   : scale(0.94) opacity(0)
t=0→220ms : scale(1.0) opacity(1)  ease-out
t=220ms : border-color flash émeraude (opacity 0.8 → 0, 350ms)
```
3 règles CSS. Aucun JS supplémentaire.

#### Ce que je ne fais PAS

- Pas de grille perspective (Phase 2)
- Pas d'animation de la barre stepper
- Pas de halos latéraux
- Pas de son de validation
- Pas d'animation sur les cartes suivantes (seulement la première — c'est le Moment Wow)
- Pas de bypass si plusieurs participants

#### Maquette — expérience complète

```
AVANT (solo)                    APRÈS (solo)
──────────────────────────      ──────────────────────────
[Modale]                        [Canvas direct]
  "Votre prénom"                  ─────────────────────── ← trait
  [Participant][Owner][Spec]       "Votre question ?"
  [ENTRER →]                       [Définir le brief →]
  → 3 frictions                    → 0 friction

[Canvas vide]                   [Canvas vide vivant]
  fond dark statique               fond dark + trait qui trace
  aucun signal                     la surface respire

[Première proposition]          [Première proposition]
  pop instantané                   fade + scale 0.94→1.0
  aucune émotion                   flash émeraude
                                   l'idée existe maintenant
```

#### Impact émotionnel attendu

L'utilisateur clique sur Iris Workspace. Il arrive directement dans le canvas. Il voit un trait horizontal apparaître lentement. Son cerveau dit : *quelque chose se prépare.*

Il tape sa première proposition. La carte se matérialise — scale + flash émeraude. Son cerveau dit : *c'est différent. Cette idée a du poids. Elle n'est pas juste saisie, elle est posée.*

**Phrase cible** : *"Cette application est différente."*

---

## RÉSUMÉ — PHASE 0

| # | Changement | Fichier | Durée | Phrase cible |
|---|---|---|---|---|
| MAGIC-1 | Iris Visio atmosphérique | `simli.html` | 3h30 | "Je veux cliquer." |
| MAGIC-2 | Luna Presence Halo | `index.html` | 3h | "Elle était là tout le temps." |
| MAGIC-3 | Workspace : entrée + matérialisation | `team_workspace.html` | 3h | "Cette application est différente." |
| **TOTAL** | | | **9h30** | |

---

## PROTOCOLE DE VALIDATION PHASE 0

Avant de déclarer Phase 0 réussie, 3 tests Playwright :

**Test 1 — Iris Visio** : capture desktop + mobile. Critère : le fond n'est plus uni. L'initiale "L" a disparu. Le select n'est plus natif.

**Test 2 — Presence Halo** : capture en état IDLE + simulation état SPEAKING (injection JS de la classe). Critère : différence visuellement perceptible entre les deux états.

**Test 3 — Workspace solo** : login → clic Iris Workspace → vérifier que la modale ne s'affiche pas → vérifier que le trait se trace → ajouter une proposition → vérifier l'animation de matérialisation.

**Si les 3 tests passent** : Phase 0 réussie. On a la preuve que la direction est bonne. On investit les 62h restantes.

**Si un test échoue** : on corrige uniquement cet item. On ne touche pas aux autres.

---

## CE QU'ON APPREND DE PHASE 0

Phase 0 n'est pas seulement 3 corrections. C'est un test de la direction entière.

Si après Phase 0, un utilisateur dit *"c'est différent"* — on a prouvé que le Masterplan est juste. On déroule les Phases 1, 2, 3 avec confiance.

Si après Phase 0, un utilisateur dit *"c'est joli mais c'est tout"* — on a économisé 62h et on sait qu'il faut retravailler la direction avant d'investir.

**C'est exactement ce que fait Apple avant de lancer un produit : ils testent l'effet émotionnel d'un seul geste avant de construire tout le système autour.**

---

*Ce document ne contient aucune ligne de code.*  
*Il est soumis à validation fondateur avant implémentation.*  
*Phase 0 → validation → Phase 1 → validation → Phase 2 → validation → Phase 3.*
