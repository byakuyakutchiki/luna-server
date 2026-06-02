# Objectifs actifs Luna

Ce fichier est la source de vérité pour savoir ce sur quoi travaille chaque agent.
Mise à jour obligatoire avant toute modification majeure.

---

## Objectif 001 — Monitoring vocal réel

**Statut** : assigné — analyse en cours
**Priorité** : haute
**Lead** : Claude
**Date ouverture** : 2026-05-25
**Date assignation** : 2026-05-25

### Problème

Le bouton vocal peut ne pas produire de voix et s'arrêter après ~20 secondes.
Le monitoring `/api/admin/objectives` → `voix` vérifie les endpoints techniques
mais ne simule pas l'expérience utilisateur réelle (flux audio reçu ou non).

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **DeepSeek** | Analyser `web_voice_bridge.py`, `realtime_bridge.py`, `startVoice()` — voir `DEEPSEEK_AVIS.md` | **En cours** |
| **Codex** | Vérifier commits voix, fix AudioWorklet, timeout, tests — voir `CODEX_AVIS.md` | **En cours** |
| **Kimi** | Audit documentaire — promesse utilisateur vs réalité — voir `KIMI_AVIS.md` | **En cours** |
| **Cursor** | Vérifier intégration locale, cohérence fichiers VS Code | À faire |
| **Claude** | Synthèse finale, correction, déploiement | En attente des avis |

### Fichiers concernés (hypothèse)

- `luna_web.py` → `_check_objective_voix()`, `/ws/luna-voice`, `/api/voice/*`
- `static/index.html` → `startVoice()`, AudioWorklet vs ScriptProcessorNode
- `integrations/web_voice_bridge.py` ou `realtime_bridge.py`

### Interdictions pour cet objectif

- Pas de déploiement Cloud Run sans validation Claude + Ludovic
- Pas de suppression de modules voix existants
- Pas de refactor massif — correction minimale ciblée
- Pas d'appels vocaux réels pour tester (simulation seulement)

### Livrables attendus de chaque agent

1. Cause probable identifiée (fichier + ligne)
2. Correction minimale proposée
3. Tests à lancer pour valider sans action réelle
4. Risques de régression identifiés
5. Validation Ludovic requise ? oui / non

### Validation

- [ ] DeepSeek a posté son avis dans `agents/DEEPSEEK_AVIS.md`
- [ ] Codex a posté son avis dans `agents/CODEX_AVIS.md`
- [ ] Kimi a posté son avis dans `agents/KIMI_AVIS.md`
- [ ] Claude a synthétisé dans `DECISION_FINALE.md`
- [ ] Ludovic a validé
- [ ] Déployé sur Cloud Run

---

## Objectif 002 — Audit fonctionnel APK onglet par onglet

**Statut** : en attente (après objectif 001)
**Priorité** : normale
**Lead** : Claude
**Date ouverture** : 2026-05-25

### Problème

L'APK v2.8 est déployée mais les boutons de chaque onglet n'ont pas été testés
sur appareil réel depuis les dernières corrections (voix, monitoring, branding).

### Périmètre

Tester dans l'ordre : Instructions → Services → Documents → Formulaires → Cartes → Monde → Profil → Réglages

### Statut

- [ ] Instructions
- [ ] Services / Concierge
- [ ] Documents
- [ ] Formulaires
- [ ] Cartes
- [ ] Monde
- [ ] Profil
- [ ] Réglages

---

## Objectif 003 — Cerveau APK / télémétrie appareil réel

