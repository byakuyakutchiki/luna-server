# LUNA PRESENCE ENGINE — FEUILLE DE ROUTE D'IMPLÉMENTATION
## Phase 1 / Phase 2 / Phase 3

**Auteur** : Claude — Lead Product Designer / Front-End Principal  
**Date** : 13 juin 2026  
**Référence** : `LUNA_PRESENCE_ENGINE_MASTERPLAN.md`  
**Statut** : Plan validé avant implémentation — aucune ligne de code  

> Ce document transforme la vision en séquence d'actions concrètes.  
> Chaque phase est indépendante et livrable. Chaque item a une estimation, une maquette textuelle, et un critère de validation.

---

## PRINCIPE DE PRIORISATION

Trois critères ordonnent les items :

**Impact émotionnel** — Est-ce que ça change ce que l'utilisateur *ressent* ?  
**Risque fonctionnel** — Est-ce que ça peut casser quelque chose qui marche ?  
**Effort** — Combien de temps raisonnablement ?  

On commence par : impact fort + risque nul + effort faible.  
On termine par : impact fort + risque modéré + effort plus élevé.

---

## PHASE 1 — "Luna respire"
### Objectif : l'interface n'est plus statique. Elle est vivante à 0% d'interaction.
### Durée estimée : 3–4 jours
### Risque fonctionnel : nul — CSS et micro-JS uniquement, aucune route touchée

---

### P1-A — Design System (token CSS unifié)
**Fichier** : `static/luna-design-system.css` (nouveau fichier, importé dans tous les HTML)  
**Durée** : 4h  
**Risque** : nul  

**Maquette — contenu du fichier :**
```
:root {
  /* Fonds */
  --luna-bg-base     : #020810   → nuit parisienne
  --luna-bg-panel    : #0d1117   → verre teinté YAWatch
  --luna-bg-card     : #111827   → carte glassmorphism

  /* Couleurs narratives */
  --luna-violet      : #7c3aed   → présence Luna dans le système
  --luna-doll        : #7B4FA6   → robe velours de Luna Doll
  --luna-iris        : #10b981   → Iris active / protection
  --luna-gold        : #f59e0b   → décision / validation importante
  --luna-fog         : #6b7280   → secondaire / discret

  /* Texte */
  --luna-text-1      : #e5e7eb   → primaire
  --luna-text-2      : #9ca3af   → secondaire
  --luna-text-3      : #4b5563   → tertiaire

  /* Halos */
  --luna-glow-v      : rgba(124,58,237,0.15)   → violet doux
  --luna-glow-i      : rgba(16,185,129,0.12)   → émeraude doux
  --luna-glow-g      : rgba(245,158,11,0.15)   → or doux

  /* Borders */
  --luna-border      : rgba(255,255,255,0.08)
  --luna-border-iris : rgba(16,185,129,0.25)

  /* Animations */
  --luna-ease-out    : cubic-bezier(0.16, 1, 0.3, 1)
  --luna-ease-in     : cubic-bezier(0.7, 0, 0.84, 0)
  --luna-breathe     : 4s ease-in-out infinite
  --luna-pulse       : 6s ease-in-out infinite
}
```
**Critère de validation** : Importer dans 3 pages, vérifier que les variables s'appliquent correctement, aucune régression visuelle.

---

### P1-B — Fond login vivant
**Fichier** : `static/index.html` — section CSS `.auth-screen`  
**Durée** : 2h  
**Risque** : nul  

**Maquette avant/après :**
```
AVANT :
┌─────────────────────────────────────────┐
│  fond bleu-violet statique              │
│         ┌──────────────┐               │
│         │  LUNA        │               │
│         │  email       │               │
│         │  mdp         │               │
│         │  [Se connecter]│             │
│         └──────────────┘               │
└─────────────────────────────────────────┘

APRÈS :
┌─────────────────────────────────────────┐
│  fond nuit parisienne (--luna-bg-base)  │
│  halo violet haut-gauche  ·  pulse 8s  │
│  halo émeraude bas-droite ·  pulse 11s │
│  grain très léger overlay (opacity .02)│
│         ┌──────────────┐               │
│         │  ·LUNA·      │ ← breathing   │
│         │  email       │               │
│         │  mdp         │               │
│         │  [Se connecter] ←glow hover  │
│         └──────────────┘               │
│  silhouette Luna filigrane (op. 0.04)  │
└─────────────────────────────────────────┘
```
**Critère de validation** : Capture Playwright avant/après. Le fond respire. Aucun élément de formulaire n'a bougé.

