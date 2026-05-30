# Codex — Decision d'execution pour Claude — Objectif 014

Agent : Codex  
Date : 2026-05-30  
Statut : decision de coordination apres avis Kimi + Claude, en attente DeepSeek 014  

---

## Decision courte

Claude ne doit pas coder une nouvelle fonctionnalite visio tant que DeepSeek n'a pas livre sur GitHub le rapport `DEEPSEEK_VISIO_CAPABILITY_GAP_014.md`.

Claude peut seulement preparer ou executer, apres validation explicite Ludovic, le deploiement de la correction deja faite : retrait de la barre texte Iris non validee.

Tout ce qui touche voix production, vision camera, Cloud Run env vars, avatar, UI visible ou canal texte secours est bloque jusqu'a preuve terrain + validation niveau 2.

---

## Ce que Claude doit lire avant action

1. `docs/AGENTS_COLLABORATION/OBJECTIF_014_RECADRAGE_VISIO_REELLE.md`
2. `docs/AGENTS_COLLABORATION/AGENT_RULES_LIGHT.md`
3. `docs/AGENTS_COLLABORATION/QUEUE.md`
4. `docs/AGENTS_COLLABORATION/agents/KIMI_REAL_VISIO_UX_014.md`
5. `docs/AGENTS_COLLABORATION/agents/CLAUDE_PLAN_VISIO_014.md`
6. `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_VISIO_CAPABILITY_GAP_014.md` des qu'il existe

---

## Autorise maintenant

### A. Preparation de deploiement

Claude peut verifier que le code courant ne contient plus la barre texte Iris intrusive et preparer un deploiement propre.

Mais il ne deploie pas tant que Ludovic n'a pas ecrit clairement : "deploie".

### B. Smoke tests non sensibles

Claude peut preparer les tests suivants, sans action payante :

- page visio chargee ;
- `/health` ou endpoint equivalent ;
- aucune barre texte permanente ;
- aucun SMS, appel, email, paiement, reservation ;
- aucune session Simli longue.

### C. Rapport GitHub

Claude doit publier dans `AGENT_CHANNEL.md` :

- commit deploye si deploiement valide ;
- revision Cloud Run si deploiement realise ;
- tests effectues ;
- limites restantes.

---

## Interdit tant que DeepSeek 014 manque

Claude ne code pas :

- correction voix ElevenLabs en production ;
- correction env vars Cloud Run ;
- correction vision camera ;
- modification du payload Simli ;
- nouveau canal texte secours ;
- reduction ou refonte visible de la barre top mobile ;
- avatar Luna/Iris ;
- actions Twilio, SMS, appel, email, paiement, reservation.

Raison : Kimi a donne l'avis terrain, Claude a reconnu l'erreur produit, mais le gap technique DeepSeek 014 n'est pas encore livre sur GitHub.

---

## Ordre d'execution impose

1. DeepSeek livre `DEEPSEEK_VISIO_CAPABILITY_GAP_014.md` sur GitHub.
2. Codex relit et transforme en matrice de decision.
3. Claude recoit une liste exacte de patches autorises.
4. Ludovic valide les points niveau 2/3.
5. Claude code minimalement.
6. Kimi teste le rendu reel.
7. Deploiement Cloud Run seulement apres feu vert Ludovic.

---

## Decisions Ludovic encore requises

| Sujet | Pourquoi | Niveau |
| --- | --- | --- |
| Deployer le retrait de la barre Iris | Correction visible en production | 2 |
| Nommer l'assistante Luna ou Iris | Incoherence actuelle Luna/Iris | 2 |
| Valider un canal texte secours discret | Nouvelle UI visible | 2 |
| Tester voix Alice 30s | Consomme credits Simli/ElevenLabs | 2 |
| Tester vision camera | Consomme credits et implique camera | 2 |
| Avatar definitif | Identite visuelle de Luna/Iris | 2 |

---

## Prompt court a donner a Claude

Claude, lis `docs/AGENTS_COLLABORATION/agents/CODEX_DECISION_CLAUDE_EXECUTION_014.md`.

Consigne Codex : tu ne codes rien de nouveau sur la visio tant que DeepSeek n'a pas pousse `DEEPSEEK_VISIO_CAPABILITY_GAP_014.md` sur GitHub. Tu peux seulement preparer le deploiement du retrait de la barre texte Iris deja code, et tu ne deploies Cloud Run que si Ludovic ecrit explicitement "deploie".

Interdit : voix, vision, Cloud Run env vars, payload Simli, avatar, nouvelle UI, Twilio, SMS, appel, email, paiement, reservation.

Si Ludovic valide le deploiement du retrait de barre : deploie uniquement le main courant, fais des smoke tests non sensibles, publie revision + tests dans `AGENT_CHANNEL.md`.

Sinon : attends DeepSeek 014 et ne code pas.
