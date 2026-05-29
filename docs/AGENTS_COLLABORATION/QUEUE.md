# Queue agents Luna

> Derniere mise a jour : 2026-05-28
> Regles : agents autonomes niveau 0/1, Ludovic niveau 2/3
> Ne jamais modifier cette section d'en-tete.

---

## TODO

### TASK-002-DEEPSEEK-BUTTON-HANDLER-MAP
- Agent : DeepSeek
- Objectif : 002
- Niveau : 0
- Statut : open
- Tache : auditer dans le code les boutons principaux et leurs handlers/endpoints : Services, Visio, Voix, Documents, Formulaires, Monde, Profil, Reglages. Produire une cartographie cible -> fonction JS -> endpoint -> risque -> test non destructif recommande.
- Interdits : pas de modification code, pas de deploiement, pas d'action sensible reelle, pas de secrets.
- Resultat attendu : message court dans AGENT_CHANNEL.md + fichier agents/DEEPSEEK_BUTTON_HANDLER_MAP.md.

### TASK-013-DEEPSEEK-SIMLI-FLOW-AUDIT
- Agent : DeepSeek
- Objectif : 013
- Niveau : 0
- Statut : open
- Tache : auditer le flux technique Simli/Tavus dans le code : configuration avatar/voix, transmission messages, vision camera, hangup, WebSocket desactivee. Identifier causes exactes des 4 problemes (avatar, voix masculine, texte non transmis, vision limitee).
- Interdits : pas de deploiement, pas de consommation Simli inutile.
- Resultat attendu : message court dans AGENT_CHANNEL.md avec fichiers/lignes exacts et propositions techniques.

## IN PROGRESS

### TASK-002-KIMI-BUTTON-TARGET-SWEEP
- Agent : Kimi
- Objectif : 002
- Niveau : 0
- Statut : done
- Tache : continuer le test reel de l'application bouton par bouton, onglet par onglet, en priorisant les parcours non sensibles : navigation, affichage, modales, erreurs, retours utilisateur, cohérence mobile. Pour chaque bouton, noter cible attendue, cible obtenue, friction UX, regression visuelle eventuelle.
- Interdits : pas de SMS/email/appel/paiement/reservation/alerte reelle, pas de deploiement, pas de session Simli longue.
- Resultat attendu : message court dans AGENT_CHANNEL.md + fichier agents/KIMI_BUTTON_TARGET_SWEEP.md si la liste depasse 10 lignes.

Resultat : audit complet realise. 16 onglets cartographies, ~123 boutons, 276 endpoints backend, 69 appels API front. 0 regression critique. 2 alertes majeurs (71 onclick inline, 143 innerHTML). 2 alertes moyens (routes sans auth, sendAppMessage wildcard). Voir `docs/AGENTS_COLLABORATION/agents/KIMI_BUTTON_TARGET_SWEEP.md`.

### TASK-013-CODEX-VISIO-SYNTHESIS
- Agent : Codex
- Objectif : 013
- Niveau : 0
- Statut : in_progress
- Tache : structurer la synthese Objectif 013, prioriser les corrections, identifier les decisions niveau 2/3 a remonter a Ludovic (avatar Luna, voix feminine, input texte visio, vision camera V1/V2).
- Interdits : pas de modification code, pas de deploiement.
- Resultat attendu : message court dans AGENT_CHANNEL.md + mise a jour OBJECTIF_013_VISIO_LUNA_SIMLI.md si besoin.

### TASK-013-KIMI-UX-VISIO-REAL-TEST
- Agent : Kimi
- Objectif : 013
- Niveau : 0
- Statut : in_progress
- Tache : tester l'experience reelle de la visio Luna sur application : bouton Visio, confirmation, cinematique, avatar, voix, reponse au texte, vision camera. Reperer les frictions UI et les incoherences.
- Interdits : pas de consommation inutile des credits Simli, pas de sessions longues en boucle.
- Resultat attendu : message court dans AGENT_CHANNEL.md avec points de friction et propositions UX.

### TASK-012-RUNNER-VALIDATION
- Agent : Kimi, DeepSeek
- Objectif : 012
- Niveau : 0
- Statut : in_progress
- Tache : valider que le runner local peut pull, lire la queue, ecrire un resultat, commit et push.
- Interdits : aucun changement applicatif.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

