#!/usr/bin/env python3
"""
Audit visuel Luna 2026 — Playwright screenshot sweep
Usage: python tools/audit_visual_luna_2026.py
Env:   LUNA_BASE_URL  (défaut: https://luna-beta-674304336025.europe-west1.run.app)
       LUNA_EMAIL     (défaut: saintlouis.ludovic@gmail.com)
       LUNA_PASSWORD  (défaut: depuis .env)
"""

import os, sys, time, json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ── Config ──────────────────────────────────────────────────────────────────
BASE_URL   = os.getenv("LUNA_BASE_URL", "https://luna-beta-674304336025.europe-west1.run.app")
EMAIL      = os.getenv("LUNA_EMAIL",    "saintlouis.ludovic@gmail.com")
PASSWORD   = os.getenv("LUNA_PASSWORD", "Luna2025!")

NOW        = datetime.now().strftime("%Y%m%d-%H%M")
OUT_DIR    = Path(__file__).parent.parent / "docs" / "audit_visual" / f"luna-2026-visual-sweep-{NOW}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

DESKTOP = {"width": 1440, "height": 1000}
MOBILE  = {"width": 390,  "height": 844}

captured = []

def log(msg): print(f"  {msg}")

def shot(page, name, full=False):
    """Prend un screenshot et l'enregistre."""
    path = OUT_DIR / f"{name}.png"
    try:
        page.screenshot(path=str(path), full_page=full, timeout=15000)
        captured.append(name)
        log(f"✓ {name}.png")
    except Exception as e:
        log(f"  ⚠ screenshot {name} échoué: {e}")
        # Fallback: screenshot sans attendre les fonts
        try:
            page.screenshot(path=str(path), full_page=full, timeout=8000,
                            animations="disabled", caret="hide")
            captured.append(name)
            log(f"✓ {name}.png (fallback)"  )
        except Exception as e2:
            log(f"  ✗ {name} abandonné: {e2}")

def wait(page, ms=1200):
    page.wait_for_timeout(ms)

def login(page):
    """Se connecte à Luna."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    wait(page, 800)
    try:
        page.fill("#loginEmail",    EMAIL,    timeout=5000)
        page.fill("#loginPassword", PASSWORD, timeout=5000)
        page.click("#loginBtn")
        wait(page, 2500)
    except Exception as e:
        log(f"⚠ login skip: {e}")

def capture_home(page, prefix):
    """Page d'accueil — chat + onglets."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    wait(page, 1500)
    shot(page, f"{prefix}_01_home")
    # Tentative d'ouvrir le menu rapide
    try:
        page.evaluate("() => document.getElementById('actionToggle') && document.getElementById('actionToggle').click()")
        wait(page, 600)
        shot(page, f"{prefix}_02_home_action_menu")
        page.evaluate("() => document.getElementById('actionToggle') && document.getElementById('actionToggle').click()")
    except: pass

def capture_tabs(page, prefix):
    """Onglets principaux."""
    tabs = [
        ("chat",         "03_tab_chat"),
        ("services",     "04_tab_services"),
        ("friends",      "05_tab_friends"),
        ("activities",   "06_tab_activities"),
        ("monde",        "07_tab_monde"),
        ("contacts",     "08_tab_contacts"),
        ("instructions", "09_tab_instructions"),
        ("documents",    "10_tab_documents"),
        ("reports",      "11_tab_reports"),
        ("formulaires",  "12_tab_formulaires"),
        ("carte",        "13_tab_carte"),
        ("guardian",     "14_tab_guardian"),
        ("profil",       "15_tab_profil"),
        ("quotas",       "16_tab_quotas"),
    ]
    for tab_val, fname in tabs:
        try:
            btn = page.query_selector(f'.tab-btn[data-tab="{tab_val}"]')
            if btn:
                btn.click()
                wait(page, 900)
                shot(page, f"{prefix}_{fname}")
        except Exception as e:
            log(f"  ⚠ onglet {tab_val}: {e}")

def capture_page(page, url, name, wait_ms=1800, full=False):
    """Navigue vers une URL et capture."""
    try:
        page.goto(f"{BASE_URL}{url}", wait_until="networkidle", timeout=20000)
        wait(page, wait_ms)
        shot(page, name, full=full)
    except Exception as e:
        log(f"  ⚠ {name}: {e}")

