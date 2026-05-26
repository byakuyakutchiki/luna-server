# Cursor — Avis Objectif 011 — Audit UI mobile onglet Services

**Date** : 2026-05-26  
**Objectif** : Audit complet onglet Services / Conciergerie  
**Rôle** : Audit UI mobile, cartes, modales, résultats, responsive  
**Règle absolue** : Observer la lisibilité et l'ergonomie sur téléphone, ne pas coder  

---

## Mission Cursor

Tester l'onglet Services sur téléphone réel ou émulateur :

1. Grille de services lisible sur mobile ?
2. Cartes trop petites, textes coupés ?
3. Modales utilisables avec clavier virtuel ?
4. Résultats inline ou en popup ?
5. Bouton Retour visible ?
6. Pas de scroll horizontal ?

**Interdit** : Coder directement, modifier CSS, tester actions réelles.

---

## Phase 1 — Setup test mobile

### Environnements de test

- **Émulateur Android** : Tailles de viewport : 320px, 375px, 480px, 768px
- **Téléphone réel** : Si possible 4" à 6" écran
- **DevTools** : Mode responsive design (F12 → Ctrl+Shift+M)

### Points de contrôle

1. **Zoom** : Pas de zoom requis pour lire le texte
2. **Scroll** : Vertical OK, horizontal INTERDIT
3. **Toucher** : Boutons min 44px de hauteur
4. **Safe area** : Notch/Home indicator ne cache rien (iOS)

---

## Phase 2 — Audit grille Services

### Dimensions mesurées sur mobile

```
Viewport 320px (iPhone SE) :
┌─────────────────────────────┐
│  Services                   │
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ Vols                    │ │
│ │ Trouver un vol          │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ Hôtels                  │ │
│ │ Trouver un hôtel        │ │
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ SMS                     │ │
│ │ Envoyer un message      │ │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**Problèmes identifiés à observer** :

| Viewport | Problème observé | Critique ? | Correction minimale |
|---|---|---|---|
| 320px | Cartes tenant ? | ✓/❌ | Réduire padding ? |
| 320px | Texte visible ? | ✓/❌ | Font-size > 14px ? |
| 320px | Scroll horizontal ? | ✓/❌ | Éliminer overflow |
| 320px | Boutons touchables ? | ✓/❌ | Min 44px height |
| 375px | Même layout ? | ✓/❌ | - |
| 480px | Grille 2 colonnes ? | ✓/❌ | - |
| 768px | Grille 3 colonnes ? | ✓/❌ | - |

---

## Phase 3 — Audit cartes (conc-card)

### Pour chaque carte, observer sur 320px

1. **Visibilité**
   - Titre lisible ?
   - Description coupée ?
   - Icône visible ?

2. **Interactivité**
   - Padding autour du texte suffisant ?
   - Bouton cliquable sans zoom ?
   - Feedback visuel au clic ?

3. **Mise en page**
   - Une colonne ou deux ?
   - Hauteur constante ou variable ?
   - Espace blanc suffisant ?

### Exemple audit une carte (Vols)

```
Viewport 320px :
┌─────────────────┐
│ ✈️ Vols         │  ← Titre : 16px, lisible
│                 │
│ Trouver un vol  │  ← Description : 14px, lisible
│ (taper dates)   │  ← Indication : 12px, trop petit ?
│ [Chercher]      │  ← Bouton : 44px height OK
└─────────────────┘