**Statut** : idée validée par Ludovic — cadrage multi-agents demandé
**Priorité** : haute
**Lead** : Claude
**Date ouverture** : 2026-05-25
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_003_CERVEAU_APK.md`

### Vision

Cloud Run sait ce qu'il sert. L'APK sait ce que l'utilisateur vit.
Luna doit comparer les deux pour détecter les décalages entre GitHub, Docker,
Cloud Run et l'expérience réelle sur le téléphone.

### Problème

Aujourd'hui, une modification peut être correcte dans GitHub ou Cloud Run,
mais l'APK réelle peut rester silencieuse, obsolète, bloquée ou décalée
pendant plusieurs minutes sans que les agents le sachent.

Le téléphone de Ludovic doit devenir une sonde vivante : version APK, URL active,
WebView, permission micro, WebSocket voix, audio reçu, erreurs JS et dernier
contact serveur doivent remonter au cerveau central.

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Architecture finale, arbitrage sécurité, décision d'implémentation | À cadrer |
| **DeepSeek** | Prototype local VS Code : schéma heartbeat + analyse Android/WebView | À cadrer |
| **Kimi** | Audit documentaire : promesse utilisateur vs observabilité APK réelle | À cadrer |
| **Codex** | Cadrage GitHub, PR, tests automatisables, garde-fous de branche | En cours |
| **Cursor** | Vérifier cohérence locale VS Code / fichiers Android / frontend | À cadrer |

### Livrables attendus

1. Schéma minimal d'événement APK → serveur.
2. Proposition d'endpoint serveur, sans secret production dans l'APK.
3. Liste des signaux critiques : version, build frontend, URL Cloud Run, écran, voix, WebSocket, audio, erreurs.
4. Stratégie d'affichage dans `/api/admin/objectives` ou dashboard admin.
5. Risques confidentialité / batterie / spam réseau / sécurité.
6. Plan de rollback et désactivation.

### Interdictions pour cet objectif

- Pas de déploiement Cloud Run sans validation Ludovic.
- Pas de collecte de données personnelles fines sans consentement explicite.
- Pas de position exacte, audio brut, transcript privé ou secret dans la télémétrie.
- Pas de capacité de déploiement ou d'administration Cloud depuis l'APK.
- Pas de gros refactor Android ou backend : commencer par heartbeat minimal.

### Validation

- [ ] Claude a validé l'architecture.
- [ ] DeepSeek a proposé un schéma technique.
- [ ] Kimi a audité la promesse documentaire.
- [ ] Codex a préparé la PR de cadrage.
- [ ] Ludovic a validé le périmètre.
- [ ] Implémentation sur branche dédiée.
- [ ] Test sur téléphone fondateur.

---

## Objectif 004 — API fondateur : diagnostic APK + journal des actions

**Statut** : ouvert — cadrage multi-agents demandé après déploiement Objectif 003 Phase 1
**Priorité** : haute
**Lead** : Claude
**Date ouverture** : 2026-05-25
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_004_API_FONDATEUR_DIAGNOSTIC.md`

### Vision

Objectif 003 observe le réel. Objectif 004 doit interpréter ce réel,
proposer une décision lisible à Ludovic, et garder une trace de ce qui a été
proposé, validé ou exécuté.

### Problème

Le heartbeat APK centralise l'état réel du téléphone, mais une donnée brute ne
suffit pas. Luna doit transformer ce signal en diagnostic fondateur :

- est-ce normal ?
- est-ce un décalage APK / Cloud Run ?
- quelle est la cause probable ?
- quelle action est recommandée ?
- cette action est-elle automatique, proposée, ou interdite sans validation ?
- quelle trace garde-t-on ?

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Architecture finale, API fondateur, arbitrage actions autorisées | À cadrer |
| **DeepSeek** | Proposer moteur de diagnostic + schéma actions/journal | À cadrer |
| **Kimi** | Audit UX fondateur : textes lisibles, traçabilité, validation | À cadrer |
| **Codex** | Cadrage GitHub, garde-fous, tests de diagnostics sans production | En cours |
| **Cursor** | Vérifier cohérence frontend `fondateur.html` / endpoints / états | À cadrer |

### Livrables attendus

1. Fonction d'analyse serveur type `_analyze_apk_state()`.
2. Schéma de diagnostic : status, cause probable, action recommandée, niveau de validation.
3. Journal d'actions fondateur : proposé / validé / exécuté / résultat.
4. Liste des actions sûres, actions proposées, actions interdites sans Ludovic.
5. Intégration UI dans `fondateur.html` ou dashboard admin.
6. Tests sans appel Cloud Run destructif ni modification production automatique.

### Interdictions pour cet objectif

- Pas de déploiement automatique depuis l'API fondateur.
- Pas de rebuild APK automatique sans validation Ludovic.
- Pas de modification `.env`, Cloud Run, Redis critique ou secrets sans validation.
- Pas d'action corrective invisible : toute proposition ou action doit être journalisée.
- Pas d'auto-healing complet dans cette phase : seulement diagnostic + recommandations + traces.

