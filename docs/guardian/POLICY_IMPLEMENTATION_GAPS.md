# Guardian — Policy Implementation Gap Analysis
**Date : 15 juin 2026**
**Référence politique : GUARDIAN_BEHAVIOR_POLICY_V2.md**
**Statut : LECTURE SEULE — aucune modification de code**

---

## Méthode

Lecture exhaustive de :
- `core/guardian/engine.py` (795 lignes)
- `core/guardian/alerts.py` (109 lignes)
- `core/guardian/profiles.py` (87 lignes)
- `static/guardian.html` (contexte précédent)

Chaque règle de la Policy V2 est comparée à l'implémentation réelle.

---

## Légende

| Statut | Signification |
|---|---|
| ✅ Implémentée | La règle est présente et fonctionnelle dans le code |
| ⚠️ Partielle | La règle est partiellement présente — une partie manque |
| ❌ Absente | La règle n'existe pas dans le code actuel |

---

## RÈGLE 1 — Mode Nuit (23h–7h en safe zone)

### STATUT : ❌ Absente

### PREUVE

```python
# engine.py:675 — le flag existe dans la config par défaut
ProfileType.SENIOR: {
    "night_mode": True,   # ← déclaré ici
    ...
}

# engine.py:423–467 — _compute_risk() — night_mode n'est jamais lu
def _compute_risk(self, session, pos, now):
    signals = {}
    # ← PAS DE LECTURE de session.config.get("night_mode")
    # ← PAS DE SUSPENSION des signaux immobility la nuit
    
    # Signal 1 : Immobilité — actif H24, sans distinction nuit/jour
    if session.is_immobile and session.immobile_since:
        signals["immobility"] = ...   # déclenche aussi à 23h30

    # Signal 3 : Night anomaly (hors zone la nuit) — c'est différent du mode nuit
    if (hour >= 22 or hour < 6) and not session.in_safe_zone:
        signals["night_anomaly"] = 0.5
```

**Conclusion :** `night_mode: True` est un paramètre de configuration **mort**. Il est déclaré mais jamais lu. Les signaux d'immobilité s'activent identiquement à 3h du matin et à 15h. Dormir dans son lit déclenche une alerte après 30 minutes.

### IMPACT : 🔴 Critique

Sans mode nuit, Guardian enverra des SMS d'alerte chaque nuit de sommeil. Perte de confiance garantie en moins d'une semaine pour 100% des familles.

### EFFORT : Faible

Ajouter 4–6 lignes dans `_compute_risk()` pour lire `night_mode` et supprimer `immobility` / `prolonged_immobility` des signaux entre 23h et 7h si `in_safe_zone = True`.

### RECOMMANDATION

```python
# À ajouter dans _compute_risk(), avant Signal 1 :
hour = now.hour
night_hours = (hour >= 23 or hour < 7)
night_mode = session.config.get("night_mode", False)
if night_mode and night_hours and session.in_safe_zone:
    # Sommeil probable — suspendre immobilité
    pass  # ne pas calculer immobility / prolonged_immobility
else:
    # Signal 1 : Immobilité (logique existante)
    ...
```

---

## RÈGLE 2 — Safe Zone (geofence)

### STATUT : ✅ Implémentée

### PREUVE

```python
# engine.py:57–59 — SafeZone.contains() par distance haversine
def contains(self, point: GeoPoint) -> bool:
    return _haversine(self.lat, self.lng, point.lat, point.lng) <= self.radius_m

# engine.py:385–421 — _check_geofences() — sortie/entrée zone
def _check_geofences(self, session, pos):
    # Génère geofence_exit et geofence_enter events

# engine.py:436–437 — signal geofence_exit dans _compute_risk
if not session.in_safe_zone and session.config.get("safe_zones"):
    signals["geofence_exit"] = 0.6 if profile != ProfileType.HOME else 0.8
```

**Nuance :** La configuration par défaut a `"safe_zones": []`. La fonctionnalité n'est active que si l'utilisateur configure au moins une zone. Si aucune zone n'est configurée, le signal `geofence_exit` ne se déclenche jamais.

### IMPACT : 🟡 Faible (si safe zones vides)

### EFFORT : N/A

---

## RÈGLE 3 — Timeout vérification 10 minutes

### STATUT : ❌ Absente (valeur incorrecte)

### PREUVE

