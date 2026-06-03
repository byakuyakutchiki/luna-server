# KIMI — UX Iris Team / Telework Operating System (Objectif 022)

> Agent : Kimi  
> Objectif : 022  
> Niveau : 0  
> Date : 2026-06-03  
> Statut : livré — attente DeepSeek technique + arbitrage Codex avant implémentation

---

## 1. Vision UX fondatrice

Iris ne « discute » pas. Elle **travaille**. L'utilisateur doit sentir qu'il pilote un centre de commande, pas qu'il chatte avec un bot.

**Principe immuable :**  
> Chaque interaction produit un artefact visuel — tableau, brouillon, graphique, planning, compte-rendu — jamais un pavé texte brut.

**Différence visuelle Luna / Iris (renforcée)**

| Aspect | Luna | Iris |
|---|---|---|
| Couleur dominante | Violet Luna `#8B74F7` | Indigo Iris `#5B6EF5` |
| Texture | Bulle conversationnelle, ronde, chaleureuse | Panneau de verre, bord droit, technique |
| Animation | Flottante, légère, respiration | Construite, stagger, assemblage de blocs |
| Ton | « Je t'écoute » | « Je prépare / Voici / Valide » |
| Sortie | Parole, conseil | Rendu visuel, action, document |

---

## 2. Architecture d'écran

### 2.1 Desktop (≥1024px)

```
┌─────────────────────────────────────────────────────────────┐
│  Header Luna (fixe, 56px) — violet #8B74F7                 │
├──────────────────────────┬──────────────────────────────────┤
│                          │                                  │
│  Zone Audio Iris         │  IRIS COMMAND SCREEN             │
│  (orbe + transcript)     │  (panneau de verre, 520px min)   │
│                          │                                  │
│  ┌──────┐                │  ┌────────────────────────────┐  │
│  │  🎙️  │  "Prépare un   │  │  STATUS RAIL               │  │
│  │ Iris │   business     │  │  ● Analyse → Structuration │  │
│  └──────┘   plan"        │  │  → Préparation → Prêt      │  │
│                          │  └────────────────────────────┘  │
│  Transcript (1 ligne     │  ┌────────────────────────────┐  │
│  discrète, centrée)      │  │  RENDER PRINCIPAL          │  │
│                          │  │  (data_board, chart,       │  │
│                          │  │   document_draft, etc.)    │  │
│                          │  └────────────────────────────┘  │
│                          │  ┌────────────────────────────┐  │
│                          │  │  ACTIONS / VALIDATION      │  │
│                          │  │  [Modifier] [Télécharger]  │  │
│                          │  │  [✓ Valider et exécuter]   │  │
│                          │  └────────────────────────────┘  │
│                          │                                  │
├──────────────────────────┴──────────────────────────────────┤
│  Footer navigation (mobile uniquement)                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Mobile (<768px)

```
┌─────────────────────────────┐
│  Header Luna (fixe, 48px)  │
├─────────────────────────────┤
│                             │
│  Zone Audio Iris            │
│  (orbe 64px, centré-haut)  │
│                             │
│  STATUS RAIL (sticky,      │
│  32px, compact)            │
│                             │
│  ┌───────────────────────┐  │
│  │  RENDER PRINCIPAL     │  │
│  │  (pleine largeur,     │  │
│  │   max 55vh, scroll)   │  │
│  └───────────────────────┘  │
│                             │
│  [Actions sticky bottom]   │
│                             │
└─────────────────────────────┘
```

**Règles de layout immuables :**
- Command Screen ne superpose jamais l'orbe audio
- Mobile : panneau principal slide-up depuis le bas, pas overlay opaque
- Desktop : Command Screen = colonne droite fixe, jamais modale centrée
- Transcript utilisateur = 1 ligne max, centrée, opacité 0.6
- Transcript Iris = **caché** (ne pas remplir l'écran de parole)

---

## 3. Design system — Tokens

### Couleurs

| Token | Clair | Sombre | Usage |
|---|---|---|---|
| `--bg-primary` | `#F5F7FA` | `#0A0A0F` | Fond global |
| `--bg-panel` | `rgba(255,255,255,0.72)` | `rgba(20,20,28,0.72)` | Panneau verre |
| `--bg-panel-solid` | `#FFFFFF` | `#14141C` | Fond panneau fallback |
| `--accent-iris` | `#5B6EF5` | `#7B8FFF` | Accent Iris (indigo) |
| `--accent-luna` | `#8B74F7` | `#A78BFA` | Accent Luna (violet) |
| `--status-analyse` | `#F59E0B` | `#FBBF24` | En cours d'analyse |
| `--status-struct` | `#8B5CF6` | `#A78BFA` | Structuration |
| `--status-prep` | `#3B82F6` | `#60A5FA` | Préparation |
| `--status-ready` | `#10B981` | `#34D399` | Prêt |
| `--status-warn` | `#F59E0B` | `#FBBF24` | Validation requise |
| `--status-error` | `#EF4444` | `#F87171` | Erreur / blocage |
| `--text-primary` | `#111827` | `#F3F4F6` | Texte principal |
| `--text-secondary` | `#6B7280` | `#9CA3AF` | Texte secondaire |
| `--border-glass` | `rgba(255,255,255,0.24)` | `rgba(255,255,255,0.08)` | Bordure verre |

