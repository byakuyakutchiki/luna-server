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
from core.guardian.alerts import build_sms_cancellation, send_guardian_alerts

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

# Profil senior, seuil = 45 min, en safe zone, 20h (pas nuit)
# night_mode = True mais heure = 20h → pas en night_hours → night_mode_active = False
# → le signal immobility DOIT se déclencher car pas de mode nuit actif le soir
now_evening = datetime.now().replace(hour=20, minute=0, second=0)
simulate_immobility(session, minutes=60, now=now_evening)
risk = engine._compute_risk(session, pos, now_evening)

# 60 min > seuil 45 min → immobility signal présent
# score = 0.4 + 0.4*(15/45) ≈ 0.53 → MEDIUM → vérification vocale, PAS de SMS direct
check("Signal immobility présent à 60 min le soir (attendu)",
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
session.verification_attempt = 1
session.alert_level = AlertLevel.MEDIUM

risk = RiskScore(total=0.60, signals={"immobility": 0.60})
now = datetime.utcnow()
events = engine._handle_risk(session, risk, pos, now)

check("Aucune escalade après 3 min (timeout = 10 min)",
      not any(e.event_type == "alert_escalated" for e in events),
      f"events={[e.event_type for e in events]}")
check("Aucune 2e vérification après 3 min",
      not any(e.event_type == "verification_needed" for e in events),
      f"events={[e.event_type for e in events]}")
check("Aucun SMS envoyé",
      len(sms) == 0,
      f"sms_count={len(sms)}")
check("alert_pending toujours True",
      session.alert_pending,
      f"alert_pending={session.alert_pending}")


# ─────────────────────────────────────────────
# TEST 4 — Niveau 3 : utilisateur ignore 12 min → 2e vérification
# ─────────────────────────────────────────────

print("\n=== TEST 4 : Utilisateur ignore 12 min → 2e vérification (Niveau 3) ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Simuler première vérification envoyée il y a 12 min
sent_at = datetime.utcnow() - timedelta(minutes=12)
session.alert_pending = True
session.verification_sent_at = sent_at.isoformat()
session.verification_attempt = 1
session.alert_level = AlertLevel.MEDIUM

risk = RiskScore(total=0.60, signals={"immobility": 0.60})
now = datetime.utcnow()
events = engine._handle_risk(session, risk, pos, now)

check("2e vérification déclenchée après 10 min sans réponse",
      any(e.event_type == "verification_needed" for e in events),
      f"events={[e.event_type for e in events]}")
check("attempt=2 sur la 2e vérification",
      any(e.event_type == "verification_needed" and e.metadata.get("attempt") == 2 for e in events),
      f"events={[(e.event_type, e.metadata) for e in events]}")
check("alert_pending toujours True (attente 2e réponse)",
      session.alert_pending,
      f"alert_pending={session.alert_pending}")
check("verification_attempt = 2",
      session.verification_attempt == 2,
      f"verification_attempt={session.verification_attempt}")
check("Aucun SMS envoyé au Niveau 3",
      len(sms) == 0,
      f"sms_count={len(sms)}")


# ─────────────────────────────────────────────
# TEST 4b — Utilisateur ignore 16 min → escalade Niveau 4
# ─────────────────────────────────────────────

print("\n=== TEST 4b : Utilisateur ignore 16 min → escalade Niveau 4 ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)

# Simuler 2e vérification envoyée il y a 6 min (16 min après la 1re)
sent_at = datetime.utcnow() - timedelta(minutes=6)
session.alert_pending = True
session.verification_sent_at = sent_at.isoformat()
session.verification_attempt = 2
session.alert_level = AlertLevel.MEDIUM

risk = RiskScore(total=0.60, signals={"immobility": 0.60})
now = datetime.utcnow()
events = engine._handle_risk(session, risk, pos, now)

check("Escalade déclenchée après 5 min sans réponse à la 2e vérification",
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

# Simuler une alerte déjà envoyée avec vérification en cours
session.alerts_sent = 1
session.last_alert_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
session.alert_pending = True
session.verification_attempt = 1
engine._sessions["test_session"] = session

result = engine.register_verification_response("test_session", ok=True)

check("Réponse 'OK — alerte annulée'",
      "OK" in result,
      f"result={result}")
check("verification_attempt réinitialisé à 0",
      session.verification_attempt == 0,
      f"verification_attempt={session.verification_attempt}")
check("Grace period activée (grace_period_until défini)",
      session.grace_period_until is not None,
      f"grace_period_until={session.grace_period_until}")
check("Grace period = 30 min dans le futur",
      session.grace_period_until is not None and
      datetime.fromisoformat(session.grace_period_until) > datetime.utcnow() + timedelta(minutes=25) and
      datetime.fromisoformat(session.grace_period_until) < datetime.utcnow() + timedelta(minutes=35),
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
# TEST 7 — Check-in caméra manqué : cycle Niveau 3 → Niveau 4
# ─────────────────────────────────────────────

print("\n=== TEST 7 : Check-in caméra manqué ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)
session.alert_pending = True
session.verification_attempt = 1
session.verification_sent_at = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
engine._sessions["test_session"] = session

# 1re vérification caméra manquée → Niveau 3 (2e vérification)
result = engine.handle_checkin_missed("test_session")
check("1re vérif caméra manquée → Niveau 3",
      result.get("status") == "level3",
      f"status={result.get('status')}")
check("Niveau 3 : pas de SMS",
      result.get("alerts_sent") == 0,
      f"alerts_sent={result.get('alerts_sent')}")
check("verification_attempt = 2 après Niveau 3",
      session.verification_attempt == 2,
      f"verification_attempt={session.verification_attempt}")

# 2e vérification caméra manquée → Niveau 4 (SMS)
result = engine.handle_checkin_missed("test_session")
check("2e vérif caméra manquée → Niveau 4",
      result.get("status") == "level4",
      f"status={result.get('status')}")
check("Niveau 4 : SMS envoyé",
      result.get("alerts_sent") == 1,
      f"alerts_sent={result.get('alerts_sent')}")
check("verification_attempt réinitialisé à 0",
      session.verification_attempt == 0,
      f"verification_attempt={session.verification_attempt}")


# ─────────────────────────────────────────────
# TEST 8 — Coupe-circuit SMS Guardian (GUARDIAN_SMS_ENABLED=false)
# ─────────────────────────────────────────────

print("\n=== TEST 8 : Coupe-circuit SMS Guardian ===")


def fake_sms_guardian_blocked(to, body, label=""):
    """Simule _tracked_sms_send quand GUARDIAN_SMS_ENABLED=false."""
    return True, {"sid": "DISABLED", "guardian_sms_disabled": True, "blocked": True}


result = send_guardian_alerts(
    sms_send_fn=fake_sms_guardian_blocked,
    contacts=[{"phone": "+33600000001", "name": "Marie"}],
    person_name="Marie",
    description="Pas de réponse au contrôle Guardian",
    lat=48.8566,
    lng=2.3522,
    alert_level="high",
    profile_type="senior",
)

check("SMS Guardian bloqué compté dans 'blocked'",
      len(result.get("blocked", [])) == 1 and len(result.get("sent", [])) == 0,
      f"blocked={result.get('blocked')}, sent={result.get('sent')}")
check("Aucun SMS Guardian marqué comme envoyé quand il est bloqué",
      len(result.get("sent", [])) == 0,
      f"sent={result.get('sent')}")


# ─────────────────────────────────────────────
# TEST 9 — Chute : respect du plafond 3 alertes / 24h
# ─────────────────────────────────────────────

print("\n=== TEST 9 : Chute respecte le plafond 3 alertes/24h ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)
session.alerts_sent = 3
session.alerts_window_start = (datetime.utcnow() - timedelta(hours=1)).isoformat()
engine._sessions["test_session"] = session

event = engine.trigger_fall("test_session", peak_g=2.5)
check("trigger_fall bloque l'alerte quand plafond atteint",
      event.metadata.get("alert_blocked") is True,
      f"metadata={event.metadata}")
check("Compteur reste à 3 après chute bloquée",
      session.alerts_sent == 3,
      f"alerts_sent={session.alerts_sent}")

# Fenêtre réinitialisée : alerte autorisée
session2 = make_session(profile="senior", in_safe_zone=True)
session2.alerts_sent = 3
session2.alerts_window_start = (datetime.utcnow() - timedelta(hours=25)).isoformat()
engine2, sms2 = make_engine()
engine2._sessions["test_session2"] = session2
event2 = engine2.trigger_fall("test_session2", peak_g=2.5)
check("trigger_fall autorise l'alerte apres 24h (fenêtre reset)",
      event2.metadata.get("alert_blocked") is not True and session2.alerts_sent == 1,
      f"metadata={event2.metadata}, alerts_sent={session2.alerts_sent}")


# ─────────────────────────────────────────────
# TEST 10 — SOS incrémente le compteur d'alertes
# ─────────────────────────────────────────────

print("\n=== TEST 10 : SOS incrémente alerts_sent ===")
engine, sms = make_engine()
session = make_session(profile="senior", in_safe_zone=True)
engine._sessions["test_session"] = session

event = engine.trigger_sos("test_session")
check("trigger_sos incrémente alerts_sent à 1",
      session.alerts_sent == 1,
      f"alerts_sent={session.alerts_sent}")
check("trigger_sos met à jour last_alert_at",
      session.last_alert_at is not None,
      f"last_alert_at={session.last_alert_at}")
check("trigger_sos niveau CRITICAL",
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
