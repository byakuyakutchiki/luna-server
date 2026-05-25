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

Voix féminine mentionnée : **oui** (source : `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` § "La voix par défaut demandée par le fondateur doit être féminine. Le fallback recommandé est `coral` ou une autre voix féminine explicitement configurée via `OPENAI_VOICE_NAME`" ; `docs/CAHIER_DES_CHARGES_MONITORING.md` §12 "TTS OpenAI configuré avec voix féminine par défaut : `coral` ou autre voix féminine définie par `OPENAI_VOICE_NAME`")

Temps réel mentionné : **oui** (source : `docs/CAHIER_DES_CHARGES_MONITORING.md` §12 "conversation orale avec Luna via WebSocket OpenAI Realtime" ; `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` "Voix doit permettre à l'utilisateur de parler naturellement à Luna" / "réponse vocale naturelle")

Comportement en cas d'échec documenté : **oui** (source : `docs/CAHIER_DES_CHARGES_MONITORING.md` §12 "Si le micro, OpenAI, quota ou WebSocket bloque : message utilisateur clair, pas de silence" ; `docs/PROMPT_CLAUDE_MONITORING_VOIX.md` "jamais de silence si le micro, OpenAI, quota, WebSocket ou navigateur bloque" / "message compréhensible si permission micro refusée" / "erreur loggée/Sentry si le bouton échoue")

#### Cohérence documentation ↔ monitoring

Checks documentés non implémentés :
- **Feedback utilisateur au clic** : le monitoring vérifie que `startVoice` et `/ws/luna-voice` existent dans le HTML (ligne 3106), mais ne teste pas que le clic produit un retour visuel en < 1s comme promis.
- **Permission micro refusée** : documentée comme obligatoire ("message compréhensible si permission micro refusée") mais aucun check monitoring ne simule ou ne vérifie ce parcours.
- **Voix réellement féminine à l'exécution** : le monitoring vérifie la présence de la chaîne `coral` dans le code source (`index.html`), mais ne vérifie pas la valeur réelle de `OPENAI_VOICE_NAME` au runtime ni la configuration côté serveur (`web_voice_bridge.py` ligne 34 utilise `os.getenv("OPENAI_VOICE_NAME", "coral")` — le monitoring ne vérifie pas que cette variable env est bien définie ou que sa valeur est féminine).
- **Quota/budget vérifié avant démarrage** : documenté dans le cahier des charges §12, mais `_check_objective_voix` ne vérifie pas le quota voix avant de déclarer le service OK.
- **Gestion fin de session / timeout** : le cahier des charges mentionne des durées et un avertissement, mais le monitoring ne vérifie pas que le timer de 300s ou l'inactivité de 300s fonctionnent.
- **Auto-reconnexion x3** : documentée mais pas testée par le monitoring.

Checks implémentés sans base documentaire :
- **Détection `coral` dans le HTML** (`_check_objective_voix` ligne ~3100) : le check cherche `"coral"` dans `static/index.html`, mais ce n'est pas dans le cahier des charges. La source de vérité devrait être la valeur runtime `OPENAI_VOICE_NAME` ou la configuration `web_voice_bridge.py`, pas le HTML statique.
- **`ws_voice_ok = True` hardcodé** (ligne 3083) : le monitoring déclare `/ws/luna-voice monté` sans vérification dynamique réelle de la route. Ce n'est pas un check documenté dans le cahier des charges, c'est une assertion aveugle.

#### Cohérence documentation ↔ bug observé