### Typographie

- **Famille** : `Inter, system-ui, sans-serif`
- **Titre panneau** : 18px / 600 / tracking -0.01
- **Sous-titre** : 14px / 500 / `--text-secondary`
- **Données tableau** : 13px / 400 / `tabular-nums`
- **Badge/Tag** : 11px / 600 / uppercase / letter-spacing 0.04em
- **Bouton principal** : 14px / 600
- **Bouton secondaire** : 14px / 500

### Verre (Glassmorphism)

```css
.ics-panel {
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(40px) saturate(140%);
  -webkit-backdrop-filter: blur(40px) saturate(140%);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
}
```

Mode sombre : `background: rgba(20, 20, 28, 0.72)`, `border: rgba(255,255,255,0.08)`

### Ombre et élévation

| Niveau | Usage | Valeur |
|---|---|---|
| 1 | Carte interne | `0 1px 3px rgba(0,0,0,0.06)` |
| 2 | Panneau | `0 8px 32px rgba(0,0,0,0.08)` |
| 3 | Modale / drawer | `0 16px 48px rgba(0,0,0,0.12)` |
| 4 | Orbe actif | `0 0 24px rgba(91, 110, 245, 0.4)` |

---

## 4. Les 10 familles de capacités — UX par famille

### 4.1 Assistant de réunion

**Trigger oraux :**  
"Iris, prends les notes", "Sors les décisions", "Qui doit faire quoi ?"

**Render type principal :** `meeting_board`

**Structure visuelle :**
```
┌─────────────────────────────┐
│  📋 Réunion en cours        │
│  14:32 — 3 participants     │
├─────────────────────────────┤
│  DÉCISIONS                  │
│  ✓ Budget validé à 15K€    │
│  ✓ Deadline fixée au 15/06 │
│  ○ Nom du prestataire ?    │  ← missing_info
├─────────────────────────────┤
│  ACTIONS                    │
│  □ Lucas — devis technique │
│  □ Sarah — contrat MSA     │
│  □ Moi — validation finale │
├─────────────────────────────┤
│  SUJETS OUVERTS             │
│  🔶 Budget non décidé      │
│  🔶 Échéance non confirmée │
├─────────────────────────────┤
│  [Générer le CR] [Envoyer] │
└─────────────────────────────┘
```

**États temps réel :**
1. `analyse` — "Analyse de la réunion..." (pulse orange)
2. `struct` — "Structuration des décisions..." (pulse violet)
3. `prep` — "Préparation du compte-rendu..." (pulse bleu)
4. `ready` — "Compte-rendu prêt — 5 décisions, 3 actions" (vert fixe)

**Rendus secondaires :** `action_board`, `decision_board`, `document_draft`, `status_rail`

**Garde-fou UX :**
- Aucun envoi de CR sans bouton `[Envoyer après validation]` cliqué
- `missing_info` en jaune, jamais caché
- Actions non cochables par Iris seule — utilisateur coche

---

### 4.2 Assistant télétravail individuel

**Trigger oraux :**  
"Organise ma journée", "Quelles sont mes priorités ?", "Où on en est sur le projet X ?"

**Render type principal :** `kanban_board`

**Structure visuelle :**
```
┌─────────────────────────────┐
│  📌 Ma journée — 3 juin    │
├─────────────────────────────┤
│  🔴 URGENT      🟡 EN COURS  │
│  ────────────   ──────────── │
│  • Devis MSA    • Appel      │
│  • Facture      client       │
│                               │
│  🟢 FAIBLE    🔵 PLANIFIÉ    │
│  ────────────   ──────────── │
│  • Veille       • Réunion    │
│    hebdo        équipe       │
├─────────────────────────────┤
│  [+] Ajouter  [Réorganiser] │
└─────────────────────────────┘
```

