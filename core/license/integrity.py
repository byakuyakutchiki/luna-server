import hashlib, hmac, json, os, time


class IntegrityChecker:
    """Verifies code integrity by checking file hashes against a signed manifest."""

    CRITICAL_PATHS = [
        "luna_web.py",
        "core/license/heartbeat.py",
        "core/license/fingerprint.py",
        "core/safety/guardian.py",
        "core/memory/memory_manager.py",
        "core/memory/redis_client.py",
        "core/instructions/executor.py",
        "core/actions/quota_guard.py",
    ]

    def __init__(self, base_dir: str, hmac_key: str):
        self.base_dir = base_dir
        self.hmac_key = hmac_key.encode() if isinstance(hmac_key, str) else hmac_key
        self.manifest_path = os.path.join(base_dir, "data", ".integrity.json")

    def _hash_file(self, filepath: str) -> str:
        """SHA-256 of a file."""
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def generate_manifest(self) -> dict:
        """Calculate hashes for all critical files and sign the manifest."""
        hashes = {}
        for relpath in self.CRITICAL_PATHS:
            fullpath = os.path.join(self.base_dir, relpath)
            if os.path.exists(fullpath):
                hashes[relpath] = self._hash_file(fullpath)
            # Also check .so compiled versions
            so_path = fullpath.replace(".py", ".cpython-311-x86_64-linux-gnu.so")
            if os.path.exists(so_path):
                hashes[relpath + ".so"] = self._hash_file(so_path)

        manifest = {
            "hashes": hashes,
            "generated_at": time.time(),
            "file_count": len(hashes),
        }
        # Sign with HMAC
        raw = json.dumps(manifest, sort_keys=True).encode()
        signature = hmac.new(self.hmac_key, raw, hashlib.sha256).hexdigest()
        manifest["signature"] = signature

        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        with open(self.manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def verify(self) -> dict:
        """Verify all file hashes match the signed manifest."""
        if not os.path.exists(self.manifest_path):
            return {"valid": False, "reason": "Manifest manquant", "tampered": []}

        with open(self.manifest_path) as f:
            manifest = json.load(f)

        # Verify HMAC signature
        signature = manifest.pop("signature", "")
        raw = json.dumps(manifest, sort_keys=True).encode()
        expected_sig = hmac.new(self.hmac_key, raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return {
                "valid": False,
                "reason": "Manifest signature invalide",
                "tampered": ["MANIFEST"],
            }

        # Check each file
        tampered = []
        for relpath, expected_hash in manifest.get("hashes", {}).items():
            actual_path = relpath
            if actual_path.endswith(".so"):
                actual_path = actual_path[:-3]  # Remove .so suffix we added
                fullpath = os.path.join(
                    self.base_dir,
                    actual_path.replace(".py", ".cpython-311-x86_64-linux-gnu.so"),
                )
            else:
                fullpath = os.path.join(self.base_dir, actual_path)

            if not os.path.exists(fullpath):
                tampered.append(f"{relpath} (MISSING)")
                continue

            actual_hash = self._hash_file(fullpath)
            if actual_hash != expected_hash:
                tampered.append(f"{relpath} (MODIFIED)")

        if tampered:
            return {
                "valid": False,
                "reason": f"{len(tampered)} fichier(s) modifie(s)",
                "tampered": tampered,
            }

        return {"valid": True, "reason": "OK", "tampered": []}
