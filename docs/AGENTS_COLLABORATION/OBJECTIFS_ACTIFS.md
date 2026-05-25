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

## Règle d'ouverture d'un objectif

Pour ouvrir un nouvel objectif :
1. Ajouter une section ici avec statut `en analyse`
2. Affecter les agents concernés
3. Définir les interdictions et livrables
4. Notifier dans `TABLEAU_DE_BORD.md`
