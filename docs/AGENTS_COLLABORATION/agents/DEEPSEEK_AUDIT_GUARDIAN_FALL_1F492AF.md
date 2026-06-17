# DeepSeek — Audit Guardian chute accéléromètre — commit `1f492af`

**Date** : 2026-06-17  
**Agent** : DeepSeek (audit technique / risques)  
**Scope** : commit `1f492af` — "détection de chute accéléromètre — alerte en < 1s"  
**Fichiers audités** :
- `core/guardian/engine.py` (`trigger_fall`, `trigger_sos`, `_handle_risk`, `_compute_risk`)
- `core/guardian/alerts.py` (`send_guardian_alerts`, `build_sms_alert`)
- `luna_web.py` (`guardian_fall_detected`, `guardian_sos`, `guardian_location`, `_tracked_sms_send`, `_PUBLIC_PATHS`)
- `static/guardian.html` (`window.lunaFallDetected`, `window.lunaFallCancelled`, bridge JS)
- `android-app/java/fr/yawatch/luna/MainActivity.java` (détection chute, overlay, `sendFallToBackend`, `cancelFallAlertInternal`)
- `tests/test_guardian_p0.py`

---

## Verdict court

❌ **La chaîne de chute ne fonctionne pas en l'état.**

Le commit ajoute une détection native Android et un pipeline backend, mais **les requêtes Android vers le backend ne sont pas authentifiées**. Les endpoints `/api/guardian/fall-detected/` et `/api/guardian/verify-response/` retournent donc **401**, ce qui rend l'alerte chute et l'annulation "Je vais bien" inopérantes côté serveur.

En plus de ce blocage, le moteur ne respecte pas son propre plafond d'alertes pour les chutes, et le SOS n'incrémente pas le compteur 24h. Le tout crée un risque de spam SMS et une fausse sensation de sécurité.

**Ne pas considérer ce chantier comme terminé / déployable en l'état.**

---

## Correctifs appliqués (2026-06-17)

Les patchs suivants ont été appliqués localement :

| Problème | Fichier(s) | Correctif |
|---|---|---|
| Requêtes Android non authentifiées | `MainActivity.java`, `guardian.html` | Bridge `LunaBridge.setAuthToken(token)` + envoi `Authorization: Bearer ...` dans `sendFallToBackend()` et `cancelFallAlertInternal()`. |
| `trigger_fall()` bypass plafond | `core/guardian/engine.py` | Méthode `_can_send_alert()` + `alert_blocked` dans metadata de l'event. |
| `trigger_sos()` n'incrémente pas le compteur | `core/guardian/engine.py` | Mise à jour de `alerts_sent`, `last_alert_at` et `alerts_window_start`. |
| `guardian_fall_detected` ne reflète pas le plafond | `luna_web.py` | Retour 429 si `alert_blocked`, ajout de `guardian_sms_enabled` / `sms_blocked`. |
| Escalade Niveau 4 envoyée avec level MEDIUM | `luna_web.py` | `alert_level="high"` forcé pour `alert_escalated`. |
| Absence de tests | `tests/test_guardian_p0.py` | Tests 9 (chute + plafond) et 10 (SOS + compteur). |

**Résultat des tests :** 51/51 ✅ PASS.

**Reste à faire :** rebuild l'APK (`android-app/build.sh`) et test terrain réel.

---

## 1. Bugs critiques (P0)

### 1.1 Android n'envoie pas le JWT — toute la chaîne chute est en 401

**Où :** `android-app/java/fr/yawatch/luna/MainActivity.java:1070-1125` et `:1068-1086`

`sendFallToBackend()` et `cancelFallAlertInternal()` font des `HttpURLConnection` vers :
- `POST /api/guardian/fall-detected/{sid}`
- `POST /api/guardian/verify-response/{sid}`

Ils envoient `Content-Type: application/json` mais **aucun header `Authorization`**. Or ces routes ne sont **pas** dans `_PUBLIC_PATHS` (`luna_web.py:3604-3615`), et le middleware exige un Bearer JWT (`luna_web.py:4792`).

**Conséquence :**
- L'alerte chute n'atteint jamais le backend.
- Le bouton "SOS maintenant" de l'overlay natif (qui appelle aussi `fall-detected`) ne fonctionne pas.
- L'annulation "Je vais bien" n'est pas enregistrée côté serveur.

