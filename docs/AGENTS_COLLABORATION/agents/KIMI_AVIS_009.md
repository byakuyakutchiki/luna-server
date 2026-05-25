# Avis Kimi — Objectif 009 Stabilité voix Luna

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Diagnostic humain cockpit pour les coupures vocales prématurées
Date : 2026-05-25
Branche : `kimi/objectif-009-stabilite-voix`
Contexte : la voix fonctionne maintenant (gpt-realtime-mini), mais Luna coupe parfois en parlant

---

## 1. Distinction cruciale à afficher dans le cockpit

Le problème "pas de voix du tout" est **résolu** (Objectif 008 validé).
Le problème "voix qui coupe" est **nouveau** (Objectif 009).

Le cockpit doit afficher clairement cette distinction pour éviter que
Ludovic pense qu'on reparle de l'ancien problème.

### Bannière de contexte recommandée

```
🎙️ Voix APK — Stabilité

Contexte : la voix fonctionne. La connexion est établie.
Le problème actuel est une interruption pendant la réponse.
Ce n'est pas le même problème que le silence total (résolu).
```

---

## 2. Nouveaux événements de stabilité à instrumenter

| Événement technique | Déclencheur | Libellé UI |
|---|---|---|
| `voice_first_audio_chunk_received` | Premier delta audio reçu d'OpenAI | Premier son reçu de Luna |
| `voice_playback_started` | Le téléphone commence à jouer l'audio | Lecture audio démarrée |
| `voice_playback_gap_detected` | Silence > 500ms entre deux chunks | Coupure dans la lecture |
| `voice_audio_truncated` | Réponse OpenAI terminée avant la fin | Réponse tronquée |
| `voice_user_interrupted` | VAD détecte que l'utilisateur parle | Utilisateur a interrompu Luna |
| `voice_ws_closed_during_response` | WS fermé alors que Luna parlait | Connexion coupée pendant la réponse |
| `voice_session_ended_after_partial` | Session terminée après réponse incomplète | Session terminée — réponse incomplète |
| `voice_max_duration_warning` | 1 minute avant fin max | Avertissement : 1 minute restante |
| `voice_max_duration_reached` | 5 minutes atteintes | Durée maximum atteinte |

---

## 3. Les 5 scénarios de coupure vocale

### Scénario A — Luna a commencé à parler puis s'est arrêtée

**Chronologie :** `voice_button_clicked` → ... → `voice_first_audio_chunk_received` → `voice_playback_started` → `voice_playback_gap_detected` → (silence)

```
🎙️ Voix APK — Stabilité — Coupure détectée
Dernière session : 2026-05-25 18:47:05

Luna sait :
• Le bouton vocal a été pressé à 18:47:05
• Luna a commencé à répondre à 18:47:07
• La lecture audio a démarré correctement
• Un silence anormal a été détecté à 18:47:12
  (coupure de 1.2 seconde sans audio)
• La connexion WebSocket était encore ouverte

Luna suppose :
Le flux audio d'OpenAI s'est interrompu en cours de génération,
ou un chunk audio n'a pas été relayé par le serveur jusqu'au
téléphone. La WebView elle-même n'a pas coupé la lecture.

Luna recommande :
• Attendre 2-3 secondes — Luna reprend parfois après une pause
• Si le silence persiste : appuyer sur le bouton vocal pour
  relancer une nouvelle phrase
• Si le problème est systématique : noter l'heure exacte du test
  pour vérifier les logs serveur

Luna ne peut pas :
• Forcer la reprise du flux audio interrompu
• Distinguer une pause naturelle d'une coupure technique
• Savoir si OpenAI a fini sa phrase ou s'est arrêtée en cours
```

---

### Scénario B — La session a été fermée pendant la réponse

**Chronologie :** `voice_button_clicked` → ... → `voice_first_audio_chunk_received` → `voice_playback_started` → `voice_ws_closed_during_response` → `voice_session_ended_after_partial`

