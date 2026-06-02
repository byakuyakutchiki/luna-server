# Kimi — Iris Visual System V2 — Objectif 021

Date : 2026-06-02
Agent : Kimi
Domaine : UX / UI exclusivement — ne pas toucher au code backend

**Ambition : numéro mondial. Pas le meilleur en France. Le meilleur sur terre.**

---

## Ce que tu dois livrer

Trois chantiers indépendants, livrés dans ce fichier en réponse :

1. **Teams Overlay** — panneau participants style Zoom/Teams, intégré dans `/simli`
2. **Light / Dark Mode** — vrai thème clair premium, pas une inversion
3. **8 nouveaux render_type visuels** — maquettes et specs CSS

---

## Chantier 1 — Teams Overlay

### 1.1 Objectif

Quand une session collaborative est active (`session_id` dans le token), afficher
un panneau participants dans l'interface `/simli`, aussi naturel que Zoom ou Teams.
L'owner peut mute/kick. Tout le monde voit qui parle.

### 1.2 Placement

```
+----------------------------------------------------------+
|                       [⚪] Iris                           |
|  [TEAMS PANEL]                   [IRIS COMMAND SCREEN]   |
|  ┌────────────────┐                                      |
|  │ Session VoltAI │                                      |
|  │ ─────────────  │                                      |
|  │ 👑 Ludovic  🎤 │  ← parle en ce moment               |
|  │ 👤 Marie    🔇 │  ← mute                              |
|  │ 🟢 M. Dupont🔕 │  ← guest, écoute seulement           |
|  │ ─────────────  │                                      |
|  │ [+ Inviter]    │                                      |
|  └────────────────┘                                      |
|  [🎤 Parler]                          [🔴 Raccrocher]    |
+----------------------------------------------------------+
```

**Desktop** : panneau gauche fixe 240px, sticky, fond verre.
**Mobile** : barre horizontale compacte (avatars + indicateur "qui parle") en haut, tap pour déployer liste complète.

### 1.3 Composants du panneau

#### Header session
```
Session VoltAI          ●  3 participants
```
- Nom session : `--text-primary` 14px bold
- Compteur : `--text-tertiary` 12px + dot vert animé

#### Ligne participant
```
[AVATAR] Prénom     [🎤] [MUTE] [KICK]
```

Éléments :
- **Avatar** : cercle 32px, initiales en fond `rgba(139,116,247,0.2)`, texte violet
- **Indicateur qui parle** : anneau pulsant vert `#4ade80` autour de l'avatar quand actif
- **Badge rôle** :
  - 👑 Owner : couronne violet, 10px
  - 👤 Trusted : icône silhouette, cyan
  - 🟢 Guest : point vert, sans icône texte
- **Statut voix** : icône micro 14px. Vert = parle. Gris barré = mute.
- **Bouton MUTE** (owner uniquement) : visible au hover, icône 🔇, fond `rgba(255,183,77,0.12)`, pas de texte
- **Bouton KICK** (owner uniquement) : visible au hover, icône ✕, fond `rgba(255,107,123,0.12)`, pas de texte
- **Label validation requise** : si guest demande une action, badge ambre `⏳` sur sa ligne

#### Bouton Inviter
```
[+  Inviter]
```
- Fond : `rgba(139,116,247,0.1)`, border violet 1px, radius 100px
- Texte : "Inviter" 13px
- Action : appelle `POST /api/iris/session/{id}/invite` → affiche lien/QR

#### Mobile compact bar
```
[👑L] [👤M] [🟢D]    ● 3         [déployer ↓]
```
- Hauteur 44px, fond verre, sticky en haut
- Tap : slide down list complète, overlay fond `rgba(0,0,0,0.6)`

### 1.4 États visuels importants

| État | Visuel |
|---|---|
| Participant parle | Anneau vert pulsant 2s autour avatar |
| Participant mute | Micro gris barré + fond légèrement plus sombre |
| Guest demande action | Badge ⏳ ambre + ligne surbrillance douce |
| Action en attente validation | Bannière ambre discrète sous la liste : "Marie demande à envoyer un email — [Approuver] [Refuser]" |
| Participant déconnecté | Avatar grisé, opacity 0.4, "(hors ligne)" 11px |
| Session terminée | Overlay "Session terminée" sur le panneau |

