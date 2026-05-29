# Audit Qualité Graphique — Garde visuelle Luna

> Agent : Kimi  
> Date : 2026-05-28  
> Tâche : TASK-002-KIMI-VISUAL-QUALITY-GATE  
> Scope : `static/index.html` + `static/simli.html`  
> Méthode : Analyse statique CSS (pas de test navigateur graphique)

---

## Verdict global

**Note : 6.5/10** — Fonctionnel mais avec une dette visuelle significative. L'identité premium de Luna est présente (dégradés violets, glassmorphism, animations soignées) mais noyée sous une accumulation de styles incohérents.

---

## Métriques clés

| Métrique | index.html | simli.html | Seuil recommandé | Verdict |
|----------|-----------|------------|------------------|---------|
| Couleurs uniques | **315** | 87 | < 30 | 🔴 Mauvais |
| `!important` | **324** | 1 | < 20 | 🔴 Mauvais |
| box-shadow | 91 | 12 | < 40 | 🟡 Trop |
| border-radius uniques | 22 | 11 | < 6 | 🟡 Trop |
| Taille CSS | **95 KB** | 25 KB | < 30 KB | 🔴 Monstre |
| Transitions | 53 | — | — | 🟢 OK |
| Animations | 35 | — | — | 🟢 OK |
| Media queries | 11 | — | — | 🟢 OK |

---

## Problèmes identifiés

### 🔴 CRITIQUE — 315 couleurs dans index.html
**Impact** : Aucune palette visuelle cohérente. Luna perd son identité.  
**Description** : Le CSS contient 315 valeurs de couleur distinctes. Une app premium devrait en avoir 15-25 maximum (primaire, secondaire, neutres, états, accents).  
**Exemples de dérive** :
- `#0a0a1a`, `#0d0d1f`, `#0d0d2b`, `#1a1a2e`, `#1a1a3a`, `#1a1a3e`, `#1a1a48` — 7 noirs-bleus différents pour le fond
- `#10b981`, `#16a34a`, `#22c55e`, `#34d399`, `#4ade80`, `#6ee7b7` — 6 verts différents
- `#7c8cf8`, `#a78bfa`, `#60a5fa`, `#38bdf8`, `#67e8f9` — 5 bleus/violets différents

**Recommandation** : Créer une palette CSS variables (`:root`) avec 15-20 tokens maximum. Migrer progressivement.

### 🔴 CRITIQUE — 324 `!important`
**Impact** : Impossible à maintenir, régressions visuelles fréquentes, spécificité en guerre.  
**Description** : Presque une déclaration CSS sur deux utilise `!important`. C'est un signe que le CSS a été écrit en mode "patch sur patch" sans architecture.  
**Recommandation** : Refactoriser les 10 règles les plus critiques. Utiliser des classes utilitaires cohérentes.

### 🟡 MAJEUR — CSS 95 KB monolithique
**Impact** : Temps de chargement, maintenance difficile, risque de régression.  
**Description** : Tout le CSS est inline dans `<style>` à l'intérieur d'un fichier HTML de 8356 lignes. Pas de séparation des préoccupations.  
**Recommandation** : Extraire le CSS dans un fichier `luna.css` séparé (niveau 2/3, refactor majeure).

### 🟡 MOYEN — 22 border-radius différents
**Impact** : Incohérence visuelle, pas de système de design.  
**Description** : Les arrondis vont de 4px à 50px sans logique systématique. Certains boutons sont 50px (pill), d'autres 12px, d'autres 16px...  
**Recommandation** : Standardiser sur 3-4 tokens : `sm` (6px), `md` (12px), `lg` (16px), `pill` (50px).

### 🟡 MOYEN — 91 box-shadow
**Impact** : Interface lourde, effet "tout brille", fatigue visuelle.  
**Description** : Trop d'ombres portées créent un effet de profondeur inconsistant. Certains éléments ont des ombres violaces, d'autres noires, d'autres bleues.  
**Recommandation** : Réduire à 3-4 ombres standardisées : `subtle`, `elevated`, `glow`.

### 🟢 OK — simli.html est bien meilleur
- 87 couleurs (encore beaucoup mais raisonnable pour une page cinématique)
- 1 seul `!important`
- CSS cohérent avec l'ambiance immersive
- **Le design de simli.html devrait être le standard pour l'app principale.**

---

## Points forts à préserver

1. **Glassmorphism** — Les fonds blurés (`backdrop-filter: blur`) sont réussis et premium.
2. **Animations** — Les transitions et micro-interactions sont fluides.
3. **Dégradés violets** — La signature `#7c8cf8` → `#a78bfa` est forte et reconnaissable.
4. **simli.html** — La cinématique est soignée, le grain film, la vignette, le Ken Burns : tout ça est premium.

---

## Recommandations prioritaires

### Niveau 1 (autonome — sans changement visuel immédiat)
- [ ] Créer `static/luna.css` avec les variables CSS de base (15 tokens couleur, 4 radius, 4 shadows)
- [ ] Documenter la palette dans `docs/DESIGN_SYSTEM.md`

### Niveau 2 (validation Ludovic — refactor visuelle)
- [ ] Migrer le CSS de `index.html` vers `luna.css`
- [ ] Standardiser les couleurs sur la palette (réduire 315 → ~20)
- [ ] Standardiser les border-radius (22 → 4)
- [ ] Nettoyer les `!important` (324 → < 20)

### Niveau 3 (refactor majeure)
- [ ] Extraire les composants réutilisables (boutons, cartes, modales)
- [ ] Audit accessibilité (contraste WCAG AA)

---

*Audit qualité graphique terminé. Luna est premium dans l'intention mais accumule de la dette visuelle. La priorité est de créer un design system minimal avant d'ajouter de nouvelles fonctionnalités visibles.*