### Validation

- [x] Claude a validé le modèle d'actions et implémenté Phase 1 (commit b9a42e8)
- [x] DeepSeek a proposé le moteur de diagnostic
- [x] Kimi a validé les textes fondateur
- [x] Codex a préparé la PR de cadrage
- [x] Ludovic a validé les 3 décisions (waiting_first_contact, journal 30j, niveau 1 sans confirmation)
- [x] Implémenté et déployé sur Cloud Run (révision luna-beta-00433-zxg)
- [ ] Test sur heartbeat réel APK — **en attente rebuild APK**

---

## Objectif 005 — Événements voix APK : prouver ce qui se passe quand Ludovic appuie sur le bouton vocal

**Statut** : cadré — en attente validation heartbeat réel (objectif 004)
**Priorité** : haute
**Lead** : Claude
**Date ouverture** : 2026-05-25
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_005_EVENTS_VOIX_APK.md`
**Dépendance** : Objectif 003/004 — le premier heartbeat réel doit avoir été reçu

### Problème

Le heartbeat sait que le téléphone respire. Mais quand Ludovic appuie sur le bouton vocal et n'entend rien après 20 secondes, le cockpit ne peut pas encore savoir à quelle étape ça bloque.

### Vision

Chronologie réelle visible dans le cockpit fondateur :
```
voice_button_clicked → microphone_permission_granted → voice_ws_opened
→ voice_audio_sent → voice_no_audio_after_timeout → voice_ws_closed
```

Affichage fondateur :
```
Voix APK — Problème important
Luna sait : bouton appuyé, micro OK, WebSocket ouvert — aucun audio reçu après 20s.
Luna suppose : la réponse OpenAI ou le playback WebView ne revient pas jusqu'au téléphone.
Luna recommande : vérifier la chaîne WebSocket → OpenAI → audio client.
```

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Schéma final, `POST /api/apk/event`, diagnostic voix, `fondateur.html` | À faire |
| **DeepSeek** | Points d'injection dans `startVoice()`, timer 20s, cas précis silence | À solliciter |
| **Kimi** | Textes cockpit fondateur : sait / suppose / recommande / ne peut pas | À solliciter |
| **Cursor** | Cohérence UI, vérifier que les événements JS ne cassent pas `startVoice()` | À solliciter |
| **Codex** | Cadrage PR, garde-fous, découpage | À solliciter |

### Livrable principal

```
POST /api/apk/event          — reçoit les événements voix depuis le JS
GET /api/admin/apk-diagnosis — champ voice_events ajouté
fondateur.html               — section voix avec chronologie
```

### Interdictions pour cet objectif

- Pas d'audio brut, pas de transcript
- Pas de géolocalisation
- Pas de correction automatique de la voix
- Pas de déploiement sans validation Ludovic
- Pas de rebuild APK pour cette phase (événements JS uniquement dans `static/index.html`)
- Pas de gros refactor de `startVoice()` — injection minimale

### Validation

- [x] Schéma événements validé par Claude
- [x] Claude a implémenté `POST /api/apk/event` (commit 7c31a2a)
- [x] Claude a mis à jour `_analyze_voice_events()` avec textes Kimi
- [x] Claude a mis à jour `fondateur.html` section 🎙️ Voix APK
- [x] Kimi a rédigé les textes fondateur (intégrés, branche `kimi/objectif-005-events-voix`)
- [ ] DeepSeek doit refaire audit sur `origin/main` (voir `CLAUDE_TO_DEEPSEEK_005_UPDATE.md`)
- [ ] Cursor doit vérifier la cohérence UI et non-régression `startVoice()`
- [ ] **Heartbeat réel APK reçu** ← BLOQUANT — rebuild APK nécessaire
- [ ] **Ludovic valide avant déploiement** ← BLOQUANT
- [ ] Test réel : bouton vocal → `voice_no_audio_after_timeout` visible dans cockpit

---

## Objectif 006 — Validation du cerveau Luna sur panne vocale réelle

**Statut** : partiellement validé — heartbeat OK, télémétrie voix insuffisante → Objectif 007  
**Priorité** : critique  
**Lead final** : Claude  
**Date ouverture** : 2026-05-25  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_006_VALIDATION_CERVEAU_VOIX.md`