### 1.5 Actions en attente — bannière owner

Quand un invité déclenche une action sensible (bloquée en attente) :

```
+──────────────────────────────────────────+
│  ⏳ Marie demande : envoyer email        │
│  client@bess.fr — "Compte-rendu BESS"   │
│                [Refuser]  [Approuver]   │
+──────────────────────────────────────────+
```

- Fond : `rgba(255,183,77,0.08)`
- Bordure : ambre `#FFB74D` 1px
- Bouton Approuver : vert `rgba(74,222,128,0.15)`, texte `#4ade80`
- Bouton Refuser : corail `rgba(255,107,123,0.1)`, texte `#FF6B7B`
- Timeout visuel : barre fine qui se réduit (10 min → auto-reject)

### 1.6 Intégration JavaScript (ce que Claude implémente)

Kimi spécifie seulement les comportements. Claude code.

**Polling participants** : `GET /api/iris/session/{id}/status` toutes les 5s
→ met à jour la liste sans recharger la page

**Mute/Kick** :
- Mute : `POST /api/iris/session/{id}/revoke` n'est pas mute — à prévoir comme signal WS `{type:"mute", participant_id}`
- Kick : `POST /api/iris/session/{id}/revoke` avec `participant_id`

**Approbation** :
- `GET /api/iris/session/{id}/pending` toutes les 3s (si owner)
- Approuver : `POST /api/iris/session/{id}/approve/{action_id}`
- Refuser : `POST /api/iris/session/{id}/reject/{action_id}`

---

## Chantier 2 — Light / Dark Mode

### 2.1 Principe

Deux palettes complètes. Pas d'inversion CSS. Pas de `filter: invert()`.
Chaque variable a une valeur dark ET une valeur light.

**Critère qualité** : le thème clair doit ressembler à une interface MacOS/Linear/Notion premium.
Fond blanc cassé, typographie sombre, accents violets plus saturés. Pas de fond blanc pur.

### 2.2 Variables CSS — les deux thèmes

```css
/* ── DARK (défaut) ── */
:root,
[data-theme="dark"] {
  --bg-base:          #000609;
  --bg-panel:         rgba(10, 10, 15, 0.75);
  --bg-panel-solid:   #0a0a0f;
  --bg-hover:         rgba(255, 255, 255, 0.03);
  --bg-active:        rgba(139, 116, 247, 0.08);
  --border-subtle:    rgba(255, 255, 255, 0.05);
  --border-accent:    rgba(139, 116, 247, 0.2);
  --text-primary:     rgba(255, 255, 255, 0.92);
  --text-secondary:   rgba(255, 255, 255, 0.55);
  --text-tertiary:    rgba(255, 255, 255, 0.28);
  --text-title:       #ffffff;
  --iris-violet:      #8B74F7;
  --iris-violet-dim:  rgba(139, 116, 247, 0.15);
  --iris-cyan:        #40E0FF;
  --iris-amber:       #FFB74D;
  --iris-coral:       #FF6B7B;
  --iris-green:       #4ade80;
  --orb-glow:         rgba(139, 116, 247, 0.25);
  --shadow-panel:     0 24px 80px rgba(0,0,0,0.5);
  --backdrop-blur:    blur(40px) saturate(180%);
}

/* ── LIGHT ── */
[data-theme="light"] {
  --bg-base:          #f5f4f8;
  --bg-panel:         rgba(255, 255, 255, 0.88);
  --bg-panel-solid:   #ffffff;
  --bg-hover:         rgba(139, 116, 247, 0.04);
  --bg-active:        rgba(139, 116, 247, 0.08);
  --border-subtle:    rgba(0, 0, 0, 0.07);
  --border-accent:    rgba(139, 116, 247, 0.3);
  --text-primary:     rgba(15, 10, 30, 0.92);
  --text-secondary:   rgba(15, 10, 30, 0.52);
  --text-tertiary:    rgba(15, 10, 30, 0.28);
  --text-title:       #0f0a1e;
  --iris-violet:      #6d55e8;
  --iris-violet-dim:  rgba(109, 85, 232, 0.1);
  --iris-cyan:        #0099bb;
  --iris-amber:       #d97706;
  --iris-coral:       #e53e3e;
  --iris-green:       #16a34a;
  --orb-glow:         rgba(109, 85, 232, 0.2);
  --shadow-panel:     0 8px 40px rgba(0,0,0,0.12), 0 1px 3px rgba(0,0,0,0.08);
  --backdrop-blur:    blur(20px) saturate(160%);
}
```

