# Décision finale

Ce fichier centralise les décisions techniques validées par Ludovic.

---

## Décision #1 — Monitoring 11 objectifs

**Date** : 2026-05-25
**Sujet** : Monitoring réel Luna — `GET /api/admin/objectives`

**Décision** : Implémenté. 11 objectifs actifs dans `luna_web.py`.

**État** : ✅ Déployé sur Cloud Run, validé.

---

## Décision #2 — Voix féminine coral + fix APK AudioWorklet

**Date** : 2026-05-25
**Sujet** : Voix OpenAI Realtime dans APK Android

**Problème** : AudioWorklet via `createObjectURL(blob)` échoue silencieusement dans WebView Android. Voix masculine `alloy` utilisée par défaut au lieu de `coral`.

**Solution retenue** :
- Détection `LunaApp/` dans User-Agent (défini par `MainActivity.java`)
- Si WebView : utiliser `ScriptProcessorNode` directement (pas AudioWorklet)
- `OPENAI_VOICE_NAME=coral` dans `.env` et Cloud Run

**État** : ✅ Déployé sur Cloud Run — à valider sur appareil réel.

---

## Décision #3 — Branding IA masqué

**Date** : 2026-05-25
**Sujet** : Mentions Claude/Anthropic supprimées de l'interface

**Décision** : Aucun badge/label IA visible dans l'interface utilisateur final. Le choix du moteur IA reste confidentiel.

**État** : ✅ Appliqué dans `index.html`.

---

## Décision #4 — Workflow multi-agents

**Date** : 2026-05-25
**Sujet** : Coordination Claude / Codex / Cursor / Kimi / DeepSeek

**Règles validées** :
- Claude = codeur final, décision technique finale
- Codex = corrections ciblées, commits, PR, tests
- Autres = lecture, analyse, propositions
- Aucun push direct en production sans revue Claude + validation Ludovic
- Ce répertoire `docs/AGENTS_COLLABORATION/` = espace de coordination partagé

**État** : ✅ Structure créée, commitée sur `main`.

---

## Prochaine décision à prendre

**Sujet** : Audit fonctionnel onglets APK — tester chaque bouton sur appareil réel
**Statut** : En attente de validation Ludovic

- [ ] Validé par Ludovic
- [ ] À revoir
- [ ] Refusé

Commentaire Ludovic :
