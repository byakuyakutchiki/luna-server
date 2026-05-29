# DeepSeek — Audit Flux Simli / Visio Luna

Agent : DeepSeek  
Objectif : 013  
Type : audit technique  
Date : 2026-05-29  

## Synthese

DeepSeek confirme les constats Kimi : la visio s'ouvre, mais le flux n'est pas encore assez coherent pour une experience Luna premium. Les causes probables sont techniques et produit : configuration avatar/voix, canal texte absent, vision non temps reel, fin de session Simli a securiser.

## Flux actuel

1. L'app principale lance la visio via `static/index.html:4618` `startCall()`.
2. La page `/simli` charge `static/simli.html`.
3. `static/simli.html:1399` appelle `POST /api/simli/start`.
4. Le backend cree la session Simli dans `luna_web.py:6827` `_start_simli_visio()`.
5. La visio utilise Daily.js cote front ; plusieurs messages systeme passent par `dailyCall.sendAppMessage()`.
6. La perception camera passe par `static/simli.html:1949` vers `POST /api/visio/perception`.

## Points techniques

| Probleme | Fichier / ligne | Diagnostic | Niveau |
| --- | --- | --- | --- |
| Avatar pas Luna | `luna_web.py:6832` | `SIMLI_FACE_ID` vient de l'environnement ; le choix/remplacement avatar est une decision produit. | 2 |
| Voix masculine | `luna_web.py:6890`, `luna_web.py:6894` | Fallbacks `CARTESIA_VOICE_ID` / `ELEVENLABS_VOICE_ID`; choix voix feminine a valider avant Cloud Run. | 2 |
| Texte utilisateur absent | `static/simli.html` | Pas d'input texte visio visible ; `sendAppMessage()` existe mais sert surtout aux messages systeme. | 2 |
| Vision limitee | `static/simli.html:1949` | Capture image puis `/api/visio/perception`, pas vision temps reel native. | 2 |
| Messages systeme trop larges | `static/simli.html:1255`, `1270`, `1334`, `1345`, `1646`, `1695`, `1973`, `2002` | `sendAppMessage` doit etre cible/qualifie avant invitations externes. | 1/2 |
| Raccrochage Simli | `static/simli.html:2190`, `2194`; `luna_web.py:7040` | `doHangup()` appelle `/api/call/end`, historiquement Tavus. `maxIdleTime` backend est maintenant reduit a 60s (`luna_web.py:6886`). | 1 puis 2 si endpoint Simli officiel |

## Risques

- Risque credit : reduit par `maxIdleTime=60`, mais une vraie fermeture Simli reste a confirmer.
- Risque UX : voix masculine + avatar generique cassent l'immersion.
- Risque accessibilite : sans input texte, l'utilisateur ne peut pas ecrire en visio.
- Risque confidentialite : messages systeme Daily.js doivent etre audites avant invitation externe.

## Actions proposees

Niveau 1 possible :

- verifier que la confirmation raccrocher fonctionne bien sur mobile ;
- ajouter message clair si transcription/notes indisponibles ;
- documenter le comportement `sendAppMessage` avant correction.

Niveau 2, validation Ludovic :

- choisir une voix feminine Simli/Cartesia/ElevenLabs ;
- choisir si l'avatar actuel est "assistante visio Luna" ou si un avatar Luna est cree ;
- valider l'ajout d'une barre de saisie texte en visio ;
- valider si la vision reste en V1 par capture periodique ou passe en vision plus frequente.

Decision Ludovic requise : oui pour avatar, voix, input texte visio et vision avancee.