Issues:
- "taper dates" en gris clair : difficile à lire sur blanc
- Bouton bordé ou plein couleur ? (pas clair)
- Tout se rentre dans 320px ? Oui
```

---

## Phase 4 — Audit modales et pop-ups

### Questionnaire pour chaque interaction

1. **SMS/Email/Appel (confirmation modale)**
   ```
   ┌──────────────────────────┐
   │ Envoyer SMS ?            │  ← Titre
   ├──────────────────────────┤
   │ À : +33 6 12 34 56 78    │  ← Contact
   │                          │
   │ Message :                │
   │ "Salut, ça va ?"         │  ← Aperçu message
   │ (peut être long/texte    │
   │  coupé par keyboard)     │
   ├──────────────────────────┤
   │ [Annuler] [Envoyer]      │  ← Boutons
   └──────────────────────────┘
   ```
   - Modale s'affiche sur 320px ? Oui/Non
   - Clavier virtuel cache le message ? Oui/Non
   - Boutons cliquables ? Oui/Non
   - Scroll nécessaire ? Oui/Non

2. **Recherche (résultats inline)**
   - Résultats s'affichent où (inline, modal, new panel) ?
   - Sont-ils scrollables verticalement ?
   - Y a-t-il scroll horizontal sur 320px ? NON ✓
   - Format résultat lisible (titre + 1 ligne max) ?

3. **Alerte urgence (confirmation 2x)**
   - Compte à rebours visible sur 320px ?
   - Boutons bien séparés pour toucher au doigt ?
   - Texte "DERNIÈRE CHANCE" lisible ?

---

## Phase 5 — Audit CSS responsive

### Breakpoints actuels dans `static/index.html`

Chercher :
```css
@media (max-width: 480px) { ... }
@media (min-width: 481px) { ... }
@media (min-width: 768px) { ... }
```

**À vérifier** :

| Viewport | Breakpoint cible | Layout | Problème observé |
|---|---|---|---|
| 320px | ≤ 480px | 1 col ? | ? |
| 375px | ≤ 480px | 1 col ? | ? |
| 480px | Transition | 1→2 col ? | Saut ?  |
| 768px | ≥ 768px | 2-3 col ? | ? |
| 1024px | ≥ 768px | 3 col ? | ? |

---

## Phase 6 — Audit résultats et affichage

### Cas par cas

1. **Météo (résultat simple)**
   - ☀️ 22°C, ensoleillé → S'affiche où ?
   - Taille texte 16px sur 320px → Lisible ?
   - Rafraîchir possible ?

2. **Vols (résultat complexe)**
   - Liste de cartes vols (départ, durée, prix)
   - Chaque vol sur une ligne ? Plusieurs lignes ?
   - Prix en gros sur 320px ? Oui/Non
   - Clic détails → Modale ou page complète ?

3. **Restaurants (résultat avec images)**
   - Affiche image + nom + note + distance
   - Image carrée ou rectangle ?
   - Texte coupé si long nom ?
   - Clic → Map ou détails ?

4. **Alerte urgence (résultat statut)**
   - "✅ Alerte envoyée à 47 contacts"
   - Zone verte/succès visible ?
   - Clic OK retour à Services ?

---

## Phase 7 — Points de rupture identifiés

### Critiques (bloquent usage sur mobile)

- [ ] Scroll horizontal sur 320px
- [ ] Texte > 44px impossible à lire sans zoom
- [ ] Boutons < 44px de hauteur (impossible au toucher)
- [ ] Modale clavier cache le contenu
- [ ] Cartes se chevauchent ou sortent du viewport

### Importants (dégradent l'UX)

- [ ] Icône manquante ou trop petite
- [ ] Couleur du bouton manque de contraste
- [ ] Spacing entre cartes inégal
- [ ] Overflow hidden non appliqué

### Mineurs (nice to have)

- [ ] Padding asymétrique
- [ ] Font weight pas cohérent
- [ ] État hover non applicable au mobile

---

## Phase 8 — Audit safe-area (iOS)

### Si sur iPhone avec notch/home indicator

1. **Notch en haut** :
   - Logo, bouton retour, texte ne sont pas cachés ?
   - Padding top suffisant (min 20px pour iPhone 12+) ?

2. **Home indicator en bas** :
   - Boutons ne sont pas cachés ?
   - Padding bottom suffisant (min 16px pour iPhone) ?

3. **Keyboard virtuel** :
   - Safe area respectée quand clavier ouvert ?
   - Inputs restent visibles ?

---

## Tableau récapitulatif audit

| Critère | 320px | 375px | 480px | 768px | Observation |
|---|---|---|---|---|---|
| Grille visible | ✓/❌ | ✓/❌ | ✓/❌ | ✓/❌ | ? |
| Scroll horizontal | ✓/❌ | ✓/❌ | ✓/❌ | ✓/❌ | ? |
| Boutons touchables | ✓/❌ | ✓/❌ | ✓/❌ | ✓/❌ | ? |
| Texte lisible | ✓/❌ | ✓/❌ | ✓/❌ | ✓/❌ | ? |
| Modales utilisables | ✓/❌ | ✓/❌ | ✓/❌ | ✓/❌ | ? |
| Clavier ne cache rien | ✓/❌ | ✓/❌ | ✓/❌ | ✓/❌ | ? |
| Safe-area OK | — | — | — | N/A | ? |

---

## Livrables Cursor

1. **Audit mobile par viewport**
   - 320px, 375px, 480px, 768px
   - Problèmes visuels observés
   - Critique vs important vs mineur

2. **Screenshots annotés** (si possible)
   - Marquer où le texte coupe
   - Marquer où le scroll horizontal apparaît
   - Marquer les zones du clavier qui cache

3. **CSS correction minimale proposée**
   - Ne pas refondre, juste corriger le critique
   - Ex: "Ajouter `overflow-x: hidden` au container"
   - Ex: "Réduire padding: 16px → 12px sur 320px"

4. **Recommandations UI**
   - Taille cartes adaptée par viewport
   - Confirmations modales utilisables
   - Textes priorités pour lire

---

## Interdictions

❌ Ne pas coder directement.  
❌ Ne pas refondre le CSS.  
❌ Ne pas tester actions réelles.  
✅ Juste observer et documenter les problèmes.  

---

## Statut

⏳ Audit mobile à lancer.

**Prochaines étapes** :
- DeepSeek audit technique
- Kimi audit UX textes
- Claude synthétise tout
- Ludovic valide avant corrections

**Status** : 📱 Audit responsive en attente
