# Avis Kimi — Objectif 006 Validation du cerveau sur panne vocale réelle

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Vérifier que le diagnostic cockpit est humain, juste, compréhensible
Date : 2026-05-25
Branche : `kimi/objectif-006-validation-cerveau`
Contexte réel : Ludovic teste l'APK, bouton vocal silencieux après 15-20 secondes

---

## Résumé exécutif

**Verdict : le cerveau Luna est prêt à voir la panne. Les textes sont cohérents, non culpabilisants, et la distinction entre heartbeat / événements voix / silence audio est claire.**

Quelques ajustements mineurs recommandés avant le test réel.

---

## 1. Le cockpit explique-t-il la panne sans accuser Ludovic ?

### OUI — avec une réserve mineure

**Textes vérifiés dans le code (`luna_web.py` lignes 20356-20470)**

| Scénario | Texte `luna_knows` | Accusation ? |
|---|---|---|
| `no_data` (aucun événement) | "Aucun événement voix n'a encore été reçu depuis le téléphone fondateur." | Non — factuel, "encore" laisse le bénéfice du doute |
| `no_audio_timeout` (silence 20s) | "le bouton vocal a été appuyé, le microphone est autorisé, la connexion s'est ouverte, de l'audio a été envoyé — mais aucun audio n'a été reçu en retour après 20 secondes" | Non — chronologie précise, aucun jugement |
| `mic_denied` | "Le bouton vocal a été appuyé mais le microphone n'a pas été autorisé par l'utilisateur." | Non — précise "par l'utilisateur" (Android), pas "par Ludovic" |
| `ws_error` | "Le WebSocket voix a rencontré une erreur avant que Luna n'ait pu répondre." | Non — technique, pas personnel |
| `ok` (succès) | "La session voix a produit de l'audio reçu par l'APK." | Non — positif sans emphase |
| `partial` | "Événements reçus : ... La session est peut-être encore en cours" | Non — laisse l'incertitude |

### Réserve mineure identifiée

Dans `static/fondateur.html` (ligne ~478) :

```javascript
var statusLabels = {
  ok: "Tout va bien",
  no_audio_timeout: "Problème important",
  mic_denied: "Microphone non autorisé",
  ws_error: "Erreur de connexion",        // ← ici
  partial: "Session partielle",
  no_data: "Aucun événement reçu"
};
```

**`ws_error: "Erreur de connexion"`** — le mot "Erreur" est présent. Dans KIMI_AVIS_005.md j'avais recommandé d'éviter ce terme. Proposition : **"Problème de connexion vocale"** (aligné avec le libellé `_VOICE_EVENT_LABELS` qui utilise déjà cette formulation).

### Recommandation

Corriger `statusLabels.ws_error` dans `fondateur.html` :
```javascript
ws_error: "Problème de connexion vocale",
```

---

## 2. Cohérence de `luna_sait`, `luna_suppose`, `luna_recommande`, `luna_ne_peut_pas`

### COHÉRENT — tableau de vérification

| Scénario | `luna_knows` | `luna_guesses` | `luna_recommends` | `luna_cannot` | Cohérent ? |
|---|---|---|---|---|---|
| `no_data` | Aucun événement reçu | Soit pas testé, soit télémétrie inactive | Appuyer sur le bouton vocal | Savoir si déjà appuyé sans événement | Oui — la supposition couvre le manque de donnée |
| `no_audio_timeout` | Chronologie complète jusqu'à l'envoi audio | 3 causes possibles OpenAI/serveur/WebView | Vérifier clés, quota, tester desktop | Corriger auto, forcer son, déterminer seule | Oui — chaque niveau est logique |
| `mic_denied` | Bouton appuyé, micro non autorisé | Permission refusée ou révoquée | Paramètres Android → Autorisations | Accorder à la place de l'utilisateur | Oui — limite claire |
| `ws_error` | WS a rencontré une erreur | Coupure réseau, timeout, OpenAI | Attendre 30s, vérifier réseau | Ouvrir la connexion, contourner réseau | Oui — recommandation proportionnée |
| `ok` | Audio reçu par l'APK | (vide) | Aucune action nécessaire | Vérifier que l'utilisateur a bien entendu | Oui — limite honnête |
| `partial` | Liste des événements reçus | Session en cours ou incomplète | Attendre et recharger | Distinguer en cours vs incomplète | Oui — reflète l'incertitude |

### Point de vigilance

