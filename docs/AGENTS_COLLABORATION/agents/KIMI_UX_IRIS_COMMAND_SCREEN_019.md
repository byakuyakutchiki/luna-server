# Kimi — UX Iris Command Screen V1 — Objectif 019

Date : 2026-06-02
Agent : Kimi
Type : direction UX concrete / spec visuelle
Niveau : 2 (validation Ludovic requise avant code)

Sources :
- `docs/AGENTS_COLLABORATION/agents/CODEX_RECADRAGE_IRIS_COMMAND_SCREEN_019.md`
- `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_DIRECTION_ARTISTIQUE_IRIS_COMMAND_SCREEN_019.md`

---

## 1. Principe — Iris s'allume, pas s'affiche

Quand Ludovic dit "Iris, fais-moi un tableau des factures", l'ecran ne montre pas un message.
Il s'allume. Un panneau de verre emerge. Des donnees apparaissent ligne par ligne.
Iris travaille devant Ludovic, pas dans un chat cache.

**Ce n'est pas un chatbot avec panneau. C'est une operateuse qui ouvre son ecran de controle.**

---

## 2. Structure d'ecran global

### 2.1 Desktop (> 1024px)

```
+----------------------------------------------------------+
|                                                          |
|                    [⚪]                                   |  ← Orbe Iris
|                     Iris                                 |     centre-haut
|                                                          |
|  +------------------+  +-------------------------------+ |
|  |                  |  |                               | |
|  |   TRANSCRIPT     |  |     IRIS COMMAND SCREEN       | |  ← Panneau principal
|  |   (historique    |  |                               | |
|  |    vocal)        |  |  +-------------------------+  | |
|  |                  |  |  |  STATUS RAIL            |  | |
|  |                  |  |  +-------------------------+  | |
|  |                  |  |  |                         |  | |
|  |                  |  |  |   RENDU PRINCIPAL       |  | |
|  |                  |  |  |   (Data / Doc / Action) |  | |
|  |                  |  |  |                         |  | |
|  |                  |  |  +-------------------------+  | |
|  |                  |  |  |  CONTEXT + MISSING      |  | |
|  |                  |  |  +-------------------------+  | |
|  +------------------+  +-------------------------------+ |
|                                                          |
|  [🎤 Parler]                              [🔴 Raccrocher]|  ← Barre basse
|                                                          |
+----------------------------------------------------------+
```

**Regles desktop** :
- Orbe en haut, centre, 96px. C'est le seul element permanent.
- Transcript a gauche (30% largeur), scrollable, texte secondaire.
- Command Screen a droite (max 520px), ancre au centre-droit.
- Quand le Command Screen est ferme, l'orbe est seul au centre de l'ecran.
- Quand le Command Screen s'ouvre, l'orbe monte legerement (translateY -40px) et le panneau emerge a droite.
- Le fond reste noir pur. Pas de texture, pas de degrade.

### 2.2 Mobile (< 768px)

```
+----------------------------------+
|                                  |
|           [⚪]                   |  ← Orbe 72px
|          Iris                    |
|                                  |
+----------------------------------+
|  +----------------------------+  |
|  |  STATUS RAIL               |  |  ← 44px hauteur
|  +----------------------------+  |
|  |                            |  |
|  |    RENDU PRINCIPAL         |  |  ← Panneau principal
|  |    (scrollable)            |  |     55vh max
|  |                            |  |
|  +----------------------------+  |
|  |  CONTEXT + MISSING         |  |  ← 80px, repli
|  +----------------------------+  |
+----------------------------------+
|  [🎤]              [🔴 Raccrocher]|
+----------------------------------+
```

**Regles mobile** :
- Orbe en haut, 72px, toujours visible.
- Status Rail sous l'orbe, sticky, 44px.
- Rendu Principal = panneau pleine largeur, max 55vh, border-radius haut 24px.
- Context + Missing = section repli sous le rendu (tap pour deployer).
- Transcript masque par defaut. Tap sur "Historique" dans Status Rail pour voir.
- Le panneau emerge depuis le bas (slide up + fade).

---

## 3. Les 6 composants

### 3.1 Status Rail

Barre horizontale fine qui dit ce qu'Iris fait en ce moment.

