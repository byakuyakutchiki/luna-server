import os, sys, logging

logger = logging.getLogger("license")


class AntiDebug:
    """Detect debugging/analysis attempts."""

    @staticmethod
    def check() -> dict:
        """Run all anti-debug checks. Returns {"clean": bool, "threats": [...]}"""
        threats = []

        # 1. Check for ptrace (Linux debugger attachment)
        try:
            if os.path.exists("/proc/self/status"):
                with open("/proc/self/status") as f:
                    for line in f:
                        if line.startswith("TracerPid:"):
                            pid = int(line.split(":")[1].strip())
                            if pid != 0:
                                threats.append(f"ptrace_attached:pid={pid}")
                            break
        except Exception:
            pass

        # 2. Check for Python debuggers in loaded modules
        debug_modules = ["pydevd", "pdb", "debugpy", "rpdb", "pudb", "ipdb"]
        for mod in debug_modules:
            if mod in sys.modules:
                threats.append(f"debugger_module:{mod}")

        # 3. Check for common reverse engineering environment variables
        suspect_env = [
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONINSPECT",
            "PYTHONBREAKPOINT",
        ]
        for var in suspect_env:
            if os.environ.get(var):
                # PYTHONDONTWRITEBYTECODE is common in Docker, skip it
                if var != "PYTHONDONTWRITEBYTECODE":
                    threats.append(f"suspect_env:{var}")

        # 4. Check for strace/ltrace (check /proc/self/syscall)
        try:
            if os.path.exists("/proc/self/syscall"):
                # If readable by a non-root process while being traced, flag it
                pass  # Reading syscall itself is not a reliable indicator
        except Exception:
            pass

        # 5. Check for LD_PRELOAD (library injection)
        if os.environ.get("LD_PRELOAD"):
            threats.append(f"ld_preload:{os.environ['LD_PRELOAD']}")

        return {"clean": len(threats) == 0, "threats": threats}