**Rendus secondaires :** `roadmap`, `action_board`, `status_rail`, `document_insight`

**Garde-fou UX :**
- Drag & drop sur desktop, tap-hold sur mobile
- Couleurs de priorité fixes : rouge/jaune/vert/ble
- Roadmap = timeline horizontale avec milestones cliquables

---

### 4.3 Assistant équipe / projet

**Trigger oraux :**  
"Crée un espace pour l'équipe", "Invite Lucas", "Qui est responsable du budget ?"

**Render type principal :** `session_panel`

**Structure visuelle :**
```
┌─────────────────────────────┐
│  👥 Session : Projet MSA   │
│  Owner : Ludovic            │
├─────────────────────────────┤
│  PARTICIPANTS               │
│  ● Ludovic (owner) 🎙️      │
│  ○ Lucas (invité)          │
│  ○ Sarah (invitée)         │
├─────────────────────────────┤
│  RÔLES & RESPONSABILITÉS    │
│  Lucas → Technique          │
│  Sarah → Juridique          │
├─────────────────────────────┤
│  ACTIONS EN DIRECT          │
│  □ Devis — Lucas            │
│  □ Contrat — Sarah          │
├─────────────────────────────┤
│  [Inviter] [Paramètres]    │
│  ⚠️ Actions sensibles =    │
│     validation owner        │
└─────────────────────────────┘
```

**Garde-fou UX :**
- Owner = seul à pouvoir mute/kick
- Invité demande action sensible → badge `⏳ En attente de validation`
- Bouton `[Valider l'action]` visible uniquement pour owner

---

### 4.4 Assistant dirigeant

**Trigger oraux :**  
"Prépare un business plan", "Compare ces deux fournisseurs", "Où on en est sur les KPI ?"

**Render types principaux :** `kpi_cards`, `chart`, `budget_board`, `comparison`, `decision_board`, `document_draft`

**Structure KPI cards :**
```
┌─────────────────────────────┐
│  📊 Tableau de bord MSA    │
├─────────────────────────────┤
│  ┌────────┐ ┌────────┐     │
│  │ CA     │ │ Marge  │     │
│  │ 45K€   │ │ 32%    │     │
│  │ ↑ 12%  │ │ ↑ 5%   │     │
│  └────────┘ └────────┘     │
│  ┌────────┐ ┌────────┐     │
│  │ Clients│ │ Délai  │     │
│  │ 12     │ │ 4.2j   │     │
│  │ ↑ 3    │ │ ↓ 0.5j │     │
│  └────────┘ └────────┘     │
├─────────────────────────────┤
│  [Voir le graphique]        │
└─────────────────────────────┘
```

**Structure Comparison :**
```
┌─────────────────────────────┐
│  ⚖️ Comparaison Fournisseurs│
├──────┬──────────┬───────────┤
│      │ Fourn. A │ Fourn. B  │
├──────┼──────────┼───────────┤
│ Prix │ 12K€     │ 10K€      │
│ Délai│ 3 sem.   │ 4 sem.    │
│ Note │ ⭐⭐⭐⭐    │ ⭐⭐⭐      │
│ RGPD │ ✓        │ ✗         │
├──────┴──────────┴───────────┤
│  💡 Recommandation :        │
│     Fourn. A — meilleur     │
│     rapport qualité/délai   │
│  [Valider ce choix]         │
└─────────────────────────────┘
```

**Garde-fou UX :**
- `missing_info` affiché si données incomplètes
- Bouton `[Valider]` jaune, jamais vert, tant que non confirmé
- Budget = toujours en €, toujours avec source

---

### 4.5 Assistant documents

**Trigger oraux :**  
"Analyse ce contrat", "Compare ces deux devis", "Où est la facture du 15 mai ?"

**Render types principaux :** `document_insight`, `document_draft`, `comparison`, `timeline`, `action_board`

**Structure Document Insight :**
```
┌─────────────────────────────┐
│  📄 Contrat_MSA_v2.pdf      │
│  12 pages — 2.4 MB          │
├─────────────────────────────┤
│  RISQUES DÉTECTÉS           │
│  🔴 Clause de non-concurrence │
│      trop large (§4.2)      │
│  🟡 Délai de paiement 60j   │
│      (préférable : 30j)     │
│  🟢 RGPD mentionné          │
├─────────────────────────────┤
│  DATES CLÉS                 │
│  • Signature : 15/06/2026   │
│  • Révision : 15/06/2027    │
├─────────────────────────────┤
│  [Télécharger l'analyse]   │
│  [Demander une modification]│
└─────────────────────────────┘
```