### Problème

Ludovic teste l'APK réelle. Le bouton vocal peut toujours rester silencieux après
15 à 20 secondes. Maintenant que le heartbeat, le diagnostic APK et les événements
voix existent, il faut vérifier si Luna détecte réellement cette panne et l'explique
dans le cockpit fondateur.

### But

Valider la boucle :

```
test réel Ludovic → événements APK → diagnostic serveur → cockpit fondateur
→ recommandation → journal → correction validée
```

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Ludovic** | Reproduire la panne sur téléphone et valider le diagnostic affiché | En cours |
| **Claude** | Lead final : synthèse, correction minimale, déploiement si validé | En attente des avis |
| **Codex** | Cadrage GitHub, rôles, garde-fous, critères de validation | En cours |
| **DeepSeek** | Audit `startVoice()`, `sendApkEvent()`, timer silence, WebSocket, erreurs JS | À solliciter |
| **Kimi** | Audit humain des textes cockpit et du journal fondateur | À solliciter |
| **Cursor** | Vérification UI mobile, assets, non-régression frontend | À solliciter |

### Validation

- [x] Heartbeat APK réel visible. ← validé (révision luna-beta-00438-f4j)
- [ ] Test bouton vocal produit une chronologie d'événements. → Objectif 007
- [ ] `voice_no_audio_after_timeout` ou erreur équivalente visible si silence. → Objectif 007
- [ ] Cockpit fondateur explique la cause probable.
- [ ] Journal fondateur trace le test et la conclusion.
- [x] Aucun asset graphique ne disparaît. ← validé commit a3545a1
- [ ] Claude propose la correction finale.
- [ ] Ludovic valide avant déploiement/rebuild.

---

## Objectif 007 — Télémétrie vocale précise APK

**Statut** : ouvert — implémentation en cours  
**Priorité** : critique  
**Lead** : Claude  
**Date ouverture** : 2026-05-25  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_007_TELEMETRIE_VOIX_APK.md`

### Problème

Heartbeat OK. Mais seulement `voice_session_ended` arrive dans Redis.
Deux bugs identifiés par Claude :
1. `session_ts = 0` pour `voice_button_clicked` → groupé dans une session fantôme
2. `_apkEventCount >= 10` trop bas pour 21 événements

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Fix session_ts + plafond + implémentation 21 événements | En cours |
| **DeepSeek** | Audit startVoice(), session_ts, chemins alternatifs, fetch/WebSocket Android | À solliciter |
| **Kimi** | Textes cockpit pour 8 scénarios voix | À solliciter |
| **Cursor** | UI mobile, non-régression startVoice() | À solliciter |
| **Codex** | Critères validation, garde-fous, synthèse Claude | À solliciter |
| **Ludovic** | Test réel après déploiement | En attente déploiement |

### Validation

- [x] Claude a identifié les causes (session_ts=0 + plafond 10→30)
- [x] DeepSeek — `agents/DEEPSEEK_AVIS_007.md` (branche ds/objectif-007)
- [x] Kimi — `agents/KIMI_AVIS_007.md` (branche kimi/objectif-007)
- [x] Codex — `agents/CODEX_AVIS_007.md` (2 branches codex/007)
- [x] Claude a implémenté et déployé (commit 01ac7a5, révision 00439-7v9)
- [x] **Ludovic a validé sur téléphone réel** — 11 événements reçus, chronologie complète
- [x] Chronologie complète visible dans le cockpit fondateur

**OBJECTIF 007 VALIDÉ** — 2026-05-25

Résultat test réel : clic → token → micro → capture → WS ouvert → premier audio envoyé
→ WS fermé (5s) → session terminée. Blocage confirmé : côté serveur / OpenAI Realtime.
Note : branches DeepSeek/Kimi NE PAS merger directement (divergences — utiliser docs uniquement).

---

## Objectif 008 — Correction voix OpenAI Realtime : modèle + bridge

**Statut** : ✅ VALIDÉ — voix Luna entendue sur téléphone réel Ludovic (2026-05-25)
**Priorité** : critique  
**Lead** : Claude  
**Date ouverture** : 2026-05-25  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_008_CORRECTION_VOIX_OPENAI.md`
**Document DeepSeek APK** : `docs/AGENTS_COLLABORATION/OBJECTIF_008_DEEPSEEK_TEMPS_REEL_APK.md`

