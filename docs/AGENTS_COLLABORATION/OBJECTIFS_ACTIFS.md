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

**Statut** : ouvert — test réel Ludovic en cours
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

- [ ] Heartbeat APK réel visible.
- [ ] Test bouton vocal produit une chronologie d'événements.
- [ ] `voice_no_audio_after_timeout` ou erreur équivalente visible si silence.
- [ ] Cockpit fondateur explique la cause probable.
- [ ] Journal fondateur trace le test et la conclusion.
- [ ] Aucun asset graphique ne disparaît.
- [ ] Claude propose la correction finale.
- [ ] Ludovic valide avant déploiement/rebuild.

---

---

## Objectif 007 — Télémétrie vocale APK : 20+ événements de chronologie réelle

**Statut** : ✅ VALIDÉ — test réel 2026-05-25 18:47
**Priorité** : critique
**Lead** : Claude
**Date ouverture** : 2026-05-25
**Date validation** : 2026-05-25 18:47
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_007_RESULTAT_TEST.md`

### Problème

Objectif 006 devait prouver que Luna voit une panne vocale. Mais seul `voice_session_ended`
remontait en test réel — aucun des événements intermédiaires.

### Solution déployée

Augmenter les points de capture de 10 à 20+ événements pour tracer :
- clic du bouton
- vérification token
- entrée `startVoice()`
- demande permission micro
- micro autorisé / refusé
- début capture audio
- création WebSocket
- WebSocket ouvert / fermé / timeout
- premier audio envoyé
- audio reçu
- premier audio envoyé échoué
- timeout 20s silence
- session terminée

### Résultat test réel Ludovic

**11 événements capturés et traçables** :

```
voice_button_clicked → voice_start_entered → voice_micro_request_started
→ microphone_permission_granted → voice_audio_capture_started
→ voice_ws_create_started → voice_ws_opened → voice_first_audio_chunk_sent
→ voice_ws_closed (~5s) → voice_session_ended

