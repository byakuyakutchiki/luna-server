# Codex — Audit objectifs assistante visio Luna

Agent : Codex  
Objectif : 013  
Type : audit  
Date : 2026-05-29  

## Verdict court

La secretaire de Luna ne realise pas encore tous ses objectifs pendant la visio.  
Elle peut deja lancer une session, parler via Simli, recevoir des tool calls, produire des notes, lire un contexte camera indirect et appeler des outils backend.  
Mais l'experience n'est pas encore prouvee comme "secretaire exploitable" parce que l'identite de l'utilisateur, le canal texte, la vision en direct et la validation des actions sensibles restent incomplets ou non testes terrain.

## Matrice des objectifs demandables en visio

| Objectif demande en visio | Etat actuel | Preuve code | Risque | Conclusion |
| --- | --- | --- | --- | --- |
| Parler avec l'assistante | Partiel | `luna_web.py:6827` `_start_simli_visio()`, `static/simli.html` Daily.js | voix a valider | OK apres test voix Alice < 30s |
| Reconnaitre Ludovic par son nom | Partiel | `firstMessage` utilise `subscriber_name`; contexte via `build_tavus_context()` | identité vocale non prouvee | Elle peut savoir le nom si profil correct, mais ne reconnait pas encore la voix de Ludovic |
| Comprendre la voix utilisateur | Partiel | Simli fait STT -> LLM ; `SpeechRecognition` local sert surtout aux notes (`static/simli.html:2073`) | depend Simli/navigateur | A tester en vrai, phrase courte |
| Repondre au texte tape | Non pret | `OBJECTIF_013`: pas d'input texte visio ; `sendAppMessage` existe mais pas UI utilisateur | UX bloquante | Niveau 2 : ajouter input texte visio |
| Dire "je te vois" / decrire camera | Partiel | `/api/visio/perception` (`luna_web.py:7297`), capture 12s (`static/simli.html:1945`) | pas temps reel, injection fragile | V1 existe, mais doit etre testee et renforcee |
| Dire "tu leves la main" | Non prouve | vision capture 320x240 toutes 12s + description OpenAI Vision | latence/faux negatif | A classer P1 test terrain, pas garanti |
| Prendre des notes de visio | Plutot OK | `/api/visio/notes`, `/api/visio/notes/save` | qualite transcript variable | A tester sur session courte |
| Analyser un document montre/upload en visio | Partiel | `/api/visio/upload` (`static/simli.html:1657`) | fichier prive/cout IA | OK avec fichier factice uniquement |
| Inviter quelqu'un en visio | Partiel sensible | `/api/call/invite-guest`, `/api/call/create-join-link` | SMS/cout/confidentialite | Interdit en dev sans validation |
| Envoyer SMS / appeler / email | Techniquement present | `_handle_tavus_tool_call()` dispatch `send_sms`, `call_contact`, `send_email` | Twilio/cout/action reelle | Bloque par regle cout : jamais sans feu vert |
| Creer rappel / instruction | Present | `_tool_create_instruction()`, `/api/instructions` | faible si non sensible | Bon candidat test non destructif |
| Meteo / actualites / recherche web | Present | tools `get_weather`, `get_news`, `search_web` | hallucination si tool echoue | Test non destructif recommande |
| Restaurant / hotel / vol / paiement | Present en outils | `search_places`, `search_hotels`, `search_flights`, `request_payment` | paiement/reservation/cout | Audit seulement, pas action reelle |
| Guardian / alerte / surveillance | Present mais sensible | `alert_contacts`, guardian endpoints | sécurité/legal/SMS | Interdit sans validation explicite |

## Ce qui est deja corrige

- Voix feminine : Claude/Kimi ont configure ElevenLabs Alice + `elevenlabsLanguageCode=fr`, a valider en test local court.
- Credits Simli : `maxIdleTime` reduit a 60s.
- Messages Simli : `sendAppMessage` cible le bot quand il est detecte.
- Raccrochage : confirmation utilisateur ajoutee.
- Twilio : regle officielle zero SMS/appel reel sans validation Ludovic.

## P0/P1 avant de dire "la secretaire atteint ses objectifs"

1. P0 : test voix Alice < 30 secondes, sans Twilio.
2. P0 : verifier que Luna dit bien "Ludovic" depuis le profil/contexte.
3. P1 : test camera simple : "est-ce que tu me vois ?" puis "je leve la main".
4. P1 : tester une demande non sensible : "prends une note : test visio Luna".
5. P1 : tester meteo/actualites via tool non destructif.
6. P2 : ajouter un input texte visio, car aujourd'hui le texte utilisateur n'a pas de vrai canal.
7. P2 : definir si l'avatar actuel est l'assistante visio ou creer un avatar Luna.

## Conclusion

Non, l'audit complet des objectifs "secretaire pendant visio" n'etait pas encore formalise avant ce fichier.  
Ce fichier devient la grille de validation. L'etape suivante n'est pas de tester 100 choses au hasard, mais de passer cette matrice une ligne apres l'autre, avec des tests courts et sans action facturee.
