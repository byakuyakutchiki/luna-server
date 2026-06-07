# Claude — Iris Workspace — État d'implémentation

> Dernière mise à jour : 2026-06-07
> Référence active : IRIS_WORKSPACE_V3_CAHIER_FONDATEUR_IMPLEMENTATION_FINAL.md
> Flux par étape : IRIS_WORKSPACE_FLOW_ETAPES_V3.md

---

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `static/team_workspace.html` | Page `/team` — 821 lignes — V3 déployée (révision `luna-beta-00605-qlg`) |
| `luna_web.py` | Route `GET /team` (inchangée) |
| `docs/.../IRIS_WORKSPACE_V3_CAHIER_FONDATEUR_IMPLEMENTATION_FINAL.md` | Source de vérité officielle |
| `docs/.../IRIS_WORKSPACE_FLOW_ETAPES_V3.md` | Schéma de flux par étape — **à valider avant implémentation** |

---

## Ce qui est en place (V3 déployée)

### Esthétique YAWatch Corporate ✅
- Fond `#050b1a` (noir profond), panneaux verre, bordures métal
- Iris = vert émeraude `#10d48e`
- IQ = cyan analytique `#22d3ee`
- Luna = violet stratégique `#a78bfa`
- Zéro emoji métier — icônes SVG linéaires (diamant / document / hexagone / flèche / noyau)

### Stepper 13 étapes ✅
- Navigation avant/arrière
- Dots done/active/locked visibles
- Actions contextuelles par étape dans la barre basse

### Orbite participants ✅
- Ligne haute : Alice / Thomas / Sarah (tiles avec initiales, micro, halo speaking)
- Ligne basse : Ludovic (owner) + Iris + IQ + Luna
- Admin hover menu : mute / retirer / exclure (UI only)

### Source import 3 modes ✅
- Fichier · Lien web · Note manuelle

### Overlays IA distincts ✅
- Organisation Iris / Analyse IQ / Refonte / Comparaison / Recommandation Luna

---

## Problème identifié — Diagnostic Codex (7 juin 2026)

### Problème 1 — Pas de moteur d'étape

Le plan central affiche **simultanément** propositions, sources, décisions et synthèses, quelle que soit l'étape active.

**Ce qui devrait se passer :**
- Étape 3 (Collecte) → seulement des propositions
- Étape 6 (Analyse IQ) → proposition gagnante + sources + rapport IQ
- Étape 10 (Reco Luna) → recommandation Luna centrale, reste en fond atténué

**Ce qui se passe aujourd'hui :**
- Toutes les cartes visibles en permanence
- Le stepper change les boutons mais pas le contenu du canvas
- Résultat : brouillon

### Problème 2 — Pas de présence réelle

Les tiles participants montrent des initiales dans un cercle.

**Ce qui devrait se passer :**
- Caméra réelle (SimliVideoTile / WebRTC tile) → Phase P0.2
- Halo orateur (animation sur prise de parole)
- Micro activable par siège
- Main levée visible
- Simli comme composant de présence intégré

**Ce qui se passe aujourd'hui :**
- Initiales statiques
- Icône micro statique

### Problème 3 — Plan central = grille de cartes

Le plan central ressemble à un Trello.

**Ce qui devrait se passer (selon la phase) :**
- Étape 3 : propositions qui s'ajoutent en live (sensation de contribution)
- Étape 4 : les propositions se regroupent en thèmes (Iris anime)
- Étape 8 : V1 atténuée à gauche, V2 Iris à droite avec diff visible
- Étape 10 : recommandation Luna occupe le centre, tout recule

**Ce qui se passe aujourd'hui :**
- Grid CSS statique, même affichage à toutes les étapes

---

## Prochaine implémentation — Moteur d'étape

> **En attente de validation du schéma IRIS_WORKSPACE_FLOW_ETAPES_V3.md par Ludovic.**

### Cible : `canvasState[étape]`

Chaque étape définit :

```js
CANVAS_STATE[étape] = {
  allowed: ['prop', 'source', 'objection', ...],  // types affichables
  mode: { prop: 'edit', source: 'read', decision: 'hidden' },  // mode par type
  layout: 'grid' | 'grouped' | 'diff' | 'central',  // disposition
  transition: 'slide' | 'fade' | 'group',  // animation en entrée
  iris_status: 'waiting' | 'active' | 'done',
  iq_status: 'waiting' | 'active' | 'done',
  luna_status: 'waiting' | 'active' | 'done',
}
```

Transition d'étape :
1. Filtrer les objets → cacher ce qui n'est pas autorisé
2. Appliquer le mode (éditable / lecture / atténué)
3. Changer le layout si nécessaire
4. Mettre à jour statuts Iris / IQ / Luna
5. Mettre à jour la barre d'actions
6. Déclencher l'animation de transition

### Fichiers à modifier

- `static/team_workspace.html` uniquement
- Aucune modification de `luna_web.py`
- Aucun déploiement sans validation Ludovic

---

## Roadmap phases

| Phase | Objectif | Statut |
|---|---|---|
| P0.1 | Refonte visuelle YAWatch Corporate, stepper 13 étapes, orbite, SVG icons | ✅ Déployé |
| **P0.2** | **Moteur d'étape : canvasState, filtrage, transitions** | ⏳ En attente validation flux |
| P0.3 | Présence réelle : SimliVideoTile, caméra/micro par siège, halo orateur | À planifier |
| P0.4 | Upload fichier réel + preview document | À planifier |
| P0.5 | Vote multi-participants temps réel (WebSocket) | À planifier |
| P1.1 | Mémoire vivante : IdeaVersion, diff, restauration | À planifier |
| P1.2 | Refonte Iris connectée au LLM | À planifier |
| P1.3 | Analyse IQ connectée au LLM | À planifier |
| P1.4 | Recommandation Luna connectée au LLM | À planifier |
| P2 | Export PDF/Word + distribution aux participants | À planifier |

---

## Interdictions actives

- Pas de SMS / email / appel / paiement / réservation
- Pas de secret côté frontend
- Pas de suppression irréversible
- **Pas de déploiement sans validation explicite Ludovic**
- **Pas de nouvelle fonctionnalité avant validation du schéma de flux**
