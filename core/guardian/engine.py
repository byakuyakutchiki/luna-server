"""
Luna Guardian - Moteur de surveillance géolocalisée

Pipeline : Position GPS → Analyse comportementale → RiskScore → Vérification → Alerte avec localisation
Remplace totalement la détection caméra (perception) par le GPS du smartphone.
"""
import json
import logging
import math
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

from .profiles import get_profile, format_profile_message

logger = logging.getLogger("luna.guardian")

# ─────────────────────────────────────────────
# ENUMS & VALUE OBJECTS
# ─────────────────────────────────────────────

class ProfileType(str, Enum):
    SENIOR  = "senior"
    DOG     = "dog"
    BABY    = "baby"
    HOME    = "home"


class AlertLevel(str, Enum):
    LOW      = "low"       # score < 0.45
    MEDIUM   = "medium"    # 0.45–0.75 → vérification vocale
    HIGH     = "high"      # > 0.75 → SMS contacts avec position
    CRITICAL = "critical"  # SOS manuel → alerte immédiate


@dataclass
class GeoPoint:
    lat: float
    lng: float
    accuracy: float = 15.0   # mètres
    speed: Optional[float] = None  # m/s, None si inconnu
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def distance_to(self, other: "GeoPoint") -> float:
        """Distance haversine en mètres"""
        return _haversine(self.lat, self.lng, other.lat, other.lng)


@dataclass
class SafeZone:
    name: str
    lat: float
    lng: float
    radius_m: float = 100.0

    def contains(self, point: GeoPoint) -> bool:
        return _haversine(self.lat, self.lng, point.lat, point.lng) <= self.radius_m


@dataclass
class RiskScore:
    total: float
    signals: Dict[str, float] = field(default_factory=dict)
    level: AlertLevel = AlertLevel.LOW
    description: str = ""

    def __post_init__(self):
        if self.total >= 0.9:
            self.level = AlertLevel.CRITICAL
        elif self.total >= 0.75:
            self.level = AlertLevel.HIGH
        elif self.total >= 0.45:
            self.level = AlertLevel.MEDIUM
        else:
            self.level = AlertLevel.LOW


@dataclass
class GuardianEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str = ""
    description: str = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    risk_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────

@dataclass
class GuardianSession:
    session_id: str
    tenant_id: int
    profile_type: ProfileType
    config: Dict[str, Any]

    # Etat courant
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_active: bool = True
    last_position: Optional[GeoPoint] = None
    last_moved_at: Optional[str] = None      # dernière position significativement différente
    is_immobile: bool = False
    immobile_since: Optional[str] = None
    in_safe_zone: bool = True
    current_zone: Optional[str] = None

    # Etat alerte
    alert_pending: bool = False
    alert_level: AlertLevel = AlertLevel.LOW
    verification_sent_at: Optional[str] = None
    last_alert_at: Optional[str] = None
    alerts_sent: int = 0


# ─────────────────────────────────────────────
# ENGINE
# ─────────────────────────────────────────────

