# Claude — Diagnostic STT / Image / Identité — Objectif 014

Agent : Claude  
Date : 2026-05-31  
Statut : diagnostic code — aucun déploiement  
Référence : `CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`

---

## Résumé des 4 problèmes identifiés

| Priorité | Problème | Cause racine | Fichier / ligne |
|---|---|---|---|
| **P0** | Iris n'entend pas Ludovic | Bug race condition micro/Daily | `simli.html:1219–1223` |
| **P0** | Iris se présente comme "Riff" | Alice (EN) prononce "Iris" à l'anglaise | `luna_web.py:6860` + choix voix |
| **P1** | Voix accent anglais | Alice n'est pas une voix FR native | `luna_web.py:6876` |
| **P1** | Image/avatar distordu | `scale(1.5)` sur phone-avatar + iframe sans aspect-ratio | `simli.html:125` + `166` |

---

## 1. STT — Iris n'entend pas Ludovic

### Cause racine : race condition `allow="microphone"` vs `join()`

**Code incriminé** (`simli.html:1214–1223 + 1395–1399`) :

```javascript
// Étape 1 — createFrame crée l'iframe Daily.js (synchrone)
dailyCall = window.DailyIframe.createFrame(tavusFrameEl, {
    iframeStyle: { width: '100%', height: '100%', border: 'none' },
    showLeaveButton: false,
    showFullscreenButton: false,
});

// Étape 2 — setTimeout 300ms pour mettre allow="microphone" sur l'iframe
setTimeout(function() {
    var fi = tavusFrameEl.querySelector('iframe');
    if (fi) fi.allow = 'camera; microphone; autoplay; ...';
}, 300);  // ← EN RETARD

// ... (handlers événements) ...

// Étape 3 — join() appelé IMMÉDIATEMENT, AVANT les 300ms
dailyCall.join({
    url: conversationUrl,
    startVideoOff: false,
    startAudioOff: false,  // ← demande le micro, mais allow pas encore posé
});
```

**Ce qui se passe** : Daily.js charge l'URL de la room dans l'iframe. Au chargement, il tente d'accéder au microphone. À ce moment, `allow="microphone"` n'est pas encore posé sur l'iframe (il le sera 300ms plus tard). Le navigateur bloque l'accès micro dans l'iframe. Résultat : Simli ne reçoit jamais l'audio de Ludovic → STT silencieux → Iris ne répond pas.

**Preuve indirecte** : le `firstMessage` ("Bonjour Ludovic...") fonctionne — c'est le TTS de Simli, côté bot. Mais aucune réponse après → le STT côté utilisateur est mort.

**Vérification en console** : si `[ERROR][simli] daily_cam_error` ou `[ERROR][simli] daily_error` apparaissent avec `NotAllowedError` ou `PermissionDeniedError` → confirmation.

### Patch minimal (niveau 1 — UI non visible, non destructif)

Remplacer le `setTimeout` par un attribut posé **avant** que Daily.js ne charge la room. Utiliser `DailyIframe.wrap()` avec un iframe pré-existant qui a déjà `allow` correctement configuré.

**Patch A** : essai synchrone immédiat + retry court :

```javascript
dailyCall = window.DailyIframe.createFrame(tavusFrameEl, {
    iframeStyle: { width: '100%', height: '100%', border: 'none' },
    showLeaveButton: false,
    showFullscreenButton: false,
});

// Tenter synchrone immédiatement (Daily crée parfois l'iframe sync)
var _setAllow = function() {
    var fi = tavusFrameEl.querySelector('iframe');
    if (fi) { fi.allow = 'camera; microphone; autoplay; display-capture; compute-pressure; fullscreen'; return true; }
    return false;
};
if (!_setAllow()) {
    // Retry rapide si l'iframe n'existe pas encore
    setTimeout(_setAllow, 50);
    setTimeout(_setAllow, 150);
    setTimeout(_setAllow, 300);
}
```

**Patch B** (plus fiable) : injecter un `<iframe>` pré-configuré dans le DOM avant createFrame, puis utiliser `DailyIframe.wrap()` :

Dans le HTML, remplacer `<div id="tavusFrame"></div>` par :
```html
<div id="tavusFrame">
  <iframe id="dailyIframe"
    allow="camera; microphone; autoplay; display-capture; compute-pressure; fullscreen"
    style="width:100%;height:100%;border:none;"
    src="about:blank"></iframe>
</div>
```

Dans le JS, remplacer `createFrame` par :
```javascript
var existingIframe = document.getElementById('dailyIframe');
dailyCall = window.DailyIframe.wrap(existingIframe, {
    showLeaveButton: false,
    showFullscreenButton: false,
});
```

Le `allow` est présent dès le début → microphone accordé quand `join()` charge l'URL.

**Niveau** : 1 — pas d'UI visible, pas de secret, patch local uniquement. Déploiement niveau 2 (validation Ludovic).

---

## 2. Identité — "Riff" au lieu de "Iris"

### Cause racine : Alice (ElevenLabs) prononce "Iris" à l'anglaise

**Explication phonétique** :
- Prononciation anglaise de "Iris" : /ˈaɪrɪs/ → "EYE-riss"
- Prononciation française : /i.ʁis/ → "ee-REE"
- Alice est une voix à dominante anglaise. Même avec `elevenlabsLanguageCode: "fr"`, elle prononce "Iris" à l'anglaise → entendu par Ludovic comme "Riff" ou "Riss"

**Code incriminé** (`luna_web.py:6860`) :
```python
"firstMessage": f"Bonjour {subscriber_name} ! C'est Iris, votre secrétaire. Je vous vois..."
```