**Garde-fou UX :**
- Suppression = double confirmation + bouton rouge
- Consentement RGPD affiché avant tout upload
- Documents classés par projet/source/date

---

### 4.6 Assistant communication

**Trigger oraux :**  
"Prépare un SMS à Lucas", "Rédige un mail de relance", "Envoie une invitation réunion"

**Render types principaux :** `action_board`, `document_draft`, `contact_board`, `status_rail`

**Structure Document Draft (email) :**
```
┌─────────────────────────────┐
│  ✉️ Brouillon email         │
│  À : Lucas <lucas@...>      │
│  Objet : Relance devis MSA  │
├─────────────────────────────┤
│  Bonjour Lucas,             │
│                             │
│  Suite à notre échange...   │
│  [corps du message]         │
│                             │
│  Cordialement,              │
│  Ludovic                    │
├─────────────────────────────┤
│  ⏰ Horaire : 09:15 — OK    │
│  📵 Pas un numéro d'urgence │
├─────────────────────────────┤
│  [Modifier]                 │
│  [✓ Valider et envoyer]     │
│  ⚠️ Cette action sera       │
│     journalisée             │
└─────────────────────────────┘
```

**Garde-fou UX :**
- Bouton envoi = jaune `validation_required`, jamais vert
- Horaires interdits (22h-7h) = blocage grisé + message
- Numéros d'urgence = blocage rouge + alerte
- Journal visible dans `status_rail`

---

### 4.7 Assistant recherche externe

**Trigger oraux :**  
"Cherche Base Legacy sur le web", "Compare les prix de X", "Fais-moi une veille sur Y"

**Render type principal :** `research_board` (à créer si absent)

**Structure Research Board :**
```
┌─────────────────────────────┐
│  🔍 Recherche : Base Legacy │
│  5 sources trouvées         │
├─────────────────────────────┤
│  SOURCES                    │
│  1. siteofficiel.fr         │
│     « Base Legacy est... »  │
│  2. linkedin.com/...        │
│     « Fondateur : ... »     │
│  3. journaldugeek.com       │
│     « Test complet... »     │
├─────────────────────────────┤
│  SYNTHÈSE                   │
│  Base Legacy = outil de     │
│  gestion de patrimoine...   │
├─────────────────────────────┤
│  LIMITES                    │
│  ⚠️ Dernière source date   │
│     de 2024                 │
├─────────────────────────────┤
│  [Exporter] [Creuser]      │
└─────────────────────────────┘
```

**Fallback :** `context_panel` avec sources listées

**Garde-fou UX :**
- Sources toujours visibles, jamais cachées
- Limites affichées en bas, jamais en petit texte
- Pas de « Je n'ai pas accès » si l'outil est branché

---

### 4.8 Assistant vision

**Trigger oraux :**  
"Qu'est-ce que tu vois ?", "Lis ce document", "Il y a quelqu'un ?"

**Render types principaux :** `context_panel`, `document_insight`, `status_rail`, `media_board`

**Structure Context Panel (vision) :**
```
┌─────────────────────────────┐
│  👁️ Vision                  │
├─────────────────────────────┤
│  ● Active — caméra frontale │
│  📷 Capture traitée         │
├─────────────────────────────┤
│  DESCRIPTION                │
│  « Je vois un bureau avec   │
│    un ordinateur portable,  │
│    une tasse et des         │
│    documents. »             │
├─────────────────────────────┤
│  OBJETS DÉTECTÉS            │
│  💻 Ordinateur  📄 Documents│
│  ☕ Tasse      📱 Téléphone │
├─────────────────────────────┤
│  [Décrire à nouveau]        │
└─────────────────────────────┘
```

**État inactif (honête) :**
```
┌─────────────────────────────┐
│  👁️ Vision                  │
├─────────────────────────────┤
│  ○ Inactive                 │
│  Cause : caméra non         │
│  autorisée ou mode web      │
├─────────────────────────────┤
│  [Activer la caméra]        │
└─────────────────────────────┘
```

**Garde-fou UX :**
- Jamais « Iris voit » sans description réelle
- Vision inactive = statut clair + cause + action
- Objets détectés = badges, pas texte brut

