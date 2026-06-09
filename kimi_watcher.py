#!/usr/bin/env python3
"""
kimi_watcher.py — Poll /tmp/iris_audit/handoff_to_claude/ every 5s for new Kimi instructions.
Displays new or modified files as they appear. Run in a terminal before starting a work session.
"""
import os, time, sys, hashlib

WATCH_DIR = "/tmp/iris_audit/handoff_to_claude"
POLL_INTERVAL = 5

def file_sig(path):
    try:
        stat = os.stat(path)
        return (stat.st_size, stat.st_mtime)
    except OSError:
        return None

def scan(watch_dir):
    result = {}
    if not os.path.isdir(watch_dir):
        return result
    for fname in os.listdir(watch_dir):
        fpath = os.path.join(watch_dir, fname)
        if os.path.isfile(fpath):
            result[fname] = file_sig(fpath)
    return result

def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[Erreur lecture: {e}]"

def display(fname, fpath, label):
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  {label}: {fname}")
    print(sep)
    content = read_file(fpath)
    lines = content.splitlines()
    preview = "\n".join(lines[:40])
    print(preview)
    if len(lines) > 40:
        print(f"  ... ({len(lines) - 40} lignes supplémentaires)")
    print(sep)

def main():
    print(f"[kimi_watcher] Surveillance de {WATCH_DIR}")
    print(f"[kimi_watcher] Intervalle : {POLL_INTERVAL}s — Ctrl+C pour arrêter\n")

    prev = scan(WATCH_DIR)
    if not os.path.isdir(WATCH_DIR):
        print(f"[kimi_watcher] Dossier absent, en attente...")

    while True:
        try:
            time.sleep(POLL_INTERVAL)
            curr = scan(WATCH_DIR)

            for fname, sig in curr.items():
                fpath = os.path.join(WATCH_DIR, fname)
                if fname not in prev:
                    display(fname, fpath, "NOUVEAU FICHIER KIMI")
                elif prev[fname] != sig:
                    display(fname, fpath, "FICHIER MODIFIÉ KIMI")

            for fname in prev:
                if fname not in curr:
                    print(f"\n[kimi_watcher] Fichier supprimé : {fname}")

            prev = curr

        except KeyboardInterrupt:
            print("\n[kimi_watcher] Arrêt.")
            sys.exit(0)

if __name__ == "__main__":
    main()
