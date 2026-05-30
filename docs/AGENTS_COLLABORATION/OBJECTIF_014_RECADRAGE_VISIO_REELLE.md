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

## Vision finale de la visio

Iris n'est pas un chatbot affiché sur une page vidéo.  
Iris est la secrétaire visio de Luna : une présence qui accompagne Ludovic ou un exploitant pendant un échange vidéo, avec une posture professionnelle, discrète et utile.

La finalité utilisateur :

1. **Présence** : l'utilisateur a l'impression de parler à une assistante réelle, pas à une interface technique.
2. **Identité** : Iris sait à qui elle parle, par exemple Ludovic, à partir du profil/contexte autorisé.
3. **Écoute** : Iris comprend une phrase vocale simple, sans demander à l'utilisateur de taper sauf secours.
4. **Vision** : Iris peut répondre à une question visuelle simple : "tu me vois ?", "je lève la main ?", "qu'est-ce que tu vois ?".
5. **Secrétariat** : Iris peut prendre une note, résumer l'appel, créer un rappel, chercher une information non sensible.
6. **Protection** : Iris refuse ou demande validation pour SMS, appel, email, paiement, réservation, alerte, données sensibles.
7. **Sobriété UI** : l'écran visio reste immersif ; les contrôles doivent être discrets, contextuels, pas une messagerie permanente.
8. **Économie** : chaque test réel est court, mesuré, sans boucle Simli/ElevenLabs/Twilio.

Si une proposition ne sert pas au moins un de ces points, elle ne doit pas être codée.

---

## Targets fonctionnelles Iris en visio

| Target | Exemple utilisateur | Résultat attendu | Preuve avant validation |
| --- | --- | --- | --- |
| Saluer l'utilisateur | "Bonjour" | Iris répond en français et peut dire "Ludovic" si le profil le permet | Test réel court |
| Comprendre la voix | "Prends une note : appeler le garage demain" | Note créée ou transcript local avec confirmation claire | Trace notes / message outil |
| Voir la présence | "Est-ce que tu me vois ?" | Iris répond à partir de la caméra, sans inventer | Description caméra cohérente |
| Voir un geste simple | "Je lève la main" | Iris décrit ou confirme si la vision le détecte | Test main levée |
| Résumer l'échange | "Fais-moi un résumé" | Résumé propre dans les notes visio | `/api/visio/notes` OK |
| Chercher une info simple | "Quelle est la météo ?" | Réponse via contexte/tool, sans hallucination | Tool ou contexte temps réel |
| Créer un rappel non sensible | "Rappelle-moi demain à 9h" | Rappel proposé/créé avec confirmation | Trace instruction |
| Inviter quelqu'un | "Invite X" | Refus en dev ou demande validation car SMS/visio tiers | Aucun SMS sans Ludovic |
| Appeler/SMS/email | "Appelle maman" | Demande validation, pas d'action réelle en dev | Aucun Twilio consommé |
| Paiement/réservation | "Réserve/paye" | Refus ou validation niveau 3 | Aucun paiement/réservation |
| Canal texte secours | L'utilisateur ne peut pas parler | Option discrète, non intrusive, activable à la demande | Validation UX Kimi + Ludovic |

---

## Contextes implicites de visio

Iris doit comprendre le cadre de la visio avant d'agir.  
Elle ne doit pas demander mécaniquement "dans quel mode sommes-nous ?" si le contexte est évident. Elle doit inférer le cadre avec humanité, puis adapter ses options.

| Contexte | Indices possibles | Posture Iris | Options utiles |
| --- | --- | --- | --- |
| **Visio personnelle Ludovic/Iris** | Ludovic seul, échange direct, demande libre | Présence chaleureuse, naturelle, non robotique | écouter, répondre, voir, prendre une note si demandé |
| **Visio professionnelle** | mots comme client, rendez-vous, réunion, dossier, exploitant, projet | secrétaire discrète, structurée, efficace | notes automatiques discrètes, résumé, actions à suivre, points de décision |
| **Visio démonstration exploitant** | présentation de Luna, test application, futur exploitant | posture claire et rassurante, expliquer sans surjouer | montrer capacités, répondre simplement, éviter jargon technique |
| **Visio assistance utilisateur fragile** | besoin d'aide, confusion, fatigue, inquiétude | rassurer, ralentir, reformuler, ne pas brusquer | voir/entendre, rappeler, guider étape par étape |
| **Visio avec invité tiers** | autre participant rejoint, partage de lien | confidentialité renforcée, retenue | prise de notes possible, actions sensibles bloquées |
| **Visio document / administratif** | document montré/upload, formulaire, facture | secrétaire administrative | lire, résumer, extraire échéances, préparer rappel |
| **Visio urgence / inquiétude** | chute, malaise, danger, SOS | calme, sécurité, demander confirmation quand possible | alerte seulement selon règles validées, jamais fausse promesse |

