# Codex — Protocole test visio reel — Objectif 017

Date : 2026-06-01
Agent : Codex
Type : proposition
Niveau : 0

## Probleme

Les captures ADB prouvent que la visio s'ouvre, mais elles ne prouvent pas la boucle vivante :
- Ludovic parle ;
- Luna entend ;
- Luna comprend ;
- Luna repond dans un delai humain ;
- Luna voit la camera ;
- Luna contextualise la visio et agit selon la cible.

Le logcat Android ne remonte pas les marqueurs JS utiles (`speech_start`, `llm_start`, `tts_done`, `total_latency_ms`). Il faut donc capturer la visio autrement.

## Protocole de test terrain

Session courte : 30 secondes maximum pour economiser les credits Simli/ElevenLabs.

### 1. Video ecran telephone

But : voir en reel ce que Ludovic voit, pas seulement une photo.

Commande ADB :
```powershell
$adb='C:\Users\saint\Documents\Codex\tools\android-platform-tools\platform-tools\adb.exe'
& $adb shell screenrecord --time-limit 30 /sdcard/luna_visio_test.mp4
& $adb pull /sdcard/luna_visio_test.mp4 docs/AGENTS_COLLABORATION/phone_tests/
```

### 2. Console WebView en direct

But : capter les vrais logs JS pendant la visio.

Etapes :
1. detecter le WebView actif ;
2. `adb forward tcp:9222 localabstract:webview_devtools_remote_<pid>` ;
3. lire `http://127.0.0.1:9222/json` ;
4. attacher un client DevTools au WebSocket ;
5. enregistrer `Runtime.consoleAPICalled` pendant l'appel.

Livrable attendu :
`docs/AGENTS_COLLABORATION/phone_tests/<session>/webview_console_visio.jsonl`

### 3. Script ou bridge si DevTools insuffisant

Si la console WebView reste muette, Claude doit ajouter un bridge debug non sensible :
- soit `window.__lunaVisioLogs` exportable ;
- soit endpoint interne debug non sensible ;
- soit log Android via WebView/console si l'APK le permet.

Interdit :
- pas de secret ;
- pas de contenu audio brut ;
- pas de SMS/appel/paiement ;
- pas de stockage long des donnees personnelles.

## Phrases test standard

Dire seulement ces phrases pendant le test :
1. `Bonjour, est-ce que tu m'entends ?`
2. `Je m'appelle Ludovic. Qui suis-je ?`
3. `Est-ce que tu me vois ?`
4. `Je leve la main. Qu'est-ce que tu vois ?`
5. `Prends une note : appeler Lucas demain.`

## Cibles de performance

| Cible | Acceptable V1 | Premium vise |
|---|---:|---:|
| Detection parole | < 800 ms | < 400 ms |
| Premiere reponse audible | < 3 s | < 1.8 s |
| Tour complet moyen | < 4 s | < 2.5 s |
| Comprehension identite Ludovic | 100% apres contexte | 100% implicite |
| Vision camera | description simple fiable | contexte utile et actionnable |
| Anti-boucle voix | obligatoire | invisible pour l'utilisateur |

## Definition de fini visio

La visio n'est pas validee quand l'avatar apparait seulement.

Elle est validee quand :
1. l'appel se lance sans distorsion ;
2. Luna salue Ludovic avec une voix feminine francaise acceptable ;
3. Luna entend Ludovic ;
4. Luna repond naturellement ;
5. Luna sait que l'utilisateur est Ludovic ;
6. Luna voit au moins une information camera simple ;
7. Luna peut prendre une note contextuelle ;
8. les logs prouvent les etapes et les latences ;
9. aucun cout inutile n'est declenche ;
10. l'UI reste premium et non intrusive.

## Missions agents

Codex :
- capturer video + console pendant un test reel ;
- produire la matrice preuve -> bug -> cause probable -> correctif.

Kimi :
- evaluer l'experience percue : voix, delai, naturel, qualite visuelle, coherence humaine.

DeepSeek :
- auditer la boucle technique STT/LLM/TTS/vision et les risques anti-boucle.

Claude :
- coder seulement apres preuve terrain et cible validee ;
- ne pas deployer sans feu vert Ludovic si changement niveau 2.