class GuardianEngine:
    """
    Moteur principal Guardian.
    Reçoit des positions GPS, calcule un risque, déclenche vérifications et alertes.
    """

    # Seuils de mouvement : déplacement > MOVE_THRESHOLD considéré comme "en mouvement"
    MOVE_THRESHOLD_M = 10.0

    # Anti-spam alertes : délai minimum entre deux alertes
    ALERT_COOLDOWN_SEC = 300  # 5 min

    def __init__(self, redis_client, openai_client=None):
        self.rc = redis_client            # RedisClient sync (luna_web._redis_client)
        self.llm = openai_client          # openai.OpenAI sync, optionnel
        self._sessions: Dict[str, GuardianSession] = {}  # cache mémoire
        self._ws_connections: Dict[str, List] = {}       # session_id → [websockets]

    # ── Gestion sessions ──────────────────────────────

    def create_session(self, tenant_id: int, profile_type: str, config: dict) -> GuardianSession:
        sid = f"guard_{uuid.uuid4().hex[:10]}"
        profile = ProfileType(profile_type) if profile_type in ProfileType._value2member_map_ else ProfileType.SENIOR
        session = GuardianSession(
            session_id=sid,
            tenant_id=tenant_id,
            profile_type=profile,
            config={**_default_config(profile), **config},
        )
        self._sessions[sid] = session
        self._persist_session(session)
        logger.info(f"Guardian session {sid} created (profile={profile_type}, tenant={tenant_id})")
        return session

    def get_session(self, session_id: str) -> Optional[GuardianSession]:
        if session_id in self._sessions:
            return self._sessions[session_id]
        return self._load_session(session_id)

    def stop_session(self, session_id: str) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.is_active = False
        self._persist_session(session)
        self._sessions.pop(session_id, None)
        self._log_event(session_id, GuardianEvent(
            event_type="session_stopped",
            description="Session Guardian arrêtée",
        ))
        return True

    # ── Traitement position GPS ────────────────────────

    def process_location(self, session_id: str, lat: float, lng: float,
                          accuracy: float = 15.0, speed: Optional[float] = None
                          ) -> Tuple[RiskScore, List[GuardianEvent]]:
        """
        Point d'entrée principal : traite une nouvelle position GPS.
        Retourne (RiskScore, events générés).
        """
        session = self.get_session(session_id)
        if not session or not session.is_active:
            return RiskScore(0.0, description="Session inactive"), []

        new_pos = GeoPoint(lat=lat, lng=lng, accuracy=accuracy, speed=speed)
        events: List[GuardianEvent] = []
        now = datetime.utcnow()

        # 1. Enregistrer la position
        moved = self._update_position(session, new_pos, now)

        # 2. Vérifier les zones sûres
        zone_event = self._check_geofences(session, new_pos)
        if zone_event:
            events.append(zone_event)

        # 3. Calculer le score de risque
        risk = self._compute_risk(session, new_pos, now)

        # 4. Enregistrer l'événement position (périodique, pas à chaque update)
        if moved or len(events) > 0:
            events.append(GuardianEvent(
                event_type="location_update",
                description=f"Position mise à jour{' (mouvement)' if moved else ''}",
                lat=lat, lng=lng,
                risk_score=risk.total,
            ))

        # 5. Déclencher vérification / alerte si nécessaire
        alert_events = self._handle_risk(session, risk, new_pos, now)
        events.extend(alert_events)

        # 6. Persister
        self._persist_session(session)
        for evt in events:
            self._log_event(session_id, evt)

        # 7. Broadcast WebSocket
        self._broadcast(session_id, {
            "type": "update",
            "risk": risk.total,
            "level": risk.level.value,
            "lat": lat, "lng": lng,
            "signals": risk.signals,
        })

        return risk, events

    def trigger_sos(self, session_id: str) -> GuardianEvent:
        """SOS manuel — alerte immédiate, position envoyée aux contacts."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError("Session introuvable")

        event = GuardianEvent(
            event_type="sos_triggered",
            description="🆘 Bouton SOS activé par l'utilisateur",
            lat=session.last_position.lat if session.last_position else None,
            lng=session.last_position.lng if session.last_position else None,
            risk_score=1.0,
        )
        self._log_event(session_id, event)
        self._broadcast(session_id, {"type": "sos", "data": event.to_dict()})

        # Alerte directe sans vérification vocale
        session.alert_level = AlertLevel.CRITICAL
        session.alert_pending = False
        self._persist_session(session)

        logger.warning(f"SOS triggered on session {session_id}")
        return event

    def register_verification_response(self, session_id: str, ok: bool) -> str:
        """
        Enregistre la réponse de l'utilisateur à la vérification vocale.
        ok=True → tout va bien, annule l'alerte
        ok=False → confirme l'alerte
        """
        session = self.get_session(session_id)
        if not session:
            return "Session introuvable"
        if ok:
            session.alert_pending = False
            session.alert_level = AlertLevel.LOW
            session.verification_sent_at = None
            self._log_event(session_id, GuardianEvent(
                event_type="verified_ok",
                description="Utilisateur a confirmé qu'il va bien",
                lat=session.last_position.lat if session.last_position else None,
                lng=session.last_position.lng if session.last_position else None,
            ))
            self._persist_session(session)
            return "OK — alerte annulée"
        else:
            session.alert_pending = True
            self._persist_session(session)
            return "Alerte confirmée — contacts notifiés"

    def get_events(self, session_id: str, limit: int = 50) -> List[dict]:
        """Retourne les derniers événements de la session."""
        if not self.rc:
            return []
        key = f"luna:guardian:{session_id}:events"
        try:
            raw = self.rc.client.lrange(key, 0, limit - 1)
            events = []
            for r in raw:
                try:
                    events.append(json.loads(r))
                except Exception:
                    pass
            return events
        except Exception as e:
            logger.error(f"get_events error: {e}")
            return []

    def get_timeline(self, session_id: str) -> List[dict]:
        """Timeline intelligente : regroupe les events par période significative."""
        events = self.get_events(session_id, limit=200)
        timeline = []
        for evt in events:
            ts = evt.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    hour_label = dt.strftime("%H:%M")
                except Exception:
                    hour_label = ts[:16]
            else:
                hour_label = "?"
            timeline.append({
                "time": hour_label,
                "type": evt.get("event_type", ""),
                "description": evt.get("description", ""),
                "lat": evt.get("lat"),
                "lng": evt.get("lng"),
                "risk": evt.get("risk_score"),
            })
        return timeline

    def update_config(self, session_id: str, new_config: dict) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False
        session.config.update(new_config)
        self._persist_session(session)
        return True

    # ── WebSocket ────────────────────────────────────

    def register_ws(self, session_id: str, ws) -> None:
        self._ws_connections.setdefault(session_id, []).append(ws)

    def unregister_ws(self, session_id: str, ws) -> None:
        conns = self._ws_connections.get(session_id, [])
        if ws in conns:
            conns.remove(ws)

    def _broadcast(self, session_id: str, data: dict) -> None:
        conns = self._ws_connections.get(session_id, [])
        for ws in list(conns):
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(ws.send_json(data))
            except Exception:
                pass

    # ── Logique interne ───────────────────────────────

    def _update_position(self, session: GuardianSession, new_pos: GeoPoint, now: datetime) -> bool:
        """Met à jour la position, retourne True si déplacement significatif."""
        moved = False
        if session.last_position:
            dist = session.last_position.distance_to(new_pos)
            if dist > self.MOVE_THRESHOLD_M:
                session.last_moved_at = now.isoformat()
                session.is_immobile = False
                session.immobile_since = None
                moved = True
            else:
                # Pas de mouvement significatif — vérifier immobilité
                threshold_min = session.config.get("immobility_threshold_minutes", 30)
                if session.last_moved_at:
                    last_move = datetime.fromisoformat(session.last_moved_at)
                    elapsed = (now - last_move).total_seconds() / 60
                    if elapsed >= threshold_min and not session.is_immobile:
                        session.is_immobile = True
                        session.immobile_since = session.last_moved_at
        else:
            session.last_moved_at = now.isoformat()

        session.last_position = new_pos
        return moved

    def _check_geofences(self, session: GuardianSession, pos: GeoPoint) -> Optional[GuardianEvent]:
        """Vérifie les zones sûres, retourne un event si sortie détectée."""
        safe_zones_raw = session.config.get("safe_zones", [])
        if not safe_zones_raw:
            return None

        safe_zones = [SafeZone(**z) if isinstance(z, dict) else z for z in safe_zones_raw]
        in_any_zone = False
        current_zone = None

        for zone in safe_zones:
            if zone.contains(pos):
                in_any_zone = True
                current_zone = zone.name
                break

        was_in_zone = session.in_safe_zone
        session.in_safe_zone = in_any_zone
        session.current_zone = current_zone

        # Sortie de zone
        if was_in_zone and not in_any_zone:
            return GuardianEvent(
                event_type="geofence_exit",
                description="⚠️ Sortie de zone sûre détectée",
                lat=pos.lat, lng=pos.lng,
                risk_score=0.6,
            )
        # Retour en zone
        if not was_in_zone and in_any_zone:
            return GuardianEvent(
                event_type="geofence_enter",
                description=f"✅ Retour en zone : {current_zone}",
                lat=pos.lat, lng=pos.lng,
                risk_score=0.0,
            )
        return None

    def _compute_risk(self, session: GuardianSession, pos: GeoPoint, now: datetime) -> RiskScore:
        """Calcule le score de risque à partir des signaux comportementaux."""
        signals: Dict[str, float] = {}
        profile = session.profile_type

        # Signal 1 : Immobilité
        if session.is_immobile and session.immobile_since:
            immobile_min = (now - datetime.fromisoformat(session.immobile_since)).total_seconds() / 60
            threshold = session.config.get("immobility_threshold_minutes", 30)
            # Score proportionnel jusqu'à 2x le seuil
            signals["immobility"] = min(0.8, 0.4 + 0.4 * (immobile_min - threshold) / max(threshold, 1))

        # Signal 2 : Sortie de zone sûre
        if not session.in_safe_zone and session.config.get("safe_zones"):
            signals["geofence_exit"] = 0.6 if profile != ProfileType.HOME else 0.8

        # Signal 3 : Nuit + hors zone (entre 22h et 6h)
        hour = now.hour
        if (hour >= 22 or hour < 6) and not session.in_safe_zone:
            signals["night_anomaly"] = 0.5

        # Signal 4 : Vitesse anormale (chute détectée : vitesse soudaine puis zéro)
        if profile == ProfileType.SENIOR and pos.speed is not None:
            if pos.speed > 5.0:  # > 18 km/h à pied = chute/impact
                signals["speed_anomaly"] = 0.7

        # Signal 5 : Inactivité longue (> 2x threshold)
        if session.is_immobile and session.immobile_since:
            immobile_min = (now - datetime.fromisoformat(session.immobile_since)).total_seconds() / 60
            threshold = session.config.get("immobility_threshold_minutes", 30)
            if immobile_min > threshold * 2:
                signals["prolonged_immobility"] = 0.85

        # Calcul du score total (max pondéré, pas somme pour éviter faux positifs)
        if not signals:
            total = 0.0
            desc = "Situation normale"
        else:
            total = max(signals.values())
            # Bonus si plusieurs signaux concordants
            if len(signals) >= 2:
                total = min(1.0, total + 0.1)
            desc = _risk_description(signals, profile)

        return RiskScore(total=total, signals=signals, description=desc)

    def _handle_risk(self, session: GuardianSession, risk: RiskScore,
                     pos: GeoPoint, now: datetime) -> List[GuardianEvent]:
        """Déclenche vérification ou alerte selon le niveau de risque."""
        events = []

        if risk.level == AlertLevel.LOW:
            return events

        # Anti-spam
        if session.last_alert_at:
            elapsed = (now - datetime.fromisoformat(session.last_alert_at)).total_seconds()
            if elapsed < self.ALERT_COOLDOWN_SEC:
                return events

        if risk.level == AlertLevel.MEDIUM and not session.alert_pending:
            # Vérification vocale
            session.alert_pending = True
            session.verification_sent_at = now.isoformat()
            session.alert_level = AlertLevel.MEDIUM
            events.append(GuardianEvent(
                event_type="verification_needed",
                description=f"Vérification vocale déclenchée — {risk.description}",
                lat=pos.lat, lng=pos.lng,
                risk_score=risk.total,
                metadata={"signals": risk.signals, "message": _verification_message(session)},
            ))
            self._broadcast(session.session_id, {
                "type": "verification_needed",
                "message": _verification_message(session),
                "risk": risk.total,
            })

        elif risk.level in (AlertLevel.HIGH, AlertLevel.CRITICAL):
            # Alerte directe
            session.alert_pending = False
            session.last_alert_at = now.isoformat()
            session.alerts_sent += 1
            session.alert_level = risk.level
            location_url = f"https://maps.google.com/?q={pos.lat},{pos.lng}" if pos else None

            event = GuardianEvent(
                event_type="alert_triggered",
                description=f"🔔 Alerte {risk.level.value} — {risk.description}",
                lat=pos.lat, lng=pos.lng,
                risk_score=risk.total,
                metadata={
                    "signals": risk.signals,
                    "location_url": location_url,
                    "level": risk.level.value,
                },
            )
            events.append(event)
            self._broadcast(session.session_id, {
                "type": "alert",
                "data": event.to_dict(),
                "location_url": location_url,
            })
            logger.warning(f"Guardian ALERT [{risk.level.value}] session={session.session_id} score={risk.total:.2f}")

        # Vérification en attente depuis > 2 min → escalade
        if (session.alert_pending and session.verification_sent_at and
                risk.level >= AlertLevel.MEDIUM):
            elapsed = (now - datetime.fromisoformat(session.verification_sent_at)).total_seconds()
            if elapsed > 120:  # 2 min sans réponse
                session.alert_pending = False
                session.last_alert_at = now.isoformat()
                session.alert_level = AlertLevel.HIGH
                location_url = f"https://maps.google.com/?q={pos.lat},{pos.lng}" if pos else None
                esc_event = GuardianEvent(
                    event_type="alert_escalated",
                    description="⚠️ Pas de réponse à la vérification — alerte escaladée",
                    lat=pos.lat, lng=pos.lng,
                    risk_score=0.8,
                    metadata={"location_url": location_url, "no_response_seconds": int(elapsed)},
                )
                events.append(esc_event)

        return events

    # ── Persistance Redis ─────────────────────────────

    def _persist_session(self, session: GuardianSession) -> None:
        if not self.rc:
            return
        key = f"luna:{session.tenant_id}:guardian:{session.session_id}"
        data = {
            "session_id": session.session_id,
            "tenant_id": str(session.tenant_id),
            "profile_type": session.profile_type.value,
            "config": json.dumps(session.config, ensure_ascii=False),
            "started_at": session.started_at,
            "is_active": "1" if session.is_active else "0",
            "is_immobile": "1" if session.is_immobile else "0",
            "in_safe_zone": "1" if session.in_safe_zone else "0",
            "current_zone": session.current_zone or "",
            "alert_pending": "1" if session.alert_pending else "0",
            "alert_level": session.alert_level.value,
            "alerts_sent": str(session.alerts_sent),
        }
        if session.last_position:
            data["last_lat"] = str(session.last_position.lat)
            data["last_lng"] = str(session.last_position.lng)
            data["last_pos_ts"] = session.last_position.timestamp
        if session.last_moved_at:
            data["last_moved_at"] = session.last_moved_at
        if session.immobile_since:
            data["immobile_since"] = session.immobile_since
        if session.verification_sent_at:
            data["verification_sent_at"] = session.verification_sent_at
        if session.last_alert_at:
            data["last_alert_at"] = session.last_alert_at

        try:
            self.rc.client.hset(key, mapping=data)
            self.rc.client.expire(key, 86400 * 7)  # TTL 7j
            # Index des sessions actives du tenant
            idx_key = f"luna:{session.tenant_id}:guardian:sessions"
            if session.is_active:
                self.rc.client.sadd(idx_key, session.session_id)
            else:
                self.rc.client.srem(idx_key, session.session_id)
        except Exception as e:
            logger.error(f"Guardian persist error: {e}")

    def _load_session(self, session_id: str) -> Optional[GuardianSession]:
        if not self.rc:
            return None
        # Cherche dans tous les tenants (on n'a pas le tenant_id ici)
        try:
            keys = self.rc.client.keys(f"luna:*:guardian:{session_id}")
            if not keys:
                return None
            data = self.rc.client.hgetall(keys[0])
            if not data:
                return None
            pos = None
            if data.get("last_lat") and data.get("last_lng"):
                pos = GeoPoint(
                    lat=float(data["last_lat"]),
                    lng=float(data["last_lng"]),
                    timestamp=data.get("last_pos_ts", datetime.utcnow().isoformat()),
                )
            session = GuardianSession(
                session_id=session_id,
                tenant_id=int(data.get("tenant_id", 1)),
                profile_type=ProfileType(data.get("profile_type", "senior")),
                config=json.loads(data.get("config", "{}")),
                started_at=data.get("started_at", datetime.utcnow().isoformat()),
                is_active=data.get("is_active") == "1",
                last_position=pos,
                last_moved_at=data.get("last_moved_at") or None,
                is_immobile=data.get("is_immobile") == "1",
                immobile_since=data.get("immobile_since") or None,
                in_safe_zone=data.get("in_safe_zone", "1") == "1",
                current_zone=data.get("current_zone") or None,
                alert_pending=data.get("alert_pending") == "1",
                alert_level=AlertLevel(data.get("alert_level", "low")),
                verification_sent_at=data.get("verification_sent_at") or None,
                last_alert_at=data.get("last_alert_at") or None,
                alerts_sent=int(data.get("alerts_sent", 0)),
            )
            self._sessions[session_id] = session
            return session
        except Exception as e:
            logger.error(f"Guardian load session error: {e}")
            return None

    def _log_event(self, session_id: str, event: GuardianEvent) -> None:
        if not self.rc:
            return
        key = f"luna:guardian:{session_id}:events"
        try:
            self.rc.client.lpush(key, json.dumps(event.to_dict(), ensure_ascii=False))
            self.rc.client.ltrim(key, 0, 499)  # Max 500 events
            self.rc.client.expire(key, 86400 * 7)
        except Exception as e:
            logger.error(f"Guardian log event error: {e}")

    def get_active_sessions(self, tenant_id: int) -> List[str]:
        if not self.rc:
            return []
        try:
            idx_key = f"luna:{tenant_id}:guardian:sessions"
            return list(self.rc.client.smembers(idx_key))
        except Exception:
            return []


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distance haversine en mètres entre deux coordonnées GPS."""
    R = 6_371_000  # rayon Terre en mètres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _default_config(profile: ProfileType) -> dict:
    defaults = {
        ProfileType.SENIOR: {
            "immobility_threshold_minutes": 30,
            "night_mode": True,
            "dignity_mode": True,
            "safe_zones": [],
            "verification_enabled": True,
            "emergency_contacts": [],
            # auto_call_112 : non implémenté — Luna ne peut pas appeler le 112
        },
        ProfileType.DOG: {
            "immobility_threshold_minutes": 60,
            "safe_zones": [],
            "forbidden_zones": [],
            "verification_enabled": False,
            "emergency_contacts": [],
        },
        ProfileType.BABY: {
            "immobility_threshold_minutes": 5,
            "safe_zones": [],
            "night_monitoring": True,
            "verification_enabled": False,
            "emergency_contacts": [],
        },
        ProfileType.HOME: {
            "immobility_threshold_minutes": 120,
            "safe_zones": [],
            "armed_modes": ["away", "night"],
            "verification_enabled": True,
            "emergency_contacts": [],
            # auto_call_112 : non implémenté — Luna ne peut pas appeler le 112
        },
    }
    return defaults.get(profile, defaults[ProfileType.SENIOR])


