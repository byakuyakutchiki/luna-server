# Test UX Visio Luna — Audit terrain + code (Objectif 013)

> Agent : Kimi (Linux VM)  
> Date : 2026-05-28  
> Scope : `static/simli.html` (2245 lignes) + `luna_web.py` (section Simli/visio)  
> Méthode : analyse statique approfondie + tests curl (endpoints protégés, auth requise)  
> Contrainte : pas de session Simli longue, pas de consommation crédits inutile

---

## 1. Parcours utilisateur complet

### Étape 1 — Lancement depuis l'app principale
- **Trigger** : Bouton "Visio Luna" dans `index.html` → `callBtn.addEventListener` → `startCall()` → `_showDurationPicker()` → redirection `/simli?duration=X`
- **Confirmation P0** : ✅ `_showConfirm()` affiche "Lancer la visio Luna ?" avant redirection

### Étape 2 — Écran de démarrage (`simli.html`)
- **Titre** : "Visio avec Luna"
- **Sous-titre** : "Luna vous voit et vous entend. Parlez naturellement, elle vous repond en direct."
- **Sélecteur durée** : 15min / 30min / 1h (défaut) / 2h / Illimité
- **Bouton** : "Démarrer" (vert)
- **Lien retour** : "← Retour au chat"
- **Auto-démarrage** : Si `?duration=X` dans l'URL, sélectionne la valeur la plus proche et clique auto après 300ms

**Friction UX identifiée :**
- 🟡 L'utilisateur n'a pas le temps de lire l'écran si `?duration` est présent (auto-click après 300ms). Sur mobile, le DOM peut mettre plus de 300ms à charger → risque de clic sur mauvais élément.

### Étape 3 — Pré-test micro / caméra
- **Vérification micro** : `getUserMedia({audio:true})` → visualiseur à barres audio
- **Vérification caméra** : `getUserMedia({video:{facingMode:'user'}})` → fallback `video:true` si échec
- **Boutons** : "Commencer la visio" (désactivé tant que micro non OK) + "Retour" (annule)
- **Fallback audio-only** : Si caméra refusée, message "Caméra non disponible — visio en audio."

**Friction UX identifiée :**
- 🟢 Très bien fait. Le fallback audio-only est clair et rassurant.

### Étape 4 — Cinématique (5 actes)

| Acte | Durée ~ | Description |
|------|---------|-------------|
| ACT 1 — Establishing shot | 3s | Fond de scène (SVG dynamique selon météo/heure) + Ken Burns drift |
| ACT 2 — Phone vibrate | 2s | Téléphone apparaît, vibre |
| ACT 3 — Phone ring | 3s | Notification "Luna" apparaît, glow pulse |
| ACT 4 — Phone answer | 2s | Avatar apparaît dans le téléphone |
| ACT 5 — Zoom + fullscreen | 4s | Zoom progressif, lettres cinema, fond noir, iframe Tavus/Simli fullscreen |

**Friction UX identifiée :**
- 🟡 **Durée totale ~14s avant de voir Luna** — sur mobile avec connexion lente, l'attente du `createVisioCall()` + la cinématique peut faire croire à un bug.
- 🟡 **Pas de bouton "Skip"** sur la cinématique. L'utilisateur ne peut pas passer la séquence s'il l'a déjà vue.
- 🟢 **Fond météo dynamique** — belle touche immersive.

### Étape 5 — Visio active (Daily.js iframe)
- **Barre d'actions** (haut) : 🔇 Mute Luna | 📨 Inviter | 🔗 Partager | 📝 Notes | 📎 Analyser | 🎙 Indicateur micro
- **Bouton raccrocher** (bas, rouge) : "Raccrocher"
- **Badge provider** (haut droite) : "Tavus" ou "Simli" selon le provider actif
- **Vision** (bas gauche) : "Luna voit" / "Observation" — toggle silencieux au clic

**Friction UX identifiée :**
- 🟡 **Aucun input texte** — Si le micro ne marche pas ou si l'utilisateur préfère écrire (en public, sourd/muet), il n'y a aucun moyen de communiquer avec Luna. **C'est un point bloquant pour l'accessibilité.**
- 🟡 **Mute Luna = instruction texte, pas vrai mute** — Le bouton "🔇 Luna muette" envoie un message texte à Luna via `sendAppMessage`, pas un vrai mute audio. Si Luna est en train de parler, elle continue jusqu'à la fin de sa phrase. Confusion potentielle.
- 🟡 **SpeechRecognition fr-FR uniquement** — Pas de fallback sur Firefox/Safari. Les notes visio ne captureront pas la parole.

