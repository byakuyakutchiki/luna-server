# KIMI — Audit UX Render Final Iris — Objectif 022

> Agent : Kimi  
> Objectif : 022  
> Niveau : 0  
> Date : 2026-06-03  
> Statut : audit termine — corrections UX proposees, bug technique NON masque

---

## 1. Methode d'audit

Audit code-readonly de static/simli.html lignes 3708-3757 (work/timeout), 620-677 (panel CSS), 1485-1507 (panel HTML), 820-826 (mobile CSS). Aucun test terrain (VM sans micro). Verdicts bases sur le code reel + retour Ludovic "panneau ouvert mais rien dedans".

---

## 2. Constat terrain (transcrit depuis retour Ludovic)

| Symptome | Localisation code | Verdict UX |
|---|---|---|
| Panneau s'ouvre mais vide | _icsShowWorking() l.3708 | Panneau ouvre trop tot (immediat) |
| "Preparation trop longue" apparait | _icsShowWorkTimeout() l.3736 | Message anxiogene, passif, sans action |
| "Elle affiche le panneau mais ne fait pas ce qu'elle dit" | Chaine render | Rupture pipeline confirme par Codex |

---

## 3. Audit UX point par point

### 3.1 Panneau s'ouvre trop tot — FLASH INUTILE

Code : _icsShowWorking() ouvre le panneau IMMEDIATEMENT (panel.className = 'ics-panel open st-analyse').

Probleme : Si le rendu arrive en < 500ms, l'utilisateur voit un flash d'ouverture/fermeture inutile.

Proposition : Delay d'ouverture de 400ms. Si le rendu arrive avant 400ms, afficher directement sans animation ics-boot.

Risque technique : Aucun — purement UX, ne masque pas le bug.

---

### 3.2 "Preparation trop longue" — ANXIOGENE ET PASSIF

Code : _icsShowWorkTimeout() affiche un titre negatif "Preparation trop longue", un sous-titre verbeux, 3 etapes passives, zero bouton d'action.

Problemes :
1. Titre negatif : "trop longue" culpabilise
2. Sous-titre verbeux : 2 phrases pour dire "ca marche pas"
3. 3 etapes passives : 2 constats + 1 suggestion vague
4. Zero bouton d'action : l'utilisateur doit taper un nouveau message
5. Pas de diagnostic : l'utilisateur ne sait pas si c'est sa faute, un bug, ou un manque de donnees
6. Pas de fallback intelligent : "reformuler ou simplifier" est la seule option

Proposition — ecran Diagnostic :
- Titre neutre : "Diagnostic en cours"
- Sous-titre factuel : "Le rendu n'a pas ete recu dans le delai attendu."
- 3 boutons d'action : [Relancer la demande] [Simplifier] [Donnees manquantes ?]
- Lien discret : "Voir le diagnostic technique" (logs pour support)
- Garder le statut "warning" (amber) — ne pas masquer la rupture
- Proposer des actions concretes, pas juste du texte
- Le lien technique est discret (font-size: 10px, monospace) pour le support
- Si le bug est corrige, cet ecran disparaitra naturellement

---

### 3.3 Boutons dominant l'ecran mobile

Code mobile : max-height: 42vh, 4 boutons toujours visibles (Modifier, Copier, Telecharger, Fermer).

Probleme : 4 boutons x ~36px hauteur + padding = ~160px de boutons. Dans 42vh (~300px sur mobile), les boutons prennent plus de 50% de la hauteur. Le contenu utile est ecrase. "Modifier" et "Telecharger" sont inutiles si le panneau est vide.

Proposition :
- Desktop : garder les 4 boutons en ligne
- Mobile : 2 boutons visibles max (Copier + Fermer) + menu trois-points pour Modifier/Telecharger
- Cacher Modifier/Telecharger si le contenu est vide ou si rType === 'missing_info'
- Reduire max-height mobile a 38vh (deja propose dans KIMI_AUDIT_UX_IRIS_WORKBENCH_V1_019.md)

---

### 3.4 Mode clair — CONTRASTE FAIBLE

Code : [data-theme="light"] .ics-panel { background: rgba(255,255,255,0.96); } Grille holographique a 0.028 d'opacite.

Probleme : 0.96 d'opacite sur blanc = presque opaque, mais la grille holographique a 0.028 est invisible. Le rendu est un rectangle blanc plat. --ics-text2 sur blanc = faible lisibilite.

Proposition :
- Mode clair : background: rgba(250,250,252,0.92) (legerement bleute, moins plat)
- Grille holographique en clair : rgba(0,210,255,0.06) au lieu de 0.028
- --ics-text2 en mode clair : #4B5563 au lieu de gris clair
- Garder les coins HUD cyan visibles

---

### 3.5 Pas de progression visible pendant la preparation

