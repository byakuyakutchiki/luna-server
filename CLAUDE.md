# Claude — Inbox de collaboration IA

Ce fichier sert de point de passage entre Ludo, Codex, Claude, Kimi et DeepSeek pour le chantier Luna.

---

## ⚠️ RÈGLE ABSOLUE AVANT TOUTE MODIFICATION

Claude, **AVANT DE MODIFIER QUOI QUE CE SOIT** :

Tu dois considérer cette demande comme un **refactoring ciblé** et **NON comme une refonte générale** de l'application.

### Tu ne dois PAS :
- supprimer des fonctionnalités existantes
- supprimer des écrans existants
- supprimer des routes existantes
- supprimer des workflows existants
- supprimer des services existants
- supprimer des composants existants
- réécrire des modules qui ne sont pas concernés
- simplifier l'application en retirant des fonctionnalités
- casser la compatibilité des fonctionnalités actuelles

### PÉRIMÈTRE AUTORISÉ (interventions ciblées)

**Luna** : expérience conversationnelle, mémoire utilisateur, vocal, widget Hey Luna, chargement du contexte.

**Guardian** : déclenchement vocal, widget sécurité, messages d'urgence, confirmations vocales, robustesse des alertes.

**Coordination Luna ↔ Iris ↔ Guardian** : circulation du contexte, orchestration, expérience utilisateur.

### PÉRIMÈTRE INTERDIT (sauf nécessité technique critique)
- Iris Workspace (moteur de décisions, réserves, dossier final, dashboard, workflow, analyse, propositions, sources, actions)
- Architecture SaaS, licences, sécurité serveur, authentification, facturation, monitoring
- Infrastructure Cloud Run, architecture Redis
- Architecture Guardian existante
- APIs existantes qui fonctionnent déjà

### PRINCIPE DE PRÉCAUTION

Si un changement risque de :
- supprimer une fonctionnalité
- casser un workflow
- modifier un comportement existant

→ **arrêter** — expliquer à Ludo — **demander validation avant de continuer**.

### OBJECTIF

Nous ne faisons **PAS** une réécriture de Luna, de YAWatch ou du Workspace.
Nous faisons uniquement une **amélioration ciblée** de l'expérience vocale, du contexte utilisateur et du mode Guardian.
**Tout le reste doit continuer à fonctionner exactement comme aujourd'hui.**

---

## Gouvernance IA — Méthode de travail

### Rôles

**Claude = Lead technique**
- Analyse l'architecture et prend les décisions techniques
- Lit et écrit le code sur GitHub
- Valide tout changement avant application en production
- Garant de la stabilité, de la sécurité et des intérêts de Ludo (fondateur)

**ChatGPT/Codex = Interface vocale + Relai**
- Capture la voix de Ludo et reformule la demande proprement
- Peut générer des suggestions rapides de code
- Relaie les décisions de Claude vers Ludo à l'oral
- Ne pousse rien en production sans validation Claude

### Flux de travail

```
Ludo (voix) → ChatGPT reformule → Claude analyse + décide
     Claude implémente / valide → ChatGPT lit le résultat à Ludo
```

### Protocole obligatoire avant toute modification

```
1. git pull origin main
2. Lire CLAUDE.md (ce fichier)
3. Lire docs/METHODE_TRAVAIL_FONDATEUR.md
4. Lire le prompt actif : docs/PROMPT_CLAUDE_MONITORING_*.md
5. Vérifier git log --oneline -5 (voir ce que l'autre IA vient de faire)
6. Ne travailler que sur l'objectif indiqué dans "Tâche prioritaire actuelle"
7. Ne pas toucher aux fichiers déjà en chantier par l'autre IA
```

### Règles non-négociables

1. **Claude a le dernier mot** sur toute modification production
2. **Aucun push direct de Codex** sans revue Claude préalable
3. **Ludo valide** toute modification majeure avant merge sur `main`
4. **Anti-régression** : analyser les dépendances avant toute modification
5. **Validation humaine obligatoire** pour : refactorisation, changement d'API, sécurité, licensing, migration BDD
6. **Stabilité avant optimisation** : ne jamais casser une fonctionnalité stable pour un gain mineur
7. **Zéro doublon** : si l'objectif est déjà implémenté ou en cours, passer au suivant