### Cause racine identifiée

Modèle `gpt-4o-realtime-preview-2024-12-17` (daté déc 2024) → OpenAI ferme le WS
pendant `_configure_session()` (~2s après connexion). Logs confirment :
`WARNING: WebVoice: OpenAI WS closed during send`.

### Périmètre autorisé par Ludovic

- Lecture logs / Cloud Run / code serveur : **autorisé**
- Correction `OPENAI_REALTIME_MODEL` : **attendre validation Ludovic**
- Correction bridge (session.created + logs) : **attendre validation Ludovic**
- Déploiement : **interdit sans validation Ludovic**
- Modification client APK pour la voix : **interdit**
- Pull-to-refresh APK : **accepté comme amélioration séparée** (à cadrer après 008)

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Investigation lecture seule : logs, web_voice_bridge.py, modèle OpenAI | En cours |
| **DeepSeek** | IA désignée dans l'expérience APK : diagnostic temps réel, cache, WebView, boutons | À solliciter |
| **Kimi** | Textes cockpit (icônes 007 + scénarios OpenAI error) | À solliciter |
| **Codex** | Garde-fous, règle no-merge branches divergentes | À solliciter |
| **Cursor** | Intégration icônes Kimi dans fondateur.html | À solliciter |
| **Ludovic** | Validation avant tout déploiement | En attente |

### Validation

- [x] Cause racine identifiée par Claude (logs Cloud Run)
- [ ] DeepSeek temps réel APK — `agents/DEEPSEEK_AVIS_008_TEMPS_REEL_APK.md`
- [ ] DeepSeek — `agents/DEEPSEEK_AVIS_008.md`
- [ ] Kimi — `agents/KIMI_AVIS_008.md`
- [ ] Codex — `agents/CODEX_AVIS_008.md`
- [ ] Cursor — `agents/CURSOR_AVIS_008.md`
- [x] **Ludovic a validé — voix entendue sur téléphone réel**
- [x] Voix Luna entendue sur téléphone réel Ludovic ✅

### Reste à améliorer (post-008)
- Luna s'arrête parfois de parler seule (coupure VAD ou session) — à investiguer objectif 009

### Exigence Ludovic — DeepSeek dans l'expérience téléphone

Pour les prochains tests boutons/onglets, DeepSeek doit être l'IA désignée pour
voir ce qui se passe dans l'APK en temps réel.

Architecture : APK → serveur Luna → DeepSeek API côté serveur → cockpit/journal.

Interdit : clé DeepSeek dans l'APK, audio brut, transcript privé, appel IA permanent
sans anomalie.

---

## Règle d'ouverture d'un objectif

Pour ouvrir un nouvel objectif :
1. Ajouter une section ici avec statut `en analyse`
2. Affecter les agents concernés
3. Définir les interdictions et livrables
4. Notifier dans `TABLEAU_DE_BORD.md`

---

## Note transversale — Sentry

Sentry est une source d'observation du cerveau Luna.

Toute erreur utile observée dans Sentry doit être résumée dans GitHub sous forme
filtrée/anonymisée, notamment dans `RAPPORT_SENTRY_OBJECTIF_008.md`.

Règle : aucun secret, token, cookie, clé API, email privé, audio brut ou transcript
privé ne doit être copié dans GitHub.

---

## Objectif 014 — Recadrage visio réelle / rôles agents / preuve terrain

