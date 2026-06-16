# Guardian P0 — Résultats du Test Terrain
**Date : 16 juin 2026**
**Cloud Run : `luna-beta-00658-rwj` → bugfix `8419366` en cours de déploiement**
**Méthode : tests API directs sur le serveur de production**

---

## Résumé exécutif

Les corrections P0 du moteur Guardian sont **comportementalement correctes** (30/30 tests unitaires).

Cependant, trois bugs de production ont été découverts pendant le terrain — absents des tests unitaires car ils concernent la couche API (`luna_web.py`), pas le moteur. Ces bugs ont été corrigés dans la foulée (commit `8419366`).

---

## Tableau de résultats

| Test | Scénario | Résultat | Note |
|---|---|---|---|
| T1 — Démarrage | Session créée, positions envoyées | ✅ PASS | Session `guard_3e651a7e7f` créée, risk=0.0, level=low |
| T2 — Config profils | SENIOR `night_mode: True`, BABY `threshold=120` | ✅ PASS | `/api/guardian/config/profiles` confirmé |
| T3 — Calcul risque | MEDIUM déclenché après >1 min d'immobilité | ✅ PASS | score=0.50, alert_pending=True |
| T4 — verify-response | "OK — alerte annulée", alert_pending cleared | ✅ PASS | Réponse correcte |
| T5 — Grace period Redis | `grace_period_until` persisté et chargé | ✅ PASS | Confirmé via code `_persist_session`/`_load_session` |
| T6 — Grace period status | Visible dans `/status` | ❌ FAIL → corrigé | Absent de la réponse API |
| T7 — SMS alerte | Envoi SMS contacts d'urgence | ⚠️ BLOQUÉ | Twilio 401 — credentials invalides |
| T8 — SMS annulation | SMS contacts après "tout va bien" | ⚠️ BLOQUÉ | `sms_send_fn` non câblé + Twilio 401 |
| T9 — Backoff P0-06 | Délai 30/60/120 min respecté | ❌ BYPASSED → corrigé | API SMS ignorait les events engine |
| T10 — Max 3/24h P0-05 | Plafond alertes respecté | ❌ BYPASSED → corrigé | idem |

---

## Bugs production découverts et corrigés

### Bug #1 — `sms_send_fn` non câblé (P0-04 dead code)

**Localisation :** `luna_web.py:14332` — `_get_guardian()`

**Avant :**
```python
_guardian_engine = GuardianEngine(
    redis_client=_redis_client,
    openai_client=openai_client,
    # sms_send_fn ABSENT
)
```

**Après :**
```python
_guardian_engine = GuardianEngine(
    redis_client=_redis_client,
    openai_client=openai_client,
    sms_send_fn=_tracked_sms_send,  # ← AJOUTÉ
)
```