### Étape 6 — Raccrocher
- **Trigger** : Bouton "Raccrocher" ou back button Android
- **Actions** : `doHangup()` → `POST /api/call/end` + `dailyCall.leave()` + `dailyCall.destroy()`
- **Auto-save notes** : Si contenu présent, POST `/api/visio/notes` avec `auto_save=true` avant navigation
- **Redirection** : `/` (app principale) après 5s max ou immédiat si pas de contenu

**Friction UX identifiée :**
- 🔴 **Hangup ne gère pas Simli** — `POST /api/call/end` est conçu pour Tavus. Simli n'a pas de route `/api/simli/end`. La session Simli expire seule après `maxIdleTime` (300s = 5min). **L'utilisateur paie pour 5 minutes supplémentaires après avoir raccroché.**
- 🟡 **Pas de confirmation avant raccrocher** — Un clic accidentel sur le bouton rouge termine la session immédiatement.

---

## 2. Problèmes techniques identifiés dans le code

### 🔴 CRITIQUE — Pas d'input texte dans la visio
**Fichier** : `static/simli.html`  
**Impact** : Accessibilité + usage en environnement bruyant  
**Description** : Simli/Daily.js est audio-only. Aucun `<input>` ou `<textarea>` n'existe dans l'interface pour permettre à l'utilisateur d'écrire. Simli supporte pourtant les messages texte via `sendAppMessage`.  
**Recommandation** : Ajouter une barre de saisie texte en bas de l'écran (comme dans le chat) qui envoie des messages `conversation.echo` à Simli.

### 🔴 CRITIQUE — Hangup Simli non géré = crédits gaspillés
**Fichier** : `static/simli.html` l.2190-2236 + `luna_web.py`  
**Impact** : ~5 minutes de crédits Simli gaspillées par session  
**Description** : `doHangup()` appelle `POST /api/call/end` qui ne gère que Tavus. Simli n'a pas d'endpoint `/api/simli/end`. Le `maxIdleTime` Simli est à 300s.  
**Recommandation** : Créer `POST /api/simli/end` qui appelle l'API Simli pour terminer la session, et l'appeler dans `doHangup()` quand `currentProvider === 'simli'`.

### 🟠 MAJEUR — Voix masculine par défaut
**Fichier** : `luna_web.py` l.6888-6895  
**Impact** : Luna a une voix d'homme — rupture d'immersion  
**Description** :
```python
payload["voiceId"] = os.getenv("CARTESIA_VOICE_ID", "65b25c5d-ff07-4687-a04c-da2f43ef6fa9")
payload["voiceId"] = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
```
Ces IDs par défaut sont probablement masculins.  
**Niveau** : 2 (choix voix = décision Ludovic)  
**Recommandation** : Choisir une voix féminine française sur Cartesia ou ElevenLabs, puis mettre à jour l'env var correspondante sur Cloud Run.

### 🟠 MAJEUR — Avatar générique (pas Luna)
**Fichier** : `luna_web.py` l.6832  
**Impact** : L'avatar ne ressemble pas à Luna — rupture d'immersion  
**Description** : `face_id = os.getenv("SIMLI_FACE_ID", "")` — l'avatar configuré est probablement un modèle générique Simli.  
**Niveau** : 2 (création avatar = validation Ludovic)  
**Recommandation** : Utiliser les photos de référence dans `docs/assets/luna_avatar_sources/` pour créer un avatar Simli personnalisé, ou choisir un avatar féminin existant dans la galerie Simli.

### 🟠 MAJEUR — `sendAppMessage(..., '*')` envoie à tous les participants
**Fichier** : `static/simli.html` l.1655, 1700, 1978, 2007  
**Impact** : Fuite de messages système si un invité est présent  
**Description** : Le deuxième argument `'*'` envoie le message à tous les participants Daily.js. Si un invité externe rejoint la visio, il recevra les messages système (vision, documents, mute).  
**Recommandation** : Remplacer `'*'` par une cible spécifique (le bot Simli) ou utiliser `'*'` seulement pour les messages destinés à tous.