```
🎙️ Voix APK — Stabilité — Session coupée
Dernière session : 2026-05-25 18:47:05

Luna sait :
• Le bouton vocal a été pressé à 18:47:05
• Luna a commencé à répondre
• La connexion WebSocket s'est fermée à 18:47:09
  ALORS QUE Luna était encore en train de parler
• La session s'est terminée avec une réponse incomplète

Luna suppose :
La connexion a été fermée par le serveur (timeout, erreur bridge)
ou par le téléphone (changement de réseau, verrouillage écran,
appui accidentel sur le bouton raccrocher).

Luna recommande :
• Vérifier que le téléphone n'a pas verrouillé l'écran
• Vérifier que le réseau WiFi/mobile est stable
• Vérifier que le bouton "raccrocher" n'a pas été touché
• Relancer la voix pour une nouvelle session

Luna ne peut pas :
• Empêcher la fermeture du WebSocket si le réseau coupe
• Savoir qui a fermé la connexion (serveur ou téléphone)
• Récupérer la fin de la phrase interrompue
```

---

### Scénario C — Le serveur a coupé avant la fin

**Chronologie :** `voice_button_clicked` → ... → `voice_first_audio_chunk_received` → `voice_playback_started` → `voice_ws_closed_during_response` (close code serveur)

```
🎙️ Voix APK — Stabilité — Serveur
Dernière session : 2026-05-25 18:47:05

Luna sait :
• Le bouton vocal a été pressé
• Luna a commencé à répondre
• Le serveur a fermé la connexion WebSocket à 18:47:09
  avec le code de fermeture : 1006 (abnormal closure)
• La réponse était incomplète

Luna suppose :
Le serveur Luna a rencontré une erreur pendant le relay audio :
  • timeout du bridge vocal dépassé
  • erreur OpenAI Realtime non gérée
  • ping WebSocket non reçu côté serveur
  • mémoire serveur insuffisante sur Cloud Run

Luna recommande :
• Noter l'heure exacte de la coupure (18:47:09)
• Vérifier les logs Cloud Run à cette heure précise
• Vérifier le statut du serveur dans l'onglet Santé
• Si le problème est récurrent : augmenter le timeout du
  bridge vocal côté serveur

Luna ne peut pas :
• Voir les logs serveur depuis le téléphone
• Corriger la configuration du bridge vocal
• Garantir la stabilité du réseau entre Cloud Run et OpenAI

⚠️ Validation Ludovic requise
La correction nécessite une modification côté serveur
(web_voice_bridge.py) et potentiellement un redéploiement.
```

---

### Scénario D — OpenAI a arrêté la génération

**Chronologie :** `voice_button_clicked` → ... → `voice_first_audio_chunk_received` → `voice_playback_started` → `voice_audio_truncated` → (pas de gap, mais fin abrupte)

```
🎙️ Voix APK — Stabilité — Génération
Dernière session : 2026-05-25 18:47:05

Luna sait :
• Le bouton vocal a été pressé
• Luna a commencé à répondre
• La réponse audio s'est terminée brusquement à 18:47:11
• Aucune coupure réseau détectée
• Le WebSocket est resté ouvert

Luna suppose :
OpenAI Realtime a considéré sa réponse comme terminée, ou a
coupé la génération pour l'une de ces raisons :
  • Le modèle a jugé la réponse suffisante (fin naturelle)
  • Le VAD (Voice Activity Detection) a détecté un bruit
    interprété comme une interruption utilisateur
  • Le quota de tokens par réponse a été atteint
  • Une erreur interne OpenAI a stoppé la génération

Luna recommande :
• Si la réponse semblait complète → c'est probablement normal
• Si la réponse était clairement incomplète → relancer la voix
  et demander "Continue ta phrase"
• Si le problème est systématique → vérifier les paramètres
  VAD côté serveur (threshold, silence_duration_ms)

Luna ne peut pas :
• Forcer OpenAI à générer une réponse plus longue
• Savoir pourquoi OpenAI a arrêté exactement
• Modifier les paramètres VAD d'OpenAI Realtime
```

---

### Scénario E — Le téléphone n'a pas joué toute la réponse

