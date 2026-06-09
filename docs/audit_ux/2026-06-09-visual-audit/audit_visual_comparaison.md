# Audit Visuel Obligatoire — Comparaison Référence vs Réalité
**Date** : 2026-06-09  
**Auditeur** : Kimi + OpenAI Vision  
**Méthode** : Comparaison pixel à pixel entre la référence graphique officielle et la capture Playwright  
**Référence** : `docs/audit_ux/2026-06-09-visual-audit/reference_officielle.png`  
**Capture réelle** : `docs/audit_ux/2026-06-09-visual-audit/screenshots/02_workspace_empty.png`  
**Revision** : `luna-beta-00636-n2r`  
**URL** : `https://luna-beta-674304336025.europe-west1.run.app/team`

---

## SCORE GLOBAL DE CONVERGENCE

**Convergence estimée : 25-30%**

L'implémentation est fonctionnellement stable mais visuellement très éloignée de la référence. La différence n'est pas une question de "détails CSS" — c'est une différence de **layout structurel** et d'**ambiance lumineuse** fondamentale.

---

## RAPPORT D'ÉCART DÉTAILLÉ

### 1. LAYOUT GLOBAL — Écart CRITIQUE

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Structure** | 3 colonnes distinctes : sidebar gauche (~15%), canvas central (~55%), sidebar droite (~25%) | Layout vertical simple : header, stepper, canvas, participants, drawer | **Structure complètement différente** |
| **Panneaux** | Chaque zone est un panneau glassmorphism avec bordures lumineuses | Zones fusionnées, pas de délimitation claire | Critique |
| **Espace** | Canvas central est encadré, avec marges visibles | Canvas prend toute la largeur sans encadrement | Majeur |

**Correction requise** :
```css
/* Layout 3 colonnes */
.workspace-container {
  display: grid;
  grid-template-columns: 280px 1fr 320px;
  grid-template-rows: 64px 1fr 180px;
  height: 100vh;
  gap: 16px;
  padding: 16px;
}
```

**Note** : Ce n'est pas juste du CSS — c'est une refonte de la structure HTML. La sidebar droite (Mission + Participants) n'existe pas dans le code actuel. Elle doit être créée.

---

### 2. HEADER / BARRE SUPÉRIEURE — Écart CRITIQUE

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Logo YAWATCH** | Grand logo Y géométrique stylisé (80×80px environ) + texte "YAWATCH INDUSTRIES" en uppercase élégant | Petit logo rond (~32px) + texte standard | Critique |
| **Sous-titre** | "IRIS WORKSPACE" en lettres espacées, vert clair | "Iris Workspace" en texte normal | Majeur |
| **Titre session** | "NOUVELLE SESSION STRATÉGIQUE" + date + créateur, centré en haut | Titre en haut à droite, petit | Majeur |
| **Contrôles** | "MODE FOCUS" bouton + icône notifications avec badge "2" + avatar owner avec dropdown | "1 participants 0 sources" texte brut | Critique |

**Correction requise** :
- Remplacer le logo rond par un logo Y géométrique SVG (style référence)
- "IRIS WORKSPACE" en `letter-spacing: 4px`, couleur vert clair
- Titre session centré avec sous-titre date
- Ajouter bouton MODE FOCUS, icône notification, avatar owner

---

### 3. SIDEBAR GAUCHE (Navigation) — Écart CRITIQUE

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Structure** | Sidebar verticale complète avec icônes, noms, numéros, statuts | Stepper horizontal compact | **Structure inexistante** |
| **Étapes** | 5 items verticaux : BRIEF (✓ Terminé), COLLECTE (2 En cours), ANALYSE (3 À venir), DÉCISION (4 À venir), LIVRABLE (5 À venir) | 5 petits pills horizontaux | Critique |
| **Item actif** | COLLECTE a un fond violet avec glow, bordure lumineuse | COLLECTE a un fond vert foncé, pas de glow | Majeur |
| **Icônes** | Chaque étape a une icône distincte (losange, cube, graphique, hexagone, plume) | Pas d'icônes | Majeur |
| **Progression** | Jauge circulaire "2/5" avec 40% en bas de la sidebar | Pas de jauge circulaire | Majeur |

**Correction requise** :
- Transformer le stepper horizontal en sidebar verticale
- Ajouter des icônes SVG par étape
- Créer une jauge circulaire SVG pour la progression
- L'étape active doit avoir un fond violet `rgba(139, 92, 246, 0.2)` avec `box-shadow: 0 0 20px rgba(139, 92, 246, 0.4)`

---

### 4. CANVAS CENTRAL — Écart CRITIQUE

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Orbe Y** | ÉNORME (~300px), au centre, avec anneaux concentriques multiples, glow vert/violet intense | Petite (~50px), au centre, glow très subtil | **Taille ×6 trop petite** |
| **Logo Y** | Grand logo Y transparent (~400px) à droite du canvas | Absent | Critique |
| **Fond** | Texturé avec grille, traînées lumineuses, halos diffus, profondeur réelle | Noir quasi-uni `#020810` | Critique |
| **Halo** | Halo vert émeraude massif + reflets violets | Halo vert très faible | Majeur |

