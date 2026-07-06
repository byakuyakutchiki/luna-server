# Findings actuels — Audit Guardian Voice APK

## ✅ Ce qui fonctionne

- Authentification APK : token présent, pas de message `Token invalide ou manquant`.
- Guardian s’ouvre correctement.
- `SpeechRecognition` est disponible dans la WebView de l’APK.
- La page `/static/debug/speech_test.html` fonctionne :
  - `rec.start()` appelé.
  - `onstart` déclenché.
  - `onresult` déclenché.
- Le micro physique et la permission Android semblent OK.

## ❌ Ce qui ne fonctionne pas

- Dans la page Guardian réelle, **« Luna écoute » reste INACTIF**.
- `Last /trigger status` : `-`.
- `Last guardian_session_id` : `-`.
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

## ❓ Questions ouvertes

- L’URL `trace---...` contient-elle les dernières corrections ?
- `_vocalStart()` est-elle appelée dans Guardian réel ?
- `rec.start()` échoue-t-il silencieusement ?
- La détection de mot-clé fonctionne-t-elle avec les transcripts répétés ?
- Le countdown et `/trigger` sont-ils atteints ?

## ⛔ Ce qui n’a pas encore été prouvé

La **première rupture exacte** dans la chaîne vocale n’a pas encore été identifiée avec certitude.

Les logs de diagnostic ajoutés dans `static/guardian.html` doivent maintenant permettre de la trouver.
