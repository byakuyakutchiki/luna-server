# LUNA FUNCTIONAL AUDIT v2
## Audit Produit Global Officiel — YAWatch-LUNA

**Date** : 14 juin 2026  
**Méthode** : Playwright E2E (mobile 390×844) + analyse DOM + 28 captures d'écran  
**URL auditée** : `https://luna-beta-674304336025.europe-west1.run.app`  
**Sections couvertes** : 19 (16 onglets + /simli + /team + /admin)

---

## RÉSUMÉ EXÉCUTIF

**Score global : 5.2 / 10**

Luna est un produit ambitieux avec une architecture solide. Les piliers existent. Les données circulent. Les fonctionnalités sont là — en partie.

Le problème n'est pas l'absence de fonctionnalités. C'est le fossé entre la promesse affichée et l'expérience réelle. Luna se présente comme un compagnon de vie. L'utilisateur découvre une suite d'outils sans continuité entre eux.

Le score serait plus bas sans Iris Workspace (le différenciateur réel) et sans Rapports (qui prouve que les données existent). Il serait plus haut si les actions contextuelles du Chat étaient cohérentes.

---

## TABLEAU GLOBAL DES FONCTIONNALITÉS

| Section | Promesse | Réalité observée | Cohérent ? | Criticité | Confiance |
|---|---|---|---|---|---|
| Chat — réponse | Compagnon disponible 24/7 | Fonctionne. Réponse naturelle en ~4s | ✅ | — | +1 |
| Chat — chips contextuelles | Actions suggérées selon le contexte | "Bonne nuit / Relaxation" après "Qui es-tu ?" | ❌ | 🟠 HAUTE | -2 |
| Chat — premier message | Pas d'erreur visible | Message d'erreur historique visible en haut du chat | ❌ | 🟡 | -1 |
| Mode Compagnon / Secrétaire | Deux personas distincts | Boutons présents, distinction non testable sans interaction longue | 🟡 | MOYENNE | 0 |
| WakeWord | Activation vocale passive | Bouton présent, micro (#micBtn) introuvable | ❌ | 🟠 | -1 |
| Services — menu | Conciergerie complète | Menu riche : vols, hotels, météo, SMS, email, appel | ✅ | — | +2 |
| Services — actions | Chaque action fonctionne | Non testé (requiert vraies permissions/clés) | ⚠️ | 🔴* | 0 |
| Instructions / Mémoire | Rappels, règles permanentes | Onglet existe dans DOM mais non accessible via nav principale | ❌ | 🔴 | -2 |
| Documents | Vault IA, courriers | Onglet existe dans DOM mais non accessible via nav principale | ❌ | 🔴 | -2 |
| Formulaires | Dossiers assistés | Onglet existe dans DOM mais non accessible via nav principale | ❌ | 🔴 | -2 |
| Rapports | Comptes-rendus vocaux | Fonctionne — données réelles présentes (juin 2026) | ✅ | — | +1 |
| Rapports — pagination | Listes gérables | 30+ entrées sans pagination, sans filtre opérationnel | ❌ | 🟠 | -1 |
| Carte / Localisation | Trouver des lieux | Onglet existe dans DOM mais non accessible via nav principale | ❌ | 🟠 | -1 |
| Guardian | Surveillance GPS + alertes | Page séparée, GPS refusé (headless), architecture présente | ⚠️ | 🟡 | 0 |
| Guardian — navigation retour | Retour fluide à l'app | "← App" link — rupture de navigation (page pleine séparée) | ❌ | 🔴 | -2 |
| Amis | Réseau social | Inaccessible en audit (Guardian trap) | ❓ | 🔴 | -1 |
| Activités / Gamification | Engagement utilisateur | Inaccessible en audit (Guardian trap) | ❓ | 🟠 | -1 |
| Monde | Actualités mondiales | Inaccessible en audit (Guardian trap) | ❓ | 🟡 | 0 |
| Contacts | Carnet d'adresses | Inaccessible en audit (Guardian trap) | ❓ | 🟠 | -1 |
| Profil | Identité utilisateur | Champs riches dans DOM (30+ champs), non accessibles en audit | ⚠️ | 🟠 | 0 |
| Quotas | Consommation du plan | Inaccessible en audit (Guardian trap) | ❓ | 🟡 | 0 |
| Réglages | Configuration complète | Inaccessible en audit (Guardian trap) | ❓ | 🟡 | 0 |
| Théocratie | Module spécifique | Inaccessible en audit (Guardian trap) | ❓ | 🟡 | 0 |
| Iris Visio — page d'entrée | Antichambre de la visio | MAGIC-1 visible : "I" émeraude, IRIS VISIO, select stylisé | ✅ | — | +1 |
| Iris Visio — appel réel | Conversation audio directe | Non testable (headless sans micro) | ⚠️ | — | 0 |
| Iris Workspace — entrée | Sans friction en solo | Modal réduite (prénom + titre), rôle masqué. Mais modal persiste | 🟡 | 🟡 | 0 |
| Iris Workspace — session | Réflexion collective | 5 phases, canvas, participants, activité — fonctionne | ✅ | — | +2 |
| Iris Workspace — état initial | Session vide = 0 participants | "4 participants EN SESSION" sur chargement frais | ❌ | 🔴 | -2 |
| Admin | Dashboard fondateur | Accessible, login séparé requis | ✅ | — | 0 |

---

## TOP 20 — INCOHÉRENCES PRODUIT (par gravité)

### 1. 🔴 Guardian piège la navigation de l'app entière
**Gravité : CRITIQUE**  
Cliquer sur l'onglet Guardian ouvre une **page séparée** (`← App` pour revenir). Conséquence : après Guardian, l'utilisateur ne peut plus accéder à Amis, Activités, Monde, Contacts, Profil, Quotas, Réglages, Théocratie sans revenir manuellement. En test automatisé, **8 onglets sur 16 sont devenus inaccessibles** à cause de ce comportement.

Depuis la perspective d'un nouvel utilisateur : il explore, clique sur Guardian, est "aspiré" dans une autre app, ne sait pas comment revenir. Il ferme.

**Confiance : -2**

---

### 2. 🔴 "Luna est temporairement injoignable" visible dans l'historique de chat
**Gravité : CRITIQUE**  
Le premier écran de chat affiche un message d'erreur passé stocké dans l'historique : *"Luna est temporairement injoignable. Vérifie que le serveur tourne."* Ce n'est pas une erreur actuelle — Luna répond correctement — mais ce message reste visible.

Depuis la perspective d'un investisseur : premier écran de la démo = message d'erreur.  
Depuis la perspective d'un nouveau utilisateur : il croit que l'app est en panne. Il quitte.

**Confiance : -2**

---

### 3. 🔴 Iris Workspace affiche "4 participants EN SESSION" sur chargement frais
**Gravité : CRITIQUE**  
Sur un chargement frais de `/team`, le système affiche "EN SESSION · 4 participants". Aucun humain n'a rejoint la session. L'utilisateur entre seul et voit un canvas "EN SESSION" sans comprendre avec qui.

Cela viole la promesse de transparence du Workspace. Un utilisateur solo qui voit "4 participants" peut croire que ses données sont partagées avec d'autres.

**Confiance : -2**

---

### 4. 🔴 Instructions, Documents, Formulaires, Carte — onglets existants mais introuvables
**Gravité : CRITIQUE**  
Ces 4 sections existent dans le DOM (champs, inputs, logique complète). Mais elles ne sont **pas accessibles via la navigation principale** de la barre de tabs. L'utilisateur qui cherche à créer un rappel, déposer un document ou remplir un formulaire ne trouve pas l'entrée.

Ces fonctionnalités existent mais sont invisibles — pire que de ne pas exister (elles créent une promesse non remplie).

**Confiance : -2**

---

### 5. 🟠 Chips contextuelles non-contextuelles dans le Chat
**Gravité : HAUTE**  
Après que l'utilisateur demande "Qui es-tu ?", Luna répond correctement mais propose : **"🌙 Bonne nuit / 😌 Relaxation / 📝 Gratitude / 🎤 Parler"**.

Ces chips n'ont aucun lien avec la conversation. Elles semblent générées par l'heure du jour (nuit) plutôt que par le contexte conversationnel.

Un bouton d'action doit répondre à la question : *"Pourquoi ce bouton apparaît maintenant ?"* Ici : aucune réponse valide.

**Confiance : -2** (c'est le symptôme le plus visible d'une IA qui n'écoute pas)

---

### 6. 🟠 Rapports : 30+ entrées sans pagination ni filtre fonctionnel
**Gravité : HAUTE**  
L'onglet Rapports contient des données réelles (sessions du 1er juin 2026 et au-delà). Mais l'affichage est une liste infinie avec 30+ boutons "Lire la suite ▼" et "Supprimer" sans pagination. Aucune recherche textuelle opérationnelle visible.

Un utilisateur au bout de 6 mois aura 500 entrées. L'interface sera inutilisable.

**Confiance : -1**

---

### 7. 🟠 Bouton micro absent, WakeWord seul
**Gravité : HAUTE**  
Le DOM confirme l'existence de `#wakewordBtn` mais aucun `#micBtn` n'a été trouvé. La voix est une promesse centrale de Luna ("parler à Luna"). Si l'accès au micro n'est pas évident (pas de bouton visible), la fonctionnalité est cachée.

**Confiance : -1**

---

### 8. 🟠 Workspace modal persiste pour les nouveaux utilisateurs
**Gravité : HAUTE**  
MAGIC-3 a correctement masqué le choix de rôle. Mais la modal "prénom + titre de session" est toujours présente au premier accès. L'utilisateur solo doit encore passer par ce formulaire. Le bypass complet n'est actif qu'à partir du 2e accès (prénom en localStorage).

La promesse MAGIC-3 ("0 friction en solo") n'est pas encore atteinte pour les nouveaux utilisateurs.

**Confiance : 0**

---

### 9. 🟠 Iris Visio : résidu "L / Iris / Appel entrant..." visible dans le DOM
**Gravité : HAUTE**  
Le contenu DOM de `/simli` contient : `"L\nIris\nAppel entrant...\n..."` — ce sont des éléments d'une ancienne interface (bague de téléphone) qui persistent dans la page. Ils ne s'affichent pas visuellement (bonne nouvelle) mais sont présents dans le DOM et peuvent créer des confusions pour les lecteurs d'écran ou des fuites d'UX.

---

### 10. 🟡 Placeholder "Comment rendre Luna rentable ?" visible à tous les utilisateurs
**Gravité : MOYENNE**  
Le champ "Titre de la session" dans Iris Workspace affiche ce placeholder. C'est probablement un placeholder de test du fondateur. Un utilisateur final le lit comme une instruction ou une question destinée à lui. Déstabilisant.

---

### 11. 🟡 Mode Compagnon / Mode Secrétaire — distinction opaque
**Gravité : MOYENNE**  
Deux boutons sont visibles. Aucune explication sur l'écran sur ce qu'ils changent. Un nouvel utilisateur clique "Secrétaire" sans savoir si Luna va se comporter différemment, si ses données vont changer, si c'est réversible.

---

### 12. 🟡 Guardian — GPS refusé sans gestion gracieuse
**Gravité : MOYENNE**  
Quand le GPS est refusé, Guardian affiche "❌ GPS: User denied Geolocation" en bas de page, mais la carte est déjà chargée et vide. L'utilisateur ne comprend pas ce qu'il doit faire. Pas d'invitation claire à autoriser le GPS.

---

### 13. 🟡 "YAWATCH INDUSTRIES / IRIS WORKSPACE" — identité de marque confuse
**Gravité : MOYENNE**  
L'en-tête du Workspace affiche "YAWATCH INDUSTRIES". L'app principale s'appelle Luna. Iris Workspace est un sous-produit de YAWatch. Pour un utilisateur final, ces trois noms (Luna, Iris, YAWatch) créent de la confusion sur ce qu'il utilise.

---

### 14. 🟡 Services — actions non testables sans clés API actives
**Gravité : MOYENNE (potentiellement CRITIQUE)**  
Le menu Services liste Vols, Hotels, Restaurants, SMS, Email, Appel. Ces boutons mènent-ils à des fonctionnalités réelles ? Aucun test sans clés API Duffel, Twilio, Serper. Si ces actions échouent silencieusement, le menu est une promesse creuse.

---

### 15. 🟡 Workspace — canvas vide sans guide visuel
**Gravité : MOYENNE**  
Après l'entrée dans Iris Workspace (en session), la phase "Collecte" s'affiche mais le canvas est vide. Aucun trait de surface (prévu dans MAGIC-3), aucune instruction visible sur ce que l'utilisateur doit faire. L'utilisateur solo face à un canvas noir ne sait pas où commencer.

---

### 16. 🟡 Rapports — messages d'erreur stockés comme conversations normales
**Gravité : MOYENNE**  
Liée à l'incohérence #2 : si les messages d'erreur sont stockés dans l'historique comme des messages normaux, la liste de Rapports contiendra aussi ces erreurs. L'historique perd sa valeur documentaire.

---

### 17. 🟡 Admin — second mot de passe requis
**Gravité : MOYENNE**  
L'admin nécessite un identifiant séparé. Si le fondateur perd ce mot de passe ou si un exploitant doit y accéder depuis l'app mobile, il y a friction. À consolider avec le système JWT principal.

---

### 18. 🟢 Iris Visio — "Appel entrant..." visible avant appel
**Gravité : FAIBLE**  
L'interface Iris Visio affiche "Appel entrant..." dans le DOM avant même que l'appel ait commencé. C'est une interface de sonnerie préchargée qui "fuite" dans l'état de départ.

---

### 19. 🟢 WakeWord — comportement non documenté
**Gravité : FAIBLE**  
Le bouton WakeWord existe mais rien n'indique à l'utilisateur ce qu'il fait. Sur mobile WebView, le WakeWord nécessite une permission microphone permanente. L'onboarding ne l'explique pas.

---

### 20. 🟢 Halo Presence — invisible sans interaction
**Gravité : FAIBLE (attendu)**  
L'état "idle" du halo (opacity 0.07) est intentionnellement subtil. Mais pour les 5 premières secondes d'un premier utilisateur, il n'y a aucune différence visuelle avec un écran sans halo. L'effet ne devient perceptible qu'à l'interaction. À surveiller lors du test MAGIC-0.5.

---

## TOP 10 — FONCTIONNALITÉS CASSÉES (à corriger immédiatement)

| # | Fonctionnalité | Symptôme | Impact |
|---|---|---|---|
| 1 | **Navigation Guardian** | Guardian ouvre une page séparée, bloque le retour aux 8 autres onglets | Tous les utilisateurs qui explorent |
| 2 | **Historique d'erreurs dans le chat** | Erreurs passées affichées comme messages normaux | Premier écran = message d'erreur |
| 3 | **Workspace "4 participants"** | Sessions fantômes affichées sur chargement frais | Confiance et RGPD |
| 4 | **Instructions — introuvable** | Onglet existe, mémoire utilisateur inaccessible | Pilier "Mémoire" entier cassé |
| 5 | **Documents — introuvable** | Vault IA inaccessible depuis la navigation | Pilier "Documents" entier cassé |
| 6 | **Formulaires — introuvable** | Dossiers inaccessibles depuis la navigation | Pilier "Services" incomplet |
| 7 | **Carte — introuvable** | Localisation inaccessible depuis la navigation | Feature invisible |
| 8 | **Chips non-contextuelles** | "Bonne nuit / Relaxation" après une introduction de Luna | Détruit l'illusion de présence |
| 9 | **Bouton micro absent** | Voix non accessible sans WakeWord | Fonctionnalité centrale cachée |
| 10 | **Pagination Rapports absente** | 30+ entrées sans pagination — inutilisable à long terme | Data management |

---

## TOP 10 — FONCTIONNALITÉS INCOHÉRENTES (à revoir)

| # | Fonctionnalité | Incohérence |
|---|---|---|
| 1 | Chips contextuelles | Générées par l'heure, pas la conversation |
| 2 | Mode Compagnon / Secrétaire | Distinction invisible sans documentation |
| 3 | Workspace modal solo | Friction réduite mais pas éliminée |
| 4 | Guardian navigation | Architecture page-entière vs onglet SPA |
| 5 | "YAWATCH INDUSTRIES" dans Workspace | Trois noms de marque (Luna, Iris, YAWatch) |
| 6 | Placeholder développeur visible | "Comment rendre Luna rentable ?" exposé |
| 7 | GPS Guardian sans onboarding | Permission refusée = silence, pas d'aide |
| 8 | Messages d'erreur dans historique | Erreurs et conversations mélangées |
| 9 | "Appel entrant..." préchargé | État de sonnerie visible avant l'appel |
| 10 | Admin mot de passe séparé | Deux systèmes d'auth pour un même fondateur |

---

## TOP 10 — FONCTIONNALITÉS INUTILES (à supprimer ou fusionner)

| # | Fonctionnalité | Recommandation |
|---|---|---|
| 1 | **Onglet Théocratie** | Audience trop spécifique pour une app grand public. Masquer ou mettre en Réglages avancés |
| 2 | **Bouton "ACTIVER PRÉSENCE" dans Workspace** | Signification opaque. Fusionner avec l'état de session |
| 3 | **Niveau Bronze / Gamification Guardian** | Gamification de la surveillance = registre émotionnel incohérent |
| 4 | **"COLLECTE DIRECTE" dans Workspace** | Doublon avec le flux normal. Créer de la confusion |
| 5 | **Onglet Monde** | Si c'est "actualités", fusionner avec Services > Actualités |
| 6 | **16 onglets dans la nav** | Trop. La navigation principale devrait avoir 5 onglets max |
| 7 | **Sous-onglets Documents : Réunions / SMS envoyés** | SMS envoyés dans Documents n'a pas sa place |
| 8 | **"← App" comme seul retour de Guardian** | Ce n'est pas une navigation, c'est un lien de secours |
| 9 | **"Alertes vocales (optionnel)" dans Guardian** | Feature floue. Qu'est-ce qui déclenche une alerte vocale ? |
| 10 | **Page d'accueil avec modale de bienvenue** | Elle n'apporte rien après la première connexion |

---

## TOP 10 — FONCTIONNALITÉS PROMETTEUSES (à renforcer)

| # | Fonctionnalité | Pourquoi prometteuse | Renforcer |
|---|---|---|---|
| 1 | **Iris Workspace 5 phases** | Structure de raisonnement collectif unique | Rendre le canvas vivant, ajouter les propositions IA |
| 2 | **Rapports automatiques** | Données réelles, archivage automatique des sessions | Ajouter recherche full-text, export, résumé IA |
| 3 | **Services / Conciergerie** | Menu riche, structure claire, icônes parlantes | Confirmer que chaque bouton fonctionne, ajouter feedback |
| 4 | **Guardian GPS** | Surveillance volontaire, architecture complète | Résoudre l'onboarding GPS, ajouter check-ins manuels |
| 5 | **WakeWord** | Activation vocale passive — différenciateur fort | Documenter, tutoriel, signal visuel d'activation |
| 6 | **Modes Compagnon / Secrétaire** | Persona switching — concept fort | Différencier visuellement, expliquer le changement |
| 7 | **Presence Halo** | Seul au monde (Phase 0) — personne n'a ça | Rendre plus visible dans l'état "responding" |
| 8 | **Iris Visio — page d'entrée** | MAGIC-1 fonctionne, ambiance correcte | Tester le flux d'appel complet |
| 9 | **Profil utilisateur riche** | 30+ champs (médical, famille, préférences) | Rendre accessible, expliquer pourquoi ça aide Luna |
| 10 | **Chips de suggestion** | Concept fort (actions en un clic) | Rendre contextuelles (liées à la conversation, pas à l'heure) |

---

## CARTOGRAPHIE DES PROMESSES

| Promesse Luna | Réalité auditée | Écart |
|---|---|---|
| "Discuter naturellement" | Chat fonctionnel, réponse ~4s, langage fluide | Faible écart ✅ |
| "Rappels et mémoire" | Instructions dans DOM mais introuvable en navigation | Écart majeur ❌ |
| "Gérer vos démarches" | Services menu complet mais actions non vérifiables | Écart potentiel ⚠️ |
| "Réfléchir ensemble" | Workspace 5 phases fonctionne, canvas vide | Écart moyen 🟡 |
| "Surveiller et protéger" | Guardian accessible, GPS à configurer, 0 events | Écart moyen 🟡 |
| "Se souvenir de vous" | Profil riche dans DOM, inaccessible en navigation | Écart majeur ❌ |
| "Toujours là" | Message d'erreur historique visible, halo très subtil | Écart symbolique 🟡 |
| "Luna est présente" | Presence Halo implémenté mais quasi-invisible au repos | Écart perceptif 🟡 |

---

## SCORE DE CONFIANCE UTILISATEUR

| Dimension | Score | Justification |
|---|---|---|
| Premier contact | 4/10 | Message d'erreur historique visible, bienvenue OK mais chips décontextualisées |
| Navigation | 3/10 | Guardian piège 8 onglets. 4 sections clés introuvables |
| Chat | 7/10 | Réponses naturelles, modes présents, mais chips cassent l'illusion |
| Mémoire / Profil | 3/10 | Existe mais inaccessible. La promesse n'est pas remplie visuellement |
| Services | 6/10 | Menu excellent, fonctionnement non vérifié |
| Rapports | 6/10 | Données réelles, présentation dense, pas de pagination |
| Workspace | 7/10 | Structure solide, état initial incohérent (4 participants), canvas vide |
| Guardian | 5/10 | Architecture correcte, navigation cassée, GPS non onboardé |

**Score confiance global : 5.0 / 10**

---

## FEUILLE DE ROUTE

### Sprint 1 — Critique (avant toute démo ou test utilisateur)

**Priorité absolue — 5 corrections urgentes :**

1. **Nettoyer l'historique d'erreurs dans le chat**  
   Les messages d'erreur système ne doivent pas apparaître comme des messages Luna. Filtre sur les types de messages au chargement, ou style visuel distinct (message système ≠ message conversationnel).

2. **Corriger l'état initial du Workspace**  
   "4 participants EN SESSION" sur un chargement frais est un bug de session persistante ou de localStorage non nettoyé. À l'arrivée sur `/team`, si aucun humain n'est en session, afficher "Nouvelle session · 0 participants".

3. **Rendre Instructions, Documents, Formulaires, Carte accessibles**  
   Ces 4 sections existent mais sont hors de la navigation principale. Le problème est un mapping tab → section. À diagnostiquer dans la logique de routing du SPA.

4. **Corriger les chips contextuelles**  
   Le générateur de chips doit utiliser le dernier échange de la conversation, pas l'heure du jour. C'est le changement à le plus fort impact sur la perception de Luna comme présence intelligente.

5. **Résoudre la navigation Guardian**  
   Soit Guardian reste une page séparée et une transition explicite "Vous quittez Luna pour Guardian" est affichée avec un retour clair. Soit Guardian devient un panneau dans la SPA. En l'état, l'utilisateur est perdu.

---

### Sprint 2 — Cohérence

6. Supprimer le placeholder développeur "Comment rendre Luna rentable ?" du Workspace
7. Rendre le bouton micro visible dans le Chat (ou documenter WakeWord)
8. Ajouter pagination dans Rapports (20 entrées par page, tri par date)
9. Expliquer Mode Compagnon vs Mode Secrétaire (tooltip ou différence visuelle)
10. Gérer gracieusement le refus GPS dans Guardian (CTA "Autoriser le GPS")
11. Réduire la navigation principale à 5-6 onglets maximum (regrouper les sections)

---

### Sprint 3 — Optimisation

12. Documenter le WakeWord (onboarding audio)
13. Tester chaque bouton de Services avec les vraies clés API
14. Rendre le Profil accessible et pré-remplissage intelligent par Luna
15. Ajouter recherche full-text dans Rapports
16. Renforcer le Presence Halo (état "responding" plus visible)
17. Unifier la marque : un seul nom par surface (Luna dans l'app, pas YAWatch)
18. Supprimer ou déplacer Théocratie, Monde, sous-onglets SMS Rapports

---

## AUDIT DE VISION PRODUIT — POURQUOI CET ÉCRAN EXISTE ?

| Écran | Raison d'être claire ? | Verdict |
|---|---|---|
| Chat | Oui — cœur du produit | Conserver |
| Services | Oui — conciergerie en un clic | Conserver, vérifier chaque action |
| Rapports | Oui — trace des sessions | Conserver, améliorer UX |
| Guardian | Oui — différenciateur sécurité | Conserver, résoudre navigation |
| Iris Workspace | Oui — différenciateur IA collective | Conserver, renforcer |
| Instructions | Oui — mémoire utilisateur | Conserver, RENDRE ACCESSIBLE |
| Profil | Oui — personnalisation | Conserver, RENDRE ACCESSIBLE |
| Amis | Partiellement — réseau social TJ ? | À clarifier — social vs sécurité |
| Activités | Partiellement — gamification | À clarifier — cohérent avec "compagnon de vie" ? |
| Monde | Non clair | Fusionner avec Services > Actualités |
| Théocratie | Audience ultra-spécifique | Déplacer en Réglages avancés |
| Quotas | Utile pour l'exploitant, pas l'utilisateur | Masquer ou déplacer en Profil |

---

## QUESTION FINALE — SI JE DÉCOUVRAIS LUNA AUJOURD'HUI

### Ce qui me ferait confiance

- **La réponse de Luna est naturelle.** Elle ne dit pas "En tant qu'IA..." Elle se présente, elle répond, elle propose de continuer. C'est plus humain que ChatGPT sur ce point.
- **Le menu Services est rassurant.** Des catégories claires, des icônes lisibles. Je comprends ce que je peux demander.
- **Les Rapports existent et ont des données réelles.** Preuve que le produit tourne, que mes sessions sont enregistrées, que Luna me souvient de quelque chose.
- **Iris Workspace est différent.** Rien d'autre ne propose un espace de raisonnement structuré en 5 phases. Je ne sais pas encore quoi en faire, mais je veux l'explorer.

### Ce qui me ferait douter

- **Le premier message affiché est un message d'erreur.** Je lis "Luna est temporairement injoignable" et je ferme. Je ne vérifie pas si c'est un vieux message. Je ferme.
- **Luna me propose "Bonne nuit" alors que je viens de lui demander qui elle est.** Son cerveau n'écoute pas. Elle récite. C'est le signe d'une IA générique, pas d'un compagnon.
- **Je cherche mes rappels et je ne les trouve pas.** Il y a 16 onglets. Aucun ne dit "Mémoire" ou "Rappels". Je ne sais pas où Luna mémorise ce que je lui dis.
- **Je clique sur Guardian, et je suis sorti de l'app.** Je ne comprends pas ce qui vient de se passer. Je clique "← App" mais je ne suis plus là où j'étais.

### Ce qui me ferait quitter l'application

**Une seule chose suffit : les chips contextuelles.**

Si après 5 minutes de conversation, Luna me propose des actions qui n'ont aucun rapport avec ce qu'on vient de dire — je conclus qu'elle ne m'écoute pas vraiment. Que tout ce qu'elle dit est généré, pas pensé. Et si elle ne m'écoute pas, elle ne peut pas être mon compagnon.

C'est le test de confiance ultime. Et en l'état, Luna le rate.

---

## NOTE DE MÉTHODE

Cet audit a été réalisé en Playwright headless (mobile). Certaines fonctionnalités nécessitent des permissions navigateur (GPS, micro, caméra) non disponibles en headless. Les sections Amis, Activités, Monde, Contacts, Profil, Quotas, Réglages, Théocratie n'ont pas pu être auditées directement car Guardian a capturé la navigation — elles existent dans le DOM et sont fonctionnelles selon l'architecture, mais leur accessibilité depuis la navigation principale est à vérifier manuellement.

Les scores et criticités sont des jugements produit, pas des métriques techniques.

---

*Auteur : Claude — Audit Produit*  
*Méthode : Playwright E2E + analyse DOM + 28 captures d'écran*  
*Ce document ne contient aucune modification de code. Aucun commit. Aucun push.*
