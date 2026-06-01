# Codex — Cible qualité visio niveau Tavus — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : cadrage produit / risque
Niveau : 0

## Demande Ludovic

L'objectif visio Luna n'est pas une simple visio qui affiche un avatar et lit une phrase.

La cible explicite est une experience au niveau Tavus :
- voix naturelle ;
- reactivite forte ;
- reponse rapide ;
- presence vivante ;
- secretaire dynamique ;
- interaction fluide ;
- sentiment d'une personne utile et alerte, pas d'un bot lent ou depressif.

Citation intention produit :
> "Je veux le meme niveau, la meme qualite, la meme reactivite, reponse voix naturelle. J'ai demande une secretaire reactive et dynamique, pas depressive."

## Cible non négociable

La visio Luna/Iris est NON VALIDEE tant que l'experience ne donne pas :

| Axe | Cible V1 acceptable | Cible premium visee |
|---|---|---|
| Voix | feminine FR naturelle, pas pateuse | chaleureuse, claire, vivante |
| Latence premiere reponse | < 3 s | < 1.8 s |
| Tour complet moyen | < 4 s | < 2.5 s |
| Compréhension | phrases standard 100% | conversation naturelle robuste |
| Energie | professionnelle, alerte | secretaire dynamique et rassurante |
| Camera | voit au moins une action simple | comprend le contexte visuel |
| UI | pas de libelle `Chatbot`, pas de bricolage | experience premium coherente Luna |
| Logs | chaque maillon mesurable | monitoring continu léger |

## Ce qui est explicitement hors cible

- voix lente, pateuse, robotique ou avec accent bizarre ;
- reponses "je ne comprends pas" sur phrases simples ;
- avatar qui parle seul sans ecouter ;
- salutation initiale sans dialogue ensuite ;
- latence longue sans indicateur ;
- statut `Luna voit` sans perception reelle ;
- libelle `Chatbot` visible dans une experience secretaire ;
- test qui consomme credits sans preuve technique.

## Implication technique

Simli peut rester l'avatar si utile, mais Luna doit controler la boucle intelligente :

`micro -> STT fiable -> LLM -> TTS naturel -> playback -> vision -> actions non sensibles`

Si la pile actuelle ne permet pas cette qualite, l'equipe doit proposer une architecture alternative :
- STT serveur/OpenAI/Whisper si Web Speech API WebView est trop faible ;
- TTS premium configure pour voix FR naturelle ;
- anti-echo obligatoire ;
- logs de latence obligatoires ;
- vision camera réelle via frame/image vers un modele vision, jamais simple badge.

## Decision Codex

La cible Tavus-level devient la reference de validation UX.

Claude ne doit pas corriger seulement "pour que ca parle".
Kimi ne doit pas valider une voix "moins pire".
DeepSeek ne doit pas s'arreter a "techniquement possible".
Codex ne valide pas tant que Ludovic ne ressent pas une secretaire reactive, claire et utile.

## Prochaine action

1. DeepSeek contre-audite la capture actuelle avec cette cible Tavus-level.
2. Claude ajoute le bridge logs post-salutation.
3. Kimi definit la grille UX voix/reaction/energie.
4. Codex relance un test court apres instrumentation.

