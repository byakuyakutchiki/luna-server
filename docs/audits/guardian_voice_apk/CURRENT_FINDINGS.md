# Findings actuels — Audit Guardian Voice APK

## ✅ Ce qui fonctionne

- Authentification APK : token présent, pas de message `Token invalide ou manquant`.
- Guardian s’ouvre correctement.
- `SpeechRecognition` est disponible dans la WebView de l’APK.
- La page `/static/debug/speech_test.html` fonctionne :
  - `rec.start()` appelé.
  - `onstart` déclenché.
  - `onresult` déclenché.
- Le micro physique et la permission Android semblent OK (preuve : Speech Test capture l’audio).

## ❌ Ce qui ne fonctionne pas

- Dans la page Guardian réelle, **« Luna écoute » reste INACTIF**.
- `Last /trigger status` : `-`.
- `Last guardian_session_id` : `-`.
- **L’appel backend `/api/guardian/sos/{sid}` (ou ancien `/trigger`) n’est jamais atteint.**
- Le SOS vocal ne part jamais depuis l’APK.

## 🔍 Problèmes techniques observés

### 1. Transcript répété

Dans `speech_test.html`, les résultats intermédiaires s’accumulent :

```
"ààà l'aide"
"ààà l'aide à l'aide"
"ààà l'aide à l'aide je..."
```

Cela indique que la reconstruction du transcript parcourt tous les `event.results` au lieu de n’utiliser que les nouveaux segments (`event.resultIndex`).

### 2. APK pointe vers une révision Cloud Run ancienne

Panneau diagnostic APK :

```
Backend URL: https://trace---luna-beta-gly3g647na-ew.a.run.app/guardian
Backend version: unknown
Cloud Run revision: unknown
```

L’APK charge la révision `trace` (`luna-beta-00987-vif`) et non la révision audit actuelle (`phase-a-auth---...` / `luna-beta-phase-b-logs`).

Cela peut expliquer pourquoi les corrections de Phase A/B ne sont pas visibles dans l’APK.

### 3. Guardian réel n’active pas l’écoute

Le Speech Test fonctionne, mais Guardian reste inactif. Cela suggère que la fonction `_vocalStart()` dans `guardian.html` n’est pas appelée, ou s’arrête avant `rec.start()`.

### 4. GuardianService — clarification

Le service Android `GuardianService` actuel est un **service foreground de notification uniquement** (Phase 1). Il ne fait pas d’écoute vocale native persistante. Il ne doit pas être présenté comme une source VOSK validée.

L’écoute vocale dans l’APK repasse actuellement par la WebView et la Web Speech API, comme dans Chrome.

## ❓ Questions ouvertes

- L’URL `trace---...` contient-elle les dernières corrections ?
- `_vocalStart()` est-elle appelée dans Guardian réel ?
- `rec.start()` échoue-t-il silencieusement ?
- La détection de mot-clé fonctionne-t-elle avec les transcripts répétés ?
- Le countdown et `/api/guardian/sos/{sid}` sont-ils atteints ?

## ⛔ Première rupture probable

La première rupture probable se situe à l’un de ces deux endroits :

1. **Activation de l’écoute Guardian réelle** : Guardian n’appelle pas `_vocalStart()` ou cette fonction s’arrête avant `rec.start()`.
2. **Passage `onresult` → matcher** : même si l’écoute démarre, le transcript reconstruit avec répétitions empêche la détection du mot-clé, donc `openVocalCountdown()` n’est jamais appelé.

## ⛔ Ce qui n’a pas encore été prouvé

La **première rupture exacte** dans la chaîne vocale n’a pas encore été identifiée avec certitude. Des logs supplémentaires sont nécessaires sur la vraie page Guardian, en condition APK.
