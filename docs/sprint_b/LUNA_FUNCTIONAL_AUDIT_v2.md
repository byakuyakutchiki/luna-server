# LUNA FUNCTIONAL AUDIT v2 — AUDIT PRODUIT GLOBAL OFFICIEL

**Produit :** YAWatch-LUNA  
**Dépôt audité :** https://github.com/byakuyakutchiki/luna-server  
**Date de l'audit :** 2026-06-14  
**Méthode :** lecture de code, tests d'endpoints, démarrage local, inspection des pages statiques. Aucun code modifié. Aucun commit.  
**Auteur :** Kimi Code CLI (auditeur produit indépendant)

---

## Résumé exécutif

YAWatch-LUNA est un produit très ambitieux — une assistante IA autonome multi-canale (chat, voix, visio), un workspace de raisonnement collectif (Iris), un système de sécurité (Guardian), une mémoire Redis, de la gamification et une gouvernance multi-agents. L'implémentation technique est impressionnante par sa couverture fonctionnelle.

Cependant, **la cohérence produit est gravement compromise** par :

1. **Un verrouillage initial absolu** : le serveur est inutilisable tant qu'un PV de recette n'est pas signé, et le module de signature n'est pas livré dans ce dépôt.
2. **Des promesses non tenues** : visio avatar, appels téléphoniques, conciergerie web, réservations directes sont annoncés mais partiellement ou totalement indisponibles.
3. **Des bugs de production** : appels de méthodes inexistantes dans le moteur d'instructions.
4. **Des incohérences commerciales** : prix et quotas différents selon le document consulté (README, guides opérationnels, état de projet, code).
5. **Une UX trompeuse** : pages de démo hardcodées, boutons affichés comme fonctionnels mais renvoyant "disponible en Phase P0.x", actions contextuelles proposées sans contexte.
6. **Une dépendance totale à OpenAI** : sans clé valide, le cœur conversationnel est mort.

**Score global sur 10 : 3,5 / 10**

> Le produit donne l'impression d'une démo très avancée, pas d'un service fiable prêt à être mis entre les mains d'utilisateurs réels.

---

## Top 20 incohérences produit (par gravité)

