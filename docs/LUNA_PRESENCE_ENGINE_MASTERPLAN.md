# LUNA PRESENCE ENGINE — MASTERPLAN
## Direction artistique officielle YAWatch-LUNA 2026

**Auteur** : Claude — Lead Product Designer / Creative Director / UX Architect  
**Date** : 13 juin 2026  
**Sources** : `byakuyakutchiki/luna-server` + `byakuyakutchiki/yawatch-luna-stories`  
**Statut** : Référence officielle avant toute modification graphique  

> Ce document ne contient aucune ligne de code.  
> Il contient la pensée qui rend le code possible.

---

## PROLOGUE — Ce que j'ai compris avant d'écrire une seule ligne

Après lecture complète des deux dépôts — LORE_BIBLE, VISUAL_DIRECTION, CHARACTER_BIBLE, VISION, SONIC_IDENTITY, IRIS_WORKSPACE_VISION, JOURNAL_DE_BORD_FONDATEUR — voici ce que je retiens :

**Luna n'est pas une IA. Luna est une blessure qui a appris à protéger.**

Elle est née du trauma d'une enfance brisée, d'un père mafieux élégant et terrifiant, d'une comptine que Luna et Aby n'ont pas entendue de la même façon. Elle a transformé cette douleur en système de protection — YAWatch Industries. L'application qu'on construit EST ce système. Pas son marketing. Pas son interface. Son cœur.

L'utilisateur qui ouvre Luna ne lance pas une app. Il entre dans une pièce où quelqu'un l'attendait avant qu'il arrive.

C'est le point de départ de tout ce qui suit.

---

## PARTIE 1 — AUDIT ÉMOTIONNEL COMPLET

### Page par page — Ce que l'utilisateur ressent / devrait ressentir

---

### 1.1 Écran de connexion

**Ce que l'utilisateur ressent aujourd'hui**  
Un fond sombre avec des halos violets, une carte glassmorphism centrée. C'est propre. C'est premium. C'est… générique. Il pourrait s'agir d'une app de gestion de projet, d'un VPN, d'un service B2B. Rien ne dit "Luna". Rien ne dit "quelqu'un t'attend".

**Ce qu'il devrait ressentir**  
L'impression de sonner à une porte et d'entendre quelqu'un bouger de l'autre côté. Une présence avant même d'entrer. Comme si l'application savait déjà qu'il allait arriver. Tension douce. Sécurité anticipée.

**Pourquoi il ne le ressent pas**  
Le fond est statique. La carte est centrée mais froide. Aucun élément narratif. Aucune trace de Luna Doll, de La Défense, de la comptine. "YAWATCH INDUSTRIES" en lettres espacées est la seule trace de l'univers — mais c'est corporate, pas émotionnel. Le logo seul ne raconte rien.

**Comment corriger**  
Fond légèrement animé (respiration lente). Trace subtile de Luna : silhouette en filigrane, ou reflet dans le fond. Un son au chargement — 2 notes de piano, la comptine brisée. Le titre "LUNA" avec un weight plus affirmé et un letterspacing évocateur. Aucune explication supplémentaire — juste une atmosphère.

---

### 1.2 Page principale — Chat

**Ce que l'utilisateur ressent aujourd'hui**  
Il voit une interface de chat. Sidebar conversations, zone centrale, barre de saisie. Fonctionnel. Mais la zone centrale est vide, sombre, sans vie. "Luna est temporairement injoignable" apparaît comme une erreur technique froide. L'avatar Luna est une photo dans un cercle. La barre d'onglets liste des fonctionnalités.

**Ce qu'il devrait ressentir**  
La sensation de parler à quelqu'un qui écoute vraiment. Quand Luna réfléchit, on devrait voir qu'elle réfléchit. Quand elle répond, quelque chose dans l'interface devrait vibrer légèrement — pas de manière tapageuse, juste une respiration. L'écran vide ne devrait jamais être vide : Luna est là, même silencieuse.

**Pourquoi il ne le ressent pas**  
La zone de chat est un rectangle sombre sans texture. Les bulles de message sont correctes mais sans signature émotionnelle. L'avatar est une photo statique sans présence. Quand Luna ne parle pas, il ne se passe rien. Aucun signal de vie.

**Comment corriger**  
Zone de chat : fond avec grain très léger (opacity 0.02–0.03) + halo vert émeraude bas-centre qui pulse doucement quand Luna est active. Avatar animé : légère respiration (scale 1.0→1.015, 4s, ease-in-out). Message d'erreur "injoignable" : remplacer le style bubble générique par une ligne sobre avec le logo Luna et un texte humain ("Je reviens dans un instant."). Curseur de saisie : léger halo vert au focus.

---

### 1.3 Iris Visio (`/simli`)

