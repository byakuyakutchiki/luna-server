# DeepSeek / Codex — Audit flux morts visio Iris — Objectif 017

## Source

Texte DeepSeek transmis par Ludovic apres lecture de :

- `CODEX_F12_LOGS_BRUTS_VISIO_IRIS_017.md`
- `CLAUDE_AUDIT_PROVIDER_CONTROLES_VISIO_017.md`
- `KIMI_REFONTE_UI_VISIO_IRIS_V1_017.md`
- `CODEX_MISSION_COLLECTIVE_VISIO_IRIS_017.md`

## Verdict DeepSeek

La rupture principale expliquee par les logs F12 est :

`POST /api/visio/transcribe -> 500`

avec :

`The python-multipart library must be installed to use form parsing.`

Diagnostic :

- VAD OK ;
- MediaRecorder OK ;
- blob audio envoye OK ;
- backend STT casse avant Whisper ;
- LLM jamais appele ;
- TTS jamais appele ;
- Iris ne peut pas repondre.

Le fix attendu est bien l'ajout de `python-multipart` dans les dependances Cloud Run.

## Audit flux morts / doublons selon DeepSeek

DeepSeek signale les risques suivants :

| Sujet | Diagnostic DeepSeek | Statut Codex |
|---|---|---|
| `python-multipart` manquant | confirme par F12 | confirme et corrige dans `requirements-cloudrun.txt` |
| Double `getUserMedia` | Daily peut prendre le micro, puis VAD redemande le micro | confirme comme risque reel |
| Simli auto STT | possible double STT avec le STT Simli | a verifier, pas prouve dans le payload actuel |
| Tavus encore actif | routes Tavus et boot Tavus existent | confirme, mais changement env/routes = decision Ludovic |
| Controles Daily visibles | mic/camera/barre participants/provider UI polluent l'interface | confirme par capture et audit Claude/Kimi |
| Badge `Iris voit` | mensonger si aucune description vision | confirme, deja corrige en `Vision en attente/active` dans code courant |
| Double mute / double raccrocher | provider + UI Luna/Iris peuvent diverger | confirme comme risque UX |
| Web Speech API ancien | DeepSeek pense voir un reste | non confirme : `SpeechRecognition` absent de `static/simli.html` courant |

## Verification Codex

### 1. Web Speech API

Recherche dans `static/simli.html` :

`SpeechRecognition` / `webkitSpeechRecognition`

Resultat :

aucune occurrence trouvee.

Conclusion :

ne pas demander une suppression qui ne correspond pas au code courant.

### 2. Simli auto STT

Payload actuel `_start_simli_visio()` :

- `simliAPIKey`
- `faceId`
- `systemPrompt`
- `firstMessage`
- `customLLMConfig`
- `ttsProvider`
- `voiceId`
- `ttsAPIKey`
- `elevenlabsLanguageCode`

Pas de champ explicite `enable_auto_stt`.

Conclusion :

risque a verifier dans la documentation/provider Simli, mais non prouve par le code actuel.

### 3. Tavus encore actif

Confirme dans `luna_web.py` :

- `ENABLE_TAVUS_BOOT` existe et vaut `true` par defaut ;
- Tavus est prioritaire pour plans `premium` / `fondateur` si configure ;
- routes `/api/call`, `/api/call/end`, `/api/call/invite-guest`, `/api/webhook/tavus` presentes.

Conclusion :

la desactivation Tavus n'est pas un micro-fix. C'est une decision niveau 2/3 selon impact provider/couts.

### 4. Controles Daily

Claude a deja ajoute :

- `showParticipantsBar: false`
- `showLocalVideo: false`
- `showLeaveButton: false`
- `showFullscreenButton: false`

Conclusion :

prochain test terrain doit verifier si ces options masquent vraiment la barre participants et la preview locale.

### 5. Double micro

Confirme dans `static/simli.html` :

- Daily rejoint la room ;
- ensuite `_startSpeechCapture()` lance `_startVAD()` ;
- `_startVAD()` appelle encore `navigator.mediaDevices.getUserMedia({ audio: true })`.

Conclusion :

risque reel, surtout Android/WebView. Prochaine correction probable : reutiliser la piste audio Daily si disponible, fallback `getUserMedia` seulement si necessaire.

## Decision Codex

Priorite immediate :

1. Deployer dernier `main` avec `python-multipart`.
2. Retester F12 jusqu'a obtenir `vad_stt_http 200`.
3. Si STT passe, verifier `vad_transcribed`, `llm_http`, `tts_http`, `audio_play_start`.
4. Si RMS/micro reste instable apres fix multipart, traiter le double `getUserMedia`.
5. Ne pas desactiver Tavus sans validation Ludovic.

## Message AGENT_CHANNEL

Agent : DeepSeek / Codex  
Objectif : 017  
Type : audit flux morts / arbitrage  
Résumé : DeepSeek confirme la cause racine STT : `python-multipart` absent Cloud Run. Il identifie aussi des risques produits/techniques : double `getUserMedia`, controles Daily, Tavus encore actif, badge vision, double mute/raccrocher. Codex corrige deux extrapolations : pas de `SpeechRecognition` trouve dans `static/simli.html`, et Simli auto STT non prouve par le payload courant.  
Fichier concerné : `static/simli.html`, `luna_web.py`, `requirements-cloudrun.txt`  
Risque : eleve si test sans deploy multipart ; moyen si double micro persiste ; niveau 2/3 si Tavus est desactive.  
Décision Ludovic requise : oui pour desactivation Tavus ; non pour test multipart et audit double micro.  
Action proposée : deploy dernier main, retest F12, puis traiter double `getUserMedia` si STT passe mais micro instable.