---

### P1-C — Avatar Luna animé (breathing)
**Fichier** : `static/index.html` — CSS sur l'avatar `#lunaAvatar` ou équivalent  
**Durée** : 1h  
**Risque** : nul  

**Animation CSS :**
```
@keyframes luna-breathe {
  0%, 100% { transform: scale(1.0); }
  50%       { transform: scale(1.015); }
}
.luna-avatar { animation: luna-breathe var(--luna-breathe); }
```
**Critère de validation** : L'avatar respire à 0% d'interaction. La photo n'est pas déformée. L'animation est imperceptible à vitesse normale, perceptible si on fixe l'écran 5 secondes.

---

### P1-D — Luna Presence Halo (zone chat)
**Fichier** : `static/index.html` — élément pseudo ou div `.luna-presence-halo`  
**Durée** : 3h  
**Risque** : faible (ajout d'un élément CSS, aucune logique métier)  

**Maquette — zone chat :**
```
┌─────────────────────────────────────────┐
│                                         │
│  [bulle Luna]  "Je reviens..."          │
│                                         │
│                                         │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ ← halo émeraude
│  ░   halo radial bas, opacity 0.06   ░  │    pulse 6s
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │    actif quand Luna répond
│                                         │
│  [ Message pour Luna...          ] [►] │
└─────────────────────────────────────────┘
```
**États :**
- Luna inactive → halo opacity 0.04, pulse lent (8s)
- Luna écoute → halo opacity 0.08, pulse moyen (4s)
- Luna répond → halo opacity 0.12, pulse rapide (2s)

**Critère de validation** : 3 états visuellement distincts. La transition entre états prend 600ms. Le fond de chat n'est plus identique quand Luna parle et quand elle ne parle pas.

---

### P1-E — Message d'erreur humanisé
**Fichier** : `static/index.html` — logique d'affichage du message "injoignable"  
**Durée** : 1h  
**Risque** : nul  

**Maquette avant/après :**
```
AVANT :
┌────────────────────────────────────────────┐
│  [avatar]  Luna                            │
│  Luna est temporairement injoignable.      │
│  Vérifie que le serveur tourne.            │
└────────────────────────────────────────────┘

APRÈS :
┌────────────────────────────────────────────┐
│  [avatar ·breathing]  Luna                 │
│  "Je reviens dans un instant."             │
└────────────────────────────────────────────┘
```
**Règle** : jamais de jargon technique visible à l'utilisateur final. Les erreurs système restent dans les logs.

**Critère de validation** : Message affiché dans Playwright. Aucun mot technique visible. Ton cohérent avec Luna.

---

### P1-F — Fond Iris Visio atmosphérique
**Fichier** : `static/simli.html` — section CSS fond + remplacement avatar  
**Durée** : 4h  
**Risque** : nul  

**Maquette avant/après :**
```
AVANT :
┌─────────────────────────────┐
│  fond bleu nuit uni froid   │
│                             │
│    ●  L                     │
│    Iris Visio               │
│    [Durée ▼]                │
│    [DÉMARRER]               │
│    ← Retour                 │
│                             │
└─────────────────────────────┘

APRÈS :
┌─────────────────────────────┐
│  décor SVG nocturne         │
│  Ken Burns lent (60s)       │
│  opacity 0.30               │
│  halo violet centré         │
│    ○  Luna silhouette       │ ← remplace "L"
│    Iris Visio               │
│    [1 heure    ▾]           │ ← custom select
│    [   DÉMARRER   ]         │
│    ← Retour au chat         │
│                             │
└─────────────────────────────┘
```
**Décor SVG** : utiliser l'un des assets existants `static/assets/backgrounds/*.svg` (décor nocturne ou intérieur)

**Critère de validation** : Capture Playwright. Le fond est cinématique. L'initiale "L" a disparu. Le dropdown natif a disparu.

---

### P1-G — Fond + identité Admin
**Fichier** : `static/admin.html` (ou équivalent)  
**Durée** : 2h  
**Risque** : nul  

**Maquette avant/après :**
```
AVANT :
┌──────────────────────────────────────────┐
│                                          │
│                                          │
│            ┌────────────────┐            │
│            │  Luna Admin    │            │
│            │  [mot de passe]│            │
│            │  [Se connecter]│            │
│            └────────────────┘            │
│                                          │
└──────────────────────────────────────────┘

APRÈS :
┌──────────────────────────────────────────┐
│  [YAWatch ⬦]  YAWatch Industries         │
│  ·····················halo émeraude·····│
│                                          │
│      ┌────────────────────────────┐      │
│      │  YAWatch Industries        │      │ ← logo
│      │  Accès Opérateur           │      │ ← bandeau
│      │  ─────────────────────     │      │
│      │  [mot de passe admin    ]  │      │
│      │  [      Se connecter    ]  │      │
│      └────────────────────────────┘      │
│          border émeraude opacity 0.25    │
└──────────────────────────────────────────┘
```
**Critère de validation** : La page admin a une identité. On sait qu'on est dans un espace sérieux, pas dans une app générique.

---

### P1-H — Photos GTA visibilité Workspace
**Fichier** : `static/team_workspace.html`  
**Durée** : 30 min  
**Risque** : nul  

```
Sélecteur : .tw-bg-char img (ou équivalent)
Changement : opacity 0.15 → 0.35
```
**Critère de validation** : Capture Playwright. Luna et Aby sont visibles derrière le workspace. L'univers est présent.

---

### Résumé Phase 1

| Item | Fichier | Durée | Impact |
|---|---|---|---|
| P1-A Design System | `luna-design-system.css` | 4h | Structurant |
| P1-B Fond login vivant | `index.html` | 2h | Fort |
| P1-C Avatar breathing | `index.html` | 1h | Moyen |
| P1-D Presence Halo chat | `index.html` | 3h | Fort |
| P1-E Message humanisé | `index.html` | 1h | Moyen |
| P1-F Fond Iris Visio | `simli.html` | 4h | Très fort |
| P1-G Admin identité | `admin.html` | 2h | Fort |
| P1-H Photos GTA | `team_workspace.html` | 0.5h | Moyen |
| **TOTAL** | | **~17h30** | |

**Après Phase 1 :** Luna respire. Les 5 problèmes critiques sont résolus. L'application n'est plus statique.

---

## PHASE 2 — "Luna matérialise"
### Objectif : les moments clés deviennent des scènes. Le Workspace s'anime. Les Moments Wow 1 à 6 existent.
### Durée estimée : 5–7 jours
### Risque fonctionnel : faible à modéré — animations JS sur des éléments existants

---

### P2-A — Moment Wow 1 : Premier lancement
**Fichier** : `static/index.html` — animation d'entrée de l'écran de login  
**Durée** : 3h  

**Séquence :**
```
t=0ms    : fond noir
t=200ms  : fond nuit parisienne (fade-in 600ms)
t=600ms  : halo violet gauche (fade-in 400ms)
t=900ms  : halo émeraude droit (fade-in 400ms)
t=1100ms : carte login (slide from bottom 20px + fade 300ms)
t=1300ms : logo YAWatch (fade 200ms)
t=1500ms : champs et bouton (fade 200ms)
```
**Ne joue qu'une fois** (localStorage flag `luna_intro_played`).

---

### P2-B — Moment Wow 4 : Démarrage Iris Visio
**Fichier** : `static/simli.html` — animation bouton DÉMARRER  
**Durée** : 4h  

**Séquence :**
```
[clic DÉMARRER]
t=0ms   : bouton pulse (scale 0.96 → 1.0, 200ms)
t=200ms : fond SVG accélère (Ken Burns speed x3, 1s)
t=800ms : halo violet s'élargit (radius 20% → 60%, opacity 0.3, 600ms)
t=1200ms: transition vers cinématique (fade-out 400ms)
```
**Critère** : L'appui sur DÉMARRER n'est plus un clic — c'est le début d'une scène.

---

### P2-C — Moment Wow 6 : Entrée Workspace
**Fichier** : `static/team_workspace.html` — animation d'entrée du canvas  
**Durée** : 5h  

**Séquence (après passage modale) :**
```
t=0ms   : canvas noir
t=200ms : grille perspective (fade-in 800ms, opacity 0.04)
t=600ms : halos latéraux (fade-in 600ms)
t=900ms : trait de surface horizontal (trace de gauche à droite, 1.2s)
t=1500ms: barre stepper (fade-in 400ms)
t=1800ms: zone canvas prête — texte "Votre question stratégique..." (fade-in 300ms)
```

---

### P2-D — Moment Wow 7 : Matérialisation proposition
**Fichier** : `static/team_workspace.html` — fonction d'ajout d'objet  
**Durée** : 3h  

```
Carte nouvelle proposition :
t=0ms   : scale(0.93) opacity(0)
t=200ms : scale(1.0) opacity(1)  — ease-out 200ms
t=200ms : border émeraude flash (opacity 1 → 0, 400ms)

Stagger si plusieurs cartes : délai 80ms entre chaque
```

---

### P2-E — Moment Wow 8 : Décision scellée
**Fichier** : `static/team_workspace.html` — événement validation décision  
**Durée** : 3h  

```
[Décision validée]
t=0ms   : icône cadenas apparaît (scale 0→1, 200ms)
t=200ms : pulse radial or (radius 0 → 80px, opacity 0.4 → 0, 600ms)
t=300ms : titre de la carte passe en --luna-gold
t=600ms : état stable — carte décision en gold
```

---

### P2-F — Canvas d'attente Workspace (surface vivante)
**Fichier** : `static/team_workspace.html` — état vide du canvas  
**Durée** : 4h  

**Maquette :**
```
État vide du canvas Workspace :

┌─────────────────────────────────────────────┐
│  stepper  [1]──[2]──[3]──...──[13]         │
├─────────────────────────────────────────────┤
│                                             │
│   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─    ← trait animé │
│                                             │
│   "Quelle est votre question stratégique ?" │
│                                             │
│        [Définir le brief →]                 │
│                                             │
│  ·  ·  ·  ←  points pulsants (attente Iris) │
│                                             │
└─────────────────────────────────────────────┘
```
Le trait horizontal se trace de gauche à droite en 1.5s, puis pulse très doucement. Les 3 points apparaissent seulement si l'utilisateur ne fait rien pendant 5s — signal que Iris attend.

---

### P2-G — Bypass modale solo (Workspace)
**Fichier** : `static/team_workspace.html` — logique d'entrée  
**Durée** : 3h  

**Logique :**
```
Si (participants === 0 ET profil.prenom est défini) :
  → entrée automatique en Owner avec profil.prenom
  → modale skippée
  → animation d'entrée P2-C directement
Sinon :
  → modale normale
```
**Critère** : En solo, l'utilisateur ne voit pas la modale. Il entre directement dans son Workspace.

---

### P2-H — États IA visibles (écoute / réflexion / réponse)
**Fichier** : `static/index.html` + `static/simli.html`  
**Durée** : 4h  

**Maquette des 3 états :**
```
ÉCOUTE     → anneau émeraude pulsant autour avatar (opacity 0.6, pulse 2s)
             label discret : aucun (silence = présence)

RÉFLEXION  → anneau blanc très pâle (opacity 0.3, pulse 4s lent)
             3 points animés (·  ·  ·) sous l'avatar, stagger 300ms

RÉPONSE    → anneau émeraude fixe (opacity 0.8, pas de pulse)
             halo Presence Halo en intensité max
             text stream visible en temps réel
```

---

### Résumé Phase 2

| Item | Fichier | Durée | Moment Wow |
|---|---|---|---|
| P2-A Premier lancement | `index.html` | 3h | WOW-1 |
| P2-B Démarrage Iris Visio | `simli.html` | 4h | WOW-4 |
| P2-C Entrée Workspace | `team_workspace.html` | 5h | WOW-6 |
| P2-D Matérialisation proposition | `team_workspace.html` | 3h | WOW-7 |
| P2-E Décision scellée | `team_workspace.html` | 3h | WOW-8 |
| P2-F Canvas d'attente | `team_workspace.html` | 4h | — |
| P2-G Bypass modale solo | `team_workspace.html` | 3h | — |
| P2-H États IA visibles | `index.html`, `simli.html` | 4h | WOW-3, WOW-5 |
| **TOTAL** | | **~29h** | |

**Après Phase 2 :** Les 6 premiers Moments Wow existent. Le Workspace est vivant. L'interface matérialise.

---

## PHASE 3 — "Luna se souvient"
### Objectif : les 4 derniers Moments Wow. Luna Doll visible. Continuité série. Anti-ChatGPT complet.
### Durée estimée : 5–7 jours
### Risque fonctionnel : modéré — implique la logique de persistance et des interactions nouvelles

---

### P3-A — Moment Wow 9 : Dossier final compilé
**Fichier** : `static/team_workspace.html` — étape 12 (export)  
**Durée** : 5h  

**Séquence :**
```
[Étape 12 atteinte]
t=0ms    : toutes les cartes des étapes précédentes visibles (opacity 1)
t=500ms  : cartes se compactent vers le bas (stagger 80ms, scale 1→0.3, opacity 1→0)
t=1500ms : icône dossier au centre (scale 0→1, 300ms)
t=1700ms : icône dossier se ferme (animation fermeture)
t=2000ms : timestamp apparaît sous le dossier (fade 300ms)
t=2200ms : bouton "Télécharger le dossier final" (fade 300ms)
```

---

### P3-B — Moment Wow 10 : Souvenir sauvegardé
**Fichier** : `static/index.html` — logique de sauvegarde note/mémoire  
**Durée** : 4h  

**Séquence :**
```
[Note sauvegardée]
t=0ms   : fragment de texte (copie de la note) apparaît
t=200ms : fragment monte (translateY 0 → -80px) + opacity (1 → 0), 1200ms
t=800ms : halo violet pulse une fois autour de l'avatar
t=1400ms: message Luna : "Je m'en souviendrai." (fade-in, reste 2s, fade-out)
```

---

### P3-C — Luna Doll dans l'interface
**Fichiers** : `static/index.html`, `static/simli.html`, `static/team_workspace.html`  
**Durée** : 4h  

**Placement :**
```
Écran de login     : Luna Doll silhouette en filigrane, bas-droit, opacity 0.05
                     Taille 80px. SVG minimaliste (robe violette, forme poupée).

Iris Visio         : Luna Doll en illustration centrée sous "Iris Visio"
                     Remplace l'initiale "L". Opacity 0.8. Taille 60px.

Workspace (footer) : Micro-icône Luna Doll, 16px, opacity 0.3, en bas à gauche.
                     Tooltip au hover : "YAWatch Industries"
```
**Règle** : Luna Doll est toujours reconnaissable. Jamais robotique. Jamais LED. Forme douce, robe violette (#7B4FA6).

---

### P3-D — Transitions de page (continuité atmosphérique)
**Fichiers** : `static/index.html` + logique de navigation JS  
**Durée** : 3h  

**Pattern :**
```
[Navigation vers /team, /simli, ou retour /]
t=0ms   : fade-out current page (opacity 1→0, 150ms)
t=150ms : page cible monte (opacity 0→1, 200ms)
```
Fade simple. Aucun slide agressif. Continuité d'atmosphère garantie.

---

### P3-E — Moment Wow 2 : Première connexion
**Fichier** : `static/index.html`  
**Durée** : 3h  

**Séquence (premier login uniquement — flag localStorage) :**
```
t=0ms   : fond respire (scale 1.0→1.02, opacity +0.02, 800ms)
t=400ms : halo pulse une fois (radius +20%, 600ms)
t=800ms : page chat s'ouvre
t=1000ms: premier message Luna apparaît avec stream (WOW-3)
           Texte : "Je suis là." (1 phrase. Rien d'autre.)
```

---

### P3-F — Typographie signature
**Fichier** : `static/luna-design-system.css` + tous les HTML  
**Durée** : 3h  

**Règles :**
```
LUNA  → font-weight: 800, letter-spacing: 0.15em, text-transform: uppercase
IRIS  → font-weight: 700, letter-spacing: 0.12em, text-transform: uppercase
YAWATCH → font-weight: 700, letter-spacing: 0.10em, text-transform: uppercase
```
Ces 3 mots ne s'écrivent jamais en minuscules dans les titres de pages et les en-têtes.

---

### P3-G — Audit Anti-ChatGPT final
**Fichiers** : tous  
**Durée** : 4h (relecture + corrections ponctuelles)  

**Checklist :**
```
□ Aucun message système visible (erreur 404, "Chargement...", "Traitement...")
□ Tous les textes de feedback sont en première personne de Luna
□ Aucun widget isolé sans contexte narratif
□ La barre de saisie n'est jamais le seul élément visible quand Luna est "silencieuse"
□ Sur chaque page, si on retire le logo Luna — est-ce encore reconnaissable ?
□ La question série est posée pour chaque page modifiée
```

---

### Résumé Phase 3

| Item | Fichier | Durée | Moment Wow |
|---|---|---|---|
| P3-A Dossier final | `team_workspace.html` | 5h | WOW-9 |
| P3-B Souvenir sauvegardé | `index.html` | 4h | WOW-10 |
| P3-C Luna Doll visible | multiple | 4h | — |
| P3-D Transitions de page | `index.html` + JS | 3h | — |
| P3-E Première connexion | `index.html` | 3h | WOW-2 |
| P3-F Typographie signature | CSS + HTML | 3h | — |
| P3-G Audit Anti-ChatGPT | multiple | 4h | — |
| **TOTAL** | | **~26h** | |

**Après Phase 3 :** Les 10 Moments Wow existent. Luna Doll est dans l'interface. La typographie est signée. L'application passe le test Anti-ChatGPT.

---

## RÉCAPITULATIF GLOBAL

| Phase | Durée | Résultat |
|---|---|---|
| Phase 1 — Luna respire | ~17h30 | Interface vivante à 0% d'interaction |
| Phase 2 — Luna matérialise | ~29h | Moments Wow 1,3,4,5,6,7,8 — Workspace animé |
| Phase 3 — Luna se souvient | ~26h | Moments Wow 2,9,10 — Luna Doll — Anti-ChatGPT |
| **TOTAL** | **~72h (~9 jours)** | **Luna Presence Engine complet** |

---

## PROTOCOLE DE VALIDATION PAR PHASE

Avant de passer à la phase suivante, valider avec Playwright :

**Phase 1** : 8 screenshots avant/après (une par item). Vérifier que aucun workflow existant n'est cassé (login, chat, voix, workspace, admin).

**Phase 2** : Enregistrement vidéo (Playwright `recordVideo`) de chaque Moment Wow. Durée : 5s minimum par moment. Vérifier que les animations ne bloquent pas les interactions.

**Phase 3** : Test complet parcours utilisateur (login → chat → Iris Visio → Workspace → dossier final → sauvegarde). Vérifier checklist Anti-ChatGPT sur chaque page.

---

## UNE RÈGLE AU-DESSUS DE TOUTES LES AUTRES

> Avant chaque item implémenté, lire la phrase-cible de la page dans le Masterplan.  
> Après chaque item implémenté, prendre une capture et se demander :  
> **"Est-ce que quelqu'un qui vient de voir un épisode de YAWatch-LUNA reconnaîtrait cet écran ?"**

Si non — recommencer.

---

*Ce document ne contient aucune ligne de code.*  
*Il est la feuille de route de validation avant implémentation.*  
*Ne pas commencer la Phase 2 sans validation fondateur de la Phase 1.*  
*Ne pas commencer la Phase 3 sans validation fondateur de la Phase 2.*