### 🟡 MOYEN — Vision caméra limitée (pas temps réel)
**Fichier** : `static/simli.html` l.1893-2034  
**Impact** : Luna "voit" toutes les 12s seulement, en basse résolution (320×240)  
**Description** : Capture canvas → `toDataURL('image/jpeg', 0.55)` → POST `/api/visio/perception` → GPT-4o-mini Vision → injection texte. Ce n'est pas de la vision temps réel native.  
**Niveau** : 2 (amélioration coûteuse en tokens)  
**Recommandation V1** : Garder le système actuel mais réduire l'intervalle à 8s.  
**Recommandation V2** : Streaming vision temps réel (coût élevé, à valider avec Ludovic).

### 🟡 MOYEN — Auto-démarrage trop rapide (300ms)
**Fichier** : `static/simli.html` l.1511  
**Impact** : L'utilisateur n'a pas le temps de voir l'écran de démarrage  
**Recommandation** : Augmenter à 1200ms minimum, ou ajouter un bouton "Démarrer" explicite même avec `?duration`.

### 🟡 MOYEN — Cinématique non skippable
**Fichier** : `static/simli.html` (toute la séquence cinématique)  
**Impact** : Friction pour les utilisateurs réguliers  
**Recommandation** : Ajouter un bouton "Passer" ou détecter `localStorage.skipCinematic = true` après la première visio.

### 🟢 MINEUR — `SpeechRecognition` non supporté Firefox/Safari
**Fichier** : `static/simli.html` l.2042-2084  
**Impact** : Notes visio ne captureront pas la parole sur ces navigateurs  
**Recommandation** : Afficher un message explicite : "Notes : transcription vocale indisponible sur ce navigateur."

### 🟢 MINEUR — Pas de confirmation avant raccrocher
**Fichier** : `static/simli.html` l.2238  
**Impact** : Risque de fin de session accidentelle  
**Recommandation** : Ajouter `_showConfirm("Raccrocher ?", "La session va se terminer.", doHangup)` — niveau 1.

---

## 3. Synthèse des problèmes par sévérité

| Sévérité | Compteur | Items |
|----------|----------|-------|
| 🔴 Critique | 2 | Pas d'input texte, Hangup Simli non géré = crédits gaspillés |
| 🟠 Majeur | 4 | Voix masculine, Avatar générique, sendAppMessage wildcard, Mute = instruction texte |
| 🟡 Moyen | 3 | Vision limitée 12s, Auto-démarrage 300ms, Cinématique non skippable |
| 🟢 Mineur | 2 | SpeechRecognition compat, Pas de confirmation hangup |

---

## 4. Priorisation des corrections (proposition)

### Niveau 1 (autonome)
1. **Confirmation hangup** — `_showConfirm()` avant `doHangup()` — 5 lignes
2. **Auto-démarrage 1200ms** — changer `300` → `1200` — 1 ligne
3. **Message SpeechRecognition** — afficher info si non dispo — 3 lignes
4. **Hangup Simli** — créer `POST /api/simli/end` + l'appeler dans `doHangup()` — ~30 lignes

### Niveau 2 (validation Ludovic)
5. **Voix féminine** — Choisir ID Cartesia/ElevenLabs + configurer env var Cloud Run
6. **Avatar Luna** — Choisir/créer `SIMLI_FACE_ID` + configurer env var Cloud Run
7. **Input texte visio** — Ajouter barre de saisie + `sendAppMessage` — design UI à valider
8. **Vision V1/V2** — Décider intervalle (8s?) ou streaming temps réel

### Niveau 3 (validation + Claude)
9. **sendAppMessage wildcard** — Audit sécurité complet des messages système

---

## 5. Tests non destructifs recommandés (par Ludovic)

1. **Lancer visio sans micro** → vérifier le fallback audio-only
2. **Lancer visio sans caméra** → vérifier le message et la continuité
3. **Raccrocher une session Simli** → vérifier combien de temps la session reste active côté Simli (devrait être instantané après correction)
4. **Inviter un contact** → vérifier que le lien fonctionne et que les messages système ne fuient pas
5. **Notes visio** → vérifier la génération et la sauvegarde
6. **Upload document** → vérifier l'analyse et l'injection dans la conversation

---

*Fin du rapport UX Visio Luna.*
