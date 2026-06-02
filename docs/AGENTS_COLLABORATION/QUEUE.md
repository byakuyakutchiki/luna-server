# Queue agents Luna

> Derniere mise a jour : 2026-05-28
> Regles : agents autonomes niveau 0/1, Ludovic niveau 2/3
> Ne jamais modifier cette section d'en-tete.

---

## TODO

### TASK-019-KIMI-UX-IRIS-COMMAND-SCREEN
- Agent : Kimi
- Objectif : 019
- Niveau : 0
- Statut : open
- Tache : proposer la direction UX premium de Iris Command Screen. Ce n'est pas un panneau texte : c'est un ecran virtuel qui s'allume et affiche Data Board, Document Draft, Action Board, Context Panel, Missing Info Panel, Status Rail. Definir rendu mobile/desktop, style futuriste/pro, interactions et criteres anti-chatbot.
- Interdits : ne pas valider un simple bloc texte, ne pas melanger Luna/Iris, ne pas proposer une UI qui superpose les controles.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/KIMI_UX_IRIS_COMMAND_SCREEN_019.md` + message court dans AGENT_CHANNEL.md.

### TASK-019-DEEPSEEK-ARCHI-IRIS-COMMAND-SCREEN
- Agent : DeepSeek
- Objectif : 019
- Niveau : 0
- Statut : open
- Tache : auditer l'architecture technique pour transformer une intention utilisateur en rendu visuel : table/document/checklist/contexte/infos manquantes. Proposer schema minimal JS + garde-fous, sans action sensible. Verifier comment eviter que Iris reponde "je ne peux pas afficher" alors que le frontend sait afficher.
- Interdits : pas d'action SMS/email/appel/paiement/reservation, pas de stockage cloud, pas de secrets.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_IRIS_COMMAND_SCREEN_019.md` + message court dans AGENT_CHANNEL.md.

### TASK-019-CLAUDE-ATTENTE-SCOPE-COMMAND-SCREEN
- Agent : Claude
- Objectif : 019
- Niveau : 2
- Statut : open
- Tache : attendre Kimi + DeepSeek ou consigne Codex explicite avant de coder. Ne pas refaire un simple Workbench texte. Quand le scope est tranche, implementer le Command Screen V1 visuel : Data Board HTML, Document Draft, Action Board, Context Panel, Missing Info Panel, Status Rail.
- Interdits : pas de deploiement sans validation Ludovic, pas d'action sensible, pas de "c'est bon" sans preuve visuelle.
- Resultat attendu : commit code + `docs/AGENTS_COLLABORATION/agents/CLAUDE_IMPL_IRIS_COMMAND_SCREEN_019.md` apres validation Codex/Ludovic.

### TASK-015-CODEX-LOG-ANALYSIS
- Agent : Codex
- Objectif : 015
- Niveau : 0/1
- Statut : done
- Tache : analyser les logs terrain Ludovic apres instrumentation, determiner ce qui marche/ne marche pas, et corriger le risque de boucle du pont STT local.
- Interdits : pas de deploiement, pas de secret, pas de session longue.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CODEX_LOG_ANALYSIS_VISIO_015.md` + patch si necessaire + message AGENT_CHANNEL.

Resultat : micro local playable et bot audio playable, mais Simli STT non prouve, pont `conversation.echo` ignore ou inefficace, STT local capte aussi la voix Iris. Pont automatique desactive par defaut dans `static/simli.html`. Vision toujours KO (`vision_no_track`).

### TASK-015-CODEX-STT-BRIDGE-PATCH
- Agent : Codex
- Objectif : 015
- Niveau : 1/2
- Statut : done
- Tache : participer au code en proposant un patch minimal non visible pour diagnostiquer et secourir la boucle micro/STT/reponse.
- Interdits : pas de deploiement, pas de secret, pas de nouvelle UI visible.
- Resultat attendu : patch `static/simli.html` + `docs/AGENTS_COLLABORATION/agents/CODEX_PATCH_STT_BRIDGE_VISIO_015.md` + message AGENT_CHANNEL.

Resultat : logs F12 ajoutes, `_sendAppMessageToBot()` globalise, logs Daily audio/participants ajoutes, pont STT local ajoute si Simli ne remonte pas d'utterance utilisateur. Non deploye.

### TASK-015-CLAUDE-INSTRUMENTATION-VISIO
- Agent : Claude
- Objectif : 015
- Niveau : 0/2
- Statut : open
- Tache : lire `OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`. Auditer le code courant pour prouver la chaine micro/STT/reponse/audio remote/image. Proposer instrumentation minimale non visible.
- Interdits : pas de deploiement, pas de secret, pas de nouvelle UI visible, pas de session longue, pas d'action sensible.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CLAUDE_INSTRUMENTATION_VISIO_015.md` + message AGENT_CHANNEL.