**Correction requise** :
```css
/* Orbe Y */
.orbe-y {
  width: 300px;
  height: 300px;
  filter: drop-shadow(0 0 60px rgba(16, 185, 129, 0.6))
          drop-shadow(0 0 120px rgba(139, 92, 246, 0.3));
}

/* Anneaux concentriques */
.rings::before, .rings::after {
  content: '';
  position: absolute;
  border: 1px solid rgba(16, 185, 129, 0.3);
  border-radius: 50%;
}

/* Fond texturé */
.canvas-bg {
  background: 
    radial-gradient(ellipse at 30% 50%, rgba(16, 185, 129, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 70% 30%, rgba(139, 92, 246, 0.06) 0%, transparent 40%),
    linear-gradient(180deg, #0a1218 0%, #020810 100%);
}
```

**Logo Y transparent** : Ajouter un grand logo Y (~400px) en `position: absolute; right: 5%; top: 20%; opacity: 0.15;` avec un gradient de masque.

---

### 5. SIDEBAR DROITE (Mission + Participants) — Écart CRITIQUE

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Structure** | Panneau complet avec sections : MISSION, ACTIVITÉ RÉCENTE, bouton historique | **N'existe pas** | **Structure inexistante** |
| **Mission** | Section "MISSION" avec : Sujet, Owner (LUDOVIC + badge VOUS), Participants IA (Iris, IQ, Luna avec photos réalistes) | Informations dispersées dans le header/context | Critique |
| **Participants** | Photos réalistes des IA (visages humains), noms, rôles | Avatars circulaires avec initiales (I, IQ, L) | Critique |
| **Activité** | "ACTIVITÉ RÉCENTE" avec timeline (Iris a rejoint, IQ a rejoint, Luna a rejoint, Session créée) | Absente | Majeur |
| **Bouton** | "VOIR L'HISTORIQUE" en bas de la sidebar | Absent | Mineur |

**Correction requise** :
- **Créer la sidebar droite** — elle n'existe pas dans le code actuel
- Section MISSION avec le sujet, owner, participants
- Participants IA : utiliser des avatars générés (pas de photos réelles possibles sans assets) OU des avatars stylisés plus grands avec indicateurs
- Timeline d'activité

**Note sur les photos** : La référence montre des photos réalistes. Sans assets photos, utiliser des avatars générés style référence (silhouettes stylisées) OU agrandir les avatars existants et ajouter des indicateurs audio (barres animées).

---

### 6. PANNEAU PARTICIPANTS (bas) — Écart CRITIQUE

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Layout** | 4 cartes horizontales avec photos réalistes, noms, rôles, indicateurs audio | 4 petits chips avec initiales | Critique |
| **Photos** | Photos réalistes de visages humains | Avatars circulaires avec lettres | Majeur |
| **Indicateurs audio** | Barres vertes animées sous chaque participant | Absents | Majeur |
| **Badge** | Badge "VOUS" sur Ludovic | Badge "(vous)" petit | Mineur |
| **Caméra/Micro** | Icônes caméra ON / micro ON avec indicateurs verts | CAMÉRA / MICRO texte simple | Majeur |
| **Bouton quitter** | "QUITTER LA SESSION" violet, grand | Absent | Mineur |

**Correction requise** :
```css
.participant-card {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.participant-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 2px solid rgba(16, 185, 129, 0.4);
}

.audio-bars {
  display: flex;
  gap: 3px;
  height: 20px;
  align-items: flex-end;
}
.audio-bar {
  width: 4px;
  background: linear-gradient(to top, #10b981, #34d399);
  border-radius: 2px;
  animation: audioPulse 1s ease-in-out infinite;
}
```

---

### 7. TYPOGRAPHIE ET HIÉRARCHIE — Écart MAJEUR

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Titre principal** | "Aucune proposition active" — 24px+, "proposition" en violet | "Aucune proposition active — choisissez une piste." — texte gris, taille moyenne | Majeur |
| **Sous-titre** | "Les participants peuvent déposer leurs pistes d'étude librement." — gris clair, centré | "Soumettez une piste dans la section PROPOSITIONS ci-dessous." — gris sombre, petit | Majeur |
| **CTA** | "+ DÉPOSER UNE PROPOSITION" — grand, centré, glassmorphism | "Soumettre une piste..." — petit, en bas, simple | Majeur |

**Correction requise** :
```css
.empty-title {
  font-size: 28px;
  font-weight: 600;
  color: #e5e7eb;
}
.empty-title .highlight {
  color: #a78bfa; /* violet */
}
.empty-subtitle {
  font-size: 16px;
  color: #9ca3af;
}
.empty-cta {
  font-size: 16px;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 12px;
  color: #e5e7eb;
}
```

---

