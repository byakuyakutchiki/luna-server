# Codex — Decision prochaine etape audio visio — Objectif 014

Agent : Codex  
Date : 2026-05-30  
Statut : decision apres diagnostic Claude `CLAUDE_DIAGNOSTIC_AUDIO_SILENT_014.md`  

---

## Decision courte

Le diagnostic Claude est coherent : le silence complet apres activation ElevenLabs pointe d'abord vers une voix ElevenLabs inaccessible avec la cle actuelle, ou vers un bloc TTS Simli qui echoue sans fallback.

On ne deploie rien maintenant.

Prochaine etape obligatoire : verifier la voix ElevenLabs hors Simli, avec un test tres court.

---

## Hypothese prioritaire

| Hypothese | Probabilite Codex | Pourquoi |
| --- | --- | --- |
| Voice ID Alice inaccessible avec la cle ElevenLabs | Haute | Avant ElevenLabs : voix par defaut Simli audible. Apres ElevenLabs + Alice : silence complet. |
| Simli accepte la room mais echoue silencieusement sur le TTS | Haute | La room s'ouvre, donc le probleme est apres `roomUrl`. |
| WebView/Daily bloque l'audio | Moyenne-faible | Possible, mais le changement exact coincide avec le passage a ElevenLabs. |
| Env vars absentes | Faible | Claude a verifie leur presence dans Cloud Run. |

---

## Ordre de test impose

### Test 1 — Console navigateur, zero cout

But : savoir si le bot Simli rejoint la room.

Ludovic ou Kimi lance une visio courte et releve seulement les lignes console `[simli]` :

- `daily_createFrame`
- `daily_joined`
- `bot_detected` ou `bot_joined`
- `daily_error`

Si `bot_joined` est absent, le probleme est Simli/Daily/session.

Si `bot_joined` est present mais silence, le probleme est TTS/voice/audio track.

### Test 2 — ElevenLabs direct, cout negligeable, validation Ludovic requise

But : verifier si `6BlZrFdruL4hpXFHmHUC` parle avec la cle ElevenLabs du compte.

Resultats attendus :

- HTTP 200 + MP3 lisible : la voix Alice est accessible, le probleme est cote Simli/payload/Daily.
- HTTP 401/403/422 : la voix n'est pas utilisable avec cette cle ou ce compte. Il faut choisir une voix disponible dans "My Voices" ou ajouter Alice au compte.

Ce test ne doit pas etre publie avec une cle dans GitHub.

---

## Ce que Claude peut faire maintenant

1. Produire une commande de test ElevenLabs sans afficher la cle.
2. Executer le test seulement si Ludovic valide explicitement.
3. Rapporter uniquement le status HTTP, le type d'erreur et la taille du MP3 si succes.
4. Si la voix est invalide, proposer une voix accessible depuis le compte ElevenLabs, sans deployer.
5. Si la voix est valide, passer au diagnostic Simli payload / endpoint / Daily audio track.

---

## Ce que Claude ne doit pas faire

- ne pas changer `ELEVENLABS_VOICE_ID` au hasard ;
- ne pas redeployer Cloud Run ;
- ne pas relancer des sessions Simli longues ;
- ne pas contourner par une barre texte ;
- ne pas publier la cle ElevenLabs ;
- ne pas annoncer "corrige" sans audio entendu par Ludovic.

---

## Ce que DeepSeek doit faire

DeepSeek doit continuer le contre-audit :

- verifier si `ttsProvider`, `ttsAPIKey`, `voiceId`, `elevenlabsLanguageCode` sont bien les champs attendus par Simli ;
- verifier si `/auto/start/configurable` est encore fiable ou deprecie pour ce cas ;
- identifier si Simli renvoie une erreur TTS exploitable quelque part ;
- proposer instrumentation minimale sans secret.

---

## Prompt court pour Claude

Claude, lis :

`docs/AGENTS_COLLABORATION/agents/CODEX_DECISION_AUDIO_NEXT_STEP_014.md`

Decision Codex : ne deploie rien. Le prochain test est ElevenLabs direct hors Simli, uniquement si Ludovic valide explicitement. Tu dois tester si la voix `6BlZrFdruL4hpXFHmHUC` est accessible avec la cle ElevenLabs du compte.

Rapporte seulement :

- status HTTP ;
- erreur type 401/403/422 si echec ;
- taille du MP3 si succes ;
- conclusion : voix accessible ou non.

Aucune cle dans GitHub. Aucun redeploiement.

---

## Prompt court pour Kimi

Kimi, pendant le prochain test visio court, ton role est terrain :

- observer si l'avatar apparait ;
- relever les lignes console `[simli]` ;
- dire si `bot_joined` ou `bot_detected` apparait ;
- noter si l'audio est totalement silencieux ;
- aucun test long, aucun credit gaspille.