### TASK-015-DEEPSEEK-ARCHI-VISIO
- Agent : DeepSeek
- Objectif : 015
- Niveau : 0
- Statut : open
- Tache : auditer l'architecture visio et comparer Simli auto/start/configurable, Simli SDK/WebRTC, LiveKit/Pipecat + Simli, secours STT navigateur local -> LLM -> TTS.
- Interdits : pas de secret, pas de deploiement, pas de session longue, pas d'action sensible.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_VISIO_015.md` + message AGENT_CHANNEL.

### TASK-015-KIMI-QUALITE-VISIO
- Agent : Kimi
- Objectif : 015
- Niveau : 0/2
- Statut : done
- Tache : evaluer voix, accent, naturel, rythme, image/avatar. Proposer 3 voix feminines FR candidates max et une correction image premium.
- Interdits : pas de deploiement, pas de session longue, pas de changement graphique majeur sans validation.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/KIMI_QUALITE_VISIO_015.md` + message AGENT_CHANNEL.

Resultat : Verdict voix actuelle (Alice) = NON ACCEPTABLE. 3 candidates FR natives : Camille (recommandee, chaleureuse), Camille Martin (professionnelle), Anais (neute). Phrase de test unique fournie. Grille evaluation 6 criteres. Image : 3 niveaux correction (CSS, faceId portrait, avatar perso). Decisions Ludovic requises : choix voix + nom. Voir KIMI_QUALITE_VISIO_015.md.

### TASK-015-CODEX-TEST-MATRIX
- Agent : Codex
- Objectif : 015
- Niveau : 0
- Statut : done
- Tache : creer matrice de validation terrain pour la visio temps reel.
- Interdits : pas de code applicatif, pas de deploiement.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CODEX_TEST_MATRIX_VISIO_015.md` + message AGENT_CHANNEL.

Resultat : matrice 8 tests creee : lancement, image, voix, micro/STT, latence, identite, note, fin session.

### TASK-014-CLAUDE-DIAGNOSTIC-STT-IMAGE
- Agent : Claude
- Objectif : 014
- Niveau : 0/2
- Statut : open
- Tache : apres test terrain revision luna-beta-00463-ktx, diagnostiquer pourquoi Iris parle mais n'entend pas Ludovic/ne repond pas, et pourquoi image/avatar est distordu. Lire `CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`.
- Interdits : pas de nouvelle UI visible, pas de secret, pas de session Simli longue, pas de deploiement sans validation Ludovic, pas d'action sensible.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CLAUDE_DIAGNOSTIC_STT_IMAGE_014.md` + message AGENT_CHANNEL.

### TASK-014-DEEPSEEK-STT-SIMLI-COUNTER-AUDIT
- Agent : DeepSeek
- Objectif : 014
- Niveau : 0
- Statut : open
- Tache : contre-auditer le flux Simli bidirectionnel : pourquoi firstMessage joue mais la voix Ludovic n'est pas comprise ? Verifier payload requis, endpoint auto/configurable, STT, events Daily, app-message, transcript.
- Interdits : pas de secret, pas de deploiement, pas de session longue.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_STT_SIMLI_COUNTER_AUDIT_014.md` + message AGENT_CHANNEL.

### TASK-014-KIMI-VOICE-IDENTITY-IMAGE
- Agent : Kimi
- Objectif : 014
- Niveau : 0/2
- Statut : open
- Tache : juger la voix actuelle (accent anglais, qualite faible, "Iris" entendu "Riff") et l'image/avatar distordu. Proposer une voix feminine FR credible et une correction UX/image sans regression.
- Interdits : pas de deploiement, pas de session longue, pas de changement graphique majeur sans validation Ludovic.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/KIMI_VOICE_IDENTITY_IMAGE_014.md` + message AGENT_CHANNEL.

### TASK-014-CODEX-TERRAIN-POST-TTS-VERDICT
- Agent : Codex
- Objectif : 014
- Niveau : 0
- Statut : done
- Tache : transformer le retour terrain Ludovic apres revision luna-beta-00463-ktx en verdict et nouvelles taches agents.
- Interdits : pas de code applicatif, pas de deploiement.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md` + message AGENT_CHANNEL.

Resultat : sortie audio debloquee mais Objectif 014 non valide : identite vocale KO, voix/accent KO, STT/micro KO, image/avatar distordu.

### TASK-014-CODEX-AUDIO-NEXT-STEP
- Agent : Codex
- Objectif : 014
- Niveau : 0
- Statut : done
- Tache : transformer le diagnostic Claude audio silencieux en decision d'action, sans redeploiement au hasard.
- Interdits : pas de code applicatif, pas de test consommant credits, pas de secret.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CODEX_DECISION_AUDIO_NEXT_STEP_014.md` + message AGENT_CHANNEL.

