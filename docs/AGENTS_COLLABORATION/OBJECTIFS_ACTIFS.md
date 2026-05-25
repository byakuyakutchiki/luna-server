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

**Statut** : ouvert — diagnostic lecture seule en cours  
**Priorité** : critique  
**Lead** : Claude  
**Date ouverture** : 2026-05-25  
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_008_CORRECTION_VOIX_OPENAI.md`

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
| **DeepSeek** | Audit `web_voice_bridge.py` — session.created, correction minimale bridge | À solliciter |
| **Kimi** | Textes cockpit (icônes 007 + scénarios OpenAI error) | À solliciter |
| **Codex** | Garde-fous, règle no-merge branches divergentes | À solliciter |
| **Cursor** | Intégration icônes Kimi dans fondateur.html | À solliciter |
| **Ludovic** | Validation avant tout déploiement | En attente |

### Validation

- [x] Cause racine identifiée par Claude (logs Cloud Run)
- [ ] DeepSeek — `agents/DEEPSEEK_AVIS_008.md`
- [ ] Kimi — `agents/KIMI_AVIS_008.md`
- [ ] Codex — `agents/CODEX_AVIS_008.md`
- [ ] Cursor — `agents/CURSOR_AVIS_008.md`
- [ ] **Ludovic valide le correctif avant déploiement**
- [ ] Voix Luna entendue sur téléphone réel

---

## Règle d'ouverture d'un objectif

Pour ouvrir un nouvel objectif :
1. Ajouter une section ici avec statut `en analyse`
2. Affecter les agents concernés
3. Définir les interdictions et livrables
4. Notifier dans `TABLEAU_DE_BORD.md`
