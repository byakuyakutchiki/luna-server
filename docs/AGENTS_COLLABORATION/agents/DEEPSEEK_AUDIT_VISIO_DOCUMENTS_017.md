# DeepSeek — Audit Visio + Documents — Objectif 017

Source : DeepSeek web, transmis par Ludovic le 2026-06-01.
Agent : DeepSeek
Type : avis / risque / proposition
Niveau : 0

## Verdict court

Visio :
- Maillon le plus probablement cassé : STT WebView + risque d'écho Simli.
- La latence est structurelle : pas de streaming TTS et pas de warm-up ElevenLabs.
- La vision caméra n'est pas prouvée dans le flux visio.

Documents :
- L'onglet mobile Documents reste sur une surface v1.
- Le vrai dashboard porte-document existe plutôt dans `static/documents.html` et les routes `/api/documents/v2/*`.
- Ces routes v2 ne sont pas encore intégrées clairement dans l'onglet mobile principal.

Patch immédiat recommandé :
- Visio : attendre la capture Codex, puis si STT natif KO, ajouter fallback STT serveur type Whisper/OpenAI + anti-écho.
- Documents : brancher l'onglet mobile sur les routes v2 ou intégrer une surface mobile du dashboard v2.

Patch interdit pour l'instant :
- Activer la caméra/vision sans protocole de test Codex.
- Déployer la visio sans preuve STT.
- Supprimer la surface Documents v1 sans validation UX Kimi et sauvegarde.
- Scanner des documents personnels sans consentement explicite.

## Note Codex de coordination

DeepSeek écrit que `static/index.html` n'appelle aucune API côté Documents.
Correction Codex : l'onglet mobile appelle bien des APIs v1 / secrétaire, mais il ne surface pas clairement `/api/documents/v2/*`.

Le fond du diagnostic reste valide : le mobile n'affiche pas encore le vrai porte-document attendu.

## Visio — Analyse technique

| Maillon | État probable | Preuve attendue | Risque | Correctif minimal |
|---|---|---|---|---|
| STT WebView | Très probablement cassé ou instable. Web Speech API souvent non fiable en Android WebView. | Console WebView : présence de `SpeechRecognition` / `webkitSpeechRecognition`, logs `speech_reco`, `speech_start`. | Reconnaissance silencieuse ou incompréhension. | Fallback STT serveur si API absente ou KO. |
| Écho Simli | Probable si le micro capte la voix de l'avatar/TTS. | Logs montrant que le STT capture la salutation ou la réponse d'Iris. | Boucle audio, phrases incohérentes, "je ne comprends pas". | Couper/ignorer le STT pendant playback + constraints `echoCancellation`, `noiseSuppression`. |
| JWT/auth | Probablement OK si la visio se lance, mais à vérifier pour `/api/visio/chat`. | Status HTTP `/api/visio/chat`, erreurs 401/403. | Echec silencieux côté utilisateur. | Vérifier token/refresh avant session. |
| `/api/visio/chat` | Probablement fonctionnel mais non prouvé en situation réelle. | Logs `llm_start`, `llm_done`, texte entrant/sortant. | Réponse lente ou non pertinente. | Ne pas patcher sans preuve. |
| `/api/visio/tts` | Fonctionnel mais latence ElevenLabs possible. | Logs `tts_start`, `tts_done`, taille audio, status HTTP. | Voix tardive, expérience cassée. | Warm-up/cache si latence confirmée. |
| ElevenLabs | Voix configurée mais qualité perçue KO. | Paramètres voix et rendu terrain. | Voix bizarre / non naturelle. | Ajuster voix et paramètres après boucle conversationnelle prouvée. |
| Audio playback WebView | Probablement OK, mais à vérifier. | Logs `audio_play_start`, `audio_play_blocked`, `audio_play_end`. | Audio bloqué/distordu. | `audioContext.resume()` après geste utilisateur si nécessaire. |
| Vision caméra | Non prouvée. | Capture/log montrant frame caméra transmise à un modèle vision et réponse exploitable. | Faux affichage "Luna voit" sans perception réelle. | Ne pas activer sans protocole Codex. |

## Documents — Analyse technique

| Surface | Fichier/route | État actuel | Gap | Correctif minimal |
|---|---|---|---|---|
| Onglet mobile Documents | `static/index.html` | Surface minimale avec compteurs, recherche, scanner, filtre `Tous`, documents générés. | Pas encore le porte-document complet. | Brancher un dashboard mobile v2. |
| Dashboard Documents v2 | `static/documents.html` | Interface plus proche du porte-document : catégories, timeline, actions. | Non intégré à l'onglet mobile principal. | Lier ou intégrer dans `index.html`. |
| Routes API v2 | `luna_web.py` `/api/documents/v2/*` | Routes présentes : dashboard, catégories, timeline, actions. | Surface mobile ne les utilise pas clairement. | Appeler v2 depuis l'onglet mobile. |
| Scan | `static/index.html` + routes docs | Scan visible mais expérience porte-document non prouvée. | Classification/action post-scan non visible sur l'écran réel. | Test avec document factice non sensible. |
| Consentement / RGPD | UI Documents | Consentement non visible dans la capture mobile. | Risque données personnelles. | Ajouter garde-fou consentement avant scan/upload. |
| Documents générés | `static/index.html` | Mélangés dans le même espace. | Confusion avec documents scannés. | Séparer `Porte-document` et `Documents générés`. |

## Décision proposée à Codex

Codex doit tester :
1. disponibilité réelle de `SpeechRecognition` dans WebView ;
2. logs `speech_reco`, `speech_start`, `llm_done`, `tts_done`, `audio_play_*`, `total_latency_ms` ;
3. latence `/api/visio/chat` et `/api/visio/tts` ;
4. disponibilité des routes `/api/documents/v2/*` sous JWT.

Kimi doit valider :
1. UX mobile du dashboard v2 ;
2. clarté de la promesse porte-document ;
3. séparation documents scannés / documents générés ;
4. consentement avant scan.

Claude peut coder seulement après preuve :
1. fallback STT serveur si Web Speech API KO ;
2. anti-écho si le STT capture la voix d'Iris ;
3. branchement v2 Documents si Kimi valide la surface mobile.

Ludovic doit éviter de valider pour l'instant :
1. activation caméra/vision sans protocole ;
2. déploiement visio sans capture STT ;
3. suppression v1 sans backup ;
4. scan de vrais documents sensibles avant consentement.

## Message AGENT_CHANNEL.md prêt à copier

Agent : DeepSeek
Objectif : 017
Type : avis / risque / proposition
Résumé : 5 lignes max
Visio : STT WebView probablement cassé ou instable + risque d'écho Simli non traité. Recommandé : capture Codex d'abord, puis fallback STT serveur/Whisper si API Web Speech KO, anti-écho si la voix d'Iris est recaptée. Documents : onglet mobile encore sur surface v1, dashboard v2 existe mais n'est pas intégré. Risques : latence, voix non naturelle, confusion Documents v1/v2, consentement RGPD avant scan.
Fichier concerné : static/simli.html ; static/index.html ; static/documents.html ; luna_web.py
Risque : élevé pour visio ; moyen pour Documents/RGPD
Décision Ludovic requise : oui pour tout déploiement visio, caméra/vision, scan réel de document sensible
Action proposée : Codex capture WebView/logs ; Kimi valide UX Documents v2 mobile ; Claude code uniquement après preuve ; DeepSeek maintient audit technique.

