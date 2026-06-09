# PROMPT — Chantier UX/UI Premium Iris Workspace
**Date** : 2026-06-09  
**Émetteur** : ChatGPT (Architecte Produit) + Ludovic (PO)  
**Destinataire** : Claude (Implémentation)  
**Statut V1** : ✅ TERMINÉE — Feature Décision & Traçabilité gelée  
**Nouveau chantier** : IRIS UX/UI PREMIUM

---

## 🛑 RÈGLE ABSOLUE — NE PAS CRÉER DE NOUVEAUX OBJETS MÉTIER

Tout ce qui suit **EXISTE DÉJÀ** dans le code. Ne pas créer, ne pas renommer, ne pas modifier la structure des objets suivants :

| Objet | Existence |
|---|---|
| `decision` | ✅ Backend + Frontend |
| `actions` | ✅ Backend + Frontend |
| `reserves` | ✅ Backend + Frontend |
| `report` (dossier final) | ✅ Backend + Frontend |
| `propositions` | ✅ Backend + Frontend |
| `sources` | ✅ Backend + Frontend |
| `brief` | ✅ Backend + Frontend |
| `stepper` (5 phases) | ✅ Frontend |

**Ce chantier est PUREMENT VISUEL et EXPÉRIENTIEL.**

---

## 🎯 OBJECTIF

Transformer un **workflow validé** en une **expérience premium**.

| Avant | Après |
|---|---|
| Application fonctionnelle | Salle de réflexion augmentée |
| Interface technique | Workspace immersif |
| Dossier brut | Document présentable |
| IA = concepts | IA = présence visuelle |

---

## 📋 5 PRIORITÉS UX (ordre d'implémentation recommandé)

### PRIORITÉ 1 — Workspace Immersif

**Problème actuel** : L'interface ressemble à une application web classique (barre de titre, colonnes, sections empilées).

**Cible** : L'utilisateur doit avoir l'impression d'entrer dans un **espace de réflexion dédié**, pas dans un formulaire.

**Direction** :
- Réduire les éléments de UI "généraux" (barres de titre répétées, bordures visibles partout)
- Créer une **zone centrale immersive** pour le canvas
- Le panneau participants doit être **intégré** au décor, pas une barre en bas
- La section PROPOSITIONS en bas doit être **repositionnée** ou **intégrée** plus élégamment
- Dark mode premium (profondeur, ombres subtiles, pas du gris plat)

**À ne PAS faire** :
- ❌ 3D lourd, WebGL overkill
- ❌ Plein écran forcé
- ❌ Masquer les contrôles essentiels

---

### PRIORITÉ 2 — Hiérarchie Visuelle Immédiate

**Problème actuel** : L'œil doit lire pour comprendre la structure. Les niveaux d'information ne sautent pas aux yeux.

**Cible** : Le regard doit comprendre immédiatement :

```
Mission (titre, discret)
  ↓
Question (en évidence)
  ↓
Décision actuelle (carte centrale, visuellement dominante)
  ↓
Actions (sous la décision, visuellement subordonnées)
  ↓
Réserves (encore plus subordonnées, mais visibles)
```