**Reproduction :** lancer l'APK, démarrer Guardian, déclencher une chute simulée, observer les logs serveur `401` sur `/api/guardian/fall-detected/`.

### 1.2 `trigger_fall()` bypass le plafond 3 alertes / 24h

**Où :** `core/guardian/engine.py:276-322`

La méthode incrémente `alerts_sent` sans vérifier `MAX_ALERTS_PER_24H` ni l'âge de la fenêtre. Le commentaire du commit prétend le respecter, mais ce n'est pas implémenté.

**Preuve :**
```python
session.alerts_sent = 3
session.alerts_window_start = il y a 1h
engine.trigger_fall(...)
# => alerts_sent = 4  (attendu: 3, bloqué)
```

**Conséquence :** spam SMS possible jusqu'à épuisement du crédit Twilio / saturation des contacts.

### 1.3 `trigger_sos()` n'incrémente pas `alerts_sent`

**Où :** `core/guardian/engine.py:252-274`

`trigger_sos()` ne met pas à jour `alerts_sent` ni `last_alert_at`. La route `guardian_sos` n'incrémente pas non plus ce compteur. Donc :
- Le plafond 3 alertes / 24h n'est **jamais** atteint par les SOS.
- Un utilisateur (ou un bug) peut spammer SOS indéfiniment.
- Les statistiques de session sont faussées.

**Preuve :**
```python
engine.trigger_sos(...)
# => alerts_sent reste à 0, last_alert_at reste None
```

---

## 2. Bugs importants (P1)

### 2.1 `guardian_fall_detected` ne retourne pas l'état du coupe-circuit SMS

**Où :** `luna_web.py:15142-15148`

Contrairement à `guardian_sos`, la route chute ne renvoie pas `guardian_sms_enabled` ni `sms_blocked`. L'utilisateur ne sait pas si les SMS ont été bloqués par `GUARDIAN_SMS_ENABLED=false`.

### 2.2 `guardian_location` peut envoyer un SMS d'escalade avec `alert_level="medium"`

**Où :** `luna_web.py:14891-14934` + `core/guardian/engine.py:869-896`

Dans `_handle_risk`, l'escalade Niveau 4 met `session.alert_level = HIGH` mais ne recalcule pas `risk.level`. La route `guardian_location` utilise `risk.level.value` pour l'SMS. Si le signal GPS est encore à 0.6 (MEDIUM), le SMS est envoyé avec `alert_level="medium"`, ce qui sélectionne le template `geofence_alert` au lieu du template `immobility_alert`.

### 2.3 `_handle_risk` laisse passer les niveaux CRITICAL sans plafond

**Où :** `core/guardian/engine.py:794-814`

La condition `if risk.level != AlertLevel.CRITICAL` protège seulement le plafond. Or `CRITICAL` peut être atteint par une combinaison de signaux (score ≥ 0.9), pas seulement par SOS. Un utilisateur hors zone la nuit + immobile peut donc bypasser le plafond.

### 2.4 Pas de rate-limit spécifique SOS / chute

Seul le rate-limit global IP existe (`luna_web.py:4321-4343`). Un client authentifié peut bombarder `guardian_sos` et `guardian_fall_detected`.

---

## 3. Limitations et risques produit

### 3.1 Détection de chute uniquement au premier plan

