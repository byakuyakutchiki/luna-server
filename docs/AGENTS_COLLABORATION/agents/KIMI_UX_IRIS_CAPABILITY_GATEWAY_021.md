# Kimi — Iris Capability Gateway — UX Premium

> **Objectif** : 021
> **Agent** : Kimi
> **Date** : 2026-06-02
> **Statut** : livrable UX — prêt pour implémentation Claude
> **Base** : `KIMI_UX_IRIS_021.md` (Teams Overlay + Light/Dark + 8 render_type)
> **Ce fichier** : addendum Capability Gateway — garde-fous, research_board, états travail

---

## 1. Target exacte (TARGET_CELL)

**Objectif** : Iris ne dit pas "je ne peux pas accéder". Elle montre qu'elle travaille.

**Fonctionnalité** : Interface visuelle du Capability Gateway dans `/simli`.

**Target** : Quand un utilisateur demande une capacité (recherche, document, action, carte, équipe), Iris projette immédiatement un rendu visuel structuré qui montre :
- ce qu'elle fait en ce moment (état) ;
- les données/source qu'elle utilise ;
- le résultat structuré ;
- les actions possibles avec garde-fou.

**Utilisateur cible** : Ludovic (owner), équipe trusted, invités temporaires.

---

## 2. Matrice de validation par capacité

| Capacité | `render_type` | Backend attendu | Frontend attendu | Garde-fou visuel |
|---|---|---|---|---|
| Recherche web | `research_board` | API recherche externe | Sources + synthèse + fiabilité | Badge "Sources vérifiées" ou "Résultat approximatif" |
| Documents vault | `document_insight`, `document_draft`, `media_board`, `form_board` | `/api/documents/v2/*` | Contenu structuré + tags | Masquer si invité non autorisé |
| Contact / Appel | `contact_board` | Twilio, contacts | Fiche + historique + actions | Boutons bloqués en gris si non-owner, badge "Validation requise" |
| Action sensible | `action_board` avec `requires_confirmation` | Préparation tool | Récap + coût + risque + destinataire | Barre ambre bloquante, timer 10min |
| Carte / Itinéraire | `map_board` | Maps API ou placeholder | Carte statique + distances | Aucune position précise sans consentement |
| Session équipe | Teams Overlay | `session_manager.py` | Liste participants + rôles + actions | Scope projet affiché, actions grisées |
| Finances | `budget_board` | Budget/quotas | KPI + barres + alertes | Ne pas exposer total patrimoine aux invités |
| Décision | `decision_board` | Comparaison interne | 2-3 colonnes + reco Iris | Mentionner si données incomplètes |
| Kanban | `kanban_board` | Tâches internes | Colonnes + cartes | Permissions CRUD selon rôle |
| Réunion | `meeting_board` | Historique session | CR + décisions + actions | Validation avant envoi |

---

## 3. Addendum — `research_board` (Couche A)

Spécifique manquant dans `KIMI_UX_IRIS_021.md`.

### Déclencheur
"cherche sur le web", "actualités sur", "synthèse de", "qu'en dit internet"

### Maquette

```
+──────────────────────────────────────────────────────+
│  RECHERCHE  — "Base Legacy"                          │
│                                                      │
│  🔍 Iris a consulté 4 sources (2.3s)                │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Synthèse                                      │  │
│  │  Base Legacy est un projet immobilier en       │  │
│  │  cours à Paris 15e. Livraison prévue 2027.     │  │
│  │  Promoteur : Nexity. Prix moyen : 8 900€/m².   │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Sources consultées                                  │
│  ● site-immobilier.fr        — fiabilité élevée     │
│  ● wikipedia.org             — fiabilité moyenne    │
│  ● journal-local.fr          — fiabilité moyenne    │
│  ● forum-discussion.com      — fiabilité faible ⚠   │
│                                                      │
│  [Ouvrir source 1]  [Copier synthèse]  [Explorer]   │
+──────────────────────────────────────────────────────+
```

### Spec CSS

- Header : icône loupe `🔍` + texte "Iris a consulté N sources (Xs)"
- Synthèse : fond `--bg-panel`, border `--border-subtle`, padding 14px, texte 13px line-height 1.7
- Sources : liste verticale, chaque ligne = nom domaine (souligné, `--iris-cyan`) + badge fiabilité
- Badge fiabilité :
  - Élevée : `ics-badge ok` — vert
  - Moyenne : `ics-badge neu` — gris
  - Faible : `ics-badge warn` — ambre + `⚠`
- Boutons footer : même style que `ics-actions` existant

### Responsive mobile
- Sources collapsées sous accordéon "Voir les sources"
- Synthèse reste visible

