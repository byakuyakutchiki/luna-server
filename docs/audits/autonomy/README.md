# Pack audit externe — Autonomie Luna Supervisor

Date : 2026-07-14
Branche : `audit/autonomy-supervisor-pack-2026-07-14`
Objectif : fournir à un auditeur externe (DeepSeek, ChatGPT, humain) une vue lisible de l’architecture d’autonomie sans exposer de secrets.

## Contenu

- `tools/luna_supervisor/` : code source du superviseur autonome multi-agents.
- `config/agent_budget_policy.yaml` : politique de budget et garde-fous.
- `config/luna_mission_charter.yaml` : charte produit et critères d’acceptation.
- `docs/agents-runtime-inventory.md` : inventaire des agents et fournisseurs IA.
- `docs/audits/autonomy/agent-shared/` : rapports de missions, checklist, roadmap, état courant.

## Ce qui est explicitement exclu

- `.env`, `.env.*`, secrets, credentials.
- `data/*.db`, bases de données locales.
- `android-app/build/`, APK, artefacts compilés.
- Keystore, certificats, tokens.
- Code applicatif Guardian, Luna web, Cortex, Iris, etc.

## Usage recommandé

Cette branche est en lecture seule. Elle sert à l’audit externe de l’architecture de supervision autonome. Aucune modification ici n’impacte les branches de développement.
