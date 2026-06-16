# Guardian — Red Team Behavior Review
**Sprint B — Audit comportemental**
**Date : 15 juin 2026**
**Auteur : Claude (Red Team)**
**Périmètre : diagnostic et cassage des règles — AUCUNE MODIFICATION**

---

## Méthode

Lecture complète de :
- `core/guardian/engine.py` — moteur GPS, calcul risque, escalade
- `core/guardian/profiles.py` — profils, seuils, templates SMS
- `core/guardian/alerts.py` — construction et envoi des SMS
- `core/perception/analyzer.py` — analyse scène caméra
- `core/perception/detector.py` — prompt Vision, classifications
- `static/guardian.html` — interface, flux utilisateur

Le "GUARDIAN_BEHAVIOR_POLICY_v1.md" n'existe pas encore comme fichier séparé — les règles sont directement dans le code. Ce rapport audite les règles **telles qu'elles fonctionnent réellement**.

---

## Architecture du système d'alerte (résumé)

```
GPS → _compute_risk() → RiskScore
   └─ Signaux : immobility, geofence_exit, night_anomaly, speed_anomaly, prolonged_immobility

score < 0.45  → LOW    → rien
0.45–0.75     → MEDIUM → vérification vocale (prompt "tout va bien ?")
0.75–1.0      → HIGH   → SMS contacts avec lien Maps
1.0           → CRITICAL → SOS manuel → SMS immédiat

Pas de réponse vérification en 120s → escalade HIGH automatique → SMS
```

---

## SCÉNARIO 1 — Personne qui dort

### La règle actuelle (code)

```python
# engine.py:449–454
if session.is_immobile and session.immobile_since:
    immobile_min = (now - datetime.fromisoformat(session.immobile_since)).total_seconds() / 60
    threshold = session.config.get("immobility_threshold_minutes", 30)
    if immobile_min > threshold * 2:
        signals["prolonged_immobility"] = 0.85
```

Profil senior : `threshold = 30 min`. Au bout de **35 min d'immobilité** → MEDIUM → vérification vocale. Au bout de **60 min** → 0.85 → HIGH → **SMS aux contacts**.

### Verdict : ⛔ RISQUE

**Dormir = immobilité garantie.** Une personne qui se couche à 22h00 recevra une vérification vocale à 22h30. Si elle dort (pas de réponse), le timer de 2 min s'écoule → SMS envoyé à 22h32.

Le `night_anomaly` n'aggrave pas si la personne est en safe zone (`not session.in_safe_zone`), mais **l'immobility seule suffit**.

**Impact** : Les contacts reçoivent un SMS chaque nuit. Perte de confiance immédiate. Abandon du service en 3 jours.

**Ce qui manque** : Un flag `night_mode` existe dans la config (`"night_mode": True`) mais n'est **nulle part utilisé dans le code** du moteur. C'est une variable morte.

---

## SCÉNARIO 2 — Personne qui regarde la télévision immobile

### La règle actuelle

Même calcul que le sommeil. Assis immobile ≥ 35 min → MEDIUM.

```python
signals["immobility"] = min(0.8, 0.4 + 0.4 * (immobile_min - threshold) / max(threshold, 1))
# À 35 min : 0.4 + 0.4*(5/30) = 0.467 → MEDIUM
```

### Verdict : ⛔ RISQUE

**Regarder un film de 40 minutes déclenche une vérification vocale.** "Luna vous demande : tout va bien ?" pendant un polar du dimanche soir.

Il n'y a aucune distinction entre immobilité choisie (repos, lecture, TV) et immobilité subie (malaise). Guardian traite les deux identiquement.

**Impact** : faux positif humiliant, répété à chaque série. L'utilisateur désactive Guardian définitivement.

---

## SCÉNARIO 3 — Personne qui tombe puis se relève

### Côté GPS

```python
# engine.py:445–448
if profile == ProfileType.SENIOR and pos.speed is not None:
    if pos.speed > 5.0:  # > 18 km/h à pied = chute/impact
        signals["speed_anomaly"] = 0.7
```