---

## 4. Addendum — États "Iris travaille"

Quand Iris prépare une réponse (recherche, analyse document, comparaison), l'écran doit montrer la progression, pas un simple spinner.

### 4.1 Séquence visuelle

```
Étape 1 — Analyse de la demande
  [●○○○]  "Je comprends ce que vous cherchez..."

Étape 2 — Recherche en cours
  [●●○○]  "Je consulte les sources disponibles..."

Étape 3 — Synthèse
  [●●●○]  "J'organise les informations..."

Étape 4 — Projection
  [●●●●]  → rendu final apparaît
```

### 4.2 Implémentation visuelle

Dans le `ics-rail` (status bar du Command Screen), remplacer le simple texte "En cours" par :

```css
.ics-progress-steps {
  display: flex; gap: 4px; align-items: center;
}
.ics-step {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--ics-text3);
  transition: all 0.4s ease;
}
.ics-step.done { background: var(--ics-cyan); box-shadow: 0 0 4px var(--ics-cyan); }
.ics-step.active { background: var(--ics-amber); animation: ics-pulse 1.2s infinite; }
```

**Texte dynamique** sous les dots : phrase descriptive de l'étape en cours, 11px `--text-secondary`.

**Quand le rendu arrive** : les dots passent tous en vert, texte "Prêt", puis fade-out rapide (0.3s) pour laisser place au contenu.

---

## 5. Addendum — Garde-fous visuels par capacité

### 5.1 Consentement position (Map)

Si Iris demande la position :

```
┌──────────────────────────────────────────┐
│  LOCALISATION                            │
│                                          │
│  📍 Votre position est masquée           │
│                                          │
│  [Activer la localisation]               │
│                                          │
│  Sans consentement, Iris affiche         │
│  uniquement l'adresse demandée.          │
└──────────────────────────────────────────┘
```

- Bouton "Activer" : violet plein
- Texte explicatif : `--text-tertiary`, 11px

### 5.2 Filtre invité (Documents / Contacts)

Si un guest demande un document hors scope :

```
┌──────────────────────────────────────────┐
│  🔒 ACCÈS RESTREINT                      │
│                                          │
│  Ce document ne fait pas partie du       │
│  projet auquel vous êtes invité.         │
│                                          │
│  Demandez à Ludovic d'élargir            │
│  votre accès si nécessaire.              │
└──────────────────────────────────────────┘
```

- Fond : `rgba(255,107,123,0.04)`
- Bordure : corail 1px
- Icône cadenas `--iris-coral`

### 5.3 Coût action (Twilio)

Avant validation d'un appel/SMS :

```
┌──────────────────────────────────────────┐
│  ⚠ VALIDATION REQUISE                    │
│                                          │
│  Action : Appel vers +33 6 12 34 56 78   │
│  Durée estimée : 5 min                   │
│  Coût estimé : 0.15 €                    │
│  Crédit Twilio restant : 12.40 €         │
│                                          │
│  [Annuler]              [Approuver]      │
└──────────────────────────────────────────┘
```

- Coût : `--iris-amber`, font-weight 600
- Crédit restant : `--iris-green`
- Bouton Approuver : vert, mais pas trop visible (éviter le clic accidentel)

---

## 6. Checklist avant implémentation Claude

- [x] Teams Overlay — desktop + mobile
- [x] Light / Dark Mode — variables + toggle
- [x] 8 nouveaux `render_type` — specs CSS + ASCII
- [x] `research_board` — spec complète (ce fichier)
- [x] États progression — dots + phrases
- [x] Garde-fous visuels — map, invité, coût
- [x] Responsive mobile — règles pour chaque type
- [ ] **DeepSeek** : audit backend + contrat intent→tool→render (à faire)
- [ ] **Claude** : implémentation après scope Codex

---

## 7. Règles immuables UX

1. **Jamais de panneau texte brut.** Toujours structuré, toujours typographié, toujours avec un `render_type`.
2. **Jamais de superposition.** Mobile : un seul panneau actif à la fois.
3. **Jamais de confusion Luna/Iris.** L'écran est Iris. La voix est Iris. Luna reste l'application globale.
4. **Jamais d'action réelle sans barre de validation.** Visuellement bloquant, ambre, avec timer.
5. **Jamais de données sensibles visibles aux invités.** Filtrage visuel explicite (cadenas, message).
6. **Jamais de spinner sans contexte.** "Chargement..." est interdit. "Je consulte les sources..." est obligatoire.

---

*Livrable UX Kimi — Objectif 021 Iris Capability Gateway — prêt pour implémentation.*