### 8. COULEURS ET PALETTE — Écart MAJEUR

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Vert principal** | Émeraude profond `#10b981` avec glow fort | Vert plus clair, glow faible | Majeur |
| **Violet** | Violet prononcé `#8b5cf6` utilisé pour l'étape active, les accents, les halos | Violet quasi absent | Majeur |
| **Noir de fond** | Très profond mais texturé, avec des reflets | Noir plat `#020810` | Majeur |
| **Blanc/cassé** | `#e5e7eb` pour les titres, `#9ca3af` pour le texte secondaire | Gris terne | Mineur |

**Palette cible** :
```css
:root {
  --iris-green: #10b981;
  --iris-green-glow: rgba(16, 185, 129, 0.4);
  --iris-violet: #8b5cf6;
  --iris-violet-glow: rgba(139, 92, 246, 0.4);
  --bg-primary: #020810;
  --bg-panel: rgba(255, 255, 255, 0.03);
  --text-primary: #e5e7eb;
  --text-secondary: #9ca3af;
  --border-subtle: rgba(255, 255, 255, 0.08);
}
```

---

### 9. EFFETS (Glassmorphism, Glow, Ombres) — Écart MAJEUR

| | Référence | Réalité | Écart |
|---|---|---|---|
| **Glassmorphism** | Panneaux avec `backdrop-filter: blur(20px)`, fond `rgba(255,255,255,0.03)`, bordures `rgba(255,255,255,0.1)` | `blur(6-10px)`, bordures très discrètes | Majeur |
| **Glow** | Glow vert massif sur l'orbe, glow violet sur l'étape active, glow subtil sur les bordures | Glow très faible, presque invisible | Majeur |
| **Ombres** | Ombres portées douces mais visibles sur les panneaux | Ombres très faibles | Mineur |

**Correction requise** :
```css
.glass-panel {
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.glow-green {
  box-shadow: 0 0 40px rgba(16, 185, 129, 0.3);
}

.glow-violet {
  box-shadow: 0 0 40px rgba(139, 92, 246, 0.3);
}
```

---

### 10. AMBIANCE GÉNÉRALE — Écart CRITIQUE

| | Référence | Réalité |
|---|---|---|
| **Impression** | Poste de commandement stratégique, produit premium, IA haut de gamme | Application web fonctionnelle, prototype dark mode |
| **Immersion** | Forte — les éléments lumineux et la profondeur créent une ambiance | Faible — le canvas vide domine |
| **Identité** | YAWATCH Industries est partout (logo, couleurs, style) | YAWATCH est un petit texte en header |

---

## LISTE PRIORISÉE DES CORRECTIONS

### 🔴 CRITIQUE (bloquant la validation)

| # | Correction | Difficulté | Impact |
|---|---|---|---|
| 1 | **Créer le layout 3 colonnes** (sidebar gauche + canvas + sidebar droite) | Difficile | Structurel |
| 2 | **Agrandir l'orbe Y ×6** + anneaux concentriques + glow massif | Moyenne | Visuel fort |
| 3 | **Créer la sidebar droite** (Mission + Participants IA + Activité) | Difficile | Structurel |
| 4 | **Transformer le stepper en sidebar gauche verticale** avec icônes + jauge | Difficile | Structurel |
| 5 | **Refonte du header** avec logo Y géométrique + contrôles + titre centré | Moyenne | Identité |

### 🟡 MAJEUR (doit être corrigé)

| # | Correction | Difficulté |
|---|---|---|
| 6 | **Fond canvas texturé** (grille, traînées, halos, logo Y transparent) | Moyenne |
| 7 | **Palette violet** utilisée pour les accents, l'étape active, les halos | Facile |
| 8 | **Glassmorphism renforcé** (blur 20px, bordures lumineuses, ombres) | Facile |
| 9 | **Typographie** : titre 28px avec highlight violet, sous-titre 16px | Facile |
| 10 | **Participants bas** : cartes plus grandes, indicateurs audio, bouton quitter | Moyenne |

---

## CONCLUSION

**L'écart entre la référence et la réalité est structurel**, pas seulement cosmétique. La référence demande :
1. Un **layout 3 colonnes** qui n'existe pas
2. Une **sidebar droite** (Mission + Participants) qui n'existe pas
3. Une **sidebar gauche** (Navigation verticale + Progression) qui n'existe pas
4. Un **canvas central riche** (orbe géante, fond texturé, logo Y) qui n'existe pas
5. Un **header premium** (logo géométrique, contrôles) qui n'existe pas

**Ce n'est pas 10 corrections CSS. C'est une refonte HTML/CSS complète de l'interface.**

**Recommandation** : Claude doit traiter cette refonte comme une **reconstruction UI**, pas comme des ajustements. Les régressions fonctionnelles restent la règle d'or — tout le workflow V1 doit continuer de fonctionner.

---

## RÈGLES ABSOLUES (inchangées)

- ❌ Ne jamais modifier le workflow métier
- ❌ Ne jamais modifier les objets métier
- ❌ Ne jamais supprimer les caméras/micros/participants
- ✅ Le script `yawatch_audit.py` doit continuer de passer
