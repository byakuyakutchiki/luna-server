# BRIEF P3 — Dossier final premium (IRIS WORKSPACE REPORT)

**Priorité** : P3 (choix PO Ludovic)  
**Responsable implémentation** : Claude  
**Responsable audit** : Kimi  
**Statut** : 🚀 EN COURS  
**Référence visuelle** : `docs/ChatGPT Image Jun 9, 2026, 09_17_00 PM.png`  

---

## 🎯 Objectif

Transformer le dossier final d'un **texte brut monospace** en un **rapport exécutif premium** digne de YAWATCH Industries.

Le dossier final est le livrable officiel d'Iris. L'utilisateur va :
- le lire
- le copier
- le partager
- l'archiver

Il doit refléter l'identité premium du workspace.

---

## 🔴 Problèmes actuels (capture V1.3b)

### 1. Police monospace brut
- **Actuel** : `font-family: monospace` sur l'en-tête et les champs
- **Attendu** : Police system-ui propre, hiérarchie typographique nette

### 2. Titres de section microscopiques
- **Actuel** : `9px uppercase gris` — illisibles
- **Attendu** : `12-13px`, weight `700`, couleur iris ou blanc cassé, avec icône

### 3. En-tête anonyme
- **Actuel** : "📄 Dossier final — snapshot" + boutons "Copier le texte" / "Retour"
- **Attendu** : **En-tête premium YAWATCH** avec branding

### 4. Réserves indifférenciées
- **Actuel** : Liste texte simple, sans code couleur
- **Attendu** : Visuellement hiérarchisées par sévérité

### 5. Synthèse Iris perdue
- **Actuel** : Bloc italique gris transparent
- **Attendu** : Section **prestigieuse**, encadrée, mise en valeur comme pièce maîtresse

---

## ✅ Spécifications détaillées

### SP-1 — En-tête premium YAWATCH

```
┌─────────────────────────────────────────────────────────────┐
│  ◆  YAWATCH INDUSTRIES                                      │
│     IRIS WORKSPACE REPORT                                   │
│     ─────────────────────                                   │
│     Dossier final — snapshot                                │
│     [Copier]  [Retour au workspace]                         │
└─────────────────────────────────────────────────────────────┘
```

- [ ] Logo Y géométrique 24px + "YAWATCH INDUSTRIES" en `11px` uppercase tracking `2px`
- [ ] "IRIS WORKSPACE REPORT" en `18px` weight `700`
- [ ] Ligne décorative iris sous le titre (1px, 60% largeur)
- [ ] Sous-titre "Dossier final — snapshot" en `10px` gris
- [ ] Boutons repositionnés à droite, style glassmorphism

### SP-2 — En-tête métadonnées (carte premium)

Remplacer le bloc monospace par une **carte vitrine** :

```
┌─────────────────────────────────────────────────────────────┐
│  📋 MISSION          Audit UX post-déploiement              │
│  👤 OWNER            Auditeur UX                            │
│  📅 DATE             10 juin 2026                           │
│  🔖 VERSION          1.0 (snapshot)                         │
│  🤝 PARTICIPANTS     Iris · IQ · Luna                       │
└─────────────────────────────────────────────────────────────┘
```

- [ ] Fond : `rgba(12,20,40,0.6)` avec `backdrop-filter: blur(10px)`
- [ ] Bordure : `1px solid rgba(255,255,255,0.08)`
- [ ] Border-radius : `12px`
- [ ] Padding : `16px 20px`
- [ ] Labels : `10px` uppercase, couleur `var(--dim2)`, icône emoji
- [ ] Valeurs : `13px` weight `600`, couleur `var(--text)`
- [ ] Lignes séparées par `border-bottom` subtil

### SP-3 — Titres de section exécutifs

Remplacer les titres `9px gris uppercase` par :

- [ ] Taille : `12px`
- [ ] Weight : `700`
- [ ] Letter-spacing : `1.5px`
- [ ] Text-transform : `uppercase`
- [ ] Couleur : `var(--iris)` (vert) ou blanc cassé
- [ ] **Icône SVG** à gauche (pas emoji) pour chaque section :
  - Question → icône point d'interrogation
  - Propositions → icône ampoule
  - Décision → icône coche/cible
  - Actions → icône checklist
  - Réserves → icône warning
  - Sources → icône lien
  - Synthèse → icône étoile/couronne (prestige)
- [ ] Séparateur sous le titre : `1px solid rgba(16,212,142,0.15)`
- [ ] Margin-bottom : `12px`

### SP-4 — Réserves visuellement hiérarchisées

Chaque réserve doit avoir un **code couleur immédiat** :