def _verification_message(session: GuardianSession) -> str:
    profile = get_profile(session.profile_type.value)
    name = session.config.get("person_name") or "vous"
    return format_profile_message(profile["verification_message"], name=name)


def reverse_geocode(lat: float, lng: float, redis_client=None) -> str:
    """Convertit lat/lng en adresse lisible via Nominatim (cache Redis 24h)."""
    if redis_client:
        cache_key = f"luna:geocode:{lat:.4f}:{lng:.4f}"
        try:
            cached = redis_client.client.get(cache_key)
            if cached:
                return cached.decode() if isinstance(cached, bytes) else cached
        except Exception:
            pass
    try:
        import httpx
        url = (f"https://nominatim.openstreetmap.org/reverse"
               f"?format=json&lat={lat}&lon={lng}&zoom=18&addressdetails=1")
        resp = httpx.get(url, headers={"User-Agent": "LunaGuardian/1.0"}, timeout=4.0)
        data = resp.json()
        parts = []
        addr = data.get("address", {})
        for key in ("road", "house_number", "suburb", "city", "town", "village", "postcode"):
            if addr.get(key):
                parts.append(addr[key])
                if len(parts) >= 3:
                    break
        address = ", ".join(parts) if parts else data.get("display_name", f"{lat:.5f}, {lng:.5f}")
        address = address[:80]
        if redis_client:
            try:
                redis_client.client.setex(cache_key, 86400, address)
            except Exception:
                pass
        return address
    except Exception:
        return f"{lat:.5f}, {lng:.5f}"


