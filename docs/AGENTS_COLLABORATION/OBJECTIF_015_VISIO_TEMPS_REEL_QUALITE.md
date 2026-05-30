# Objectif 015 — Visio temps reel exploitable

Date : 2026-05-31  
Owner produit : Ludovic  
Coordination : Codex  
Statut : ouvert  

---

## Pourquoi on ouvre 015

Objectif 014 a permis de cadrer la vision et de debloquer la sortie audio. Mais le test terrain apres `luna-beta-00465-6wh` montre que la visio n'est pas encore exploitable.

Retour Ludovic :

- la voix parle, mais elle n'est pas naturelle ;
- accent anglais trop prononce ;
- delai trop long avant la parole ;
- voix percue comme lourde/pateuse, presque en crise ;
- image/avatar encore distordu ;
- l'assistante n'entend pas correctement Ludovic ;
- elle ne repond pas de maniere conversationnelle.

Conclusion : on doit arreter les micro-patches au hasard. Il faut prouver la chaine temps reel complete.

---

## Definition de reussite

La visio est validee seulement si, sur un test terrain court (< 45s), Ludovic peut :

1. lancer la visio ;
2. voir un avatar non distordu ;
3. entendre une voix feminine francaise credible ;
4. parler une phrase simple ;
5. etre compris sans repeter ;
6. recevoir une reponse pertinente en moins de quelques secondes ;
7. demander une action simple non sensible, par exemple "prends une note de test" ;
8. constater que la note ou le transcript existe ;
9. raccrocher sans consommation inutile.

---

## Targets P0/P1

| Priorite | Target | Critere terrain |
| --- | --- | --- |
| P0 | Micro/STT | Ludovic dit une phrase simple, elle est comprise |
| P0 | Reponse conversationnelle | Iris repond au contenu, pas seulement au firstMessage |
| P0 | Latence | Reponse ressentie comme fluide, pas interminable |
| P1 | Voix | Feminine, francaise, naturelle, pas anglaise/pateuse |
| P1 | Identite | Ne dit pas "Riff", ne cree pas de confusion Luna/Iris |
| P1 | Image | Avatar non etire, stable, propre |
| P1 | Preuve | Logs non secrets prouvent chaque etage |

---

## Architecture actuelle a auditer

Chemin actuel :

1. `luna_web.py` cree une session via `https://api.simli.ai/auto/start/configurable`.
2. Le frontend ouvre `roomUrl` dans Daily.js iframe.
3. Simli joue un `firstMessage` avec ElevenLabs.
4. On espere que Simli gere ensuite micro -> STT -> LLM -> TTS -> avatar.

Risque majeur : ce mode "auto/start/configurable + Daily iframe" est opaque. On ne controle pas clairement STT, LLM, TTS, latence, events, ni piste audio. La documentation Simli actuelle recommande plutot LiveKit, Pipecat ou SDKs quand on veut controler une stack de voice bot temps reel.

Sources a prendre en compte :

- Simli docs : `https://docs.simli.com/`
- Simli SDK JS : `https://docs.simli.com/api-reference/javascript`
- Simli custom WebRTC : `https://docs.simli.com/api-reference/simli-webrtc`
- ElevenLabs TTS : `https://elevenlabs.io/docs/api-reference/text-to-speech/convert/`

---

## Decision Codex

On ne fait plus de deploiement correctif direct tant que les agents n'ont pas produit une preuve par etage.

Le prochain travail n'est pas "changer encore une ligne". Le prochain travail est :

1. instrumenter ou lire les logs pour savoir si Ludovic est capture ;
2. mesurer la latence ;
3. auditer si l'architecture Simli auto peut vraiment faire une conversation bidirectionnelle fiable ;
4. tester et choisir une voix francaise native ;
5. stabiliser le ratio image seulement apres diagnostic exact.

---

## Repartition agents

### Claude — Integrateur / instrumentation

Mission : prouver ou infirmer la chaine micro/STT/reponse/image dans le code actuel.

Livrable :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_INSTRUMENTATION_VISIO_015.md`

Doit couvrir :

- events Daily reels disponibles ;
- piste audio locale publiee ou non ;
- piste audio bot recue ou non ;
- `conversation.utterance` recu ou non ;
- transcript utilisateur alimente ou non ;
- latence entre parole utilisateur et reponse ;
- CSS/iframe responsable ou non de la distorsion ;
- patch d'instrumentation minimal, non secret, sans UI intrusive.

Interdit : redeployer une correction fonctionnelle sans validation.

### DeepSeek — Audit architecture / faisabilite

Mission : dire si le mode Simli actuel est le bon pour les targets.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_VISIO_015.md`

Doit comparer :

