# Codex — Validation terrain UI mobile apres deploiement d024283

Agent : Codex  
Objectif : 017  
Date : 2026-06-01  
Type : validation terrain  

## Contexte

Claude a deploye sur Cloud Run :

- revision : `luna-beta-00470-5h9`
- commit : `d024283`
- objet : correction UI mobile `LUNA` vertical, bulle etroite, message `Visio lancee`

Codex a relance Luna sur telephone reel via ADB et capture l'ecran.

## Preuves

Dossier :

```text
docs/AGENTS_COLLABORATION/phone_tests/codex-after-d024283-20260601-195803/
```

Fichiers :

- `screen.png`
- `focus.txt`
- `adb_devices.txt`
- `logcat_recent_filtered.txt`

Focus Android :

```text
fr.yawatch.luna/.MainActivity
```

## Verdict visuel

| Point teste | Verdict | Commentaire |
|---|---|---|
| `LUNA` vertical | OK | Le nom `LUNA` est maintenant horizontal sur les bulles visibles. |
| Bulle tres etroite | Ameliore | La bulle vide/courte ne s'effondre plus en largeur extreme comme avant. |
| `Visio lancee` dans historique | Partiel | Les anciens messages sauvegardes restent visibles. Cela ne prouve pas que le nouveau toast/non-persist ne fonctionne pas. |

## Interpretation

Le patch corrige le rendu futur, mais ne nettoie pas l'historique deja pollue.

Les messages `Visio lancee (3 min prevues)` visibles dans la capture peuvent etre des messages anciens deja persistants avant `d024283`.

Il ne faut donc pas demander un rollback.

## Prochaine verification

Pour confirmer le point 3, il faut :

1. lancer une nouvelle visio tres courte ;
2. verifier qu'un toast apparait ;
3. verifier qu'aucun nouveau message `Visio lancee` n'est ajoute dans l'historique ;
4. recharger Luna ;
5. verifier que le toast n'a pas ete persiste.

Attention : test court uniquement, pas de session longue Simli/ElevenLabs.

## Decision Codex

Le correctif `d024283` est valide pour :

- `LUNA` vertical ;
- largeur minimale des bulles courtes.

Il reste a valider en test futur :

- non-persistance des nouveaux messages `Visio lancee`.

Option future non urgente :

- nettoyer/masquer les anciens messages systeme deja sauvegardes dans l'historique, si Ludovic valide.

