# Luna Avatar Assets

Objectif : centraliser les references visuelles Luna pour Objectif 013 Visio, Simli et futurs avatars video.

Regle : ces fichiers sont des sources de reference, pas encore des assets production. Ne pas remplacer l'avatar Simli, Tavus ou l'UI sans validation Ludovic.

## Dossier partage

Tous les agents doivent utiliser ce dossier :

`docs/assets/luna_avatar_sources/`

La VM recupere les fichiers avec `git pull`. Windows les garde dans le repo local. La planche rapide est :

`docs/assets/luna_avatar_sources/contact_sheet.jpg`

## References principales

| Fichier | Origine | Usage conseille |
| --- | --- | --- |
| `luna_adulte_reference.jpg` | Windows Downloads, `luna.photo.adulte.jpg` | Reference prioritaire avatar Luna adulte / Simli |
| `luna_app_avatar_current.jpg` | App actuelle, `static/assets/luna_avatar.jpg` | Reference avatar existant dans Luna |
| `luna_app_child_current.png` | App actuelle, `static/assets/luna_enfant.png` | Reference Luna enfant actuelle |
| `luna_doll_reference_01.jpg` | Windows Downloads | Reference style Luna doll |
| `luna_doll_reference_02.jpg` | Windows Downloads | Reference style Luna doll |
| `luna_doll_reference_03.jpg` | Windows Downloads | Reference style Luna doll |
| `luna_doll_reference_04.jpg` | Windows Downloads | Reference style Luna doll |
| `luna_doll_decor_reference.jpg` | Windows Downloads | Decor / ambiance |
| `luna_decor_reference_02.jpg` | Windows Downloads | Decor / ambiance |
| `luna_transition_imaginaire_reference.jpg` | Windows Downloads | Ambiance transition / imaginaire |
| `luna_video_home_thumb.jpg` | `docs/video/avatars` | Reference video/presentation |
| `luna_video_gloria_bright_thumb.jpg` | `docs/video/avatars` | Reference avatar video |
| `luna_video_gloria_warm_thumb.jpg` | `docs/video/avatars` | Reference avatar video |
| `luna_video_thumb_001.jpg` a `luna_video_thumb_005.jpg` | `docs/video/avatars` | References miniatures video |

## Decision Ludovic requise

Validation obligatoire avant :

- creation d'un avatar Simli public/base sur ces sources ;
- changement du `SIMLI_FACE_ID` ;
- remplacement de l'avatar visible en production ;
- modification voix/genre/persona de Luna en visio.

## Action Objectif 013

Kimi : verifier quelle image correspond le mieux a l'identite Luna adulte.

DeepSeek : auditer ou se configure `SIMLI_FACE_ID`, la voix et le flux conversationnel.

Codex : garder ce catalogue a jour et ne pas pousser de secrets ni de fichiers sensibles.
