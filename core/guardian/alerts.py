"""
Luna Guardian - Escalade des alertes

Quand le risque est élevé :
  1. Vérification vocale (push WebSocket)
  2. Si pas de réponse (2 min) → SMS aux contacts de confiance avec lien Maps précis
  3. Contacts peuvent intervenir eux-mêmes ou appeler le 112
  4. auto_call_112 : NON IMPLÉMENTÉ — Luna ne peut pas appeler le 112 directement.
     Le SMS invite les contacts à appeler le 112 eux-mêmes.

RGPD : Les positions GPS sont stockées 7 jours en Redis (TTL), jamais en base.
"""
import logging
from typing import Optional, List, Dict

logger = logging.getLogger("luna.guardian.alerts")


def build_sms_alert(
    person_name: str,
    description: str,
    lat: Optional[float],
    lng: Optional[float],
    alert_level: str,
    profile_type: str,
    address: Optional[str] = None,
    redis_client=None,
) -> str:
    """Construit le SMS d'alerte avec adresse humaine et lien Maps."""
    from .profiles import get_profile, format_profile_message

    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else None

    # Résolution adresse si non fournie
    if not address and lat and lng:
        try:
            from .engine import reverse_geocode
            address = reverse_geocode(lat, lng, redis_client)
        except Exception:
            address = maps_link

    profile = get_profile(profile_type)
    level_emoji = "🆘" if alert_level == "critical" else "⚠️"

    if alert_level == "critical":
        template = profile.get("sos_message", "{name} — alerte ! {maps_link}")
    elif alert_level == "high":
        template = profile.get("immobility_alert", "{name} — {duration}. {address}")
    else:
        template = profile.get("geofence_alert", "{name} hors zone. {address}")

    body = format_profile_message(
        template,
        name=person_name or "Utilisateur",
        duration=description,
        address=address or "position inconnue",
        maps_link=maps_link or "position non disponible",
    )

    footer = f"\n📍 {address}" if address and maps_link and address != maps_link else ""
    if maps_link and maps_link not in body:
        footer += f"\n🗺️ {maps_link}"

    footer += "\n\nRendez-vous sur place si besoin, ou appelez le 15/112 en urgence.\nRépondez OUI si vous intervenez."

    return (f"{level_emoji} Luna Guardian\n{body}{footer}")[:320]


def send_guardian_alerts(
    sms_send_fn,              # callable(to, body, label) → (bool, details)
    contacts: List[Dict],     # [{"phone": "+33...", "name": "..."}]
    person_name: str,
    description: str,
    lat: Optional[float],
    lng: Optional[float],
    alert_level: str,
    profile_type: str,
    auto_call_112: bool = False,
) -> Dict:
    """
    Envoie les alertes SMS aux contacts de confiance.
    Retourne un résumé des envois.
    """
    results = {"sent": [], "failed": [], "call_112_attempted": False}

    if not contacts:
        logger.warning("Guardian alert: no contacts configured")
        return results

    msg = build_sms_alert(person_name, description, lat, lng, alert_level, profile_type)

    for contact in contacts:
        phone = contact.get("phone", "")
        name = contact.get("name", "Contact")
        if not phone:
            continue
        try:
            ok, details = sms_send_fn(phone, msg, label=f"Alerte Guardian → {name}")
            if ok:
                results["sent"].append({"phone": phone, "name": name})
                logger.info(f"Guardian alert SMS sent to {name} ({phone})")
            else:
                results["failed"].append({"phone": phone, "name": name, "error": str(details)})
                logger.warning(f"Guardian alert SMS failed to {name}: {details}")
        except Exception as e:
            results["failed"].append({"phone": phone, "name": name, "error": str(e)})

    return results
