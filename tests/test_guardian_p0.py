"""
Tests comportementaux Guardian P0 — Policy V2
Valide les 6 scénarios demandés dans la mission P0.
Aucun Redis requis — sessions en mémoire uniquement.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from core.guardian.engine import (
    GuardianEngine, GuardianSession, ProfileType, AlertLevel,
    GeoPoint, RiskScore, _default_config,
)
from core.guardian.alerts import build_sms_cancellation

PASS = "✅ PASS"
FAIL = "❌ FAIL"

results = []

def check(name, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, status, detail))
    print(f"  {status} {name}" + (f" — {detail}" if detail else ""))
    return condition


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_engine(sms_log=None):
    """Engine sans Redis, avec collecteur SMS optionnel."""
    sms_calls = sms_log if sms_log is not None else []
    def fake_sms(to, body, label=""):
        sms_calls.append({"to": to, "body": body, "label": label})
        return True, "ok"
    engine = GuardianEngine(redis_client=None, sms_send_fn=fake_sms)
    return engine, sms_calls


def make_session(profile="senior", hour_override=None, in_safe_zone=True):
    """Crée une session en mémoire sans Redis."""
    config = _default_config(ProfileType(profile))
    config["emergency_contacts"] = [{"phone": "+33600000001", "name": "Test Contact"}]
    config["person_name"] = "Marie"
    session = GuardianSession(
        session_id="test_session",
        tenant_id=1,
        profile_type=ProfileType(profile),
        config=config,
        in_safe_zone=in_safe_zone,
    )
    return session


def simulate_immobility(session, minutes, now=None):
    """Simule une immobilité de X minutes."""
    if now is None:
        now = datetime.utcnow()
    moved_at = now - timedelta(minutes=minutes + 1)
    session.is_immobile = True
    session.immobile_since = moved_at.isoformat()
    session.last_moved_at = moved_at.isoformat()
    return now


# ─────────────────────────────────────────────
# TEST 1 — Personne qui dort → aucune alerte
# ─────────────────────────────────────────────

print("\n=== TEST 1 : Personne qui dort ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Nuit : 23h30
now_night = datetime.now().replace(hour=23, minute=30, second=0)
simulate_immobility(session, minutes=60, now=now_night)
pos = GeoPoint(lat=48.8566, lng=2.3522)
risk = engine._compute_risk(session, pos, now_night)

check("Mode nuit actif → signal immobility absent",
      "immobility" not in risk.signals,
      f"signals={risk.signals}")
check("Mode nuit actif → signal prolonged_immobility absent",
      "prolonged_immobility" not in risk.signals,
      f"signals={risk.signals}")
check("Score risque = 0 (dormir en safe zone la nuit)",
      risk.total == 0.0,
      f"risk.total={risk.total}")
check("Niveau = LOW (pas d'alerte)",
      risk.level == AlertLevel.LOW,
      f"level={risk.level}")

# Vérifier que _handle_risk ne génère aucun event
events = engine._handle_risk(session, risk, pos, now_night)
check("Aucun événement généré pendant le sommeil",
      len(events) == 0,
      f"events={[e.event_type for e in events]}")


# ─────────────────────────────────────────────
# TEST 2 — Télévision 45 min → aucune alerte
# ─────────────────────────────────────────────

print("\n=== TEST 2 : Télévision 45 min (jour) ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Profil senior, seuil = 30 min, en safe zone, 20h (pas nuit)
# night_mode = True mais heure = 20h → pas en night_hours → night_mode_active = False
# → le signal immobility DOIT se déclencher car pas de mode nuit actif le soir
now_evening = datetime.now().replace(hour=20, minute=0, second=0)
simulate_immobility(session, minutes=45, now=now_evening)
risk = engine._compute_risk(session, pos, now_evening)

# 45 min > seuil 30 min → immobility signal présent (comportement correct)
# score = 0.4 + 0.4*(15/30) = 0.60 → MEDIUM → vérification vocale, PAS de SMS direct
check("Signal immobility présent à 45 min le soir (attendu)",
      "immobility" in risk.signals,
      f"signals={risk.signals}")
check("Niveau MEDIUM (vérification, pas SMS)",
      risk.level == AlertLevel.MEDIUM,
      f"level={risk.level}, score={risk.total:.2f}")

# _handle_risk → vérification vocale, pas de SMS
events = engine._handle_risk(session, risk, pos, now_evening)
check("Événement verification_needed (pas alert_triggered)",
      any(e.event_type == "verification_needed" for e in events),
      f"events={[e.event_type for e in events]}")
check("Aucun SMS envoyé (juste vérification in-app)",
      len(sms) == 0,
      f"sms_count={len(sms)}")


# ─────────────────────────────────────────────
# TEST 3 — Utilisateur ignore 3 min → aucun SMS
# ─────────────────────────────────────────────

print("\n=== TEST 3 : Utilisateur ignore 3 min (< 10 min) → aucun SMS ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Simuler vérification envoyée il y a 3 min
sent_at = datetime.utcnow() - timedelta(minutes=3)
session.alert_pending = True
session.verification_sent_at = sent_at.isoformat()
session.alert_level = AlertLevel.MEDIUM

risk = RiskScore(total=0.60, signals={"immobility": 0.60})
now = datetime.utcnow()
events = engine._handle_risk(session, risk, pos, now)

check("Aucune escalade après 3 min (timeout = 10 min)",
      not any(e.event_type == "alert_escalated" for e in events),
      f"events={[e.event_type for e in events]}")
check("Aucun SMS envoyé",
      len(sms) == 0,
      f"sms_count={len(sms)}")
check("alert_pending toujours True",
      session.alert_pending,
      f"alert_pending={session.alert_pending}")


# ─────────────────────────────────────────────
# TEST 4 — Utilisateur ignore 15 min → escalade
# ─────────────────────────────────────────────

print("\n=== TEST 4 : Utilisateur ignore 15 min → escalade ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Simuler vérification envoyée il y a 15 min
sent_at = datetime.utcnow() - timedelta(minutes=15)
session.alert_pending = True
session.verification_sent_at = sent_at.isoformat()
session.alert_level = AlertLevel.MEDIUM

risk = RiskScore(total=0.60, signals={"immobility": 0.60})
now = datetime.utcnow()
events = engine._handle_risk(session, risk, pos, now)

check("Escalade déclenchée après 15 min sans réponse",
      any(e.event_type == "alert_escalated" for e in events),
      f"events={[e.event_type for e in events]}")
check("alert_pending = False après escalade",
      not session.alert_pending,
      f"alert_pending={session.alert_pending}")
check("Niveau HIGH après escalade",
      session.alert_level == AlertLevel.HIGH,
      f"alert_level={session.alert_level}")
check("Compteur alertes incrémenté",
      session.alerts_sent == 1,
      f"alerts_sent={session.alerts_sent}")


# ─────────────────────────────────────────────
# TEST 5 — Utilisateur répond "tout va bien" → SMS annulation
# ─────────────────────────────────────────────

print("\n=== TEST 5 : Utilisateur répond 'tout va bien' → SMS annulation ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Simuler une alerte déjà envoyée
session.alerts_sent = 1
session.last_alert_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
session.alert_pending = True
engine._sessions["test_session"] = session

result = engine.register_verification_response("test_session", ok=True)

check("Réponse 'OK — alerte annulée'",
      "OK" in result,
      f"result={result}")
check("Grace period activée (grace_period_until défini)",
      session.grace_period_until is not None,
      f"grace_period_until={session.grace_period_until}")
check("Grace period = 2h dans le futur",
      session.grace_period_until is not None and
      datetime.fromisoformat(session.grace_period_until) > datetime.utcnow() + timedelta(hours=1, minutes=55),
      f"grace_period_until={session.grace_period_until}")
check("SMS d'annulation envoyé",
      len(sms) == 1,
      f"sms_count={len(sms)}")
if sms:
    check("Contenu SMS = fausse alerte",
          "fausse alerte" in sms[0]["body"].lower() or "Fausse alerte" in sms[0]["body"],
          f"body_preview={sms[0]['body'][:60]}")
check("alert_pending = False",
      not session.alert_pending,
      f"alert_pending={session.alert_pending}")
check("alert_level = LOW",
      session.alert_level == AlertLevel.LOW,
      f"alert_level={session.alert_level}")

# Vérifier que la grace period bloque les nouvelles alertes
risk_medium = RiskScore(total=0.60, signals={"immobility": 0.60})
events_after = engine._handle_risk(session, risk_medium, pos, datetime.utcnow())
check("Grace period bloque les nouvelles vérifications",
      len(events_after) == 0,
      f"events={[e.event_type for e in events_after]}")

# Test SMS annulation : build_sms_cancellation
cancel_msg = build_sms_cancellation("Marie", "14h32")
check("Format SMS annulation correct",
      "✅" in cancel_msg and "Fausse alerte" in cancel_msg,
      f"msg={cancel_msg[:80]}")


# ─────────────────────────────────────────────
# TEST 6 — Plus de 3 alertes → blocage anti-spam
# ─────────────────────────────────────────────

print("\n=== TEST 6 : Plus de 3 alertes → blocage ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=False)  # hors zone pour déclencher HIGH
session.config["safe_zones"] = [{"name": "Maison", "lat": 48.86, "lng": 2.35, "radius_m": 100}]

# Simuler 3 alertes déjà envoyées dans la fenêtre 24h
session.alerts_sent = 3
session.alerts_window_start = (datetime.utcnow() - timedelta(hours=2)).isoformat()
session.last_alert_at = (datetime.utcnow() - timedelta(hours=1)).isoformat()

risk_high = RiskScore(total=0.80, signals={"geofence_exit": 0.60, "night_anomaly": 0.50})
events = engine._handle_risk(session, risk_high, pos, datetime.utcnow())

check("Aucun événement (plafond 3/24h atteint)",
      len(events) == 0,
      f"events={[e.event_type for e in events]}")
check("Aucun SMS envoyé (bloqué par plafond)",
      len(sms) == 0,
      f"sms_count={len(sms)}")
check("Compteur toujours à 3 (non incrémenté)",
      session.alerts_sent == 3,
      f"alerts_sent={session.alerts_sent}")

# Vérifier que le backoff progressif fonctionne après 1 alerte
print("\n  --- Sous-test backoff progressif ---")
session2 = make_session(profile="senior", in_safe_zone=False)
session2.config["safe_zones"] = [{"name": "Maison", "lat": 48.86, "lng": 2.35, "radius_m": 100}]
session2.alerts_sent = 1
session2.alerts_window_start = datetime.utcnow().isoformat()
session2.last_alert_at = (datetime.utcnow() - timedelta(minutes=10)).isoformat()  # 10 min ago

events2 = engine._handle_risk(session2, risk_high, pos, datetime.utcnow())
check("Bloqué par backoff (10 min < 30 min après 1ère alerte)",
      len(events2) == 0,
      f"events={[e.event_type for e in events2]}")

session3 = make_session(profile="senior", in_safe_zone=False)
session3.config["safe_zones"] = [{"name": "Maison", "lat": 48.86, "lng": 2.35, "radius_m": 100}]
session3.alerts_sent = 1
session3.alerts_window_start = datetime.utcnow().isoformat()
session3.last_alert_at = (datetime.utcnow() - timedelta(minutes=35)).isoformat()  # 35 min ago

events3 = engine._handle_risk(session3, risk_high, pos, datetime.utcnow())
check("Autorisé après 35 min (> 30 min backoff 1ère alerte)",
      any(e.event_type == "alert_triggered" for e in events3),
      f"events={[e.event_type for e in events3]}")


# ─────────────────────────────────────────────
# TEST 7 — Session CRITICAL ancienne réinitialisée au démarrage
# ─────────────────────────────────────────────

print("\n=== TEST 7 : Session CRITICAL ancienne réinitialisée au démarrage ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)
# Simuler une alerte SOS vieille de 3h sans alerte pending
session.alert_level = AlertLevel.CRITICAL
session.alert_pending = False
session.last_alert_at = (datetime.utcnow() - timedelta(hours=3)).isoformat()
session.alerts_sent = 2
engine._sessions["test_session"] = session
# _load_session n'est pas appelée car la session est déjà en mémoire ;
# on appelle explicitement le garde-fou pour prouver le comportement.
engine._maybe_clear_stale_alert(session)

check("Alerte ancienne réinitialisée à LOW",
      session.alert_level == AlertLevel.LOW,
      f"alert_level={session.alert_level}")
check("last_alert_at effacé après réinitialisation",
      session.last_alert_at is None,
      f"last_alert_at={session.last_alert_at}")


# ─────────────────────────────────────────────
# TEST 8 — SOS avec même incident_id ne re-déclenche pas
# ─────────────────────────────────────────────

print("\n=== TEST 8 : SOS idempotent par incident_id ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)
session.last_position = GeoPoint(lat=48.8566, lng=2.3522)
engine._sessions["test_session"] = session

incident_id = "incident_test_42"
event1 = engine.trigger_sos("test_session", context="test", incident_id=incident_id)
sent1 = session.alerts_sent
event2 = engine.trigger_sos("test_session", context="test", incident_id=incident_id)

check("Premier SOS incrémente alerts_sent",
      sent1 == 1,
      f"alerts_sent={sent1}")
check("Deuxième SOS avec même incident_id ne réincrémente pas",
      session.alerts_sent == 1,
      f"alerts_sent={session.alerts_sent}")
check("Événement doublon marqué comme duplicate",
      event2.metadata.get("duplicate") is True,
      f"metadata={event2.metadata}")
check("Niveau reste CRITICAL",
      session.alert_level == AlertLevel.CRITICAL,
      f"alert_level={session.alert_level}")


# ─────────────────────────────────────────────
# RÉSUMÉ
# ─────────────────────────────────────────────

print("\n" + "="*60)
print("RÉSUMÉ DES TESTS")
print("="*60)
passes = sum(1 for _, s, _ in results if s == PASS)
fails = sum(1 for _, s, _ in results if s == FAIL)
print(f"Total : {len(results)} tests — {passes} ✅ PASS — {fails} ❌ FAIL")
if fails == 0:
    print("→ Tous les comportements P0 sont conformes à la Policy V2")
else:
    print("→ Des corrections sont nécessaires")
    for name, status, detail in results:
        if status == FAIL:
            print(f"  {FAIL} {name} — {detail}")

sys.exit(0 if fails == 0 else 1)
