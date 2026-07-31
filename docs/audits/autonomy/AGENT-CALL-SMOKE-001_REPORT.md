# Rapport de smoke test : AGENT-CALL-SMOKE-001

- **Mission ID** : AGENT-CALL-SMOKE-001
- **Date** : 2026-07-17T19:48:28.691744+00:00
- **Runner ID** : luna-vm-01
- **Statut global** : partial

## Appels agents

| Agent | Tenté | Succès | Décision | Durée (ms) | Erreur |
|-------|-------|--------|----------|------------|--------|
| kimi | True | True | complete | 6859 | - |
| deepseek | True | False | - | - | erreur inattendue: Champs manquants dans la décision: ['expected_result', 'files_relevant', 'requested_action', 'summary'] |
| codex | False | False | - | - | budget insuffisant: provider_codex_desactive |

## Routing (decide_agent)

- **operator** : should_call=False, role=, agent=, reason=adb_indisponible:?
- **auditor** : should_call=False, role=, agent=, reason=adb_indisponible:?
- **coordinator** : should_call=False, role=, agent=, reason=adb_indisponible:?

## Fallback (clés absentes)

- **auditor** : fallback_agent=kimi, ok=True
- **coordinator** : fallback_agent=kimi, ok=True

## Budget après test

- Total aujourd'hui : 8 / 10
- État du gouverneur : block_non_essential

## Conclusion

Certains agents ont répondu, d'autres ont échoué ou été bloqués par le budget. Voir le tableau ci-dessus.