**Statut** : ouvert — critique  
**Priorité** : très haute  
**Lead coordination** : Codex  
**Date ouverture** : 2026-05-30  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_014_RECADRAGE_VISIO_REELLE.md`

### Problème

Objectif 013 a dérivé : des changements visibles ont été codés sans preuve terrain suffisante ni validation produit claire. Ludovic observe en production :

- une grosse barre de chat Iris non conforme à la vocation visio ;
- ElevenLabs non fonctionnel en production ;
- vision caméra non prouvée ;
- reconnaissance de Ludovic non prouvée ;
- objectifs secrétaire non réalisés.

### Règle

Avant toute nouvelle correction visible : matrice objectif réel -> preuve terrain -> risque -> décision.

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Kimi** | Oeil terrain / UX réelle / qualité visuelle / test rendu publié | À faire |
| **Codex** | Vision produit, target de chaque bouton/workflow, matrice de validation | Fait |
| **DeepSeek** | Audit gap technique voix/vision/STT/tool calls/env Cloud Run | À faire |
| **Claude** | Plan d'intégration final seulement après matrice + validation | À faire |
| **Ludovic** | Validation niveau 2/3 : UI visible, voix, avatar, vision, déploiement | Selon besoin |

### Validation

- [x] Codex a créé le cadrage Objectif 014.
- [ ] Kimi a regardé/testé le rendu réel visio publié.
- [ ] DeepSeek a identifié les gaps techniques exacts.
- [ ] Claude a proposé un plan sans nouveau code visible non validé.
- [ ] Barre texte Iris traitée : retirée, masquée ou redesign discret validé.
- [ ] Voix production vérifiée.
- [ ] Vision caméra vérifiée.
- [ ] Ludovic ne reçoit plus de "teste c'est bon" sans preuve préalable.

---

## Objectif 010 — Historique intelligent des conversations + mémoire Luna

**Statut** : ouvert — cadrage multi-agents  
**Priorité** : haute  
**Lead final** : Claude  
**Date ouverture** : 2026-05-25  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_010_HISTORIQUE_MEMOIRE_CHAT.md`

### Problème

Le chat Luna manque d'organisation par conversations. Le fil peut devenir trop long.
Luna doit aussi conserver une mémoire utile de son architecture, des décisions et de
son identité, sans l'exposer inutilement.

Un bug UI mobile est aussi à traiter séparément : le bouton `Connexion` /
`Déconnexion` est coupé sur téléphone.

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Backend conversations, stockage, endpoints, intégration finale | À solliciter |
| **DeepSeek** | Audit frontend chat, menu trois traits, localStorage/WebView/cache | À solliciter |
| **Kimi** | UX conversationnelle, titrage automatique, mémoire non intrusive | À solliciter |
| **Cursor** | UI mobile, menu conversations, correction bouton coupé | À solliciter |
| **Codex** | Cadrage, garde-fous mémoire, séparation bug UI / architecture | En cours |
| **Ludovic** | Validation produit sur téléphone | En attente |

### Validation

- [ ] Avis Claude rendu.
- [ ] Avis DeepSeek rendu.
- [ ] Avis Kimi rendu.
- [ ] Avis Cursor rendu.
- [ ] Avis Codex rendu.
- [ ] Ludovic valide l'architecture.
- [ ] Implémentation sur branche dédiée.
- [ ] Test téléphone validé.

---

## Objectif 013 — Visio Luna réelle / Simli / voix / vision caméra