`speed_anomaly = 0.7` → HIGH → **SMS direct** (pas de vérification intermédiaire).

### Côté caméra

```python
# analyzer.py:139–161
if person_on_floor:
    if floor_duration >= 300:   # 5 min → concern
    elif floor_duration >= 120: # 2 min → attention
else:
    self._floor_start = None  # reset si relevée
```

La personne se relève en 30 secondes → `_floor_start` remis à None → **pas d'anomalie caméra**.

### Verdict : ⛔ RISQUE DOUBLE

**GPS side** : Le GPS smartphone mesure une vitesse > 5 m/s dans deux cas : une vraie chute/impact ET une **perturbation GPS normale** (sortie d'un tunnel, bâtiment, signal retrouvé après perte). Les deux cas déclenchent `speed_anomaly = 0.7 → HIGH → SMS`. La personne qui sort du métro reçoit une alerte. La personne qui tombe dans sa cuisine ET se relève en 30 secondes reçoit aussi le SMS — alors qu'elle va bien.

**Pas de rétractation** : Une fois le SMS HIGH envoyé, il n'y a **aucun SMS d'annulation** si l'utilisateur se relève et appuie sur "Tout va bien". Les contacts restent en alerte.

**Vitesse GPS chute réelle** : Lors d'une vraie chute, la vitesse GPS n'atteint pas 5 m/s (18 km/h). Une chute libre depuis la position debout dure ~0.4 seconde et couvre ~0.8 m. Le GPS échantillonne toutes les secondes — il ne capture pas cet événement. Le `speed_anomaly` est **une métaphore scientifiquement incorrecte**.

---

## SCÉNARIO 4 — Caméra coupée

### La règle actuelle

Aucun signal Guardian déclenché si la caméra s'arrête. La boucle `_sendFrame()` s'arrête silencieusement.

```js
// guardian.html:1260
function _sendFrame(){
  if(!SID||(CAM_STATE!=='active'&&CAM_STATE!=='external')) return;
  // Si CAM_STATE devient 'inactive', boucle s'arrête sans event Guardian
```

### Verdict : ✅ VALIDÉ (avec nuance)

Ne pas alerter sur une caméra coupée est la **bonne décision par défaut**. Alerter systématiquement sur une caméra coupée serait un vecteur de faux positifs massifs (batterie, changement d'appli, poche).

**Nuance** : La caméra coupée intentionnellement pour éviter la détection (agression, intrusion) n'est pas signalée. Pour le profil `home` (surveillance domicile), une caméra qui se coupe pendant une session active DEVRAIT générer un event `info`. Mais pour le profil `senior`, c'est correct.

**Ce qui manque** : Distinction par profil. `home` → log info si cam coupée en session. `senior` → silence correct.

---

## SCÉNARIO 5 — Téléphone retourné

### Cascade de signaux déclenchés

1. Caméra voit le sol : `persons_count = 0`
2. Si quelqu'un était visible → event `PERSON_LEFT` (info, pas d'alerte)
3. Après 1h sans personne visible → `EXTENDED_ABSENCE` (attention caméra)
4. GPS : position fixe → immobility après 30 min → MEDIUM

### Verdict : ⛔ RISQUE

**Un téléphone retourné sur une table combine deux signaux indépendants** qui peuvent pousser le score à HIGH :

- `immobility (0.47)` + `bonus 2 signaux (+0.1)` = 0.57 → MEDIUM puis escalade
- Si prolongée : `prolonged_immobility (0.85)` → HIGH → SMS

La personne est simplement à table, téléphone retourné pour ne pas être dérangée.

**Aggravant** : Le `EXTENDED_ABSENCE` côté caméra est stocké dans Redis mais n'influence pas directement le `RiskScore` GPS (les deux systèmes sont découplés). Cependant, `perception_concern` peut être loggé et broadcasté via WebSocket.

---

## SCÉNARIO 6 — Animal dans le champ de la caméra

### Prompt Vision

```python
# detector.py:65
"- Compte uniquement les personnes clairement visibles"
"- Objets pertinents: meubles, animaux, electromenager, nourriture"
```

Un chat ou chien est correctement classifié en objet, pas en personne.

### Verdict : ✅ VALIDÉ (avec réserve)

Les animaux ne déclenchent pas de faux positif "personne présente" en conditions normales.

**Réserve** : GPT-4o-mini analyse des frames JPEG 320×240 à 65% de qualité. Sur une frame dégradée, un chien couché peut être mal interprété comme `lying_floor` par le modèle si la consigne n'est pas suffisamment stricte. Risque faible mais non nul.

**Profil DOG spécifique** : Si le téléphone est attaché à l'animal (tracking GPS), la vitesse du chien au sprint (~8 m/s) dépasse le seuil `speed_anomaly > 5.0`. Mais le profil DOG n'a pas `speed_anomaly` dans son calcul (`ProfileType.SENIOR` uniquement). ✅

---

## SCÉNARIO 7 — Utilisateur qui ignore les messages

### La règle actuelle

```python
# engine.py:529–543
if (session.alert_pending and session.verification_sent_at and
        risk.level >= AlertLevel.MEDIUM):
    elapsed = (now - datetime.fromisoformat(session.verification_sent_at)).total_seconds()
    if elapsed > 120:  # 2 min sans réponse
        session.alert_level = AlertLevel.HIGH
        # → SMS aux contacts
```

### Verdict : ⛔ RISQUE CRITIQUE

**2 minutes, c'est dramatiquement insuffisant.**

Scénarios où 2 minutes sans réponse est normal et anodin :
- Utilisateur dans la douche (10–20 min)
- Utilisateur au téléphone
- Utilisateur qui conduit (ne voit pas le message)
- Utilisateur qui fait la cuisine (mains mouillées)
- Utilisateur qui dort (voir scénario 1)
- Utilisateur âgé qui ne regarde pas son téléphone souvent

Dans tous ces cas, les contacts reçoivent un **SMS d'alerte réel** dans les 2 minutes suivant une vérification. C'est presque systématiquement une fausse alarme.

**Conséquence produit** : Si un contact reçoit 3 fausses alarmes par semaine, il **arrête de répondre**. Quand la vraie urgence arrive, l'alerte est ignorée. C'est l'effet "loup" — le risque le plus grave d'un système Guardian.

---

## SCÉNARIO 8 — Utilisateur qui répond tardivement

### La règle actuelle

```python
# engine.py:261–285
def register_verification_response(self, session_id: str, ok: bool) -> str:
    if ok:
        session.alert_pending = False
        session.alert_level = AlertLevel.LOW
        # → log "verified_ok"
        return "OK — alerte annulée"
```

Le SMS d'escalade a déjà été envoyé. La réponse OK de l'utilisateur annule l'état interne Guardian mais **n'envoie aucun SMS de désescalade aux contacts**.

### Verdict : ⛔ RISQUE

Les contacts sont en alerte. Ils peuvent appeler le SAMU (15), appeler la police (17), se déplacer physiquement. Rien dans le système ne leur dit "fausse alarme, tout va bien". L'utilisateur lui-même ne peut pas annuler l'alerte auprès des contacts depuis l'interface.

**Impact légal** : Un contact qui appelle le 112 pour une fausse alarme fait intervenir les secours inutilement. En France, un faux appel au 112 peut être sanctionné (art. 322-14 CP : 2 ans + 30 000€). Si l'utilisateur a déclenché l'alerte Guardian sans urgence réelle, la responsabilité est complexe.

---

## PROBLÈMES SUPPLÉMENTAIRES TROUVÉS

### A — `night_mode` est une variable morte

```python
# profiles.py:25
"night_mode": True,
```

```python
# engine.py — ABSENT
# Aucune occurrence de night_mode dans _compute_risk()
```

Le `night_mode` est déclaré dans la config par défaut senior mais **jamais lu dans le moteur**. C'est un dead code qui donne une fausse impression de protection nocturne.

### B — Anti-spam insuffisant

```python
ALERT_COOLDOWN_SEC = 300  # 5 min
```

Le cooldown de 5 minutes s'applique entre deux alertes HIGH. Mais si la condition persiste (personne immobile depuis 2h), une nouvelle alerte est envoyée toutes les 5 minutes. En **8h de sommeil**, cela peut générer ~96 SMS.

Le code ne comporte pas de plafond absolu d'alertes par session ni de backoff progressif.

### C — `speed_anomaly` GPS est scientifiquement inexact

La documentation interne dit "chute/impact possible" pour `speed > 5 m/s`. Mais :
- Une vraie chute humaine dure 0.3–0.5s → GPS (1 Hz) ne la capte pas
- La vitesse GPS peut paraître > 5 m/s lors de perturbations du signal (zone urbaine dense, passage d'un bâtiment)
- Cela classe un bug GPS comme "chute"

Le signal `speed_anomaly` est un **faux proxy** pour la détection de chute.

### D — Nominatim en usage commercial

```python
# engine.py:727
url = "https://nominatim.openstreetmap.org/reverse?..."
headers = {"User-Agent": "LunaGuardian/1.0"}
```

Les [Terms of Use Nominatim](https://nominatim.org/release-docs/latest/api/Overview/#terms-of-use) interdisent l'usage commercial intensif sans contribution. Luna est un service payant. Chaque alerte envoie une requête Nominatim. **Violation potentielle des CGU Nominatim.**

De plus, les coordonnées GPS exactes de l'utilisateur sont transmises à un serveur tiers (OpenStreetMap Foundation) sans mention explicite dans la politique RGPD.

### E — Consentement contacts RGPD

Les SMS d'alerte envoient la **position GPS précise** d'un utilisateur à ses contacts. Ces contacts :
- N'ont pas consenti à recevoir leurs données traitées par Luna
- Reçoivent un lien Google Maps avec les coordonnées exactes de la personne surveillée
- Ne peuvent pas exercer leurs droits RGPD (accès, effacement) car ils ne sont pas utilisateurs Luna

**Article 13 RGPD** : l'information doit être donnée à la personne dont les données sont traitées. Ici les contacts reçoivent des données sur l'utilisateur, mais l'utilisateur n'a pas fourni le consentement des contacts pour recevoir sa position.

### F — Pas de route DELETE / droit à l'oubli

Aucune route `DELETE /api/guardian/session/:id` ou `DELETE /api/guardian/data/:tenant_id` n'existe dans le code. Le TTL Redis de 7 jours est la seule "suppression". Un utilisateur qui demande l'effacement de ses données Guardian n'a aucun mécanisme self-service.

### G — Profil BABY seuil 5 min

```python
# profiles.py (moteur engine.py)
ProfileType.BABY: {
    "immobility_threshold_minutes": 5,
```

Un bébé de 5 mois dort 16h par jour. Le seuil de 5 minutes d'immobilité déclenche une alerte dès la première sieste. Les parents recevraient des alertes toutes les 5 minutes. C'est inutilisable en l'état.

**Note** : le profil `baby` dans `profiles.py` dit `120 min` mais `_default_config` dans `engine.py` dit `5 min`. **Incohérence entre les deux fichiers.**

---

## SYNTHÈSE PAR RÈGLE

| # | Scénario | Verdict | Cause principale |
|---|---|---|---|
| 1 | Personne qui dort | ⛔ RISQUE | threshold 30 min, night_mode dead code |
| 2 | Regarde la TV immobile | ⛔ RISQUE | même signal, aucune distinction intention |
| 3 | Tombe puis se relève | ⛔ RISQUE | SMS HIGH sans annulation, speed_anomaly proxy faux |
| 4 | Caméra coupée | ✅ VALIDÉ | silence correct (nuance profil home) |
| 5 | Téléphone retourné | ⛔ RISQUE | cascade immobility + absence caméra |
| 6 | Animal dans le champ | ✅ VALIDÉ | prompt Vision correct, profil DOG OK |
| 7 | Utilisateur ignore les messages | ⛔ RISQUE CRITIQUE | 2 min = trop court, effet "loup" |
| 8 | Répond tardivement | ⛔ RISQUE | pas de SMS annulation aux contacts |

---

## CORRECTIONS INDISPENSABLES

Classées par impact. Rien d'autre.

### C1 — Timeout vérification : 2 min → 10 min

```python
# engine.py:532 — ACTUEL
if elapsed > 120:  # 2 min sans réponse

# DEVRAIT ÊTRE
if elapsed > 600:  # 10 min sans réponse
```

**Priorité : BLOQUANTE.** C'est la cause racine des fausses alarmes les plus fréquentes.

### C2 — Suspendre immobilité entre 23h et 7h si en safe zone

```python
# engine.py:_compute_risk() — AJOUTER
hour = now.hour
in_night_hours = (hour >= 23 or hour < 7)
if in_night_hours and session.in_safe_zone and session.config.get("night_mode", True):
    signals.pop("immobility", None)
    signals.pop("prolonged_immobility", None)
```

**Priorité : BLOQUANTE.** Dormir dans son lit ne doit jamais déclencher d'alerte.

### C3 — SMS d'annulation si réponse OK après escalade

Quand `register_verification_response(ok=True)` est appelé APRÈS qu'un SMS a été envoyé (`session.alerts_sent > 0`), envoyer un SMS de désescalade aux contacts.

```
"✅ Luna Guardian : fausse alarme confirmée. {name} va bien.
Répondu le {heure}. Aucune intervention nécessaire."
```

**Priorité : HAUTE.** Sans cela, chaque fausse alarme provoque une intervention inutile.

### C4 — Corriger l'incohérence BABY threshold

`profiles.py` dit 120 min, `engine.py` dit 5 min. Choisir un seul endroit (engine.py) et appliquer **120 min** pour BABY, avec note explicite "sieste normale non détectée".

### C5 — Anti-spam progressif

```python
# Backoff : 5 min → 30 min → 2h → stop
ALERT_BACKOFF = [300, 1800, 7200]
# Plafonner à 5 SMS par session par 24h
MAX_ALERTS_PER_SESSION = 5
```

Sans backoff, une immobilité prolongée génère des dizaines de SMS.

### C6 — Supprimer `speed_anomaly` ou le sécuriser

Soit supprimer le signal (GPS ne détecte pas les chutes), soit exiger **deux points consécutifs** avec vitesse anormale avant de l'activer, et descendre le score à 0.4 (MEDIUM, pas HIGH).

---

## SCORE FINAL

```
╔═══════════════════════════════════╗
║   SCORE GUARDIAN : À AMÉLIORER   ║
╚═══════════════════════════════════╝
```

**Pourquoi pas DANGEREUX :**
- Vérification vocale avant SMS (intention correcte)
- Pas d'appel 112 automatique (`auto_call_112: non implémenté`)
- Anti-spam 5 min présent (insuffisant mais existant)
- Jamais de diagnostic médical dans les messages
- TTL Redis 7j (durée courte)

**Pourquoi pas ROBUSTE :**
- Scénarios 1, 2, 5, 7 génèrent des fausses alarmes quasi-certaines en usage quotidien
- `night_mode` déclaré mais jamais appliqué
- Timeout 2 min irréaliste
- Pas de SMS d'annulation
- `speed_anomaly` proxy inexact
- Incohérence baby threshold

**Pour atteindre ROBUSTE :** implémenter C1 et C2 (les deux urgents). Sans ces deux corrections, Guardian enverra des SMS à des proches toutes les nuits. Les corrections C3–C6 stabilisent le reste.

---

*Méthode : Red Team — lecture code source uniquement, aucune modification*
*Fichiers lus : engine.py, profiles.py, alerts.py, analyzer.py, detector.py, guardian.html*
*Aucun SMS envoyé. Aucun GPS déclenché. Aucune caméra activée.*