- option A : garder Simli auto/start/configurable ;
- option B : Simli SDK / WebRTC avec pipeline controle ;
- option C : LiveKit/Pipecat + Simli avatar ;
- option D : secours temporaire : STT navigateur local -> LLM -> TTS/Simli.

Pour chaque option :

- faisabilite ;
- temps d'implementation ;
- cout ;
- risque ;
- controle voix/STT/latence ;
- compatibilite Cloud Run ;
- decision Ludovic requise.

### Kimi — Qualite voix/image/UX

Mission : proteger la credibilite humaine.

Livrable :

`docs/AGENTS_COLLABORATION/agents/KIMI_QUALITE_VISIO_015.md`

Doit proposer :

- 3 voix feminines FR candidates maximum, testables sur ElevenLabs ;
- phrase de test unique pour comparer les voix ;
- criteres : naturel, accent, rythme, chaleur, professionnalisme ;
- correction image premium sans etirement ;
- decision claire : voix actuelle acceptable ou non.

### Codex — Coordination / matrice de validation

Mission : produire la matrice de tests et bloquer les deploiements non prouves.

Livrable :

`docs/AGENTS_COLLABORATION/agents/CODEX_TEST_MATRIX_VISIO_015.md`

Doit contenir :

- 8 tests terrain courts ;
- resultat attendu ;
- logs attendus ;
- cout estime ;
- qui execute ;
- quand on considere la target validee.

---

## Interdictions communes

- pas de session Simli longue ;
- pas de SMS/appel/email/paiement/reservation ;
- pas de secret dans GitHub ;
- pas de changement UI majeur sans validation Ludovic ;
- pas de deploiement Cloud Run sans feu vert ;
- pas de "c'est bon teste" sans preuve par target.

---

## Prompt complet a donner a Claude

Claude, lis :

`docs/AGENTS_COLLABORATION/OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`

Retour terrain apres `luna-beta-00465-6wh` :

- Iris parle mais la voix est mauvaise : accent anglais, qualite non naturelle, lenteur, impression de voix lourde/pateuse ;
- image/avatar encore distordu ;
- surtout : Ludovic parle mais Iris n'entend pas/ne repond pas correctement.

Ta mission n'est pas de redeployer encore un patch au hasard.

Mission Claude :

1. auditer le code courant `static/simli.html` et `luna_web.py` ;
2. identifier quelles preuves manquent pour micro/STT/reponse ;
3. proposer instrumentation minimale non visible ;
4. prouver si Daily publie la piste audio locale ;
5. prouver si Simli emet `conversation.utterance` ou equivalent ;
6. prouver si le bot publie une piste audio remote ;
7. analyser pourquoi l'avatar reste distordu malgre le patch ;
8. produire :

`docs/AGENTS_COLLABORATION/agents/CLAUDE_INSTRUMENTATION_VISIO_015.md`

Interdits :

- pas de deploiement ;
- pas de secret ;
- pas de nouvelle UI visible ;
- pas de session longue ;
- pas d'action sensible.

---

## Prompt complet a donner a DeepSeek

DeepSeek, lis :

`docs/AGENTS_COLLABORATION/OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`

Mission DeepSeek :

Faire l'audit architecture de la visio. On doit savoir si le mode actuel Simli `auto/start/configurable + Daily iframe` peut vraiment remplir les targets :

- comprendre Ludovic ;
- repondre vite ;
- voix feminine FR naturelle ;
- avatar non distordu ;
- logs/preuves exploitables ;
- cout maitrise.

Compare :

1. garder Simli auto/start/configurable ;
2. passer Simli SDK/WebRTC ;
3. passer LiveKit/Pipecat + Simli ;
4. secours temporaire STT navigateur local -> LLM -> TTS.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_ARCHI_VISIO_015.md`

Pour chaque option : faisabilite, cout, risque, controle, delai, decision Ludovic.

Pas de secret, pas de deploiement, pas de session longue.

---

## Prompt complet a donner a Kimi

Kimi, lis :

`docs/AGENTS_COLLABORATION/OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`

Mission Kimi :

Ludovic juge la voix actuelle inacceptable : accent anglais, voix non naturelle, lente, pateuse. L'image/avatar reste distordu.

Tu dois proteger la credibilite humaine de Luna/Iris.

Livrable :

`docs/AGENTS_COLLABORATION/agents/KIMI_QUALITE_VISIO_015.md`

Attendu :

1. verdict sur la voix actuelle : acceptable ou non ;
2. 3 voix feminines FR candidates maximum dans ElevenLabs, a tester ;
3. une phrase de test unique pour comparer les voix ;
4. criteres de choix : naturel, accent FR, chaleur, rythme, professionnalisme ;
5. proposition image/avatar : comment eviter distorsion sans casser l'immersion ;
6. decision Ludovic requise.

Pas de deploiement, pas de session longue, pas de changement graphique majeur.

