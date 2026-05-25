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

## Tâche prioritaire actuelle

**Objective 009 — OUVERT** 🔄 Corriger les coupures audio Luna — diagnostic multi-agents

### Statut Objectives

| Objective | Statut | Détails |
|---|---|---|
| 001-006 | ✅ Baseline | Monitoring de base implémenté sur 10 zones |
| 007 Télémétrie Voix | ✅ **TERMINÉ** | 11 événements remontés en test réel |
| 008 Voix Pipeline | ✅ **VALIDÉ PARTIELLEMENT** | Cause OpenAI quota insuffisant identifiée + corrigée |
| 008-stabilité Coupures | 🔄 **FUSIONNÉ AVEC 009** | Objectif 009 plus complet multi-agents |
| **009 Stabilité Voix** | 🔄 **EN COURS** | Diagnostic multi-agents de coupures audio |

### Objective 009 — Stabilité voix Luna

**Problème** : Luna s'arrête parfois de parler / coupe la réponse sans raison claire

**Approche** : Diagnostic multi-agents coordonné, correction minimale

**Agents et missions** :

| Agent | Mission | Deadline |
|---|---|---|
| **Ludovic** 🔴 | Test réel + heure exacte + observation | ASAP |
| **Claude** 🔵 | Lead : logs serveur, cause probable, correction | 30min après Ludovic |
| **DeepSeek** 🟠 | Télémétrie APK, seuils incident, diagnostics type | Parallèle Claude |
| **Kimi** 🟢 | Textes cockpit clairs et non-culpabilisants | Après Claude |
| **Cursor** 🟡 | UI mobile vérification, états vocaux | Parallèle DeepSeek |
| **Codex** ⚪ | Coordination, synthèse, garde-fous | Final |

**Points à investiguer** (Claude priority order) :

1. **Logs Cloud Run** à heure exacte de Ludovic
   - /ws/luna-voice ouvert/fermé quand ?
   - Code fermeture WS (1000 vs autre) ?

2. **OpenAI Realtime state**
   - Timeout après combien de secondes ?
   - VAD a arrêté la génération ?
   - response.audio.delta complète ou non ?

3. **WebSocket fermé par qui ?**
   - Serveur côté Luna ?
   - Client APK ?

4. **Correction proposée**
   - Minimal : 1-3 lignes max
   - Pas de refactor WebSocket
   - Pas de changement modèle OpenAI

**Livrables attendus** :

1. Ludovic : heure exacte + comportement test
2. Claude : cause probable + logs preuve + correction + risques
3. DeepSeek : seuils incident + diagnostics + `DEEPSEEK_AVIS_009.md`
4. Kimi : textes cockpit par zone + `KIMI_AVIS_009.md`
5. Cursor : screenshots UI + propositions + `CURSOR_AVIS_009.md`
6. Codex : synthèse `DECISION_FINALE_009.md` + validation checklist

**Timeline estimée** : ~2h30 (Ludovic 15min + Claude 30min + DeepSeek 30min + Kimi 20min + Cursor 20min + Codex 30min)

**Documentation complète** : `docs/AGENTS_COLLABORATION/OBJECTIF_009_STABILITE_VOIX.md`

**Status avant Objective 009** :

```
✅ Voix fonctionne avec gpt-realtime-mini
✅ Pipeline valide : APK → serveur → OpenAI → audio retour
✅ Cause du silence total résolue : OpenAI quota
⚠️ Problème restant : Luna coupe/s'arrête pendant conversation
```

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
