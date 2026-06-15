# Guardian — Résultats d'implémentation P0
**Date : 15 juin 2026**
**Mission : GUARDIAN P0 IMPLEMENTATION**
**Référence : GUARDIAN_BEHAVIOR_POLICY_V2.md + POLICY_IMPLEMENTATION_GAPS.md**

---

## Résumé exécutif

Les 7 gaps P0 identifiés dans `POLICY_IMPLEMENTATION_GAPS.md` ont été implémentés.

**Score tests : 30/30 ✅**

Aucune architecture modifiée. Aucune nouvelle fonctionnalité ajoutée. Alignement comportemental uniquement.

---

## P0-01 — Mode Nuit

### Fichier modifié
`core/guardian/engine.py` — fonction `_compute_risk()`

### Changement

**Avant :** `night_mode: True` déclaré dans la config par défaut (ligne 675), jamais lu dans `_compute_risk()`.

**Après :** Ajout en tête de `_compute_risk()` :
```python
hour = now.hour
night_hours = (hour >= 23 or hour < 7)
night_mode_active = (
    session.config.get("night_mode", False)
    and night_hours
    and session.in_safe_zone
)
```
Les signaux `immobility` et `prolonged_immobility` sont protégés par `if not night_mode_active`. Le signal `night_anomaly` (hors zone la nuit) reste actif.

### Test réalisé

```
=== TEST 1 : Personne qui dort ===
✅ PASS Mode nuit actif → signal immobility absent       signals={}
✅ PASS Mode nuit actif → signal prolonged_immobility absent  signals={}
✅ PASS Score risque = 0 (dormir en safe zone la nuit)   risk.total=0.0
✅ PASS Niveau = LOW (pas d'alerte)                       level=AlertLevel.LOW
✅ PASS Aucun événement généré pendant le sommeil         events=[]
```

### Résultat : ✅ CONFORME

Dormir dans sa safe zone entre 23h et 7h ne génère plus aucune alerte.

---

## P0-02 — BABY Threshold

### Fichier modifié
`core/guardian/engine.py` — fonction `_default_config()`

### Changement

**Avant :**
```python
ProfileType.BABY: {
    "immobility_threshold_minutes": 5,   # BUG : 5 min
    ...
}
```

**Après :**
```python
ProfileType.BABY: {
    "immobility_threshold_minutes": 120,  # Sieste normale alignée sur profiles.py
    "night_mode": True,                   # Silence nocturne activé
    ...
}
```

Alignement avec `profiles.py` (qui déclarait déjà 120 min correctement).

### Test réalisé

```python
baby = _default_config(ProfileType.BABY)
assert baby['immobility_threshold_minutes'] == 120  ✅
assert baby.get('night_mode') == True               ✅
```

### Résultat : ✅ CONFORME

Une sieste de 2h ne déclenche plus d'alerte pour un profil BABY.

---

## P0-03 — Timeout vérification 10 minutes

### Fichier modifié
`core/guardian/engine.py` — fonction `_handle_risk()`

### Changement

**Avant :**
```python
if elapsed > 120:  # 2 min sans réponse
```

**Après :**
```python
if elapsed > 600:  # 10 min sans réponse — Policy V2 §Niveau 2
```

### Tests réalisés

```
=== TEST 3 : Utilisateur ignore 3 min → aucun SMS ===
✅ PASS Aucune escalade après 3 min (timeout = 10 min)  events=[]
✅ PASS Aucun SMS envoyé                                 sms_count=0
✅ PASS alert_pending toujours True                      alert_pending=True

=== TEST 4 : Utilisateur ignore 15 min → escalade ===
✅ PASS Escalade déclenchée après 15 min sans réponse   events=['alert_escalated']
✅ PASS alert_pending = False après escalade             alert_pending=False
✅ PASS Niveau HIGH après escalade                       alert_level=AlertLevel.HIGH
✅ PASS Compteur alertes incrémenté                      alerts_sent=1
```