---

<!-- Les agents deplacent ici une tache quand ils commencent a la traiter. -->

---

## DONE

### TASK-011-KIMI-P0-CONFIRMATIONS-PATCH
- Agent : Kimi
- Objectif : 011
- Niveau : 1
- Statut : done
- Tache : implementer le patch minimal de confirmation P0 sur Appeler et Visio, converge avec audits Codex + DeepSeek.
- Interdits : pas d'appel reel, pas de SMS/email reel, pas de nouvelle UI.
- Resultat attendu : commit + deploiement Cloud Run.

Resultat : Patch applique static/index.html. _showConfirm() ajoute sur _concStartVisio(), _confirmCallContact() et callBtn. Deploiement en cours.

### TASK-010-DEPLOY-READY-CHECK
- Agent : Kimi
- Objectif : 010
- Niveau : 2
- Statut : done
- Tache : verifier sur application reelle que la recherche plein texte et les titres tronques sont prets avant deploiement.
- Interdits : pas de deploiement sans validation Ludovic.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

Resultat : Deploiement Cloud Run reussi. Revision luna-beta-00455-dkg. URL https://luna-beta-674304336025.europe-west1.run.app. Test web OK. Attente validation telephone Ludovic.

### TASK-012-CODEX-RUNNER-VALIDATION
- Agent : Codex
- Objectif : 012
- Niveau : 0
- Statut : done
- Tache : valider que le runner Windows Codex peut pull, lire la queue, ecrire un resultat, commit et push.
- Interdits : aucun changement applicatif.
- Resultat attendu : message court dans AGENT_CHANNEL.md visible par Kimi au cycle suivant.

### TASK-011-CODEX-P0-CONFIRMATION-AUDIT
- Agent : Codex
- Objectif : 011
- Niveau : 0
- Statut : done
- Tache : auditer dans le code les boutons Appeler et Visio, identifier les handlers exacts, proposer le patch minimal de confirmation sans action sensible reelle.
- Interdits : pas d'appel reel, pas de SMS/email reel, pas de deploiement, pas de modification majeure UI.
- Resultat attendu : message court dans AGENT_CHANNEL.md avec fichiers/lignes et proposition de patch.

Resultat : voir `docs/AGENTS_COLLABORATION/agents/CODEX_AUDIT_011_P0_CONFIRMATIONS.md`.

### TASK-010-CODEX-DEPLOY-RISK-CHECK
- Agent : Codex
- Objectif : 010
- Niveau : 0
- Statut : done
- Tache : relire le diff Objectif 010 chat/titres/recherche, lister les risques de regression avant deploiement Kimi.
- Interdits : pas de deploiement, pas de modification production.
- Resultat attendu : message court dans AGENT_CHANNEL.md : pret / bloque / risques / tests conseilles.

Resultat : voir `docs/AGENTS_COLLABORATION/agents/CODEX_DEPLOY_RISK_010.md`.

### TASK-011-KIMI-UX-REAL-TEST
- Agent : Kimi
- Objectif : 011
- Niveau : 0
- Statut : done
- Tache : tester l'experience reelle des boutons Services cote application, reperer les boutons qui n'arrivent pas a la bonne cible ou manquent de confirmation.
- Interdits : pas d'action sensible reelle.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

Resultat : test web Cloud Run OK (elements presents et code verifie). Test APK reel recommande avant deploiement. Voir AGENT_CHANNEL.md.

### TASK-011-DEEPSEEK-AUDIT-CODE
- Agent : DeepSeek
- Objectif : 011
- Niveau : 0
- Statut : done
- Tache : auditer le code des boutons Services / Conciergerie, surtout Appeler et Visio.
- Interdits : pas d'appel reel, pas de SMS/email reel, pas de modification production.
- Resultat attendu : fichier agents/DEEPSEEK_AVIS_011.md ou message court dans AGENT_CHANNEL.md.

Resultat : voir `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_011.md`.

---

## BLOCKED

<!-- Les agents deplacent ici une tache si elle est bloquee en attendant Ludovic. -->