| Sévérité | Couleur | Label | Style |
|----------|---------|-------|-------|
| 🟡 Jaune | `#f59e0b` | ATTENTION | Border-left 3px jaune, fond `rgba(245,158,11,0.05)` |
| 🟠 Orange | `#f97316` | RÉSERVE | Border-left 3px orange, fond `rgba(249,115,22,0.05)` |
| 🔴 Rouge | `#ef4444` | CRITIQUE | Border-left 3px rouge, fond `rgba(239,68,68,0.05)` |

- [ ] Carte individuelle par réserve (pas une liste simple)
- [ ] Border-radius : `8px`
- [ ] Padding : `12px 14px`
- [ ] Badge couleur avec le label en `9px` uppercase
- [ ] Titre de la réserve en `13px` weight `600`
- [ ] Corps en `12px` line-height `1.7`

### SP-5 — Synthèse Iris (section prestigieuse)

La synthèse est la **pièce maîtresse** du rapport. Elle doit être visuellement distincte.

- [ ] **Encadré spécial** : bordure `1px solid rgba(16,212,142,0.25)`
- [ ] **Fond** : `rgba(16,212,142,0.06)` (plus marqué que le reste)
- [ ] **Border-radius** : `10px`
- [ ] **Header** : "SYNTHÈSE IRIS" avec icône couronne/étoile en `var(--iris)`
- [ ] **Label "Rapport généré par Iris"** en `10px` italic, couleur `var(--dim)`
- [ ] Texte en `13px` (pas 12px), line-height `1.85`, couleur `var(--text)`
- [ ] **Pas d'italique** (contrairement à l'actuel)
- [ ] Box-shadow subtil : `0 4px 20px rgba(16,212,142,0.08)`

### SP-6 — Carte Décision

La décision doit être **l'élément le plus imposant** du rapport.

- [ ] Fond : `rgba(16,212,142,0.08)` (plus dense)
- [ ] Bordure : `1px solid rgba(16,212,142,0.35)`
- [ ] Border-radius : `10px`
- [ ] Padding : `16px`
- [ ] Label "DÉCISION VALIDÉE" en badge vert avec icône coche
- [ ] Texte de la décision en `14px` weight `600`
- [ ] Date + owner en `10px` gris en dessous

### SP-7 — Liste Propositions / Actions / Sources

Remplacer les listes simples par des **cartes lignes** :

- [ ] Chaque élément = ligne avec fond `rgba(255,255,255,0.02)`
- [ ] Hover : `rgba(255,255,255,0.04)`
- [ ] Border-radius par élément : `6px`
- [ ] Padding : `8px 12px`
- [ ] Icône à gauche (pas emoji, mais SVG stylisé)
- [ ] Texte principal en `12px`
- [ ] Métadonnées (auteur, date) alignées à droite en `9px` gris
- [ ] Séparateur entre éléments : `4px` d'espace (pas de border)

### SP-8 — Boutons d'action

- [ ] "Copier le texte" : style primaire iris (fond vert, texte blanc)
- [ ] "Retour au workspace" : style secondaire glassmorphism
- [ ] Border-radius : `8px`
- [ ] Padding : `8px 16px`
- [ ] Font-size : `11px` weight `700` uppercase

---

## 🎨 Palette & tokens

```css
--rpt-bg: rgba(8,14,30,0.85);
--rpt-card-bg: rgba(12,20,40,0.6);
--rpt-border: rgba(255,255,255,0.08);
--rpt-iris-glow: rgba(16,212,142,0.08);
--rpt-amber: #f59e0b;
--rpt-orange: #f97316;
--rpt-red: #ef4444;
```

---

## 🚫 Règles d'or

- ❌ **Plus de `font-family: monospace`** nulle part dans le rapport
- ❌ **Plus de `9px` pour les titres de section**
- ❌ **Plus de emoji** comme icônes principales (utiliser des SVG simples)
- ✅ **Tout le contenu existant** (Mission, Owner, Date, etc.) doit être préservé
- ✅ **La fonction `copyReport()`** doit continuer de fonctionner
- ✅ **La fonction `hideReport()`** doit continuer de fonctionner
- ✅ **Aucune régression fonctionnelle**

---

## 📋 Checklist Claude

```
□ Refonte CSS complète des classes .tw-rpt-*
□ En-tête YAWATCH / IRIS WORKSPACE REPORT
□ Carte vitrine métadonnées (glassmorphism)
□ Titres de section avec icônes SVG
□ Carte Décision imposante
□ Réserves en cartes colorées (jaune/orange/rouge)
□ Synthèse Iris encadrée prestigieuse
□ Listes en cartes lignes stylisées
□ Boutons premium
□ Vérifier copyReport() et hideReport()
□ Vérifier yawatch_audit.py 6/6
□ Déployer
□ Notifier Kimi pour audit
```

---

**Date brief** : 2026-06-10  
**Validé par** : Ludovic (PO)  
