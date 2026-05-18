#!/usr/bin/env python3
"""
Test rapide des 3 providers LLM supportés par Luna.
Usage:
  python tools/test_llm_providers.py
  LLM_PROVIDER=deepseek LLM_API_KEY=sk-xxx python tools/test_llm_providers.py
  LLM_PROVIDER=kimi     LLM_API_KEY=sk-xxx python tools/test_llm_providers.py

Retourne un tableau récapitulatif et exit 0 si tous les providers testés passent.
"""

import os
import sys
import time
import argparse

# Pour pouvoir lancer depuis n'importe où
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from integrations.llm.provider import build_llm_client, get_llm_model, LLM_PROVIDERS

LUNA_TEST_PROMPT = "Réponds juste 'OK' sans ponctuation ni majuscule."

def test_provider(provider: str, api_key: str) -> dict:
    os.environ["LLM_PROVIDER"] = provider
    os.environ["LLM_API_KEY"] = api_key
    # reset le cache d'env dans le module
    import importlib, integrations.llm.provider as p
    importlib.reload(p)

    _, _, label = p.LLM_PROVIDERS.get(provider, p.LLM_PROVIDERS["openai"])
    model = p.get_llm_model()

    result = {"provider": provider, "label": label, "model": model, "status": "❌", "latency_ms": None, "error": None}
    try:
        client = p.build_llm_client(api_key)
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": LUNA_TEST_PROMPT}],
            max_tokens=10,
            temperature=0,
        )
        latency = int((time.time() - t0) * 1000)
        answer = resp.choices[0].message.content.strip().lower()
        result["latency_ms"] = latency
        if "ok" in answer:
            result["status"] = "✅"
        else:
            result["status"] = "⚠️ "
            result["error"] = f"réponse inattendue: '{answer}'"
    except Exception as e:
        result["error"] = str(e)[:120]
    return result


def main():
    parser = argparse.ArgumentParser(description="Test LLM providers Luna")
    parser.add_argument("--openai-key",  default=os.getenv("OPENAI_API_KEY", ""))
    parser.add_argument("--deepseek-key", default=os.getenv("DEEPSEEK_API_KEY", ""))
    parser.add_argument("--kimi-key",    default=os.getenv("KIMI_API_KEY", ""))
    parser.add_argument("--provider",    default=None, help="Tester un seul provider")
    args = parser.parse_args()

    tests = []
    if args.provider:
        key_map = {"openai": args.openai_key, "deepseek": args.deepseek_key, "kimi": args.kimi_key}
        key = key_map.get(args.provider, "")
        if not key:
            print(f"Clé manquante pour {args.provider}. Passez --{args.provider}-key ou définissez la var d'env.")
            sys.exit(2)
        tests = [(args.provider, key)]
    else:
        if args.openai_key:
            tests.append(("openai", args.openai_key))
        else:
            print("⚠️  OPENAI_API_KEY non définie — skip")
        if args.deepseek_key:
            tests.append(("deepseek", args.deepseek_key))
        else:
            print("⚠️  DEEPSEEK_API_KEY non définie — skip")
        if args.kimi_key:
            tests.append(("kimi", args.kimi_key))
        else:
            print("⚠️  KIMI_API_KEY non définie — skip")

    if not tests:
        print("Aucune clé fournie. Ajoutez OPENAI_API_KEY/DEEPSEEK_API_KEY/KIMI_API_KEY dans .env")
        sys.exit(2)

    print(f"\n{'Provider':<12} {'Label':<22} {'Model':<28} {'Status':<5} {'Latence'}")
    print("-" * 85)
    failures = 0
    for provider, key in tests:
        r = test_provider(provider, key)
        latency = f"{r['latency_ms']}ms" if r["latency_ms"] else "—"
        print(f"{r['provider']:<12} {r['label']:<22} {r['model']:<28} {r['status']:<5} {latency}")
        if r["error"]:
            print(f"           └─ {r['error']}")
        if "❌" in r["status"]:
            failures += 1

    print()
    if failures:
        print(f"ECHEC: {failures} provider(s) en erreur.")
        sys.exit(1)
    print("Tous les providers testés fonctionnent.")
    sys.exit(0)


if __name__ == "__main__":
    main()