### Résultat : ✅ CONFORME

Un utilisateur sous la douche, au téléphone ou qui conduit n'est plus escaladé en 2 minutes.

---

## P0-04 — SMS d'annulation

### Fichiers modifiés
- `core/guardian/alerts.py` — nouvelle fonction `build_sms_cancellation()`
- `core/guardian/engine.py` — `__init__()` (nouveau param `sms_send_fn`) + `register_verification_response()`

### Changements

**alerts.py :** nouvelle fonction :
```python
def build_sms_cancellation(person_name: str, confirmed_at: str) -> str:
    return (
        f"✅ Luna Guardian\n"
        f"Fausse alerte confirmée. {person_name} a confirmé "
        f"qu'il/elle allait bien à {confirmed_at}.\n"
        f"Aucune intervention nécessaire. Merci."
    )[:320]
```

**engine.py — __init__ :** ajout de `sms_send_fn=None` :
```python
def __init__(self, redis_client, openai_client=None, sms_send_fn=None):
    self.sms_send_fn = sms_send_fn
```

**engine.py — register_verification_response :** appel SMS si `alerts_sent > 0` :
```python
if session.alerts_sent > 0 and self.sms_send_fn:
    cancel_msg = build_sms_cancellation(person_name, confirmed_at)
    for contact in contacts:
        self.sms_send_fn(phone, cancel_msg, label="Annulation alerte Guardian")
```

### Test réalisé

```
=== TEST 5 : Utilisateur répond 'tout va bien' → SMS annulation ===
✅ PASS Réponse 'OK — alerte annulée'
✅ PASS SMS d'annulation envoyé                          sms_count=1
✅ PASS Contenu SMS = fausse alerte
         body_preview=✅ Luna Guardian\nFausse alerte confirmée. Marie a confirmé qu
✅ PASS Format SMS annulation correct
```

### Résultat : ✅ CONFORME

Les contacts reçoivent un SMS d'annulation automatique dans la minute suivant un "tout va bien" après alerte.

---

## P0-05 — Limite 3 alertes / 24h

### Fichier modifié
`core/guardian/engine.py` — constantes + `_handle_risk()` + `GuardianSession` + persistance Redis

### Changements

**Constante ajoutée :**
```python
MAX_ALERTS_PER_24H = 3
```

**GuardianSession — nouveau champ :**
```python
alerts_window_start: Optional[str] = None
```

**_handle_risk() — vérification avant alerte HIGH :**
```python
if session.alerts_window_start:
    w_elapsed = (now - datetime.fromisoformat(session.alerts_window_start)).total_seconds()
    if w_elapsed >= 86400:
        session.alerts_sent = 0   # Nouveau cycle 24h
        session.alerts_window_start = None
    elif session.alerts_sent >= self.MAX_ALERTS_PER_24H:
        return events  # Bloqué
# Premier envoi → initialiser la fenêtre 24h
if session.alerts_window_start is None:
    session.alerts_window_start = now.isoformat()
session.alerts_sent += 1
```

### Test réalisé

```
=== TEST 6 : Plus de 3 alertes → blocage ===
✅ PASS Aucun événement (plafond 3/24h atteint)   events=[]
✅ PASS Aucun SMS envoyé (bloqué par plafond)      sms_count=0
✅ PASS Compteur toujours à 3 (non incrémenté)     alerts_sent=3
```

### Résultat : ✅ CONFORME

Après 3 alertes SMS sur 24h, Guardian reste en surveillance sans spam.

---

## P0-06 — Backoff progressif (30 → 60 → 120 min)

### Fichier modifié
`core/guardian/engine.py` — constante + `_handle_risk()`

### Changement

**Avant :** `ALERT_COOLDOWN_SEC = 300` (5 min fixe)

