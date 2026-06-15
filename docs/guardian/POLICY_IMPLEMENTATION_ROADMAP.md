# Guardian — Policy Implementation Roadmap
**Date : 15 juin 2026**
**Source : POLICY_IMPLEMENTATION_GAPS.md**
**Référence politique : GUARDIAN_BEHAVIOR_POLICY_V2.md**
**Statut : PLANIFICATION — aucune implémentation dans ce document**

---

## Grille de priorité

| Priorité | Critère |
|---|---|
| **P0** | Bloque le déploiement. Cause des dommages immédiats (SMS nocturnes, spam, panique). |
| **P1** | Manquement important à la Policy V2. Cause des faux positifs fréquents ou perte de confiance. |
| **P2** | Amélioration de qualité. La Policy est partiellement respectée mais perfectible. |
| **P3** | Évolution future. Conforme au minimum requis, mais la Policy prévoit mieux. |

---

## P0 — INDISPENSABLE (bloquer tout déploiement sans ces corrections)

### P0-01 — Mode Nuit

**Règle manquante :** Policy V2 §Partie 4.1

**Symptôme actuel :** Guardian envoie un SMS d'alerte après 30 minutes d'immobilité nocturne. Un senior qui dort reçoit une alerte à ses proches à 22h30.

**Fichier :** `core/guardian/engine.py` — fonction `_compute_risk()` lignes 423–467

**Ce qu'il faut faire :**
Lire la clé de config `night_mode` (déjà déclarée, jamais lue). Entre 23h et 7h, si `session.in_safe_zone = True`, ne pas calculer les signaux `immobility` et `prolonged_immobility`.

**Effort estimé :** 6–10 lignes

**Risque si non corrigé :** Abandon massif du service dès la première nuit (100% des familles SENIOR affectées).

---

### P0-02 — BABY : seuil 5 min → 120 min

**Règle manquante :** Policy V2 §Partie 4.2, §Scénario 17

**Symptôme actuel :** `_default_config(ProfileType.BABY)` dans engine.py:690 retourne `immobility_threshold_minutes: 5`. Un bébé qui dort 6 minutes déclenche une alerte. profiles.py dit 120 min mais n'est pas la source utilisée.

**Fichier :** `core/guardian/engine.py` — fonction `_default_config()` ligne 690

**Ce qu'il faut faire :**
Corriger `"immobility_threshold_minutes": 5` en `120` dans `_default_config(ProfileType.BABY)`.
Unifier avec profiles.py (les deux fichiers doivent avoir la même valeur).

**Effort estimé :** 1 ligne

**Risque si non corrigé :** Service inutilisable pour les familles avec bébé. Alerte toutes les 5 minutes de sieste.

---

### P0-03 — Timeout vérification : 2 min → 10 min

**Règle manquante :** Policy V2 §Niveau 2, §Scénario 12

**Symptôme actuel :** engine.py:532 `if elapsed > 120:` — escalade en 2 minutes. Un utilisateur sous la douche, au téléphone ou conduisant reçoit un SMS d'alerte à ses proches en 2 minutes.

**Fichier :** `core/guardian/engine.py` — fonction `_handle_risk()` ligne 532

**Ce qu'il faut faire :**
Changer `120` en `600` (10 minutes).

**Effort estimé :** 1 ligne

**Risque si non corrigé :** 2–5 faux positifs SMS par semaine par utilisateur dans une utilisation normale.

---

### P0-04 — SMS d'annulation

**Règle manquante :** Policy V2 §6.2

**Symptôme actuel :** Aucune fonction de SMS d'annulation. Quand l'utilisateur répond "tout va bien" après une alerte, les contacts ne sont jamais informés. Ils restent en état d'alerte indéfiniment.

**Fichiers :**
- `core/guardian/alerts.py` — ajouter `build_sms_cancellation()`
- `core/guardian/engine.py` — appeler depuis `register_verification_response(ok=True)` si `alerts_sent > 0`

**Ce qu'il faut faire :**
1. Ajouter `build_sms_cancellation(person_name, confirmed_at)` dans alerts.py
2. Ajouter `send_guardian_alerts()` avec ce message dans `register_verification_response()` quand `ok=True` et `session.alerts_sent > 0`
3. Passer la fonction `sms_send_fn` et les contacts à `register_verification_response()` (ou via une callback)

**Effort estimé :** 30–40 lignes

**Risque si non corrigé :** Contacts paniqués à chaque faux positif. Appels SAMU inutiles. Risque légal.

---

### P0-05 — Limite 3 alertes/24h (compteur existant mais jamais vérifié)

**Règle manquante :** Policy V2 §Partie 7.5

