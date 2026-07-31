# Addendum — AGENT-CALL-SMOKE-001

Date : 2026-07-17T20:00:00+02:00

## Contexte

Le premier run du smoke test a donné un résultat `partial` :

- **Kimi** : appel réussi, décision `complete`.
- **DeepSeek** : appel réel effectué, mais la réponse ne contenait pas les champs requis du JSON de décision.
- **OpenAI/Codex** : non tenté car le provider `codex` est désactivé dans `BudgetGovernor` (`provider_codex_desactive`).

## Causes identifiées

1. **Prompt smoke trop vague pour DeepSeek/OpenAI**
   - Les callers DeepSeek et OpenAI utilisent un `user_prompt` plus court que celui de Kimi.
   - L'objectif ne spécifiait pas explicitement la structure JSON exacte attendue.
   - Le contexte `SMOKE_CONTEXT` avait `adb.available=False`, ce qui faisait échouer le routage `decide_agent` avec `adb_indisponible`.

2. **Provider Codex désactivé**
   - `BudgetGovernor._provider_enabled("codex")` vérifie d'abord `shutil.which("codex")`.
   - La CLI `codex` n'est pas installée, donc le provider est marqué désactivé.
   - L'API OpenAI est configurée, mais la logique actuelle ne la prend pas en compte pour activer `codex`.

## Corrections apportées

Dans `tools/luna_supervisor/agent_call_smoke.py` :

- Objectif smoke précisé avec la structure JSON exacte :
  ```json
  {"summary":"smoke ok","decision":"complete","requested_action":{"type":"none"},"files_relevant":[],"expected_result":"smoke test ok","requires_human_validation":false}
  ```
- `SMOKE_CONTEXT["adb"]["available"]` passé à `True` pour que `routing.decide_agent` ne bloque pas.
- Tests unitaires ajoutés dans `tools/luna_supervisor/tests_agent_call_smoke.py`.

## État après corrections

Les tests unitaires passent (callers mockés).

Aucun nouvel appel réel n'a été effectué après les corrections car le budget est à **8/10** (état `block_non_essential`). Relancer DeepSeek/OpenAI risquerait d'atteindre la limite journalière.

## Bilan honnête

| Agent | Config | Réseau | Appel réel | Statut |
|-------|--------|--------|------------|--------|
| Kimi | OK | OK | OK (decision=complete) | **OK_PROUVE** |
| DeepSeek | OK | OK | Échec format JSON (corrigé dans le code) | **A_VERIFIER** (besoin d'un nouvel appel) |
| OpenAI/Codex | OK | OK | Non tenté (provider désactivé par budget/CLI) | **A_VERIFIER** |

## Prochaines actions

- Réexécuter `agent-call-smoke` quand le budget le permettra (demain ou après réinitialisation).
- Ou corriger `BudgetGovernor._provider_enabled` pour activer `codex` via `OPENAI_API_KEY` si la CLI n'est pas installée.

Aucun secret exposé, aucun push/deploy.
