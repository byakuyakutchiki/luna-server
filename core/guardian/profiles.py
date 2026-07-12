"""
Luna Guardian — Profils différenciés

Chaque profil a son propre vocabulaire, ses seuils, et ses messages.
Ton : respectueux (senior), positif (dog), doux (baby), neutre (home).
Jamais de diagnostic médical.
"""
from typing import Dict, Any


PROFILES: Dict[str, Dict[str, Any]] = {
    "senior": {
        "label": "👤 Proche",
        "icon": "👴",
        "immobility_threshold_minutes": 45,  # Policy V2 §4.2
        "safe_zone_radius_m": 100,
        "check_in_message": "Bonjour {name} ! Comment vous sentez-vous aujourd'hui ?",
        "verification_message": "Luna vous demande : tout va bien ? Appuyez sur le bouton vert si vous allez bien.",
        "immobility_alert": "{name} n'a pas bougé depuis {duration}. Pouvez-vous prendre de ses nouvelles ?",
        "geofence_alert": "{name} a quitté sa zone habituelle. Dernière position : {address}.",
        "sos_message": "🆘 {name} a activé une alerte. Position précise : {maps_link}",
        "level4_message": "Si vous êtes inquiet(e), nous vous recommandons d'appeler le 15 (SAMU) ou le 112. Position : {maps_link}",
        "verified_ok_message": "Merci ! Je suis contente que vous alliez bien. Passez une belle journée.",
        "activity_good": "Bonne activité aujourd'hui !",
        "dignity_mode": True,
    },
    "dog": {
        "label": "🐕 Animal",
        "icon": "🐕",
        "immobility_threshold_minutes": 90,
        "safe_zone_radius_m": 200,
        "check_in_message": "{name} a-t-il mangé et eu sa promenade aujourd'hui ?",
        "verification_message": "Vérification en cours pour {name}. Votre animal est-il en sécurité ?",
        "immobility_alert": "{name} n'est pas sorti depuis {duration}. Peut-être a-t-il besoin d'une promenade ?",
        "geofence_alert": "{name} a quitté son territoire habituel. Dernière position : {address}.",
        "sos_message": "🐕 Alerte pour {name} — position : {maps_link}",
        "level4_message": "Si votre animal est en danger, contactez un vétérinaire ou le 17 (police). Position : {maps_link}",
        "verified_ok_message": "Super ! {name} va bien.",
        "activity_good": "Belle promenade !",
        "dignity_mode": False,
    },
    "baby": {
        "label": "👶 Bébé/Enfant",
        "icon": "👶",
        "immobility_threshold_minutes": 120,  # sieste normale
        "safe_zone_radius_m": 50,
        "check_in_message": "Comment se porte {name} ?",
        "verification_message": "Vérification suggérée pour {name}. Un adulte peut-il confirmer que tout va bien ?",
        "immobility_alert": "Absence de mouvement pour {name} depuis {duration}. Vérification non médicale suggérée.",
        "geofence_alert": "{name} semble avoir quitté sa zone. Dernière position connue : {address}.",
        "sos_message": "⚠️ Alerte pour {name}. Un proche doit vérifier. Position : {maps_link}",
        "level4_message": "En cas de doute sur la santé de {name}, appelez le 15 (SAMU). Position : {maps_link}",
        "verified_ok_message": "Merci pour votre attention pour {name}.",
        "activity_good": "{name} est actif(ve) !",
        "dignity_mode": False,
        "disclaimer": "Ce service signale uniquement des anomalies de position. Il ne remplace jamais un avis médical.",
    },
    "home": {
        "label": "🏠 Logement",
        "icon": "🏠",
        "immobility_threshold_minutes": 240,
        "safe_zone_radius_m": 50,
        "check_in_message": "Tout va bien au logement ?",
        "verification_message": "Présence détectée — confirmez votre identité.",
        "immobility_alert": "Aucun signal du logement depuis {duration}.",
        "geofence_alert": "Mouvement détecté hors périmètre : {address}.",
        "sos_message": "🏠 Alerte logement — position : {maps_link}",
        "level4_message": "En cas d'intrusion ou danger, appelez le 17 (police) ou le 112. Position : {maps_link}",
        "verified_ok_message": "Zone confirmée sûre.",
        "activity_good": "Logement sécurisé.",
        "dignity_mode": False,
    },
}


def get_profile(profile_type: str) -> Dict[str, Any]:
    """Retourne la config du profil, avec fallback sur senior."""
    return PROFILES.get(profile_type, PROFILES["senior"])


def format_profile_message(template: str, **kwargs) -> str:
    """Remplace {name}, {duration}, {address}, {maps_link} dans un template."""
    try:
        return template.format(**{k: v or "" for k, v in kwargs.items()})
    except KeyError:
        return template
