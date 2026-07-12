#!/usr/bin/env python3
"""Parse .env et écrit les variables dans un fichier (usage interne systemd)."""
import os
import sys

if len(sys.argv) < 2:
    sys.exit(1)

out_path = sys.argv[1]
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

lines = []
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Coupe commentaire inline (heuristique : espace + #)
            if " #" in line:
                line = line.split(" #", 1)[0].rstrip()
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            # Supprime quotes simples/doubles autour de la valeur
            if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                v = v[1:-1]
            if not k:
                continue
            # Échappe les apostrophes pour bash single-quoted
            safe_v = v.replace("'", "'\"'\"'")
            lines.append(f"export '{k}'='{safe_v}'")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