**Symptôme actuel :** `session.alerts_sent` est incrémenté (engine.py:505) mais jamais vérifié dans `_handle_risk()`. Pas de plafond d'alertes.

**Fichier :** `core/guardian/engine.py` — fonction `_handle_risk()` ligne 501

**Ce qu'il faut faire :**
Ajouter avant l'envoi d'alerte HIGH/CRITICAL :
```python
MAX_ALERTS_PER_24H = 3
if session.alerts_sent >= MAX_ALERTS_PER_24H:
    # Maintenir en Niveau 3 sans nouveau SMS
    return events
```
Ajouter aussi un champ `alerts_window_start` (timestamp) pour réinitialiser le compteur après 24h.

**Effort estimé :** 10–15 lignes

**Risque si non corrigé :** Spam SMS illimité. Facture Twilio incontrôlée. Contacts qui bloquent le numéro.

---

### P0-06 — Anti-spam progressif (backoff 30→60→120 min)

**Règle manquante :** Policy V2 §Partie 7.2

**Symptôme actuel :** `ALERT_COOLDOWN_SEC = 300` (5 min fixe). Avec immobilité persistante (nuit, sieste), une alerte toutes les 5 minutes.

**Fichier :** `core/guardian/engine.py` — constante ligne 138 et utilisation ligne 480

**Ce qu'il faut faire :**
Remplacer le cooldown fixe par un calcul progressif :
```python
ALERT_BACKOFF_SEC = [1800, 3600, 7200]  # 30, 60, 120 min
cooldown = ALERT_BACKOFF_SEC[min(session.alerts_sent, len(ALERT_BACKOFF_SEC)-1)]
if elapsed < cooldown:
    return events
```

**Effort estimé :** 5–8 lignes

**Risque si non corrigé :** Spam SMS toutes les 5 minutes en cas d'immobilité persistante.

---

### P0-07 — Grace period 2 heures

**Règle manquante :** Policy V2 §Partie 4.3

**Symptôme actuel :** Après un "tout va bien", Guardian peut déclencher une nouvelle vérification 5 minutes plus tard si l'immobilité GPS persiste.

**Fichier :** `core/guardian/engine.py` — GuardianSession + `_handle_risk()`

**Ce qu'il faut faire :**
1. Ajouter `grace_period_until: Optional[str] = None` dans GuardianSession dataclass
2. Dans `register_verification_response(ok=True)` : `session.grace_period_until = (now + timedelta(hours=2)).isoformat()`
3. Dans `_handle_risk()`, en début de fonction : `if session.grace_period_until and now < datetime.fromisoformat(session.grace_period_until): return []`

**Effort estimé :** 10–12 lignes

**Risque si non corrigé :** Utilisateurs re-alertés immédiatement après avoir confirmé "tout va bien". Abandon certain.

---

## P1 — IMPORTANT (qualité et conformité Policy V2)

### P1-01 — Seuils immobilité selon Policy V2 (SENIOR, DOG, HOME)

**Règle manquante :** Policy V2 §Partie 4.2

**Divergences :**
- SENIOR : 30 min (code) → 45 min (Policy) : trop sensible
- DOG : 60 min (engine) → 90 min (Policy + profiles.py) : incohérence
- HOME : 120 min (engine) → 240 min (Policy) : trop sensible

**Fichier :** `core/guardian/engine.py` — `_default_config()` lignes 671–705

**Effort estimé :** 4 lignes

---

### P1-02 — Niveau 3 (deuxième vérification avant SMS)

**Règle manquante :** Policy V2 §Niveau 3

**Symptôme actuel :** Une seule vérification (Niveau 2) avant escalade directe en HIGH/SMS. Aucun Niveau 3 intermédiaire.

**Fichiers :** `core/guardian/engine.py` — GuardianSession + `_handle_risk()`

**Ce qu'il faut faire :**
1. Ajouter `verification_attempt: int = 0` dans GuardianSession
2. Modifier `_handle_risk()` : sur escalade (elapsed > 600s), si `verification_attempt == 0` → deuxième vérification + son, `verification_attempt = 1`, réinitialiser timer. Si `verification_attempt >= 1` et elapsed > 300s supplémentaires → SMS.

**Effort estimé :** 20–25 lignes

---

### P1-03 — Supprimer speed_anomaly comme proxy de chute

**Règle manquante :** Policy V2 §Scénario 5

**Symptôme actuel :** `speed_anomaly > 5 m/s → score 0.7 → HIGH → SMS direct`. GPS ne détecte pas les chutes. Perturbations GPS = faux positifs.

**Fichier :** `core/guardian/engine.py` lignes 444–447 + 757–759