---

### 4.9 Assistant conformité / garde-fous

**Trigger implicite (toujours actif)**

**Render types principaux :** `action_board`, `status_rail`, `missing_info`

**Structure Action Board (validation requise) :**
```
┌─────────────────────────────┐
│  ⚠️ Action sensible détectée│
├─────────────────────────────┤
│  Type : Envoi de SMS        │
│  Destinataire : 06 12 34..  │
│  Contenu : « Relance devis »│
├─────────────────────────────┤
│  VÉRIFICATIONS              │
│  ✓ Horaire OK (09:15)       │
│  ✓ Pas un numéro d'urgence  │
│  ✓ Quota SMS restant : 47   │
│  ✓ Consentement RGPD OK     │
├─────────────────────────────┤
│  [✓ Confirmer l'envoi]      │
│  [✗ Annuler]                │
└─────────────────────────────┘
```

**Garde-fou UX :**
- Toute action sensible = écran complet de validation
- Pas de mini-toast ou de checkbox seule
- Annulation = retour à l'état précédent, pas écran vide
- Journal de toute action visible dans `status_rail`

---

### 4.10 Assistant Jarvis / centre de commande

**Trigger oraux :**  
"Prépare-moi un dossier complet sur X", "Surveille ce sujet", "Montre-moi où on en est"

**Render types principaux :** `status_rail`, `roadmap`, `kanban_board`, `meeting_board`, `document_draft`, `research_board`

**Structure Status Rail (mode Jarvis — toujours visible) :**
```
┌─────────────────────────────┐
│  🎯 Mission : Dossier MSA  │
├─────────────────────────────┤
│  ● Étape 1/5 — Recherche    │
│    web en cours...          │
│    [████████░░░░░░░░░░] 40% │
│  ○ Étape 2 — Documents      │
│  ○ Étape 3 — Analyse        │
│  ○ Étape 4 — Synthèse       │
│  ○ Étape 5 — Livrable       │
├─────────────────────────────┤
│  ⏱️ Estimation : 2 min      │
│  [Annuler la mission]       │
└─────────────────────────────┘
```

**États temps réel (séquence obligatoire) :**
1. `Iris analyse...` — pulse orange
2. `Iris cherche...` — pulse violet
3. `Iris structure...` — pulse bleu
4. `Iris projette...` — pulse indigo
5. `Prêt — modifier / télécharger / sauvegarder / envoyer après validation` — vert fixe

**Interdictions absolues :**
- Rester silencieux > 10s sans feedback
- Remplir l'écran de parole Iris
- Dire « patiente » sans barre/état visible
- Présenter un faux résultat comme terminé

---

## 5. Composants transversaux

### 5.1 Status Rail

Présent sur **tous** les rendus. 7 états visuels :

| État | Couleur | Animation | Texte |
|---|---|---|---|
| `idle` | Gris | — | Iris à l'écoute |
| `analyse` | Orange | Pulse 1.5s | Analyse en cours... |
| `search` | Violet | Pulse 1.5s | Recherche... |
| `struct` | Bleu | Pulse 1.5s | Structuration... |
| `prep` | Indigo | Pulse 1.5s | Préparation... |
| `ready` | Vert | Fixe + glow | Prêt |
| `warn` | Jaune | Pulse 1s | Validation requise |
| `error` | Rouge | Shake 0.4s | Erreur — [Détails] |

**Mobile :** rail compact 32px, icône + texte court  
**Desktop :** rail complet 40px, icône + texte + micro-barre de progression

### 5.2 Transcript

- **Utilisateur** : 1 ligne max, centrée, opacité 0.6, 13px
- **Iris** : **caché** — ne pas afficher les longs discours
- **System** : uniquement erreurs ou confirmations courtes

### 5.3 Orbe audio

- Desktop : 80px, centre-haut gauche
- Mobile : 64px, centre-haut
- 5 états visuels : idle (gris), écoute (pulse vert), réflexion (pulse violet), parole (pulse indigo), erreur (pulse rouge)

### 5.4 Actions sticky

Boutons toujours visibles en bas du panneau :
- `[Modifier]` — secondaire, gris
- `[Télécharger]` — secondaire, gris
- `[✓ Valider et exécuter]` — primaire, vert (jaune si validation requise)

Mobile : boutons pleine largeur, empilés verticalement

---

## 6. Mode clair / sombre