**Desktop** : haut du Command Screen, pleine largeur, 48px.
**Mobile** : sous l'orbe, sticky, 44px.

```
+--------------------------------------------------+
|  IRIS COMMAND SCREEN          [●] Analyse en cours |
+--------------------------------------------------+
```

**Etats et couleurs** :

| Etat | Texte | Couleur | Animation |
|---|---|---|---|
| Ecoute | "Iris ecoute" | Violet `#8B74F7` | Pulse doux 2s |
| Analyse | "Analyse en cours" | Ambre `#FFB74D` | Pulse rapide 1s |
| Construction | "Construction du rendu" | Cyan `#40E0FF` | Lignes progressives |
| Pret | "Pret — a valider" | Violet `#8B74F7` | Fixe, glow subtil |
| Validation requise | "Validation requise" | Ambre `#FFB74D` | Pulse lent |
| Termine | "Termine" | Blanc `#fff` | Fixe |
| Erreur | "Erreur — reessayer" | Corail `#FF6B7B` | Pulse 3x |

**Interdit** : pas de spinner classique (loader circulaire). Utiliser un point lumineux pulse ou des lignes qui se remplissent.

### 3.2 Rendu Principal — 3 types

#### A. Data Board (tableau de donnees)

**Quand** : "fais un tableau", "compare", "liste des factures"

```
+------------------------------------------+
|  DATA BOARD                              |
+------------------------------------------+
|                                          |
|  +----+----------+-------+------+------+ |
|  | #  | Fournis. | Mont. | Ech. | Stat.| |
|  +----+----------+-------+------+------+ |
|  | 1  | EDF      | 89€   | 15/06| ⚠️   | |
|  | 2  | SFR      | 45€   | 12/06| ✅   | |
|  | 3  | AXA      | 120€  | 01/07| ⚠️   | |
|  +----+----------+-------+------+------+ |
|                                          |
|  [2 alertes] [Total : 254€/mois]         |
+------------------------------------------+
```

**Spec visuelle** :
- Fond : `--glass-bg` (verre fume)
- Bordure : `--glass-border`
- Header ligne : fond `rgba(139,116,247,0.08)`, texte `--iris-violet`
- Lignes alternees : fond `rgba(255,255,255,0.02)` / transparent
- Badges statut :
  - ✅ Vert `#4ade80` — OK
  - ⚠️ Ambre `#FFB74D` — Attention
  - ❌ Corail `#FF6B7B` — Critique
- Separateurs : ligne 1px `rgba(255,255,255,0.04)`
- Chiffres : font-variant-numeric tabular-nums
- Hover ligne : fond `rgba(139,116,247,0.06)`
- **Pas de markdown visible. Pas de bordures epaisses.**

#### B. Document Draft (brouillon document)

**Quand** : "redige un courrier", "prepare une note", "ecris une lettre"

```
+------------------------------------------+
|  DOCUMENT DRAFT                          |
+------------------------------------------+
|                                          |
|  Objet : Demande de resiliation          |
|                                          |
|  Destinataire : Service Clients EDF      |
|  Adresse : TSA 12345, 75008 Paris        |
|                                          |
|  Madame, Monsieur,                       |
|                                          |
|  Je vous ecris pour vous informer de     |
|  ma decision de resilier mon contrat     |
|  souscrit le 15 mars 2024...             |
|                                          |
|  [................................]      |
|  [................................]      |
|                                          |
|  Cordialement,                           |
|  Ludovic Dupont                          |
+------------------------------------------+
```

**Spec visuelle** :
- Fond : `--glass-bg`
- Titre objet : `--text-title` (20px, medium), violet `#8B74F7`
- Meta (destinataire, date) : `--text-secondary` (13px)
- Corps : `--text-body` (15px, regular), line-height 1.7
- Paragraphes : marge-bas 16px
- Blocs repliques/dialogue : indentation 24px + bordure gauche 2px violet
- **Ressemble a un vrai document A4, pas a un bloc de chat.**

#### C. Action Board (plan d'action / checklist)

**Quand** : "fais une checklist", "qu'est-ce qu'il reste a faire", "plan d'action"