**Ce qu'il faut faire :**
Supprimer le signal `speed_anomaly` de `_compute_risk()` et le retirer de `_risk_description()`. Ou le reclasser en signal DOUTE (score 0.2) sans escalade directe.

**Effort estimé :** Suppression : 4 lignes. Reclassification : 8 lignes.

---

### P1-04 — Coordonnées GPS arrondies dans SMS (±100m)

**Règle manquante :** Policy V2 §RGPD §8.4

**Symptôme actuel :** `maps_link = f"https://maps.google.com/?q={lat},{lng}"` — coordonnées exactes (6 décimales = précision ~1m).

**Fichier :** `core/guardian/alerts.py` ligne 32 + `engine.py` ligne 507

**Ce qu'il faut faire :**
```python
maps_link = f"https://maps.google.com/?q={round(lat,3)},{round(lng,3)}"
```
3 décimales = précision ~100m.

**Effort estimé :** 2 lignes

---

### P1-05 — TTL Redis : 7 jours → 24h pour positions GPS

**Règle manquante :** Policy V2 §8.1

**Symptôme actuel :** `self.rc.client.expire(key, 86400 * 7)` — positions GPS conservées 7 jours.

**Fichier :** `core/guardian/engine.py` lignes 583 et 643

**Ce qu'il faut faire :**
Changer `86400 * 7` en `86400` (24h) pour les clés de position GPS. Garder 7 jours pour les events (traçabilité légale).

**Effort estimé :** 2 lignes

---

## P2 — AMÉLIORATION (qualité longue durée)

### P2-01 — Gestion GPS perdu (watchdog)

**Règle manquante :** Policy V2 §Scénario 10

**Symptôme actuel :** Si le GPS cesse d'envoyer des positions, le moteur ne le détecte pas. Aucun event "GPS perdu".

**Ce qu'il faut faire :**
Ajouter un champ `last_gps_at: Optional[str]` dans GuardianSession. Une tâche périodique backend vérifie si `now - last_gps_at > 10 min` → event `gps_lost`. Si `now - last_gps_at > 20 min` → Niveau 2.

**Effort estimé :** Moyen — nécessite une tâche périodique (cron ou asyncio task)

---

### P2-02 — Gestion réseau perdu (heartbeat)

**Règle manquante :** Policy V2 §Scénario 11

**Ce qu'il faut faire :**
Heartbeat WebSocket côté client toutes les 60s. Backend log la déconnexion. Si WebSocket fermé > 30 min pendant session active → SMS informatif (non alerte) : "Application hors ligne depuis 30 min."

**Effort estimé :** Moyen — frontend + backend

---

### P2-03 — SMS retour à la normale (fin de session)

**Règle manquante :** Policy V2 §6.3

**Ce qu'il faut faire :**
Dans `stop_session()`, si `session.alerts_sent > 0`, envoyer un SMS informatif optionnel : "Session terminée. Tout s'est bien passé."

**Effort estimé :** 15–20 lignes

---

### P2-04 — Log informatif caméra coupée (profil HOME)

**Règle manquante :** Policy V2 §Scénario 4 (profil HOME)

**Ce qu'il faut faire :**
Si profil HOME et caméra inactive pendant une session active, générer un event `camera_offline` (log interne, pas SMS).

**Effort estimé :** Faible — event seulement

---

## P3 — FUTUR (conformité avancée RGPD et UX)

### P3-01 — Route DELETE /api/guardian/data (droit à l'oubli)

**Règle manquante :** Policy V2 §8.3

**Ce qu'il faut faire :**
Route `DELETE /api/guardian/data` (ou `DELETE /api/guardian/session/:id/data`) qui supprime immédiatement toutes les clés Redis du tenant : positions, events, sessions.

**Effort estimé :** Faible côté code, mais nécessite validation sécurité (authentification obligatoire).

---

### P3-02 — Remplacer Nominatim ou le documenter

**Règle manquante :** Policy V2 §8.2

**Contexte :** Nominatim (OpenStreetMap) est utilisé pour la résolution d'adresse. Les CGU Nominatim interdisent l'usage commercial intensif. Luna est un service payant.

**Options :**
- Option A : Documenter l'usage dans la politique de confidentialité + contact OSM pour usage commercial
- Option B : Remplacer par un arrondi de coordonnées (ne nécessite pas Nominatim, juste 3 décimales)
- Option C : Utiliser un service tiers payant (Google Geocoding API, HERE, Geocodio)

**Effort estimé :** Option B = Faible. Options A/C = Moyen.

---

### P3-03 — Consentement contacts (UI)

**Règle manquante :** Policy V2 §8.3

**Ce qu'il faut faire :**
Lors de l'ajout d'un contact d'urgence, afficher une case à cocher : "Je confirme avoir informé [Prénom Contact] qu'il/elle peut recevoir des alertes SMS Luna." Stocker le consentement avec timestamp.

