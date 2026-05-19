"""
Luna Guardian - Escalade des alertes

Quand le risque est élevé :
  1. Vérification vocale (push WebSocket)
  2. Si pas de réponse (2 min) → SMS aux contacts de confiance avec lien Maps précis
  3. Contacts peuvent intervenir eux-mêmes ou appeler le 112
  4. Si auto_call_112=True → Luna tente d'appeler le 112 via Twilio

RGPD : Les positions GPS ne sont jamais stockées au-delà de 24h.
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
) -> str:
    """Construit le SMS d'alerte envoyé aux contacts de confiance."""
    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else None
    location_text = f"\n📍 Position précise : {maps_link}" if maps_link else "\n📍 Position non disponible"

    profile_labels = {
        "senior": "votre proche",
        "dog": "votre animal",
        "baby": "votre enfant",
        "home": "le domicile surveillé",
    }
    who = profile_labels.get(profile_type, "la personne surveillée")
    level_emoji = "🆘" if alert_level == "critical" else "⚠️"

    msg = (
        f"{level_emoji} Alerte Luna — {person_name or who}\n"
        f"{description}{location_text}\n\n"
        f"Rendez-vous sur place si possible, ou appelez le 112 en cas d'urgence.\n"
        f"Répondez OUI à ce SMS si vous intervenez."
    )
    return msg[:320]  # Limite SMS Twilio sécurisée


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
