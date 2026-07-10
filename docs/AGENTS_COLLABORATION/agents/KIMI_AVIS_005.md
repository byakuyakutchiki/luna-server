# Avis Kimi — Objectif 005 Événements voix APK

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Textes cockpit voix + validation libellés événements
Date : 2026-05-25
Branche : `kimi/objectif-005-events-voix`
Contexte réel : Ludovic a testé l'APK, bouton vocal silencieux après 15-20 secondes

---

## 1. Validation des 10 libellés d'événements côté UI

### Libellés techniques → Libellés humains validés

| # | Événement technique | Libellé UI proposé | Statut Kimi | Commentaire |
|---|---|---|---|---|
| 1 | `voice_button_clicked` | Bouton vocal appuyé | ✅ Valide | Factuel, neutre, court |
| 2 | `microphone_permission_granted` | Microphone autorisé | ✅ Valide | Confirme le succès de la permission |
| 3 | `microphone_permission_denied` | Microphone refusé | ⚠️ À préciser | Peut être confondu avec "Luna a refusé". Proposition : "Permission micro refusée par l'utilisateur" ou "Microphone non autorisé" |
| 4 | `voice_ws_opened` | Connexion vocale ouverte | ✅ Valide | Clair, évite le jargon "WebSocket" |
| 5 | `voice_audio_sent` | Audio envoyé vers Luna | ✅ Valide | Met en perspective utilisateur→serveur |
| 6 | `voice_audio_received` | Luna répond vocalement | ✅ Valide | Confirme que l'audio est reçu ET destiné à être joué |
| 7 | `voice_no_audio_after_timeout` | Luna n'a pas répondu après 20 secondes | ✅ Valide | Ne culpabilise pas, ne parle pas d'"erreur" |
| 8 | `voice_ws_closed` | Connexion vocale fermée | ✅ Valide | Neutre, attend le contexte pour le ton |
| 9 | `voice_ws_error` | Problème de connexion vocale | ✅ Valide | "Problème" est plus doux que "erreur" |
| 10 | `voice_session_ended` | Session vocale terminée | ✅ Valide | Neutre, couvre stop manuel et fin normale |

### Recommandations sur les libellés

- **Événement 3** (`microphone_permission_denied`) : le libellé court "Microphone refusé" est ambigu. Dans le cockpit, préférer : **"L'utilisateur a refusé l'accès au microphone"** ou **"Permission microphone non accordée"**. Cela distingue clairement l'action utilisateur d'un refus technique.
- **Événement 7** (`voice_no_audio_after_timeout`) : le libellé ne doit jamais contenir le mot "erreur" ni "échec". Le cas réel de Ludovic est exactement celui-ci. Le texte doit rester descriptif : "Luna n'a pas répondu après 20 secondes" = factuel.
- **Événement 8** (`voice_ws_closed`) : le libellé seul ne dit pas si c'est normal ou anormal. Le cockpit doit contextualiser avec les événements précédents.

---

## 2. Textes cockpit fondateur par scénario

### Format appliqué systématiquement

```
🎙️ Voix APK — [Statut]

Luna sait : [faits observés, chronologie]
Luna suppose : [hypothèse la plus probable, avec incertitude]
Luna recommande : [action concrète pour Ludovic]
Luna ne peut pas : [limite claire, pas de fausse promesse]
```

---

### Scénario A — Succès complet (référence)

**Chronologie :** `voice_button_clicked` → `microphone_permission_granted` → `voice_ws_opened` → `voice_audio_sent` → `voice_audio_received` → `voice_session_ended`

```
🎙️ Voix APK — Tout va bien

Luna sait : le bouton vocal a été appuyé, le microphone est autorisé,
la connexion s'est ouverte, du audio a été envoyé et Luna a répondu
vocalement. La session s'est terminée normalement.
Durée : 2 min 34 s.

Luna suppose : la chaîne complète fonctionne sur ce téléphone.

Luna recommande : aucune action. La voix est opérationnelle.

Luna ne peut pas : vérifier que l'utilisateur a bien entendu (volume,
qualité audio, environnement bruyant).
```

---

### Scénario B — Cas réel Ludovic : silence après 15-20 secondes