```python
# engine.py:529–532 — escalade après vérification
if (session.alert_pending and session.verification_sent_at and
        risk.level >= AlertLevel.MEDIUM):
    elapsed = (now - datetime.fromisoformat(session.verification_sent_at)).total_seconds()
    if elapsed > 120:  # ← 2 MINUTES — Policy dit 10 minutes (600s)
        session.alert_pending = False
        session.last_alert_at = now.isoformat()
        session.alert_level = AlertLevel.HIGH
        # → SMS envoyé
```

**Conclusion :** Le timeout est de **2 minutes** au lieu de **10 minutes** requis par la Policy V2. L'utilisateur sous la douche, au téléphone, ou qui conduit reçoit un SMS d'alerte à ses proches après 2 minutes de non-réponse.

### IMPACT : 🔴 Critique

C'est la deuxième cause principale de faux positifs. Un utilisateur ne regardant pas son téléphone pendant 2 minutes (ce qui est normal) déclenche une alerte SMS.

### EFFORT : Faible

Changer `120` en `600` (une ligne).

### RECOMMANDATION

```python
if elapsed > 600:  # 10 minutes — Policy V2 §Niveau 2
```

---

## RÈGLE 4 — Niveau 3 : deuxième vérification après 5 minutes

### STATUT : ❌ Absente

### PREUVE

La Policy V2 définit un **Niveau 3 SUSPICION FORTE** :
- Niveau 2 → pas de réponse dans 10 min → Niveau 3 → deuxième vérification → attente 5 min → Niveau 4

Dans le code actuel :
```python
# engine.py:529–546 — escalade directe Niveau 2 → HIGH (Niveau 4)
if elapsed > 120:
    session.alert_level = AlertLevel.HIGH  # ← saute directement à HIGH
    # SMS envoyé immédiatement — PAS de Niveau 3 intermédiaire
    esc_event = GuardianEvent(
        event_type="alert_escalated",
        description="⚠️ Pas de réponse à la vérification — alerte escaladée",
        ...
    )
```

Il n'y a que deux états : vérification envoyée (MEDIUM) → escalade directe (HIGH). Aucun état intermédiaire de "deuxième tentative".

### IMPACT : 🟠 Élevé

Le système passe de la première vérification au SMS contact sans deuxième chance. Ajoute des faux positifs dans tous les cas où la première notification n'a pas été vue.

### EFFORT : Moyen

Ajouter un état `verification_level: int` (1 ou 2) dans GuardianSession, et brancher la logique d'escalade sur deux étapes.

### RECOMMANDATION

Ajouter `verification_attempt: int = 0` dans GuardianSession. Sur elapsed > 600s et `verification_attempt == 1`, envoyer une deuxième vérification (avec son) et réinitialiser le timer à now. Sur elapsed > 600+300s (5 min de plus), escalader.

---

## RÈGLE 5 — SMS d'alerte

### STATUT : ⚠️ Partielle

### PREUVE

```python
# alerts.py:19–66 — build_sms_alert() existe
def build_sms_alert(person_name, description, lat, lng, alert_level, profile_type, ...):
    maps_link = f"https://maps.google.com/?q={lat},{lng}"  # ← coordonnées EXACTES
    ...
    footer += "\nRendez-vous sur place si besoin, ou appelez le 15/112 en urgence."

# alerts.py:69–108 — send_guardian_alerts() existe
def send_guardian_alerts(sms_send_fn, contacts, ...):
    # Envoie aux contacts
```

**Ce qui fonctionne :** Construction du SMS, envoi multi-contacts, footer légal 15/112.

**Ce qui manque :**
1. Coordonnées GPS exactes dans le lien Maps (Policy dit ±100m arrondi)
2. Le SMS est généré lors d'un `alert_escalated` event (engine.py:537–544) mais **la fonction `send_guardian_alerts()` n'est jamais appelée dans engine.py**. Elle existe dans `alerts.py` mais son appel effectif est dans `luna_web.py` (non lu mais présumé). À vérifier.

### IMPACT : 🟠 Élevé (si SMS jamais envoyé)

### EFFORT : Faible (correction coordonnées ±100m)

### RECOMMANDATION

Arrondir les coordonnées à 3 décimales (~100m) avant construction du lien :
```python
maps_link = f"https://maps.google.com/?q={round(lat,3)},{round(lng,3)}"
```

