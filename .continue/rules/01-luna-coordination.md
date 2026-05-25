---
name: Luna coordination and production guardrails
alwaysApply: true
description: Mandatory workflow rules for AI agents working on Luna.
---

# Luna Coordination Rules

- Read `AGENTS.md` and `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md` before proposing meaningful changes.
- Treat GitHub as code state only. GitHub does not prove Cloud Run, Docker images, or the APK are updated.
- Work locally and through GitHub branches/PRs only. Do not deploy to Google Cloud, run `deploy.sh`, change production Cloud Run, or modify production secrets without explicit Ludovic validation.
- DeepSeek may propose and edit code, but major changes require Ludovic validation before merge or deployment.
- Do not expose, print, commit, or modify API keys, `.env` secrets, service-account files, production URLs with credentials, or private tokens.
- Keep changes small and targeted. Avoid broad refactors unless Ludovic explicitly validates the scope.
- Never overwrite another agent's report file in `docs/AGENTS_COLLABORATION/agents/`.
- For changes touching `luna_web.py`, `index.html`, APK/WebView behavior, Redis, auth, Stripe, monitoring, or dashboards, list risks and rollback before implementation.
- Keep work on a dedicated branch until validation. Do not push directly to `main`.