**Chronologie :** `voice_button_clicked` → `microphone_permission_granted` → `voice_ws_opened` → `voice_audio_sent` → `voice_no_audio_after_timeout` → `voice_ws_closed`

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été appuyé à 13:04:22, le microphone est
autorisé, la connexion vocale s'est ouverte, du audio a été envoyé vers
le serveur... mais aucun audio n'a été reçu en retour après 20 secondes.
La connexion s'est fermée à 13:04:45.

Luna suppose : le problème se situe entre le serveur OpenAI Realtime
et le retour audio vers le téléphone. Trois causes possibles :
  1. OpenAI Realtime n'a pas répondu (quota épuisé, clé invalide, modèle indisponible)
  2. Le serveur a reçu la réponse audio mais ne l'a pas relayée correctement
  3. La réponse a été envoyée au téléphone mais la WebView ne l'a pas jouée
Luna ne sait pas laquelle de ces trois causes est la bonne.

Luna recommande :
  • Vérifier le statut OpenAI dans l'onglet Clés (ANTHROPIC_KEY_CHAT / OPENAI_API_KEY)
  • Vérifier que le quota voix n'est pas épuisé
  • Ouvrir la console développeur de la WebView (si possible) pour voir
    si des messages d'erreur JavaScript apparaissent après le clic vocal
  • Tester la voix depuis un navigateur desktop (Chrome) pour comparer :
    si ça marche sur desktop mais pas sur APK, le problème est côté WebView

Luna ne peut pas :
  • Corriger automatiquement le flux audio
  • Forcer le téléphone à jouer du son
  • Déterminer seule si le problème est réseau, serveur, OpenAI ou WebView
```

**⚠️ Ce qui ne faut PAS écrire (anti-pattern identifié) :**

```
❌ "Erreur voix : le service ne fonctionne pas"               → trop vague, culpabilisant
❌ "Tu n'as pas entendu Luna parler"                           → suppose que Ludovic attendait, fausse certitude
❌ "OpenAI est en panne"                                       → Luna ne sait pas ça, elle suppose
❌ "Le micro ne marche pas"                                    → faux, le micro a été autorisé et audio a été envoyé
❌ "Recommence en appuyant sur le bouton"                      → anxiogène si Ludovic l'a déjà fait 5 fois
```

---

### Scénario C — Permission micro refusée

**Chronologie :** `voice_button_clicked` → `microphone_permission_denied`

```
🎙️ Voix APK — Fonctionnement réduit

Luna sait : le bouton vocal a été appuyé, mais l'accès au microphone
a été refusé. Aucun audio n'a pu être capturé.

Luna suppose : l'utilisateur a refusé la permission quand Android
l'a demandée, ou l'avait déjà refusée auparavant.

Luna recommande :
  • Aller dans Paramètres Android > Applications > Luna > Autorisations
  • Activer "Microphone"
  • Fermer Luna complètement (swipe up) et la rouvrir

Luna ne peut pas :
  • Contourner la permission Android
  • Forcer l'activation du micro à distance
```

---

### Scénario D — WebSocket ne s'ouvre pas

**Chronologie :** `voice_button_clicked` → `microphone_permission_granted` → `voice_ws_error`

```
🎙️ Voix APK — Problème important

Luna sait : le bouton vocal a été appuyé, le microphone est autorisé,
mais la connexion vocale n'a pas pu s'ouvrir.

Luna suppose : le réseau mobile/WiFi bloque le WebSocket, ou le serveur
Cloud Run est momentanément indisponible, ou le token d'authentification
est invalide.

Luna recommande :
  • Vérifier la connexion internet du téléphone
  • Attendre 30 secondes et réessayer
  • Si le problème persiste, vérifier que l'URL Cloud Run est correcte
    dans l'onglet APK Fondateur

Luna ne peut pas :
  • Ouvrir la connexion à la place du téléphone
  • Contourner un blocage réseau
```

---

### Scénario E — Audio envoyé mais aucune réponse reçue (timeout long)

**Chronologie :** `voice_button_clicked` → `microphone_permission_granted` → `voice_ws_opened` → `voice_audio_sent` → (silence prolongé) → `voice_ws_closed`

```
🎙️ Voix APK — Attention

Luna sait : le bouton vocal a été appuyé, le micro est autorisé,
la connexion s'est ouverte, du audio a été envoyé... mais la session
s'est fermée sans que Luna ait répondu vocalement.