```
+------------------------------------------+
|  ACTION BOARD                            |
+------------------------------------------+
|                                          |
|  Prioritaire — 2 items                   |
|  +------------------------------------+  |
|  | [ ] Resilier EDF avant 15/06       |  |
|  |     ⚠️ Echeance dans 3 jours        |  |
|  +------------------------------------+  |
|  | [ ] Prevenir le proprietaire       |  |
|  |     📎 Modele de lettre prete       |  |
|  +------------------------------------+  |
|                                          |
|  A suivre — 3 items                      |
|  +------------------------------------+  |
|  | [✓] Resilier internet SFR          |  |
|  | [✓] Reserver camion demenagement   |  |
|  | [ ] Changer adresse poste          |  |
|  +------------------------------------+  |
|                                          |
+------------------------------------------+
```

**Spec visuelle** :
- Sections par priorite : "Prioritaire", "A suivre", "Termine"
- Cartes : fond `rgba(255,255,255,0.03)`, border-radius 12px, padding 14px
- Checkbox : carre arrondi 6px, bordure 1.5px `--text-tertiary`
  - Coche : violet `#8B74F7`, animation scale 0→1
- Tag echeance : ambre `#FFB74D` si < 7j, corail `#FF6B7B` si < 2j
- Tag piece jointe : cyan `#40E0FF`
- **Chaque action est une carte, pas une ligne de texte.**

### 3.3 Context Panel

**Quand** : toujours visible quand Command Screen ouvert.
Resume ce qu'Iris a compris de la demande.

```
+------------------------------------------+
|  CONTEXTE COMPRIS                        |
+------------------------------------------+
|  • Type : tableau de factures mensuelles |
|  • Periode : juin 2026                   |
|  • Criteres : montant, echeance, statut  |
+------------------------------------------+
```

**Spec** :
- Fond : plus transparent que le rendu principal
- Texte : `--text-secondary` (13px)
- Items : puces fines, pas de puces rondes
- **Donne confiance sans etre intrusif.**

### 3.4 Missing Info Panel

**Quand** : Iris a besoin de donnees supplementaires.

```
+------------------------------------------+
|  INFOS MANQUANTES                        |
+------------------------------------------+
|  Pour finaliser le tableau, j'ai besoin :|
|                                          |
|  [ ] Le budget mensuel maximum           |
|  [ ] Si tu veux trier par echeance       |
|  [ ] Ton adresse actuelle (pour CAF)     |
|                                          |
|  [💬 Repondre a Iris]                    |
+------------------------------------------+
```

**Spec** :
- Bordure : ambre `#FFB74D`, 1px, opacite 0.3
- Fond : `rgba(255,183,77,0.04)`
- Items : cases a cocher ou champs de saisie inline
- Bouton reponse : violet `#8B74F7`, radius 100px
- **Apparait uniquement quand necessaire.**

### 3.5 Actions Locales (barre de boutons)

```
+------------------------------------------+
|  [Modifier]  [Copier]  [Telecharger]  [✕]|
+------------------------------------------+
```

**Spec** :
- Desktop : 4 boutons en ligne, flex, gap 12px
- Mobile : 2 boutons par ligne (wrap)
- Modifier : bordure `--glass-border`, fond transparent
- Copier : violet `#8B74F7`, fond `rgba(139,116,247,0.15)`
- Telecharger : cyan `#40E0FF`, fond `rgba(64,224,255,0.12)`
- Fermer : texte `--text-tertiary`, sans fond
- Border-radius : 100px (pill shape)
- **Interdit** : carres, ombres, emojis

---

## 4. Animations — specification precise

### 4.1 Ouverture du Command Screen

**Sequence** (desktop) :
1. `0ms` — Orbe monte (translateY -40px, 400ms, ease-out-expo)
2. `100ms` — Panneau apparait (opacity 0→1, scale 0.96→1, 500ms)
3. `200ms` — Status Rail se dessine (width 0→100%, 400ms)
4. `300ms` — Contenu apparait ligne par ligne (stagger 60ms par element)
5. `600ms` — Actions locales apparaissent (translateY 10px→0, opacity 0→1, 300ms)

**Sequence** (mobile) :
1. `0ms` — Panneau slide up depuis le bas (translateY 100%→0, 400ms, ease-spring)
2. `150ms` — Status Rail fade in
3. `250ms` — Contenu stagger 60ms