---

## RÈGLE 6 — SMS d'annulation

### STATUT : ❌ Absente

### PREUVE

```python
# engine.py:261–285 — register_verification_response(ok=True)
def register_verification_response(self, session_id: str, ok: bool):
    if ok:
        session.alert_pending = False
        session.alert_level = AlertLevel.LOW
        session.verification_sent_at = None
        self._log_event(...)  # ← log interne seulement
        self._persist_session(session)
        return "OK — alerte annulée"
        # ← AUCUN SMS d'annulation envoyé aux contacts

# alerts.py — aucune fonction build_sms_cancellation() ou send_cancellation_sms()
```

**Conclusion :** Quand l'utilisateur confirme "tout va bien" après qu'un SMS d'alerte a été envoyé, les contacts ne reçoivent **aucune information**. Ils restent en état d'alerte indéfiniment.

### IMPACT : 🔴 Critique

Les contacts reçoivent une alerte. Ils ne reçoivent jamais "fausse alarme, tout va bien." Ils interviennent inutilement (appel SAMU, déplacement). Perte de confiance radicale. Risque légal (faux appel 112 par un contact).

### EFFORT : Faible

Ajouter `build_sms_cancellation()` dans alerts.py et l'appeler depuis `register_verification_response()` si `session.alerts_sent > 0`.

### RECOMMANDATION

```python
# alerts.py — NOUVELLE FONCTION
def build_sms_cancellation(person_name: str, confirmed_at: str) -> str:
    return (f"✅ Luna Guardian\n"
            f"Fausse alerte. {person_name} a confirmé qu'il/elle allait bien "
            f"à {confirmed_at}.\n"
            f"Aucune intervention nécessaire. Merci.")

# engine.py — dans register_verification_response() si ok=True et alerts_sent > 0
if ok and session.alerts_sent > 0:
    # Appeler send_guardian_alerts() avec le SMS d'annulation
```

---

## RÈGLE 7 — SMS retour à la normale (fin de session)

### STATUT : ❌ Absente

### PREUVE

```python
# engine.py:167–178 — stop_session()
def stop_session(self, session_id: str) -> bool:
    session.is_active = False
    self._persist_session(session)
    self._log_event(session_id, GuardianEvent(
        event_type="session_stopped",
        description="Session Guardian arrêtée",  # ← log interne uniquement
    ))
    return True
    # ← AUCUN SMS "Session terminée, tout s'est bien passé"
```

### IMPACT : 🟡 Moyen

Les contacts ne savent pas que la session est terminée. Si une alerte a été envoyée dans la journée, ils ne savent pas si la situation est résolue ou non.

### EFFORT : Faible