### 2.3 Toggle visuel

Bouton discret dans la barre basse, à côté du bouton raccrocher :

```
[🌙]  ←  dark   /   [☀]  ← light
```

- 32px × 32px, border-radius 50%
- Dark : fond `rgba(255,255,255,0.06)`, icône 🌙 gris clair
- Light : fond `rgba(0,0,0,0.06)`, icône ☀ sombre
- Transition `background 0.3s, color 0.3s`
- Au clic : `document.documentElement.setAttribute('data-theme', ...)` + `localStorage.setItem('iris-theme', ...)`
- Au chargement : lire `localStorage.getItem('iris-theme')` ou `prefers-color-scheme`

### 2.4 Règles par composant en mode light

| Composant | Adaptation obligatoire |
|---|---|
| Fond page | `--bg-base` — violet très pale, pas blanc pur |
| Panneaux verre | `--bg-panel` — blanc translucide, backdrop-filter réduit |
| Texte | `--text-primary` sombre, contraste WCAG AA minimum |
| Orbe | Gradient violet → cyan, moins lumineux que dark |
| Status Rail | Fond blanc, texte sombre, accents violet plus saturé |
| Data Board | Lignes alternées gris très clair, header violet clair |
| Chart.js | Couleurs adaptées : violet `#6d55e8`, cyan `#0099bb`, fond blanc |
| Timeline | Trait vertical violet, points blancs bordure violette |
| Teams Panel | Fond blanc, avatars fond violet pâle |
| Texte transcript | Fond blanc cassé, bulles légèrement teintées |

### 2.5 Interdits en mode light

- Pas de `filter: invert()` global
- Pas de fond blanc pur `#ffffff` sur le fond de page
- Pas d'icônes qui restent blanc (invisible sur fond clair)
- Pas de glow néon en mode clair (trop agressif)
- Pas de transitions instantanées entre thèmes — `transition: background 0.3s, color 0.3s, border-color 0.3s`

---

## Chantier 3 — 8 nouveaux render_type : specs visuelles

### 3.1 kanban_board

**Déclencheur** : "kanban", "tâches", "à faire", "en cours", "colonnes"

```
+──────────────────────────────────────────────────────+
│  KANBAN                                   [+ Tâche]  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌────────┐ │
│  │ À FAIRE  │  │ EN COURS │  │ BLOQUÉ   │ │ TERMINÉ│ │
│  │ 3 items  │  │ 2 items  │  │ 1 item   │ │ 5 items│ │
│  │          │  │          │  │          │ │        │ │
│  │ [carte]  │  │ [carte]  │  │ [carte]  │ │[carte] │ │
│  │ [carte]  │  │ [carte]  │  │          │ │[carte] │ │
│  │ [carte]  │  │          │  │          │ │[carte] │ │
│  └──────────┘  └──────────┘  └──────────┘ └────────┘ │
+──────────────────────────────────────────────────────+
```

Spec :
- 4 colonnes : "À faire" (neutre), "En cours" (cyan), "Bloqué" (corail), "Terminé" (vert)
- Couleur header colonne = accent de l'état
- Cartes : fond `--bg-panel`, radius 12px, padding 12px, titre + tag optionnel
- Scroll vertical par colonne indépendant
- Mobile : swipe horizontal entre colonnes

### 3.2 contact_board

**Déclencheur** : "contact", "fiche", "qui est", "appelle", "envoie à", prénom + nom reconnu

