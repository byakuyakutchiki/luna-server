#!/usr/bin/env python3
"""
Test harness autonome Iris WebSocket.

Usage:
  python tools/test_iris_ws.py                          # teste staging
  python tools/test_iris_ws.py --url https://...        # teste n'importe quelle instance
  python tools/test_iris_ws.py --prod                   # teste prod (attention)
  python tools/test_iris_ws.py --phrase "bonjour iris"  # phrase unique

Ce script permet à Claude de tester le comportement d'Iris sans intervention humaine.
Il envoie des messages texte (sans audio), lit les réponses et vérifie les invariants.
"""

import asyncio
import json
import sys
import time
import argparse
import httpx
import websockets

# ── Config ──────────────────────────────────────────────────────────────────
STAGING_URL = "https://luna-staging-674304336025.europe-west1.run.app"
PROD_URL    = "https://luna-beta-674304336025.europe-west1.run.app"
LOCAL_URL   = "http://localhost:8888"

EMAIL    = "saintlouis.ludovic@gmail.com"
PASSWORD = "Luna2025!"

# Phrases de test et le comportement attendu
TEST_SUITE = [
    {
        "phrase": "Bonjour Iris, qui es-tu ?",
        "expect_render": True,
        "expect_no_loop": True,
        "description": "Identité de base — doit appeler iris_render une fois puis parler",
    },
    {
        "phrase": "As-tu un panneau visuel ou un écran ?",
        "expect_render": True,
        "expect_iris_affirms_panel": True,
        "description": "Connaissance du panneau ICS — doit affirmer qu'elle a l'ICS",
    },
    {
        "phrase": "Montre-moi un tableau avec 3 colonnes : Tâche, Priorité, Statut",
        "expect_render": True,
        "description": "Rendu tableau — doit afficher quelque chose dans le panneau (type au choix du modèle en voix)",
    },
    {
        "phrase": "Quelle est la météo à Paris aujourd'hui ?",
        "expect_render": True,
        "description": "Appel outil get_weather + rendu",
    },
]