**Où :** `MainActivity.java:1182-1191` (`onPause` désenregistre l'accéléromètre)

Si l'application est en arrière-plan ou si l'écran est éteint, il n'y a **aucune** détection de chute. C'est une limitation majeure pour un produit de sécurité. Android exige un service foreground et des permissions spécifiques pour la détection en arrière-plan.

### 3.2 Algorithme de chute sensible aux faux positifs

**Où :** `MainActivity.java:886-916`

- Seuil de chute libre : < 4 m/s² pendant ≥ 80 ms.
- Seuil d'impact : > 22 m/s² (~2.2g) dans les 800 ms.

Un téléphone dans une poche lâche peut ne pas détecter la chute libre. Inversement, courir, sauter, poser violemment le téléphone ou un coup peuvent déclencher un faux positif.

### 3.3 Pas de retry si le POST chute échoue

**Où :** `MainActivity.java:1099-1126`

`sendFallToBackend()` est exécuté dans un thread unique. S'il y a une erreur réseau (timeout, 401, 503), l'alerte est perdue. Il n'y a ni retry, ni file locale, ni notification de l'utilisateur en cas d'échec.

### 3.4 L'overlay Android ne récupère pas le token JWT

Même si on ajoute un header `Authorization`, le Java natif ne sait pas quel token utiliser. Le token est stocké dans `localStorage` du WebView ou dans un cookie. Il faudrait un bridge JS→Java pour le transmettre, ou une route publique signée avec un token de session dédié.

### 3.5 Pas de tests automatisés pour la chute

`tests/test_guardian_p0.py` ne couvre pas `trigger_fall`, `guardian_fall_detected` ni le plafond SOS. Les 45 tests passent, mais ils ne valident pas le nouveau chantier.

---

## 4. Scénarios critiques

### Scénario A — Chute réelle avec l'APK
1. L'utilisateur tombe, l'accéléromètre déclenche l'overlay.
2. Il ne peut pas répondre dans les 30s.
3. Android appelle `POST /api/guardian/fall-detected/{sid}` **sans token**.
4. Serveur répond **401**.
5. **Aucun SMS n'est envoyé.** Les contacts ne sont pas alertés.

### Scénario B — Spam de chutes
1. Un client (ou un bug) appelle `fall-detected` 10 fois en 5 minutes.
2. `trigger_fall()` incrémente `alerts_sent` à chaque fois, sans plafond.
3. 10 SMS sont envoyés aux contacts.

### Scénario C — Spam de SOS
1. L'utilisateur appuie 10 fois sur SOS.
2. `trigger_sos()` ne touche jamais à `alerts_sent`.
3. 10 SMS SOS sont envoyés.

---

## 5. Ce qui doit être corrigé avant production

### P0 — Bloquant

1. **Authentifier les requêtes Android natives.**
   - Option A : le WebView transmet le JWT à Java via `LunaBridge` (`window.LunaBridge.setAuthToken(token)`), et Java l'envoie dans `Authorization: Bearer ...`.
   - Option B : créer une route publique signée avec un token de session Guardian dédié (HMAC côté serveur, transmis au JS au démarrage).
2. **Implémenter le plafond 3 alertes / 24h dans `trigger_fall()`** (comme dans `handle_checkin_missed`).
3. **Faire en sorte que `trigger_sos()` incrémente `alerts_sent` et `last_alert_at`**, et que `guardian_sos()` respecte le plafond (sauf décision explicite de bypass).
4. **Ajouter des tests P0** pour `trigger_fall` avec plafond et `trigger_sos` avec plafond.

### P1 — Important

5. `guardian_fall_detected` doit retourner `guardian_sms_enabled` et `sms_blocked` comme `guardian_sos`.
6. Corriger `guardian_location` pour envoyer `alert_level="high"` lors d'une escalation Niveau 4.
7. Appliquer le plafond 24h à tous les chemins CRITICAL (pas seulement HIGH), sauf SOS qui reste prioritaire.
8. Ajouter un rate-limit par session sur `guardian_sos` et `guardian_fall_detected`.
9. Ajouter un retry / file locale dans `sendFallToBackend` en cas d'échec réseau.
10. Documenter la limitation "détection uniquement au premier plan" dans l'interface utilisateur.

### P2 — Amélioration

11. Calibrer l'algorithme de chute (tests terrain avec plusieurs téléphones / positions).
12. Envisager un service foreground pour la détection en arrière-plan.
13. Nettoyer `pendingPeakG` et l'état de chute si la session est arrêtée pendant l'overlay.

---

## 6. Décision recommandée

**Ne pas déployer le commit `1f492af` en production** avant correction des P0.

**Validation minimale avant merge :**
- Test E2E avec l'APK : simuler une chute, vérifier que le backend reçoit `fall-detected` (pas 401), que les SMS partent, et que l'annulation fonctionne.
- Test unitaire : `trigger_fall` respecte le plafond 3/24h.
- Test unitaire : `trigger_sos` incrémente `alerts_sent`.

**Conformément aux règles de coordination**, toute décision de déploiement doit être validée par Ludovic.

---

*Avis rédigé par DeepSeek. Ne pas modifier ce fichier sans en avertir l'auteur.*