Resultat : prochaine etape imposee = logs console `[simli]` + test ElevenLabs direct hors Simli si Ludovic valide. Aucun redeploiement tant que la voix Alice n'est pas confirmee accessible avec la cle.

### TASK-014-CLAUDE-DIAGNOSTIC-AUDIO-SILENT
- Agent : Claude
- Objectif : 014
- Niveau : 0/2
- Statut : open
- Tache : diagnostiquer le silence complet en visio apres deploiement P0 voix. Lire `CODEX_INCIDENT_P0_VISIO_AUDIO_SILENT_014.md`, isoler la chaine audio par etage : Simli start, payload, LLM, TTS, Daily/WebRTC, WebView, mute, logs.
- Interdits : pas de nouvelle UI visible, pas de secret, pas de Twilio/SMS/appel/email/paiement/reservation, pas de session Simli longue, pas de deploiement correctif sans validation Ludovic si niveau 2.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CLAUDE_DIAGNOSTIC_AUDIO_SILENT_014.md` + message AGENT_CHANNEL.

### TASK-014-DEEPSEEK-AUDIO-SILENT-COUNTER-AUDIT
- Agent : DeepSeek
- Objectif : 014
- Niveau : 0
- Statut : open
- Tache : contre-auditer la conclusion precedente "env vars ElevenLabs = cause". Le test terrain dit silence complet. Verifier payload Simli, endpoint Simli auto/configurable, noms de champs TTS, compatibilite ElevenLabs, Daily/WebView audio remote, logs existants et instrumentation minimale.
- Interdits : pas de secret, pas de deploiement, pas de session longue, pas d'action sensible.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIO_SILENT_COUNTER_AUDIT_014.md` + message AGENT_CHANNEL.

### TASK-014-CODEX-CLAUDE-EXECUTION-DECISION
- Agent : Codex
- Objectif : 014
- Niveau : 0
- Statut : done
- Tache : transformer les avis Kimi + Claude en consigne executable pour Claude, avec limites de code et deploiement Cloud Run.
- Interdits : pas de code applicatif, pas de deploiement.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CODEX_DECISION_CLAUDE_EXECUTION_014.md` + message AGENT_CHANNEL.

Resultat : Claude est bloque sur tout nouveau code voix/vision/UI/Cloud Run tant que DeepSeek 014 n'est pas livre sur GitHub. Seule action autorisee : preparer le deploiement du retrait de la barre Iris non validee, puis deployer uniquement si Ludovic donne le feu vert explicite.

### TASK-014-KIMI-REAL-VISIO-UX
- Agent : Kimi
- Objectif : 014
- Niveau : 0/2
- Statut : done
- Tache : lire la vision finale dans OBJECTIF_014_RECADRAGE_VISIO_REELLE.md, surtout "Contextes implicites de visio" et "Options attendues pendant une visio", puis regarder/tester le rendu reel. Juger si Iris comprend le cadre (personnel/pro/demo/assistance/invite/admin/urgence) et sert la promesse secretaire visio.
- Interdits : pas de deploiement, pas de session Simli longue, pas de correction UI visible sans validation Ludovic.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/KIMI_REAL_VISIO_UX_014.md` + message court AGENT_CHANNEL + commit/push GitHub.

Resultat : 10 targets juges contre la vision finale. Verdicts detailles dans le rapport. Points cles : (1) barre Iris = regression validee, suppression OK ; (2) proposition canal texte secours = swipe-up mini-drawer discret ; (3) 5 boutons top mobile = surcharge a corriger ; (4) incoherence nom Luna/Iris = friction cognitive ; (5) voix/vision/comprehension = non prouvees, tests terrain requis. Aucun code modifie, aucun credit consomme.