### 4.2 Mise a jour du rendu

Quand Iris met a jour le tableau/document :
- Lignes/cartes qui changent : fond pulse violet 0.3s
- Nouvelles lignes : slide in depuis la gauche 300ms
- Lignes supprimees : opacity 1→0 + translateX -20px, 200ms

### 4.3 Fermeture

- Panneau : opacity 1→0 + scale 1→0.98, 250ms
- Orbe : retour position initiale, 400ms
- Contenu : efface apres animation

### 4.4 Etat "Iris travaille"

- Status Rail : point lumineux pulse selon la couleur de l'etat
- Bordure du panneau : glow subtil (box-shadow) de la couleur d'etat
- Orbe : halo de la meme couleur, opacite 0.15

---

## 5. CSS concret — variables et classes

### Variables (complement de DeepSeek)

```css
:root {
  /* DeepSeek */
  --void: #000000;
  --glass-bg: rgba(10, 10, 15, 0.75);
  --glass-border: rgba(255, 255, 255, 0.05);
  --glass-blur: 40px;
  --glass-saturate: 180%;
  --iris-violet: #8B74F7;
  --iris-violet-glow: rgba(139, 116, 247, 0.3);
  --data-cyan: #40E0FF;
  --alert-amber: #FFB74D;
  --error-coral: #FF6B7B;
  --text-primary: rgba(255, 255, 255, 0.9);
  --text-secondary: rgba(255, 255, 255, 0.55);
  --text-tertiary: rgba(255, 255, 255, 0.3);
  --font: 'Inter', -apple-system, sans-serif;
  --radius-panel: 24px;
  --radius-button: 100px;
  --ease-spring: cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 300ms;
  --duration-normal: 600ms;

  /* Kimi additions */
  --command-screen-width: 520px;
  --command-screen-mobile-max-height: 55vh;
  --status-rail-height: 48px;
  --status-rail-mobile-height: 44px;
  --orb-desktop: 96px;
  --orb-mobile: 72px;
  --action-button-height: 40px;
}
```

### Classes principales

```css
/* Command Screen */
.iris-command-screen {
  position: absolute;
  top: 120px;
  right: 40px;
  width: min(var(--command-screen-width), calc(100% - 80px));
  display: none;
  flex-direction: column;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-panel);
  background: var(--glass-bg);
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-saturate));
  box-shadow: 0 0 0 1px rgba(139,116,247,0.06), 0 24px 80px rgba(0,0,0,0.4);
  overflow: hidden;
}
.iris-command-screen.open { display: flex; }
.iris-command-screen.state-analyse { box-shadow: 0 0 0 1px rgba(255,183,77,0.1); }
.iris-command-screen.state-ready { box-shadow: 0 0 0 1px rgba(139,116,247,0.12); }

/* Status Rail */
.status-rail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--status-rail-height);
  padding: 0 var(--space-md);
  border-bottom: 1px solid var(--glass-border);
}
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  margin-right: 10px;
}
.status-dot.pulse { animation: statusPulse 2s ease-in-out infinite; }

/* Data Board */
.data-board table {
  width: 100%; border-collapse: collapse; font-size: 14px;
}
.data-board th {
  text-align: left; padding: 12px 16px;
  color: var(--iris-violet); font-weight: 500;
  border-bottom: 1px solid rgba(139,116,247,0.15);
  background: rgba(139,116,247,0.04);
}
.data-board td {
  padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.03);
  color: var(--text-primary);
}
.data-board tr:hover { background: rgba(139,116,247,0.04); }

/* Document Draft */
.doc-draft .doc-title {
  font-size: 20px; font-weight: 500; color: var(--iris-violet);
  margin-bottom: 8px; line-height: 1.3;
}
.doc-draft .doc-meta {
  font-size: 13px; color: var(--text-secondary); margin-bottom: 24px;
}
.doc-draft .doc-body {
  font-size: 15px; line-height: 1.7; color: var(--text-primary);
}
.doc-draft .doc-body p { margin-bottom: 16px; }

/* Action Board */
.action-board .action-section { margin-bottom: 20px; }
.action-board .action-section-title {
  font-size: 11px; font-weight: 600; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-tertiary);
  margin-bottom: 10px;
}
.action-card {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px; border-radius: 12px;
  background: rgba(255,255,255,0.03); margin-bottom: 8px;
  border: 1px solid transparent; transition: all 0.2s;
}
.action-card:hover { background: rgba(255,255,255,0.05); border-color: var(--glass-border); }
.action-card .checkbox {
  width: 18px; height: 18px; border-radius: 6px;
  border: 1.5px solid var(--text-tertiary); flex-shrink: 0;
}
.action-card .checkbox.checked {
  background: var(--iris-violet); border-color: var(--iris-violet);
}

/* Animations */
@keyframes statusPulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.3); }
}
@keyframes panelIn {
  from { opacity: 0; transform: scale(0.96) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
```

