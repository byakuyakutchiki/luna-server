# DeepSeek — Contre-audit commit 3012fb9

**Objectif :** 017 — Visio Iris  
**Fichier audité :** `static/simli.html`  
**Commit audité :** `3012fb9`  
**Type :** contre-audit technique

## Verdict DeepSeek

Déployable pour test terrain : **oui, sous condition**.

Le patch Claude est solide et les diagnostics couvrent le cycle :

`micro -> VAD -> MediaRecorder -> Whisper -> LLM -> TTS`

Score estimé : **83/100**.

Points forts relevés :
- diagnostic `AudioContext` initial + reprise si suspendu ;
- suivi piste micro ;
- logs RMS parole/silence ;
- logs `MediaRecorder` chunks + blob size ;
- statuts HTTP STT / LLM / TTS ;
- détection de conflit Daily/Simli ;
- fallback PTT conservé.

## Angles morts signalés par DeepSeek

1. `track.muted` doit être vérifié explicitement.
2. Les `401 JWT` doivent éviter un échec silencieux.

## Arbitrage Codex

Après vérification locale du commit `3012fb9` :

- `track.muted` est **déjà présent** dans le log `vad_track` :
  `label=... state=... enabled=... muted=...`
- En revanche, aucun endpoint `/api/auth/refresh` n'existe dans le dépôt au moment de cet audit.

Donc il ne faut **pas** demander à Claude de coder un appel aveugle vers `/api/auth/refresh`.

La bonne correction minimale est :

1. garder `track.muted` dans `vad_track` ;
2. ajouter un `warn` explicite si `t0.muted === true` ;
3. pour `401`, afficher un message clair côté utilisateur : session expirée, reconnectez-vous ;
4. ne pas ajouter de refresh automatique tant qu'une vraie route serveur n'est pas définie.

## Décision

Déployable pour test terrain : **oui** si le test vise à collecter les logs.

Mini-patch recommandé avant test long :

- `vad_track_muted` si piste live mais muette ;
- message utilisateur propre sur `401` ;
- pas de refresh token fantôme.

## Message canal agent

Agent : DeepSeek / Codex  
Objectif : 017  
Type : contre-audit / arbitrage  
Résumé : Patch `3012fb9` validé pour test terrain. DeepSeek estime le diagnostic à 83/100. Codex corrige deux points : `track.muted` est déjà loggé, mais il manque un warning dédié ; `/api/auth/refresh` n'existe pas, donc pas de refresh automatique à coder sans route serveur.  
Fichier concerné : `static/simli.html`  
Risque : moyen si on code un endpoint inexistant ; faible si on se limite à logs + message session expirée.  
Décision Ludovic requise : non pour mini-patch diagnostic ; oui pour création d'un vrai système refresh auth.  
Action proposée : Claude ajoute `vad_track_muted` + message 401 clair, puis déploiement test terrain court.
