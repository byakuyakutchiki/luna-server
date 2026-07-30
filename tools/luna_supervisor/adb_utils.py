"""Utilitaires ADB pour le superviseur Luna.

Fournit la détection et la résolution d'un device Android disponible,
avec fallback automatique vers un périphérique USB si le device configuré
est injoignable.
"""

import logging
import re
import shutil
import subprocess
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def list_adb_devices() -> str:
    """Retourne la sortie brute de `adb devices -l`."""
    adb = shutil.which("adb")
    if not adb:
        logger.warning("adb introuvable dans le PATH")
        return ""
    try:
        result = subprocess.run(
            [adb, "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0:
            logger.warning("adb devices a échoué: %s", result.stderr.strip())
            return ""
        return result.stdout
    except Exception as e:
        logger.warning("Impossible d'exécuter adb devices: %s", e)
        return ""


def parse_adb_devices(output: str) -> List[Dict[str, str]]:
    """Parse la sortie d'adb devices -l et retourne les devices connectés."""
    devices: List[Dict[str, str]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or "List of devices" in line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        device_id = parts[0]
        state = parts[1]
        if state != "device":
            continue
        is_usb = "usb:" in line
        # Extrait le modèle si présent
        model_match = re.search(r"model:(\S+)", line)
        model = model_match.group(1) if model_match else ""
        devices.append({"id": device_id, "usb": str(is_usb), "model": model, "raw": line})
    return devices


def resolve_android_device(config: Dict[str, str]) -> Tuple[str, str]:
    """Résout l'ANDROID_DEVICE_ID à utiliser.

    Si le device configuré est disponible, le conserve.
    Sinon, effectue un fallback vers le premier device USB disponible,
    puis vers n'importe quel device connecté.
    Met à jour config["ANDROID_DEVICE_ID"] en place.

    Retourne (device_id_utilisé, output_brut_adb_devices).
    """
    configured = config.get("ANDROID_DEVICE_ID", "")
    output = list_adb_devices()
    devices = parse_adb_devices(output)

    if configured:
        for dev in devices:
            if dev["id"] == configured:
                return configured, output

    usb_devices = [d for d in devices if d["usb"] == "True"]
    fallback = usb_devices[0] if usb_devices else (devices[0] if devices else None)

    if fallback:
        new_id = fallback["id"]
        config["ANDROID_DEVICE_ID"] = new_id
        logger.info(
            "ADB fallback: device configuré '%s' indisponible, utilisation de '%s' (USB=%s, model=%s)",
            configured or "(aucun)",
            new_id,
            fallback["usb"],
            fallback["model"],
        )
        return new_id, output

    return configured, output
