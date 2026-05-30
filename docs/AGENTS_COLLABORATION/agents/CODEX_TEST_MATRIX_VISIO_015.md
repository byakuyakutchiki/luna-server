# Codex — Matrice de test visio — Objectif 015

Agent : Codex  
Date : 2026-05-31  
Statut : v1  

---

## Principe

Chaque test doit durer moins de 45 secondes. On ne teste pas "au feeling" : chaque target a une preuve attendue.

---

## Tests terrain minimaux

| # | Target | Test Ludovic | Preuve attendue | Valide si |
| --- | --- | --- | --- | --- |
| 1 | Lancement | Ouvrir visio | Avatar apparait sans erreur | room ouverte + pas d'erreur bloquante |
| 2 | Image | Observer avatar 5s | Pas d'etirement visage/corps | rendu propre mobile |
| 3 | Voix | Ecouter salutation | voix FR feminine naturelle | pas d'accent anglais fort, pas de voix pateuse |
| 4 | Micro/STT | Dire "Tu m'entends ?" | log ou reponse indique comprehension | elle repond au contenu |
| 5 | Latence | Dire "Dis simplement oui" | delai mesure | reponse rapide et fluide |
| 6 | Identite | Dire "Comment je m'appelle ?" | reponse Ludovic si contexte dispo | pas d'invention |
| 7 | Note | Dire "Prends une note : test visio" | note/transcript cree | visible dans notes |
| 8 | Fin session | Raccrocher | session stoppee | pas de consommation continue |

---

## Logs attendus sans secret

- `daily_joined`
- `bot_joined` ou equivalent
- piste audio locale `playable/live`
- piste audio remote bot presente
- event de parole utilisateur ou transcript
- event de reponse assistant
- temps entre parole utilisateur et premiere reponse
- erreurs Daily/Simli/TTS si presentes

---

## Regle de validation

Une target n'est pas validee parce que le code existe. Elle est validee seulement si :

1. le test terrain reussit ;
2. le log confirme l'etage technique ;
3. le cout reste raisonnable ;
4. Ludovic juge l'experience acceptable.

---

## Decision Codex actuelle

La visio n'est pas prete pour exploitant.

P0 absolu : prouver la boucle conversationnelle micro -> comprehension -> reponse.

P1 ensuite : voix FR native + image propre.
