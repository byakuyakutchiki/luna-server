# Codex — Analyse logs terrain visio — Objectif 015

Agent : Codex
Date : 2026-05-31
Source : logs console Ludovic apres deploiement avec instrumentation

---

## Verdict court

Les logs prouvent que :

1. La room Simli demarre.
2. Le micro local est publie (`probe_local_audio playable`).
3. Le bot Simli rejoint la room.
4. Le bot publie de l'audio (`probe_bot_audio playable`).
5. Le navigateur capte bien des phrases via `SpeechRecognition`.
6. Mais Simli ne produit pas d'utterance utilisateur exploitable.
7. Le pont STT local `conversation.echo` ne declenche pas de vraie reponse conversationnelle.
8. La vision camera ne marche pas (`vision_no_track camera non disponible`).
9. Le STT local capte aussi la voix de l'assistante, ce qui cree un risque de boucle.

Conclusion : la visio n'est pas une conversation temps reel fiable.

---

## Preuves dans les logs

### Ce qui fonctionne

```text
createVisioCall_ok provider=simli
daily_joined simli
bot_joined ...
probe_local_audio playable
probe_bot_audio playable
speech_reco demarre fr-FR
speech_captured est-ce que tu m'entends
```

Interpretation :

- Le probleme n'est plus la permission micro brute.
- Le probleme n'est plus la sortie audio du bot.
- Le navigateur entend Ludovic.

### Ce qui ne fonctionne pas

```text
local_stt_bridge_sent est-ce que tu m'entends
app_msg_ {"type":""}
```

Interpretation :

- Le message envoye via `conversation.echo` n'est pas traite comme une vraie parole utilisateur par Simli.
- Aucun `stt_user_utterance` natif Simli n'apparait.
- Aucun `latency_ms` user -> assistant n'apparait.

Donc le flux Simli auto ne prouve pas : micro -> STT -> LLM -> reponse.

### Boucle dangereuse observee

```text
speech_captured comment puis-je vous aider
local_stt_bridge_sent comment puis-je vous aider
speech_captured je ne comprends pas tout a fait ta question...
local_stt_bridge_sent je ne comprends pas tout a fait ta question...
```

Interpretation :

- `SpeechRecognition` capte la voix d'Iris sortie par les haut-parleurs.
- Le pont local renvoie cette phrase au bot.
- Cela peut creer une boucle ou parasiter la conversation.

Decision Codex : le pont STT local automatique est desactive par defaut dans le code.

### Vision camera non fonctionnelle

```text
vision_no_track camera non disponible
```

Interpretation :

- La piste video locale n'est pas accessible au code de vision.
- Iris ne peut pas repondre "je te vois" avec l'architecture actuelle.
- La camera dans l'iframe Daily ne suffit pas a fournir un track exploitable au script parent.

---

## Decision architecture

Option A (`Simli auto/start/configurable + Daily iframe`) n'atteint pas les targets P0 avec les preuves actuelles.

Elle peut rester comme mode avatar/TTS temporaire, mais elle ne doit plus etre consideree comme architecture principale pour :

- STT fiable ;
- vision camera ;
- logs complets ;
- reponse conversationnelle garantie.

La recommandation Codex devient :

1. garder l'instrumentation ;
2. desactiver le pont STT automatique ;
3. ne pas multiplier les redeploiements de l'Option A ;
4. demander a DeepSeek/Claude une decision Option B : Simli SDK/WebRTC ou pipeline controle ;
5. choisir une voix FR native avant nouveau test produit.

---

## Patch Codex applique

Fichier : `static/simli.html`

Ajout :

```javascript
var _localSttBridgeEnabled = false;
```

Le pont local n'envoie plus automatiquement les phrases captees vers Simli.

Raison : il capte aussi la voix d'Iris et peut provoquer une boucle.

---

## Prochaines actions imposees

### Claude

1. Lire ce rapport.
2. Ne pas redeployer le pont STT auto comme solution.
3. Proposer une architecture conversationnelle controlee ou un mode test explicite, pas automatique.
4. Verifier pourquoi la camera n'est pas accessible (`vision_no_track`).

### DeepSeek

1. Mettre a jour son audit architecture avec ces logs.
2. Dire clairement si Option A doit etre abandonnee pour le STT/vision.
3. Evaluer Option B comme prochaine vraie implementation.

### Kimi

1. Continuer choix voix FR native.
2. Ne pas valider l'experience tant que le flux conversationnel n'est pas prouve.

---

## Decision Ludovic

Avant tout nouveau deploiement, il faut choisir :

1. Veut-on deployer seulement la desactivation du pont STT auto pour eviter la boucle ?
2. Veut-on passer a une implementation Option B plus controlee ?
3. Quelle voix FR native retenir pour les prochains tests ?
