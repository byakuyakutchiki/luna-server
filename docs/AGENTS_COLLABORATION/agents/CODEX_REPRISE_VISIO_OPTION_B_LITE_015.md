# Codex — Reprise Objectif 015 apres test terrain

Date : 2026-06-01  
Agent : Codex  
Type : decision coordination  
Niveau : 0/2

## Retour terrain Ludovic

Ludovic a reteste la visio apres les derniers travaux :

- la voix est un peu meilleure ;
- Iris ne repond toujours pas de facon fiable ;
- Ludovic parle, son micro fonctionne, mais Iris ne semble pas exploiter la parole ;
- Iris ne comprend toujours pas ce qui se passe a la camera ;
- il faut arreter les tests au feeling et prouver la chaine par etage.

## Etat code constate

Le code actuel contient bien l'Option B-lite :

```text
Web Speech API -> /api/visio/chat -> /api/visio/tts -> lecture audio frontend
```

Fichiers concernes :

- `static/simli.html`
- `luna_web.py`

Endpoints presents :

- `POST /api/visio/chat`
- `POST /api/visio/tts`

Marqueurs attendus en console F12 pour une phrase simple :

```text
speech_start
speech_end
stt_done
llm_start
llm_done
tts_start
tts_done
audio_play_start
audio_play_end
total_latency_ms
```

## Decision Codex

Le prochain travail n'est plus de choisir une nouvelle voix ou de retoucher l'avatar.

Le P0 est de savoir ou casse la chaine B-lite :

| Logs observes | Conclusion | Responsable |
|---|---|---|
| aucun `speech_start` | code B-lite non deploie, SpeechRecognition non lance, ou navigateur bloque | Claude |
| `speech_start` sans `llm_start` | bug frontend dans `_irisReply()` ou garde `_irisReplying` bloquee | Claude |
| `llm_start` sans `llm_done` | endpoint `/api/visio/chat` KO, auth/JWT, OpenAI ou erreur serveur | Claude + DeepSeek |
| `tts_start` sans `tts_done` | endpoint `/api/visio/tts` KO, ElevenLabs, voix, timeout | Claude + Kimi |
| `audio_play_start` sans reponse utile | audio joue mais experience produit encore mauvaise | Kimi + Codex |
| `total_latency_ms` > 4000 regulierement | conversation non fluide V1 | Kimi + DeepSeek |
| `vision_no_track` | vision camera non branchee dans le parent ; Daily iframe ne suffit pas | Claude + DeepSeek |

## Missions immediates

### Claude

1. Confirmer sur GitHub la revision Cloud Run active et le commit exact deploye.
2. Confirmer que `f224954` / Option B-lite est bien dans la revision active.
3. Ajouter si necessaire une preuve serveur non sensible pour `/api/visio/chat` et `/api/visio/tts`.
4. Corriger uniquement le point qui casse la chaine B-lite.
5. Ne pas deployer une autre architecture sans validation Ludovic.

### DeepSeek

1. Auditer le code reel Option B-lite dans `static/simli.html` et `luna_web.py`.
2. Verifier les risques : authFetch/JWT, blocage audio navigateur, Web Speech API sur cible mobile/WebView, boucle `_irisReplying`, cout ElevenLabs.
3. Produire une conclusion courte : "cause probable + patch minimal + risque".
4. Pousser sur GitHub. Si ce n'est pas sur GitHub, ce n'est pas livre.

### Kimi

1. Garder Camille comme voix de test provisoire.
2. Ne plus relancer de tests voix payants tant que la boucle conversationnelle n'est pas prouvee.
3. Juger l'experience seulement apres presence de `total_latency_ms`.
4. Proteger le rendu : pas de barre texte visible lourde, pas d'UI qui casse la vision Luna.

### Codex

1. Tenir la matrice de preuve.
2. Bloquer les travaux disperses.
3. Remonter a Ludovic uniquement les decisions niveau 2/3.

## Vision camera

La vision n'est pas resolue par B-lite.

Le log `vision_no_track` veut dire que le code ne recupere pas une vraie frame camera exploitable depuis la page parent. Il faut une tache separee :

```text
camera parent getUserMedia -> frame courte -> analyse vision -> injection contexte Iris
```

Cette correction est niveau 2/3 si elle implique camera, OpenAI vision, consentement utilisateur, cout API ou changement workflow.

## Definition de succes V1

Une visio est acceptable seulement si :

- Iris entend une phrase simple de Ludovic ;
- Iris repond en francais en 1 a 2 phrases ;
- le temps total est < 3 s dans 80% des tours simples ;
- le temps total est < 4 s dans 95% des tours simples ;
- aucun echo de sa propre voix n'est re-capture comme demande utilisateur ;
- la camera a un statut clair : "non activee", "autorisee mais non analysee", ou "analyse OK".

