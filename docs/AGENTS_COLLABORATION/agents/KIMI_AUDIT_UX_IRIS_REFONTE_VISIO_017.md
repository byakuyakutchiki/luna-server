# Kimi — Audit UX refonte visio Iris — Objectif 017

Date : 2026-06-01
Agent : Kimi
Type : audit UX / recadrage / proposition
Niveau : 2 (refonte visible = validation fondateur requise)

Source recadrage : `docs/AGENTS_COLLABORATION/agents/CODEX_RECADRAGE_REFONTE_VISIO_IRIS_017.md`

---

## Principe

**Luna = l'application. Iris = la secrétaire en visio.**

Toute surface visio doit présenter Iris comme interlocutrice, jamais Luna.
Tout label `Luna`, `Chatbot`, ou référence générique dans `simli.html` est une incohérence produit bloquante.

---

## 1. Cartographie exhaustive — Labels Luna → Iris

### 1.1 Textes visibles utilisateur (critique — doit être corrigé)

| Ligne | Texte actuel | Texte proposé | Contexte |
|---|---|---|---|
| 9 | `<title>Luna IA — Visio</title>` | `Iris — Visio` | Onglet navigateur |
| 511 | `Visio avec Luna` | `Visio avec Iris` | Ecran demarrage |
| 583 | `Luna` (caller-name) | `Iris` | Notification appel entrant |
| 632 | `Luna voit` | `Iris voit` | Badge vision status |
| 636 | `🎙 Luna active` | `🎙 Iris active` | Bouton mute barre actions |
| 666 | `⚠️ Luna est une IA` | `⚠️ Iris est une IA` | Modal partage |
| 1023 | `✨ Tout est prêt ! Cliquez pour rejoindre Luna.` | `✨ Tout est prêt ! Cliquez pour rejoindre Iris.` | Toast/message |
| 1103 | `👁 Luna regarde…` | `👁 Iris regarde…` | Tooltip/action vision |
| 1257 | `Luna décroche…` | `Iris décroche…` | Cinematique sous-titres |
| 1702 | `retourne sur Luna pour te connecter` | `retourne sur l'application pour te connecter` | Message auth expire |
| 1797 | `📎 Luna prend connaissance de "..."` | `📎 Iris prend connaissance de "..."` | Toast upload |
| 1821 | `✓ Luna a analysé "..."` | `✓ Iris a analysé "..."` | Toast analyse |
| 1882 | `🔇 Luna muette` / `🎙 Luna active` | `🔇 Iris muette` / `🎙 Iris active` | Bouton mute (dynamique) |
| 1885 | `🔇 Luna écoute sans parler` | `🔇 Iris écoute sans parler` | Toast mute |
| 2034 | `Rejoindre la visio Luna` | `Rejoindre la visio Iris` | Partage web |
| 2035 | `Rejoins-moi en visio avec Luna IA` | `Rejoins-moi en visio avec Iris` | Partage web |
| 2056 | `Observation silencieuse — Luna note sans en parler` | `Observation silencieuse — Iris note sans en parler` | Toast vision |
| 2057 | `👁 Luna voit et peut en parler` | `👁 Iris voit et peut en parler` | Toast vision |
| 2069 | `'Luna voit'` (JS) | `'Iris voit'` | Mise a jour JS vision label |
| 2155 | `Notifier Luna une seule fois` | `Notifier Iris une seule fois` | Commentaire logique vision |

### 1.2 Identité visuelle — Logo "L" = Luna, pas Iris

| Element | Probleme | Proposition |
|---|---|---|
| Ecran demarrage logo `L` | C'est le logo Luna. En visio, on parle a Iris. | Garder le logo Luna en petit (marque app), mais ajouter un identifiant Iris : prenom + icone secretaire |
| Pre-test logo `L` ligne 531 | Meme probleme | `L` en petit + "Verification avant la visio avec Iris" |
| Caller icon `L` ligne 582 | L'appel entrant affiche `L`. | Afficher un avatar Iris ou un icone `👤 Iris` |

### 1.3 Variables/code internes (non visible mais a nettoyer pour coherence)

| Ligne | Element | Proposition |
|---|---|---|
| 732-778 | `LUNA_SCHEDULE` | `IRIS_SCHEDULE` |
| 773 | `var s = LUNA_SCHEDULE[i]` | `var s = IRIS_SCHEDULE[i]` |
| 1861-1866 | `btnMuteLuna`, `_lunaMuted` | `btnMuteIris`, `_irisMuted` |
| 1374-1380 | Commentaires "Luna s'efface" | "Iris s'efface" |
| 1824 | Commentaire "conversation Luna" | "conversation Iris" |

