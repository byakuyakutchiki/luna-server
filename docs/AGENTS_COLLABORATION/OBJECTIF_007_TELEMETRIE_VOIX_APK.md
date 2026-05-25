# Objectif 007 — Télémétrie vocale précise APK

**Statut** : ouvert — en cours d'implémentation  
**Priorité** : critique  
**Lead** : Claude  
**Date ouverture** : 2026-05-25  
**Dépendance** : Objectif 006 (heartbeat réel OK — validé)

---

## Constat post-Objectif 006

- Heartbeat APK réel reçu ✅
- Téléphone fondateur vu récemment ✅
- APK v2.8 active et à jour ✅
- Voix : un seul événement remonte → `voice_session_ended` ✅
- Tous les autres événements sont perdus ❌

**Luna sait que le téléphone est vivant, mais ne sait pas où le flux vocal bloque.**

---

## Cause technique identifiée par Claude

Deux bugs dans la télémétrie existante (`static/index.html`) :

### Bug 1 — session_ts = 0 pour les premiers événements

Dans `sendApkEvent()`, le champ `session_ts` utilise `_voiceStartTime` :
```javascript
session_ts: _voiceStartTime ? Math.floor(_voiceStartTime / 1000) : 0,
```

Quand `voice_button_clicked` est envoyé (avant l'appel à `startVoice()`),
`_voiceStartTime` n'est pas encore défini → `session_ts = 0`.

L'analyse serveur groupe par `session_ts`. Les événements avec `session_ts=0`
tombent dans une "session fantôme" distincte. Seul `voice_session_ended`
(qui a le bon `session_ts`) apparaît dans la dernière session visible.

**Fix** : introduire `_voiceSessionStartTs = Date.now()` dans le handler de click,
utiliser ce timestamp pour tous les événements de la session.

### Bug 2 — plafond _apkEventCount trop bas

```javascript
if (_apkEventCount >= 10) return;
```

Avec 21 événements à instrumenter, le plafond est trop bas.

**Fix** : passer à 30.

---

## But objectif 007

Quand Ludovic appuie sur le bouton vocal, Luna doit pouvoir dire :
- quelle étape a réussi
- quelle étape a échoué
- ce qui manque pour aller plus loin

**Règle centrale** : on ne corrige pas encore la voix fonctionnelle.
On améliore d'abord la télémétrie pour obtenir une chronologie complète
ou un point d'arrêt explicite.

---

## Événements à instrumenter (21)

| Événement | Moment | Priorité |
|---|---|---|
| `voice_click_received` | Clic sur le bouton | Critique |
| `voice_start_entered` | Entrée dans `startVoice()` | Critique |
| `voice_token_present` | Token JWT valide au démarrage | Critique |
| `voice_token_missing` | Token absent ou invalide | Critique |
| `voice_state_blocked` | `voiceActive` déjà true au clic | Critique |
| `voice_micro_request_started` | `getUserMedia` appelé | Haute |
| `voice_micro_permission_granted` | `getUserMedia` OK | Haute |
| `voice_micro_permission_denied` | Refus micro (NotAllowedError) | Haute |
| `voice_ws_create_started` | Création WebSocket démarrée | Haute |
| `voice_ws_create_failed` | `new WebSocket()` a jeté une exception | Haute |
| `voice_ws_opened` | `onopen` reçu | Haute |
| `voice_ws_closed` | `onclose` reçu | Haute |
| `voice_ws_error` | `onerror` reçu | Haute |
| `voice_capture_started` | ScriptProcessor ou AudioWorklet actif | Normale |
| `voice_first_audio_chunk_sent` | Premier chunk audio envoyé côté WS | Haute |
| `voice_audio_send_failed` | Erreur lors de l'envoi chunk | Normale |
| `voice_first_audio_chunk_received` | Premier chunk audio reçu du serveur | Haute |
| `voice_playback_started` | Lecture audio déclenchée côté client | Normale |
| `voice_playback_failed` | Erreur lors de la lecture | Normale |
| `voice_no_audio_after_timeout` | Timer 20s écoulé sans audio reçu | Critique |
| `voice_session_ended` | `stopVoice()` appelé | Critique |

---

## Sorties anticipées à tracer

- token absent ou invalide
- bouton vocal appelé mais `startVoice()` non lancé
- session déjà active (`voiceActive = true`)
- permission micro refusée
- `getUserMedia` qui échoue pour une autre raison
- WebSocket jamais créé (exception constructor)
- WebSocket créé mais jamais ouvert
- WebSocket fermé avant premier audio
- audio capturé mais non envoyé (réseau bloqué ?)
- audio reçu mais non joué (AudioContext bloqué ?)
- timeout 20s sans audio reçu

---

## Rôles

### Claude — Lead final et intégrateur

- Diagnostic initial et causes (fait)
- Implémentation du fix `session_ts` + plafond + nouveaux événements
- Relecture avis DeepSeek, Kimi, Cursor, Codex
- Vérification Cloud Run, Redis, cockpit après déploiement
- Déploiement uniquement après validation Ludovic
- Ne pas corriger la voix fonctionnelle avant chronologie suffisante

### DeepSeek — Mission technique (VS Code)

**Branche** : `ds/objectif-007-telemetrie-voix`

- Auditer `static/index.html` : bouton vocal, handler mobile, `startVoice()`,
  `stopVoice()`, WebSocket, `getUserMedia`, AudioWorklet, ScriptProcessor
- Vérifier si d'autres chemins de code appellent `startVoice()` (line 4574,
  6978, 6984 — clicks programmatiques sur `lunaVoiceBtn`)