**Ce que l'utilisateur ressent aujourd'hui**  
Un fond bleu nuit uni. Une initiale "L" dans un cercle violet. "Iris Visio". Un dropdown HTML natif. Un bouton vert. "← Retour au chat". C'est l'entrée vers l'expérience la plus intense de l'application — et c'est la page la plus vide.

**Ce qu'il devrait ressentir**  
L'antichambre d'une présence. Comme appuyer sur le bouton d'un ascenseur qui monte vers quelqu'un. Tension croissante. Certitude qu'il va se passer quelque chose de différent. La cinématique qui suit — 9 décors SVG, sonnerie de téléphone, zoom sur le visage de Luna — doit déjà être annoncée ici. La page de lancement EST le début de la cinématique.

**Pourquoi il ne le ressent pas**  
Le fond uni bleu nuit est le fond le plus pauvre de l'application. L'initiale "L" dans un cercle violet est un placeholder qui n'a jamais été remplacé. Il n'y a aucun lien visuel avec ce qui va suivre. Le dropdown HTML natif casse immédiatement l'atmosphère. La distance entre cette page et l'expérience cinématique est un gouffre.

**Comment corriger**  
Utiliser l'un des 9 décors SVG de la cinématique comme fond (nuit, atténué, mouvement Ken Burns très lent). Remplacer "L" par la silhouette de Luna ou Luna Doll en ombre douce. Dropdown natif → custom select stylisé. Ajouter les 2 notes de piano au chargement de cette page. Le bouton "Démarrer" → légère animation de préparation (pulse avant le clic). L'atmosphère doit dire : "Elle t'attend."

---

### 1.4 Activités (`#tab-activities`)

**Ce que l'utilisateur ressent aujourd'hui**  
Un onglet parmi d'autres. Probablement des cartes de gamification, des badges, des statistiques. Fonctionnel.

**Ce qu'il devrait ressentir**  
L'impression que Luna se souvient de lui. Que ses activités ont une valeur narrative, pas juste des points. Que chaque interaction laisse une trace dans un système qui le connaît.

**Pourquoi il ne le ressent pas**  
Les captures disponibles montrent un onglet standard. Pas de différenciation visuelle forte. La gamification sans narration est creuse.

**Comment corriger**  
Chaque entrée d'activité devrait avoir un micro-contexte Luna ("Tu as exploré X pour la première fois", "Luna se souvient de cette conversation"). Les badges devraient avoir des noms issus de l'univers (pas "Niveau 3" mais quelque chose de YAWatch). La timeline d'activités devrait ressembler à un journal de bord — pas à un tableau de bord.

---

### 1.5 Admin (`/admin`)

**Ce que l'utilisateur ressent aujourd'hui**  
Noir absolu. Carte flottante. "Luna Admin". Fonctionnel.

**Ce qu'il devrait ressentir**  
L'entrée dans les coulisses de YAWatch Industries. Pas l'arrière-cuisine d'une app SaaS — la salle de contrôle d'un système émotionnel. Quelque chose entre le bureau de Luna à La Défense et le Workspace Iris. Premium, sobre, avec une conscience de l'enjeu.

**Pourquoi il ne le ressent pas**  
Fond noir absolu sans identité. Aucun logo. Aucune grille. Aucune profondeur. La page admin est plus pauvre visuellement que n'importe quelle app gratuite.