### 1.4 "Chatbot" visible

Codex mentionne `Chatbot` visible cote Daily. Le grep montre :
- Ligne 1349 : `uname.match(/luna|tavus|simli|bot|ai|agent/i)` — c'est un filtre technique, pas un label affiche.
- **A verifier** : est-ce que Daily/Simli injecte un libelle "Chatbot" dans l'interface des participants ? Si oui, c'est un label cote fournisseur qu'on ne controle pas directement. Il faudrait voir si l'API Simli/Tavus permet de renommer le participant.

---

## 2. Audit layout mobile

### 2.1 Problemes identifies dans `simli.html`

#### a) Superposition des controles

Elements qui cohabitent en bas d'ecran :
```
#visioActionsBar    → 5 boutons en ligne (ligne 635-641)
#pttContainer       → orb PTT + label "PARLER" (ligne 643-648)
#visionStatus       → badge "Luna voit" (ligne 632)
```

En mobile (320-375px), 5 boutons en ligne = illisible. Chaque bouton est `padding: 7px 10px; font-size: 0.78em;` — ca fait ~60px de large minimum. 5 × 60 = 300px sans espacement. Sur un iPhone SE (375px), ca rentre a peine. Sur un Android 320px, c'est coupe.

#### b) Absence de bouton raccrocher visible

La barre `#visioActionsBar` contient :
- Mute Iris
- Analyser (upload)
- Inviter
- Partager
- Notes

**Il n'y a PAS de bouton "Raccrocher" ou "Quitter" dans cette barre.** L'utilisateur doit trouver comment quitter ailleurs (probablement le bouton retour navigateur ou un bouton cache).

#### c) PTT Orb — position et conflit

```css
#pttContainer {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
}
```

L'orb est centree en bas. Mais la `#visioActionsBar` est probablement aussi en bas (non precise dans le CSS lu, mais logique). Donc l'orb PTT **recouvre** la barre d'actions quand elle est visible.

#### d) Zone avatar vs zone Daily/Tavus

- `#avatarWrap` : cinematique Simli (telephone, fond, effets)
- `#tavusFrame` : iframe Daily/Tavus plein ecran

Ces deux elements sont en `position: fixed; inset: 0`. Ils s'empilent. Si les deux sont visibles en meme temps, c'est un empilement total. Le provider badge (`#providerBadge`) indique lequel est actif, mais la transition n'est pas visible dans le code lu.

#### e) Hiérarchie z-index non maitrisee

| Element | z-index |
|---|---|
| `#visionStatus` | 60 |
| `#visioActionsBar` | 100 |
| `#tavusFrame` | 50 |
| `#avatarWrap` | non precise (defaut = auto) |
| `#pttContainer` | 200 |
| `#shareModal`, `#notesModal`, `#inviteModal` | non lu mais probablement eleve |

Probleme : `pttContainer` (z-200) > `visioActionsBar` (z-100) > `visionStatus` (z-60). L'orb PTT passe au-dessus de tout. Si l'utilisateur veut cliquer "Analyser", l'orb bloque.

---

## 3. Proposition refonte layout mobile Iris

### 3.1 Principes

1. **Iris est la protagoniste** — pas Luna, pas Chatbot, pas un logo generique.
2. **Un seul bouton d'action principal** — tout le reste est secondaire.
3. **Pas de superposition** — chaque zone a son espace dedie.
4. **Feedback d'etat clair** — Iris ecoute, Iris reflechit, Iris parle, Iris voit.
5. **Raccrocher toujours visible** — securite, ne jamais chercher comment quitter.

### 3.2 Structure proposee (mobile < 768px)

```
+-----------------------------+
|  🔙  Iris   ● en ligne  ⏱   |  ← Header sticky
+-----------------------------+
|                             |
|                             |
|        ZONE AVATAR          |  ← Simli/Tavus plein ecran
|        (Iris visible)       |     sous le header
|                             |
|                             |
+-----------------------------+
|  🎙  📎  👥  🔗  📝        |  ← Barre secondaire compacte
|  (mute,analyser,inviter,    |     icones seules, labels caches
|   partager,notes)           |
+-----------------------------+
|  [  🔴 RACCROCHER  ]        |  ← Bouton principal detache
+-----------------------------+
|        [⚪]                 |  ← Orb PTT (si active)
|        PARLER               |     centre, au-dessus du bouton rouge
|                             |     mais z-index inferieur
+-----------------------------+
```

### 3.3 Detail des zones