### Axes de travail (éviter les doublons)

| IA | Rôle principal |
|---|---|
| **Claude** | Implémentation code, revue des PR Codex, monitoring backend |
| **Codex** | Préparation docs/prompts, UI/CSS, structure cahiers des charges |
| **Ludo** | Vision fondateur, validation, arbitrage, définition des objectifs |

### Priorités fondateur

- Continuité de service pour les exploitants
- Modèle économique 70/30 préservé
- PV de recette et verrouillage serveur intacts
- Expérience utilisateur final avant tout

---

Objectif global : transformer le cahier des charges fonctionnel en monitoring concret, objectif par objectif, pour que chaque onglet de l'application soit vérifié sur sa promesse utilisateur réelle.

## Source de vérité

- Cahier des charges : `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Methode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`
- Repo principal : `byakuyakutchiki/luna-server`
- Backend : `luna_web.py`
- Guide technique : `GUIDE_DEV.md`

## Boussole fondateur

Ludo est le fondateur. Les IA travaillent dans son interet et dans l'interet de la qualite de Luna.

Priorites non negociables :

- l'application doit fonctionner avant d'ajouter de nouvelles ambitions ;
- tous les boutons visibles doivent etre audites progressivement ;
- aucune modification ne doit casser l'APK, le WebView ou les dashboards ;
- la qualite graphique doit rester premium ;
- le modele licence / royalties doit rester protege ;
- l'exploitant doit pouvoir exploiter, mais pas reproduire ou contourner la technologie ;
- le fondateur doit voir les indicateurs necessaires a ses droits, sans aspirer la comptabilite interne complete de l'exploitant.

Lire `docs/METHODE_TRAVAIL_FONDATEUR.md` avant de proposer une architecture ou une modification sensible.

## Règle de travail

Ne pas travailler sur tous les onglets en même temps.

On valide un objectif à la fois :

1. Instructions
2. Services / Concierge
3. Documents
4. Formulaires
5. Cartes
6. Puis les autres onglets

Pour chaque objectif, il faut produire :

- objectif utilisateur clair
- checks techniques
- checks fonctionnels
- statut `ok`, `warning`, `degraded`, `critical`
- preuves de réussite
- auto-heal possible
- limites à ne pas franchir
- procédure de test

## Tâche prioritaire actuelle — Iris Visual System V2 + Teams UI (2 juin 2026)

**Ambition : numéro mondial. Chaque écran Iris doit être meilleur que ce qui existe.**

**Backend Teams : TERMINÉ** (commit c2b1990 — IrisSessionManager, 10 routes API, WS handler collaboratif).
**Ce qui reste : UX frontend (Kimi) + Inférence intelligente (DeepSeek) + 8 nouveaux types (Claude après livrables).**

---

### Instructions Kimi — URGENT

**Fichier mission complet : `docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_021.md`**

Trois chantiers simultanés :

**1. Teams Overlay** (panneau participants style Zoom/Teams dans `/simli`)
- Liste participants avec rôles (owner 👑, trusted 👤, guest 🟢)
- Indicateur qui parle (anneau pulsant vert autour avatar)
- Boutons mute/kick (owner uniquement, visibles au hover)
- Bannière actions en attente de validation (owner approuve/rejette)
- Mobile : barre compacte horizontal + déploiement slide down

**2. Light / Dark Mode** (vrai thème clair premium)
- Variables CSS complètes : `--bg-base`, `--bg-panel`, `--text-primary`, etc.
- Palettes dark ET light dans `:root` vs `[data-theme="light"]`
- Bouton toggle [🌙/☀] dans la barre basse, persisté dans localStorage
- Aucune inversion de couleur — vraie palette clair inspirée MacOS/Linear

**3. 8 nouveaux render_type : specs visuelles** (skeleton HTML + CSS)
`kanban_board`, `contact_board`, `map_board`, `decision_board`,
`budget_board`, `meeting_board`, `media_board`, `form_board`

Livrer dans : `docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_021.md` (en réponse dans ce fichier)
Ne pas modifier luna_web.py. Ne pas déployer.

---

### Instructions DeepSeek — URGENT

