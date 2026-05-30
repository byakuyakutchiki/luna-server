# Claude — Plan intégrateur Objectif 014

Agent : Claude  
Tâche : TASK-014-CLAUDE-NO-CODE-BEFORE-MATRIX  
Date : 2026-05-30  
Statut : livrable — en attente audits DeepSeek + Kimi avant tout code

---

## Ce que j'ai retenu de la vision Iris (Codex + Ludovic)

Iris n'est pas un chatbot vidéo avec une barre de saisie.  
Iris est une **présence assistante** : voir, entendre, comprendre, rassurer, noter, protéger.  
L'UI doit laisser la vidéo respirer. Aucun élément permanent ne doit couvrir le flux.

---

## Erreur commise Objectif 013

J'ai ajouté la barre texte Iris sans passer par la matrice. J'ai déclaré des correctifs "résolus" sans preuve terrain. Je déploierai seulement après preuve + validation Ludovic.

**Correction déjà dans le code** : barre supprimée, commit `4e1d2ba` pushé, **non déployé** — déploiement attend validation Ludovic.

---

## État factuel des 10 targets — sans suppositions

| Target | Ce qui est dans le code | Ce qui manque |
|---|---|---|
| **Saluer Ludovic** | `firstMessage` utilise `subscriber_name` depuis `profile.first_name` | Vérifier que la DB a `first_name="Ludovic"` + **preuve terrain** |
| **Voix féminine FR** | `ELEVENLABS_VOICE_ID=6BlZrFdruL4hpXFHmHUC` (Alice) + `elevenlabsLanguageCode=fr` configurés | **DeepSeek doit vérifier** que ces vars sont bien dans Cloud Run et qu'ElevenLabs répond |
| **Comprendre la voix** | Simli fait STT → gpt-4o-mini nativement | **Preuve terrain** : pas encore testée sur phrase réelle |
| **Voir la présence / "tu me vois ?"** | Capture canvas 12s → `/api/visio/perception` → injection `[Système vision]` | **Preuve terrain** : pas encore testée sur scène réelle |
| **Voir un geste simple** | Même pipeline vision (320x240, 12s) | Latence 12s = pas temps réel. Kimi doit tester |
| **Résumer l'échange** | `/api/visio/notes` existe, transcript local dans `_visioTranscript` | **Preuve terrain** : pas encore testée |
| **Météo / info simple** | Tools `get_weather`, `get_news`, `search_web` branchés | **Preuve terrain** : non testée en visio |
| **Créer un rappel** | `_tool_create_instruction` existe | **Preuve terrain** : non testée |
| **Refuser SMS/appel/email** | Guard `_ACTION_TOOLS` présent, demande confirmation | **Preuve terrain** : non testée en visio |
| **Canal texte discret** | Barre retirée. Pas d'alternative encore | **Kimi doit proposer** : bouton discret ? commande vocale "je veux écrire" ? panneau temporaire ? |

---

## Ce que j'attends avant tout code nouveau

### DeepSeek → TASK-014-DEEPSEEK-VISIO-CAPABILITY-GAP
1. Lister les env vars actuelles de Cloud Run luna-beta (sans secrets dans GitHub)
2. Confirmer que `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` sont bien là
3. Expliquer pourquoi la voix était masculine en prod (Cartesia absent → ElevenLabs → mais lequel ?)
4. Vérifier que `/api/visio/perception` reçoit bien des frames et que l'injection dans Simli fonctionne
5. Tester `GET /api/admin/objectives` pour voir l'état réel des services

### Kimi → TASK-014-KIMI-REAL-VISIO-UX
1. Tester la visio réelle sur mobile (maintenant sans la barre)
2. Verdict : est-ce qu'Iris ressemble à une secrétaire crédible ?
3. Proposition concrète pour le canal texte secours (format discret, non intrusif)
4. Dire si l'immersion vidéo est respectée

---

## Ce que je ferai seulement après ces audits

| Action | Condition |
|---|---|
| Déployer le revert barre | Validation Ludovic |
| Corriger les env Cloud Run si gap trouvé | Audit DeepSeek + validation Ludovic |
| Implémenter canal texte discret | Proposition UX Kimi validée par Ludovic |
| Améliorer vision caméra (fréquence injection) | Audit DeepSeek + test Kimi + validation Ludovic |

---

## Ce que je ne ferai jamais sans preuve

- Déclarer "la voix fonctionne" sans que Ludovic l'entende en prod
- Déclarer "la vision caméra marche" sans test terrain décrit par Kimi
- Ajouter une UI visible sans matrice validée
- Déployer niveau 2/3 sans validation Ludovic