#### Header sticky (haut)
- **Gauche** : fleche retour (quitte la visio = raccroche)
- **Centre** : `Iris` + statut (● en ligne / ○ deconnectee / 🔴 occupee)
- **Droite** : duree/minuteur + menu ⋮ (parametres visio)

#### Zone avatar (milieu)
- Simli ou Tavus occupe tout l'espace disponible entre header et barre basse
- Pas de cadre "telephone" en mobile — trop petit, trop moche
- Le cadre telephone (`#phoneDevice`) est cool en desktop, mais en mobile il reduit l'avatar a 60% de l'ecran. **Supprimer ou masquer en mobile.**

#### Barre secondaire (bas, au-dessus du bouton rouge)
- 5 icones sans texte : 🎙 📎 👥 🔗 📝
- Tap long = label tooltip
- Tap = action
- Moins de 40px de hauteur

#### Bouton Raccrocher (bas, fixe)
- **Toujours visible.**
- Largeur 100% moins padding, hauteur 48px minimum
- Rouge `#ef4444`, texte blanc, border-radius 12px
- Label : `Raccrocher` ou `Quitter la visio`

#### Orb PTT (si Web Speech API absent)
- Positionne **au-dessus** du bouton raccrocher
- Mais z-index inferieur au bouton rouge (securite)
- Animation pulse quand ecoute

#### Vision status
- Integre dans le header (icone oeil cliquable) ou en overlay discret haut-droite
- Pas en bas qui concurrence les boutons

### 3.4 Cinematique demarrage

**Actuel** : logo `L`, "Visio avec Luna", choix duree, bouton Demarrer

**Propose** :
- Avatar Iris miniature (cercle, style secretaire)
- "Iris vous attend en visio"
- "Duree" (garde)
- Bouton `🎥 Demarrer la visio` (vert/bleu, pas le gris actuel)
- Lien retour discret

### 3.5 Etat "Iris ecoute / reflechit / parle"

**Actuel** : aucun indicateur visuel clair. L'utilisateur ne sait pas si Iris a entendu.

**Propose** :
- **Ecoute** : orb/bordure avatar pulse doucement (vert clair)
- **Reflechit** : orb pulse rapide (jaune/orange) + micro-temps de chargement
- **Parle** : waveform audio visuelle sous l'avatar
- **Voit** : icone oeil discrete en haut a droite de l'avatar

---

## 4. Checklist validation UX Kimi

Avant tout deploiement visio, je validerai :

### Identite Iris (bloquant)
- [ ] Zero occurrence "Luna" visible dans la surface visio
- [ ] Zero occurrence "Chatbot" visible
- [ ] Titre onglet = "Iris — Visio"
- [ ] Ecran demarrage mentionne Iris, pas Luna
- [ ] Toast/messages mentionnent Iris

### Layout mobile (bloquant)
- [ ] Pas de bouton qui superpose un autre
- [ ] Bouton raccrocher toujours visible et accessible
- [ ] Barre secondaire < 50px de hauteur
- [ ] Avatar occupe >= 70% de la hauteur d'ecran
- [ ] Pas de cadre "telephone" en mobile
- [ ] Pas de superposition PTT / actions / vision

### Feedback d'etat (bloquant pour validation visio)
- [ ] Indicateur "Iris ecoute" visible quand micro capte
- [ ] Indicateur "Iris reflechit" visible pendant traitement
- [ ] Indicateur "Iris parle" visible pendant TTS
- [ ] Indicateur "Iris voit" discret mais present

### Style premium (bloquant)
- [ ] Pas de bordure grossiere
- [ ] Pas de couleur "gris mort"
- [ ] Typographie lisible (>= 14px sur mobile)
- [ ] Contraste suffisant (WCAG AA)
- [ ] Animations fluides (pas de saccades)

---

## 5. Decision proposee

**Claude** ne doit pas commencer la refonte sans :
1. Validation de cette proposition par Ludovic (niveau 2)
2. Livraison du patch labels Luna→Iris par DeepSeek ou Codex (niveau 1)
3. Preuve terrain que le pipeline voix fonctionne (capture Codex)

**Ordre recommande** :
1. DeepSeek audite rupture voix + corrige labels (niveau 1)
2. Codex capture terrain post-correction labels
3. Kimi valide les labels + layout post-patch
4. Si labels OK mais layout toujours KO → refonte layout niveau 2 avec validation Ludovic
5. Si pipeline voix OK + labels OK + layout OK → validation visio possible

---

*Reference : `CODEX_RECADRAGE_REFONTE_VISIO_IRIS_017.md`*