Dans le scénario `no_audio_timeout`, `luna_guesses` énumère 3 causes possibles. C'est correct, mais il faut s'assurer que le cockpit n'affiche pas ça comme une liste à cocher que Ludovic doit explorer lui-même. Le texte est bien formulé comme une énumération de pistes, pas comme un questionnaire.

### Recommandation

Aucune correction nécessaire sur les textes eux-mêmes. Vérifier lors du test réel que Ludovic ne trouve pas la liste des 3 causes "trop technique". Si c'est le cas, simplifier en :

> "Luna suppose : le problème vient probablement du serveur vocal ou du téléphone. Pour savoir lequel, tester depuis un navigateur desktop permet de trancher."

---

## 3. Distinction : absence de heartbeat / absence d'événement voix / silence audio réel

### BIEN DISTINGUÉ — trois couches séparées

**Couche 1 — Heartbeat APK (`/api/admin/apk-diagnosis`)**

Affiché dans la section **"APK Fondateur — Sonde vivante"** de `fondateur.html`.

| Statut heartbeat | Signification | Affichage cockpit |
|---|---|---|
| `waiting_first_contact` | Aucun heartbeat jamais reçu | "Luna attend : le heartbeat APK n'a pas encore été reçu" |
| `heartbeat_lost` | Pas de heartbeat depuis > 24h | "Problème — L'APK n'a pas contacté le serveur depuis plus de 24h" |
| `heartbeat_old` | Pas de heartbeat depuis > 2h | "Attention — L'APK n'a pas été ouverte depuis Xh" |
| `apk_version_obsolete` | Version APK différente | "Attention — APK vX active, vY attendue" |
| `ok` | Heartbeat récent, version OK | "OK — APK vX active et à jour" |

**Couche 2 — Événements voix (`/api/admin/apk-voice-events`)**

Affiché dans la section **"Voix APK"** de `fondateur.html`.

| Statut voix | Signification | Affichage cockpit |
|---|---|---|
| `no_data` | Heartbeat OK mais aucun événement voix | "Aucun événement reçu" |
| `mic_denied` | Bouton appuyé, micro refusé | "Microphone non autorisé" |
| `ws_error` | WS ouvert puis erreur | "Problème de connexion vocale" |
| `no_audio_timeout` | Bouton→micro→WS→envoi→silence 20s | "Problème important" |
| `partial` | Événements incomplets | "Session partielle" |
| `ok` | Audio envoyé ET reçu | "Tout va bien" |

**Couche 3 — Silence audio réel (cas Ludovic)**

C'est le scénario `no_audio_timeout`. Le cockpit affiche :
1. Le statut "Problème important" (rouge)
2. `luna_knows` : chronologie complète jusqu'à l'envoi audio
3. `luna_guesses` : 3 causes possibles côté serveur/OpenAI/WebView
4. `luna_recommends` : vérifier clés, quota, tester desktop
5. `luna_cannot` : corriger auto, forcer son, déterminer seule
6. **Chronologie visuelle** avec icônes et heures

### Vérification de la distinction

| Situation | Section cockpit affichée | Statut | Correct ? |
|---|---|---|---|
| APK fermée / pas installée | APK Fondateur | `waiting_first_contact` ou `heartbeat_lost` | Oui |
| APK ouverte mais bouton jamais testé | Voix APK | `no_data` | Oui |
| APK ouverte, bouton testé, micro refusé | Voix APK | `mic_denied` | Oui |
| APK ouverte, bouton testé, silence 20s | Voix APK | `no_audio_timeout` | Oui |

### Point d'attention

Quand Ludovic verra le cockpit pour la première fois après avoir testé le bouton vocal, il verra **deux sections** :
1. APK Fondateur → probablement "OK" (si heartbeat récent)
2. Voix APK → "Problème important" avec la chronologie

C'est la bonne structure. Mais il faut s'assurer que Ludovic comprenne que ces deux sections sont indépendantes : le téléphone est vivant (section 1) mais la voix a un problème (section 2).

### Recommandation

Ajouter une ligne subtile dans l'affichage `no_data` et `no_audio_timeout` pour rappeler que le heartbeat est OK :

```javascript
// Dans loadVoiceDiagnosis(), si heartbeat est OK :
html += '<div style="color:#555;font-size:0.78em;margin-bottom:8px;">Le téléphone fondateur est en ligne. Le problème est spécifique à la voix.</div>';
```

---

## 4. Le journal fondateur raconte-t-il l'histoire de manière lisible ?

### PARTIEL — journal APK présent, journal voix absent

