#!/usr/bin/env python3
"""
Création en masse des comptes beta-testeurs YAWatch Luna.

Usage:
    1. Remplis la liste TESTERS ci-dessous avec tes 15 proches
    2. Lance: python3 tools/create_beta_testers.py

Le script se connecte au dashboard admin, crée les comptes,
et génère un fichier CSV récapitulatif à envoyer à chacun.
"""

import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — À MODIFIER
# ═══════════════════════════════════════════════════════════════

# URL de ton serveur Luna (HTTPS)
LUNA_URL = os.getenv("LUNA_URL", "https://localhost:8888")

# Mot de passe admin (depuis .env ou en dur ici)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

# ═══════════════════════════════════════════════════════════════
# LISTE DES 15 TESTEURS — REMPLIS ICI
# ═══════════════════════════════════════════════════════════════
# Chaque testeur: (prénom, nom, email, mot_de_passe, plan)
# Plans: "essentiel" (79€), "confort" (149€), "premium" (249€)
# Pour le beta test gratuit, "essentiel" suffit pour tester.

TESTERS = [
    # --- Famille Saint-Louis (beta test fev 2026) ---
    ("Gwladys",  "Saint-Louis", "gwladys.saintlouis@gmail.com",  "Luna2026!", "essentiel"),
    ("Sabine",   "Saint-Louis", "sabinesaintlouis@gmail.com",    "Luna2026!", "essentiel"),

    # --- A ajouter quand tu auras leurs emails ---
    # ("Andreze",  "Saint-Louis", "andreze@email.com",     "Luna2026!", "essentiel"),
    # ("Victor",   "Saint-Louis", "victor@email.com",      "Luna2026!", "essentiel"),
]

# ═══════════════════════════════════════════════════════════════
# SCRIPT — NE PAS MODIFIER EN DESSOUS
# ═══════════════════════════════════════════════════════════════

# SSL: accepter le certificat auto-signé en dev
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def api_call(method, path, data=None, token=None):
    """Appel HTTP vers l'API Luna."""
    url = f"{LUNA_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=_ssl_ctx, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body_err)
        except json.JSONDecodeError:
            return e.code, {"error": body_err}
    except urllib.error.URLError as e:
        return 0, {"error": f"Connexion impossible: {e.reason}"}


def admin_login(password):
    """Authentification admin → retourne le JWT."""
    status, data = api_call("POST", "/api/admin/login", {"password": password})
    if status == 200 and "token" in data:
        return data["token"]
    print(f"  ERREUR login admin: {status} — {data.get('error', data)}")
    return None


def create_tester(token, first_name, last_name, email, password, plan):
    """Crée un compte testeur via l'API admin."""
    payload = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "plan": plan,
    }
    status, data = api_call("POST", "/api/admin/clients", payload, token)
    return status, data


def main():
    print("=" * 60)
    print("  YAWatch Luna — Creation comptes beta-testeurs")
    print("=" * 60)
    print()

    # Vérifier le mot de passe admin
    password = ADMIN_PASSWORD
    if not password:
        password = input("Mot de passe admin Luna: ").strip()
    if not password:
        print("ERREUR: Mot de passe admin requis.")
        sys.exit(1)

    # Login admin
    print(f"Connexion a {LUNA_URL}...")
    token = admin_login(password)
    if not token:
        print("ERREUR: Impossible de se connecter au dashboard admin.")
        print("Verifie que Luna tourne et que le mot de passe est correct.")
        sys.exit(1)
    print("  Admin connecte !\n")

    # Créer les comptes
    results = []
    ok_count = 0
    fail_count = 0

    for i, (first_name, last_name, email, pwd, plan) in enumerate(TESTERS, 1):
        print(f"[{i:2d}/15] {first_name} {last_name} <{email}> plan={plan}... ", end="")

        status, data = create_tester(token, first_name, last_name, email, pwd, plan)

        if status == 200 and data.get("success"):
            tid = data.get("tenant_id", "?")
            print(f"OK (tenant_id={tid})")
            results.append({
                "status": "OK",
                "tenant_id": tid,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": pwd,
                "plan": plan,
            })
            ok_count += 1
        elif status == 409:
            print(f"DEJA EXISTANT ({data.get('error', '')})")
            results.append({
                "status": "EXISTE",
                "tenant_id": "-",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": pwd,
                "plan": plan,
            })
            fail_count += 1
        else:
            err = data.get("error", str(data))
            print(f"ERREUR {status}: {err}")
            results.append({
                "status": f"ERREUR ({status})",
                "tenant_id": "-",
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": pwd,
                "plan": plan,
            })
            fail_count += 1

    # Résumé
    print()
    print("=" * 60)
    print(f"  RESULTAT: {ok_count} crees, {fail_count} erreurs/existants")
    print("=" * 60)

    # Générer le fichier récap CSV
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"beta_testers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Status;Tenant_ID;Prenom;Nom;Email;Mot_de_passe;Plan;URL_Connexion\n")
        for r in results:
            f.write(
                f"{r['status']};{r['tenant_id']};{r['first_name']};{r['last_name']};"
                f"{r['email']};{r['password']};{r['plan']};{LUNA_URL}\n"
            )

    print(f"\n  Fichier recap: {csv_path}")
    print(f"  Envoie a chaque testeur sa ligne (email + mot de passe + URL)")
    print()

    # Afficher le tableau récap
    print(f"  {'#':>2}  {'Status':<10} {'TID':>4}  {'Prenom':<12} {'Email':<30} {'Plan':<10}")
    print(f"  {'—'*2}  {'—'*10} {'—'*4}  {'—'*12} {'—'*30} {'—'*10}")
    for i, r in enumerate(results, 1):
        print(
            f"  {i:2d}  {r['status']:<10} {str(r['tenant_id']):>4}  "
            f"{r['first_name']:<12} {r['email']:<30} {r['plan']:<10}"
        )

    print()
    print("  Les testeurs se connectent sur:")
    print(f"    {LUNA_URL}/")
    print("  avec leur email + mot de passe ci-dessus.")
    print()


if __name__ == "__main__":
    main()
