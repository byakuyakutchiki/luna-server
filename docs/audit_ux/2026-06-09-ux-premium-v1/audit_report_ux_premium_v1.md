# Audit UX — Chantier UX/UI Premium V1
**Date** : 2026-06-09  
**Auditeur** : Kimi  
**Revision** : `luna-beta-00635-xsv`  
**URL** : `https://luna-beta-674304336025.europe-west1.run.app/team`  
**Screenshots** : `docs/audit_ux/2026-06-09-ux-premium-v1/screenshots/`

---

## VERDICT GLOBAL

**Priorité 1 — Workspace immersif : ❌ NON VALIDÉE**

Ce n'est pas encore un workspace premium. C'est une interface fonctionnelle rendue plus sombre avec des bordures plus fines. L'ambiance "salle de réflexion stratégique" n'est pas là.

---

## CE QUE CLAUDE A IMPLÉMENTÉ (résumé de ses notes)

| Zone | Changement technique |
|---|---|
| Canvas bg | 5 gradients imbriqués, `#020810` |
| Orbit participants | Chips horizontaux 34px pill |
| Header | 44px, border transparente |
| Context bar L2 | 13px 700 |
| Context L1/L3 | 9px dim2 |
| Carte Décision | Box-shadow verte, fond contrasté, texte 14px 700 |
| Propositions | Drawer avec handle toggle |
| Borders globales | Passées à 0.05 / 0.09 |

---

## POURQUOI ÇA NE FONCTIONNE PAS VISUELLEMENT

### 1. Le canvas est une vaste zone noire vide

**Observation** : Sur les captures 02, 03, 04, le canvas central occupe ~70% de l'écran et n'affiche qu'un texte gris pâle sur fond noir quasi-uni.

**Problème** : "5 gradients imbriqués" ne se traduisent pas visuellement. Le résultat perçu est un fond plat et sombre, pas une "profondeur réelle".

**Ce qu'attend la direction artistique** : Métal brossé, verre fumé, surfaces premium, halos diffus, éclairages indirects.

**Ce qu'on voit** : Du `#020810` avec un texte gris.

### 2. Les participants sont des puces, pas des présences

**Observation** : En bas de l'écran, Ludovic/Iris/IQ/Luna apparaissent sous forme de petits chips horizontaux sombres.

**Problème** : Ils se perdent dans le fond noir. Les noms sont petits. Les statuts "EN ATTENTE" manquent de contraste. On ne perçoit pas qu'il s'agit de "membres permanents du conseil stratégique".

**Ce qu'il faudrait** :
- Taille plus grande
- Couleurs de fond distinctes et plus saturées
- Glow subtil autour de l'avatar actif
- Nom + rôle bien lisibles
- Séparation claire entre owner et IA

### 3. La carte Décision flotte dans le vide

**Observation** (capture 06) : La carte Décision est bien verte et contrastée, mais elle est isolée dans un océan noir.

**Problème** : Il n'y a pas de hiérarchie visuelle entre la Décision et le reste du canvas. Elle devrait être le **centre visuel** de l'interface, avec un éclairage/gradient qui attire l'œil.

### 4. Manque de matière et de lumière

**Observation** : Aucun effet de verre (`backdrop-filter: blur`), aucun halo diffus, aucun reflet, aucune ombre portée élégante.

**Problème** : Tout est plat. Les panneaux ressemblent toujours à des `div` HTML, pas à des "éléments physiques haut de gamme".

### 5. Le drawer PROPOSITIONS est cassé

**Observation** : Sur toutes les captures, le drawer PROPOSITIONS apparaît comme un trait mince tout en bas de l'écran. Le texte "PROPOSITIONS" est à peine visible.

**Problème fonctionnel** : Le script d'audit n'a pas réussi à cliquer sur `#btnPropAdd` car l'élément n'était pas visible. C'est une **régression fonctionnelle**.

**Capture 04** : La proposition n'a pas pu être soumise automatiquement.

### 6. Les boutons ont des couleurs criardes

**Observation** : Les boutons comme "VALIDER LA DÉCISION" et "VALIDER UNE DÉCISION" utilisent un vert vif (`#00c48c` ou similaire) qui ne s'intègre pas harmonieusement avec l'ambiance sombre premium.

**Problème** : Le vert vif est fonctionnel mais pas premium. Il faudrait un vert plus soutenu, plus métallisé, peut-être avec un gradient subtil.

### 7. Le header est toujours trop "app web"

**Observation** : "YAWATCH INDUSTRIES" + "Iris Workspace" à gauche, compteurs à droite.

**Problème** : Le logo YAWATCH n'est pas mis en valeur. L'ensemble ressemble à une barre d'application, pas à un élément d'identité d'un produit premium.

### 8. Manque de hiérarchie de lecture

**Observation** : Question, ÉTAPE, EN COURS, Étape 3/13 sont empilés avec des tailles de police proches.

**Problème** : On ne comprend pas immédiatement la structure Mission→Question→Décision→Actions→Réserves.

---

## RÉGRESSIONS FONCTIONNELLES

| Élément | Problème | Sévérité |
|---|---|---|
| `#btnPropAdd` | Non visible, drawer Propositions inaccessible | 🔴 CRITIQUE |
| `OUVRIR UNE RÉSERVE` | Non visible, modal inaccessible | 🔴 CRITIQUE |
| Setup modal | Le champ titre semble manquant ou renommé — script d'audit échoue | 🔴 CRITIQUE |

**Conséquence** : Le workflow validé en V1 est partiellement cassé. Impossible de tester le dossier final sur cette revision.

---

## COMPARAISON AVANT / APRÈS

