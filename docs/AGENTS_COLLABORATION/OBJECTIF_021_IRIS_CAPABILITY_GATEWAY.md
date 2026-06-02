# Objectif 021 — Iris Capability Gateway

Date : 2026-06-02  
Lead coordination : Codex  
Statut : cadrage actif — avant nouveau code visible

---

## 1. Decision produit

Iris ne doit pas etre un chatbot qui dit "je ne peux pas acceder".

Iris doit etre une operatrice de travail : elle comprend la demande, choisit l'outil, affiche ce qu'elle fait dans son ecran de commande, puis demande validation avant toute action sensible.

L'objectif n'est pas seulement d'afficher un joli tableau. L'objectif est de creer un canal fiable entre :

1. les donnees externes ;
2. les donnees internes Luna ;
3. les outils d'action ;
4. l'ecran visuel Iris ;
5. les garde-fous RGPD, cout et validation.

---

## 2. Couches obligatoires

### Couche A — Recherche externe

Iris doit pouvoir chercher dehors quand la demande le justifie :

- recherche web ;
- actualites ;
- meteo ;
- lieux/adresses/services ;
- pages web a lire ;
- donnees cartographiques ou itineraires.

Resultat attendu : Iris affiche les sources et une synthese exploitable dans un `research_board`, `map_board`, `data_board` ou `decision_board`.

Interdit : repondre "je n'ai pas acces" si un outil existe. Si l'outil echoue, Iris affiche la cause dans un `status_rail` ou `missing_info`.

### Couche B — Documents internes

Iris doit pouvoir travailler avec le porte-documents :

- upload document ;
- liste des documents ;
- recherche document ;
- resume ;
- comparaison de documents ;
- extraction d'echeances, montants, obligations ;
- classement scanne/genere ;
- preparation d'un document a sauvegarder.

Resultat attendu : `document_insight`, `document_draft`, `data_board`, `timeline`, `decision_board`.

Garde-fou : consentement, JWT, droit a l'oubli, aucune fuite de document vers un invite non autorise.

### Couche C — Actions externes

Iris doit pouvoir preparer puis executer apres validation :

- appel Twilio ;
- SMS ;
- email ;
- invitation session Iris ;
- relance contact ;
- reservation ou paiement uniquement en mode preparation, jamais auto.

Resultat attendu : `action_board` avec recapitulatif clair, cout/risque, destinataire, bouton confirmer/refuser.

Interdit : action reelle sans validation owner. Interdit d'appeler 15/17/18/112/3114/3977. Interdit d'appeler entre 22h et 7h sans regle speciale validee. Interdit de consommer Twilio en boucle.

### Couche D — Monde / Map / 3D

Iris doit pouvoir utiliser les donnees de carte quand c'est utile :

- position approximative si consentie ;
- lieux ;
- itineraire ;
- contexte geographique ;
- carte monde/sociale Luna ;
- affichage visuel dans `map_board`.

Garde-fou : pas de position precise ni exposition publique sans consentement explicite.

### Couche E — Collaboration Teams interne

Iris doit pouvoir gerer une session collaborative interne :

- inviter un participant ;
- afficher les participants ;
- roles : owner / trusted / guest ;
- mute / kick / statut parole ;
- actions sensibles demandees par invite = validation owner.

Resultat attendu : overlay participants style Teams/Zoom + pending action board.

---

## 3. Contrat de livraison

Une capacite Iris est livree seulement si les 5 cases sont vraies :

1. l'outil existe cote backend ou l'absence est documentee ;
2. Iris sait appeler l'outil ;
3. le resultat revient avec un statut verifiable ;
4. l'ecran Iris affiche le resultat dans le bon `render_type` ;
5. les garde-fous sont appliques avant toute action sensible.

Si une seule case manque, l'equipe ne dit pas "c'est bon".

---

## 4. Tests fondateurs obligatoires

### Test 1 — Recherche externe

Phrase : "Iris, cherche sur le web Base Legacy et fais-moi une synthese exploitable."

Validation :

- Iris ne dit pas "je n'ai pas acces" ;
- elle appelle un outil recherche ou affiche la cause exacte si l'outil est indisponible ;
- elle affiche les sources ;
- elle produit un `research_board` ou `data_board`.

### Test 2 — Documents

Phrase : "Iris, retrouve mes documents sur ce sujet et compare-les."

Validation :

- Iris interroge le porte-documents ;
- si aucun document, elle affiche `missing_info` ;
- si documents presents, elle affiche `document_insight` ou `decision_board`.

### Test 3 — Appel externe

Phrase : "Iris, prepare un appel a ce contact."

Validation :

- aucun appel ne part ;
- `action_board` montre destinataire, but, cout/risque, validation ;
- confirmation owner obligatoire avant Twilio.

### Test 4 — Carte

Phrase : "Iris, montre-moi ou se situe ce lieu et comment y aller."

Validation :

- Iris affiche `map_board` ou cause exacte d'indisponibilite ;
- aucune position precise partagee sans consentement.

### Test 5 — Session equipe

Phrase : "Iris, invite Marie dans cette session et donne-lui acces au projet BESS uniquement."

Validation :

- lien invite prepare ;
- role et scope visibles ;
- owner peut mute/kick ;
- invite ne peut pas declencher d'action sensible sans validation owner.

---

## 5. Missions agents

### Codex

Role : coordination, scope, garde-fous, verification GitHub.

Livrables :

- cette specification ;
- audit des outils reels disponibles ;
- consigne finale Claude apres avis Kimi + DeepSeek ;
- tests terrain et refus de validation partielle.

### Kimi

Role : vision UX premium.

Mission :

- definir l'interface Capability Gateway : panneau outils, mode clair/sombre, overlay Teams, ecran de recherche, carte, documents, validation action ;
- verifier que le rendu donne une impression de "centre de commande", pas un chat ;
- signaler toute regression visuelle.

Livrable attendu : `docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_CAPABILITY_GATEWAY_021.md`.

### DeepSeek

Role : audit technique et risques.

Mission :

- cartographier tous les outils existants : recherche, documents, map, Twilio, contacts, Teams ;
- verifier quels outils sont exposes a `/ws/iris-voice` et `VOICE_TOOLS` ;
- lister les gaps backend/frontend ;
- proposer un contrat `intent -> tool -> render_type -> garde-fou`.

Livrable attendu : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_IRIS_CAPABILITY_GATEWAY_021.md`.

### Claude

Role : integration finale, apres scope Codex.

Mission avant feu vert :

- lire cette specification ;
- ne pas coder de nouvelle action reelle ;
- attendre l'audit DeepSeek + UX Kimi + consigne Codex ;
- preparer un plan d'implementation V1.

Mission apres feu vert Codex/Ludovic :

- brancher les outils lecture/recherche deja existants sur Iris ;
- afficher les resultats dans Command Screen ;
- ajouter `action_board` de validation pour Twilio/SMS/email/invitation ;
- ne deployer qu'apres validation Ludovic.

---

## 6. Priorite V1

V1 doit livrer, dans cet ordre :

1. recherche externe visible ;
2. documents/vault visible ;
3. `action_board` actions sensibles ;
4. map board ;
5. Teams overlay owner/guest ;
6. mode clair/sombre.

La priorite n'est pas d'ajouter 100 outils. La priorite est qu'Iris arrete de parler dans le vide et montre qu'elle travaille.

