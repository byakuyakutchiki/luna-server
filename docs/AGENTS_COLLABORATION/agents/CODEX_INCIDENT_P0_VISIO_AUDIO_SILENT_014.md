# Codex — Incident P0 visio audio silencieux — Objectif 014

Agent : Codex  
Date : 2026-05-30  
Statut : incident terrain apres test Ludovic  

---

## Signal terrain Ludovic

Apres deploiement annonce par Claude (`luna-beta-00462-q7n`) avec `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID`, Ludovic teste la visio.

Resultat terrain : Iris ne parle pas du tout. Pas de voix masculine, pas de voix feminine : silence complet.

Conclusion : le probleme n'est plus seulement "voix masculine faute ElevenLabs". Le probleme P0 est "aucune sortie audio audible en visio".

---

## Decision Codex

Claude ne doit pas ajouter de fonctionnalite produit tant que la chaine audio visio n'est pas isolee.

Priorite unique : diagnostic P0 audio silencieux, avec preuve par etage.

Interdits maintenus :

- pas de nouvelle UI visible ;
- pas de refonte visio ;
- pas d'avatar ;
- pas de Twilio/SMS/appel/email/paiement/reservation ;
- pas de session Simli longue ;
- pas de secret dans GitHub ;
- pas de conclusion "corrige" sans test terrain.

---

## Chaine a isoler

Claude doit verifier et documenter chaque etage :

| Etage | Question | Preuve attendue |
| --- | --- | --- |
| 1. Session Simli | `/api/simli/start` retourne bien `conversation_url` + `conversation_id` | log redige sans secret |
| 2. Reponse API Simli | `auto/start/configurable` accepte le payload TTS/LLM | status HTTP + champs utiles, sans cle |
| 3. LLM | Simli recoit `OPENAI_API_KEY` et peut produire une reponse | log Simli/Cloud Run ou evenement Daily |
| 4. TTS | ElevenLabs est appele avec le bon provider, voice ID et modele compatible | preuve non secrete ou test TTS court hors visio |
| 5. Daily/WebRTC | un participant bot rejoint et publie une piste audio | events Daily `participant-joined`, tracks/audio |
| 6. Navigateur/WebView | l'audio entrant n'est pas bloque par autoplay, mute, permissions ou sortie volume | event lecture audio / track playable |
| 7. Frontend | le bouton mute Luna n'est pas actif et aucune piste remote n'est coupee | etat UI + logs |
| 8. Terrain | Ludovic entend une phrase courte | test < 30s |

---

## Causes probables a tester

1. Payload Simli TTS mal nomme ou obsolete : le code utilise `ttsProvider`, `ttsAPIKey`, `voiceId`, `elevenlabsLanguageCode`.
2. Endpoint Simli Auto possiblement obsolete/deprecie : la doc actuelle marque plusieurs endpoints `auto/*` comme deprecated.
3. Voice ID ElevenLabs invalide ou non accessible avec la cle.
4. Cle ElevenLabs sans permission TTS/voices ou quota insuffisant.
5. `OPENAI_API_KEY` absent/invalide cote Cloud Run pour la session Simli.
6. Bot Simli rejoint la room mais ne publie pas de piste audio.
7. Daily/WebView bloque l'audio entrant, autoplay ou permission micro/audio.
8. `firstMessage` n'est pas joue par Simli avec ce mode de session.
9. `Cartesia` present par erreur et prioritaire dans le code, avec config incomplete.
10. Logs insuffisants : on ne sait pas si le silence vient de Simli, ElevenLabs, OpenAI, Daily ou WebView.

---

## Actions Claude autorisees

### A. Diagnostic non sensible

Claude peut ajouter un endpoint ou une route debug admin non publique si elle ne revele aucun secret et si elle indique seulement :

- provider TTS choisi : `ElevenLabs` / `Cartesia` / fallback ;
- presence booleenne des env vars, jamais leur valeur ;
- voice ID tronque ou hash court ;
- dernier status Simli start ;
- dernier event Daily utile remonte par `rLog`.

### B. Test TTS court hors visio

Claude peut proposer un test serveur ElevenLabs tres court, 1 phrase, si Ludovic valide la consommation minimale.

But : savoir si ElevenLabs parle hors Simli. Si oui, le probleme est Simli/Daily/WebView. Si non, le probleme est cle/voice/quota/model.

### C. Logs terrain

Claude doit demander a Kimi de tester ou observer :

- avatar visible mais silencieux ?
- bot present dans la room ?
- micro utilisateur autorise ?
- bouton mute Luna actif/inactif ?
- message d'erreur discret ?
- audio du telephone volume OK ?

---

## Actions Claude interdites

Claude ne doit pas :

- remplacer l'architecture par un autre fournisseur sans decision Ludovic ;
- coder une barre texte pour contourner le probleme ;
- annoncer que ElevenLabs marche parce que les env vars sont presentes ;
- lancer des appels Twilio ou SMS ;
- faire des tests longs de visio ;
- pousser des secrets dans un rapport.

---

## Prompt a donner a Claude

Claude, lis `docs/AGENTS_COLLABORATION/agents/CODEX_INCIDENT_P0_VISIO_AUDIO_SILENT_014.md`.

Le test Ludovic apres ton deploiement indique : Iris ne parle pas du tout. Silence complet. Ce n'est donc pas resolu par l'ajout des env vars ElevenLabs.

Consigne Codex : stop tout nouveau code produit. Priorite unique : isoler la chaine audio visio par etage.

Tu dois produire sur GitHub :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_DIAGNOSTIC_AUDIO_SILENT_014.md`

avec :

1. ce que Cloud Run a vraiment en env, sans secret ;
2. le payload Simli envoye, sans secret ;
3. la reponse Simli start, status et champs utiles, sans secret ;
4. les logs Daily/WebRTC disponibles ;
5. si le bot rejoint et publie une piste audio ;
6. si le frontend peut jouer l'audio entrant ;
7. hypothese racine classee par probabilite ;
8. patch minimal propose, sans le deployer si niveau 2 ;
9. test court terrain demande a Ludovic.

Tu peux ajouter de l'instrumentation non visible et non secrete si elle sert a localiser le silence. Tu ne changes pas l'UX, tu ne codes pas de contournement, tu ne lances aucune action sensible.

---

## Prompt a donner a DeepSeek

DeepSeek, relis `docs/AGENTS_COLLABORATION/agents/CODEX_INCIDENT_P0_VISIO_AUDIO_SILENT_014.md`.

Ton audit precedent identifiait les env vars ElevenLabs comme cause de voix masculine. Le test terrain dit maintenant : silence complet apres deploiement.

Ta mission : contre-audit technique.

Verifie dans le code :

- payload Simli exact ;
- noms de champs TTS attendus ;
- endpoint Simli utilise et statut deprecation ;
- compatibilite ElevenLabs voice/model ;
- risque Daily/WebView audio remote ;
- logs existants `rLog` utiles ;
- instrumentation minimale recommandee.

Livrable GitHub :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIO_SILENT_COUNTER_AUDIT_014.md`

Pas de secret, pas de deploiement, pas de session longue.