Code actuel : 3 etapes textuelles statiques, aucune animation de progression.

Probleme : L'utilisateur ne sait pas si Iris est bloquee ou en train de travailler.

Proposition :
- Ajouter une barre de progression fine en haut du panneau (2px, couleur amber, animation width 0 a 100% sur 8s)
- Les 3 etapes deviennent visuellement actives : etape courante = highlight + icone animee, etapes futures = grisees
- Compteur de temps ecoule discret (monospace, 10px, coin bas-droite)
- Si le render arrive, la barre disparait instantanement

---

### 3.6 Timeout fixe a 10s — PAS ADAPTATIF

Code : _icsWorkTimer = setTimeout(function() { ... }, 10000);

Probleme : 10s est arbitraire. Une recherche web peut prendre 15s. Une generation de document peut prendre 20s. Le timeout declenche une fausse alerte pour des operations legitimes.

Proposition : Timeout adaptatif selon le render_type :
- chart, kpi_cards : 8s
- data_board, action_board : 10s
- research_board, document_draft : 15s
- search_web, get_page_info : 12s
- Le timeout peut etre etendu si Iris envoie un message intermediaire (ex: "Je recherche...")

---

### 3.7 Le footer contexte/missing s'affiche meme quand vide

Code : if (footer) footer.style.display=hasFooter?'':'none';

Probleme : Le footer prend de la place meme quand il n'y a rien dedans. Sur mobile, chaque pixel compte.

Proposition : Verifier hasFooter AVANT d'ouvrir le panneau sur mobile. Si le contenu est vide + pas de footer, ne pas ouvrir du tout — ou afficher un message compact.

---

## 4. Tableau de synthese

| # | Probleme | Gravite | Fichier/Ligne | Correction proposee | Masque le bug ? |
|---|---|---|---|---|---|
| 1 | Panneau ouvre trop tot (flash) | Moyen | simli.html:3727 | Delay 400ms avant ouverture | Non |
| 2 | "Preparation trop longue" anxiogene | Eleve | simli.html:3743 | Ecran Diagnostic avec 3 boutons d'action | Non |
| 3 | Boutons dominant mobile | Eleve | simli.html:1501 + CSS | 2 boutons + menu trois-points sur mobile | Non |
| 4 | Mode clair trop pale | Moyen | simli.html:497 | Grille + fond + texte plus contrastes | Non |
| 5 | Pas de progression visible | Moyen | simli.html:3719 | Barre + etapes actives | Non |
| 6 | Timeout fixe 10s | Moyen | simli.html:3732 | Timeout adaptatif par render_type | Non |
| 7 | Footer vide prend de la place | Faible | simli.html:4606 | Cacher si vide | Non |

---

## 5. Livrable de correction propose

### Phase 1 (niveau 1 — peut deployer sans validation)
- Delay 400ms avant ouverture panneau
- Reduction boutons mobile (2 + menu)
- Timeout adaptatif par render_type
- Footer cache si vide

### Phase 2 (niveau 1 — peut deployer sans validation)
- Refonte "Preparation trop longue" vers "Diagnostic" avec boutons
- Barre de progression + etapes actives
- Mode clair : contraste ameliore

### Phase 3 (niveau 2 — validation Ludovic)
- Animations premium (etapes avec icones animees)
- Suggestions contextuelles au timeout (selon render_type)

---

## 6. Ce qui reste a DeepSeek

Kimi n'a PAS masque le bug technique. Les corrections UX proposees rendent la rupture PLUS VISIBLE et PLUS ACTIONNABLE pour l'utilisateur, pas moins.

DeepSeek doit confirmer :
- Pourquoi renderIrisCommand() ne recoit pas de payload final
- Si le timeout se declenche parce que le backend n'envoie pas de type: "render"
- Si iris_render est bien appele par le LLM
- Si les nouveaux outils start_meeting/organize_kanban retournent bien un payload

---

## 7. Message agent

Agent : Kimi
Objectif : 022
Tache : TASK-022-KIMI-AUDIT-RENDER-FINAL-UX
Type : audit UX termine
Resume : Audit UX render final Iris termine. 7 problemes identifies (flash panneau, message anxiogene, boutons mobile, contraste clair, progression, timeout fixe, footer vide). Aucun bug masque — les corrections proposees rendent la rupture plus visible et actionnable. 3 phases de correction definies. Attend DeepSeek audit technique + Codex arbitrage avant implementation.
Fichier concerne : docs/AGENTS_COLLABORATION/agents/KIMI_AUDIT_RENDER_FINAL_UX_022.md ; static/simli.html
Risque : faible — audit uniquement
Decision Ludovic requise : non pour l'audit ; oui pour Phase 3 animations premium
Action proposee : DeepSeek produit audit technique render final. Codex tranche corrections a implementer.