**Fichier mission complet : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_IRIS_021.md`**

**Tâche : réécrire `inferCommandRenderFromText` pour 20 types de projection**

La fonction actuelle est trop basique → Iris atterrit sur `context_panel` presque toujours.
Version cible : 20 types, ordre de priorité défini, regex robustes avec accents.

Plus : améliorer `_icsBuildPayload` pour extraire des données réelles du texte sur 8 types :
`kpi_cards` (chiffres + unités), `timeline` (dates), `chart` (séries numériques),
`decision_board` (options + pros/cons), `budget_board`, `meeting_board`, `kanban_board`, `contact_board`

Livrer dans : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_IRIS_021_LIVRABLE.md`
Format : bloc JS complet prêt à coller dans `simli.html` + matrice 40 phrases test.
Ne pas modifier luna_web.py. Ne pas déployer.

---

### Instructions Codex — TEST TERRAIN

**Tâche : tester l'état actuel de l'Iris Command Screen déployé**

1. Ouvrir `/simli` sur `https://luna-beta-674304336025.europe-west1.run.app`
2. Parler à Iris, phrases à tester :
   - "quel est mon état ?" → attendu : `status_rail`
   - "liste mes services" → attendu : `data_board`
   - "compare EDF et Engie" → attendu : `comparison` ou `decision_board`
   - "montre-moi un graphique de mes dépenses" → attendu : `chart`
   - "fais-moi un plan d'action pour déménager" → attendu : `action_board`
   - "quelles sont mes échéances ce mois ?" → attendu : `timeline`
3. Rapporter dans `docs/AGENTS_COLLABORATION/agents/CODEX_IRIS_021_TERRAIN.md` :
   - render_type réellement affiché pour chaque phrase
   - Est-ce le bon type ?
   - Texte exact d'Iris pour chaque réponse (copier-coller)

---

### Ce que Claude implémente après livrables

1. Intégrer `inferCommandRenderFromText` V2 de DeepSeek dans `simli.html`
2. Intégrer `_icsBuildPayload` amélioré de DeepSeek
3. Ajouter les 8 nouveaux `renderIrisCommand` cases en JS/HTML (specs Kimi)
4. Ajouter CSS dark/light variables (specs Kimi)
5. Ajouter Teams overlay HTML/CSS/JS (consomme les API backend déjà disponibles)
6. Ajouter toggle dark/light mode
7. Déployer et valider avec Codex

---

## Archive — Iris Command Screen V1 (2 juin 2026)

**Chantier actif : Iris Command Screen** — panneau visuel temps réel dans `/simli` (page audio Iris).

### Contexte pour DeepSeek, Kimi, Codex

L'Iris Command Screen est un panneau latéral holographique qui s'affiche pendant la conversation vocale avec Iris.
Il doit **toujours afficher du contenu** après chaque réponse d'Iris.

**Architecture actuelle :**
- Page : `static/simli.html`
- Backend bridge : `integrations/openai/web_voice_bridge.py`
- Modèle voix : `gpt-realtime-mini` (seul modèle disponible sur ce compte OpenAI)
- Tool serveur : `iris_render` dans `VOICE_TOOLS` (`realtime_bridge.py`) + handler dans `web_voice_bridge.py`
- System prompt Iris : `_IRIS_SYSTEM` dans `luna_web.py` (ligne ~8912)

**Problème connu :**
`gpt-realtime-mini` n'appelle pas `iris_render` de manière fiable.
Le fallback client compense : quand le transcript Iris arrive sans render serveur, le client affiche la réponse dans un `context_panel`.

**Séquence d'événements OpenAI Realtime (ordre réel) :**
1. `response.audio.delta` → chunks audio envoyés au client
2. `response.audio.done` → `{type:"audio_done"}` envoyé au client
3. `response.audio_transcript.done` → `{type:"transcript", role:"luna", text:"..."}` envoyé au client

⚠️ Le transcript arrive APRÈS `audio_done`. Tout fallback basé sur `audio_done` sera vide.

**Fallback actuel (commit `20042bc` + correction suivante) :**
- Sur `transcript` role=luna : debounce 300ms → si pas de render serveur, affiche `context_panel` avec le texte d'Iris
- Variable `_icsFallbackTimer` : debounce pour laisser tous les chunks arriver

**6 types de render disponibles dans `renderIrisCommand()` :**
- `data_board` — tableau colonnes/lignes avec badges
- `document_draft` — courrier/lettre avec placeholders
- `action_board` — checklist avec cases et confirmation
- `context_panel` — sections titre/corps (fallback par défaut)
- `missing_info` — champs manquants + suggestions
- `status_rail` — liste services avec statuts colorés

