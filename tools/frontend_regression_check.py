#!/usr/bin/env python3
"""
Vérification anti-régression frontend YAWatch / Guardian.

Compare les fichiers statiques du working directory (ou d'une URL trace)
avec la branche de référence stable/frontend-reference-2026-07-05.

Routes vérifiées par défaut :
  /, /guardian, /static/index.html, /static/guardian.html,
  /static/salon.html, /static/simli.html,
  /static/manifest.json, /static/sw.js

Usage local (avant déploiement) :
  python3 tools/frontend_regression_check.py

Usage trace (après déploiement) :
  python3 tools/frontend_regression_check.py --trace https://trace---....a.run.app

Exit code :
  0 = aucune différence inattendue
  1 = différence détectée ou erreur
"""

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import urllib.request

REFERENCE_BRANCH = "stable/frontend-reference-2026-07-05"

ROUTES = [
    "/",
    "/guardian",
    "/static/index.html",
    "/static/guardian.html",
    "/static/salon.html",
    "/static/simli.html",
    "/static/manifest.json",
    "/static/sw.js",
]

# Mapping route -> chemin dans le repo
ROUTE_TO_FILE = {
    "/": "static/index.html",
    "/guardian": "static/guardian.html",
}
for r in ROUTES:
    if r not in ROUTE_TO_FILE:
        ROUTE_TO_FILE[r] = r.lstrip("/")


def run(cmd, check=True):
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"ERREUR commande : {cmd}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip()


def git_status_clean():
    """Vérifie que le working directory est propre (sauf fichiers non trackés ignorés)."""
    status = run("git status --short", check=False)
    # On ignore les fichiers non trackés qui ne sont pas dans static/
    lines = [l for l in status.splitlines() if l.strip()]
    relevant = []
    for line in lines:
        # format : "XY path" ou "XY path -> path2"
        parts = line.split()
        status_code = parts[0]
        path = parts[1]
        # MM, M , etc. : modifications staged/unstaged
        # ?? : untracked
        if status_code == "??":
            continue  # ignore untracked
        relevant.append(line)
    return len(relevant) == 0


def current_branch_and_sha():
    branch = run("git branch --show-current")
    sha = run("git rev-parse HEAD")
    return branch, sha


def get_reference_content(path):
    """Récupère le contenu d'un fichier depuis la branche de référence."""
    try:
        return run(f"git show {REFERENCE_BRANCH}:{path}")
    except SystemExit:
        print(f"  Impossible de lire {path} sur {REFERENCE_BRANCH}")
        return None


def get_working_content(path):
    """Récupère le contenu d'un fichier depuis le working directory."""
    full = os.path.join(os.getcwd(), path)
    if not os.path.exists(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def get_trace_content(base_url, route):
    """Récupère le contenu d'une route depuis une URL trace."""
    url = base_url.rstrip("/") + route
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  Impossible de télécharger {url} : {e}")
        return None


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(text):
    """Normalise les sauts de ligne pour une comparaison robuste."""
    if text is None:
        return None
    return text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")


def compare(label, ref_content, target_content):
    ref_norm = normalize(ref_content)
    target_norm = normalize(target_content)

    if ref_norm is None and target_norm is None:
        print(f"  SKIP {label} (absent des deux côtés)")
        return True
    if ref_norm is None:
        print(f"  NOUVEAU {label} (présent dans target, absent de la référence)")
        return True
    if target_norm is None:
        print(f"  MANQUANT {label} (présent dans la référence, absent du target)")
        return False
    if ref_norm == target_norm:
        print(f"  OK   {label}")
        return True
    print(f"  DIFF {label}")
    # Lignes ajoutées/supprimées
    ref_lines = ref_norm.splitlines()
    target_lines = target_norm.splitlines()
    added = len([l for l in target_lines if l not in ref_lines])
    removed = len([l for l in ref_lines if l not in target_lines])
    print(f"       lignes ajoutées: {added}, supprimées: {removed}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Vérification anti-régression frontend")
    parser.add_argument("--trace", help="URL de la trace à comparer avec la référence")
    parser.add_argument("--strict", action="store_true", help="Échouer aussi sur les fichiers untracked dans static/")
    args = parser.parse_args()

    print("=" * 60)
    print("FRONTEND REGRESSION CHECK")
    print("=" * 60)

    branch, sha = current_branch_and_sha()
    print(f"Branche courante : {branch}")
    print(f"SHA commit       : {sha}")
    print("")

    if not git_status_clean():
        print("⚠️  ATTENTION : le working directory contient des modifications non commitées.")
        print("   État git status --short :")
        print(run("git status --short", check=False))
        if args.strict:
            print("   Mode strict : échec.")
            sys.exit(1)
        print("   Mode non strict : poursuite, mais déploiement interdit tant que ce n'est pas propre.")
    else:
        print("✅ Working directory propre (hors untracked).")

    print("")
    print(f"Branche de référence : {REFERENCE_BRANCH}")
    print(f"Routes vérifiées     : {len(ROUTES)}")
    print("")

    all_ok = True
    for route in ROUTES:
        file_path = ROUTE_TO_FILE[route]
        ref_content = get_reference_content(file_path)

        if args.trace:
            target_content = get_trace_content(args.trace, route)
            label = f"{route} (trace)"
        else:
            target_content = get_working_content(file_path)
            label = f"{route} (working dir)"

        if not compare(label, ref_content, target_content):
            all_ok = False

    print("")
    if all_ok:
        print("✅ Aucune différence inattendue détectée.")
        sys.exit(0)
    else:
        print("❌ Différences détectées par rapport à la référence.")
        if args.trace:
            print("   Vérifiez que les différences correspondent aux modifications intentionnelles.")
        else:
            print("   Corrigez ou committez les modifications avant déploiement.")
        sys.exit(1)


if __name__ == "__main__":
    main()