---

## 6. Responsive — regles absolues

| Element | Desktop | Mobile |
|---|---|---|
| Orbe | 96px, centre-haut | 72px, centre-haut |
| Command Screen | Droite, 520px max, slide+scale | Bas, pleine largeur, slide up |
| Transcript | Gauche, 30%, visible | Masque, tap "Historique" |
| Status Rail | Haut du panneau, 48px | Sous orbe, sticky, 44px |
| Data Board | Table complete, colonnes visibles | Scroll horizontal si > 3 colonnes |
| Document Draft | A4-like, marges genereuses | Pleine largeur, padding 20px |
| Action Board | 2 colonnes si ecran large | 1 colonne, cartes empilees |
| Boutons actions | 1 ligne, 4 boutons | Wrap 2x2 |

---

## 7. Interdits absolus (verification avant code)

- [ ] **Pas de markdown brut visible** (pas de `| col1 | col2 |`)
- [ ] **Pas de texte qui dit "je vais afficher"** — Iris affiche directement
- [ ] **Pas de message "je ne peux pas afficher directement"**
- [ ] **Pas d'emojis** dans l'interface (sauf orbe si necessaire)
- [ ] **Pas d'ombres portees classiques** (box-shadow diffuse)
- [ ] **Pas de bordures epaisses** (> 1px)
- [ ] **Pas de coins carres** (radius minimum 12px)
- [ ] **Pas de plus d'une couleur d'accent a la fois** dans un panneau
- [ ] **Pas de textes longs sans structure** (paragraphes > 4 lignes = scinder)
- [ ] **Pas d'ecran vide sans feedback** (minimum : statut + message)
- [ ] **Pas de spinner/loader circulaire classique**
- [ ] **Pas d'envoi automatique sans confirmation**

---

## 8. Protocole Iris — message dans le prompt

Ajouter au system prompt d'Iris :

```
Quand l'utilisateur demande un tableau, un document, une checklist ou un plan d'action :
1. Tu declenches l'affichage du Command Screen avec le type approprie.
2. Tu ne dis JAMAIS "je ne peux pas afficher" ou "voici du texte".
3. Si des donnees manquent, tu affiches une structure provisoire et tu demandes les infos manquantes dans le Missing Info Panel.
4. Tu ne declenches AUCUNE action sensible (envoi, paiement, reservation) sans confirmation explicite.
5. Tu tais quand le rendu est pret, sauf si l'utilisateur te parle.
```

---

## 9. Checklist validation Kimi avant test Ludovic

- [ ] Orbe visible et reactif (4 etats couleur)
- [ ] Command Screen s'ouvre sur mot-cle detecte
- [ ] Status Rail visible avec etat pulse
- [ ] Data Board = tableau HTML, pas markdown
- [ ] Document Draft = structure document A4-like
- [ ] Action Board = cartes avec checkbox et tags
- [ ] Context Panel toujours present
- [ ] Missing Info Panel quand donnees manquantes
- [ ] Animations fluides (panel in, stagger, update)
- [ ] Mobile : pas de superposition, scroll fluide
- [ ] Palette violet Iris, pas vert Simli
- [ ] Aucun emoji dans Command Screen
- [ ] Aucune action sans confirmation
- [ ] Iris ne dit pas "je ne peux pas afficher"

---

*Reference : CODEX_RECADRAGE_IRIS_COMMAND_SCREEN_019.md, DEEPSEEK_DIRECTION_ARTISTIQUE_IRIS_COMMAND_SCREEN_019.md*