Contradiction identifiée :
- **"Feedback immédiat en moins d'une seconde"** vs **"bouton vocal silencieux"** : la documentation (`PROMPT_CLAUDE_MONITORING_VOIX.md`) exige "retour immédiat en moins d'une seconde", "jamais de silence". Le bug observé est exactement l'opposé : silence au clic, puis arrêt après ~20s.
- **"Jamais de silence"** vs comportement réel : le code `startVoice()` dans `index.html` (ligne 7558+) affiche bien des états (`_setStatus`) mais en WebView APK (`LunaApp/`), le fallback `ScriptProcessorNode` est utilisé à la place d'`AudioWorklet`. Le `console.warn` (ligne 7603) n'est pas visible par l'utilisateur — donc s'il y a un problème dans ce fallback, l'utilisateur n'a aucun feedback.
- **Arrêt après ~20 secondes** : le `ping_timeout` OpenAI est de 20s (ligne 171 `web_voice_bridge.py`). Si le client APK ne répond pas au ping applicatif dans ce délai (par exemple parce que le `ScriptProcessorNode` est saturé ou que la WebView freeze), la connexion WebSocket peut être coupée côté serveur. Cela correspond approximativement au bug "arrêt après ~20s".

Timeout mentionné dans la doc : **oui** (valeur : session max 300s / 5 min, avertissement à 1 minute avant fin, inactivité 300s / 5 min, ping OpenAI 20s, keepalive client 25s — source : `web_voice_bridge.py` lignes 55, 250-255, 270-279 ; `CAHIER_DES_CHARGES_MONITORING.md` §12)

#### Lacunes documentaires

Ce qui manque :
1. **Document de comportement WebView/APK** : aucun document ne décrit le fallback `ScriptProcessorNode` pour la WebView `LunaApp/`, ni les limitations audio d'Android WebView par rapport au navigateur desktop.
2. **Procédure de fallback voix → texte** : le code envoie `{"type": "error"}` au client qui appelle `stopVoice()` après 3s, mais il n'y a pas de document utilisateur expliquant "si la voix ne marche pas, bascule automatiquement sur le chat texte".
3. **Document des timeouts réels** : le cahier des charges mentionne "session max 300s" mais ne documente pas les autres timeouts critiques : ping OpenAI 20s, connexion OpenAI 10s, envoi client 10s, inactivité 300s. Ces valeurs sont dispersées dans le code sans centralisation documentaire.
4. **Procédure de test du bouton voix** : `PROMPT_CLAUDE_MONITORING_VOIX.md` demande "Comment tester le bouton sans vrai appel" mais aucun document ne donne cette procédure concrète.

#### Analyse code (Kimi Code CLI)

Résultat grep `LunaApp` dans index.html :
```
7048:  var match = ua.match(/LunaApp\/([\d.]+)/);
7493:  // AudioWorklet processor
7495:    "class LunaMicProcessor extends AudioWorkletProcessor {",
7588:      var _isWebView = /LunaApp\//.test(navigator.userAgent);
7599:          workletNode = new AudioWorkletNode(micCtx, "luna-mic-processor");
7603:          console.warn("[LunaVoice] AudioWorklet fallback ScriptProcessor");
7608:        var scriptNode = micCtx.createScriptProcessor(bufSize, 1, 1);
```
Détail : si `LunaApp/` est détecté dans le User-Agent, `AudioWorklet` est sauté et le code utilise `ScriptProcessorNode` (fallback). Ce fallback est invisible pour l'utilisateur (seul un `console.warn` est émis).

Voix par défaut dans web_voice_bridge.py :
- Ligne 34 : `OPENAI_VOICE_NAME = os.getenv("OPENAI_VOICE_NAME", "coral")`
- Ligne 54 : `voice: str = OPENAI_VOICE_NAME`
- Ligne 357 (dans `_configure_session`) : `"voice": self.voice`
La voix par défaut est bien `coral` (féminine) si la variable d'environnement n'est pas définie.

Timeout session (valeur réelle) :
- `max_duration_seconds: int = 300` (5 minutes) — ligne 55
- Avertissement à 1 minute avant la fin — `_duration_timer()` ligne 270-279
- Inactivité client : 300s (5 min) — `_client_keepalive()` ligne 254-255
- Ping keepalive côté serveur → client : toutes les 25s — ligne 250
- Ping/pong WebSocket OpenAI : interval 20s, timeout 20s — ligne 170-171
- Connexion OpenAI initiale : timeout 10s — ligne 175
- Envoi vers client : timeout 10s — ligne 133
- Envoi vers OpenAI : timeout 15s — ligne 99
- Tool call : timeout 45s — ligne 625

