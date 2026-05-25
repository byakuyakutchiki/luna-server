# Avis Kimi — Objectif 007 Télémétrie vocale précise APK

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Lisibilité et diagnostic humain pour la télémétrie vocale fine
Date : 2026-05-25
Branche : `kimi/objectif-007-telemetrie-voix`
Contexte réel : seul `voice_session_ended` remonte actuellement — la chronologie est incomplète

---

## 1. Audit de la télémétrie actuelle (point de vue diagnostic)

### Événements déjà instrumentés dans `static/index.html`

| Ligne | Événement | Emplacement | Problème identifié |
|---|---|---|---|
| 7865 | `voice_button_clicked` | Listener bouton | ✅ OK — envoyé avant `startVoice()` |
| 7601 | `microphone_permission_granted` | Après `getUserMedia` success | ✅ OK |
| 7794 | `microphone_permission_denied` | Catch `NotAllowedError` | ✅ OK |
| 7662 | `voice_ws_opened` | `voiceWs.onopen` | ✅ OK |
| 7642 | `voice_audio_sent` | Premier chunk audio (Worklet) | ✅ OK |
| 7701 | `voice_audio_sent` | Premier chunk audio (ScriptProcessor) | ✅ OK |
| 7710 | `voice_audio_received` | `data.type === "audio"` | ✅ OK |
| 7666 | `voice_no_audio_after_timeout` | Timer 20s dans `onopen` | ✅ OK |
| 7756 | `voice_ws_closed` | `voiceWs.onclose` | ✅ OK |
| 7787 | `voice_ws_error` | `voiceWs.onerror` | ✅ OK |
| 7837 | `voice_session_ended` | Dans `stopVoice()` — **conditionné par `if (voiceWs)`** | ⚠️ Si `stopVoice()` est appelé sans WS créé, l'événement ne part pas |

### Pourquoi seul `voice_session_ended` remonte (hypothèse Kimi)

**Constat :** `voice_button_clicked` est envoyé à la ligne 7865, AVANT `startVoice(false)`. Si `startVoice()` plante immédiatement (ligne 7751-7763, bloc catch), le listener du bouton n'a pas de try/catch. L'erreur pourrait interrompre le thread JS avant que `sendApkEvent` ne soit exécuté... sauf que `sendApkEvent` est APPELÉ AVANT `startVoice`, donc il devrait partir.

**Hypothèse plus probable :** `voice_session_ended` est le SEUL événement qui part parce que :
1. `voice_button_clicked` est envoyé (on le voit dans le code)
2. Mais `startVoice()` plante TRÈS tôt — avant même `getUserMedia`
3. Le catch (ligne 7751) met `voiceActive = false` et appelle `stopVoice()` après 3s
4. `stopVoice()` envoie `voice_session_ended` SEULEMENT si `voiceWs` existe
5. **Si `voiceWs` est null** (plantage avant création du WS), `voice_session_ended` n'est pas envoyé non plus

**Attendons** — l'objectif 007 dit que seul `voice_session_ended` remonte. Cela implique que `voiceWs` EXISTE quand `stopVoice()` est appelé, donc le WS a été créé mais quelque chose s'est passé entre la création et l'ouverture, ou après l'ouverture.

**Conclusion pour Kimi :** Quelle que soit la cause technique (mission DeepSeek), le diagnostic cockpit doit être capable de dire "Luna sait que le bouton a été pressé, mais aucun événement entre le clic et la fin de session n'a été reçu".

---

## 2. Nouveaux libellés d'événements validés côté UI

### Événements techniques → Libellés humains