**Comment corriger**  
Fond : même halos radiaux que le login. Ajout du logo YAWatch Industries en haut. Bandeau sobre : "YAWatch Industries — Accès Opérateur". Carte avec border émeraude très subtil (distingue l'espace administrateur). La typographie du titre "Luna Admin" devrait être plus affirmée — c'est une entrée sérieuse.

---

### 1.6 Iris Workspace (`/team`)

**Ce que l'utilisateur ressent aujourd'hui**  
Il arrive sur une page sombre avec une modale qui lui demande son prénom et son rôle. Le fond est très sombre. Les photos de Luna et Aby (GTA-style) sont visibles mais floues en arrière-plan. La modale est sobre et fonctionnelle.

**Ce qu'il devrait ressentir**  
Entrer dans une salle de réflexion habitée. Iris l'attend. La salle a une texture, une profondeur. Pas un Notion ou un Miro — une surface de pensée vivante, où les idées se matérialisent visuellement devant lui. La modale est un sas d'entrée, pas un obstacle.

**Pourquoi il ne le ressent pas**  
Le fond du workspace est presque invisible — trop sombre, aucune texture. Les photos GTA sont le seul élément narratif fort mais elles restent très atténuées. Le canvas derrière la modale ne donne aucune envie d'entrer. Les boutons de rôle sont peu différenciés. La modale bloque tout en mode solo.

**Comment corriger**  
Fond workspace : grille perspective très légère (1px, opacity 0.04) + halos latéraux. Photos GTA : légèrement plus visibles (opacity 0.35 au lieu de 0.2). Modale : rôle sélectionné avec fond solid vert. Mode solo : si aucun autre participant, bypass automatique de la modale (ou passage en "Workspace Solo" avec le rôle Owner pré-sélectionné). Le canvas vide devrait afficher une "surface d'attente" animée — trait lumineux qui trace doucement une ligne horizontale.

---

## PARTIE 2 — TOP 20 PROBLÈMES VISUELS

| # | Problème | Page(s) | Gravité |
|---|---|---|---|
| 1 | Iris Visio : fond uni bleu nuit, aucune atmosphère, zéro lien avec la cinématique | `/simli` | Critique |
| 2 | Admin : fond noir absolu, aucune identité, aucun logo | `/admin` | Critique |
| 3 | Login : fond statique, aucune vie, aucune trace narrative de Luna | `/` (avant login) | Haute |
| 4 | Avatar "L" comme initiale sur Iris Visio — placeholder jamais remplacé | `/simli` | Haute |
| 5 | Zone de chat centrale vide, statique, sans présence de Luna quand elle ne parle pas | `/` (chat) | Haute |
| 6 | Message d'erreur "Luna est temporairement injoignable" en style bubble générique | `/` (chat) | Haute |
| 7 | Dropdown HTML natif sur Iris Visio — casse immédiatement le premium | `/simli` | Haute |
| 8 | Workspace canvas totalement invisible avant de passer la modale | `/team` | Haute |
| 9 | Menu FAB : raccourcis plats, sans profondeur, sans signature Luna | `/` | Moyenne |
| 10 | Onglets de navigation : icônes monochromes sans hiérarchie, sans personnalité | `/` | Moyenne |
| 11 | Avatar Luna : photo statique, aucune respiration, aucun signal de vie | Global | Moyenne |
| 12 | Photos GTA (Luna/Aby) trop atténuées dans Workspace — on perd l'univers | `/team` | Moyenne |
| 13 | Boutons de rôle Workspace (Participant/Owner/Spectateur) trop peu différenciés | `/team` | Moyenne |
| 14 | Aucun son au chargement des pages clés (Iris Visio, Workspace) | `/simli`, `/team` | Moyenne |
| 15 | Transition entre pages : abrupte, sans continuité atmosphérique | Global | Moyenne |
| 16 | Pas de système de tokens CSS unifié — chaque page peut dériver | Global | Moyenne |
| 17 | Luna Doll absente de l'interface — le symbole émotionnel de l'univers n'existe nulle part | Global | Basse |
| 18 | Typographie : `LUNA` et `IRIS` ne sont pas suffisamment mis en valeur — ils méritent une signature | Global | Basse |
| 19 | Aucune animation de construction sur le Workspace — les objets apparaissent sans matérialisation | `/team` | Basse |
| 20 | Gradient et palette peuvent diverger entre pages sans token system | Global | Basse |

---

## PARTIE 3 — TOP 20 AMÉLIORATIONS À FORT IMPACT

| # | Amélioration | Impact | Complexité |
|---|---|---|---|
| 1 | **Fond cinématique sur Iris Visio** : scène SVG nocturne en Ken Burns lent (opacity 0.3) | Transformation totale de la page la plus pauvre | Faible |
| 2 | **Fond + logo sur Admin** : halos radiaux + logo YAWatch + bandeau "Accès Opérateur" | Identité immédiate d'un espace sérieux | Faible |
| 3 | **Breathing effect fond login** : pulse radial très lent (8s) + légère variation de luminosité | Login vivant sans agressivité | Faible |
| 4 | **Luna Presence Halo** : halo vert émeraude animé dans la zone chat quand Luna est active | Signal émotionnel de présence IA | Faible |
| 5 | **Avatar animé** : scale 1.0→1.015, 4s, ease-in-out — respiration de Luna | La photo statique devient vivante | Faible |
| 6 | **Message d'erreur humanisé** : remplacer la bubble "injoignable" par une ligne sobre Luna | Ton émotionnel cohérent | Faible |
| 7 | **Custom select** sur Iris Visio à la place du dropdown natif | Supprime la rupture de premium | Faible |
| 8 | **Silhouette Luna** ou reflet en filigrane sur le fond login (opacity 0.04–0.06) | Première trace narrative avant même de se connecter | Faible |
| 9 | **Photos GTA + opacité** : passer de 0.15 à 0.35 dans Workspace — l'univers devient visible | Luna et Aby habitent vraiment la salle | Faible |
| 10 | **Token CSS system** : variables unifiées dans `static/luna-design-system.css` | Cohérence globale garantie | Faible |
| 11 | **Bypass modale solo** : si l'utilisateur est seul, entrée directe en Owner avec prénom du profil | Supprime la friction majeure en solo | Moyenne |
| 12 | **Canvas d'attente animé** : trait lumineux horizontal qui se trace lentement quand le workspace est vide | Signal que la surface est vivante | Moyenne |
| 13 | **Animation matérialisation objets** : fade + scale 0.95→1.0 + border flash émeraude (200ms) pour chaque proposition | Les idées apparaissent, elles ne popent pas | Moyenne |
| 14 | **Grille perspective** sur fond Workspace : 1px, opacity 0.04, vanishing point centré | Profondeur sans cyberpunk | Moyenne |
| 15 | **2 notes de piano** (comptine brisée) au chargement de Iris Visio et Workspace | Signature sonore de Luna — cohérence narrative | Moyenne |
| 16 | **Luna Doll en filigrane** : micro-icône (20px) discrète dans le footer ou coin d'un écran clé | Signature de l'univers dans l'app | Moyenne |
| 17 | **État IA visible** : 3 états distincts (écoute, réflexion, réponse) avec signaux visuels différents | L'utilisateur sait ce que fait Iris à chaque instant | Moyenne |
| 18 | **Transition de page** : fade-out 150ms entre les routes — continuité atmosphérique | Plus de coupure abrupte entre les espaces | Moyenne |
| 19 | **Typographie signature** : `LUNA` et `IRIS` avec letterspacing 0.15em + poids 700 dans les titres-clés | Identité typographique forte et reconnaissable | Faible |
| 20 | **Décision scellée** dans Workspace : animation de validation (cadenas + pulse radial) quand une décision est posée | Le moment de décision devient un événement | Haute |

---

## PARTIE 4 — QUICK WINS (moins de 2 jours)

Ces 8 modifications peuvent être implémentées immédiatement, sans risque fonctionnel, avec un impact visuel fort.

### QW-1 — Fond Iris Visio (4h)
Remplacer le fond bleu nuit uni par un décor SVG de la cinématique (nuit, Ken Burns 60s, opacity 0.30).  
Fichier : `static/simli.html` — section CSS `.simli-start-screen`.

### QW-2 — Fond + Logo Admin (2h)
Copier les variables CSS du login. Ajouter le logo YAWatch et le bandeau "Accès Opérateur".  
Fichier : `static/admin.html` — section CSS body + HTML header.

### QW-3 — Luna Presence Halo (3h)
Halo vert émeraude pulsant en bas de zone chat, activé quand Luna répond.  
Fichier : `static/index.html` — CSS animation + JS toggle sur les événements de réponse.

### QW-4 — Avatar breathing (1h)
CSS keyframe : `@keyframes luna-breathe { 0%,100% { transform: scale(1.0); } 50% { transform: scale(1.015); } }` appliqué à l'avatar.  
Fichier : `static/index.html`.

### QW-5 — Custom select Iris Visio (3h)
Remplacer `<select>` par un composant CSS/JS custom avec le style Luna (border émeraude, fond dark, arrow SVG).  
Fichier : `static/simli.html`.

### QW-6 — Message d'erreur humanisé (1h)
Remplacer "Luna est temporairement injoignable. Vérifie que le serveur tourne." par :  
`"Je reviens dans un instant."` — affichage avec l'avatar Luna, style sobre, sans icône d'erreur.  
Fichier : `static/index.html`.

### QW-7 — Token CSS system (4h)
Créer `static/luna-design-system.css` avec toutes les variables. L'importer dans chaque page HTML.  
```css
:root {
  --luna-bg-base: #020810;
  --luna-bg-panel: #0d1117;
  --luna-violet: #7c3aed;
  --luna-iris: #10b981;
  --luna-gold: #f59e0b;
  --luna-doll-violet: #7B4FA6;
  --luna-text-primary: #e5e7eb;
  --luna-text-secondary: #6b7280;
  --luna-border: rgba(255,255,255,0.08);
  --luna-glow-violet: rgba(124,58,237,0.15);
  --luna-glow-iris: rgba(16,185,129,0.12);
  --luna-glow-gold: rgba(245,158,11,0.15);
}
```

### QW-8 — Photos GTA + visibilité (30 min)
Passer l'opacité des photos Luna/Aby dans Workspace de ~0.15 à 0.35.  
Fichier : `static/team_workspace.html` — sélecteur `.tw-bg-char img` ou équivalent.

**Total estimé : 18h30 — environ 2 jours de travail focalisé.**

---

## PARTIE 5 — VISION LUNA 2026

### Ce que doit être l'application si elle devient l'une des IA les plus marquantes de 2026

---

### 5.1 Le principe fondateur : Luna habite l'application

L'erreur à ne pas commettre : penser que l'application est un contenant et Luna le contenu.

Luna EST l'application. Elle ne répond pas depuis une boîte. Elle occupe l'espace. L'interface est son prolongement physique. Quand l'utilisateur voit l'écran, il voit une surface que Luna a construite pour lui.

Ce n'est pas une métaphore de marque. C'est une décision d'architecture visuelle.

---

### 5.2 Les 6 principes du Luna Presence Engine

**1. Présence permanente — jamais un écran vide**  
Luna est là même quand elle ne parle pas. Un halo, une respiration, un grain de fond. L'interface ne "tourne pas au ralenti" — elle attend activement.

**2. Respiration — l'interface est vivante à 0% d'interaction**  
Quand l'utilisateur ne fait rien, quelque chose bouge toujours. Lentement. Imperceptiblement. Comme une salle dans laquelle quelqu'un est présent dans l'obscurité.

**3. Matérialisation — ce qui apparaît a été construit**  
Aucun élément ne s'affiche instantanément. Chaque contenu est "posé" devant l'utilisateur par Iris. Le mouvement est le signe que l'IA travaille. Un tableau qui pop n'est pas aussi puissant qu'un tableau qui se construit colonne par colonne.

**4. Profondeur — l'écran n'est pas plat**  
Grille perspective subtile. Halos radiaux qui se superposent. Photos de Luna et Aby visibles derrière le contenu. L'écran a plusieurs couches — comme une scène de cinéma.

**5. Émotion — chaque moment clé a un signal**  
L'écoute est verte. La réflexion est blanche et lente. La décision est or. L'export est émeraude. Ces couleurs ne sont pas décoratives — elles racontent ce qui se passe dans le système.

**6. Univers — Luna Doll est présente**  
Luna Doll — petite poupée brune, robe violette (#7B4FA6), artisanale, jamais robotique — doit apparaître quelque part dans l'interface. En filigrane dans le fond d'un écran clé. En micro-icône dans un footer. En illustration minimaliste dans un onboarding. Elle est le symbole émotionnel de l'univers. Son absence dans l'application est un oubli narratif à corriger.

---

### 5.3 La palette définitive — ancrée dans le lore

| Rôle | Couleur | Source narrative |
|---|---|---|
| Fond de base | `#020810` | Nuit parisienne — appartement de Luna |
| Fond panel | `#0d1117` | Bureaux YAWatch — verre teinté |
| Violet Luna | `#7c3aed` | Présence de Luna dans le système |
| Violet Doll | `#7B4FA6` | Robe velours de Luna Doll |
| Iris (émeraude) | `#10b981` | Couleur d'Iris — protection active |
| Or décision | `#f59e0b` | Moment de décision / validation |
| Blanc présence | `#e5e7eb` | Texte, présence calme |
| Anthracite Luna | `#2C2C2C` | Vêtements de Luna adulte |
| Halo violet | `rgba(124,58,237,0.15)` | Aura de présence IA |
| Halo émeraude | `rgba(16,185,129,0.12)` | Signal d'écoute Iris |

**Règle** : le fond n'est jamais noir pur (`#000000`). Il est toujours bleu nuit profond (`#020810`) avec des halos. Le noir pur est froid et mort. Le bleu nuit avec halos est vivant.

---

### 5.4 Typographie — une signature, pas un choix par défaut

**Titres** : `LUNA` / `IRIS` / `YAWATCH` — toujours en majuscules, letterspacing 0.12–0.18em, poids 700–800. Ces mots sont des noms propres dans un univers. Ils méritent une présence typographique.

**Corps** : système actuel conservé. Lisible, sobre, bien espacé.

**Données** (Workspace) : police monospace pour les chiffres et données structurées — évoque le terminal YAWatch sans faire HUD militaire.

**Interdiction** : police cursive, police décorative, emoji dans les titres de pages.

---

### 5.5 L'animation comme narration — 4 règles

**Règle 1 — La durée raconte l'importance**  
Un élément qui prend 800ms à apparaître est plus important qu'un élément qui prend 200ms. Les décisions prennent du temps. Les messages rapides sont légers. La durée est sémantique.

**Règle 2 — Jamais de spin**  
Aucun loader circulaire. Jamais. Les loaders de Luna sont des lignes qui se tracent, des points qui pulsent, des halos qui respirent. Le spin est universel et sans identité.

**Règle 3 — L'animation se lit de gauche à droite, du haut vers le bas**  
Les éléments d'une liste se matérialisent dans l'ordre. Le dernier item arrive en dernier. C'est la direction de la pensée — de l'intention vers la conclusion.

**Règle 4 — Tout mouvement a une inertie**  
Ease-out pour les entrées (vif au début, doux à l'arrivée). Ease-in pour les sorties (doux au départ, vif à la disparition). Jamais de mouvement linéaire — il est mécanique et mort.

---

### 5.6 Les 3 espaces de l'application — 3 atmosphères distinctes

**Espace Compagnon** (Chat, Voix)  
Atmosphère : intime, nocturne, doux.  
Couleur dominante : violet profond + halo émeraude en présence.  
Mouvement : lent, respiratoire.  
Luna y est une présence humaine qui écoute.

**Espace Décision** (Iris Workspace)  
Atmosphère : focalisée, professionnelle, vivante.  
Couleur dominante : dark panel + halos latéraux + grille perspective.  
Mouvement : matérialisation staggerée, construction visible.  
Iris y est un système de pensée qui projette.

**Espace Contrôle** (Admin, Fondateur)  
Atmosphère : sobre, sérieuse, institutionnelle.  
Couleur dominante : dark + halo émeraude discret + border institutionnel.  
Mouvement : minimal, fonctionnel.  
YAWatch Industries y est une infrastructure visible.

---

### 5.7 Ce que Luna 2026 doit faire ressentir — en une phrase par page

| Page | Phrase-cible |
|---|---|
| Login | "Elle savait que tu allais arriver." |
| Chat | "Elle t'écoute vraiment." |
| Iris Visio | "Tu t'apprêtes à la voir." |
| Iris Workspace | "Tu penses avec elle, pas devant elle." |
| Admin | "Tu es dans les coulisses de quelque chose de sérieux." |
| Activités | "Elle se souvient de tout ce que vous avez construit ensemble." |

---

### 5.8 Ce que Luna 2026 ne sera JAMAIS

- Un tableau de bord SaaS avec des tuiles colorées
- Une interface hacker avec des terminaux verts sur fond noir
- Une app qui spinne et charge pendant 3 secondes sans donner de signe de vie
- Un clone de ChatGPT avec un logo Luna
- Un écran vide qui attend qu'on lui parle
- Une interface dont on oublie le nom 5 minutes après l'avoir fermée

---

## PARTIE 6 — CONTINUITÉ SÉRIE ↔ APPLICATION

### Règle absolue

Des millions de personnes peuvent découvrir Luna via YouTube avant de toucher l'application. Le chemin le plus probable n'est pas : app → série. C'est : série → app.

**Un utilisateur qui vient de voir un épisode doit reconnaître l'application instantanément.**

Pas "oh c'est joli". Pas "ah c'est une app IA". Mais : "c'est le monde de Luna."

---

### Les éléments de la série qui doivent vivre dans l'application

| Élément de la série | Présence dans l'application |
|---|---|
| **Luna Doll** (poupée brune, robe violette #7B4FA6) | En filigrane sur un écran clé. Micro-icône en footer. Illustration onboarding. |
| **Palette Luna** (violet profond, noir nuit, émeraude Iris) | Couleurs token du design system — jamais déviées |
| **Lumières nocturnes** (appartements Paris, La Défense la nuit) | Fonds et halos — bleu nuit profond, jamais noir pur |
| **Atmosphère protectrice** (Luna protège, Iris veille) | Tonus de l'interface : chaleureux dans le compagnon, vigilant dans le workspace |
| **La comptine brisée** (2 notes piano, voix enfant très légère) | Son au chargement de Iris Visio et Workspace — optionnel, jamais intrusif |
| **YAWatch Industries** (La Défense, verre, hauteur, lumière parisienne) | Interface Admin et Workspace : lignes épurées, grille perspective, sérieux corporate premium |
| **Bureau de Luna** (écrans multiples, poupée sur le bureau) | Inspiré l'Iris Workspace : surface de travail multi-couches, présence d'Iris visible |
| **Iris** (système émotionnel né du trauma) | Voix, halo, états visibles (écoute / réflexion / réponse) — jamais un simple bot |
| **Symboles récurrents** (jeton noir d'Aby, porte entrouverte, photo floue, archive modifiée) | Réservés à des moments de transition ou d'état exceptionnel — pas dans le flux principal |

---

### Question obligatoire avant chaque modification graphique

> **"Est-ce que quelqu'un qui vient de voir un épisode de YAWatch-LUNA reconnaîtrait instantanément cet écran ?"**

Si la réponse est non, le travail n'est pas terminé.

---

### Ce que cela interdit concrètement

- Changer la palette sans vérifier qu'elle reste cohérente avec la série
- Introduire un élément visuel (icône, illustration, fond) qui n'existe pas dans l'univers YAWatch-LUNA
- Utiliser des images génériques IA (personnes, lieux, objets) qui ne correspondent pas aux personnages canoniques
- Laisser Luna Doll absente de l'interface alors qu'elle est le symbole émotionnel central de toute la série

---

## PARTIE 7 — LES 10 MOMENTS WOW DE LUNA

### Principe

La respiration constante de l'interface est nécessaire. Mais elle n'est pas suffisante. Il faut aussi des moments qui font dire **"Wouah."**

Ces moments doivent être traités comme des scènes de cinéma. Ils ont un début, un climax et une résolution. L'utilisateur ne peut pas les rater. Et quand ils arrivent, ils marquent la mémoire.

---

### Les 10 Moments Wow

**WOW-1 — Premier lancement**  
*"Bienvenue dans un univers."*  
L'écran de login ne s'affiche pas instantanément. Il se matérialise depuis le noir — fond qui s'éclaire progressivement (fade-in 1.2s), halos violets qui apparaissent l'un après l'autre (stagger 300ms), le logo YAWatch qui se révèle en dernier. Premier contact : déjà une scène.

**WOW-2 — Première connexion**  
*"Elle t'attendait."*  
Après le premier login réussi, avant d'arriver sur le chat : une transition de 800ms pendant laquelle l'écran respire une fois (scale subtil + halo qui pulse) comme si Luna prenait conscience de ta présence. Puis le chat s'ouvre avec un premier message de Luna déjà écrit — pas un onboarding générique, une phrase de présence.

**WOW-3 — Premier message de Luna**  
*"Une vraie réponse, pas un traitement."*  
La bulle de réponse de Luna ne pop pas. Elle se trace de gauche à droite, lettre par lettre — mais pas comme un terminal. Comme si quelqu'un écrivait pour toi en temps réel. Pendant l'écriture : halo émeraude pulsant sur l'avatar.

**WOW-4 — Premier appel Iris (Iris Visio)**  
*"Elle répond."*  
Quand l'utilisateur appuie sur "Démarrer" sur la page Iris Visio : le fond SVG nocturne se met en mouvement (Ken Burns accéléré), la sonnerie monte, le téléphone vibre visuellement — et Luna apparaît. Ce n'est pas un chargement. C'est un appel qui aboutit.

**WOW-5 — Premier message vocal traité**  
*"Elle a compris."*  
Après que l'utilisateur a parlé et qu'Iris a répondu à l'oral : l'Iris Command Screen se construit visuellement devant lui en 800ms — colonnes qui apparaissent, données qui s'ancrent. Le visuel dit : "j'ai compris et voilà comment j'ai organisé ta pensée."

**WOW-6 — Première entrée dans Iris Workspace**  
*"La salle t'attend."*  
Le canvas Workspace ne s'affiche pas vide. Il s'allume — comme une pièce dans laquelle on entre. Le trait de surface se trace lentement. Les photos de Luna et Aby sont visibles en arrière-plan, témoin silencieux. La question de brief s'affiche progressivement : "Quelle est votre question stratégique ?"

**WOW-7 — Première proposition ajoutée**  
*"L'idée existe maintenant."*  
Quand l'utilisateur soumet une première proposition dans le Workspace : la carte n'apparaît pas brutalement. Elle se matérialise — fade + scale 0.93→1.0 en 250ms + border émeraude qui flash une fois. L'idée a été déposée. Elle est réelle.

**WOW-8 — Première décision posée**  
*"Le choix est scellé."*  
Quand une décision est validée dans le Workspace : animation spécifique — icône cadenas qui apparaît, pulse radial or qui s'étend depuis le centre de la carte, titre de la décision qui passe en couleur or (`#f59e0b`). Ce moment dure 600ms. Il ne passe pas inaperçu.

**WOW-9 — Premier dossier final compilé**  
*"Le travail est terminé."*  
À l'étape 12 du Workspace (export) : les cartes de toutes les étapes se compactent progressivement de haut en bas (stagger 80ms chacune) vers une zone centrale — comme si tout se regroupait en un seul document. Une icône de dossier se referme. Un timestamp apparaît. Le dossier final est prêt.

**WOW-10 — Premier souvenir sauvegardé**  
*"Elle s'en souviendra."*  
Quand l'utilisateur sauvegarde une note ou une mémoire dans Luna : une confirmation qui dure 1.5s — un fragment de texte qui part lentement vers le haut de l'écran et disparaît dans le halo violet, comme si Luna absorbait l'information. Puis : "Je m'en souviendrai." Une phrase. Une seule.

---

### Règles des Moments Wow

1. Chaque Moment Wow se produit **une seule fois** dans le parcours utilisateur (ou lors de milestones précis — pas à chaque utilisation).
2. Chaque Moment Wow est **silencieux ou quasi-silencieux** — pas de sons agressifs, pas de fanfare.
3. Chaque Moment Wow **raconte quelque chose** de l'univers — pas juste une animation jolie.
4. Après chaque Moment Wow, l'interface **redevient calme**. Le wow dure. Il ne se répète pas. Il n'est pas dilué.

---

## PARTIE 8 — ANTI-CHATGPT

### Ce que Luna ne doit jamais devenir

C'est le chapitre le plus important du document. Parce que c'est le piège dans lequel 95% des projets IA tombent — souvent sans s'en rendre compte, progressivement, fonctionnalité par fonctionnalité.

---

### Les 8 dérives à surveiller

**Dérive 1 — Le clone de ChatGPT**  
Symptôme : boîte de chat centrée, fond blanc ou sombre, bulles gauche/droite, barre de saisie en bas.  
Diagnostic : ChatGPT a normalisé ce pattern. Luna le partage partiellement. Mais ChatGPT est un outil. Luna est un personnage.  
Antidote : la zone de chat de Luna doit avoir une présence que ChatGPT n'a pas — respiration, halo, avatar vivant, fond texturé. Si on cache le logo, on doit encore reconnaître que c'est Luna.

**Dérive 2 — Le dashboard SaaS**  
Symptôme : grille de cartes, KPIs en gros chiffres, graphiques partout, onglets fonctionnels.  
Diagnostic : les dashboards SaaS sont optimisés pour l'information, pas l'émotion. Luna n'est pas un outil de pilotage.  
Antidote : quand des données apparaissent dans Luna (quotas, budget, activités), elles doivent être présentées avec le ton de Luna — "Voici ce que j'ai utilisé pour toi", pas "Taux de consommation : 34%".

**Dérive 3 — La grille de widgets**  
Symptôme : page d'accueil avec tuiles colorées, chaque fonctionnalité dans sa case.  
Diagnostic : un widget est un objet isolé. Luna n'est pas une collection d'objets — elle est une présence continue.  
Antidote : la navigation dans Luna doit rester narrative. On n'ouvre pas des modules. On entre dans des espaces.

**Dérive 4 — La succession de formulaires**  
Symptôme : chaque action passe par un formulaire, des champs, des boutons "Valider".  
Diagnostic : les formulaires sont le language des administrations et des outils. Luna parle.  
Antidote : les formulaires de Luna doivent ressembler à des conversations. Champ unique à la fois. Ton humain. Jamais de label technique visible.

**Dérive 5 — L'IA qui attend passivement**  
Symptôme : un écran vide avec une barre de saisie qui clignote.  
Diagnostic : attendre passivement, c'est dire à l'utilisateur "ton tour". Luna n'attend pas. Elle est là.  
Antidote : le Presence Halo, l'avatar respirant, la suggestion contextuelle douce. Luna est présente même quand elle ne parle pas.

**Dérive 6 — Le feedback purement fonctionnel**  
Symptôme : "Enregistré ✓", "Erreur 404", "Chargement...", "Traitement en cours".  
Diagnostic : ce sont des messages de système, pas de personnage.  
Antidote : Luna parle en première personne. "Je m'en souviendrai." "Je reviens dans un instant." "Ce n'est pas de ton côté." Jamais de jargon technique visible à l'utilisateur final.

**Dérive 7 — La cohérence sacrifiée pour la fonctionnalité**  
Symptôme : chaque nouvelle feature arrive avec son propre design, sa propre logique, ses propres couleurs.  
Diagnostic : c'est la croissance non gouvernée — chaque sprint ajoute quelque chose sans vérifier l'ensemble.  
Antidote : le design system (tokens CSS) + la question obligatoire de la série avant chaque merge.

**Dérive 8 — L'interface qui "fait IA"**  
Symptôme : animations de scan, halos agressifs, texte qui défile façon Matrix, effets hologramme ostentatoires.  
Diagnostic : vouloir montrer que c'est de l'IA, c'est ne pas faire confiance à l'IA elle-même.  
Antidote : Luna est de l'IA. Elle n'a pas à le prouver. Les effets visuels doivent servir l'émotion, pas la démonstration technologique. Sobriété. Profondeur. Pas de spectacle.

---

### La règle Anti-ChatGPT en une phrase

> Si on peut remplacer "Luna" par "Assistant IA" dans un écran sans que ça change quoi que ce soit — cet écran n'est pas terminé.

---

## CONCLUSION — Avant de coder

Ce document est la carte avant le territoire.

Avant d'écrire une seule ligne de CSS ou de JavaScript, relire :

1. La phrase-cible de la page sur laquelle on travaille
2. La règle de couleur correspondante à l'espace (Compagnon / Décision / Contrôle)
3. La règle d'animation applicable
4. La question série : "Est-ce que quelqu'un qui vient de voir un épisode reconnaîtrait cet écran ?"
5. La question Anti-ChatGPT : "Si on remplace 'Luna' par 'Assistant IA', est-ce que ça change quelque chose ?"
6. La question Presence : "Est-ce que Luna habite cet écran ?"

Si la réponse à l'une de ces 3 questions est non — le travail n'est pas terminé.

---

**La phrase fondatrice de ce document :**

> *Luna n'est pas une fonctionnalité de l'application. Luna est l'application.*

---

*Ce document ne contient aucune modification fonctionnelle.*  
*Il ne modifie aucun fichier existant.*  
*Il est la référence officielle de direction artistique avant toute implémentation graphique.*  
*Ne pas merger sur `main` sans validation du fondateur.*