### Ce qui reste à faire

| Tâche | Priorité | Assigné à |
|---|---|---|
| Tester fallback debounce (transcript → context_panel) | 🔴 URGENT | Codex teste + rapporte |
| Améliorer `inferCommandRenderFromText` — détecter plus de patterns | 🟡 | DeepSeek |
| V2 : sauvegarde du contenu affiché (bouton "Sauvegarder") | 🟢 | À planifier |
| V2 : export PDF/DOCX depuis le Command Screen | 🟢 | À planifier |
| V2 : actions réelles avec confirmation (SMS, note, rappel) | 🟢 | À planifier |

### Règles pour les contributions

1. **Ne jamais modifier** `.env`, `pv_lock.json`, clés API
2. **Ne jamais déployer** sans validation explicite de Ludo
3. **Ne modifier que** `static/simli.html` et `luna_web.py` pour l'ICS
4. Tout changement doit passer par PR ou patch envoyé ici dans CLAUDE.md
5. Claude a le dernier mot avant tout merge

---

## Archive — Monitoring de base TERMINÉ — 10 objectifs implémentés dans `GET /api/admin/objectives` :

| Objectif | Commit | Statut |
|---|---|---|
| Services / Concierge | `feat: monitoring Services/Concierge` | ✅ |
| Documents / Vault IA | `feat: monitoring Documents/Vault IA` | ✅ |
| Formulaires | `feat: monitoring Formulaires` | ✅ |
| Cartes / Localisation | `feat: monitoring Cartes / Localisation` | ✅ |
| Amis / Réseau Social | `feat: monitoring Amis / Réseau Social` | ✅ |
| Activités / Gamification | `feat: monitoring Activités / Gamification` | ✅ |
| Monde | `feat: monitoring Monde, Profil, Quotas, Réglages` | ✅ |
| Profil | idem | ✅ |
| Quotas | idem | ✅ |
| Réglages | idem | ✅ |

État au 25 mai 2026 : tous les objectifs de monitoring de base sont implémentés.

Prochain chantier possible :
- Monitoring Voix (objectif 12 du cahier des charges) : `docs/PROMPT_CLAUDE_MONITORING_VOIX.md`
- Ou audit fonctionnel des onglets déjà implémentés

## Archive objectif précédent — Amis

## Archive objectif précédent — Cartes

## Archive objectif précédent — Formulaires

## Archive objectif précédent — Documents / Vault IA

## Archive objectif précédent — Services / Concierge

## Sous-services Services / Concierge à surveiller

- SMS
- appel vocal
- email
- invitation visio
- compte-rendu / conclusions
- note / mémoire
- météo
- actualités
- recherche web
- lieux / commerces
- restaurants
- page web
- paiement
- vols
- hôtels
- secrétariat

## Contraintes fortes

Le monitoring ne doit jamais déclencher d'action réelle engageante.

Donc ne pas envoyer pendant un check :

- SMS réel
- appel réel
- email réel
- paiement Stripe
- réservation Duffel
- réservation hôtel
- réservation restaurant

Le monitoring doit seulement vérifier :

- fonctions présentes
- variables d'environnement présentes
- modules importables
- configuration cohérente
- dépendance optionnelle ou critique
- dernier état connu si disponible

## États attendus

- `ok` : objectif atteint
- `warning` : service optionnel absent ou profil incomplet
- `degraded` : service partiellement utilisable
- `critical` : objectif inutilisable ou action dangereuse possible

## Important

Stripe peut être absent sur le serveur fondateur sans être une panne critique.

Duffel peut être absent tant que les vols/hôtels ne sont pas activés en production.

Serper absent doit dégrader recherche web, lieux et restaurants, mais ne doit pas casser tout l'onglet Services.

Twilio absent est critique pour SMS/appels si ces actions sont promises à l'utilisateur.

## Réponse attendue après implémentation

Quand tu termines, indique :

- fichiers modifiés
- exemple JSON réel de `/api/admin/objectives`
- comment tester sans action réelle
- services `ok`, `warning`, `degraded`, `critical`
- ce qui reste à faire avant de passer à Documents