```
+──────────────────────────────────────────+
│  CONTACT                                 │
│  ┌──────────────────────────────────┐    │
│  │  [M]   Marie Dupont              │    │
│  │        Confiance : ★★★★☆         │    │
│  │        Dernière interaction : 3j │    │
│  │  📞 +33 6 12 34 56 78            │    │
│  │  ✉  marie@bess.fr               │    │
│  │  🏢 BESS — Ingénieure projet    │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Historique récent                       │
│  • SMS — "Réunion confirmée" — 28/05    │
│  • Appel — 12 min — 20/05              │
│                                          │
│  [📞 Appeler]  [✉ Email]  [💬 SMS]     │
+──────────────────────────────────────────+
```

Spec :
- Avatar : cercle 48px, initiales, fond violet pâle
- Étoiles confiance : violet rempli / gris vide
- Actions : boutons pill, chaque action = `requires_confirmation: true`
- Historique : liste 3 derniers items max, plus ancien en bas

### 3.3 map_board

**Déclencheur** : "adresse", "où est", "trajet", "itinéraire", "localisation"

```
+──────────────────────────────────────────+
│  LOCALISATION                            │
│  ┌──────────────────────────────────┐    │
│  │  [CARTE STATIQUE ou placeholder] │    │
│  │  📍 12 rue de la Paix, Paris     │    │
│  │                                  │    │
│  │  ≈ 2,4 km — 8 min à pied        │    │
│  │    12 min en voiture             │    │
│  └──────────────────────────────────┘    │
│                                          │
│  [Ouvrir dans Maps]  [Copier adresse]   │
+──────────────────────────────────────────+
```

Spec :
- Carte statique : image `maps.googleapis.com/maps/api/staticmap` ou placeholder SVG avec pin
- Si API Maps absente : placeholder fond sombre avec grille géo + pin violet
- Distance + durée : badges pill, fond verre
- Bouton "Ouvrir dans Maps" : lien externe `maps.google.com/?q=...`

### 3.4 decision_board

**Déclencheur** : "compare", "quelle option", "avantages", "inconvénients", "lequel choisir", "pour contre"

```
+──────────────────────────────────────────────────────+
│  DÉCISION                                            │
│                                                      │
│  ┌─────────────────┐     ┌─────────────────┐        │
│  │   Option A      │     │   Option B      │        │
│  │   EDF           │     │   Engie         │        │
│  │  ─────────────  │     │  ─────────────  │        │
│  │  ✓ 89€/mois    │     │  ✓ 95€/mois    │        │
│  │  ✓ Fibre incl. │     │  ✗ Fibre en +  │        │
│  │  ✗ Engagement  │     │  ✓ Sans engag.  │        │
│  │  ✓ App mobile  │     │  ✓ App mobile  │        │
│  └─────────────────┘     └─────────────────┘        │
│                                                      │
│  ★ Recommandation Iris : EDF — moins cher avec fibre │
│                                                      │
│  [Choisir EDF]                    [Choisir Engie]   │
+──────────────────────────────────────────────────────+
```

Spec :
- 2 colonnes côte à côte (ou 3 si triple comparaison)
- Colonne recommandée : bordure violette 2px + badge "★ Recommandé"
- Critères : ✓ vert / ✗ corail — pas de texte "oui/non"
- Bannière recommandation Iris : fond `rgba(139,116,247,0.06)`, texte violet

### 3.5 budget_board

**Déclencheur** : "budget", "dépenses", "combien j'ai dépensé", "mes finances", "solde"

```
+──────────────────────────────────────────+
│  BUDGET — Juin 2026                      │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │  Solde estimé        1 240 €     │    │
│  │  Dépenses ce mois      892 €     │    │
│  │  Budget restant        348 €  ⚠  │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Top dépenses                            │
│  Loyer          ████████████  650 €  73% │
│  Énergie        ███           89 €    10%│
│  Alimentation   ██            65 €     7%│
│  Autres         █             88 €    10%│
│                                          │
│  [Voir détail]  [Alertes budget]         │
+──────────────────────────────────────────+
```

