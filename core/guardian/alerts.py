"""
Luna Guardian - Escalade des alertes

Quand le risque est élevé :
  1. Vérification vocale (push WebSocket)
  2. Si pas de réponse (2 min) → SMS aux contacts de confiance avec lien Maps précis
  3. Contacts peuvent intervenir eux-mêmes ou appeler le 112
  4. Le SMS invite les contacts à appeler le 112 eux-mêmes si nécessaire.
     Luna ne peut PAS appeler les services d'urgence — interdit légalement.

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


def build_sms_alert_v1(
    person_name: str,
    lat: Optional[float],
    lng: Optional[float],
) -> str:
    """SMS minimaliste App First — SOS et chute V1.
    Message court, lien Maps, invitation à ouvrir Luna.
    """
    name = person_name or "Quelqu'un"
    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else None
    body = f"⚠️ Luna Guardian\n{name} a demandé de l'aide."
    if maps_link:
        body += f"\n\nPosition :\n{maps_link}"
    body += "\n\nOuvrez Luna pour plus d'informations."
    return body[:320]


def build_sms_cancellation(person_name: str, confirmed_at: str) -> str:
    """SMS d'annulation — envoyé aux contacts après confirmation 'tout va bien' (Policy V2 §6.2)."""
    return (
        f"✅ Luna Guardian\n"
        f"Fausse alerte confirmée. {person_name or 'La personne surveillée'} a confirmé "
        f"qu'il/elle allait bien à {confirmed_at}.\n"
        f"Aucune intervention nécessaire. Merci."
    )[:320]


async def send_guardian_dm_alerts(
    sops,
    sender_tid: int,
    person_name: str,
    description: str,
    lat: Optional[float],
    lng: Optional[float],
    alert_level: str,
    ws_push_fn=None,
    trusted_tids: Optional[set] = None,
) -> Dict:
    """Envoie une alerte Guardian en DM Luna.
    Si trusted_tids est non-vide → seulement ces amis.
    Si vide → tous les amis (comportement legacy).
    """
    friends = sops.get_friends(sender_tid)
    if not friends:
        return {"sent": [], "failed": [], "total_friends": 0}
    if trusted_tids:
        friends = {f for f in friends if f in trusted_tids or str(f) in trusted_tids}

    maps_link = f"https://maps.google.com/?q={lat},{lng}" if lat and lng else None
    level_emoji = "🆘" if alert_level == "critical" else "⚠️"
    msg_text = f"{level_emoji} ALERTE GUARDIAN — {person_name or 'Ton contact'} a besoin d'aide !"
    if description:
        msg_text += f"\n{description}"
    if maps_link:
        msg_text += f"\n📍 {maps_link}"
    msg_text += "\nContacte-le/la ou appelle le 15/112 si urgence."
    msg_text = msg_text[:500]

    results: Dict = {"sent": [], "failed": [], "total_friends": len(friends)}
    for f_tid in friends:
        try:
            room_id = sops.create_dm_room(sender_tid, int(f_tid))
            if not room_id:
                results["failed"].append({"tid": f_tid, "error": "not friends or blocked"})
                continue
            msg = sops.add_dm_message(room_id, sender_tid, msg_text)
            msg["sender_tid"] = msg.get("sender", "")
            results["sent"].append({"tid": f_tid, "room_id": room_id})
            if ws_push_fn:
                try:
                    await ws_push_fn(room_id, msg)
                except Exception:
                    pass
        except Exception as e:
            results["failed"].append({"tid": f_tid, "error": str(e)})
            logger.warning(f"Guardian DM alert failed for friend {f_tid}: {e}")

    logger.info(f"Guardian DM alerts: {len(results['sent'])} sent, {len(results['failed'])} failed")
    return results


def send_guardian_alerts(
    sms_send_fn,              # callable(to, body, label) → (bool, details)
    contacts: List[Dict],     # [{"phone": "+33...", "name": "..."}]
    person_name: str,
    description: str,
    lat: Optional[float],
    lng: Optional[float],
    alert_level: str,
    profile_type: str,
    sms_body: Optional[str] = None,
) -> Dict:
    """
    Envoie les alertes SMS aux contacts de confiance.
    Si sms_body est fourni, l'utilise directement (App First V1).
    Sinon, construit le SMS complet via build_sms_alert (GPS immobility, etc.).
    """
    results = {"sent": [], "failed": [], "blocked": [], "call_112_attempted": False}

    if not contacts:
        logger.warning("Guardian alert: no contacts configured")
        return results

    msg = sms_body if sms_body else build_sms_alert(person_name, description, lat, lng, alert_level, profile_type)

    for contact in contacts:
        phone = contact.get("phone", "")
        name = contact.get("name", "Contact")
        if not phone:
            continue
        try:
            ok, details = sms_send_fn(phone, msg, label=f"Alerte Guardian → {name}")
            if isinstance(details, dict) and details.get("blocked"):
                results["blocked"].append({"phone": phone, "name": name})
                logger.info(f"[GUARDIAN_SMS_DISABLED] Guardian alert SMS blocked for {name} ({phone})")
            elif ok:
                results["sent"].append({"phone": phone, "name": name})
                logger.info(f"Guardian alert SMS sent to {name} ({phone})")
            else:
                results["failed"].append({"phone": phone, "name": name, "error": str(details)})
                logger.warning(f"Guardian alert SMS failed to {name}: {details}")
        except Exception as e:
            results["failed"].append({"phone": phone, "name": name, "error": str(e)})

    return results
