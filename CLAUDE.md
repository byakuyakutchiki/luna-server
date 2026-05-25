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

**Objective 008 — OUVERT** 🔄 DeepSeek temps réel dans l'expérience APK

### Statut Objectives

| Objective | Statut | Détails |
|---|---|---|
| 001-006 | ✅ Baseline | Monitoring de base implémenté sur 10 zones |
| 007 Télémétrie Voix | ✅ **TERMINÉ** | 11 événements remontés en test réel, chronologie complète capturée |
| 007-bis Refresh APK | 📋 **Planned** | pull-to-refresh + apk_manual_refresh_triggered |
| **008 DeepSeek Temps Réel** | 🔄 **EN COURS** | Architecture cadrée, implémentation multi-agents en cours |

### Objective 007 — Résultat test réel (2026-05-25 18:47)

**Ludovic téléphone — APK v2.8 connectée — 11 événements capturés**

```
✅ Heartbeat OK (26s)
✅ Télémétrie OK (11 événements)
✅ Chronologie complète : clic → token OK → micro OK → capture active
   → WS créé/ouvert → premier audio envoyé → WS fermé (~5s)
❌ Pas de réponse audio reçue

DIAGNOSTIC : Blocage côté serveur vocal / OpenAI Realtime / fermeture WS prématurée
CAUSE PROBABLE : OpenAI n'a pas reçu premier audio OU n'a pas envoyé réponse
PROCHAINE ÉTAPE : Objective 008-diag investiguer logs /ws/luna-voice serveur
```

**Documentation** : `docs/AGENTS_COLLABORATION/OBJECTIF_007_RESULTAT_TEST.md`

### Objective 008 — DeepSeek temps réel APK

**Décision Ludovic** : DeepSeek devient IA "dans le téléphone" pour diagnostiquer incidents en temps réel.

**Architecture**:
```
APK téléphone (signaux)
  → Serveur Luna (clé DeepSeek protégée côté serveur)
  → DeepSeek API (diagnostic structuré)
  → Cockpit fondateur (recommandation exploitable)
```

**Cas d'usage dès 008**:
1. **Voix APK** — premier audio envoyé mais WS ferme → analyse chronologie 20+ événements
2. **Cache/WebView** — frontend obsolète → détecte mismatch version, propose clear cache
3. **Boutons futurs** — clic → aucune action → déploie DeepSeek incident
4. **UI mobile** — régression détectée → rapportée avec snapshot

**Règles d'or**:
- ✅ Clé DeepSeek côté serveur UNIQUEMENT
- ✅ Mode incident UNIQUEMENT (pas d'appels IA sans anomalie)
- ✅ Fenêtre compacte 30-60s (pas d'audio brut, pas de secret)
- ✅ Sortie structurée JSON (diagnostic + preuve + cause + zone + action + risque)

**Agents assignés**:

| Agent | Mission | Branche |
|---|---|---|
| **DeepSeek** | Format événement minimal, seuils incident, diagnostics type | `ds/objectif-008-*` |
| **Claude** | Endpoint serveur, protection clé, rate limiting, journal, cockpit | lead 008 |
| **Kimi** | Textes cockpit : observe / suppose / recommande / ne peut pas | `kimi/objectif-008-*` |
| **Codex** | Garde-fous : no API key in APK, no spam, no secrets, no auto-correct | `codex/objectif-008-*` |
| **Cursor** | Intégration UI, icônes cockpit, non-régression | `cursor/objectif-008-*` |

**Livrables attendus**:

1. `agents/DEEPSEEK_AVIS_008_TEMPS_REEL_APK.md` — format + seuils + diagnostics
2. Claude implémentation — `POST /api/deepseek/diagnose`, clé protégée, rate limit
3. Kimi formulation — textes cockpit lisibles + non-trompeurs
4. Codex validation — garde-fous + aucun secret
5. Cursor UI — cockpit intégrée + non-régression

**Documentation complète** : `docs/AGENTS_COLLABORATION/OBJECTIF_008_DEEPSEEK_TEMPS_REEL_APK.md`

### Ancien Objective — Diagnostic serveur voix (007-diag)

Le diagnostic serveur voix (logs /ws/luna-voice, OpenAI Realtime state) sera capturé
comme étape préalable à Objective 008 (Claude doit d'abord localiser exact du blocage).

Voir : `docs/AGENTS_COLLABORATION/OBJECTIF_007_RESULTAT_TEST.md` → "Points à vérifier"

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