Règle : Iris doit adapter son comportement au contexte, pas imposer une interface.  
Exemple : en visio professionnelle, la prise de notes peut être proposée ou automatique discrète. En échange personnel, elle doit rester naturelle. En présence d'un invité, les actions sensibles doivent être bloquées ou explicitement validées.

---

## Options attendues pendant une visio

Les agents doivent vérifier ces options comme des capacités de produit, pas comme de simples boutons.

| Option | But humain | Déclenchement idéal | Validation |
| --- | --- | --- | --- |
| Notes de visio | Ne rien oublier | implicite en mode pro, ou demandé vocalement | notes générées et sauvegardées |
| Résumé final | Donner une trace claire | fin de session ou demande | résumé lisible, sans hallucination |
| Actions à suivre | Transformer la conversation en tâches | contexte réunion/projet | liste actionnable |
| Observation caméra | Répondre à "tu me vois ?" et détecter élément simple | demande vocale ou besoin d'assistance | description cohérente |
| Rappel | Ne pas oublier une échéance | "rappelle-moi..." ou échéance détectée | confirmation claire |
| Recherche simple | Aider sans quitter la visio | météo/info/service proche | source/tool ou refus honnête |
| Document montré/upload | Aider sur papier/formulaire | document visible ou upload | analyse factice/test avant données réelles |
| Canal texte secours | Continuer si STT/micro échoue | bouton discret ou action temporaire | pas de barre permanente imposée |
| Invitation tiers | Faire rejoindre quelqu'un | validation explicite | aucun SMS en dev |
| Action sensible | appel/SMS/email/paiement/réservation/alerte | seulement validation Ludovic | niveau 3 |

---

## Livraison GitHub obligatoire

Tout résultat agent doit finir sur GitHub.  
Un résultat affiché uniquement dans un terminal, un chat local, une VM ou VS Code n'est pas considéré comme livré.

Format obligatoire :

1. créer ou mettre à jour un fichier dans `docs/AGENTS_COLLABORATION/agents/` ;
2. ajouter un message court dans `AGENT_CHANNEL.md` ;
3. mettre à jour `QUEUE.md` si la tâche change de statut ;
4. `git add`, `git commit`, `git pull --rebase origin main`, `git push origin main` ;
5. si conflit, résoudre sans supprimer les avis des autres agents.

DeepSeek doit appliquer cette règle explicitement : son audit local doit être poussé sur GitHub, sinon Kimi, Claude et Codex ne peuvent pas l'utiliser comme source de vérité.

---

## Ce que Kimi doit comprendre comme "visionnaire terrain"

Kimi ne doit pas seulement dire si c'est joli.  
Kimi doit vérifier si l'expérience réelle sert la promesse :

- Est-ce qu'Iris ressemble à une secrétaire visio crédible ?
- Est-ce que l'utilisateur comprend quoi faire sans mode d'emploi ?
- Est-ce que l'UI laisse la vidéo respirer ?
- Est-ce que la barre texte Iris détruit l'immersion ?
- Si un canal texte est nécessaire, doit-il être un bouton discret "Écrire", un panneau temporaire, une commande vocale "je veux écrire", ou autre ?
- Est-ce que la voix, les mots, le rythme et les contrôles donnent confiance ?
- Est-ce que l'expérience protège les crédits Simli/ElevenLabs/Twilio ?

Livrable Kimi attendu : pas une opinion vague. Il faut :

1. verdict : validé / à corriger / régression ;
2. capture ou description du rendu réel ;
3. impact sur la promesse secrétaire visio ;
4. proposition UX premium ;
5. décision Ludovic nécessaire : oui/non.

---

## Ce que DeepSeek doit comprendre comme auditeur technique

DeepSeek doit partir de la promesse fonctionnelle, pas seulement du code.

Pour chaque target, DeepSeek doit dire :

- quel fichier/fonction/endpoint est impliqué ;
- si la target est déjà branchée ou seulement supposée ;
- ce qui manque exactement : env var, payload, event, tool, auth, permission, navigateur, Cloud Run ;
- comment tester sans action sensible ;
- risque coût/sécurité/régression.

---

## Ce que Claude doit comprendre comme intégrateur

Claude ne doit pas transformer une cible produit floue en code visible.  
Son rôle est de prendre une matrice validée et de produire l'implémentation minimale.

Pour la barre Iris :

- elle ne doit pas être considérée comme validée ;
- l'action par défaut est retrait/masquage si elle casse l'immersion ;
- une alternative doit attendre l'avis Kimi + validation Ludovic si visible.

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
