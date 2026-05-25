# Luna — coordination entre agents IA

Ce dépôt utilise `docs/AGENTS_COLLABORATION/` comme espace partagé de coordination entre Claude, Codex, Cursor, Kimi et DeepSeek.

Avant toute modification importante, chaque agent doit lire :

- `docs/AGENTS_COLLABORATION/README.md`
- `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md`
- `docs/AGENTS_COLLABORATION/REGLES_DE_COORDINATION.md`
- le fichier d'avis correspondant dans `docs/AGENTS_COLLABORATION/agents/`

Règles essentielles :

- Ne pas considérer GitHub comme preuve que la production est à jour.
- Ne pas supprimer ou écraser le travail d'un autre agent.
- Distinguer clairement : code local / code commité / code mergé / image Docker / Google Cloud / APK réelle.
- Toute décision avec impact production doit être validée par Ludovic avant déploiement.

Codex est chargé des corrections ciblées, des commits, des PR et des tests.
Les décisions finales restent centralisées dans `docs/AGENTS_COLLABORATION/DECISION_FINALE.md`.
Claude a le dernier mot technique. Ludovic a le dernier mot absolu.