Spec :
- KPI top : 3 lignes, fond légèrement teinté, chiffres `font-variant-numeric: tabular-nums`
- Barres : `div` avec `width: X%`, fond violet progressif → cyan pour les grosses catégories
- Alerte si budget restant < 20% : fond corail teinté + badge ⚠
- Mobile : barres empilées pleine largeur

### 3.6 meeting_board

**Déclencheur** : "réunion", "compte-rendu", "ordre du jour", "PV", "note de réunion"

```
+──────────────────────────────────────────+
│  RÉUNION — Session VoltAI               │
│  02/06/2026 — 14h30                      │
│                                          │
│  Participants                            │
│  👑 Ludovic  👤 Marie  🟢 M. Dupont     │
│                                          │
│  Ordre du jour                           │
│  [✓] Bilan BESS Q1                      │
│  [ ] Budget 2027                         │
│  [ ] Recrutement                         │
│                                          │
│  Décisions                               │
│  • Budget approuvé : 240 000€            │
│  • Prochain point : 15/06               │
│                                          │
│  [Exporter CR]  [Envoyer aux participants]│
+──────────────────────────────────────────+
```

Spec :
- Participants : avatars inline 24px, tooltips au hover
- Ordre du jour : checkboxes interactives (mais validation avant sauvegarde)
- Section Décisions : fond légèrement plus clair, icône gavel
- Bouton "Envoyer" : `requires_confirmation: true`

### 3.7 media_board

**Déclencheur** : "photo", "image", "fichier", "document joint", "pièce jointe", "capture"

```
+──────────────────────────────────────────+
│  FICHIERS (3)                            │
│                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ [📄]    │  │ [🖼]    │  │ [📊]    │  │
│  │ CR.pdf  │  │ Plan.png│  │ Budget  │  │
│  │ 245 Ko  │  │ 1,2 Mo  │  │ .xlsx   │  │
│  └─────────┘  └─────────┘  └─────────┘  │
│                                          │
│  [Tout télécharger]                      │
+──────────────────────────────────────────+
```

Spec :
- Grille 3 colonnes (2 sur mobile)
- Icône type fichier : PDF rouge, image cyan, Excel vert, autres violet
- Nom fichier tronqué avec ellipsis
- Taille fichier : `--text-tertiary` 11px
- Hover carte : fond légèrement plus clair + bouton "Ouvrir"

### 3.8 form_board

**Déclencheur** : "formulaire", "remplis", "complète", "besoin de tes infos"

```
+──────────────────────────────────────────+
│  FORMULAIRE — Demande CAF                │
│                                          │
│  Nom *                                   │
│  [________________________]              │
│                                          │
│  Numéro allocataire *                    │
│  [________________________]              │
│                                          │
│  Motif                                   │
│  [ ] Changement de situation             │
│  [ ] Demande d'aide                      │
│  [ ] Autre                               │
│                                          │
│  [Remplir automatiquement]  [Envoyer]   │
+──────────────────────────────────────────+
```

Spec :
- Inputs : fond `--bg-hover`, bordure `--border-subtle`, radius 8px, padding 10px 14px
- Focus : bordure violet 1px + `box-shadow 0 0 0 3px rgba(139,116,247,0.12)`
- Champs obligatoires : `*` violet après label
- Bouton "Remplir auto" : pré-rempli depuis le profil, fond violet pâle
- Bouton "Envoyer" : `requires_confirmation: true`, fond violet plein

---

## Format de livraison attendu

Kimi livre dans ce fichier (en réponse) :

1. Section CSS complète pour les variables dark/light
2. HTML structure de chaque nouveau render_type (skeleton, sans JS)
3. CSS classes pour chaque composant Teams overlay
4. Règles responsive mobile pour chaque composant
5. Toutes les interdictions graphiques propres à chaque type

**Ne pas** : modifier luna_web.py, web_voice_bridge.py, session_manager.py
**Ne pas** : déployer quoi que ce soit
**Ne pas** : décider du comportement JavaScript — c'est Claude

Claude code après réception du livrable Kimi.

---

*Lead technique : Claude — 2 juin 2026*
*Domaine Kimi : UX/UI uniquement*