**Statut** : ouvert — audit multi-agents  
**Priorité** : haute  
**Lead final** : Claude  
**Date ouverture** : 2026-05-28  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_013_VISIO_LUNA_SIMLI.md`

### Problème

Ludovic a testé la visio sur l'APK réelle. Le bouton Visio lance Simli, l'avatar apparaît, mais :
1. L'avatar n'est pas Luna.
2. La voix est masculine (avatar féminin).
3. Luna ne répond pas aux messages texte.
4. Luna ne semble pas analyser la caméra.

### Architecture

Flux visio = Tavus (premium) → Simli (fallback) → Daily.js iframe (WebRTC).  
LLM côté Simli = gpt-4o-mini. TTS = Cartesia ou ElevenLabs.  
Vision caméra = capture canvas toutes les 12s → POST /api/visio/perception → injection texte.

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Kimi** | UX visio réelle : tester le parcours, frictions UI, cohérence avatar/voix | À solliciter |
| **DeepSeek** | Audit technique : flux Simli/Tavus, config voix/avatar, vision, hangup | À solliciter |
| **Codex** | Synthèse, priorisation, décisions Ludovic | À solliciter |
| **Claude** | Intégration finale après validation | En attente |
| **Ludovic** | Validation avatar, voix, input texte, vision | En attente |

### Interdictions

- Pas de déploiement sans validation.
- Pas de consommation inutile des 996 min Simli restantes.
- Pas de remplacement avatar/voix sans validation Ludovic.
- Pas de sessions longues en boucle.

### Validation

- [ ] Kimi a testé l'UX visio réelle.
- [ ] DeepSeek a audité le flux technique.
- [ ] Codex a structuré la synthèse.
- [ ] Ludovic a validé le plan d'action.
- [ ] Implémentation sur branche dédiée.
- [ ] Test téléphone validé.

---

## Objectif 011 - Audit complet onglet Services / Conciergerie

**Statut** : ouvert - audit multi-agents uniquement  
**Priorite** : tres haute  
**Lead final** : Claude  
**Date ouverture** : 2026-05-26  
**Document dedie** : `docs/AGENTS_COLLABORATION/OBJECTIF_011_AUDIT_SERVICES.md`

### Probleme

L'onglet Services contient de nombreuses fonctions : recherche, voyage, meteo,
actualites, SMS, email, appel, visio, alerte urgence, rappels, notes, documents,
contacts, formulaires, stats, missions, badges et amis en ligne.

Chaque service doit etre audite avant correction : but utilisateur, code appele,
dependances externes, resultat attendu, message d'erreur, risque, garde-fou et
remontee cockpit/cerveau.

### Regle Ludovic

Audit et observations avant action. Aucune refonte, aucun test sensible, aucun
deploiement production sans validation.

### Agents concernes

| Agent | Tache | Statut |
|---|---|---|
| **Claude** | Lead final, cartographie frontend/backend, synthese avant code | A solliciter |
| **DeepSeek** | Audit technique cartes -> handlers -> endpoint -> tools | A solliciter |
| **Kimi** | UX, promesse utilisateur, textes de reussite/echec | A solliciter |
| **Cursor** | Audit UI mobile Services, cartes, modales, resultats | A solliciter |
| **Codex** | Cadrage, garde-fous, priorites de test non destructif | En cours |
| **Ludovic** | Validation produit et tests telephone | En attente |

### Actions sensibles interdites sans validation

- SMS reel.
- Email reel.
- Appel telephone reel.
- Alerte urgence.
- Paiement.
- Reservation.
- Invitation visio a un tiers.

### Validation

- [ ] Avis Claude rendu.
- [ ] Avis DeepSeek rendu.
- [ ] Avis Kimi rendu.
- [ ] Avis Cursor rendu.
- [ ] Avis Codex rendu.
- [ ] Tous les services inventories.
- [ ] Services classes par risque.
- [ ] Ludovic valide le premier lot a corriger.

---

## Objectif 012 - Canal de decision agents Luna

**Statut** : ouvert - V1 GitHub documentaire
**Priorite** : haute
**Lead coordination** : Codex
**Date ouverture** : 2026-05-28
**Document dedie** : `docs/AGENTS_COLLABORATION/OBJECTIF_012_CANAL_DECISION_AGENTS.md`

### Probleme

Ludovic ne doit pas servir de relais manuel entre les IA par copier-coller.
Les agents doivent pouvoir converger dans GitHub, preparer les decisions, et ne
remonter au fondateur que les arbitrages importants.

### Regle Ludovic

Luna doit toujours aller vers plus beau, plus fluide et plus fonctionnel.
Aucune regression graphique. Aucun changement majeur sans validation fondateur.

### Agents concernes

| Agent | Tache | Statut |
|---|---|---|
| **Kimi** | Referent UX, graphisme, textes, detection regressions visuelles | A solliciter |
| **Codex** | Synthese, tri, garde-fous, decisions structurees | En cours |
| **DeepSeek** | Audit technique, faisabilite, risques code | A solliciter |
| **Claude** | Integration finale et deploiement apres validation si impact majeur | A solliciter |
| **Ludovic** | Validation niveau 2/3 et arbitrage fondateur | Selon besoin |

### Validation

- [x] Structure V1 creee dans `docs/AGENTS_COLLABORATION`.
- [x] Regles legeres ajoutees.
- [x] Decisions en attente / validees separees.
- [x] Canal agent court ajoute.
- [ ] Kimi poste son premier avis UX sur le canal.
- [ ] DeepSeek poste son premier avis technique sur le canal.
- [ ] Claude confirme le mode integration finale.

---

## Objectif 013 — Voix féminine FR + Identité Ludovic + Vision caméra (Simli/ElevenLabs)

**Statut** : ouvert — architecture analysée par Claude  
**Priorité** : haute  
**Lead technique** : Claude  
**Date ouverture** : 2026-05-29  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_013_VISIO_LUNA_SIMLI.md`

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Architecture + intégration ELEVENLABS_VOICE_ID | ✅ Architecture livrée |
| **Kimi** | Choix voix FR féminine + wording assistante visio | ✅ Voix Camille + wording Iris livrés |
| **DeepSeek** | Audit flux + risques coût + test plan économe | ✅ Audits techniques livrés |
| **Ludovic** | Valider la voix choisie avant déploiement | En attente |