- Confirmer ou infirmer le bug `session_ts = 0`
- Confirmer ou infirmer que `_apkEventCount` atteint 10 trop vite
- Identifier tous les `catch(e){}` silencieux qui avalent des erreurs
- Vérifier si `fetch()` peut être bloqué par le WebSocket actif sur Android WebView
- Proposer les points d'injection exacts pour les 21 événements

**Livrable** : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_007.md`

### Kimi — Mission lisibilité et diagnostic humain

**Branche** : `kimi/objectif-007-telemetrie-voix`

Pour chacun des scénarios ci-dessous, rédiger les 4 textes :
- `luna_knows` (ce que Luna sait avec certitude)
- `luna_guesses` (hypothèse probable)
- `luna_recommends` (action recommandée)
- `luna_cannot` (ce que Luna ne peut pas déduire)

**Scénarios à couvrir** :
1. `voice_click_received` uniquement → sortie anticipée non identifiée
2. `voice_token_missing` → pas de session possible
3. `voice_state_blocked` → double appui
4. `voice_micro_permission_denied` → refus micro
5. `voice_ws_create_failed` → WebSocket impossible
6. `voice_ws_opened` sans audio → `voice_no_audio_after_timeout`
7. `voice_first_audio_chunk_received` sans playback
8. Session complète OK → `voice_playback_started`

**Règles de rédaction** :
- Pas de jargon technique visible pour le fondateur
- Pas de formulation culpabilisante
- Distinguer clairement : heartbeat OK ≠ voix OK
- Textes en français, courts, directs

**Livrable** : `docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_007.md`

### Cursor — Mission UI / non-régression mobile

**Branche** : `cursor/objectif-007-telemetrie-voix`

- Vérifier que la chronologie reste lisible sur téléphone (320px → 414px)
- Vérifier que les assets graphiques ne disparaissent pas
- Vérifier que l'ajout d'événements ne casse pas le bouton vocal visuellement
- Tester visuellement `fondateur.html` et l'écran principal
- Confirmer que les nouvelles balises HTML de la section `🎙️ Voix APK`
  s'affichent correctement sur mobile
- Vérifier que la section journal voix ne déborde pas

**Livrable** : `docs/AGENTS_COLLABORATION/agents/CURSOR_AVIS_007.md`

### Codex — Mission cadrage GitHub et garde-fous

**Branche** : `codex/objectif-007-telemetrie-voix`

- Vérifier que chaque agent reste dans son rôle
- Vérifier que l'objectif 007 ne devient pas une correction fonctionnelle prématurée
- Définir les critères de validation objectif 007
- Vérifier que le RAPPORT_CLOUD_RUN est à jour
- Préparer la synthèse logique pour Claude

**Livrable** : `docs/AGENTS_COLLABORATION/agents/CODEX_AVIS_007.md`

### Ludovic — Testeur et validateur final

- Ouvrir Luna sur le téléphone réel
- Appuyer une seule fois sur le bouton vocal, attendre 20 secondes
- Copier le résultat du cockpit fondateur (section `🎙️ Voix APK`)
- Valider si le diagnostic affiché correspond à ce qu'il vit
- Valider avant tout déploiement

---

## Critères de réussite objectif 007

- [ ] Après un appui vocal réel, le cockpit affiche **plus** que `voice_session_ended`
- [ ] La chronologie montre au minimum :
  - clic reçu (`voice_click_received`)
  - entrée `startVoice` (`voice_start_entered`)
  - état token (`voice_token_present` ou `voice_token_missing`)
  - demande micro (`voice_micro_request_started`)
  - résultat micro (granted ou denied)
  - tentative WebSocket (`voice_ws_create_started`)
  - résultat WebSocket (opened ou failed)
  - capture audio ou point d'arrêt explicite
- [ ] Si la voix échoue, Luna indique l'étape bloquante avec précision
- [ ] Le journal voix garde une trace lisible du diagnostic
- [ ] `total_events_stored` montre les nouveaux types d'événements
- [ ] Aucun déploiement majeur sans validation Ludovic
- [ ] Aucun secret, audio brut, transcript privé ou donnée sensible stocké

---

## Interdictions

- Pas de correction de la voix fonctionnelle avant chronologie suffisante
- Pas de déploiement Cloud Run sans validation Ludovic
- Pas d'audio brut, pas de transcript, pas de position exacte
- Pas de rebuild APK pour cette phase (événements JS dans `static/index.html`)
- Pas de gros refactor de `startVoice()` — injection minimale uniquement
- Pas de données personnelles fines dans la télémétrie

---

## Validation

- [ ] Claude a identifié les causes (fait)
- [ ] DeepSeek a posté son avis dans `agents/DEEPSEEK_AVIS_007.md`
- [ ] Kimi a posté ses textes dans `agents/KIMI_AVIS_007.md`
- [ ] Cursor a posté son audit dans `agents/CURSOR_AVIS_007.md`
- [ ] Codex a posté la synthèse dans `agents/CODEX_AVIS_007.md`
- [ ] Claude a implémenté les corrections + nouveaux événements
- [ ] Déployé sur Cloud Run
- [ ] Ludovic a validé sur téléphone réel
- [ ] Chronologie complète visible dans le cockpit fondateur
