# Audit Visuel Luna 2026
## Direction artistique : "Luna Cinematic Operating System"

**Date** : 13 juin 2026  
**Auditeur** : Claude (Lead technique / DA front-end)  
**URL** : https://luna-beta-674304336025.europe-west1.run.app  
**Captures** : 18 screenshots — desktop 1440×1000 + mobile 390×844  
**Branche** : `visual/luna-cinematic-os-audit`

---

## Résumé exécutif

Luna est une application premium avec une identité forte en émergence. Le potentiel narratif est là — l'univers YAWatch Industries, la dualité Luna/Iris, la tension entre protection et présence. Mais l'interface actuelle ne le raconte pas encore pleinement. Les points d'entrée secondaires (Iris Visio, Admin) sont visuellement orphelins. La page principale donne une bonne base. Le Workspace a un squelette solide mais reste trop générique derrière sa modale d'entrée.

**Score global : 5,6 / 10**

---

## Pages auditées

### 1. Écran de connexion — `desktop_00_login_screen.png`

**Note : 7,5 / 10**

**Ce qui fonctionne**
- Le fond radial gradient (violet profond + halos diffus) installe immédiatement une atmosphère premium nocturne
- La carte glassmorphism est bien équilibrée : ni trop opaque, ni trop transparente
- Le logo YAWatch est lisible et centré
- "YAWATCH INDUSTRIES" en lettres espacées donne du statut
- Contraste email/password/bouton lisible

**Ce qui dérange**
- Le fond est beau mais statique — aucune vie, aucun mouvement
- Le bouton "Se connecter" violet plein manque de signature Luna (pas de halo vert émeraude, pas de tension)
- Aucun signe de Luna elle-même — pas de présence, pas d'indice narratif
- "LUNA" en titre est correct mais sans personnalité typographique forte

**Correction rapide**  
Ajouter un léger breathing effect (pulse scale 1.0→1.02 sur le fond, 8s) + teinte le bouton CTA avec un halo émeraude au hover.

**Correction ambitieuse**  
Fond vivant : particules lentes (type étoiles/grille perspective), présence de Luna en silhouette très atténuée derrière la carte (opacity 0.04–0.06), animation d'entrée de la carte (fade+slide from bottom 600ms).

---

### 2. Page principale — Chat — `desktop_01_home.png` + `mobile_01_home.png`

**Note desktop : 5,5 / 10 | Note mobile : 6 / 10**

**Ce qui fonctionne**
- La sidebar des conversations est fonctionnelle et lisible
- Le gradient violet/indigo en fond du chat donne de la profondeur
- La barre d'onglets supérieure est organisée
- Sur mobile, la pleine largeur fonctionne bien

**Ce qui dérange**
- Le message d'erreur "Luna est temporairement injoignable" apparaît comme un composant bubble générique — aucune mise en scène émotionnelle
- La zone de chat centrale est une grande surface vide sans texture ni présence
- Le haut de page (avatar + "Luna • 19°C") est trop dense sur une seule ligne, confusion entre statut technique et présence affective
- Les onglets de la barre sont des icônes texte monochrome sans hiérarchie visuelle claire
- Sur desktop, la sidebar gauche est très sombre et plate — pas de séparation nette avec le fond