def _risk_description(signals: Dict[str, float], profile: ProfileType) -> str:
    parts = []
    if "immobility" in signals or "prolonged_immobility" in signals:
        parts.append("immobilité prolongée")
    if "geofence_exit" in signals:
        parts.append("sortie de zone sûre")
    if "night_anomaly" in signals:
        parts.append("déplacement nocturne inhabituel")
    if "speed_anomaly" in signals:
        parts.append("impact/chute possible")
    return ", ".join(parts) if parts else "comportement inhabituel"


def get_profile_templates() -> Dict[str, dict]:
    """Retourne les templates de configuration par profil."""
    return {
        "senior": {
            "label": "Senior / Personne âgée",
            "description": "Surveillance immobilité, chutes, déplacements nocturnes",
            "icon": "👴",
            "default_config": _default_config(ProfileType.SENIOR),
            "signals": ["immobility", "geofence_exit", "night_anomaly", "speed_anomaly"],
        },
        "dog": {
            "label": "Animal de compagnie",
            "description": "Suivi GPS, zones autorisées/interdites",
            "icon": "🐕",
            "default_config": _default_config(ProfileType.DOG),
            "signals": ["geofence_exit", "immobility"],
        },
        "baby": {
            "label": "Bébé / Enfant",
            "description": "Surveillance zones, déplacements. Aucun diagnostic médical.",
            "icon": "👶",
            "default_config": _default_config(ProfileType.BABY),
            "signals": ["geofence_exit", "immobility"],
            "disclaimer": "Luna signale uniquement des anomalies de position. Consultez un médecin pour tout sujet de santé.",
        },
        "home": {
            "label": "Domicile / Sécurité",
            "description": "Surveillance périmètre, intrusions, absences",
            "icon": "🏠",
            "default_config": _default_config(ProfileType.HOME),
            "signals": ["geofence_exit", "night_anomaly"],
        },
    }