**Effort estimé :** Moyen (UI + backend)

---

## Tableau récapitulatif Roadmap

| ID | Règle | Priorité | Fichiers | Effort |
|---|---|---|---|---|
| P0-01 | Mode nuit | 🔴 P0 | engine.py: `_compute_risk()` | 6–10 lignes |
| P0-02 | BABY threshold 5→120 min | 🔴 P0 | engine.py: `_default_config()` | 1 ligne |
| P0-03 | Timeout 2 min → 10 min | 🔴 P0 | engine.py:532 | 1 ligne |
| P0-04 | SMS d'annulation | 🔴 P0 | alerts.py + engine.py | 30–40 lignes |
| P0-05 | Limite 3 alertes/24h | 🔴 P0 | engine.py: `_handle_risk()` | 10–15 lignes |
| P0-06 | Backoff progressif | 🔴 P0 | engine.py:138 + 480 | 5–8 lignes |
| P0-07 | Grace period 2h | 🔴 P0 | engine.py: session + handle_risk | 10–12 lignes |
| P1-01 | Seuils immobilité profils | 🟠 P1 | engine.py: `_default_config()` | 4 lignes |
| P1-02 | Niveau 3 (2e vérification) | 🟠 P1 | engine.py: session + handle_risk | 20–25 lignes |
| P1-03 | Supprimer speed_anomaly | 🟠 P1 | engine.py:444–447, 757–759 | 4–8 lignes |
| P1-04 | GPS ±100m dans SMS | 🟠 P1 | alerts.py:32 + engine.py:507 | 2 lignes |
| P1-05 | TTL Redis 7j → 24h | 🟠 P1 | engine.py:583, 643 | 2 lignes |
| P2-01 | GPS perdu watchdog | 🟡 P2 | engine.py + tâche async | Moyen |
| P2-02 | Réseau perdu heartbeat | 🟡 P2 | guardian.html + engine.py | Moyen |
| P2-03 | SMS retour à la normale | 🟡 P2 | engine.py: `stop_session()` | 15–20 lignes |
| P2-04 | Log caméra coupée (HOME) | 🟡 P2 | engine.py | Faible |
| P3-01 | DELETE route RGPD | 🟢 P3 | luna_web.py | Faible |
| P3-02 | Nominatim / alternative | 🟢 P3 | alerts.py:32 | Faible→Moyen |
| P3-03 | Consentement contacts UI | 🟢 P3 | guardian.html + backend | Moyen |

---

## Volume total d'implémentation P0

| Élément | Lignes estimées |
|---|---|
| Mode nuit (P0-01) | ~8 |
| BABY threshold (P0-02) | 1 |
| Timeout (P0-03) | 1 |
| SMS annulation (P0-04) | ~35 |
| Limite alertes (P0-05) | ~12 |
| Backoff progressif (P0-06) | ~6 |
| Grace period (P0-07) | ~11 |
| **Total P0** | **~74 lignes** |

Les 7 corrections P0 représentent environ **74 lignes de code** sur 3 fichiers (`engine.py`, `alerts.py`, et tests associés). C'est un périmètre maîtrisable, sans refonte architecturale.

---

## Ordre d'implémentation recommandé

```
Semaine 1 — P0 (déploiement bloqué sans ces corrections)
  ├── P0-02 : BABY threshold (1 ligne — risque zéro, impact immédiat)
  ├── P0-03 : Timeout 10 min (1 ligne — risque zéro, impact immédiat)
  ├── P0-01 : Mode nuit (8 lignes — cœur du problème)
  ├── P0-06 : Backoff progressif (6 lignes — dépend du compteur)
  ├── P0-05 : Limite 3 alertes/24h (12 lignes — utilise alerts_sent existant)
  ├── P0-07 : Grace period (11 lignes — nouveau champ session)
  └── P0-04 : SMS annulation (35 lignes — le plus complexe, à tester soigneusement)

Semaine 2 — P1 (qualité et conformité)
  ├── P1-01 : Seuils profils (4 lignes)
  ├── P1-03 : Supprimer speed_anomaly (4 lignes)
  ├── P1-04 : GPS ±100m SMS (2 lignes)
  ├── P1-05 : TTL Redis 24h (2 lignes)
  └── P1-02 : Niveau 3 (25 lignes — plus complexe, tester séparément)

Semaine 3+ — P2/P3 (selon priorités produit)
```

---

*Ce document ne contient aucune ligne de code modifiée.*
*Il est la traduction opérationnelle du POLICY_IMPLEMENTATION_GAPS.md.*
*Toute implémentation doit être validée par le fondateur avant commit.*
