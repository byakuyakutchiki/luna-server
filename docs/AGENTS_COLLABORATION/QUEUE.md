# Queue agents Luna

> Derniere mise a jour : 2026-05-27
> Regles : agents autonomes niveau 0/1, Ludovic niveau 2/3
> Ne jamais modifier cette section d'en-tete.

---

## TODO

### TASK-010-DEPLOY-READY-CHECK
- Agent : Kimi
- Objectif : 010
- Niveau : 2
- Statut : open
- Tache : verifier sur application reelle que la recherche plein texte et les titres tronques sont prets avant deploiement.
- Interdits : pas de deploiement sans validation Ludovic.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

### TASK-011-DEEPSEEK-AUDIT-CODE
- Agent : DeepSeek
- Objectif : 011
- Niveau : 0
- Statut : open
- Tache : auditer le code des boutons Services / Conciergerie, surtout Appeler et Visio.
- Interdits : pas d'appel reel, pas de SMS/email reel, pas de modification production.
- Resultat attendu : fichier agents/DEEPSEEK_AVIS_011.md ou message court dans AGENT_CHANNEL.md.

### TASK-011-KIMI-UX-REAL-TEST
- Agent : Kimi
- Objectif : 011
- Niveau : 0
- Statut : open
- Tache : tester l'experience reelle des boutons Services cote application, reperer les boutons qui n'arrivent pas a la bonne cible ou manquent de confirmation.
- Interdits : pas d'action sensible reelle.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

### TASK-012-RUNNER-VALIDATION
- Agent : Kimi, DeepSeek
- Objectif : 012
- Niveau : 0
- Statut : open
- Tache : valider que le runner local peut pull, lire la queue, ecrire un resultat, commit et push.
- Interdits : aucun changement applicatif.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

---

## IN PROGRESS

### TASK-012-CODEX-RUNNER-VALIDATION
- Agent : Codex
- Objectif : 012
- Niveau : 0
- Statut : in_progress
- Tache : valider que le runner Windows Codex peut pull, lire la queue, ecrire un resultat, commit et push.
- Interdits : aucun changement applicatif.
- Resultat attendu : message court dans AGENT_CHANNEL.md visible par Kimi au cycle suivant.

---

## DONE

<!-- Les agents deplacent ici une tache quand elle est terminee. -->

---

## BLOCKED

<!-- Les agents deplacent ici une tache si elle est bloquee en attendant Ludovic. -->
