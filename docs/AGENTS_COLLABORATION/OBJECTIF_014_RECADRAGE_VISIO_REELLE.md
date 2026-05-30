# Objectif 014 — Recadrage visio réelle / rôles agents / preuve terrain

**Statut** : ouvert — recadrage obligatoire avant nouvelle correction visible  
**Priorité** : critique  
**Lead coordination** : Codex  
**Décision fondateur** : Ludovic  
**Date ouverture** : 2026-05-30  

---

## Pourquoi cet objectif existe

Le travail Objectif 013 a produit des corrections techniques, mais la finalité produit n'a pas été assez cadrée avant code. Résultat terrain Ludovic :

- une grosse barre de chat "Iris" est apparue en visio ;
- ce n'est pas la vocation validée de l'application ;
- ElevenLabs n'a pas fonctionné en production ;
- l'assistante ne voit toujours pas correctement ;
- elle ne reconnaît pas Ludovic ;
- elle ne réalise pas encore les objectifs attendus d'une secrétaire en visio.

Conclusion : arrêt des ajouts visibles non cadrés. On repart d'une matrice d'objectifs réels, testée sur application réelle.

---

## Règle produit absolue

La visio n'est pas "un chat avec un avatar".  
La visio est une présence assistante : voir, entendre, comprendre, rassurer, noter, aider, exécuter seulement ce qui est autorisé.

Tout ajout UI visible doit servir cette vocation.  
Une barre de chat permanente dans la visio est considérée comme une régression si elle casse l'immersion ou transforme la visio en messagerie.

---

## Nouvelle répartition des rôles

| Agent | Rôle | Ce qu'il doit faire | Ce qu'il ne doit pas faire |
| --- | --- | --- | --- |
| **Kimi** | Oeil terrain + UX réelle | Regarder/tester l'application réelle, capturer les frictions visuelles, dire si c'est beau, cohérent, utilisable. Valider l'expérience mobile avant code final. | Ne pas ajouter une UI visible sans validation Ludovic. Ne pas déployer une expérience non testée. |
| **Codex** | Vision produit + targets + garde-fous | Définir l'objectif de chaque bouton/workflow, transformer les retours en matrice testable, bloquer le travail dans le vide, prioriser. | Ne pas prétendre qu'une feature est OK sans preuve terrain. |
| **DeepSeek** | Audit technique + risques | Vérifier fichiers, handlers, endpoints, risques de coût, auth, secrets, Twilio/Simli/ElevenLabs. Produire des tests non destructifs. | Ne pas proposer de graphisme. Ne pas lancer action sensible. |
| **Claude** | Intégrateur final | Coder seulement après matrice validée + UX validée + risques connus. Corriger proprement, déployer seulement après validation Ludovic si niveau 2/3. | Ne pas décider seul de la vision produit ni ajouter une grosse UI visible. |
| **Ludovic** | Fondateur | Valider les décisions niveau 2/3 : expérience visible, avatar, voix, vision caméra, déploiement, actions payantes. | Ne doit plus servir de relais manuel entre agents. |

---

## Matrice de finalité visio

Avant tout nouveau code, les agents doivent répondre à cette matrice.

| Objectif réel de la visio | Question terrain | Preuve attendue | Niveau |
| --- | --- | --- | --- |
| Présence crédible | Est-ce que l'assistante ressemble à une vraie présence, pas à un gadget ? | Test visuel réel mobile, screenshot ou description terrain Kimi | 2 |
| Voix féminine FR | Est-ce que la voix en production est féminine, française, cohérente ? | Test audio court < 30s, pas de boucle | 2 |
| Identité Ludovic | Est-ce qu'elle sait qu'elle parle à Ludovic ? | Elle salue Ludovic depuis le profil/contexte | 1 |
| Compréhension vocale | Est-ce qu'elle comprend une phrase simple dite au micro ? | Demande simple réussie : "prends une note de test" | 1 |
| Vision caméra | Est-ce qu'elle peut répondre "je te vois" avec observation réelle ? | Test court : présence + main levée + objet simple | 2 |
| Secrétaire utile | Peut-elle noter, résumer, rappeler, chercher une info ? | Matrice de 5 tâches non sensibles validées | 1 |
| Actions sensibles | Peut-elle appeler/SMS/email/réserver/payer ? | Interdit en dev ; seulement simulation ou validation Ludovic | 3 |
| Fin de session | Est-ce que raccrocher arrête vite la consommation ? | Test court, timer, pas de session longue | 1 |
| UI premium | Est-ce que rien ne couvre inutilement l'expérience visio ? | Kimi valide : pas de barre intrusive, pas d'élément cheap | 2 |

---

## Décisions immédiates

1. **Barre texte Iris** : non validée comme expérience produit. À retirer, masquer ou remplacer par une interaction discrète uniquement après proposition UX Kimi + validation Ludovic.
2. **Voix ElevenLabs** : ne pas déclarer résolue tant que production n'a pas parlé avec la bonne voix.
3. **Vision caméra** : ne pas déclarer résolue tant que l'assistante ne décrit pas une scène réelle en test court.
4. **Nom Iris** : à clarifier. Si Iris est l'assistante visio, elle doit être assumée comme secrétaire de Luna, pas confondue avec Luna.
5. **Aucun déploiement** sans validation Ludovic pour UI visible, voix, avatar, vision ou actions sensibles.

---

## Tâches ouvertes

### TASK-014-KIMI-REAL-VISIO-UX
- Regarder l'application réelle ou le rendu déployé.
- Juger la barre texte Iris : intrusive ou acceptable ?
- Proposer une interaction plus premium si un canal texte est vraiment nécessaire.
- Livrable : `agents/KIMI_REAL_VISIO_UX_014.md`.

### TASK-014-CODEX-TARGET-MATRIX
- Définir la matrice des objectifs visio et des preuves attendues.
- Classer P0/P1/P2/P3.
- Livrable : ce document + message AGENT_CHANNEL.

### TASK-014-DEEPSEEK-VISIO-CAPABILITY-GAP
- Vérifier pourquoi production ne voit pas / ne parle pas avec ElevenLabs.
- Identifier les gaps exacts : env vars Cloud Run, Simli payload, vision injection, STT, tool calls.
- Livrable : `agents/DEEPSEEK_VISIO_CAPABILITY_GAP_014.md`.

### TASK-014-CLAUDE-NO-CODE-BEFORE-MATRIX
- Ne pas coder de nouvelle UI visible.
- Lire la matrice, puis proposer un plan de correction minimal.
- Si correction urgente : retirer/masquer la barre texte uniquement après validation Ludovic ou instruction explicite.
- Livrable : `agents/CLAUDE_PLAN_VISIO_014.md`.

---

## Critère de sortie

Objectif 014 est terminé seulement quand :

- les rôles sont respectés ;
- la barre texte non validée est traitée ;
- la voix production est vérifiée ;
- la vision caméra est vérifiée sur scène réelle ;
- la matrice "objectif -> preuve" est utilisée avant chaque nouveau code ;
- Ludovic ne reçoit plus "c'est bon teste" sans preuve préalable.
