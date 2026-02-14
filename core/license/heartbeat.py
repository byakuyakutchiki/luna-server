import asyncio, hashlib, hmac, json, logging, os, time
from datetime import datetime, timedelta

logger = logging.getLogger("license")


class LicenseHeartbeat:
    """Manages license validation with YAWatch backend."""

    CACHE_FILE = "./data/license_cache.json"

    def __init__(self, license_key: str, license_server: str, hmac_key: str = ""):
        self.license_key = license_key
        self.license_server = license_server.rstrip("/")
        self.hmac_key = hmac_key.encode() if isinstance(hmac_key, str) else hmac_key
        self.status = "unknown"  # ok, warning, degraded, blocked
        self.action = "unknown"
        self.last_check = None
        self.last_success = None
        self.last_server_response = {}
        self.consecutive_failures = 0
        self.startup_key = None
        self._fingerprint = None
        self._fingerprint_hash = None
        self._load_cache()

    def _get_fingerprint(self):
        """Get or generate machine fingerprint."""
        if self._fingerprint_hash is None:
            from .fingerprint import MachineFingerprint

            self._fingerprint = MachineFingerprint.collect()
            self._fingerprint_hash = MachineFingerprint.generate(self._fingerprint)
        return self._fingerprint_hash

    async def activate(self) -> dict:
        """First-time activation: bind license to this machine."""
        import httpx

        fingerprint = self._get_fingerprint()
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=True) as client:
                resp = await client.post(
                    f"{self.license_server}/api/license/activate",
                    json={
                        "license_key": self.license_key,
                        "fingerprint": fingerprint,
                        "machine_info": self._fingerprint or {},
                    },
                )
            data = resp.json()
            if data.get("status") == "ok":
                self.status = "ok"
                self.startup_key = data.get("startup_key")
                self.last_success = datetime.utcnow()
                self._save_cache()
                logger.info("License activated successfully")
            else:
                self.status = data.get("action", "blocked")
                logger.error(
                    f"License activation failed: {data.get('reason', 'unknown')}"
                )
            return data
        except Exception as e:
            logger.error(f"License activation error: {e}")
            # If we have a valid cache, use it
            if self.status == "ok" and self.last_success:
                return {"status": "ok", "cached": True}
            return {"status": "error", "reason": str(e)}

    async def check(self) -> dict:
        """Periodic heartbeat check."""
        import httpx

        fingerprint = self._get_fingerprint()
        try:
            async with httpx.AsyncClient(timeout=15.0, verify=True) as client:
                resp = await client.post(
                    f"{self.license_server}/api/license/heartbeat",
                    json={
                        "license_key": self.license_key,
                        "fingerprint": fingerprint,
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": "2.0.0",
                    },
                )
            data = resp.json()
            self.last_check = datetime.utcnow()
            self.last_server_response = data

            if data.get("valid"):
                self.status = "ok"
                self.action = "ok"
                self.last_success = self.last_check
                self.consecutive_failures = 0
                self.startup_key = data.get("startup_key")
            else:
                self.action = data.get("action", "block")
                if self.action == "warning":
                    self.status = "warning"
                elif self.action == "degrade":
                    self.status = "degraded"
                else:
                    self.status = "blocked"

            self._save_cache()
            return data

        except Exception as e:
            self.consecutive_failures += 1
            self.last_check = datetime.utcnow()

            # Offline tolerance: 48h without contact = blocked
            if self.last_success:
                hours_offline = (
                    datetime.utcnow() - self.last_success
                ).total_seconds() / 3600
                if hours_offline > 48:
                    self.status = "blocked"
                    self.action = "block"
                elif hours_offline > 24:
                    self.status = "degraded"
                    self.action = "degrade"
                # Otherwise keep last known status
            else:
                # Never successfully contacted backend
                if self.consecutive_failures > 3:
                    self.status = "blocked"
                    self.action = "block"

            self._save_cache()
            return {
                "valid": self.status == "ok",
                "error": str(e),
                "action": self.action,
            }

    async def report_tamper(self, alert_type: str, details: dict):
        """Report tampering to backend."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.license_server}/api/license/alert",
                    json={
                        "license_key": self.license_key,
                        "alert_type": alert_type,
                        "details": details,
                        "fingerprint": self._get_fingerprint(),
                    },
                )
        except Exception:
            pass  # Best effort

    def is_operational(self) -> bool:
        return self.status in ("ok", "warning", "unknown")

    def is_degraded(self) -> bool:
        return self.status == "degraded"

    def is_blocked(self) -> bool:
        return self.status == "blocked"

    def get_banner_message(self):
        if self.status == "warning":
            return "Licence en attente de renouvellement. Contactez YAWatch."
        elif self.status == "degraded":
            return (
                "Service restreint — seul le chat est disponible. Contactez YAWatch."
            )
        elif self.status == "blocked":
            return (
                "Service suspendu. Contactez YAWatch pour reactiver votre licence."
            )
        return None

    def _save_cache(self):
        """Save license state to HMAC-signed cache file."""
        cache = {
            "status": self.status,
            "action": self.action,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "consecutive_failures": self.consecutive_failures,
            "startup_key": self.startup_key,
            "saved_at": time.time(),
        }
        raw = json.dumps(cache, sort_keys=True).encode()
        signature = hmac.new(self.hmac_key, raw, hashlib.sha256).hexdigest()
        cache["_sig"] = signature

        cache_dir = os.path.dirname(self.CACHE_FILE)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
        else:
            os.makedirs("data", exist_ok=True)
        with open(self.CACHE_FILE, "w") as f:
            json.dump(cache, f)

    def _load_cache(self):
        """Load and verify HMAC-signed cache."""
        if not os.path.exists(self.CACHE_FILE):
            return
        try:
            with open(self.CACHE_FILE) as f:
                cache = json.load(f)

            sig = cache.pop("_sig", "")
            raw = json.dumps(cache, sort_keys=True).encode()
            expected = hmac.new(self.hmac_key, raw, hashlib.sha256).hexdigest()

            if not hmac.compare_digest(sig, expected):
                logger.warning("License cache signature invalid — ignoring")
                return

            self.status = cache.get("status", "unknown")
            self.action = cache.get("action", "unknown")
            self.startup_key = cache.get("startup_key")
            self.consecutive_failures = cache.get("consecutive_failures", 0)
            if cache.get("last_success"):
                self.last_success = datetime.fromisoformat(cache["last_success"])
            if cache.get("last_check"):
                self.last_check = datetime.fromisoformat(cache["last_check"])

            # Check if cache is too old (48h offline tolerance)
            if self.last_success:
                hours = (
                    datetime.utcnow() - self.last_success
                ).total_seconds() / 3600
                if hours > 48:
                    self.status = "blocked"
                    self.action = "block"
                    logger.warning(
                        f"License cache expired ({hours:.0f}h offline)"
                    )

        except Exception as e:
            logger.warning(f"Failed to load license cache: {e}")
