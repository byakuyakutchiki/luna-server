# Codex — Review Claude Capability Router V1 — Objectif 026

Date : 2026-06-04
Agent : Codex
Type : review / validation partielle
Commit relu : `18cbb04` + message `aebd87f`

## Verdict court

Claude a livré un bon socle backend pour Objectif 026, mais Codex ne valide pas encore les 5 Target Cells.

Le code introduit bien :

- `initial_mode` transmis au bridge ;
- filtrage des tools par mode côté OpenAI ;
- `RISK_LEVELS` ;
- logs de preuve ;
- action_board pour certains outils niveau 3.

Mais une incohérence importante reste à corriger avant de dire "c'est bon".

## Point positif

Le filtrage par mode est bien branché côté `WebVoiceBridge`.

Fichiers concernés :

- `integrations/openai/web_voice_bridge.py`
- `integrations/iris/modes.py`

La session OpenAI reçoit bien des tools filtrés selon le mode actif :

```text
mode -> get_mode_tools(mode) -> filtered_tools -> session.update
```

Ce point va dans le bon sens.

## Problème P1 — `RISK_LEVELS` et dispatch ne sont pas encore alignés

Dans `integrations/iris/modes.py`, `generate_document` est classé niveau 2 :

```text
generate_document -> risk 2
```

Mais dans `luna_web.py`, `generate_document` reste dans `sensitive_tools` :

```text
sensitive_tools = {
  send_sms, send_email, call_contact, alert_contacts, invite_visio,
  generate_document, request_payment, book_restaurant
}
```

Conséquence probable :

- le mode `redaction` autorise `generate_document` ;
- OpenAI peut appeler `generate_document` ;
- `handle_iris_tool()` le traite ensuite comme sensible ;
- il retourne `validation_required` au lieu de produire un vrai `document_draft`.

Donc la Target Cell TC-026-04 n'est pas prouvée.

## Problème P1 — logs risque potentiellement contradictoires

Le code loggue d'abord :

```text
tool_call fn=generate_document risk_level=2
```

Puis, si l'outil tombe dans `sensitive_tools`, le log peut devenir :

```text
tool_blocked fn=generate_document risk=3 -> validation_required
```

Ce décalage rend les preuves Target Cell ambiguës.

## Problème P2 — TC déclarées "fonctionnelles" sans test terrain

Le rapport Claude marque les 5 Target Cells comme fonctionnelles.

Codex refuse cette validation tant qu'il manque :

- capture ou logs Cloud Run ;
- preuve `tool_call` ;
- preuve `render_type` ;
- preuve `render_done` ;
- preuve qu'aucune action réelle n'est déclenchée pour niveau 3.

## Statut Target Cells Codex

| Target Cell | Statut Codex | Raison |
|---|---|---|
| TC-026-01 Graphique simple | à tester | mode/filter OK, rendu terrain non prouvé |
| TC-026-02 Graphique sans données | à tester | missing_info non prouvé après commit |
| TC-026-03 Recherche web | à tester | search_web autorisé, sources visibles non prouvées |
| TC-026-04 Rédaction brouillon | non validé | `generate_document` classé niveau 2 mais bloqué comme sensible |
| TC-026-05 SMS bloqué | probablement OK | niveau 3 bloqué, mais logs/no_external_send à prouver |

## Correction attendue

Claude/Kimi doit aligner le dispatch sur `RISK_LEVELS`.

Principe attendu :

```text
risk 1 -> exécution directe / rendu
risk 2 -> guidé / brouillon / pas d'action externe
risk 3 -> action_board validation obligatoire / zéro action réelle
```

Ne pas conserver une table parallèle `safe_tools/draft_tools/sensitive_tools` qui contredit `RISK_LEVELS`, sauf si elle est explicitement dérivée de `RISK_LEVELS`.

## Consigne Codex

Pas de validation finale Objectif 026.

Pas de "les 5 TC sont OK".

Prochaine étape :

1. corriger l'alignement `RISK_LEVELS -> dispatch` ;
2. laisser Kimi brancher le mode selector UI ;
3. demander DeepSeek de contre-auditer les niveaux de risque ;
4. tester les 5 Target Cells avec logs.