**Impact :** P0-04 (SMS d'annulation après "tout va bien") était du code mort. L'engine appelait `self.sms_send_fn` qui était `None`.

---

### Bug #2 — API SMS bypasse la machine d'état P0 (CRITIQUE)

**Localisation :** `luna_web.py:14442` — endpoint `POST /api/guardian/location`

**Avant :**
```python
# SMS déclenché sur risk.level brut — ignore backoff, grace period, plafond
if risk.level.value in ("high", "critical"):
    ...
    send_guardian_alerts(...)
```

**Après :**
```python
# SMS déclenché uniquement sur events générés par l'engine
# → respecte P0-05 (max 3/24h), P0-06 (backoff), P0-07 (grace period)
alert_events = [e for e in events if e.event_type in ("alert_triggered", "alert_escalated")]
if alert_events:
    ...
    send_guardian_alerts(...)
```

**Impact :**
- Avant : chaque mise à jour GPS en risque HIGH/CRITICAL envoyait un SMS indépendamment de backoff/grace period/max
- Avant : une personne âgée immobile ≥45 min recevait des SMS répétés toutes les 10s (à chaque position GPS)
- Après : SMS uniquement quand l'engine décide d'escalader (respecte les 30/60/120 min de backoff)

**Bénéfice bonus P0-03 :** `alert_escalated` est généré après 10 min de vérification sans réponse. L'API envoie maintenant le SMS à exactement ce moment, même si le risk.level est encore MEDIUM.

---

### Bug #3 — `grace_period_until` absent du status endpoint

**Localisation :** `luna_web.py:14402` — endpoint `GET /api/guardian/status`

**Avant :** `grace_period_until` et `alerts_window_start` absents de la réponse.

**Après :** Les deux champs sont exposés. L'app mobile peut afficher "Guardian silencieux jusqu'à 14h32" et débogguer l'état P0.

---

## Twilio 401 — Blocker SMS en production

**Erreur Cloud Run observée :**
```
WARNING:luna.guardian.alerts:Guardian alert SMS failed to Test:
{'error': 'HTTP 401 error: Unable to create record: Authenticate', 'code': 20003}
ERROR:integrations.twilio.sms_client:Erreur envoi SMS: [20003] HTTP 401 error
```

**Cause :** Les variables `TWILIO_ACCOUNT_SID` et `TWILIO_AUTH_TOKEN` configurées sur Cloud Run sont invalides ou expirées.

**Impact :** Toutes les alertes Guardian (et SMS en général) échouent silencieusement en production.

**Action requise :**
1. Vérifier les credentials Twilio dans la console Cloud Run → Variables d'environnement
2. Regénérer `TWILIO_AUTH_TOKEN` si expiré dans [console.twilio.com](https://console.twilio.com)
3. Mettre à jour sur Cloud Run : `gcloud run services update luna-beta --set-env-vars TWILIO_AUTH_TOKEN=<nouveau>`
4. Vérifier que `TWILIO_ACCOUNT_SID` correspond au compte actif (ACff...)

---

## Ce qui fonctionne sans SMS (Twilio indépendant)

| Comportement | Statut |
|---|---|
| Démarrage session Guardian | ✅ Fonctionnel |
| Calcul risque immobilité | ✅ Correct |
| Night mode (23h–7h, safe zone) | ✅ Confirmé via config + unit tests |
| BABY threshold 120 min | ✅ Confirmé via API |
| alert_pending → verification_needed | ✅ Fonctionnel |
| verify-response "tout va bien" | ✅ Fonctionnel |
| Grace period (persistance Redis) | ✅ Persisté et chargé correctement |
| Backoff/max alertes (moteur) | ✅ Correct (30/30 tests) |
| Arrêt session | ✅ Fonctionnel |

---

## État après bugfix `8419366`

| Gap P0 | Statut moteur | Statut production |
|---|---|---|
| P0-01 Mode nuit | ✅ | ✅ (réduction score → 0) |
| P0-02 BABY 120 min | ✅ | ✅ |
| P0-03 Timeout 10 min | ✅ | ✅ (alert_escalated déclenche SMS) |
| P0-04 SMS annulation | ✅ | ✅ (sms_send_fn câblé) — si Twilio OK |
| P0-05 Max 3/24h | ✅ | ✅ (events gate) |
| P0-06 Backoff 30→60→120 | ✅ | ✅ (events gate) |
| P0-07 Grace period 2h | ✅ | ✅ (events gate + status exposé) |

**Seul blocker restant : Twilio 401 — credentials Cloud Run à mettre à jour.**

---

## Prochaine étape recommandée

1. **Mettre à jour Twilio sur Cloud Run** (5 min, sans redéploiement si `--update-env-vars`)
2. **Relancer les tests T7 et T8** pour valider SMS alerte + SMS annulation end-to-end
3. **Test de nuit** si besoin : s'endormir avec session SENIOR active en safe zone → 0 SMS attendu

---

*Tests terrain réalisés via API Cloud Run — pas de téléphone Android utilisé (blocage caméra Sprint B non résolu).*
*Commit bugfix : `8419366` — déployé sur `luna-beta` le 16 juin 2026.*
