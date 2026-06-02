# Claude — Inbox de collaboration IA

Ce fichier sert de point de passage entre Ludo, Codex, Claude, Kimi et DeepSeek pour le chantier Luna.

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

## Tâche prioritaire actuelle — Iris Workspace Phase 1 (2 juin 2026)

**Chantier actif : Iris Workspace comme système de projection intelligente** (objectif 020).
Voir : `docs/IRIS_WORKSPACE_VISION.md` (vision Ludo), `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_IRIS_WORKSPACE_VISION.md` (spec DeepSeek), `docs/AGENTS_COLLABORATION/agents/CLAUDE_IMPL_IRIS_WORKSPACE_020.md` (plan Claude).

### Instructions DeepSeek

**Tâche : améliorer `inferCommandRenderFromText` dans `static/simli.html` (ligne ~3373)**

La fonction doit détecter les 12 types de projection depuis le texte d'Iris :
- Présence de 2+ nombres → `kpi_cards`
- Présence de dates (15 juin, "la semaine prochaine") → `timeline`
- "phase"/"étape" + numéros → `roadmap`
- "vs" ou deux entités nommées comparées → `comparison`
- "risque"/"opportunité"/"résumé" du document → `document_insight`
- Texte > 100 mots sans structure → `context_panel`
- "évolution"/"tendance"/"croissance" + chiffres → `chart`

Livrer dans : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_IRIS_WORKSPACE_020.md`
Format attendu : bloc JS complet de la fonction + explication des regex.
Ne pas modifier d'autres fichiers. Ne pas déployer.

### Instructions Kimi

**Tâche : améliorer `_icsBuildPayload` dans `static/simli.html` (ligne ~3384)**

Objectif : extraire des données réelles du texte pour construire des payloads riches.

Pour `kpi_cards` : regex `/(\d[\d\s,.]*)\s*(€|euro|client|contrat|%|km|kg)/gi` → extraire valeur + label
Pour `timeline` : regex dates → extraire "label : date" pairs
Pour `chart` : chercher séquences de nombres séparées par virgules ou "et"
Pour `comparison` : détecter les deux entités comparées + leurs attributs

Livrer dans : `docs/AGENTS_COLLABORATION/agents/KIMI_IRIS_WORKSPACE_020.md`
Format attendu : nouvelle version de `_icsBuildPayload` + section fallback transcript améliorée.
Ne pas modifier d'autres fichiers. Ne pas déployer.

### Instructions Codex

**Tâche : tester + rapporter l'état actuel**

1. Ouvrir `/simli` sur le serveur déployé
2. Parler à Iris — vérifier que le `context_panel` s'affiche après chaque réponse
3. Tester les phrases : "quel est mon état ?", "liste mes services", "compare EDF et Engie"
4. Rapporter dans `docs/AGENTS_COLLABORATION/agents/CODEX_IRIS_WORKSPACE_020.md` :
   - Quel type de render s'affiche pour chaque phrase
   - Est-ce le bon type ?
   - Qu'est-ce qui devrait s'afficher mais ne s'affiche pas ?

Claude implémente Phase 1 (6 nouveaux types) une fois les livrables DeepSeek + Kimi reçus.

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