### Détection
- Priorité au `prefers-color-scheme`
- Toggle manuel dans paramètres (persisté localStorage)
- Transition : `transition: background 0.3s ease, color 0.3s ease`

### Adaptations sombre
- Fond : `#0A0A0F` (noir OLED)
- Panneau : `rgba(20, 20, 28, 0.72)` + blur
- Texte : `#F3F4F6` (presque blanc)
- Accent Iris : `#7B8FFF` (plus lumineux)
- Bordures : `rgba(255,255,255,0.08)`
- Ombres : moins prononcées (pas de noir sur noir)

---

## 7. Animations et micro-interactions

| Élément | Animation | Durée | Easing |
|---|---|---|---|
| Panneau apparition | scale(0.96→1) + fade | 300ms | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Carte interne | translateY(8px→0) + fade | 200ms | `ease-out` |
| Stagger contenu | délai 60ms par item | — | — |
| Orbe écoute | scale(1→1.08) pulse | 1.5s | `ease-in-out` |
| Status change | translateX(-4px→0) + couleur | 200ms | `ease` |
| Bouton hover | translateY(-1px) + shadow | 150ms | `ease` |
| Erreur | shake X ±4px | 400ms | `ease` |
| Mode toggle | background cross-fade | 300ms | `ease` |

---

## 8. Mobile-first — Règles spécifiques

- **Orbe** : 64px minimum, jamais caché
- **Command Screen** : pleine largeur, max 55vh, scroll interne
- **Status Rail** : sticky top sous header, 32px compact
- **Boutons** : pleine largeur, empilés, 48px hauteur min
- **Tableaux** : scroll horizontal obligatoire, colonnes figées
- **Cartes** : empilées verticalement, jamais côte à côte
- **Touch target** : 44px minimum
- **Font size** : 16px minimum sur inputs (évite zoom iOS)

---

## 9. Checklist de validation

Avant de déclarer un render_type « livré » :

- [ ] Le render_type a un payload JSON défini
- [ ] Le handler frontend existe et produit du HTML (pas de markdown)
- [ ] Le style respecte les tokens (pas de couleur hardcodée)
- [ ] Mobile : testé en 375px minimum
- [ ] Mode sombre : testé
- [ ] Animation : apparition fluide, pas de flash
- [ ] Actions sensibles : bouton validation jaune, jamais vert direct
- [ ] Transcript : utilisateur visible, Iris caché
- [ ] Status Rail : 7 états implémentés
- [ ] 10s timeout : warning visible si blocage
- [ ] Preuve terrain : capture écran ou log de test

---

## 10. Livrables attendus pour implémentation

### Phase 1 (V1 non dangereuse)
1. `render_type` : `meeting_board`, `kanban_board`, `document_draft`, `action_board` + `validation_required`
2. Status Rail avec 7 états
3. Mode clair/sombre
4. Animations de base
5. Pas de SMS/appel/email réel
6. Pas de suppression
7. Pas de stockage cloud nouveau sans validation

### Phase 2 (V2 — validation Ludovic requise)
1. `research_board`, `budget_board`, `media_board`
2. Drag & drop kanban
3. Session panel équipe
4. Vision caméra
5. Actions sensibles avec confirmation serveur

---

## 11. Fichiers concernés

- `static/simli.html` — Command Screen, Status Rail, orbe, transcript
- `static/luna.css` — Design system tokens, mode sombre
- `luna_web.py` — `_IRIS_SYSTEM`, `handle_iris_tool()`, routes validation
- `integrations/openai/web_voice_bridge.py` — `iris_render`, `invite_to_session`
- `core/iris/participants.py` — session, rôles, permissions

---

## 12. Message agent

Agent : Kimi  
Objectif : 022  
Tâche : TASK-022-KIMI-UX-IRIS-TEAM-TELEWORK-OS  
Type : livrable UX  
Résumé : UX complète Iris Team / Telework OS livrée. 10 familles de capacités avec render_types, design system (tokens, verre, animations), desktop/mobile, clair/sombre, garde-fous visuels, checklist validation. Attend DeepSeek contrat technique + arbitrage Codex avant implémentation V1.  
Fichier concerné : `docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_TEAM_TELEWORK_OS_022.md`  
Risque : faible — spécification uniquement  
Décision Ludovic requise : non pour ce livrable ; oui pour Phase 2 et validation V1  
Action proposée : DeepSeek produit contrat technique. Codex tranche scope V1. Kimi Code attend.