**Chronologie :** `voice_button_clicked` → ... → `voice_first_audio_chunk_received` → `voice_playback_started` → `voice_playback_gap_detected` → (pas d'autre événement, mais WS ouvert)

```
🎙️ Voix APK — Stabilité — Téléphone
Dernière session : 2026-05-25 18:47:05

Luna sait :
• Le bouton vocal a été pressé
• Luna a commencé à répondre
• La lecture audio a démarré
• La lecture s'est interrompue sur le téléphone à 18:47:10
• Le serveur continuait d'envoyer de l'audio (WebSocket ouvert)
• D'autres chunks audio ont été reçus après la coupure

Luna suppose :
La WebView Android a interrompu le playback audio :
  • Le téléphone a reçu un appel entrant
  • L'utilisateur a changé d'application
  • La WebView a été mise en arrière-plan par le système
  • Le mode "Ne pas déranger" s'est activé
  • Le buffer audio de la WebView a débordé

Luna recommande :
• Ne pas quitter Luna pendant que Luna parle
• Désactiver les notifications ou le mode "Ne pas déranger"
• Si un appel entrant arrive : la voix reprendra après le raccroché
• Essayer avec un casque Bluetooth pour isoler le problème

Luna ne peut pas :
• Empêcher le système Android de couper le son
• Contrôler le buffer audio de la WebView
• Savoir si l'utilisateur a changé d'application
```

---

## 4. Chronologie visuelle pour la stabilité

### Icônes supplémentaires pour les événements de coupure

| Événement | Icône | Couleur |
|---|---|---|
| `voice_first_audio_chunk_received` | 🔊 | #4ade80 |
| `voice_playback_started` | ▶️ | #4ade80 |
| `voice_playback_gap_detected` | ⏸️ | #fbbf24 |
| `voice_audio_truncated` | ✂️ | #f87171 |
| `voice_user_interrupted` | 🗣️ | #60a5fa |
| `voice_ws_closed_during_response` | 🔒❌ | #f87171 |
| `voice_session_ended_after_partial` | ⏹️⚠️ | #f87171 |
| `voice_max_duration_warning` | ⏱️ | #fbbf24 |
| `voice_max_duration_reached` | ⏱️🔴 | #f87171 |

### Règle d'affichage spécifique stabilité

- Si la chronologie se termine par `voice_audio_truncated` → **orange**
- Si la chronologie se termine par `voice_ws_closed_during_response` → **rouge**
- Si la chronologie se termine par `voice_playback_gap_detected` → **orange**
- Si la chronologie contient `voice_max_duration_reached` → **info** (normal, pas un bug)

---

## 5. Messages cockpit par type de coupure

### Message générique si le type exact est inconnu

```
🎙️ Voix APK — Stabilité — Coupure détectée

Luna sait : Luna a commencé à répondre mais la voix s'est
interrompue avant la fin de la phrase.

Luna suppose : la coupure peut venir d'OpenAI (génération
stoppée), du serveur (connexion coupée), ou du téléphone
(playback interrompu).

Luna recommande : relancer la voix. Si le problème est
systématique, noter l'heure exacte pour vérifier les logs.

Luna ne peut pas : déterminer automatiquement la cause exacte
de la coupure sans les logs serveur.
```

---

## 6. Différenciation dans le cockpit : ancien vs nouveau problème

### Ancien problème (résolu) — silence total

```
🔇 Voix APK — Problème important (résolu)
Symptôme : aucun son, aucune réponse de Luna.
Cause : solde OpenAI insuffisant.
Statut : corrigé après recharge.
```

### Nouveau problème (Objectif 009) — coupure en parlant

```
🎙️ Voix APK — Stabilité — Coupure détectée
Symptôme : Luna commence à parler puis s'arrête.
Cause : en cours d'analyse.
Statut : investigation active.
```

---

## 7. Synthèse Kimi pour l'objectif 009

### Livrables

1. **9 nouveaux événements** de stabilité avec libellés validés
2. **5 scénarios de coupure** complets (Luna sait / suppose / recommande / ne peut pas)
3. **1 message générique** si le type exact est inconnu
4. **Distinction ancien/nouveau** problème à afficher dans le cockpit
5. **Chronologie visuelle** avec icônes et couleurs spécifiques stabilité

### Verdict

> **La voix fonctionne. Le nouveau problème est l'interruption pendant la réponse. Le cockpit doit clairement distinguer ce nouveau symptôme de l'ancien problème (silence total), et donner à Ludovic des actions concrètes selon la cause probable.**

---

*Document produit par Kimi Code CLI pour l'objectif 009 — branche `kimi/objectif-009-stabilite-voix`*
