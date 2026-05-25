# AGENTS_COLLABORATION — Espace de coordination IA

Ce répertoire sert de salle de discussion technique entre les agents IA travaillant sur Luna.

Objectif : éviter que Claude, Codex, Cursor, Kimi ou DeepSeek travaillent chacun de leur côté sans connaître l'état réel du projet.

Référence actuelle :
- `docs/CAHIER_DES_CHARGES_MONITORING.md`
- `CLAUDE.md` (source de vérité fondateur)

Règle principale :
- GitHub n'est pas la production.
- Une modification dans GitHub ne veut pas dire que Google Cloud ou l'APK réelle sont à jour.
- Toute décision importante doit être validée par Ludovic avant déploiement.

## Rôles

| Agent | Rôle principal |
|---|---|
| **Claude** | Analyse finale, stratégie, cloud, validation technique, décisions d'implémentation, codeur final |
| **Codex** | Code, corrections ciblées, GitHub, PR, tests automatisés |
| **Cursor** | Vérification locale, édition code, contrôle cohérence fichiers |
| **Kimi** | Lecture longue, recul critique, comparaison documentation / réalité |
| **DeepSeek** | Analyse alternative, détection risques, propositions d'optimisation |

## Méthode de travail

1. Chaque agent lit l'état actuel (`ETAT_ACTUEL.md`).
2. Chaque agent écrit son avis dans son fichier dédié (`agents/<AGENT>_AVIS.md`).
3. Aucun agent ne supprime le travail d'un autre.
4. `DECISION_FINALE.md` centralise la décision retenue.
5. Claude propose l'implémentation finale — Ludovic valide avant déploiement.

## Priorités non-négociables (fondateur)

- L'application doit fonctionner avant d'ajouter de nouvelles ambitions.
- Tous les boutons visibles doivent être audités progressivement.
- Aucune modification ne doit casser l'APK, le WebView ou les dashboards.
- La qualité graphique doit rester premium.
- Le modèle licence/royalties doit rester protégé (70% fondateur / 30% exploitant).
