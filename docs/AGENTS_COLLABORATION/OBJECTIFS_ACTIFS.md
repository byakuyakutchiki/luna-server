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

- [ ] Claude a validé le modèle d'actions.
- [ ] DeepSeek a proposé le moteur de diagnostic.
- [ ] Kimi a validé les textes fondateur.
- [ ] Codex a préparé la PR de cadrage.
- [ ] Ludovic a validé ce qui peut être automatique ou non.
- [ ] Implémentation sur branche dédiée.
- [ ] Test sur heartbeat réel APK.

---

## Règle d'ouverture d'un objectif

Pour ouvrir un nouvel objectif :
1. Ajouter une section ici avec statut `en analyse`
2. Affecter les agents concernés
3. Définir les interdictions et livrables
4. Notifier dans `TABLEAU_DE_BORD.md`
