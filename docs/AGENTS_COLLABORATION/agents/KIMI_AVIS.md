# Avis Kimi

Agent : Kimi Code CLI (kimi-k2.6)
Outil : terminal — `kimi` dans le répertoire du repo
Rôle : Audit documentaire + analyse code, shell, recherche web

---

## MISSION ACTIVE — Objectif 001 voix

**Assigné le** : 2026-05-25
**Branche** : `kimi/objectif-001-voix` (pour toute modification code ou doc)
**Guide** : lire `docs/AGENTS_COLLABORATION/GUIDE_KIMI_CODE.md` avant de commencer

### Contexte

Luna propose une fonctionnalité vocale : l'utilisateur appuie sur un bouton, parle à Luna,
Luna répond avec une voix féminine (OpenAI Realtime, voix `coral`).

**Problème observé** : bouton vocal silencieux, arrêt après ~20 secondes dans l'APK.

DeepSeek et Codex analysent le code technique.
**Ta tâche est différente** : vérifier que ce qui est documenté correspond à ce qui est promis à l'utilisateur, et identifier les incohérences entre la documentation et la réalité.

### Mission 1 — Audit documentaire (spécialité Kimi)

Comparer ce qui est promis à l'utilisateur avec ce qui est réellement implémenté.

### Mission 2 — Analyse code (Kimi Code CLI)

Lancer dans le terminal depuis le repo :
```bash
grep -n "LunaApp\|ScriptProcessor\|AudioWorklet\|coral\|alloy" static/index.html
grep -n "voice_name\|timeout\|session_duration\|max_duration" integrations/openai/web_voice_bridge.py
grep -n "luna-voice\|_check_objective_voix" luna_web.py | head -20
```

Puis lire directement :
- `integrations/openai/web_voice_bridge.py` — voix par défaut, timeout, gestion fin session
- `static/index.html` — fonction `startVoice()`, détection WebView

Poster les résultats dans la section "Analyse code" ci-dessous.

---

### Documents à lire

| Document | Chemin | Ce qu'il contient |
|---|---|---|
| Prompt monitoring voix | `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` | Objectif utilisateur voix, checks attendus |
| Capacités Luna complètes | `docs/LUNA_CAPACITES_COMPLETES.md` | Ce que Luna est censée faire |
| Actions déléguées | `docs/LUNA_ACTIONS_DELEGUEES.md` | Ce que Luna fait en autonomie |
| Cahier des charges monitoring | `docs/CAHIER_DES_CHARGES_MONITORING.md` | Objectifs de monitoring |
| État actuel agents | `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md` | Situation réelle production |

### Questions précises à répondre

**1. Promesse utilisateur**
- Que promet la documentation à l'utilisateur sur la voix ?
- La voix est-elle présentée comme féminine / temps réel / toujours disponible ?
- Y a-t-il une mention du comportement en cas d'échec ?

**2. Cohérence documentation → monitoring**
- Le monitoring voix (`_check_objective_voix`) vérifie-t-il ce qui est promis ?
- Y a-t-il des checks documentés qui ne sont pas implémentés ?
- Y a-t-il des checks implémentés qui ne correspondent à aucune promesse documentée ?

**3. Cohérence documentation → comportement réel**
- La documentation mentionne-t-elle un timeout de session ?
- La documentation mentionne-t-elle un comportement spécifique dans l'APK Android ?
- Y a-t-il une contradiction entre ce qui est écrit et le comportement observé (silencieux, 20s) ?

**4. Lacunes documentaires**
- Manque-t-il un document pour décrire le comportement vocal attendu en cas d'erreur ?
- La procédure de fallback (voix échoue → que se passe-t-il ?) est-elle documentée ?

### Ce que tu dois poster ici

Remplir les sections ci-dessous.

#### Promesse documentée à l'utilisateur

Ce que la doc dit sur la voix :

Voix féminine mentionnée : oui / non (source : )
Temps réel mentionné : oui / non (source : )
Comportement en cas d'échec documenté : oui / non

#### Cohérence documentation ↔ monitoring

Checks documentés non implémentés :

Checks implémentés sans base documentaire :

#### Cohérence documentation ↔ bug observé

Contradiction identifiée :

Timeout mentionné dans la doc : oui / non (valeur : )

#### Lacunes documentaires

Ce qui manque :

#### Analyse code (Kimi Code CLI)

Résultat grep `LunaApp` dans index.html :

Voix par défaut dans web_voice_bridge.py :

Timeout session (valeur réelle) :

Gestion fin de session (reconnexion ou pas) :

#### Verdict Kimi

La documentation couvre-t-elle correctement la fonctionnalité vocale ? oui / non

Recommandation (document à créer / à corriger) :

Problème code identifié (fichier + ligne) :

---

## MISSION ACTIVE — Audit Guardian Caméra & Reconnaissance

**Assigné le** : 2026-06-17
**Objet** : Répondre à la demande de Ludovic : la caméra Guardian ne fonctionne pas et la reconnaissance délire (faux positifs).
**Fichier d'audit complet** : `docs/AUDIT_GUARDIAN_CAMERA_RECONNAISSANCE.md`

### Résumé des constats

| Thème | Verdict | Gravité |
|---|---|---|
| Caméra active (flux + envoi frames) | Partiellement fonctionnel | Moyenne |
| Reconnaissance visuelle (OpenAI Vision) | Fonctionnelle mais bruyante | Élevée |
| Faux positifs caméra | Fréquents par conception | Élevée |
| Check-in automatique caméra | Trop agressif | Critique |
| Intégration caméra ↔ moteur Guardian | Pas d'atténuation GPS | Élevée |
| Tests caméra / perception | Aucun test automatisé | Élevée |

### Problèmes critiques identifiés

1. **Check-in automatique toutes les 60 secondes** avec alerte SMS après **30 secondes** de non-réponse (`static/guardian.html:1288-1333`). Cela viole la Policy V2 (10 minutes avant escalade) et garantit des faux positifs.
2. **Reconnaissance reposant uniquement sur `gpt-4o-mini`** sans filtre de confiance, sans validation multi-frame, sans contexte GPS.
3. **Pas de fusion caméra ↔ GPS** : la caméra ne corrige pas les alertes GPS et vice-versa.
4. **Aucun test automatisé** pour la perception.
5. **Signal `speed_anomaly` GPS** toujours présent comme proxy de chute, alors que la Policy V2 dit de le désactiver.

### Recommandations prioritaires

1. Désactiver le check-in automatique par défaut (ou le mettre derrière un flag).
2. Supprimer/neutraliser `speed_anomaly` dans `core/guardian/engine.py:490-492`.
3. Vérifier `video.readyState` avant d'envoyer une frame.
4. Ajouter un test `/api/perception/status` avant activation caméra.
5. Renforcer `SceneAnalyzer` avec confiance minimale et 2 frames consécutives.
6. Fusionner les signaux caméra et GPS (atténuation si personne vivante visible).
7. Écrire des tests mockés pour la perception.

### Verdict Kimi

La fonction caméra Guardian n'est **pas prête pour la production** en l'état. Le risque de faux positifs SMS est très élevé, notamment à cause du check-in automatique. La reconnaissance visuelle a besoin d'un calibrage et d'une fusion avec le GPS avant d'être fiable.

---

### Interdictions

- Ne pas pusher sur `main` directement
- Ne pas lancer `bash deploy.sh` ou commandes Cloud Run
- Ne pas lire ni modifier `.env` ou clés API
- Modifications code → branche `kimi/*` + PR
- Modifications doc → peut commiter sur `main` directement