# ── Auth ─────────────────────────────────────────────────────────────────────
async def get_token(base_url: str) -> str:
    async with httpx.AsyncClient(timeout=15, verify=False) as client:
        r = await client.post(f"{base_url}/api/auth/login",
                              json={"email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        return r.json()["token"]


# ── WS Test Runner ───────────────────────────────────────────────────────────
class IrisTestSession:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.events: list[dict] = []
        self.render_count = 0
        self.transcript_iris: list[str] = []
        self.tool_calls: list[str] = []
        self._ws = None

    def _ws_url(self) -> str:
        proto = "wss" if self.base_url.startswith("https") else "ws"
        host = self.base_url.replace("https://", "").replace("http://", "")
        return f"{proto}://{host}/ws/iris-voice?token={self.token}&mode=discussion"

    async def connect(self) -> bool:
        url = self._ws_url()
        try:
            self._ws = await asyncio.wait_for(
                websockets.connect(url, ssl=True if url.startswith("wss") else False),
                timeout=15,
            )
            return True
        except Exception as e:
            print(f"  ✗ Connexion WS échouée: {e}")
            return False

    async def wait_ready(self, timeout=20) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=2)
                ev = json.loads(raw)
                self.events.append(ev)
                if ev.get("type") == "ready":
                    return True
                if ev.get("type") == "boot_state" and ev.get("state") == "vert":
                    pass  # continue waiting for "ready"
                if ev.get("type") == "error":
                    print(f"  ✗ Erreur serveur: {ev.get('message')}")
                    return False
            except asyncio.TimeoutError:
                continue
        return False

    async def send_text(self, text: str):
        await self._ws.send(json.dumps({"type": "text", "text": text}))

    async def collect_response(self, timeout=25) -> dict:
        """Collecte tous les événements jusqu'à audio_done ou transcript iris."""
        renders = []
        transcripts_iris = []
        tool_calls_seen = []
        boot_events = []
        deadline = time.time() + timeout
        got_audio_done = False
        got_transcript = False

        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(self._ws.recv(), timeout=min(remaining, 3))
                ev = json.loads(raw)
                self.events.append(ev)
                t = ev.get("type", "")

                if t == "render":
                    renders.append(ev)
                    self.render_count += 1
                elif t == "transcript" and ev.get("role") == "luna":
                    transcripts_iris.append(ev.get("text", ""))
                    self.transcript_iris.append(ev.get("text", ""))
                    got_transcript = True
                elif t == "tool_call":
                    tool_calls_seen.append(ev.get("name", "?"))
                    self.tool_calls.append(ev.get("name", "?"))
                elif t == "audio_done":
                    got_audio_done = True
                elif t == "boot_state":
                    boot_events.append(ev.get("state"))

            except asyncio.TimeoutError:
                # Si on a déjà un rendu ET un transcript, on peut s'arrêter
                if renders and got_transcript:
                    break
                if got_audio_done and got_transcript:
                    break
                continue

        return {
            "renders": renders,
            "transcripts_iris": transcripts_iris,
            "tool_calls": tool_calls_seen,
            "got_audio_done": got_audio_done,
            "got_transcript": got_transcript,
        }

    async def close(self):
        if self._ws:
            await self._ws.close()


# ── Assertions ───────────────────────────────────────────────────────────────
def check_result(test: dict, result: dict) -> tuple[bool, list[str]]:
    errors = []

    if test.get("expect_render") and not result["renders"]:
        errors.append("iris_render non appelé — panneau ICS vide")

    if test.get("expect_no_loop"):
        if len(result["renders"]) > 2:
            errors.append(f"BOUCLE détectée : {len(result['renders'])} appels iris_render pour 1 message")

    if test.get("expect_render_type"):
        expected = test["expect_render_type"]
        types_seen = [r.get("render_type") for r in result["renders"]]
        if expected not in types_seen:
            errors.append(f"render_type attendu={expected}, obtenu={types_seen}")

    if test.get("expect_iris_affirms_panel"):
        text_concat = " ".join(result["transcripts_iris"]).lower()
        panel_words = ["panneau", "écran", "ics", "command screen", "iris command", "visuel", "affiche"]
        if not any(w in text_concat for w in panel_words):
            errors.append(f"Iris ne mentionne pas le panneau ICS dans sa réponse: «{text_concat[:200]}»")

    if not result["got_transcript"] and not result["renders"]:
        errors.append("Aucune réponse reçue (ni rendu ni transcript)")

    return len(errors) == 0, errors


# ── Main ─────────────────────────────────────────────────────────────────────
async def run_tests(base_url: str, phrases: list[str] | None = None):
    print(f"\n{'='*60}")
    print(f"  IRIS TEST HARNESS")
    print(f"  URL: {base_url}")
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Auth
    print("── Authentification...")
    try:
        token = await get_token(base_url)
        print(f"  ✓ Token obtenu\n")
    except Exception as e:
        print(f"  ✗ Auth échouée: {e}\n")
        return False

    suite = TEST_SUITE
    if phrases:
        suite = [{"phrase": p, "expect_render": True, "expect_no_loop": True,
                  "description": "Test manuel"} for p in phrases]

    total = 0
    passed = 0
    all_results = []

    for i, test in enumerate(suite, 1):
        print(f"── Test {i}/{len(suite)}: {test['description']}")
        print(f"   Phrase: «{test['phrase']}»")

        session = IrisTestSession(base_url, token)

        connected = await session.connect()
        if not connected:
            print(f"   ✗ SKIP — connexion WS impossible\n")
            total += 1
            all_results.append({"test": test, "ok": False, "errors": ["WS connexion échouée"]})
            continue

        ready = await session.wait_ready(timeout=25)
        if not ready:
            print(f"   ✗ SKIP — session non prête (boot timeout)\n")
            await session.close()
            total += 1
            all_results.append({"test": test, "ok": False, "errors": ["Boot timeout"]})
            continue

        # Attendre que le greeting soit terminé avant d'envoyer la phrase
        # sinon "conversation_already_has_active_response"
        print(f"   ✓ Session prête — attente fin greeting...")
        await asyncio.sleep(5)
        print(f"   → envoi phrase test")
        await session.send_text(test["phrase"])

        result = await session.collect_response(timeout=30)
        ok, errors = check_result(test, result)

        total += 1
        if ok:
            passed += 1
            print(f"   ✓ PASS")
        else:
            print(f"   ✗ FAIL:")
            for err in errors:
                print(f"      → {err}")

        # Détails
        print(f"   renders={len(result['renders'])} "
              f"render_types={[r.get('render_type') for r in result['renders']]} "
              f"transcript={'oui' if result['got_transcript'] else 'non'} "
              f"tool_calls={result['tool_calls']}")
        if result["transcripts_iris"]:
            print(f"   Iris dit: «{result['transcripts_iris'][0][:120]}»")

        all_results.append({"test": test, "ok": ok, "errors": errors, "result": result})
        await session.close()
        print()

        # Pause entre tests pour éviter le rate-limit OpenAI
        if i < len(suite):
            await asyncio.sleep(3)

    # Résumé
    print(f"{'='*60}")
    print(f"  RÉSULTAT: {passed}/{total} tests passés")
    if passed == total:
        print(f"  ✓ IRIS OPÉRATIONNELLE")
    else:
        print(f"  ✗ {total - passed} tests échoués")
        for r in all_results:
            if not r["ok"]:
                print(f"    • {r['test']['description']}: {r['errors']}")
    print(f"{'='*60}\n")

    return passed == total


def main():
    parser = argparse.ArgumentParser(description="Iris WS Test Harness")
    parser.add_argument("--url", default=None, help="URL de l'instance à tester")
    parser.add_argument("--prod", action="store_true", help="Tester la prod")
    parser.add_argument("--local", action="store_true", help="Tester localhost:8888")
    parser.add_argument("--phrase", nargs="+", help="Phrases à tester manuellement")
    args = parser.parse_args()

    if args.url:
        url = args.url
    elif args.prod:
        url = PROD_URL
    elif args.local:
        url = LOCAL_URL
    else:
        url = STAGING_URL

    ok = asyncio.run(run_tests(url, phrases=args.phrase))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