**Direction** :
- **Taille de police** : Question > Décision > Actions > Réserves
- **Contraste** : Décision = zone la plus contrastée du canvas
- **Espace** : Plus d'espace autour de la Décision, moins autour des éléments subordonnés
- **Couleur** : Un code couleur clair pour chaque niveau (pas de nouveau schéma, affiner l'existant)
- **Carte Décision** : Doit être visuellement la "tête de pont" du canvas

**À ne PAS faire** :
- ❌ Redimensionner dynamiquement au scroll
- ❌ Masquer les actions/réserves par défaut
- ❌ Trop de couleurs différentes

---

### PRIORITÉ 3 — Dossier Final Premium

**Problème actuel** : Le dossier final est fonctionnel mais basique (typo monospace, sections linéaires, aspect brut).

**Cible** : Un document **présentable** — qu'on puisse montrer à un client ou archiver proprement.

**Direction** :
- **Typographie** : Remplacer `font-family: monospace` par une police élégante (serif ou sans-serif de qualité, ex: Inter, Source Serif Pro, ou Google Fonts équivalent)
- **Mise en page** :
  - En-tête avec identité visuelle (logo "Iris Workspace" ou "Compte-rendu Iris")
  - Sections visuellement délimitées (pas juste des `<hr>`)
  - Indentation et hiérarchie claire
  - Métadonnées en en-tête stylisé (tableau ou grille élégante, pas liste brute)
- **Couleurs** : Garder le dark mode mais avec des tons plus raffinés
- **Actions/Réserves dans le dossier** : Représentation visuelle (pastilles de couleur, icônes) plutôt que texte brut
- **Export** : Le bouton "Copier le texte" reste. Le Markdown généré doit être plus élégant.

**À ne PAS faire** :
- ❌ Générer un PDF côté serveur (trop lourd)
- ❌ Appeler un LLM pour "styler" le texte (zero LLM pour le dossier)
- ❌ Modifier la structure des données du report

---

### PRIORITÉ 4 — Identité Visuelle Iris / IQ / Luna

**Problème actuel** : Les IA sont des cartes avec initiales (L, I, IQ, L). Ce sont des concepts, pas des présences.

**Cible** : Chaque IA a une **identité visuelle reconnaissable** sans tomber dans le gadget.

**Direction** :
- **Avatars** : Garder les initiales mais avec une présentation soignée (couleurs de fond distinctes, formes géométriques cohérentes)
- **Palette par IA** :
  - Iris (Secrétaire exécutive) : teinte froide, posée, professionnelle
  - IQ (Analyste) : teinte neutre, analytique
  - Luna (Direction stratégique) : teinte chaude, visionnaire
  - Ludovic (Owner) : teinte distincte, autorité
- **Statuts** : "EN ATTENTE" / "TERMINÉ" doivent être visuellement codés (pastille, couleur, icône subtile)
- **Panneau participants** : Disposition plus élégante (grille harmonieuse, pas des rectangles collés)

**À ne PAS faire** :
- ❌ Avatars 3D ou animés
- ❌ Personnages cartoon
- ❌ Sons ou effets sonores

---

### PRIORITÉ 5 — Animations Discrètes

**Problème actuel** : Les transitions sont instantanées (brutales). Pas de feedback visuel sur les actions importantes.

**Cible** : Des animations **courtes et sobres** qui guident l'œil et confirment les actions.

**Direction** :
| Action | Animation suggérée |
|---|---|
| Activation d'une proposition | Glissement subtil + mise en évidence de la carte |
| Validation d'une décision | Apparition progressive de la carte Décision (fade + scale léger) |
| Création d'une action | Slide-in depuis le haut de la zone Actions |
| Création d'une réserve | Slide-in avec couleur de niveau |
| Changement de phase stepper | Transition douce entre les contenus (fade 200ms) |
| Génération du dossier final | Transition fullscreen douce (fade vers le dossier) |

**Contraintes** :
- Durée max : 300ms
- Easing : `ease-out` ou `cubic-bezier(0.4, 0, 0.2, 1)`
- Pas d'animation sur les éléments qui ne sont pas le sujet principal
- Respecter `prefers-reduced-motion`

**À ne PAS faire** :
- ❌ Animations qui ralentissent le workflow
- ❌ Effets de particules, confettis, shake
- ❌ Sons

---

## 🚫 CE QU'ON NE FAIT PAS DANS CE CHANTIER

| ❌ | Raison |
|---|---|
| Multi-participants complexes | Risque de casser la V1 fraîchement validée |
| Permissions avancées | Hors scope UX/UI |
| Workflows supplémentaires | Feature freeze V1 |
| Nouvelle logique métier | Feature freeze V1 |
| Refonte backend | Le backend est stable |
| Nouveaux objets métier | Ils existent déjà |
| Appels LLM supplémentaires | Zero LLM pour le dossier final |

---

## 📁 FICHIERS À MODIFIER

Le chantier touche essentiellement le **frontend** :

| Fichier | Nature des changements |
|---|---|
| `static/team_workspace.html` | CSS, HTML structure, animations JS |
| Éventuellement `luna_web.py` | Si des données supplémentaires sont nécessaires pour le rendu (mais priorité : éviter) |

**Règle** : Tout ce qui est visuel doit être dans le HTML/CSS/JS inline. Pas de nouvelle dépendance backend si possible.

---

## ✅ DÉFINITION DE FAIT (Definition of Done)

Le chantier est terminé quand :

1. [ ] L'interface ne ressemble plus à une "app web" mais à un "espace de réflexion"
2. [ ] La hiérarchie visuelle Mission→Question→Décision→Actions→Réserves est immédiatement lisible sans lire
3. [ ] Le dossier final est présentable (typo élégante, sections visuelles, export propre)
4. [ ] Chaque IA a une identité visuelle distincte et soignée
5. [ ] Les animations sont discrètes, courtes, et ne ralentissent pas le workflow
6. [ ] Kimi valide l'audit terrain post-implémentation (screenshots comparatifs avant/après)
7. [ ] Aucun objet métier n'a été créé, modifié, ou renommé

---

## 🔄 WORKFLOW DE VALIDATION

```
Claude implémente la priorité N
    ↓
Déploiement Cloud Run
    ↓
Kimi audit terrain (screenshots avant/après)
    ↓
Ludovic / ChatGPT validation
    ↓
Si OK → priorité N+1
```

**Une priorité à la fois.** Pas de gros bang.

---

## 📎 CONTEXTE TECHNIQUE

- **Frontend** : HTML/CSS/JS inline dans `static/team_workspace.html`
- **Backend** : WebSocket Python (`luna_web.py`), rooms stateful
- **Déploiement** : Cloud Run (`luna-beta-gly3g647na-ew.a.run.app`)
- **Audit** : Playwright pur, ~1 min, $0
- **Mode surveillance** : Actif — audit automatique post-déploiement

---

## 💬 MOT DE L'ARCHITECTE

> La prochaine valeur ajoutée ne viendra plus des fonctionnalités. Elle viendra de l'expérience utilisateur, du design, de l'identité visuelle et de l'impression qu'a l'utilisateur lorsqu'il entre dans son espace de réflexion Iris.
