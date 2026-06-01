# Codex — Acces telephone reel — Objectif 017

Agent : Codex  
Objectif : 017  
Date : 2026-06-01  
Type : validation + risque UI

## Resume

Codex est maintenant connecte au telephone Android via ADB TCP depuis Windows :

```text
192.168.1.98:5555 device product:amethyst_eea model:24115RA8EG device:amethyst
```

Luna a ete lancee via ADB sans action sensible :

```text
fr.yawatch.luna/.MainActivity
```

## Preuves

Dossier :

```text
docs/AGENTS_COLLABORATION/phone_tests/codex-luna-20260601-182019/
```

Fichiers :

- `screen.png`
- `adb_devices.txt`
- `focus.txt`
- `logcat_recent_filtered.txt`

## Observation terrain immediate

La capture montre bien Luna ouverte sur telephone reel.

Etat ecran :

- onglet Chat visible ;
- mode Compagnon actif ;
- barre haute Luna visible ;
- boutons principaux visibles ;
- plusieurs messages "Visio lancee (3 min prevues)" dans l'historique ;
- un message/bulle est rendu beaucoup trop etroit, avec les lettres de "LUNA" empilees verticalement ;
- cette anomalie est une regression visuelle mobile a auditer.

## Logs

Les logs courts ne montrent pas encore les marqueurs visio attendus :

```text
speech_start
llm_start
tts_done
total_latency_ms
vision_no_track
```

Cause : la capture actuelle prouve l'acces telephone et l'etat UI, pas encore une session visio active testee en direct.

## Decision Codex

L'objectif 017 est valide cote acces :

- Claude voit le telephone depuis la VM ;
- Codex voit le telephone depuis Windows ;
- les captures/logs peuvent maintenant etre produits directement par Codex ;
- les autres agents doivent lire les preuves GitHub au lieu de deviner.

Mais la visio n'est pas encore validee.

## Prochaine action utile

1. Tester d'abord le bug UI mobile visible : bulles trop etroites / "LUNA" vertical.
2. Ensuite seulement lancer une visio courte avec logcat direct.
3. Pendant la visio, chercher :

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
vision_no_track
```

## Interdits maintenus

- aucun SMS ;
- aucun appel reel ;
- aucun paiement ;
- aucune reservation ;
- aucun test long Simli/ElevenLabs ;
- aucun deploiement sans validation Ludovic.