| Événement technique | Libellé UI proposé | Statut Kimi |
|---|---|---|
| `voice_click_received` | Bouton vocal pressé | ✅ Valide |
| `voice_start_entered` | Fonction voix démarrée | ✅ Valide |
| `voice_token_present` | Token d'identification trouvé | ✅ Valide |
| `voice_token_missing` | Token d'identification absent | ✅ Valide |
| `voice_state_blocked` | Session vocale déjà active ou bloquée | ✅ Valide |
| `voice_micro_request_started` | Demande d'accès au microphone | ✅ Valide |
| `voice_micro_permission_granted` | Microphone autorisé | ✅ Valide (existant) |
| `voice_micro_permission_denied` | Microphone refusé | ⚠️ À préciser → "Permission microphone refusée" |
| `voice_ws_create_started` | Création de la connexion vocale | ✅ Valide |
| `voice_ws_create_failed` | Création de la connexion échouée | ✅ Valide |
| `voice_ws_opened` | Connexion vocale ouverte | ✅ Valide (existant) |
| `voice_ws_closed` | Connexion vocale fermée | ✅ Valide (existant) |
| `voice_ws_error` | Problème de connexion vocale | ✅ Valide (existant) |
| `voice_capture_started` | Capture audio démarrée | ✅ Valide |
| `voice_first_audio_chunk_sent` | Premier audio envoyé vers Luna | ✅ Valide (remplace `voice_audio_sent`) |
| `voice_audio_send_failed` | Envoi audio échoué | ✅ Valide |
| `voice_first_audio_chunk_received` | Premier audio reçu de Luna | ✅ Valide (remplace `voice_audio_received`) |
| `voice_playback_started` | Lecture audio démarrée | ✅ Valide |
| `voice_playback_failed` | Lecture audio échouée | ✅ Valide |
| `voice_no_audio_after_timeout` | Luna n'a pas répondu après 20 secondes | ✅ Valide (existant) |
| `voice_session_ended` | Session vocale terminée | ✅ Valide (existant) |

### Recommandation sur la précision

Remplacer les libellés existants trop génériques :
- `voice_audio_sent` → `voice_first_audio_chunk_sent` (précise "premier" et "chunk")
- `voice_audio_received` → `voice_first_audio_chunk_received` (précise "premier" et "reçu de Luna")

Cela permet au cockpit de dire "Premier audio envoyé à 13:04:25" et non juste "Audio envoyé".

---

## 3. Textes cockpit pour les sorties anticipées

### Format appliqué : Luna sait / suppose / recommande / ne peut pas

---

### Sortie A — Token absent ou invalide

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_token_missing`

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, la fonction voix a démarré,
mais le token d'identification n'a pas été trouvé dans le téléphone.
Aucune connexion n'a été tentée.

Luna suppose : l'utilisateur n'est plus connecté, ou le localStorage
a été vidé, ou la session JWT a expiré.

Luna recommande : retourner à l'écran de connexion, se reconnecter,
puis réessayer le bouton vocal.

Luna ne peut pas : générer un token à la place de l'utilisateur.
```

---

### Sortie B — bouton vocal appelé mais startVoice() non lancé