**Journal APK (`_write_founder_action_log` dans `luna_web.py`)**

Le diagnostic APK (heartbeat) est journalisé dans Redis (`luna:founder:actions:log`). Il est affiché dans la section APK Fondateur sous "JOURNAL (3 derniers)".

Format affiché :
```
ok          2026-05-25 13:00:00 — apk_alive
warning     2026-05-25 12:30:00 — heartbeat_old
```

**Problème identifié : le journal des événements voix n'existe pas.**

Quand Ludovic appuiera sur le bouton vocal et que le scénario `no_audio_timeout` se produira :
- L'événement sera stocké dans Redis (`luna:apk:voice:events`)
- Le diagnostic voix sera calculé à la volée par `_analyze_voice_events()`
- Mais **aucune trace durable** du diagnostic voix ne sera conservée dans le journal fondateur

Conséquence : si Ludovic revient 2 heures plus tard, il verra la chronologie des événements (car ils sont stockés 24h), mais il ne verra pas l'historique des conclusions que Luna avait tirées à chaque test.

### Recommandation

**Créer `_write_founder_voice_log()`** — analogue à `_write_founder_action_log()` mais pour les diagnostics voix.

Ou plus simplement, étendre `_write_founder_action_log()` pour aussi journaliser les changements de statut voix.

**Alternative minimale** (si pas de journal voix) : ajouter un champ `voice_status` dans le journal APK existant, pour que l'historique montre :
```
ok / voice_no_audio_timeout    2026-05-25 13:04:00 — apk_alive + panne vocale détectée
```

---

## 5. Points de contrôle pré-test réel

Avant que Ludovic ne teste, vérifier :

| # | Vérification | Où | Comment |
|---|---|---|---|
| 1 | `sendApkEvent("voice_button_clicked")` est bien appelé | `static/index.html:7865` | Confirmé — au début de `startVoice()` |
| 2 | Timer 20s déclenche `voice_no_audio_after_timeout` | `static/index.html:7666` | Confirmé — timer dans `voiceWs.onopen` |
| 3 | `voice_ws_closed` envoie le close code | `static/index.html:7756` | Confirmé — `sendApkEvent("voice_ws_closed", {ws_close_code})` |
| 4 | `microphone_permission_denied` envoie NotAllowedError | `static/index.html:7794` | Confirmé |
| 5 | Le cockpit affiche les 4 champs Kimi | `fondateur.html:472-475` | Confirmé — `luna_knows`, `luna_guesses`, `luna_recommends`, `luna_cannot` |
| 6 | La chronologie avec icônes s'affiche | `fondateur.html:477-488` | Confirmé — icônes, couleurs, heures |
| 7 | `ws_error` ne dit pas "Erreur" | `fondateur.html:~478` | À corriger — voir §1 |
| 8 | Journal voix existe | `luna_web.py` | Manquant — voir §4 |

---

## 6. Synthèse et recommandations finales

### Ce qui est prêt

1. **Textes cockpit** : cohérents, non culpabilisants, structurés Luna sait/suppose/recommande/ne peut pas
2. **Distinction heartbeat/voix/silence** : trois couches bien séparées dans deux sections du cockpit
3. **Chronologie visuelle** : icônes, couleurs, heures — lisible en un coup d'œil
4. **Libellés événements** : français clair, pas de jargon technique en affichage
5. **Filtrage sécurité** : whitelist stricte des événements et champs autorisés

### Ce qui doit être corrigé avant le test réel

1. **`fondateur.html` ligne ~478** : `ws_error: "Erreur de connexion"` → `"Problème de connexion vocale"`
2. **`luna_web.py`** : ajouter un journal des diagnostics voix (ou intégrer `voice_status` dans le journal APK existant)

### Ce qui sera validé par le test réel de Ludovic

1. Le heartbeat s'affiche-t-il correctement quand l'APK est ouverte ?
2. Les événements voix remontent-ils bien dans `/api/apk/event` ?
3. La chronologie s'affiche-t-elle avec les bonnes heures ?
4. Le texte `no_audio_timeout` est-il compris par Ludovic sans explication ?
5. La distinction entre "téléphone vivant" et "voix en panne" est-elle intuitive ?

### Verdict Kimi

> **Le cerveau Luna est prêt à voir la panne. Les textes sont humains, justes et compréhensibles. Deux micro-corrections (label ws_error + journal voix) et le test réel peut commencer.**

---

*Document produit par Kimi Code CLI pour l'objectif 006 — branche `kimi/objectif-006-validation-cerveau`*