Luna suppose : OpenAI Realtime a peut-être reçu l'audio mais n'a pas
produit de réponse (silence de l'utilisateur, audio trop faible,
problème de format PCM). Ou bien le serveur a coupé la session
pour un autre motif (quota, timeout serveur).

Luna recommande :
  • Parler clairement et fort en appuyant sur le bouton
  • Vérifier que le quota voix n'est pas à 0 dans l'onglet Quotas
  • Tester depuis un navigateur desktop pour comparer

Luna ne peut pas :
  • Entendre ce que le micro a capturé (pas d'audio brut conservé)
  • Savoir si l'utilisateur a parlé ou non pendant la session
```

---

### Scénario F — Reconnexion automatique déclenchée

**Chronologie :** `voice_button_clicked` → ... → `voice_ws_closed` → `voice_ws_opened` (reconnexion)

```
🎙️ Voix APK — Attention

Luna sait : la connexion vocale s'est interrompue, puis le téléphone
a tenté de se reconnecter automatiquement (tentative 1/3).

Luna suppose : une coupure réseau temporaire, ou le serveur a fermé
le WebSocket (timeout, erreur OpenAI).

Luna recommande : attendre la fin des tentatives de reconnexion.
Si la reconnexion échoue après 3 essais, fermer la session vocale
et réessayer.

Luna ne peut pas :
  • Garantir la reconnexion sur un réseau instable
  • Conserver la session vocale pendant une coupure prolongée
```

---

### Scénario G — Aucun événement voix jamais reçu (cas objectif 003 non déployé)

```
🎙️ Voix APK — Information

Luna sait : le téléphone fondateur envoie des signaux réguliers
(heartbeat), mais Luna n'a jamais reçu d'événement vocal.

Luna suppose : soit le bouton vocal n'a jamais été testé, soit la
télémétrie voix (objectif 005) n'est pas encore activée sur ce
téléphone, soit les événements n'arrivent pas au serveur.

Luna recommande :
  • Si tu n'as jamais testé : appuie sur le bouton vocal et parle
  • Si tu as déjà testé et que c'était silencieux : le diagnostic
    actuel confirme le bug. Pas besoin de réessayer pour l'instant.
  • Si tu as testé avec succès : la télémétrie voix n'est pas encore
    installée sur cette version de l'APK.

Luna ne peut pas :
  • Savoir si tu as déjà appuyé sur le bouton sans que l'événement
    soit remonté
  • Distinguer "pas testé" de "testé mais silencieux" sans événements
```

---

## 3. Chronologie visuelle proposée pour le cockpit

Format ligne de temps (affichage fondateur.html) :

```
13:04:22  🎙️ Bouton vocal appuyé
13:04:23  ✅ Microphone autorisé
13:04:24  🔗 Connexion vocale ouverte
13:04:25  📤 Audio envoyé vers Luna
13:04:45  ⏱️  Luna n'a pas répondu après 20 secondes
13:04:45  🔒 Connexion vocale fermée
```

**Règles d'affichage :**
- Heure précise pour chaque événement
- I cohérents et colorés selon le statut
- Le timeout de 20s doit être visuellement distinct (icône ⏱️ ou sablier)
- La durée entre `voice_audio_sent` et `voice_no_audio_after_timeout` doit être affichée

---

## 4. Textes pour l'API `GET /api/admin/apk-diagnosis` (champ `voice_summary`)

### Variantes par combinaison d'événements

| voice_status | voice_summary proposé |
|---|---|
| `voice_ok` | Bouton appuyé, micro OK, connexion ouverte, audio envoyé et reçu — session normale |
| `no_audio_timeout` | Bouton appuyé, micro OK, connexion ouverte, audio envoyé — mais aucune réponse de Luna après 20s |
| `permission_denied` | Bouton appuyé — mais le microphone n'a pas été autorisé |
| `ws_failed` | Bouton appuyé, micro OK — mais la connexion vocale n'a pas pu s'ouvrir |
| `ws_closed_no_audio` | Connexion ouverte puis fermée sans réponse audio |
| `reconnecting` | Connexion interrompue, reconnexion en cours (tentative X/3) |
| `never_tested` | Aucun événement vocal reçu depuis ce téléphone |
| `js_error` | Erreur JavaScript détectée pendant la session vocale |

---

## 5. Règles rédactionnelles pour l'objectif 005

### Ce qu'il faut faire

1. **Toujours commencer par la chronologie factuelle** : "Luna sait : à 13:04:22, le bouton a été appuyé..."
2. **Toujours distinguer observation et supposition** : "Luna suppose : ... Luna ne sait pas si..."
3. **Toujours proposer une action concrète** : pas "résoudre le problème", mais "vérifier le quota voix"
4. **Toujours indiquer la limite** : "Luna ne peut pas : corriger automatiquement"
5. **Jamais de jugement** : pas "tu n'as pas", "erreur", "échec", "obsolète"
6. **Jamais de certitude sans preuve** : pas "OpenAI est en panne", mais "OpenAI n'a pas répondu"

### Ce qu'il ne faut pas faire

| ❌ Interdit | ✅ À la place |
|---|---|
| "Erreur voix" | "Luna n'a pas reçu de réponse audio" |
| "Le micro ne marche pas" | "Le microphone n'a pas été autorisé" ou "Aucun audio n'a été envoyé" |
| "Tu n'as pas entendu" | "Aucun audio n'a été reçu par le téléphone" |
| "Recommence" | "Attends 30 secondes et réessaye si tu veux tester à nouveau" |
| "C'est un bug" | "Ce comportement correspond au problème connu (objectif 001)" |
| "OpenAI est en panne" | "OpenAI n'a pas répondu dans les 20 secondes" |
| "L'APK est cassée" | "La connexion s'est fermée sans réponse audio" |

---

## 6. Synthèse Kimi pour l'implémentation

### Livrable attendu de Claude

Dans `fondateur.html`, section voix, afficher :

```html
<div id="voiceDiagCard" class="section" style="border-color:#7c3aed40;">
  <h2>🎙️ Voix APK</h2>
  <div id="voiceDiagBody">
    <!-- Rempli dynamiquement par JS selon l'API -->
  </div>
</div>
```

Structure JSON attendue côté serveur pour le JS :

```json
{
  "voice_status": "no_audio_timeout",
  "voice_summary": "Bouton appuyé, micro OK, connexion ouverte, audio envoyé — mais aucune réponse de Luna après 20s",
  "voice_events": [
    {"event": "voice_button_clicked", "ts": "13:04:22", "label": "Bouton vocal appuyé"},
    {"event": "microphone_permission_granted", "ts": "13:04:23", "label": "Microphone autorisé"},
    {"event": "voice_ws_opened", "ts": "13:04:24", "label": "Connexion vocale ouverte"},
    {"event": "voice_audio_sent", "ts": "13:04:25", "label": "Audio envoyé vers Luna"},
    {"event": "voice_no_audio_after_timeout", "ts": "13:04:45", "label": "Luna n'a pas répondu après 20 secondes"},
    {"event": "voice_ws_closed", "ts": "13:04:45", "label": "Connexion vocale fermée"}
  ],
  "luna_knows": "le bouton vocal a été appuyé à 13:04:22, le microphone est autorisé, la connexion s'est ouverte, du audio a été envoyé... mais aucun audio n'a été reçu en retour après 20 secondes",
  "luna_guesses": "le problème se situe entre le serveur OpenAI Realtime et le retour audio vers le téléphone",
  "luna_recommends": "vérifier le statut OpenAI, vérifier le quota voix, tester depuis desktop pour comparer",
  "luna_cannot": "corriger automatiquement le flux audio, forcer le téléphone à jouer du son, déterminer seule si le problème est réseau, serveur, OpenAI ou WebView"
}
```

### Priorité d'implémentation

1. **Texte pour `voice_no_audio_after_timeout`** → C'est le cas réel de Ludovic. Doit être parfait dès le premier déploiement.
2. **Texte pour `microphone_permission_denied`** → Deuxième cause la plus fréquente.
3. **Texte pour `voice_ws_error`** → Troisième cause.
4. **Texte succès (`voice_audio_received`)** → Référence pour comparer.
5. **Texte "jamais testé"** → Pour la phase de transition avant que Ludovic ne teste.

---

*Document produit par Kimi Code CLI pour l'objectif 005 — branche `kimi/objectif-005-events-voix`*