### Patch minimal (niveau 1 — modification du prompt, pas de déploiement immédiat)

**Option A** : Réécrire le `firstMessage` pour éviter le nom au début et le faire prononcer en contexte plus court :
```python
"firstMessage": f"Bonjour {subscriber_name} ! Votre secrétaire est à l'écoute. Comment puis-je vous aider ?"
```
(retire "Iris" du `firstMessage` — le système prompt dit déjà "Tu t'appelles Iris")

**Option B** : Choisir une voix ElevenLabs native française. Voix recommandées à tester :
- `XB0fDUnXU5powFXDhCwa` — Charlotte (FR native, professionnelle)
- `Xb7hH8MSUJpSbSDYk0k2` — Alice FR (différente de l'Alice EN actuelle)
- Tester via `GET https://api.elevenlabs.io/v1/voices` avec la clé pour lister les voix disponibles

**Option C** : Forcer la prononciation dans le prompt système :
```
Quand tu prononces ton prénom, dis "ee-ree" (prononciation française).
```
(peu fiable, dépend du modèle TTS)

**Recommandation** : Option A (immédiat, sans changer la voix) + Option B en parallèle (test voix FR native avant déploiement).

---

## 3. Voix — Accent anglais (P1)

### Cause

Alice (`6BlZrFdruL4hpXFHmHUC`) est une voix du Voice Library ElevenLabs à accent anglais. `elevenlabsLanguageCode: "fr"` force le français mais n'efface pas l'accent natif anglais de la voix.

### Patch (niveau 2 — nécessite validation Ludovic)

Tester une voix ElevenLabs native française avec la clé actuelle :

```bash
# Lister les voix disponibles
curl -s "https://api.elevenlabs.io/v1/voices" \
  -H "xi-api-key: sk_774552ee20d26b8f58b953319ce391b189b388211b465218" \
  | python3 -c "import sys,json; [print(v['voice_id'], v['name'], v.get('labels',{}).get('language','')) for v in json.load(sys.stdin)['voices']]"
```

Puis tester la voix candidate avec le même appel TTS qu'utilisé pour valider la clé.

---

## 4. Image — Avatar distordu (P1)

### Cause A : `phone-avatar-frame iframe { transform: scale(1.5) }` (`simli.html:125`)

L'iframe de la phase cinématique (téléphone) est zoomée à 150%. Ce n'est pas l'iframe principale de la visio — elle est vidée après la cinématique (`phoneAvatarFrame.innerHTML = ''` à la ligne 1410). Cet élément ne cause donc pas la distorsion en visio plein écran.

### Cause B : `#tavusFrame iframe { width: 100%; height: 100% }` sans `aspect-ratio` ni `object-fit`

L'iframe Daily.js remplit tout l'écran (`position: fixed; inset: 0`). À l'intérieur de l'iframe, Daily.js rend la vidéo de l'avatar Simli. Si le ratio de la vidéo avatar (probablement 9:16 portrait ou 4:3) ne correspond pas au ratio de l'écran (16:9 paysage ou écran portrait variable), la vidéo est étirée.

On ne peut pas contrôler `object-fit` à l'intérieur d'une iframe cross-origin. Mais on peut contraindre la taille de l'iframe elle-même.

### Patch minimal (niveau 1 — CSS uniquement)

Contraindre `#tavusFrame` à un ratio 9:16 centré (format portrait avatar) ou laisser le navigateur gérer avec `max-width` :

```css
#tavusFrame {
    position: fixed; inset: 0; z-index: 20;
    display: flex; align-items: center; justify-content: center;
    background: #000;
}
#tavusFrame iframe {
    width: 100%; height: 100%; border: none;
    /* Contraindre le ratio pour éviter la distorsion */
    max-width: min(100vw, calc(100vh * 9 / 16));
    max-height: min(100vh, calc(100vw * 16 / 9));
}
```

Cela laisse des bandes noires sur les côtés si l'écran est plus large que 9:16, mais évite la distorsion.

**Alternative** : demander à Simli/Daily si le ratio de la vidéo avatar peut être configuré côté room.

**Niveau** : 1 côté CSS. Si UI visible modifiée → validation Ludovic recommandée.

---

## 5. Synthèse des patches proposés

| Patch | Fichier | Niveau | Déploiement |
|---|---|---|---|
| A — Fix microphone allow (iframe pré-existant) | `simli.html:1214` | 1 | Validation Ludovic |
| B — firstMessage sans "Iris" | `luna_web.py:6860` | 1 | Validation Ludovic |
| C — Test voix FR native ElevenLabs | `.env` + Cloud Run | 2 | Validation Ludovic |
| D — CSS ratio avatar | `simli.html:161–166` | 1 | Validation Ludovic |

**Ordre recommandé** :
1. Patch A (micro) → test terrain → si Iris répond → STT résolu
2. Patch B (firstMessage) → déployer avec A
3. Patch C (voix) → tester voix FR en local avant
4. Patch D (image) → cosmétique, après les fonctionnels

---

## 6. Test terrain demandé à Ludovic

**Avant déploiement du patch A**, pour confirmer le diagnostic micro :

1. Ouvrir la console navigateur (F12 → Console)
2. Lancer une visio (< 30s)
3. Chercher les lignes `[ERROR][simli]` — en particulier `daily_error` avec `NotAllowedError`
4. Chercher `[INFO][simli] daily_joined` et `bot_joined`
5. Après la phrase de bienvenue Iris, parler et attendre 5s
6. Chercher `app_msg_conversation_utterance` dans la console — si absent → STT mort confirmé

Envoyer les lignes console à l'équipe (aucun secret dedans).
