# Codex — Arbitrage après Target Cell DeepSeek — Objectif 021

Date : 2026-06-02  
Agent : Codex  
Type : arbitrage / consigne Claude

---

## Ce qui est validé

Le retour DeepSeek est utile : il transforme Iris Capability Gateway en matrice de capacités.

Les 10 capacités à suivre sont retenues :

1. recherche web ;
2. porte-documents ;
3. upload / analyse ;
4. carte / map ;
5. SMS ;
6. appel ;
7. email ;
8. Teams ;
9. rendu visuel ;
10. garde-fous.

---

## Correction Codex

DeepSeek propose "activer SMS" en P0. Ce n'est pas accepté comme exécution réelle.

La bonne P0 est :

- `action_board` SMS visible ;
- validation owner ;
- horaires ;
- blacklist ;
- quota/cout ;
- zéro SMS réel tant que Ludovic ne valide pas explicitement.

Même règle pour appel et email.

---

## Consigne Claude

Claude doit produire un plan d'implémentation V1, pas coder directement une action réelle.

Priorité V1 :

1. recherche externe visible avec sources ;
2. documents/vault visibles ;
3. action_board SMS/appel/email sans exécution réelle ;
4. map_board avec consentement ;
5. Teams overlay à prouver ;
6. mode clair/sombre.

Livrable attendu :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_PLAN_IRIS_CAPABILITY_GATEWAY_021.md`

---

## Message à Claude

Lire :

- `TARGET_CELL.md`
- `TARGET_REGISTER.md`
- `OBJECTIF_021_IRIS_CAPABILITY_GATEWAY.md`
- `KIMI_UX_IRIS_CAPABILITY_GATEWAY_021.md`
- `DEEPSEEK_TARGET_CELL_IRIS_CAPABILITY_021.md`
- `CODEX_ARBITRAGE_DEEPSEEK_TARGET_CELL_021.md`

Ne pas déployer. Ne pas envoyer SMS/appel/email. Ne pas annoncer "c'est bon" sans preuve target.

