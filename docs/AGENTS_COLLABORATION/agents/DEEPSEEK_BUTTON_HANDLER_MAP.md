# DeepSeek — Button Handler Map

Agent : DeepSeek  
Objectif : 002  
Type : audit technique  
Date : 2026-05-29  

## Synthese

Cartographie technique des cibles principales demandee par Ludovic. Audit non destructif uniquement : aucun SMS, email, appel, paiement, reservation, SOS ou deploiement.

## Cibles principales

| Zone | Cible utilisateur | Handler front | Endpoint / cible | Risque | Test non destructif |
| --- | --- | --- | --- | --- | --- |
| Services / Conciergerie | Cartes actions service | `static/index.html:3196` `_concDirect()` | `POST /api/concierge/action` | Moyen : beaucoup d'actions passent par un endpoint unique | Tester uniquement meteo, news, search_web, badges, stats |
| Visio | Lancer Luna visio | `static/index.html:4618` `startCall()` | redirection `/simli?duration=...` puis `POST /api/simli/start` | Moyen : Simli consomme des credits ; avatar/voix niveau 2 | Test court, raccrocher vite, verifier confirmation |
| Appel contact | Appeler contact | `static/index.html:4632` `startVoiceCall()`, `4705` `_confirmCallContact()` | `POST /api/voice-call` | Eleve : appel reel, deja garde par confirmation P0 | Ne pas tester reel sans validation Ludovic |
| Voix directe | Parler a Luna | `static/index.html:7372` bouton voix, `7787` `/ws/luna-voice` | WebSocket `/ws/luna-voice` | Moyen : depend OpenAI realtime/audio WebView | Tester bouton + telemetrie, pas appel telephonique |
| Documents | Scanner / traiter documents | `static/documents.html:632` `execAction()` | endpoints secretary/documents | Moyen si document prive ; OK avec fichiers test | Tester fichier factice uniquement |
| Formulaires | Analyser, remplir, signer | `static/formulaires.html:536`, `661`, `738` | `/api/form-filler/*` | Moyen : fichiers utilisateur, signature | Tester PDF/image factice sans donnees perso |
| Monde / Social | Monde, boutique, amis, chat | `static/world.html:11067` et suivants | `/api/world/*`, `/api/social/*` | Moyen : social/invitations/achats internes | Tester lecture, navigation, pas achat sans validation |
| Profil / Reglages | Sauvegarder preferences | `static/index.html:3993`, `4008`, `4058`, `4059` | `/api/settings`, `/api/profile` | Faible a moyen : preference utilisateur | Tester sauvegarde mineure reversible |
| Guardian | Surveillance / SOS | `static/index.html:5107`, `5137`, `5153` | `/api/guardian/start`, `/stop`, `/sos` | Eleve : SOS/action sensible | Ne pas declencher SOS reel |

## Risques prioritaires

1. `innerHTML` et `onclick` inline restent a auditer avant durcissement global. Kimi a releve 143 `innerHTML` et 71 `onclick` inline.
2. Les parcours sensibles doivent rester derriere confirmation explicite : appel, SOS, paiement, reservation, SMS/email reels.
3. Les routes visio et chat doivent etre revues cote auth/intention avant exploitation large.
4. Les tests terrain doivent privilegier lecture/navigation et endpoints non destructifs.

## Proposition DeepSeek

Priorite immediate : continuer l'audit technique sur `TASK-013-DEEPSEEK-SIMLI-FLOW-AUDIT`, puis proposer une liste P0/P1 de corrections sans refonte graphique.

Decision Ludovic requise : non pour cet audit ; oui pour toute action sensible ou changement visible majeur.