**Chronologie attendue :** `voice_click_received` → (rien d'autre)

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, mais aucun événement
suivant n'a été reçu. La fonction startVoice() n'a pas signalé
son entrée.

Luna suppose : la fonction startVoice() a planté avant de pouvoir
s'exécuter, ou un état bloquant l'a empêchée de démarrer
(JavaScript erreur, mémoire saturée, WebView figée).

Luna recommande : fermer complètement Luna (swipe up) et la rouvrir.
Si le problème persiste, vérifier que l'APK est à jour.

Luna ne peut pas : voir l'erreur exacte côté téléphone sans la
télémétrie d'erreur JavaScript.
```

---

### Sortie C — session déjà active

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_state_blocked`

```
🎙️ Voix APK — Information

Luna sait : le bouton vocal a été pressé, mais une session vocale
était déjà en cours. Le clic a été ignoré par sécurité.

Luna suppose : l'utilisateur a appuyé deux fois rapidement, ou la
session précédente ne s'est pas terminée correctement.

Luna recommande : attendre que la session en cours se termine,
ou appuyer sur le bouton "raccrocher" si visible.

Luna ne peut pas : forcer la fermeture d'une session vocale existante
sans action de l'utilisateur.
```

---

### Sortie D — écran ou état bloquant

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_state_blocked`

```
🎙️ Voix APK — Information

Luna sait : le bouton vocal a été pressé, mais l'application signale
qu'elle est dans un état qui bloque le démarrage vocal.

Luna suppose : un autre onglet, une autre fonction ou une permission
manquante empêche la voix de démarrer.

Luna recommande : revenir à l'écran d'accueil principal de Luna,
vérifier qu'aucun autre appel ou visio n'est en cours, puis réessayer.

Luna ne peut pas : déterminer quel écran ou état bloque sans
télémétrie supplémentaire.
```

---

### Sortie E — permission micro refusée

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_micro_request_started` → `voice_micro_permission_denied`

```
🎙️ Voix APK — Fonctionnement réduit

Luna sait : le bouton vocal a été pressé, la fonction voix a démarré,
la demande d'accès au microphone a été faite... mais l'utilisateur
a refusé la permission.

Luna suppose : le dialogue système Android a été refusé, ou la
permission avait été révoquée précédemment dans les paramètres.

Luna recommande : Paramètres Android → Applications → Luna →
Autorisations → Microphone → Autoriser.

Luna ne peut pas : accorder la permission à la place de l'utilisateur.
```

---

### Sortie F — getUserMedia échoue (autre que permission)

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_micro_request_started` → (pas de granted/denied)

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, la fonction voix a démarré,
la demande d'accès au microphone a été faite... mais le microphone
n'a pas pu être activé. Aucun message de permission n'a été reçu.

Luna suppose : le micro est déjà utilisé par une autre application
(visio, enregistreur), ou le téléphone n'a pas de microphone
détecté, ou la WebView n'a pas le droit d'y accéder.

Luna recommande : fermer les autres applications utilisant le micro,
vérifier que le téléphone n'est pas en mode "Ne pas déranger" avec
micro coupé, puis réessayer.

Luna ne peut pas : libérer le micro occupé par une autre application.
```

---

### Sortie G — WebSocket jamais créé

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_token_present` → `voice_ws_create_failed`

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, le token est présent,
mais la création du WebSocket a échoué avant même d'être tentée.

Luna suppose : l'URL du serveur est incorrecte, le réseau est coupé,
ou la construction de l'URL WebSocket a produit une erreur
JavaScript.

Luna recommande : vérifier la connexion internet, vérifier l'URL
Cloud Run dans l'onglet APK Fondateur, fermer et rouvrir Luna.

Luna ne peut pas : créer la connexion à la place du téléphone.
```

---

### Sortie H — WebSocket créé mais jamais ouvert

**Chronologie attendue :** `voice_click_received` → ... → `voice_ws_create_started` → (pas de `voice_ws_opened`)

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, le micro est autorisé,
le WebSocket a été créé... mais il ne s'est jamais ouvert.
Aucun message `onopen` n'a été reçu.

Luna suppose : le serveur Cloud Run est momentanément inaccessible,
ou le réseau mobile est instable, ou le token a été rejeté par
le serveur.

Luna recommande : vérifier la connexion internet, attendre 30 secondes
et réessayer. Si le problème persiste, vérifier le statut du serveur
dans l'onglet Santé serveur.

Luna ne peut pas : forcer l'ouverture du WebSocket côté serveur.
```

---

### Sortie I — WebSocket fermé avant audio

**Chronologie attendue :** `voice_click_received` → ... → `voice_ws_opened` → `voice_ws_closed` (sans `voice_first_audio_chunk_received`)

```
🎙️ Voix APK — Attention

Luna sait : le bouton vocal a été pressé, le micro est autorisé,
la connexion s'est ouverte... puis s'est fermée avant que Luna
ne réponde vocalement.

Luna suppose : la connexion a été coupée par le serveur (timeout,
quota épuisé), ou par le téléphone (changement de réseau,
fermeture de l'application).

Luna recommande : vérifier le quota voix dans l'onglet Quotas,
vérifier la stabilité du réseau, réessayer.

Luna ne peut pas : savoir qui a fermé la connexion (téléphone
ou serveur) sans les codes de fermeture WebSocket.
```

---

### Sortie J — audio capturé mais non envoyé

**Chronologie attendue :** `voice_click_received` → ... → `voice_capture_started` → (pas de `voice_first_audio_chunk_sent`)

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, le micro est autorisé,
la connexion est ouverte, la capture audio a démarré... mais
aucun chunk audio n'a été envoyé vers le serveur.

Luna suppose : le micro capte du silence (environnement très
bruyant qui déclenche le filtre anti-bruit, ou micro bouché),
ou le thread audio est bloqué dans la WebView.

Luna recommande : parler fort et clairement après avoir appuyé
sur le bouton, vérifier que le micro du téléphone n'est pas
obstrué, tester dans un environnement plus calme.

Luna ne peut pas : entendre ce que le micro capte (pas d'audio
brut conservé).
```

---

### Sortie K — audio reçu mais non joué

**Chronologie attendue :** `voice_click_received` → ... → `voice_first_audio_chunk_received` → `voice_playback_failed`

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, le micro est autorisé,
la connexion est ouverte, Luna a répondu et le téléphone a
reçu l'audio... mais la lecture n'a pas pu démarrer.

Luna suppose : le volume du téléphone est à zéro, ou la WebView
Android ne peut pas jouer de l'audio (restriction système,
mode silencieux), ou le format audio n'est pas supporté.

Luna recommande : vérifier que le volume du téléphone est allumé,
vérifier que le mode "Ne pas déranger" n'est pas actif, tester
avec un casque si possible.

Luna ne peut pas : contrôler le volume du téléphone à distance.
```

---

### Sortie L — timeout sans audio reçu (cas réel Ludovic, affiné)

**Chronologie attendue :** `voice_click_received` → `voice_start_entered` → `voice_token_present` → `voice_micro_request_started` → `voice_micro_permission_granted` → `voice_ws_create_started` → `voice_ws_opened` → `voice_capture_started` → `voice_first_audio_chunk_sent` → `voice_no_audio_after_timeout` → `voice_ws_closed`

```
🎙️ Voix APK — Problème important

Luna sait : à 13:04:22, le bouton vocal a été pressé.
À 13:04:23, la fonction voix a démarré.
À 13:04:23, le token est présent.
À 13:04:23, le microphone a été demandé.
À 13:04:24, le microphone est autorisé.
À 13:04:24, la connexion vocale a été créée.
À 13:04:25, la connexion s'est ouverte.
À 13:04:25, la capture audio a démarré.
À 13:04:26, le premier audio a été envoyé vers Luna.
À 13:04:46, Luna n'a toujours pas répondu après 20 secondes.
À 13:04:46, la connexion s'est fermée.

Luna suppose : la chaîne côté téléphone fonctionne parfaitement
(micro, connexion, envoi audio). Le problème est côté serveur
ou OpenAI Realtime. Trois causes possibles :
  1. OpenAI Realtime n'a pas répondu (quota, clé, modèle indisponible)
  2. Le serveur a reçu la réponse mais ne l'a pas relayée
  3. Le serveur a relayé mais trop tard (timeout déjà déclenché)

Luna recommande :
  • Vérifier le statut OpenAI dans l'onglet Clés
  • Vérifier que le quota voix n'est pas à 0
  • Tester depuis un navigateur desktop pour comparer
  • Si desktop fonctionne → problème WebView Android spécifique
  • Si desktop ne fonctionne pas → problème serveur/OpenAI

Luna ne peut pas :
  • Corriger automatiquement le flux audio
  • Entendre ce que le micro a capturé
  • Forcer OpenAI à répondre plus vite
  • Déterminer seule si le problème est réseau, serveur ou OpenAI
```

---

### Sortie M — Aucun événement entre clic et fin (chronologie vide)

**Chronologie attendue :** `voice_click_received` → `voice_session_ended` (rien entre les deux)

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été pressé, puis la session s'est
terminée. Aucun événement intermédiaire n'a été reçu.

Luna suppose : la fonction startVoice() a planté très tôt,
avant même de pouvoir signaler ses étapes. La WebView Android
a peut-être bloqué l'exécution, ou une erreur JavaScript s'est
produite silencieusement.

Luna recommande :
  • Vérifier que l'APK est bien la version 2.8 (télémétrie complète)
  • Fermer Luna complètement et la rouvrir
  • Si le problème persiste, tester depuis Chrome desktop pour comparer

Luna ne peut pas :
  • Voir les erreurs JavaScript de la WebView sans la console développeur
  • Savoir exactement où startVoice() s'est arrêtée
```

---

## 4. Structure du cockpit fondateur proposée (Objectif 007)

### Deux sections indépendantes

```
┌─────────────────────────────────────────┐
│ 📱 APK Fondateur — Sonde vivante        │  ← Objectif 003/004
│ OK — Téléphone vu il y a 12s            │
│ APK v2.8 active et à jour               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 🎙️ Voix APK — Problème important        │  ← Objectif 007
│ Dernière session : 2026-05-25 13:04:46  │
│                                         │
│ Luna sait :                             │
│   Le bouton a été pressé à 13:04:22     │
│   La fonction voix a démarré            │
│   Le token est présent                  │
│   Le microphone est autorisé            │
│   La connexion s'est ouverte            │
│   La capture audio a démarré            │
│   Le premier audio a été envoyé         │
│   Mais aucune réponse après 20s         │
│                                         │
│ Luna suppose :                          │
│   La chaîne téléphone fonctionne.       │
│   Le problème est côté serveur/OpenAI.  │
│                                         │
│ Luna recommande :                       │
│   Vérifier Clés OpenAI · Vérifier quota │
│   Tester depuis desktop pour comparer   │
│                                         │
│ Luna ne peut pas :                      │
│   Corriger auto · Entendre le micro     │
│   Forcer OpenAI · Déterminer seule      │
│                                         │
│ CHRONOLOGIE                             │
│ 13:04:22 🎙️ Bouton vocal pressé         │
│ 13:04:23 ▶️ Fonction voix démarrée      │
│ 13:04:23 🔑 Token présent               │
│ 13:04:23 📢 Demande micro               │
│ 13:04:24 ✅ Micro autorisé              │
│ 13:04:24 🔗 Connexion créée             │
│ 13:04:25 🔓 Connexion ouverte           │
│ 13:04:25 🎤 Capture audio démarrée      │
│ 13:04:26 📤 Premier audio envoyé        │
│ 13:04:46 ⏱️ Pas de réponse après 20s    │ ← ROUGE
│ 13:04:46 🔒 Connexion fermée            │
└─────────────────────────────────────────┘
```

---

## 5. Règles pour la chronologie visuelle (Objectif 007)

### Icônes par événement

| Événement | Icône | Couleur |
|---|---|---|
| `voice_click_received` | 🎙️ | #94a3b8 |
| `voice_start_entered` | ▶️ | #94a3b8 |
| `voice_token_present` | 🔑 | #4ade80 |
| `voice_token_missing` | 🔑❌ | #f87171 |
| `voice_state_blocked` | 🚫 | #fbbf24 |
| `voice_micro_request_started` | 📢 | #94a3b8 |
| `voice_micro_permission_granted` | ✅ | #4ade80 |
| `voice_micro_permission_denied` | ❌ | #f87171 |
| `voice_ws_create_started` | 🔗 | #94a3b8 |
| `voice_ws_create_failed` | 🔗❌ | #f87171 |
| `voice_ws_opened` | 🔓 | #4ade80 |
| `voice_ws_closed` | 🔒 | #94a3b8 |
| `voice_ws_error` | ⚠️ | #f87171 |
| `voice_capture_started` | 🎤 | #94a3b8 |
| `voice_first_audio_chunk_sent` | 📤 | #4ade80 |
| `voice_audio_send_failed` | 📤❌ | #f87171 |
| `voice_first_audio_chunk_received` | 🔊 | #4ade80 |
| `voice_playback_started` | ▶️🔊 | #4ade80 |
| `voice_playback_failed` | 🔊❌ | #f87171 |
| `voice_no_audio_after_timeout` | ⏱️ | #f87171 |
| `voice_session_ended` | ⏹️ | #94a3b8 |

### Règle d'affichage

- **Vert (#4ade80)** : étape réussie
- **Rouge (#f87171)** : échec ou timeout
- **Orange (#fbbf24)** : avertissement / blocage
- **Gris (#94a3b8)** : étape intermédiaire neutre

Le dernier événement de la chronologie doit toujours être en couleur (jamais gris) pour que Ludovic voit immédiatement où ça s'arrête.

---

## 6. Synthèse Kimi pour l'objectif 007

### Verdict

> **Le cerveau Luna peut voir la panne avec une précision chirurgicale — à condition que les 21 événements soient instrumentés et que le cockpit affiche la chronologie complète.**

### Ce qui manque actuellement

1. **Télémétrie** : seul `voice_session_ended` remonte. DeepSeek doit identifier pourquoi les autres événements ne partent pas.
2. **Journal voix** : toujours absent (identifié dans Objectif 006).
3. **Sorties anticipées** : 13 scénarios de sortie possibles — le cockpit doit avoir un texte pour chacun.

### Ce que ce document apporte

- **21 libellés d'événements** validés en français
- **13 scénarios de sortie anticipée** avec textes complets Luna sait/suppose/recommande/ne peut pas
- **Structure visuelle** du cockpit avec icônes et couleurs
- **Règle d'or** : le dernier événement affiché doit toujours être en couleur (jamais gris)

### Prochaine étape

Après correction technique par DeepSeek + Claude, Ludovic appuie une fois sur le bouton vocal et le cockpit doit afficher une chronologie complète avec un point d'arrêt explicite en couleur.

---

*Document produit par Kimi Code CLI pour l'objectif 007 — branche `kimi/objectif-007-telemetrie-voix`*
