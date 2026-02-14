import hashlib, json, platform, uuid, os, socket


class MachineFingerprint:
    """Generates a unique, reproducible fingerprint for the current machine."""

    @staticmethod
    def collect() -> dict:
        """Collect machine info for fingerprint."""
        info = {}
        # MAC address (primary network interface)
        info["mac"] = hex(uuid.getnode())
        # CPU
        info["cpu"] = platform.processor() or platform.machine()
        info["cpu_count"] = os.cpu_count()
        # Platform
        info["platform"] = platform.platform()
        info["arch"] = platform.machine()
        # Hostname
        info["hostname"] = socket.gethostname()
        # RAM (total in bytes)
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        # Round to nearest GB to tolerate small changes
                        kb = int(line.split()[1])
                        info["ram_gb"] = round(kb / 1024 / 1024)
                        break
        except Exception:
            info["ram_gb"] = 0
        # Disk serial (root filesystem)
        try:
            import subprocess
            result = subprocess.run(
                ["blkid", "-s", "UUID", "-o", "value", "/dev/sda1"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            info["disk_uuid"] = result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            info["disk_uuid"] = ""
        # Docker container ID (if running in Docker)
        try:
            with open("/proc/self/cgroup") as f:
                for line in f:
                    if "docker" in line or "containerd" in line:
                        info["container_id"] = line.strip().split("/")[-1][:12]
                        break
        except Exception:
            pass
        # Cloud provider instance ID
        # GCP
        try:
            import httpx
            resp = httpx.get(
                "http://metadata.google.internal/computeMetadata/v1/instance/id",
                headers={"Metadata-Flavor": "Google"},
                timeout=2,
            )
            if resp.status_code == 200:
                info["gcp_instance_id"] = resp.text.strip()
        except Exception:
            pass
        # AWS
        try:
            import httpx
            resp = httpx.get(
                "http://169.254.169.254/latest/meta-data/instance-id",
                timeout=2,
            )
            if resp.status_code == 200:
                info["aws_instance_id"] = resp.text.strip()
        except Exception:
            pass

        return info

    @staticmethod
    def generate(info: dict = None) -> str:
        """Generate SHA-256 fingerprint hash from machine info."""
        if info is None:
            info = MachineFingerprint.collect()
        # Use only stable fields for fingerprint (not IP which can change)
        stable = {
            "mac": info.get("mac", ""),
            "cpu": info.get("cpu", ""),
            "cpu_count": info.get("cpu_count", 0),
            "platform": info.get("platform", ""),
            "ram_gb": info.get("ram_gb", 0),
            "disk_uuid": info.get("disk_uuid", ""),
            "container_id": info.get("container_id", ""),
            "gcp_instance_id": info.get("gcp_instance_id", ""),
            "aws_instance_id": info.get("aws_instance_id", ""),
        }
        raw = json.dumps(stable, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()