| Critère | Avant (V1 fonctionnel) | Après (V1 premium) | Verdict |
|---|---|---|---|
| Lisibilité | Correcte | Dégradée (trop sombre) | ❌ Régression |
| Hiérarchie | Claire | Confuse (tout se fond) | ❌ Régression |
| Workspace immersif | Non | Non (juste plus sombre) | ❌ Pas atteint |
| Participants visibles | Tuiles lisibles | Chips sombres | ❌ Régression |
| Fonctionnalités | Toutes OK | Drawer cassé, réserve cassée | 🔴 Régression critique |
| Cohérence globale | OK | Fragmentée | ❌ Régression |

---

## ANALYSE PAR RAPPORT À LA DIRECTION ARTISTIQUE DE CHATGPT

| Direction artistique | Implémentation actuelle | Écart |
|---|---|---|
| Noir profond | `#020810` presque noir pur | ✅ Proche |
| Vert Iris métallisé | Vert vif plat | ❌ Mauvais ton |
| Violet YAWATCH accent | Presque absent | ❌ Manquant |
| Reflets cyan discrets | Absents | ❌ Manquant |
| Métal brossé | Non | ❌ Manquant |
| Verre fumé | Non | ❌ Manquant |
| Surfaces premium | Non | ❌ Manquant |
| Logo YAWATCH en identité | Petit texte en header | ❌ Sous-utilisé |
| Zone centrale noble et spacieuse | Vaste zone noire vide | ❌ Inverse |
| Étapes avec glow | Stepper standard | ❌ Pas de glow |
| Caméras intégrées | Chips sombres | ❌ Sous-intégrées |
| IA = membres du conseil | Petits boutons | ❌ Pas de présence |

---

## RECOMMANDATIONS POUR CLAUDE — ITÉRATION V1.1

### 🔴 Corriger immédiatement (bloquant)

1. **Réparer le drawer Propositions** — doit être visible et cliquable par l'audit Playwright (`#btnPropAdd`)
2. **Réparer le bouton "OUVRIR UNE RÉSERVE"** — doit être visible et cliquable
3. **Vérifier le setup modal** — le champ titre/session doit être accessible
4. **Avant toute nouvelle amélioration visuelle**, le workflow V1 doit re-fonctionner de bout en bout

### 🟡 Refonte visuelle — directives concrètes

**A. Système de lumière**
- Ajouter un **halo vert très diffus** derrière la carte Décision (radial-gradient, large blur)
- Ajouter des **reflets cyan subtils** sur les bords supérieurs des panneaux
- Utiliser `backdrop-filter: blur()` sur les modals et certains panneaux (effet verre)
- Limiter les fonds 100% noirs — utiliser des dégradés très subtils `#0a1218` → `#020810`

**B. Matière des panneaux**
- Remplacer les bordures fines par des **ombres portées douces** + bordures très légères
- Ajouter des **surfaces "verre fumé"** (`background: rgba(255,255,255,0.03)` + `backdrop-filter: blur(12px)`)
- Les cartes de proposition doivent avoir une présence physique (ombre, reflet haut)

**C. Participants — présence visuelle**
- Taille minimum 48px pour les avatars
- Couleurs de fond **saturées mais douces** par IA
- Glow/ombre colorée autour de l'avatar de l'IA qui parle ou est active
- Nom en 13-14px, rôle en 10px, bien contrasté
- Owner (Ludovic) visuellement distinct des IA

**D. Logo et identité**
- Logo YAWATCH plus visible en haut à gauche
- Utiliser le violet YAWATCH comme accent (points d'étapes actifs, badges, séparateurs)
- Le vert Iris doit être **plus soutenu**, moins néon

**E. Hiérarchie typographique**
```
Question    : 18-20px, medium, blanc cassé
Mission     : 11-12px, uppercase, gris doux
Décision    : 16px, semibold, blanc
Actions     : 14px, regular, gris clair
Réserves    : 13px, regular, gris
```

**F. Boutons**
- Boutons primaires : gradient vert soutenu + ombre verte diffuse
- Boutons secondaires : fond transparent + bordure blanche très douce
- Hover : léger glow, pas de changement de couleur brutal

### 🟢 Validation obligatoire avant prochain déploiement

Avant de redéployer, Claude doit vérifier localement :
- [ ] Setup modal fonctionne
- [ ] 3 propositions peuvent être soumises
- [ ] Proposition peut être activée
- [ ] Décision peut être validée
- [ ] Actions peuvent être ajoutées
- [ ] Réserves peuvent être ouvertes
- [ ] Dossier final peut être généré
- [ ] Le script `yawatch_audit.py` passe sans timeout

---

## CONCLUSION

**Le chantier UX/UI Premium ne peut pas être validé en l'état.**

Il y a deux problèmes simultanés :
1. **Régressions fonctionnelles graves** (drawer et réserves inaccessibles)
2. **Ambiance visuelle non atteinte** (trop sombre, trop plat, pas de matière, pas de lumière)

**La bonne nouvelle** : les régressions sont probablement faciles à corriger. Et l'ambiance premium est atteignable avec du `backdrop-filter`, des gradients radiaux subtils, des ombres colorées, et une meilleure hiérarchie typographique.

**Recommandation** : Claude corrige d'abord les régressions fonctionnelles. Puis il applique les directives de lumière/matière/ci-dessus. Puis redéploiement. Puis nouvel audit Kimi.

---

## LIENS UTILES

- Direction artistique ChatGPT : voir issue GitHub "IRIS WORKSPACE PREMIUM V1"
- Prompt UX/UI officiel : `docs/audit_ux/PROMPT_UX_UI_PREMIUM.md`
- Captures avant : `docs/audit_ux/2026-06-09-mission-reelle/screenshots/`
- Captures actuelles : `docs/audit_ux/2026-06-09-ux-premium-v1/screenshots/`