def capture_workspace_states(page, prefix):
    """États Iris Workspace."""
    page.goto(f"{BASE_URL}/team", wait_until="networkidle", timeout=20000)
    wait(page, 1500)
    shot(page, f"{prefix}_ws_00_welcome")

    # Entrer un nom si setup modal
    try:
        if page.is_visible("#setupModal", timeout=2000):
            page.fill("#setupName", "Ludo", timeout=2000)
            page.click("#setupModal .tw-mbtn.primary", timeout=2000)
            wait(page, 1000)
    except: pass

    shot(page, f"{prefix}_ws_01_entry")

    # Step 2 — Brief
    try:
        page.evaluate("() => { TW.step=2; renderStepper(); applyCanvasState(2); }")
        wait(page, 800)
        shot(page, f"{prefix}_ws_02_brief_vide")
    except: pass

    # Step 3 — Collecte vide
    try:
        page.evaluate("() => { TW.step=3; renderStepper(); applyCanvasState(3); }")
        wait(page, 800)
        shot(page, f"{prefix}_ws_03_collecte_vide")
    except: pass

    # Step 3 avec proposition ajoutée
    try:
        page.evaluate("""() => {
            TW.objects.push({id:99,type:'prop',title:'Lancer une offre freemium',detail:'Test avec 500 utilisateurs',by:'Ludo',ts:Date.now()});
            renderObjects();
        }""")
        wait(page, 600)
        shot(page, f"{prefix}_ws_04_avec_proposition")
    except: pass

    # Step 10 — Recommandation Luna
    try:
        page.evaluate("() => { TW.step=10; renderStepper(); applyCanvasState(10); }")
        wait(page, 800)
        shot(page, f"{prefix}_ws_10_luna_reco")
    except: pass

    # Step 12 — Livrable/Export
    try:
        page.evaluate("() => { TW.step=12; renderStepper(); applyCanvasState(12); }")
        wait(page, 800)
        shot(page, f"{prefix}_ws_12_export")
    except: pass

def run():
    with sync_playwright() as p:
        # ── DESKTOP ──────────────────────────────────────────────────────
        log("\n[Desktop 1440×1000]")
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=DESKTOP,
            ignore_https_errors=True,
            device_scale_factor=1.5,
        )
        page = ctx.new_page()

        log("  → Login...")
        login(page)
        shot(page, "desktop_00_login_screen")

        # Login si pas encore fait
        try:
            page.fill("#loginEmail",    EMAIL,    timeout=3000)
            page.fill("#loginPassword", PASSWORD, timeout=3000)
            page.click("#loginBtn")
            wait(page, 2500)
        except: pass

        capture_home(page, "desktop")
        capture_tabs(page, "desktop")

        # Pages spéciales
        capture_page(page, "/simli",     "desktop_17_simli",     wait_ms=2500)
        capture_page(page, "/admin",     "desktop_18_admin",     wait_ms=2000)
        capture_page(page, "/workspace", "desktop_19_workspace",  wait_ms=1800)

        capture_workspace_states(page, "desktop")

        browser.close()

        # ── MOBILE ───────────────────────────────────────────────────────
        log("\n[Mobile 390×844]")
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=MOBILE,
            ignore_https_errors=True,
            is_mobile=True,
            device_scale_factor=2,
        )
        page = ctx.new_page()

        log("  → Login...")
        login(page)
        shot(page, "mobile_00_login_screen")

        try:
            page.fill("#loginEmail",    EMAIL,    timeout=3000)
            page.fill("#loginPassword", PASSWORD, timeout=3000)
            page.click("#loginBtn")
            wait(page, 2500)
        except: pass

        capture_home(page, "mobile")
        capture_tabs(page, "mobile")
        capture_page(page, "/team",  "mobile_17_workspace", wait_ms=2000)
        capture_page(page, "/simli", "mobile_18_simli",     wait_ms=2500)

        browser.close()

    # ── Index markdown ───────────────────────────────────────────────────
    index_path = OUT_DIR / "index.md"
    lines = [
        f"# Audit visuel Luna 2026 — {NOW}\n",
        f"URL : {BASE_URL}\n",
        f"Total captures : {len(captured)}\n",
        "\n## Screenshots\n",
    ]
    for c in captured:
        lines.append(f"- [{c}]({c}.png)\n")
    index_path.write_text("".join(lines))

    print(f"\n✅ Audit terminé — {len(captured)} screenshots")
    print(f"   Dossier : {OUT_DIR}")
    print(f"   Index   : {index_path}")
    return str(OUT_DIR)

if __name__ == "__main__":
    run()