### Interdictions absolues

- ZERO SMS / appel Twilio pendant cet objectif
- Ne jamais committer ELEVENLABS_API_KEY
- Test Simli < 30 secondes par session
- Déploiement Cloud Run interdit sans validation Ludovic

### Validation

- [x] Claude a analysé l'architecture et livré OBJECTIF_013_VISIO_LUNA_SIMLI.md
- [x] Kimi a recommandé une voix (Camille — Z9ZHGvFZ90R0h0x1prsJ) + wording Iris
- [x] DeepSeek a audité les flux (DEEPSEEK_SIMLI_FLOW_AUDIT.md)
- [ ] Ludovic a validé la voix (test terrain 30s)
- [ ] ELEVENLABS_API_KEY configuré sur Cloud Run
- [ ] Déploiement Cloud Run validé par Ludovic

---

## Objectif 019 — Luna compagnon / Iris opératrice / panneau d'action

**Statut** : ouvert — cadrage produit actif
**Priorité** : haute
**Lead coordination** : Codex
**Date ouverture** : 2026-06-02
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_019_LUNA_IRIS_ACTION_PANEL.md`

### Décision Ludovic

Luna et Iris ne doivent plus être mélangées.

- **Luna** : compagnon conversationnel, conseil, discussion, vision, accompagnement.
- **Iris** : secrétaire opérationnelle, technique et administrative, capable de produire et d'exécuter avec confirmation.

Luna doit savoir dire que la demande relève d'Iris quand il faut rédiger, classer, préparer un document, faire une action ou gérer un workflow.

### État technique actuel

Le parcours Iris actif est désormais **Iris Audio** :

- `/simli` bascule en mode `AUDIO-FIRST`.
- Le flux vidéo Simli/Daily est désactivé dans le parcours actif.
- `/ws/iris-voice` utilise OpenAI Realtime.
- Les anciens endpoints `/api/visio/transcribe`, `/api/visio/chat`, `/api/visio/tts` restent comme historique/secours.

### Prochaine cible produit

Créer un panneau d'action **Iris Workbench** :

- brouillon de note ;
- brouillon de courrier ;
- tableau/checklist ;
- statut visible : analyse, rédaction, prêt, validation requise ;
- actions : modifier, télécharger, sauvegarder, annuler ;
- aucune action sensible sans confirmation explicite.

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Codex** | Coordination, séparation Luna/Iris, synthèse avant code visible | En cours |
| **Claude** | Stabiliser `/ws/iris-voice`, préparer implémentation Workbench après validation | À solliciter |
| **Kimi** | UX premium du panneau Iris Workbench, identité Luna/Iris | À solliciter |
| **DeepSeek** | Audit outils documents/actions/garde-fous et risques | À solliciter |
| **Ludovic** | Validation panneau visible et branchement Documents | En attente |

### Interdictions

- Pas de SMS, appel, email, paiement, réservation sans confirmation explicite.
- Pas de déploiement visible majeur sans validation Ludovic.
- Pas de mélange Luna/Iris dans les textes.
- Pas de retour à l'ancien avatar/visio sans décision niveau 2.
- Pas de stockage document ou export sensible sans garde-fou.

### Validation

- [x] Codex a posé le cadrage Objectif 019.
- [ ] Claude confirme l'état déployé exact d'Iris Audio.
- [ ] Kimi propose l'UX Workbench V1.
- [ ] DeepSeek cartographie les outils documents/actions utilisables.
- [ ] Ludovic valide le périmètre visible V1.
- [ ] Implémentation sur patch minimal.
- [ ] Test réel navigateur + APK.