### TASK-014-DEEPSEEK-VISIO-CAPABILITY-GAP
- Agent : DeepSeek
- Objectif : 014
- Niveau : 0
- Statut : open
- Tache : partir des targets fonctionnelles et contextes implicites Iris en visio dans OBJECTIF_014_RECADRAGE_VISIO_REELLE.md. Pour chaque target prioritaire (voix, identité Ludovic, vision, note, résumé, rappel, contexte pro/perso, tool non sensible), auditer pourquoi la production ne prouve pas le résultat. Verifier env Cloud Run attendues, payload Simli, vision injection, STT, tool calls, limites cout.
- Interdits : pas de secret dans GitHub, pas de SMS/appel/Twilio, pas de deploiement, pas de session longue.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_VISIO_CAPABILITY_GAP_014.md` + tests non destructifs + message AGENT_CHANNEL + commit/push GitHub obligatoire.

### TASK-014-CLAUDE-NO-CODE-BEFORE-MATRIX
- Agent : Claude
- Objectif : 014
- Niveau : 0/2
- Statut : done
- Tache : lire toute la vision finale, les contextes implicites et les targets fonctionnelles dans OBJECTIF_014_RECADRAGE_VISIO_REELLE.md. Stopper les ajouts UI visibles non valides, proposer un plan minimal de correction par target et par contexte. La barre texte Iris est une regression produit non validee : proposer retrait/masquage ou alternative seulement apres validation Ludovic.
- Interdits : pas de nouvelle UI visible, pas de deploiement, pas de Cloud Run, pas de secrets, pas d'action payante.
- Resultat attendu : `docs/AGENTS_COLLABORATION/agents/CLAUDE_PLAN_VISIO_014.md` + message AGENT_CHANNEL + commit/push GitHub.

Resultat : barre Iris supprimee du code (commit 4e1d2ba, non deploye — attend validation Ludovic). Plan par target produit dans CLAUDE_PLAN_VISIO_014.md. En attente audits DeepSeek (gaps env/voix/vision) et Kimi (rendu terrain + proposition canal texte discret).

---

## IN PROGRESS

<!-- Les agents deplacent ici une tache quand ils la detectent dans la queue. -->

---

## DONE

### TASK-014-CODEX-TARGET-MATRIX
- Agent : Codex
- Objectif : 014
- Niveau : 0
- Statut : done
- Tache : recadrer la visio par objectifs reels, roles agents, preuves terrain, interdiction de travailler dans le vide.
- Interdits : pas de code applicatif, pas de deploiement.
- Resultat attendu : document objectif + message canal.

Resultat : `docs/AGENTS_COLLABORATION/OBJECTIF_014_RECADRAGE_VISIO_REELLE.md` cree. Roles clarifies : Kimi oeil terrain, Codex vision produit/targets, DeepSeek risques, Claude integration finale seulement apres matrice.

### TASK-013-CODEX-VISIO-SYNTHESIS
- Agent : Codex
- Objectif : 013
- Niveau : 0
- Statut : done
- Tache : structurer la synthese Objectif 013, prioriser les corrections, identifier les decisions niveau 2/3 a remonter a Ludovic (avatar Luna, voix feminine, input texte visio, vision camera V1/V2).
- Interdits : pas de modification code, pas de deploiement.
- Resultat attendu : message court dans AGENT_CHANNEL.md + mise a jour OBJECTIF_013_VISIO_LUNA_SIMLI.md si besoin.

Resultat : audit formalise des objectifs demandables a l'assistante pendant la visio. Elle sait lancer/parler/noter/recevoir tool calls/vision indirecte, mais l'exploitabilite complete n'est pas prouvee. Voir `docs/AGENTS_COLLABORATION/agents/CODEX_AUDIT_013_OBJECTIFS_SECRETAIRE_VISIO.md`.

### TASK-002-KIMI-VISUAL-QUALITY-GATE
- Agent : Kimi
- Objectif : 002
- Niveau : 0
- Statut : done
- Tache : appliquer une garde graphique permanente sur les audits et propositions : chaque correction doit rendre Luna plus premium, plus lisible, plus fluide ou plus coherente. Signaler tout rendu cheap, mal aligne, brouillon, trop charge, mal contraste ou incoherent avec l'identite Luna.
- Interdits : pas de refonte UI majeure sans validation Ludovic, pas de changement graphique gratuit, pas de regression visuelle toleree.
- Resultat attendu : message court dans AGENT_CHANNEL.md avec verdict qualite graphique et recommandations UI prioritaires.

Resultat : verdict 6.5/10. 315 couleurs, 324 !important, 95KB CSS monolithique dans index.html. simli.html est bien meilleur (1 !important, design immersif). Priorite : creer un design system CSS minimal. Voir `docs/AGENTS_COLLABORATION/agents/KIMI_VISUAL_QUALITY_GATE.md`.

### TASK-002-KIMI-BUTTON-TARGET-SWEEP
- Agent : Kimi
- Objectif : 002
- Niveau : 0
- Statut : done
- Tache : continuer le test reel de l'application bouton par bouton, onglet par onglet, en priorisant les parcours non sensibles : navigation, affichage, modales, erreurs, retours utilisateur, coherence mobile. Pour chaque bouton, noter cible attendue, cible obtenue, friction UX, regression visuelle eventuelle.
- Interdits : pas de SMS/email/appel/paiement/reservation/alerte reelle, pas de deploiement, pas de session Simli longue.
- Resultat attendu : message court dans AGENT_CHANNEL.md + fichier agents/KIMI_BUTTON_TARGET_SWEEP.md si la liste depasse 10 lignes.

Resultat : audit complet realise. 16 onglets cartographies, ~123 boutons, 276 endpoints backend, 69 appels API front. 0 regression critique. 2 alertes majeurs (71 onclick inline, 143 innerHTML). 2 alertes moyens (routes sans auth, sendAppMessage wildcard). Voir `docs/AGENTS_COLLABORATION/agents/KIMI_BUTTON_TARGET_SWEEP.md`.

### TASK-013-KIMI-UX-VISIO-REAL-TEST
- Agent : Kimi
- Objectif : 013
- Niveau : 0
- Statut : done
- Tache : tester l'experience reelle de la visio Luna sur application : bouton Visio, confirmation, cinematique, avatar, voix, reponse au texte, vision camera. Reperer les frictions UI et les incoherences.
- Interdits : pas de consommation inutile des credits Simli, pas de sessions longues en boucle.
- Resultat attendu : message court dans AGENT_CHANNEL.md avec points de friction et propositions UX.

Resultat : audit UX complet realise. 2 problemes critiques (pas d'input texte, hangup Simli non gere = credits gaspilles). 4 problemes majeurs (voix masculine, avatar generique, sendAppMessage wildcard, mute = instruction texte). 3 problemes moyens (vision 12s, auto-demarrage 300ms, cinematique non skippable). 4 patches niveau 1 appliques (auto-demarrage 1200ms, confirm hangup, maxIdleTime 60s, sendAppMessage cible bot uniquement). Priorisation niveau 1/2/3 proposee. Voir `docs/AGENTS_COLLABORATION/agents/KIMI_UX_VISIO_REAL_TEST.md`.

### TASK-012-RUNNER-VALIDATION
- Agent : Kimi, DeepSeek
- Objectif : 012
- Niveau : 0
- Statut : done
- Tache : valider que le runner local peut pull, lire la queue, ecrire un resultat, commit et push.
- Interdits : aucun changement applicatif.
- Resultat attendu : message court dans AGENT_CHANNEL.md.

Resultat : runners Linux (Kimi) et Windows (Codex, DeepSeek) operationnels. Pull, lecture queue, ecriture resultat, commit et push valides. Conflits git geres manuellement quand plusieurs agents poussent simultanement.

### TASK-013-DEEPSEEK-SIMLI-FLOW-AUDIT
- Agent : DeepSeek
- Objectif : 013
- Niveau : 0
- Statut : done
- Tache : auditer le flux technique Simli/Tavus dans le code : configuration avatar/voix, transmission messages, vision camera, hangup, WebSocket desactivee. Identifier causes exactes des 4 problemes (avatar, voix masculine, texte non transmis, vision limitee).
- Interdits : pas de deploiement, pas de consommation Simli inutile.
- Resultat attendu : message court dans AGENT_CHANNEL.md avec fichiers/lignes exacts et propositions techniques.

Resultat : voir `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_SIMLI_FLOW_AUDIT.md`.

### TASK-002-DEEPSEEK-BUTTON-HANDLER-MAP
- Agent : DeepSeek
- Objectif : 002
- Niveau : 0
- Statut : done
- Tache : auditer dans le code les boutons principaux et leurs handlers/endpoints : Services, Visio, Voix, Documents, Formulaires, Monde, Profil, Reglages. Produire une cartographie cible -> fonction JS -> endpoint -> risque -> test non destructif recommande.
- Interdits : pas de modification code, pas de deploiement, pas d'action sensible reelle, pas de secrets.
- Resultat attendu : message court dans AGENT_CHANNEL.md + fichier agents/DEEPSEEK_BUTTON_HANDLER_MAP.md.

Resultat : voir `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_BUTTON_HANDLER_MAP.md`.

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

Resultat : test web Cloud Run OK (elements presents et code verifies). Test APK reel recommande avant deploiement. Voir AGENT_CHANNEL.md.

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