| # | Incohérence | Pilier | Gravité | Preuve |
|---|-------------|--------|---------|--------|
| 1 | **PV de recette bloque toute l'app, mais le module `pv_recette` n'est pas dans le dépôt.** | Global | 🔴 Critique | Démarrage local : `Module pv_recette non disponible — fallback .env`. `/api/setup/status` retourne `error: Module pv_recette non disponible`. |
| 2 | **Chat central mort sans clé OpenAI valide** : erreur 401 non catchée, message utilisateur "Luna a un souci technique". | Luna Audio | 🔴 Critique | Test `POST /api/chat` → `{"response":"Luna a un souci technique..."}`. Log OpenAI 401. |
| 3 | **Appels téléphoniques et visio annoncés, mais refusés par le dispatcher.** | Actions | 🔴 Critique | `core/actions/dispatcher.py:267-274` et `:350-357` retournent `feature_not_available`. |
| 4 | **Bug `self.sms.send(...)` dans `core/instructions/executor.py:626` : méthode inexistante** (devrait être `send_sms`). | Instructions | 🔴 Critique | Code source lu. Plantera à l'exécution d'une visio planifiée. |
| 5 | **Bug `self.action_service.create_action_request(...)` dans `core/instructions/executor.py:212` : méthode inexistante** (devrait être `propose_action`). | Instructions | 🔴 Critique | Code source lu. Les confirmations d'instructions planifiées sont cassées. |
| 6 | **Quotas du README (50 SMS / 60 min visio) vs code (25 SMS / 12 min visio) vs état projet (20 SMS / 15 min visio) vs guides (25/12).** | Offres | 🔴 Critique | `README.md:52-55`, `quota_guard.py:38-59`, `ETAT_PROJET_LUNA_V3.md:112-114`, `GUIDE_DEV.md:660-662`. |
| 7 | **Prix affichés différents : 79€/139€/399€ selon les documents.** | Offres | 🔴 Critique | `GUIDE_DEV.md:660` = 79€, `ETAT_PROJET_LUNA_V3.md:112` = 139€, `PROMPT_UX_UI_PREMIUM.md` (non vérifié en intégralité) = jusqu'à 399€. |
| 8 | **Visio/Tavus est retiré de la vision produit, mais reste un pilier technique** : routes, pages, setup, badges. | Vision produit | 🔴 Critique | `docs/audit_ux/FEATURE_DECISION_V1.md` dit pivot workspace. Pourtant `LUNA_MODE=full` par défaut, `static/simli.html`, routes `/api/visio/*`, intégration Tavus 787 lignes. |
| 9 | **Pages `dashboard.html`, `prospects.html`, `workspace.html`, `team_workspace.html` sont des maquettes hardcodées** (pas d'appels API, données `DEMO_SESSIONS`). | UX | 🔴 Critique | `static/dashboard.html`, `static/prospects.html`, `static/workspace.html`, `static/team_workspace.html`. |
| 10 | **`/api/instructions` interprète "Rappelle-moi de prendre mes médicaments à 20h" comme un appel (`call_contact`) à `contact_unknown`.** | Instructions | 🟠 Haute | Test réel : `POST /api/instructions` avec ce texte → action `"call"`, target `"contact_unknown"`. |
| 11 | **`QuotaGuard` ne contrôle que les SMS**, bien qu'il déclare des limites voix/visio. | Quotas | 🟠 Haute | `core/actions/quota_guard.py:154-165` : `Seuls les SMS consomment du quota pour l'instant`. |
| 12 | **Confirmation des actions non persistante** : cache mémoire uniquement, perdues au redémarrage. | Actions | 🟠 Haute | `core/actions/confirmation.py:50` : `self._pending: Dict[int, Dict[str, ActionRequest]]`. |
| 13 | **Boucle instructions non multi-tenant** : `TENANT_ID=1` en dur au chargement. | Multi-tenant | 🟠 Haute | `luna_web.py` ligne de `_load_instructions_to_scheduler`. |
| 14 | **"Iris Audio" dans le front redirige vers `/simli` (visio avatar), pas de l'audio.** | Luna Audio | 🟠 Haute | `static/index.html` carte + menu flottant → `startCall()` → `/simli?duration=...`. |
| 15 | **Concierge `search_web` retourne "Service de recherche non configure"** alors que la carte est affichée. | Conciergerie | 🟠 Haute | Test `POST /api/concierge/action` action `search_web`. |
| 16 | **Carte "Voyager" proactif promet "Chercher un vol" mais ne fait que changer d'onglet.** | UX | 🟠 Haute | `static/index.html` ligne proactive card ~6889-6890. |
| 17 | **Perception caméra promise, mais exclue de l'image Docker Cloud Run** (`ultralytics`/`opencv` non installés). | Guardian | 🟠 Haute | `Dockerfile` + `requirements-cloudrun.txt`. |
| 18 | **Actions contextuelles génériques sans contexte** : "Appelle", "Envoie un SMS à", "Rappelle-moi de" suggérées à l'utilisateur sans données. | UX | 🟡 Moyenne | `static/index.html` inputSuggestions l. 4540-4555, chips onboarding l. 6736-6740. |
| 19 | **Module `core.meeting` existe mais MeetingBaas est optionnel/désactivé** : "Luna rejoint ta réunion" n'est pas fiable. | Réunions | 🟡 Moyenne | `integrations/recall/meetingbaas_client.py`, `MEETINGBAAS_API_KEY` manquant par défaut. |
| 20 | **Tests automatisés inexistants** : seuls 3 scripts de test isolés, pas de suite pytest. | Qualité | 🟡 Moyenne | `find . -name "test*.py"` → 3 fichiers, pas de `tests/`, pas de `pytest.ini`. |

---

## Top 10 fonctionnalités cassées — À corriger immédiatement

| # | Fonctionnalité | Symptôme | Fichier / Preuve | Criticité |
|---|----------------|----------|------------------|-----------|
| 1 | **Signature du PV de recette** | Module `pv_recette` absent, setup impossible à terminer. | `luna_web.py`, logs au démarrage | 🔴 |
| 2 | **Chat texte** | Répond "Luna a un souci technique" si OpenAI retourne 401. | Test `POST /api/chat` | 🔴 |
| 3 | **Appels téléphoniques sortants** | Dispatcher retourne `feature_not_available`. | `core/actions/dispatcher.py:267` | 🔴 |
| 4 | **Visio / appels vidéo** | Dispatcher retourne `feature_not_available`. | `core/actions/dispatcher.py:350` | 🔴 |
| 5 | **Visio planifiée via instructions** | `self.sms.send()` méthode inexistante → plantage. | `core/instructions/executor.py:626` | 🔴 |
| 6 | **Confirmation des instructions** | `self.action_service.create_action_request()` inexistant. | `core/instructions/executor.py:212` | 🔴 |
| 7 | **Exécution manuelle d'instruction** | Endpoint passe un `Instruction` schema là où `ParsedInstruction` est attendu. | `luna_web.py:/api/instructions/{instr_id}/execute` | 🔴 |
| 8 | **Recherche web concierge** | Retourne "Service de recherche non configure". | Test `POST /api/concierge/action` | 🟠 |
| 9 | **Assistant analyze / generate** | Échoue avec 401 OpenAI exposé au client. | Test `POST /api/assistant/analyze` | 🟠 |
| 10 | **Perception caméra en Cloud Run** | Dépendances absentes (`ultralytics`, `opencv`). | `Dockerfile`, `requirements-cloudrun.txt` | 🟠 |

---

## Top 10 fonctionnalités incohérentes — À revoir

| # | Fonctionnalité | Promesse | Réalité | Fichier / Preuve |
|---|----------------|----------|---------|------------------|
| 1 | **Offres & quotas** | 50 SMS / 60 min visio (README). | 25 SMS / 12 min visio (code), 20/15 (état projet). | README, quota_guard.py, ETAT_PROJET |
| 2 | **Prix** | 79€ Essentiel. | 139€ ou 399€ selon docs. | GUIDE_DEV, ETAT_PROJET |
| 3 | **Iris Audio** | Appel audio Luna. | Redirection vers visio `/simli`. | `static/index.html` |
| 4 | **Carte "Voyager"** | "Chercher un vol". | Change juste d'onglet. | `static/index.html` |
| 5 | **Mode LUNA** | `full` = chat+voix+SMS+visio. | Visio refuse ou dépend de Tavus/Simli désactivé. | `luna_web.py`, `quota_guard.py` |
| 6 | **Visio dans la vision produit** | Retirée comme pilier. | Toujours routes, setup, pages, badges. | `FEATURE_DECISION_V1.md`, `static/simli.html` |
| 7 | **QuotaGuard** | Limite SMS, voix, visio. | Ne contrôle que les SMS. | `core/actions/quota_guard.py` |
| 8 | **Instructions médicaments** | Créer un rappel. | Interprété comme appel à `contact_unknown`. | Test `POST /api/instructions` |
| 9 | **Autour de moi** | Commerces/services proches. | N'utilise pas la géolocalisation du navigateur. | `static/index.html`, `luna_web.py` |
| 10 | **Assistant actions** | Outils IA internes. | Retourne `Not Found` sur l'URL attendue. | Test `/api/assistant/actions` |

---

## Top 10 fonctionnalités inutiles — À supprimer ou fusionner

| # | Fonctionnalité | Pourquoi elle est inutile / problématique | Recommandation |
|---|----------------|--------------------------------------------|----------------|
| 1 | **`static/dashboard.html` (Days Legacy)** | Maquette hardcodée, pas d'API, marque obsolète. | Supprimer ou marquer `demo-only`. |
| 2 | **`static/prospects.html` (Sophia)** | Données hardcodées, analyse simulée par `setTimeout`. | Supprimer ou fusionner avec admin. |
| 3 | **`static/workspace.html` / `team_workspace.html`** | Overlay "Démonstration Phase P1", participants fictifs, toasts "disponible en Phase...". | Supprimer ou fusionner avec Iris réel. |
| 4 | **`static/simli.html`** | Simli est désactivé (`_SIMLI_AVAILABLE=False`), mais la page existe. | Supprimer si Simli est abandonné. |
| 5 | **`static/world.html` complet en production** | 13 604 lignes de metaverse sans lien clair avec les 4 piliers. | Sortir du build produit ou réduire. |
| 6 | **`static/admin_world.html`** | Dashboard opérateur monde, mais le produit n'est pas un metaverse. | Supprimer ou fusionner avec admin. |
| 7 | **`core/meeting/` + MeetingBaas** | Fonctionnalité secondaire, clé optionnelle rarement configurée. | Désactiver par défaut. |
| 8 | **`integrations/recall/recall_client.py`** | Client Recall.ai jamais utilisé. | Supprimer. |
| 9 | **Badges "first_visio"** | Visio n'est plus un pilier. | Supprimer les badges visio. |
| 10 | **Théocratie (`/api/theo/*`)** | "Acces reserve" pour client, concept flou par rapport aux piliers. | Clarifier ou supprimer. |

---

## Top 10 fonctionnalités prometteuses — À renforcer

| # | Fonctionnalité | Pourquoi c'est prometteur | État actuel |
|---|----------------|---------------------------|-------------|
| 1 | **Guardian GPS + SOS** | Très cohérent avec le pilier sécurité. | Fonctionne, bien conçu. |
| 2 | **Mémoire Redis (profil, contacts, notes)** | Riche et bien structurée. | API complète, persistance OK. |
| 3 | **Système de safety / content filter** | Bien pensé, limites légales claires. | Implémenté, mais `MEDICAL_ADVICE` vide. |
| 4 | **Vault documentaire** | Coffre-fort RGPD cohérent. | Routes fonctionnelles. |
| 5 | **Form filler** | Remplissage PDF + OCR pertinent. | Routes fonctionnelles. |
| 6 | **Scheduler d'instructions** | Parser + heapq + retry, architecture solide. | Bugs d'intégration à corriger. |
| 7 | **Iris Workspace backend** | Sessions, participants, permissions. | Fonctionne, mais rendus visuels limités. |
| 8 | **Gamification Monde** | Système XP/badges/missions complet. | Fonctionne, mais déconnecté de la vision. |
| 9 | **Twilio SMS** | Intégration robuste, dry-run. | Très aboutie. |
| 10 | **Weather service** | Simple et fiable. | Fonctionne bien. |

---

## Cartographie des promesses Luna

| Promesse officielle | Où elle est faite | Réalité technique | Cohérent ? |
|---------------------|-------------------|-------------------|------------|
| Mémoire persistante Redis | README, GUIDE_DEV | Redis fallback mémoire si non configuré, API riche. | 🟡 Partiel |
| SMS aux contacts de confiance | README, prompt système | Fonctionne via Twilio, mais confirmation non persistante. | 🟡 Partiel |
| Passer des appels | README, front | Refusé par dispatcher. | ❌ |
| Visioconférences | README, front | Refusé par dispatcher, Simli désactivé, Tavus optionnel. | ❌ |
| Prendre des notes | README | Fonctionne. | ✅ |
| Actions autonomes avec confirmation | README | Proposition OK, exécution instable (bugs). | 🟡 Partiel |
| Limites légales / code civil | README | Filtre robuste, mais `MEDICAL_ADVICE` vide. | 🟡 Partiel |
| Contacts de confiance OTP | README | Contacts OK, OTP non implémenté selon ETAT_PROJET. | 🟡 Partiel |
| Luna Audio — discussion naturelle | Vision produit | Chat mort sans OpenAI, voice dépend du micro/Tavus. | ❌ |
| Iris Workspace — raisonnement collectif | Vision produit | Backend OK, front Simli confus, rendus visuels limités. | 🟡 Partiel |
| Guardian — surveillance volontaire | Vision produit | GPS/SOS fonctionne, caméra non opérationnelle en Cloud Run. | 🟡 Partiel |
| Mémoire — souvenirs & continuité | Vision produit | Profil + notes OK, continuité conversationnelle faible sans chat fiable. | 🟡 Partiel |

---

## Score de confiance utilisateur

Sur 10 : **3 / 10**

| Critère | Score | Justification |
|---------|-------|---------------|
| Installation sans friction | 1 | PV de recette bloque tout, module absent. |
| Fiabilité du chat | 2 | Mort sans clé OpenAI, erreurs génériques. |
| Clarté des offres | 1 | Prix/quotas contradictoires. |
| Respect des promesses | 2 | Appels/visio indisponibles, concierge partiel. |
| Confidentialité / consentement | 6 | Vault consent, Guardian opt-in, filtre safety. |
| UX cohérente | 3 | Pages factices, actions sans contexte. |
| Stabilité technique | 4 | Serveur démarre, Guardian/Redis OK, mais bugs critiques. |
| Transparence sur les limites | 3 | QuotaGuard incomplet, pas de sandbox. |

---

## Feuille de route

### Sprint 1 — Critique (bloquant)

- [ ] Livrer ou remplacer le module `pv_recette` ; permettre un mode "démo" fonctionnel sans PV.
- [ ] Corriger `self.sms.send()` → `send_sms` dans `core/instructions/executor.py:626`.
- [ ] Corriger `create_action_request()` → `propose_action()` dans `core/instructions/executor.py:212`.
- [ ] Corriger `/api/instructions/{id}/execute` pour passer un `ParsedInstruction`.
- [ ] Décider du statut des appels/visio : soit les implémenter, soit les retirer des promesses.
- [ ] Afficher clairement "OpenAI requis" si la clé est invalide, au lieu de "souci technique".
- [ ] Harmoniser les prix et quotas dans README, guides, état projet, code.

### Sprint 2 — Cohérence

- [ ] Retirer Tavus/Simli comme pilier si la visio n'est plus une promesse.
- [ ] Corriger la carte "Iris Audio" pour qu'elle ne redirige pas vers `/simli`.
- [ ] Corriger la carte "Voyager" pour ouvrir le formulaire de vol.
- [ ] Désactiver ou marquer comme démo `dashboard.html`, `prospects.html`, `workspace.html`.
- [ ] Faire fonctionner `QuotaGuard` sur voix et visio, ou ne plus les afficher comme limites.
- [ ] Persister les confirmations en attente (Redis).
- [ ] Rendre la boucle instructions multi-tenant.

### Sprint 3 — Optimisation

- [ ] Supprimer le code mort (`core/meeting/` si non utilisé, `integrations/recall/recall_client.py`, Simli).
- [ ] Implémenter un mode sandbox pour les réservations/paiements.
- [ ] Ajouter une suite de tests pytest.
- [ ] Unifier la navigation (onglets inline vs pages dédiées).
- [ ] Clarifier le positionnement du Monde / gamification par rapport aux 4 piliers.
- [ ] Documenter les dépendances tierces et leur état de configuration.

---

## TABLEAU OBLIGATOIRE — Audit par fonctionnalité

| Fonction | Promesse | Réalité | Cohérent ? | Criticité |
| -------- | -------- | ------- | ---------- | --------- |
| **Luna Audio — Chat texte** | Discuter naturellement avec Luna | Mort si OpenAI invalide ; message d'erreur générique | ❌ | 🔴 Critique |
| **Luna Audio — Voix** | Parler à Luna via micro | WebSocket existe, dépend du navigateur + OpenAI Realtime + micro | 🟡 | 🟠 Haute |
| **Luna Audio — Visio avatar** | Appel vidéo avec avatar | Refusé par dispatcher, Simli désactivé, Tavus optionnel | ❌ | 🔴 Critique |
| **Iris Workspace — Création session** | Lancer un workspace de raisonnement | Fonctionne (`POST /api/iris/session/create`) | ✅ | 🟢 Faible |
| **Iris Workspace — Rendu visuel** | 18 types de rendu (board, kanban, chart...) | Fallback quasi systématique sur `context_panel` | 🟡 | 🟠 Haute |
| **Iris Workspace — Multi-participants** | Inviter, révoquer, permissions | Backend OK, front limité | 🟡 | 🟡 Moyenne |
| **Guardian — Démarrage GPS** | Surveillance volontaire GPS/SOS | Fonctionne (`/api/guardian/start`) | ✅ | 🟢 Faible |
| **Guardian — Caméra / perception** | Aide contextuelle visuelle | Dépendances absentes en Cloud Run, route caméra incohérente avec la doc GPS | ❌ | 🟠 Haute |
| **Guardian — Alertes** | SMS aux contacts de confiance | Twilio OK, mais confirmation non persistante | 🟡 | 🟠 Haute |
| **Mémoire — Profil** | Profil riche du souscripteur | API complète, stockage Redis | ✅ | 🟢 Faible |
| **Mémoire — Notes** | Prendre des notes | Fonctionne | ✅ | 🟢 Faible |
| **Mémoire — Instructions** | Planifier des rapples/actions | Parser riche, scheduler OK, bugs d'exécution | 🟡 | 🔴 Critique |
| **Mémoire — Historique conversation** | Continuité conversationnelle | Conversation en mémoire, pas de contexte long fiable | 🟡 | 🟠 Haute |
| **Actions — SMS** | Envoyer un SMS avec confirmation | Fonctionne, quota OK | ✅ | 🟢 Faible |
| **Actions — Appel** | Appeler un contact | Refusé | ❌ | 🔴 Critique |
| **Actions — Visio** | Lancer une visio | Refusé | ❌ | 🔴 Critique |
| **Conciergerie — Météo** | Donner la météo | Fonctionne | ✅ | 🟢 Faible |
| **Conciergerie — Recherche web** | Rechercher sur le web | "Service non configuré" | ❌ | 🟠 Haute |
| **Conciergerie — Vols/Hôtels/Restaurants** | Rechercher et réserver | Recherche OK si API configurée, réservation directe bloquée / sandbox inexistant | 🟡 | 🟠 Haute |
| **Documents — Vault** | Coffre-fort documentaire | Fonctionne | ✅ | 🟢 Faible |
| **Documents — Form filler** | Remplir des PDF | Routes fonctionnelles | ✅ | 🟡 Moyenne |
| **Monde / Gamification** | XP, badges, missions | Fonctionne mais déconnecté des piliers | 🟡 | 🟡 Moyenne |
| **Admin — Dashboard** | Suivi exploitant/fondateur | Nécessite rôle admin/fondateur, partiellement testable | 🟡 | 🟡 Moyenne |
| **Setup — PV de recette** | Verrouiller le serveur après signature | Module absent, setup impossible | ❌ | 🔴 Critique |

---

## AUDIT SPÉCIAL — Luna Audio

### Vérifications effectuées

| Aspect | Test / Inspection | Résultat |
|--------|-------------------|----------|
| Micro | Front demande `getUserMedia` | Dépend du navigateur, pas de fallback clair |
| Démarrage voix | WebSocket `/ws/luna-voice` | Route présente, non testée en profondeur |
| Arrêt | Bouton stop dans `index.html` | Présent |
| Transcription | OpenAI Realtime | Inaccessible sans clé valide |
| Réponse | Chat texte | Mort avec erreur générique |
| Fluidité | Streaming SSE `/api/chat` | Impossible à évaluer, chat mort |
| Compréhension | Prompt système très long | Risque de "prompt overload", capacités annoncées non actionables |

### Questions posées

- **L'utilisateur comprend-il comment parler à Luna ?**  
  Oui, l'interface est claire (micro, chat texte, chips). Mais il ne comprendra pas pourquoi Luna ne répond pas.

- **Luna répond-elle naturellement ?**  
  Impossible à juger : le service est mort sans OpenAI valide. Le message d'erreur "Luna a un souci technique" brise toute crédibilité.

- **L'expérience est-elle crédible ?**  
  Non. L'expérience audio est dégradée par : (1) la dépendance totale à OpenAI, (2) le label "Iris Audio" qui ouvre une visio, (3) le manque de feedback sur les erreurs micro/réseau.

### Audit de confiance Luna Audio

| Sous-fonction | Impact confiance | Score |
|---------------|------------------|-------|
| Chat texte | Détruit la confiance (silence technique) | -2 |
| Voix | Neutre à négatif (dépend de too many factors) | -1 |
| Visio avatar | Détruit la confiance (promesse non tenue) | -2 |
| Smart suggestions | Diminue (actions sans contexte) | -1 |

---

## AUDIT SPÉCIAL — Iris Workspace

### Vérifications effectuées

| Étape du workflow | Test | Résultat |
|-------------------|------|----------|
| Brief | Création de session | ✅ Fonctionne |
| Proposition | Génération de rendu | 🟡 Fallback sur `context_panel` |
| Activation | Join / invite participants | ✅ Routes existent |
| Sources | Upload de source | Route `/api/team/upload-source` existe |
| Décision | Decision board | 🟡 Déclaré mais rarement rendu |
| Actions | Pending actions | ✅ Backend OK, front limité |
| Réserves | Objections | 🟡 Modèle existe, filtrage stub |
| Dossier final | Export | Non vérifié, Chart.js/Mermaid non intégrés selon `IRIS_WORKSPACE_VISION.md` |

### Question posée

**Peut-on réellement passer d'une idée à un livrable ?**

Réponse : **non**, pas dans l'état actuel. Le backend permet de créer une session et d'y inviter des participants, mais le rendu visuel est réduit à un `context_panel` générique. Les promesses de tableaux, graphiques, kanban, budgets, export PDF ne sont pas tenues. De plus, le front Iris réel (`simli.html`) est parasité par la confusion audio/visio (Simli/Tavus).

### Audit de confiance Iris Workspace

| Sous-fonction | Impact confiance | Score |
|---------------|------------------|-------|
| Création session | Augmente légèrement | +1 |
| Rendus visuels | Diminue (promesses non tenues) | -1 |
| Traçabilité décisions | Neutre (pas testable en l'état) | 0 |
| Export livrable | Diminue (non implémenté) | -1 |

---

## AUDIT SPÉCIAL — Guardian

### Vérifications effectuées

| Aspect | Test | Résultat |
|--------|------|----------|
| Accès caméra | `/api/guardian/frame/{session_id}` | Route présente mais incohérente avec docstring "remplace caméra" |
| Permissions | Guardian demande un contact d'urgence | ✅ Bonne pratique |
| Démarrage | `POST /api/guardian/start` | ✅ Fonctionne |
| Arrêt | `POST /api/guardian/stop/{session_id}` | ✅ Route existe |
| Surveillance GPS | Status / events / timeline | ✅ Fonctionne |
| Alertes | SOS / verify-response | ✅ Routes existent |
| Confidentialité | Opt-in, dignity_mode, night_mode | ✅ Bien pensé |

### Question posée

**Guardian fait-il réellement ce qu'il promet ?**

Réponse : **partiellement oui**. La surveillance GPS/SOS est fonctionnelle et bien conçue. Cependant, la promesse d'"aide contextuelle visuelle" (caméra) n'est pas tenue en production Cloud Run car les dépendances OpenCV/Ultralytics sont exclues. Et la route `/api/guardian/frame/{session_id}` utilise `core.perception` alors que le moteur Guardian est censé être GPS-only.

### Audit de confiance Guardian

| Sous-fonction | Impact confiance | Score |
|---------------|------------------|-------|
| Démarrage GPS/SOS | Augmente fortement | +2 |
| Géolocalisation familiale | Augmente | +1 |
| Caméra / perception | Diminue (non opérationnelle en prod) | -1 |
| RGPD / consentement | Augmente | +1 |

---

## AUDIT SPÉCIAL — Mémoire

### Vérifications effectuées

| Aspect | Test | Résultat |
|--------|------|----------|
| Rappels | `POST /api/instructions` | 🟡 Parser riche mais interprétations erronées |
| Souvenirs | Profil + notes | ✅ API complète |
| Relances | Scheduler + conditions | 🟡 Conditions `IF_WEATHER`/`IF_TIME_PASSED` simplifiées |
| Historique | Conversations | 🟡 En mémoire volatile, continuité faible |
| Mémoire utilisateur | Profil riche 40+ champs | ✅ Bien structurée |

### Question posée

**La mémoire est-elle contextuelle ou générique ?**

Réponse : **générique**. Le profil souscripteur est très riche, mais le chat ne l'exploite pas de manière fiable (chat mort). Les instructions planifiées sont contextuelles (heure, conditions) mais leur exécution est buguée. Les smart suggestions proposent des rappels médicaux génériques sans prescription connue.

### Audit de confiance Mémoire

| Sous-fonction | Impact confiance | Score |
|---------------|------------------|-------|
| Profil riche | Augmente | +1 |
| Notes | Augmente | +1 |
| Instructions planifiées | Diminue (bugs + interprétations erronées) | -1 |
| Continuité conversationnelle | Diminue (chat mort) | -2 |

---

## AUDIT SPÉCIAL — Actions contextuelles

### Méthode

Analyse des smart chips, cartes concierge, suggestions de saisie, modèles rapides et cartes proactives dans `static/index.html`, croisée avec les endpoints backend.

### Résultats

| Bouton / Action | Contexte déclencheur | Pertinence | Mène à quelque chose ? | Problème |
|-----------------|----------------------|------------|------------------------|----------|
| **"Créer un rappel médicaments à 20h"** | Onboarding / modèle rapide | ❌ Aucun médicament mentionné | ✅ Endpoint existe | Exemple parfait d'action sans contexte |
| **"Appelle ma famille"** | Smart chip compagnon | ⚠️ Aucun contact "famille" vérifié | ✅ `/api/chat` puis voice | Risque d'échec ou d'appel générique |
| **"Envoie un SMS à"** | Suggestion de saisie | ⚠️ Aucun destinataire | ✅ Formulaire demande contact | Phrase incomplète envoyée brute |
| **"Appelle"** | Suggestion de saisie | ❌ Aucun contact | ✅ Modal contact | Phrase incomplète |
| **"Iris Audio"** | Carte + menu flottant | ❌ Promet audio, renvoie visio | ✅ `/simli` | Incohérence audio vs visio |
| **"Voyager" / "Chercher un vol"** | Carte proactive 12h-18h | ⚠️ Heure seule | ❌ Change juste d'onglet | Promesse non tenue |
| **"Autour de moi"** | Carte concierge | ⚠️ N'utilise pas la géoloc navigateur | ✅ Recherche par ville profil | "Près de chez moi" non garanti |
| **"Réserver maintenant" (vol/hôtel)** | Résultat concierge | ⚠️ Profil incomplet | ⚠️ Nécessite Duffel + sandbox | Risque de vrai paiement sans sandbox |
| **"Alerte urgence"** | Carte concierge | ✅ Contexte explicite | ✅ SMS contacts | Pertinent et fonctionnel |
| **"Prendre une note"** | Carte + suggestion | ✅ Contexte explicite | ✅ `/api/notes` | Pertinent |

### Synthèse

Beaucoup de boutons sont affichés **parce qu'ils existent**, pas parce qu'ils sont pertinents dans le contexte. Les exemples les plus problématiques :

- Rappel médical générique sans prescription.
- Appel/SMS/visio sans contact sélectionné.
- "Iris Audio" qui n'est pas de l'audio.
- "Voyager" qui n'ouvre pas le formulaire de vol.

Ces actions non contextuelles **détruisent la confiance** : elles créent de l'espoir puis de la frustration.

---

## AUDIT DE VISION PRODUIT — Écran par écran

| Écran / Page | Pourquoi il existe ? | Verdict |
|--------------|----------------------|---------|
| `static/index.html` | PWA principale : chat, concierge, profil, guardian, monde. | ✅ Justifié mais surchargé. |
| `static/guardian.html` | Page dédiée Guardian (mobile). | ✅ Justifiée, redondante avec l'onglet. |
| `static/salon.html` | Activités sociales (chat, cinéma, karaoké). | 🟡 Confusion avec "Activités" dans l'index. |
| `static/documents.html` | Assistant documents/rappels. | ✅ Justifiée, mais redondante avec Vault/Form filler. |
| `static/formulaires.html` | Remplissage PDF. | ✅ Justifiée. |
| `static/vault.html` | Coffre-fort RGPD. | ✅ Justifiée. |
| `static/setup.html` | Wizard exploitant 10 étapes. | ✅ Justifiée, mais module backend absent. |
| `static/admin.html` | Dashboard admin. | ✅ Justifiée. |
| `static/dashboard.html` | Days Legacy — patrimoine. | ❌ Marque obsolète, données hardcodées. **Supprimer.** |
| `static/prospects.html` | Prospect Navigator. | ❌ Maquette statique. **Supprimer.** |
| `static/workspace.html` / `team_workspace.html` | Salle stratégique Iris. | ❌ Maquette de démo. **Fusionner avec Iris réel.** |
| `static/world.html` | Metaverse gamifié. | 🟡 Travaillé mais déconnecté des 4 piliers. **Sortir du build prod.** |
| `static/admin_world.html` | Admin monde. | ❌ Dépend de world.html. **Supprimer.** |
| `static/simli.html` | Visio avatar Simli. | ❌ Simli désactivé. **Supprimer.** |
| `static/pitch.html` / `pitch_live.html` | Présentation commerciale. | 🟡 Outils internes, pas pour l'utilisateur final. |
| `static/nda.html` | Signature NDA. | 🟡 Outil commercial. |
| `static/download.html` | Téléchargement APK. | ✅ Justifiée. |
| `static/demo.html` | Accueil réunion démo. | 🟡 Outil commercial. |
| `static/fondateur.html` | Superadmin. | ✅ Justifiée. |
| `static/exploitant.html` | Dashboard opérateur. | ✅ Justifiée. |

### Recommandations de vision produit

1. **Supprimer** : `dashboard.html`, `prospects.html`, `workspace.html`, `team_workspace.html`, `simli.html`, `admin_world.html`.
2. **Fusionner** : `guardian.html` dans l'onglet Guardian de `index.html`.
3. **Sortir du build production** : `world.html` (garder en démo interne).
4. **Clarifier** : le lien entre `documents.html`, `vault.html`, `formulaires.html`.

---

## QUESTION FINALE OBLIGATOIRE

> Si je découvrais Luna aujourd'hui : qu'est-ce qui me ferait confiance ? Qu'est-ce qui me ferait douter ? Qu'est-ce qui me ferait quitter l'application ?

### Ce qui me ferait confiance

- **Guardian** : le démarrage GPS/SOS est simple, le consentement est clair, le besoin d'un contact d'urgence rassure.
- **Le profil riche** : on sent que Luna peut "apprendre à me connaître".
- **L'interface est soignée** : dark mode, animations, ton chaleureux.
- **Le Vault / Form filler** : promesse concrète et routes fonctionnelles.

### Ce qui me ferait douter

- **L'application ne fait rien au premier lancement** : un PV de recette bloque tout. J'ai l'impression d'avoir acheté un appareil sans mode d'emploi.
- **Luna ne répond pas** : "Luna a un souci technique" au lieu d'une vraie réponse.
- **Les prix et quotas changent selon l'écran** : je ne sais pas ce que je paie.
- **Des boutons mènent à des fonctionnalités "bientôt disponibles"** : c'est du vaporware.
- **"Iris Audio" m'envoie vers de la vidéo** : je me demande si les créateurs savent ce qu'ils vendent.

### Ce qui me ferait quitter l'application

- **Le chat ne marche pas** : si le cœur du produit est mort, tout le reste ne sert à rien.
- **Je ne peux pas tester sans signer un PV** : trop d'engagement avant la valeur.
- **On me propose des rappels médicaux sans que je l'aie demandé** : c'est intrusif et peu fiable.
- **L'impression globale de produit inachevé** : trop de maquettes, trop de promesses, pas assez de fiabilité.

**En toute honnêteté** : je quitterais l'application dans les 5 premières minutes. Luna a l'air d'un projet très ambitieux et techniquement dense, mais pas d'un produit fini. La frustration l'emporterait sur l'enthousiasme.

---

## ANNEXE — Détails techniques des tests

### Environnement de test

- OS : Linux
- Python : 3.11.2
- Démarrage : `python3 luna_web.py` en mode `LITE`, `FOUNDATION_TEST_MODE=true`, clé OpenAI factice.
- Redis : fallback mémoire (pas de serveur Redis externe).

### Endpoints testés avec succès

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/quota`
- `POST /api/guardian/start`, `GET /api/guardian/sessions`, `GET /api/guardian/status/{id}`
- `POST /api/iris/session/create`, `GET /api/iris/session/{id}/status`
- `GET /api/notes`, `POST /api/notes`
- `POST /api/instructions`
- `GET /api/documents`, `GET /api/documents/v2/dashboard`
- `GET /api/vault/docs`, `GET /api/vault/consent`
- `GET /api/form-filler/profile`, `GET /api/form-filler/history`
- `POST /api/concierge/action` (météo OK, search_web KO)
- `GET /api/world/player`, `GET /api/world/badges`, `GET /api/world/missions`

### Endpoints testés avec échec notable

- `POST /api/chat` → "Luna a un souci technique" (OpenAI 401)
- `POST /api/assistant/analyze` → OpenAI 401 exposé
- `POST /api/concierge/action` action `search_web` → "Service non configuré"
- `POST /api/instructions` texte médicament → interprété comme `call_contact`
- `GET /api/setup/status` → "Module pv_recette non disponible"
- `GET /api/theo/hours` → "Acces reserve"

---

## ANNEXE — Incohérences documentaires

| Document | Essentiel SMS | Essentiel Voix | Essentiel Visio | Prix Essentiel |
|----------|---------------|----------------|-----------------|----------------|
| `README.md` | 50 | 30 min | 60 min | Non précisé |
| `GUIDE_DEV.md` | 25 | 40 min | 12 min | 79€ |
| `GUIDE_OPERATIONNEL.md` | 25 | 40 min | 12 min | 79€ |
| `ETAT_PROJET_LUNA_V3.md` | 20 | Non précisé | 15 min | 139€ |
| `core/actions/quota_guard.py` | 25 | 40 min | 12 min | Non précisé |
| `LUNA_SYSTEM_PROMPT` (dans `luna_web.py`) | 25 | 40 min | 12 min | 79€ |

**Recommandation immédiate :** désigner une source de vérité unique (probablement le code + le prompt système) et mettre à jour tous les documents.

---

*Fin du rapport.*
