# Claude — Implémentation Team Workspace — Objectif 035

Date V1 : 2026-06-07
Date V2 : 2026-06-07
Agent : Claude
Type : implementation V2 (refonte Phase 1 — vision IRIS_WORKSPACE_VISION_PRODUIT_UX.md)
Statut : code livré, PAS déployé (validation Ludovic requise)

## Fichiers créés / modifiés

- `static/team_workspace.html` — refonte complète V2 (768 lignes)
- `luna_web.py` — route `GET /team` (inchangée depuis V1)

---

## V2 — Phase 1 Refonte Visuelle Fondatrice

### Checklist Phase 1 (vision document)

| Exigence | Statut |
|---|---|
| Mode clair premium par défaut | ✅ fond #edf0f8, panneaux #fff |
| Grand plan central lisible | ✅ grid auto-fill, domine l'espace |
| Cartes flottantes → places autour d'une table | ✅ rangée horizontale scrollable, seats visibles |
| Iris / IQ / Luna : rôles clarifiés | ✅ sidebar dédiée + seats AI dans la rangée |
| Aucun bouton décoratif | ✅ tous les boutons ont une fonction ou sont désactivés avec explication |

### Architecture visuelle V2

```
[HEADER : logo + titre session + stats + Brief + retour Iris Audio]
─────────────────────────────────────────────────────────────────
[SEATS ROW : Ludovic 👑 | Alice | Thomas | Sarah | | 🔮 Iris | 🧠 IQ | 🌙 Luna]
─────────────────────────────────────────────────────────────────
[CANVAS                                   ] [SIDEBAR               ]
[toolbar: + Idée | + Source | + Décision  ] [Intelligences présentes]
[                                         ] [  🔮 Iris — Secrétaire ]
[  Grid auto-fill de cartes typées        ] [  🧠 IQ — Analyste     ]
[  (idea/source/decision/action/synthesis)] [  🌙 Luna — Direction  ]
[  grille pointillée bleue légère         ] [                       ]
[  hover: élévation + ombre               ] [Mission Brief          ]
[                                         ] [Sources (liste)        ]
[                                         ] [Avis Iris (conditionnel)]
─────────────────────────────────────────────────────────────────
[SPECTATEURS : Carl V. | Nina P. ✋ → promo siège]
```

### Palette couleurs V2 (light premium)

| Rôle | Couleur |
|---|---|
| Fond page | `#edf0f8` |
| Panneaux/cartes | `#ffffff` |
| Iris (accent) | `#4f46e5` bleu/indigo |
| Luna (accent) | `#7c3aed` violet |
| IQ (accent) | `#059669` vert |
| Décision | `#10b981` vert |
| Source | `#f59e0b` orange |
| Action | `#ef4444` rouge |
| Synthèse Iris | `#7c3aed` violet, fond `#faf5ff` |
| Texte principal | `#111827` |
| Texte secondaire | `#6b7280` |
| Bordures | `rgba(0,0,0,0.08)` |

### Participants : seats row

- Rangée horizontale sous le header (scrollable)
- Chaque seat : avatar initiales coloré + nom + rôle + icônes micro/cam
- `speaking` → bordure violette pulsante
- `editing` → bordure orange
- Hover owner → menu admin (mute/retirer/bannir — UI only)
- Séparateur visuel avant les 3 seats IA : Iris 🔮, IQ 🧠, Luna 🌙

### Plan central : canvas

- Fond `#f0f2f8` + grille radiale pointillée bleu pâle (24px)
- Cards : auto-fill minmax(220px, 1fr)
- 5 types : `idea` (indigo), `source` (orange), `decision` (vert), `action` (rouge), `synthesis` (violet)
- Chaque carte : type badge + titre + détail + auteur + âge
- Hover : ombre élevée + translation -1px
- Bouton ✕ en haut à droite, visible au hover seulement

### Sidebar (300px)

1. **Intelligences présentes** : Iris / IQ / Luna avec rôle textuel + statut badge (En attente / Prête / Active)
2. **Brief mission** : résumé 3 lignes ou invite "Définir le brief →"
3. **Sources** : liste des sources ajoutées (type icon + label + auteur)
4. **Avis Iris** : bouton conditionnel (désactivé si brief OU source manquants)

### Brief modal

Champs : titre, domaine, objectif, contexte, toggle recherche externe.
Validation → affiche le brief en sidebar, titre du workspace dans le header, badge Brief activé.

### Ajouter une carte (modal)

4 types sélectionnables visuellement.
Titre requis, détail optionnel.
Type `source` → ajoute aussi dans la liste Sources sidebar.

### Iris Opinion (overlay)

- Fond blanc semi-transparent avec blur
- Panneau central blanc : titre + wave animée (5 barres violettes) + analyse contextuelle
- Analyse contextuelle : Mission, Domaine, Sources, Éléments du canvas
- Bouton "Fermer l'analyse" → déverrouille le plan
- Status IQ → "Analyse" pendant l'overlay

### Spectateurs

- Bande inférieure avec mini-cards (avatar + nom + raised ✋)
- Bouton "↑ Siège" → promeut en participant (UI only)

---

## Logs F12 produits (identiques V1)

```
[TW] team_workspace_loaded
[TW] seat_assigned Ludovic owner
[TW] seat_assigned Alice M. participant
[TW] seat_assigned Thomas R. participant
[TW] seat_assigned Sarah K. participant
[TW] spectator_joined count=2
[TW] iris_opinion_locked true | brief_ready false | sources_ready false
[TW] brief_ready true              (après applyBrief())
[TW] iris_opinion_locked false | brief_ready true | sources_ready true
[TW] iris_opinion_requested true   (après clic Avis Iris)
```

---

## Critères Phase 1 validés

| Critère vision | Statut |
|---|---|
| En 3 sec : où je suis | ✅ header "Iris Workspace" + logo |
| En 3 sec : avec qui | ✅ seats row immédiat sous le header |
| En 3 sec : sur quoi | ✅ cards sur le canvas + titre workspace |
| Plan central donne envie d'y déposer quelque chose | ✅ toolbar visible, fond structuré |
| Iris/IQ/Luna : fonction claire | ✅ sidebar avec rôles textuels |
| Aucun bouton décoratif | ✅ bouton Iris grisé avec explication |
| Interface montrable à une entreprise | ✅ light mode premium |

---

## Interdictions respectées

- Aucun SMS / email / appel / paiement / réservation
- Aucun secret côté frontend
- Aucune suppression irréversible
- **Aucun déploiement** (en attente validation Ludovic)

---

## Ce qui reste pour Phase 2+

- Connexion WebSocket multi-participants temps réel
- Upload document → preview → IQ analysis (cycle complet)
- Drag & drop des cartes sur le canvas
- Annotation collaborative
- Export PDF / compte-rendu
- Toggle dark / light mode
- Intégration brief partagé avec `/simli` via WebSocket