**Correction rapide**  
Ajouter un halo vert émeraude très atténué (radial-gradient centré bas de l'écran chat, opacity 0.06) qui pulse doucement quand Luna "pense".

**Correction ambitieuse**  
Zone de chat vide : afficher une signature visuelle de Luna (ligne de code / fragment de lore, opacity 0.05) en filigrane. Avatar Luna animé (respiration légère). Onglets avec icônes SVG redessinées dans le design system Luna.

---

### 3. Menu rapide flottant — `desktop_02_home_action_menu.png`

**Note : 5 / 10**

**Ce qui fonctionne**
- Les 3 raccourcis sont clairs et nommés (Appeler un contact, Iris Workspace, Activités)
- Les couleurs des cercles (bleu, vert, orange) différencient bien les actions
- L'animation d'expansion FAB fonctionne

**Ce qui dérange**
- Les cercles sont plats, sans profondeur — ils ressemblent à des boutons Bootstrap génériques
- L'icône d'Iris Workspace (grille) ne raconte pas assez le produit
- Aucune connexion visuelle entre ces raccourcis et l'univers Luna
- La position bas-droite est correcte mais les labels (texte blanc sur fond sombre) manquent de lisibilité sur des fonds complexes

**Correction rapide**  
Ajouter un fond glassmorphism léger derrière chaque item du menu (backdrop-blur + border 1px rgba(255,255,255,0.1)).

**Correction ambitieuse**  
Remplacer les cercles plats par des capsules avec micro-glow coloré (vert pour Workspace, violet pour Visio). Animation d'entrée staggerée (chaque item 60ms après le précédent).

---

### 4. Iris Visio — `desktop_17_simli.png` + `mobile_18_simli.png`

**Note desktop : 3,5 / 10 | Note mobile : 4,5 / 10**

**Ce qui fonctionne (mobile uniquement)**
- Sur mobile, le layout centré fonctionne bien dans l'espace restreint
- Le bouton "Démarrer" vert grand format sur mobile est excellent — action claire, forte
- "← Retour au chat" est discret et bien placé

**Ce qui dérange**
- Le fond est un bleu nuit uni et froid — aucune atmosphere, aucune tension, aucun cinéma
- L'avatar "L" (initiale dans un cercle violet) est un placeholder — Luna mérite sa présence visuelle ici
- "Iris Visio" comme titre fonctionne mais manque de mise en scène — c'est l'entrée vers quelque chose d'intense, ça devrait le signaler
- Le sélecteur "Durée de l'appel" (dropdown HTML natif) casse le design premium
- Sur desktop, la surface inutilisée autour de la carte est immense et vide
- Zéro lien visuel avec la cinématique qui suit (les 9 décors SVG, la sonnerie, le zoom) — rupture de ton

**Correction rapide**  
Remplacer le fond uni par le gradient déjà utilisé sur l'écran de login (radial halos violet/émeraude). Remplacer le dropdown natif par un custom selector stylisé.

**Correction ambitieuse**  
Remplacer "L" par un avatar Luna animé (silhouette, ou photo atténuée en cercle avec glow). Fond : une des 9 scènes SVG de la cinématique (décor nocturne, Ken Burns en boucle lente, opacity 0.3). La page devient l'antichambre de la cinématique — même univers, même tension.

---

### 5. Page Admin — `desktop_18_admin.png`

**Note : 2 / 10**

**Ce qui fonctionne**
- La carte de login est fonctionnelle
- Le bouton "Se connecter" est visible

**Ce qui dérange**
- Fond noir absolu (#020810 ou similaire) — aucune atmosphère, aucune identité
- "Luna Admin" en violet est la seule marque de l'univers sur la page
- La carte flotte dans un vide total — aucune grille, aucun halo, aucune texture
- Pas de logo YAWatch Industries
- Aucune indication que c'est une interface fondateur/exploitant (statut spécial)
- Visuellement indiscernable d'une page de login générique SaaS

**Correction rapide**  
Copier le fond radial-gradient de la page login. Ajouter le logo YAWatch en haut de la carte.

**Correction ambitieuse**  
Ajouter un bandeau "YAWatch Industries — Accès Opérateur" au-dessus de la carte. Fond avec grille perspective atténuée (SVG ou CSS) + halos verts très doux (couleur Iris). Carte avec border vert émeraude opacity 0.3 (distingue l'admin de l'espace utilisateur).

---

### 6. Iris Workspace — Modale d'entrée — `desktop_ws_01_entry.png` + `mobile_17_workspace.png`

**Note desktop : 6 / 10 | Note mobile : 6,5 / 10**

**Ce qui fonctionne**
- La modale "Iris Workspace" avec le dot vert pulsant est une signature forte — le point de présence IA est une bonne idée
- Le champ "Votre prénom" + sélection de rôle (Participant / Owner / Spectateur) est fonctionnel et clair
- Le bouton "ENTRER →" en style monospace capsule est premium
- Sur mobile, la modale occupe bien l'espace et est très lisible
- Les photos GTA floutées en arrière-plan donnent de la profondeur et de la personnalité — **elles doivent être préservées**

**Ce qui dérange**
- La modale bloque l'accès au canvas — impossible de voir le workspace derrière avant d'entrer. Cela crée une friction pour l'utilisateur solo
- Les boutons de rôle (outlined) sont trop semblables entre eux — le rôle actif (Participant) est peu mis en valeur
- Le fond sous la modale (workspace en dessous, flou) est très sombre — les photos GTA sont là mais à peine lisibles
- Aucune indication de ce qui attend derrière la modale (pas de preview, pas de contexte de session)

**Correction rapide**  
Améliorer le contraste du rôle sélectionné (fond solid vert + texte blanc). Ajouter une micro-description "Session en cours — X participants" si disponible.

**Correction ambitieuse**  
Mode solo : si l'utilisateur est seul, bypasser automatiquement la modale (pré-remplir depuis le profil, entrer directement en Owner). Modale solo vs multi — deux flux visuels distincts. Ajouter un aperçu animé du canvas derrière (très flou, opacity 0.2) pour donner envie d'entrer.

---

### 7. Iris Workspace — États canvas (ws_02, ws_04, ws_12)

**Note : 4 / 10**

**Observation critique** : Tous les états ws_02 (brief), ws_04 (proposition), ws_12 (export) affichent encore la modale d'entrée — le canvas lui-même n'est pas encore accessible sans interaction manuelle. L'audit ne peut pas capturer les états internes automatiquement. C'est un bug de l'audit script (la modale JS bloque le `page.evaluate`), pas un bug produit.

**Ce qui ressort des captures partielles**
- Le canvas workspace est très sombre, quasi invisible derrière la modale
- La stepper barre en haut (si présente) n'est pas lisible dans les captures
- Les photos GTA (Luna + personnage) dans le coin supérieur droit sont bien placées — elles ancrent l'univers

**Ce qui manque visuellement**
- Le canvas vide ne signale pas l'attente — pas de grain, pas de texture, pas de "surface de réflexion"
- Les objets (propositions, décisions) apparaissent-ils avec animation ? Impossible à confirmer depuis ces captures
- Pas de différenciation visuelle entre les 13 étapes du stepper

**Correction rapide**  
Ajouter une texture très légère sur le fond du canvas (grain film 0.03 opacity ou grille 1px rgba(255,255,255,0.03)).

**Correction ambitieuse**  
Canvas vivant : quand vide, afficher une animation "en attente" (curseur qui pulse, ou ligne de réflexion qui se dessine lentement). Chaque objet ajouté (proposition, décision, action) entre avec une animation de matérialisation (fade + scale from 0.95). Le stepper supérieur s'éclaire progressivement au fil des étapes.

---

## Synthèse — 5 problèmes visuels majeurs

| # | Problème | Impact | Page(s) |
|---|---|---|---|
| 1 | **Iris Visio sans atmosphère** — fond uni froid, avatar générique "L", aucun lien avec la cinématique qui suit | Rupture de ton avant l'expérience la plus premium | `/simli` |
| 2 | **Admin visuellement mort** — fond noir vide, carte flottante sans contexte ni marque | Crédibilité opérateur nulle | `/admin` |
| 3 | **Zone de chat statique** — grande surface sans vie ni présence de Luna | Pas de feedback émotionnel quand l'IA réfléchit | `/` (zone chat) |
| 4 | **Workspace inaccessible sans modale** — le canvas est invisible avant interaction, états intermédiaires non capturables | Friction solo, pas de preview de valeur | `/team` |
| 5 | **Menu FAB plat** — raccourcis sans profondeur, sans lien avec l'univers Luna | Entrées secondaires génériques | `/` (FAB) |

---

## Direction artistique recommandée : "Luna Cinematic Operating System"

### Concept

Une interface d'exploitation émotionnelle, premium, vivante, où Iris/Luna semble construire la pensée devant l'utilisateur. Chaque écran est une scène, pas un formulaire.

### 6 axes de montée graphique

**1. Fond vivant subtil** *(priorité : haute)*  
Remplacer les fonds unis (`#020810`, bleu nuit plat) par un système de halos radiaux animés. Trois niveaux :
- Fond base : `#020810` → `#06091a` (gradient directionnel)
- Halos permanents : violet `rgba(124,58,237,0.12)` + émeraude `rgba(16,185,129,0.06)` (radial, statiques)
- Halos actifs : pulse 6–8s au-dessus quand Luna "réfléchit" ou qu'une IA répond

**2. Signature Luna** *(priorité : moyenne)*  
Fragments visuels issus de l'univers — pas partout, aux bons moments :
- Écran de login : silhouette Luna en filigrane derrière la carte (opacity 0.04)
- Iris Visio : scène SVG nocturne de la cinématique en fond (opacity 0.25–0.35)
- Workspace canvas : grain film + trait de réflexion en attente

**3. Workspace vivant** *(priorité : haute)*  
- Chaque objet (proposition, décision, action, réserve) entre avec une animation de matérialisation
- Les connexions entre objets se dessinent en temps réel
- La décision finale "se scelle" avec une animation de validation
- Le dossier final "se compile" avec un effet de fermeture progressive

**4. États IA visibles** *(priorité : haute)*  
Quatre états distincts avec signal visuel :
- **Écoute** : halo vert émeraude pulsant sur l'avatar
- **Réflexion** : animation de chargement premium (pas de spinner — lignes qui se tracent)
- **Synthèse** : l'Iris Command Screen s'anime en apparaissant
- **Décision/Export** : animation de validation + couleur or/ambre pour marquer l'importance

**5. Micro-animations métier** *(priorité : moyenne)*  
- Carte proposition : fade + scale 0.95→1.0 + border flash émeraude (200ms)
- Source ancrée : élément qui "se fixe" avec un micro-bounce
- Décision scellée : icône cadenas + pulse radial
- Dossier final compilé : animation de fermeture + timestamp apparaît

**6. Design system cohérent** *(priorité : basse mais structurante)*  
Tokens CSS à définir et appliquer uniformément :
```css
--luna-bg-base: #020810;
--luna-bg-panel: #0d1117;
--luna-violet: #7c3aed;
--luna-iris: #10b981;
--luna-gold: #f59e0b;
--luna-text-primary: #e5e7eb;
--luna-text-secondary: #6b7280;
--luna-border: rgba(255,255,255,0.08);
--luna-glow-violet: rgba(124,58,237,0.15);
--luna-glow-iris: rgba(16,185,129,0.12);
```

---

## Feuille de route Phase 1 (sans casser aucune fonctionnalité)

| Priorité | Action | Fichier | Risque |
|---|---|---|---|
| 🔴 | Fond + halos vivants sur `/simli` (login screen de Iris Visio) | `static/simli.html` | Nul |
| 🔴 | Fond + logo sur `/admin` | `static/admin.html` | Nul |
| 🟡 | Halo pulsant sur zone chat quand Luna répond | `static/index.html` | Nul |
| 🟡 | Custom select "Durée appel" sur `/simli` | `static/simli.html` | Faible |
| 🟢 | Tokens CSS unifiés dans un fichier `static/luna-design-system.css` | Nouveau fichier | Nul |
| 🟢 | Animation matérialisation objets Workspace | `static/team_workspace.html` | Faible |

---

## Commandes de reproduction

```bash
# Reproduire l'audit
git checkout visual/luna-cinematic-os-audit
python3 tools/audit_visual_luna_2026.py

# Voir les captures
ls docs/audit_visual/luna-2026-visual-sweep-20260613-1039/

# Dossier complet
open docs/audit_visual/luna-2026-visual-sweep-20260613-1039/index.md
```

---

*Audit produit sur branche `visual/luna-cinematic-os-audit` — aucune modification fonctionnelle effectuée.*  
*Ne pas merger sur `main` sans validation fondateur.*