Ajouter un SMS informatif optionnel (configurable par l'exploitant) lors de `stop_session()` si `alerts_sent > 0` pendant la session.

---

## RÈGLE 8 — Grace period 2 heures

### STATUT : ❌ Absente

### PREUVE

```python
# engine.py:100–122 — GuardianSession dataclass
@dataclass
class GuardianSession:
    # ... 
    alert_pending: bool = False
    alert_level: AlertLevel = AlertLevel.LOW
    verification_sent_at: Optional[str] = None
    last_alert_at: Optional[str] = None
    alerts_sent: int = 0
    # ← PAS DE CHAMP grace_period_until ou last_verified_ok_at
```

```python
# engine.py:469–546 — _handle_risk()
# ← PAS DE VÉRIFICATION d'une grace period
# Immédiatement après un "tout va bien", si l'immobilité persiste,
# une nouvelle vérification sera déclenchée au prochain cycle
```

**Conclusion :** Après qu'un utilisateur répond "tout va bien", il n'y a aucune protection contre une nouvelle alerte immédiate. Si le signal d'immobilité persiste (parce que la personne est toujours assise), Guardian peut déclencher une nouvelle vérification lors du prochain cycle.

### IMPACT : 🟠 Élevé

L'utilisateur répond "tout va bien" et Guardian lui repose la question 5 minutes plus tard. Frustration maximale, désactivation certaine.

### EFFORT : Faible

Ajouter `grace_period_until: Optional[str] = None` dans GuardianSession. Le renseigner à `now + 2h` lors de `register_verification_response(ok=True)`. Vérifier dans `_handle_risk()` avant tout déclenchement.

---

## RÈGLE 9 — Anti-spam progressif

### STATUT : ❌ Absente (anti-spam basique présent mais non progressif)

### PREUVE

```python
# engine.py:138
ALERT_COOLDOWN_SEC = 300  # 5 min — FIXE, pas progressif

# engine.py:477–481 — anti-spam basique
if session.last_alert_at:
    elapsed = (now - datetime.fromisoformat(session.last_alert_at)).total_seconds()
    if elapsed < self.ALERT_COOLDOWN_SEC:  # ← toujours 5 min, même pour la 10e alerte
        return events
```

**Ce qui existe :** Un cooldown de 5 minutes constant entre alertes.

**Ce qui manque :** Le backoff progressif. Après la 1ère alerte, délai 30 min. Après la 2ème, 60 min. Après la 3ème, 120 min.

**Impact mathématique :** Avec un cooldown de 5 min et une immobilité persistante (ex. nuit), Guardian envoie théoriquement 12 SMS/heure soit **96 SMS en 8h de sommeil**. En pratique limité par `alerts_sent` mais ce compteur n'est jamais vérifié (voir Règle 10).

### IMPACT : 🔴 Critique

Spam SMS aux contacts. Facture Twilio explosive. Contacts qui bloquent le numéro Luna.

### EFFORT : Faible

Remplacer `ALERT_COOLDOWN_SEC` par un calcul basé sur `session.alerts_sent`.

---

## RÈGLE 10 — Limite 3 alertes / 24h

### STATUT : ❌ Absente (compteur présent mais jamais vérifié)

### PREUVE

```python
# engine.py:121 — compteur existe dans la session
alerts_sent: int = 0

# engine.py:505 — compteur incrémenté à chaque alerte
session.alerts_sent += 1

# engine.py:469–546 — _handle_risk() — AUCUNE vérification du compteur
# Il n'y a nulle part : "if session.alerts_sent >= 3: return"
```

**Conclusion :** Le compteur `alerts_sent` est présent et incrémenté mais **jamais utilisé pour limiter les alertes**. Guardian peut envoyer un nombre illimité de SMS d'alerte sur 24h.

### IMPACT : 🔴 Critique

Sans plafond, une session de nuit avec immobilité peut générer des dizaines de SMS aux contacts.

### EFFORT : Faible

Ajouter une vérification dans `_handle_risk()` et un champ `alerts_window_start` pour réinitialiser le compteur après 24h.

---

## RÈGLE 11 — Backoff 30 → 60 → 120 minutes

### STATUT : ❌ Absente

### PREUVE

Voir Règle 9. Seul un cooldown constant de 5 minutes existe. Aucune logique de backoff progressif.

**Preuve complémentaire :** Il n'y a pas de tableau ou de calcul `[300, 1800, 7200][min(alerts_sent, 2)]` dans le code.

### IMPACT : 🔴 Critique (même que Règle 9 et 10, cumul)

### EFFORT : Faible

---

## RÈGLE 12 — Gestion GPS perdu

### STATUT : ❌ Absente

### PREUVE

Le moteur Guardian fonctionne en mode "pull" : il n'est déclenché que quand `process_location()` est appelé. Si le GPS ne transmet plus, le moteur ne fait tout simplement rien — aucun event "GPS perdu", aucun état `gps_lost`.

```python
# engine.py:182–235 — process_location()
# Appelé à chaque nouvelle position GPS
# Si aucune nouvelle position n'arrive → la fonction n'est jamais appelée
# → Guardian reste dans son dernier état sans rien détecter
```

Il n'y a pas de watchdog qui vérifie "si aucune position reçue depuis X minutes → GPS perdu".

### IMPACT : 🟡 Moyen

En cas de perte GPS intérieure, Guardian pense que la dernière position connue est toujours valide. Il ne signale pas la perte.

### EFFORT : Moyen

Nécessite soit un watchdog backend (tâche périodique), soit un heartbeat côté client. Deux architectures possibles.

---

## RÈGLE 13 — Gestion réseau perdu

### STATUT : ❌ Absente (backend)

### PREUVE

La perte réseau est un événement côté client (`guardian.html` peut détecter la perte de WebSocket). Côté backend, aucune logique ne réagit à la déconnexion WebSocket :

```python
# engine.py:339–356 — register_ws / unregister_ws
def unregister_ws(self, session_id: str, ws) -> None:
    conns = self._ws_connections.get(session_id, [])
    if ws in conns:
        conns.remove(ws)
    # ← PAS D'ÉVÉNEMENT "réseau perdu" généré
    # ← PAS D'ALERTE "offline > 30 min"
```

### IMPACT : 🟡 Moyen

La Policy dit : "Perte réseau > 30 min → SMS informatif (pas alerte)." Ce comportement n'existe pas.

### EFFORT : Moyen

Nécessite un timestamp `last_ws_ping_at` et une tâche périodique backend.

---

## RÈGLE 14 — Caméra perdue

### STATUT : ❌ Absente (dans le moteur Guardian)

### PREUVE

Le moteur Guardian (`engine.py`) ne reçoit pas de données caméra directement. Les frames caméra passent par `/api/guardian/frame/:id` et le module `perception/`. L'engine GPS ne sait pas si la caméra fonctionne.

Il n'y a pas de signal `camera_lost` dans `_compute_risk()` ni dans les événements Guardian.

**Comportement actuel :** Si la caméra s'éteint, le moteur GPS continue normalement. Aucun event, aucun état.

### IMPACT : 🟢 Faible

La Policy V2 dit que la caméra coupée seule ne doit pas alerter. L'absence de gestion est donc partiellement correcte (pas de faux positif). Mais il manque un log informatif pour le profil HOME.

### EFFORT : Faible (log informatif seulement, pas d'alerte)

---

## RÈGLE 15 — Utilisateur silencieux (pas de réponse)

### STATUT : ⚠️ Partielle

### PREUVE

```python
# engine.py:529–544 — escalade si pas de réponse
if (session.alert_pending and session.verification_sent_at):
    elapsed = (now - ...).total_seconds()
    if elapsed > 120:  # ← 2 min au lieu de 10 min
        session.alert_level = AlertLevel.HIGH
        # Escalade directe, PAS de Niveau 3 intermédiaire
```

**Ce qui fonctionne :** La logique d'escalade existe. Si l'utilisateur ne répond pas, il y a bien une escalade.

**Ce qui manque :**
1. Timeout trop court (2 min vs 10 min)
2. Pas de deuxième vérification (Niveau 3)
3. Pas de grace period post-réponse

### IMPACT : 🔴 Critique

### EFFORT : Faible

---

## RÈGLE 16 — Utilisateur répond tardivement

### STATUT : ⚠️ Partielle

### PREUVE

```python
# engine.py:261–285 — register_verification_response(ok=True)
if ok:
    session.alert_pending = False
    session.alert_level = AlertLevel.LOW
    # ← Réinitialisation correcte de l'état
    # ← Mais PAS de SMS d'annulation si alerts_sent > 0
    # ← Pas de grace period
    return "OK — alerte annulée"
```

**Ce qui fonctionne :** L'état interne de Guardian est correctement réinitialisé.

**Ce qui manque :** Le SMS d'annulation aux contacts (critique) et la grace period.

### IMPACT : 🟠 Élevé (manque SMS annulation)

---

## RÈGLE 17 — Utilisateur répond "tout va bien"

### STATUT : ⚠️ Partielle (identique à Règle 16)

### PREUVE

Même code que Règle 16. État interne OK, SMS annulation absent, grace period absente.

### IMPACT : 🟠 Élevé

---

## RÈGLE 18 — Personne qui dort

### STATUT : ❌ Absente

### PREUVE

Découle directement de l'absence du Mode Nuit (Règle 1).

```python
# Simulation du comportement actuel à 23h30 :
# GPS fixe depuis 40 min → is_immobile = True
# _compute_risk() → signals["immobility"] = min(0.8, 0.4 + 0.4*(10/30)) = 0.53
# 0.53 >= 0.45 → AlertLevel.MEDIUM → vérification envoyée
# Utilisateur dort → pas de réponse → 2 min plus tard → HIGH → SMS
```

**Profil SENIOR :** Alerte certaine toutes les nuits après 30 minutes de sommeil.

**Profil BABY :**

```python
# engine.py:690 — _default_config(ProfileType.BABY)
ProfileType.BABY: {
    "immobility_threshold_minutes": 5,  # ← 5 MIN pour le bébé
    ...
}
# profiles.py:46 — INCOHÉRENCE
"immobility_threshold_minutes": 120,   # ← 120 min dans profiles.py
```

**Il y a une incohérence de fichier.** `_default_config()` dans engine.py retourne 5 min pour BABY, tandis que profiles.py déclare 120 min. `_default_config()` est la valeur réellement utilisée lors de `create_session()` (engine.py:155). Résultat : un bébé qui dort 6 minutes déclenche une alerte.

### IMPACT : 🔴 Critique

Alerte systématique chaque nuit. Double problème pour BABY (5 min au lieu de 120 min).

### EFFORT : Faible (mode nuit) + Faible (corriger threshold BABY)

---

## RÈGLE 19 — Personne immobile (tolérance profil)

### STATUT : ⚠️ Partielle

### PREUVE

```python
# engine.py:429–433 — signal immobility
threshold = session.config.get("immobility_threshold_minutes", 30)
signals["immobility"] = min(0.8, 0.4 + 0.4 * (immobile_min - threshold) / max(threshold, 1))
```

**Ce qui fonctionne :** Le seuil par profil est paramétrable. La formule proportionne le score.

**Ce qui ne va pas :**
- Seuil SENIOR : 30 min (code) vs 45 min (Policy V2). Divergence : Policy demande 45 min.
- Seuil BABY : 5 min (code) vs 120 min (Policy V2 + profiles.py).
- Seuil HOME : 120 min (code) vs 240 min (Policy V2). Divergence : Policy demande 240 min.
- Seuil DOG : 60 min (code engine) vs 90 min (profiles.py). Incohérence.

### Tableau des écarts

| Profil | Code (engine.py) | Policy V2 | Profiles.py | Verdict |
|---|---|---|---|---|
| SENIOR | 30 min | 45 min | 30 min | ⚠️ Écart policy |
| DOG | 60 min | 90 min | 90 min | ⚠️ Incohérence |
| BABY | **5 min** | 120 min | 120 min | ❌ Bug critique |
| HOME | 120 min | 240 min | 240 min | ⚠️ Écart policy |

### IMPACT : 🔴 Critique (BABY), 🟠 Élevé (autres)

### EFFORT : Faible (ajuster les constantes dans _default_config())

---

## RÈGLE 20 — Chute probable (speed_anomaly)

### STATUT : ❌ À supprimer (présent mais invalide)

### PREUVE

```python
# engine.py:444–447 — signal speed_anomaly
# Signal 4 : Vitesse anormale (chute détectée : vitesse soudaine puis zéro)
if profile == ProfileType.SENIOR and pos.speed is not None:
    if pos.speed > 5.0:  # > 18 km/h à pied = chute/impact
        signals["speed_anomaly"] = 0.7  # → directement HIGH

# engine.py:757–759 — description "impact/chute possible"
if "speed_anomaly" in signals:
    parts.append("impact/chute possible")
```

**Pourquoi c'est invalide :**
1. Le GPS smartphone échantillonne à 1 Hz. Une chute dure 0.3–0.5 secondes. Le GPS ne la capture pas.
2. Une vitesse GPS > 5 m/s (18 km/h) résulte typiquement d'une perturbation GPS (sortie de tunnel, bâtiment, perte/reprise signal), pas d'une chute.
3. Score 0.7 → AlertLevel.HIGH → SMS direct, sans vérification. Une perturbation GPS banale déclenche donc un SMS d'alerte immédiat.
4. La Policy V2 dit explicitement : "Ce signal doit être désactivé comme indicateur de chute."

### IMPACT : 🟠 Élevé

Faux positifs à chaque perturbation GPS. Zones urbaines denses particulièrement touchées.

### EFFORT : Faible (supprimer le signal ou le reclasser en DOUTE)

---

## SYNTHÈSE GLOBALE

| # | Règle | Statut | Impact | Effort |
|---|---|---|---|---|
| 1 | Mode nuit | ❌ Absente | 🔴 Critique | Faible |
| 2 | Safe zone | ✅ Implémentée | — | — |
| 3 | Timeout 10 min | ❌ Absente (2 min) | 🔴 Critique | Faible |
| 4 | Niveau 3 (2e vérification) | ❌ Absente | 🟠 Élevé | Moyen |
| 5 | SMS d'alerte | ⚠️ Partielle | 🟠 Élevé | Faible |
| 6 | SMS d'annulation | ❌ Absente | 🔴 Critique | Faible |
| 7 | SMS retour à la normale | ❌ Absente | 🟡 Moyen | Faible |
| 8 | Grace period 2h | ❌ Absente | 🟠 Élevé | Faible |
| 9 | Anti-spam progressif | ❌ Absente | 🔴 Critique | Faible |
| 10 | Limite 3 alertes/24h | ❌ Absente (compteur inutilisé) | 🔴 Critique | Faible |
| 11 | Backoff 30→60→120 min | ❌ Absente | 🔴 Critique | Faible |
| 12 | Gestion GPS perdu | ❌ Absente | 🟡 Moyen | Moyen |
| 13 | Gestion réseau perdu | ❌ Absente | 🟡 Moyen | Moyen |
| 14 | Caméra perdue | ❌ Absente | 🟢 Faible | Faible |
| 15 | Utilisateur silencieux | ⚠️ Partielle | 🔴 Critique | Faible |
| 16 | Utilisateur répond tardivement | ⚠️ Partielle | 🟠 Élevé | Faible |
| 17 | Utilisateur "tout va bien" | ⚠️ Partielle | 🟠 Élevé | Faible |
| 18 | Personne qui dort | ❌ Absente | 🔴 Critique | Faible |
| 19 | Seuils immobilité par profil | ⚠️ Partielle (BABY critique) | 🔴 Critique | Faible |
| 20 | Chute probable (speed_anomaly) | ❌ À supprimer | 🟠 Élevé | Faible |

**Score de conformité : 1/20 règles pleinement implémentées**

---

## RÉPONSE À LA QUESTION UNIQUE

> Si Guardian était déployé demain chez 100 familles, quelles règles manquantes risqueraient le plus de provoquer faux positifs, perte de confiance, SMS inutiles, désactivation ?

### Classement par urgence opérationnelle

**1. Mode nuit ABSENT → alerte chaque nuit (Règle 1)**
Toutes les familles qui ont un senior avec le profil par défaut reçoivent un SMS dès la première nuit. Abandon du service en moins d'une semaine pour la quasi-totalité.

**2. BABY threshold 5 min au lieu de 120 min (Règle 19)**
Les familles avec un bébé reçoivent une alerte toutes les 5 minutes de sieste. Service inutilisable. Avis négatif immédiat.

**3. Timeout 2 min au lieu de 10 min (Règle 3)**
Chaque utilisateur sous la douche, en cuisine, au téléphone reçoit un SMS d'alerte à ses proches. 2-3 faux positifs par semaine par utilisateur.

**4. Pas de SMS d'annulation (Règle 6)**
Après un faux positif, les contacts ne sont jamais informés que c'était une erreur. Ils rappellent, se déplacent, certains appellent le 15. Traumatisme et perte de confiance irréversible.

**5. Anti-spam illimité — compteur présent mais jamais vérifié (Règle 10)**
Une nuit d'immobilité sans mode nuit actif peut générer des dizaines de SMS. Facture Twilio incontrôlée. Contacts qui bloquent le numéro.

**6. Pas de grace period (Règle 8)**
Après avoir répondu "tout va bien", l'utilisateur peut recevoir une nouvelle vérification 5 minutes plus tard. Agacement extrême.

**7. speed_anomaly présent (Règle 20)**
À Paris ou dans toute zone urbaine dense, les perturbations GPS déclenchent des SMS HIGH. Un métro, un parking souterrain, un bâtiment avec mauvaise réception = faux positif immédiat.

---

**Conclusion de déploiement :**

Dans l'état actuel du code, Guardian déployé chez 100 familles générerait :
- Des alertes SMS chaque nuit pour les profils SENIOR (mode nuit absent)
- Des alertes toutes les 5 minutes pour les profils BABY (seuil erroné)
- Des faux positifs quotidiens par timeout de 2 min
- Des contacts paniqués sans SMS d'annulation
- Un abandon massif du service dans les 7 premiers jours

**Guardian ne doit pas être déployé en production sans implémenter au minimum les règles 1, 3, 6, 8, 9, 10, 19 (BABY).**

---

*Analyse statique — aucune ligne de code modifiée*
*Fichiers lus : engine.py, alerts.py, profiles.py*
*Conforme à GUARDIAN_BEHAVIOR_POLICY_V2.md*