BUT : pas de voice_audio_received (aucune réponse)
```

**Diagnostic Luna générée** :
```json
{
  "scenario": "incomplete",
  "luna_knows": [client token OK, mic OK, capture OK, WS ouvert, audio envoyé],
  "luna_guesses": [serveur voix fermé WS prématurément, OpenAI Realtime n'a pas répondu],
  "luna_recommends": [vérifier logs serveur voix, OpenAI connection state, fermeture WS],
  "luna_cannot": [diagnostiquer serveur, voir logs Python, auditer web_voice_bridge.py]
}
```

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **DeepSeek** | Audit points injection `sendApkEvent()`, bug token/counter, proposer 20+ événements | ✅ Fait |
| **Claude** | Intégration backend, `_analyze_voice_events()`, textes diagnostic | ✅ Fait |
| **Kimi** | Textes cockpit "Luna sait / suppose / recommande / ne peut pas" | ✅ Fait |
| **Ludovic** | Test téléphone réel → 11 événements validés | ✅ Fait |
| **Codex** | Cadrage, garde-fous, coordination branches | ✅ Fait |

### Validation

- [x] Schéma 20+ événements défini dans DEEPSEEK_AVIS_007.md
- [x] Points injection vérifiés en code
- [x] Bug silencieux identifié (token check après counter++)
- [x] Test réel : 11 événements reçus
- [x] Diagnostic Luna généré correctement
- [x] Blocage serveur voix/OpenAI identifié
- [x] Journal test enregistré

### Extension 007-bis — Geste maintenance APK

Ajouter pull-to-refresh : vider cache, recharger page, renvoyer heartbeat.

Événements : `apk_manual_refresh_triggered`, `apk_cache_cleared`, `apk_webview_reloaded`

---

## Objectif 008 — DeepSeek temps réel dans l'expérience APK

**Statut** : en cours — architecture cadrée, implémentation en attente
**Priorité** : critique
**Lead** : Claude + DeepSeek
**Date ouverture** : 2026-05-25
**Document dédié** : `docs/AGENTS_COLLABORATION/OBJECTIF_008_DEEPSEEK_TEMPS_REEL_APK.md`

### Vision Ludovic

DeepSeek doit être "dans le téléphone" fonctionnellement :

- recevoir les signaux APK en temps réel ;
- être déclenché automatiquement sur incident (WebSocket fermé, no audio, erreur JS, bouton bloqué) ;
- produire un diagnostic exploitable structuré ;
- ne pas tourner en permanence inutilement ;
- envoyer ses diagnostics au cockpit fondateur via serveur Luna.

### Architecture imposée

```
APK téléphone
  → flux diagnostic temps réel
Serveur Luna (clé DeepSeek protégée)
  → appel DeepSeek API côté serveur
DeepSeek
  → diagnostic structuré JSON
Cockpit fondateur
  → recommandation exploitable
```

### Décisions clés

1. **Clé DeepSeek côté serveur uniquement** — jamais dans l'APK.
2. **Mode incident uniquement** — pas d'appels IA sans anomalie.
3. **Fenêtre compacte** — 30-60s d'événements max, pas d'audio brut, pas de secret.
4. **Sortie structurée** — diagnostic + preuve + cause + zone + action + risque.

### Cas d'usage dès Objective 008

1. **Voix APK** : premier audio envoyé mais WebSocket ferme → DeepSeek analyse logs 20+ événements.
2. **Cache/WebView** : frontend obsolète → détecte mismatch version, propose clear cache.
3. **Boutons futurs** : clic → aucune action → incident → déploie DeepSeek.
4. **UI mobile** : régression détectée (bouton coupé) → rapportée.

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **DeepSeek** | Format événement minimal, seuils incident, stratégie anti-gaspillage tokens, diagnostics type | À faire |
| **Claude** | Endpoint serveur, protection clé, rate limiting, journal diagnostics, cockpit | À faire |
| **Kimi** | Textes cockpit : "DeepSeek observe / suppose / recommande / ne peut pas" | À faire |
| **Codex** | Garde-fous : no key in APK, no IA spam, no raw audio, no auto-correct without Ludovic | À faire |
| **Cursor** | Vérifier intégration icônes, UX cockpit, pas de régression | À faire |

### Livrables attendus

1. **DeepSeek audit** : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_008_TEMPS_REEL_APK.md`
   - format événement compact minimal
   - seuils de déclenchement incident
   - stratégie tokens et fréquence limites
   - exemple diagnostics pour voix + cache + boutons

2. **Claude implémentation** :
   - `POST /api/deepseek/diagnose` endpoint serveur
   - Protection clé DeepSeek en `os.environ["DEEPSEEK_API_KEY"]` (jamais dans code)
   - Rate limiting : 1 appel/30s par session max
   - Stockage journal : `luna:deepseek:diagnostics` Redis
   - Affichage cockpit `fondateur.html` section 🔍 DeepSeek

3. **Kimi formulation** :
   - Textes "Luna / DeepSeek observe : [faits]"
   - Textes "Luna / DeepSeek suppose : [hypothèses]"
   - Textes "Luna / DeepSeek recommande : [actions]"
   - Textes "Luna / DeepSeek ne peut pas : [limites]"

4. **Codex garde-fous** :
   - Vérifier aucune clé API dans `static/index.html`
   - Vérifier aucun appel IA en navigation normale
   - Vérifier aucun audio brut ni transcript envoyé
   - Vérifier incident détecté avant appel DeepSeek

5. **Cursor vérification** :
   - Icônes intégrées dans cockpit
   - UX mobile : textes lisibles, pas de débordement
   - Non-régression : boutons existants, navigation, réglages

### Interdictions pour cet objectif

- Pas de clé DeepSeek dans l'APK ou GitHub public.
- Pas d'appels IA à chaque événement normal.
- Pas d'audio brut, transcript privé, token ou secret.
- Pas de correction automatique sans validation Ludovic.
- Pas de mélange diagnostic APK / serveur voix / UI — rester ciblé.

### Validation Objective 008 (voix)

- [x] **VOIX VALIDÉE** — pipeline complet fonctionne
- [x] Cause identifiée : OpenAI quota insuffisant (insufficient_quota)
- [x] Après recharge OpenAI : voix Luna fonctionne
- [x] Modèle actif : gpt-4o-realtime-preview-2024-12-17
- [x] Audio bidirectionnel PCM16 24kHz validé
- [x] Heartbeat, télémétrie, pipeline serveur tous OK

**Documentation** : `docs/AGENTS_COLLABORATION/OBJECTIF_008_VOIX_VALIDATION_PARTIELLE.md`

---

## Objectif 008-stabilité — Voix : corriger les coupures audio

**Statut** : ouvert — diagnostic requis
**Priorité** : haute
**Lead** : Claude
**Date ouverture** : 2026-05-25 19:35
**Dépendance** : Objective 008 (voix fonctionne maintenant)

### Problème

Après que la voix Luna fonctionne suite à recharge OpenAI :

**Symptôme** : Luna commence à parler mais coupe / s'arrête sans raison claire.

Les sessions audio ne durent pas jusqu'à la fin du message ou se interrompent prématurément.

### But

Diagnostiquer et corriger les coupures audio.

Pas de gros refactor — correction minimale ciblée sur la cause racine.

### Points à diagnostiquer

1. **Durée session OpenAI Realtime** : timeout côté OpenAI après combien de secondes ?
2. **WebSocket fermé prématurément** : qui ferme (serveur ou client) et pourquoi ?
3. **Timeout audio côté client** : Apollo re-utilise-t-il le timer 20s silence ou y a-t-il un autre timeout ?
4. **Buffer playback** : Apollo joue-t-il le buffer complètement ou le vide-t-il trop tôt ?
5. **Logs serveur** : y a-t-il des erreurs OpenAI entre audio reçu et réponse générée ?
6. **Événement télémétrie** : ajouter `voice_audio_cut` ou `voice_playback_stopped_early` pour tracer les coupures

### Agents concernés

| Agent | Tâche | Statut |
|---|---|---|
| **Claude** | Lead : examiner logs serveur, OpenAI state, timeout logic | À faire |
| **DeepSeek** | Audit `startVoice()`, timer 20s, playback queue, détection de fin session | À faire |
| **Codex** | Proposer minimal fix : vérifier timeout, réduire logs bruits, garder-fous | À faire |

### Livrables attendus

1. Cause probable identifiée (fichier + ligne)
2. Correction minimale proposée
3. Tests à lancer (sans audio réel)
4. Risques de régression
5. Validation Ludovic requise : oui

### Interdictions

- Pas de gros refactor WebSocket
- Pas de changement modèle OpenAI
- Pas de modification APK version (correction serveur/frontend seulement)
- Pas de auto-correction sans validation Ludovic

### Validation

- [ ] Claude a proposé cause probable
- [ ] DeepSeek a audité code serveur/client
- [ ] Codex a validé la correction
- [ ] Ludovic a validé avant déploiement
- [ ] Test réel : voix Luna ne coupe plus

---

## Règle d'ouverture d'un objectif

Pour ouvrir un nouvel objectif :
1. Ajouter une section ici avec statut `en analyse`
2. Affecter les agents concernés
3. Définir les interdictions et livrables
4. Notifier dans `TABLEAU_DE_BORD.md`