Gestion fin de session (reconnexion ou pas) :
- **Côté serveur** (`web_voice_bridge.py`) : pas de reconnexion automatique. La session se termine proprement avec `{"type": "ended"}` envoyé au client (lignes 285-288 pour max duration, lignes 258-261 pour inactivité).
- **Côté client** (`index.html`, `startVoice()`) :
  - Réception `ended` → `stopVoice()` après 2s (ligne 7706-7708)
  - Réception `error` → `stopVoice()` après 3s (ligne 7710-7713)
  - WebSocket fermé avec code inattendu → **auto-reconnexion x3** (`_voiceReconnectAttempts < _voiceMaxReconnects`) avec délai croissant (2s, 4s, 6s max 5s) et préservation du contexte (`historyData` passé en paramètre `&history=` ligne 7633-7636)
  - Codes 1000/1001 (fermeture propre) → arrêt sans reconnexion
  - Codes 4001 (session expirée) / 1011 (service indisponible) → arrêt sans reconnexion

#### Verdict Kimi

La documentation couvre-t-elle correctement la fonctionnalité vocale ? **non** (partiellement)

Recommandation (document à créer / à corriger) :
1. **Créer `docs/VOIX_WEBVIEW_BEHAVIOR.md`** : documenter le fallback `ScriptProcessorNode` en WebView Android, les timeouts réels (ping 20s, connexion 10s, session 300s), et le parcours utilisateur en cas d'échec.
2. **Corriger `docs/CAHIER_DES_CHARGES_MONITORING.md` §12** : ajouter la spécification du timeout ping OpenAI (20s) comme cause possible de coupure dans l'APK.
3. **Corriger `_check_objective_voix()` dans `luna_web.py`** :
   - Ne pas hardcoder `ws_voice_ok = True` — vérifier réellement que `@app.websocket("/ws/luna-voice")` est monté.
   - Vérifier la valeur runtime de `OPENAI_VOICE_NAME` (ou au moins la présence de la variable d'environnement) plutôt que chercher `"coral"` dans le HTML.
   - Ajouter un check sur le quota voix restant.
   - Ajouter un check sur la latence/lisibilité des erreurs côté client (feedback au clic).
4. **Créer une procédure de test** : "Comment tester le bouton voix sans vrai appel et sans consommer de quota" (simuler refus micro, vérifier que le message d'erreur s'affiche).

Problème code identifié (fichier + ligne) :
- `static/index.html:7603` — `console.warn("[LunaVoice] AudioWorklet fallback ScriptProcessor")` : invisible pour l'utilisateur APK. Si le fallback échoue ou ralentit, l'utilisateur est dans le silence.
- `static/index.html:7588-7608` — En WebView `LunaApp/`, `AudioWorklet` est systématiquement désactivé même si la WebView le supporte. C'est une détection basée uniquement sur le User-Agent, pas sur une feature-détection robuste.
- `integrations/openai/web_voice_bridge.py:171` — `ping_timeout: 20` : dans une WebView Android avec `ScriptProcessorNode`, le traitement audio peut bloquer le thread principal > 20s, ce qui peut causer la déconnexion du WebSocket côté serveur (correspond au bug "arrêt après ~20s").
- `luna_web.py:3083` — `ws_voice_ok = True  # /ws/luna-voice est monte dans luna_web.py` : assertion aveugle. Si la route est supprimée par erreur, le monitoring continuera de dire que tout va bien.
- `luna_web.py:3106` — Le check cherche `"coral"` dans `_html` (index.html) mais la source de vérité de la voix est `web_voice_bridge.py` et la variable d'environnement `OPENAI_VOICE_NAME`.

---

### Interdictions

- Ne pas pusher sur `main` directement
- Ne pas lancer `bash deploy.sh` ou commandes Cloud Run
- Ne pas lire ni modifier `.env` ou clés API
- Modifications code → branche `kimi/objectif-001-voix` + PR
- Modifications doc → peut commiter sur `main` directement
