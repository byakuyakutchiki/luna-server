# Codex — Audit web Tavus comme benchmark visio — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : benchmark produit / architecture
Niveau : 0

## Sources consultees

- Tavus Docs — Conversational Video Interface
- Tavus CVI product page
- Tavus FAQ CVI
- Tavus Replica overview
- Tavus Pricing

## Ce qu'est Tavus CVI

Tavus CVI n'est pas seulement un avatar.

C'est une pile conversationnelle video complete :
1. transport WebRTC ;
2. perception audio/video ;
3. gestion du tour de parole ;
4. STT ;
5. LLM ;
6. TTS ;
7. rendu avatar temps reel ;
8. comportements d'ecoute, micro-expressions, emotion, memoire/outils selon configuration.

## Points Tavus pertinents pour Luna

| Tavus | Implication pour Luna |
|---|---|
| Pipeline end-to-end integre | Luna ne peut pas se contenter de Simli + bouts de JS disperses |
| WebRTC temps reel | Latence et media doivent etre penses comme un seul flux |
| Perception Raven : expression, regard, ton, environnement | `Luna voit` doit signifier comprehension reelle, pas juste camera active |
| Sparrow : turn-taking et interruptibilite | La secretaire doit savoir quand ecouter/parler, eviter echo et coupures |
| STT temps reel | Web Speech API WebView n'est pas suffisant si instable |
| TTS configurable | Voix feminine FR naturelle, pas pateuse, pas depressive |
| Phoenix : rendu humain, micro-expressions, lip-sync | L'avatar doit reagir pendant l'ecoute, pas rester figé |
| Function calling / tools | Actions seulement apres confirmations, jamais sensibles automatiquement |
| Memoire / contexte | Si Ludovic est connu, la secretaire doit l'appeler Ludovic |

## Ecart Luna actuel vs Tavus-level

| Axe | Tavus-level | Luna actuel |
|---|---|---|
| Salutation | naturelle et contextualisee | se presente mais appelle `user` si profil absent |
| Tour utilisateur | reponse apres parole | KO : apres salutation, pas de reponse |
| STT | pipeline integre temps reel | non prouve, probablement fragile en WebView |
| Latence | faible, ressentie fluide | lenteur terrain |
| Voix | naturelle et vivante | bizarre / non naturelle |
| Camera | perception multimodale | camera visible, comprehension non prouvee |
| Avatar | ecoute active / micro-expressions | avatar visible mais pas credible comme secretaire |
| Logs | pipeline mesurable | logs JS manquants / DevTools mauvaise cible |

## Decision Codex

La reference Tavus change la strategie.

On ne doit plus demander :
"Comment faire parler Simli ?"

On doit demander :
"Quelle architecture donne une conversation video humaine, reactive et mesurable ?"

Donc la prochaine decision technique doit comparer :
1. continuer Simli + pipeline Luna controle ;
2. integrer Tavus CVI directement ;
3. garder Simli pour avatar seulement et construire STT/LLM/TTS/vision nous-mêmes ;
4. autre fournisseur conversationnel video.

## Garde-fou cout

Tavus a une offre gratuite avec minutes incluses, puis plans payants.
Tout test doit rester court et trace.
Aucun abonnement ou migration fournisseur sans validation Ludovic.

## Action proposee

DeepSeek :
- faire un contre-audit architecture : Simli actuel vs Tavus CVI vs pipeline maison.

Kimi :
- prendre Tavus comme benchmark UX : voix, energie, reactivite, ecoute active.

Claude :
- ne pas coder un patch minimal qui nous enferme dans une architecture incapable d'atteindre Tavus-level.
- proposer un POC controle si Ludovic valide un test Tavus court.

Codex :
- tenir la grille benchmark et refuser validation si la visio reste sous le niveau demande.