**Après :**
```python
ALERT_BACKOFF_SEC = [1800, 3600, 7200]  # 30, 60, 120 min

# Dans _handle_risk() :
if session.last_alert_at and session.alerts_sent > 0:
    elapsed_since_alert = (now - datetime.fromisoformat(session.last_alert_at)).total_seconds()
    backoff = self.ALERT_BACKOFF_SEC[min(session.alerts_sent - 1, len(self.ALERT_BACKOFF_SEC) - 1)]
    if elapsed_since_alert < backoff:
        in_backoff = True
```

La logique d'escalade (vérification sans réponse) n'est **pas** bloquée par le backoff.

### Tests réalisés

```
--- Sous-test backoff progressif ---
✅ PASS Bloqué par backoff (10 min < 30 min après 1ère alerte)   events=[]
✅ PASS Autorisé après 35 min (> 30 min backoff 1ère alerte)     events=['alert_triggered']
```

### Résultat : ✅ CONFORME

Après la 1ère alerte : attente 30 min. Après la 2ème : 60 min. Après la 3ème : bloqué par plafond.

---

## P0-07 — Grace period 2 heures

### Fichier modifié
`core/guardian/engine.py` — `GuardianSession` + `register_verification_response()` + `_handle_risk()` + persistance Redis

### Changements

**GuardianSession — nouveau champ :**
```python
grace_period_until: Optional[str] = None
```

**register_verification_response (ok=True) :**
```python
session.grace_period_until = (now + timedelta(hours=2)).isoformat()
```

**_handle_risk() — vérification en tête :**
```python
if risk.level != AlertLevel.CRITICAL and session.grace_period_until:
    if now < datetime.fromisoformat(session.grace_period_until):
        return events  # Silence
```

Le SOS (`AlertLevel.CRITICAL`) bypass la grace period.

### Tests réalisés

```
✅ PASS Grace period activée (grace_period_until défini)
         grace_period_until=2026-06-15T23:39:24.566580
✅ PASS Grace period = 2h dans le futur
✅ PASS Grace period bloque les nouvelles vérifications   events=[]
```

### Résultat : ✅ CONFORME

Après "tout va bien", Guardian reste silencieux 2h. Un SOS manuel reste toujours actif.

---

## Score total des tests

```
============================================================
RÉSUMÉ DES TESTS
============================================================
Total : 30 tests — 30 ✅ PASS — 0 ❌ FAIL
→ Tous les comportements P0 sont conformes à la Policy V2
```

---

## Fichiers modifiés

| Fichier | Nature des modifications |
|---|---|
| `core/guardian/engine.py` | P0-01,02,03,05,06,07 — 7 sections modifiées |
| `core/guardian/alerts.py` | P0-04 — ajout `build_sms_cancellation()` |
| `tests/test_guardian_p0.py` | Nouveau — 30 tests comportementaux |

---

## État de conformité après P0

| Gap | Statut avant | Statut après |
|---|---|---|
| P0-01 Mode nuit | ❌ Variable morte | ✅ Implémenté |
| P0-02 BABY threshold | ❌ 5 min (bug) | ✅ 120 min |
| P0-03 Timeout 10 min | ❌ 2 min | ✅ 10 min |
| P0-04 SMS annulation | ❌ Absent | ✅ Implémenté |
| P0-05 Limite 3/24h | ❌ Compteur inutilisé | ✅ Vérifié et bloquant |
| P0-06 Backoff progressif | ❌ 5 min fixe | ✅ 30→60→120 min |
| P0-07 Grace period 2h | ❌ Absent | ✅ Implémenté |

**Guardian est maintenant déployable sans risque de spam SMS nocturne.**

Les gaps P1–P3 (Niveau 3, speed_anomaly, GPS perdu, RGPD) restent planifiés dans `POLICY_IMPLEMENTATION_ROADMAP.md`.

---

*Aucune architecture modifiée. Aucune nouvelle fonctionnalité. Alignement comportemental uniquement.*
*Tests exécutés localement sans Redis, sans Twilio, sans réseau.*
