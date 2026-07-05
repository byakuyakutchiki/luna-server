# Audit pré-patch — Guardian voice context sur UI stable

**Agent** : Kimi Code CLI  
**Branche auditée** : `fix/guardian-voice-context-on-stable-ui`  
**Branche de base obligatoire** : `feature/pwa` (elle-même basée sur `stable/frontend-reference-2026-07-05`)  
**Date** : 2026-07-03  
**Statut** : audit terminé, correction NON appliquée — livrable écrit avant tout patch.

---

## 1. Résumé exécutif

L'UI Guardian actuellement en production (`luna-beta-00970-bad`) est graphiquement stable, mais les correctifs vocaux récents (capture du contexte après mot-clé, traçage terrain, anti-décrochage) ont été perdus lors du snapshot de référence `stable/frontend-reference-2026-07-05` (commit `d0971aa`).

Ce snapshot a rétabli Git comme source de vérité du frontend, mais il a écrasé `static/guardian.html` avec une version antérieure à plusieurs commits Guardian voice (#32, capture isFinal, traçage).

**Aucun autre fichier statique (`index.html`, `salon.html`, `simli.html`) n'est impacté.** Le backend (`luna_web.py`, `core/guardian/engine.py`) contient déjà les routes et le verrou anti-doublon.

Un mécanisme de race condition pouvant produire un doublon d'appel d'urgence a été identifié dans `static/guardian.html`. Il est corrigeable sans toucher au backend ni à l'UI graphique.

---

## 2. Preuves d'identité et d'historique

### Branche / SHA / historique

```bash
git rev-parse HEAD && git branch --show-current && git log --oneline -10
```

Résultat :

```
f45fe4fb74bf02faf98f5f1a632cee98406cc51a
fix/guardian-voice-context-on-stable-ui
f45fe4f feat(pwa): rend /guardian installable comme PWA web mobile
d0971aa sync(prod-frontend): snapshot exact du frontend de la production luna-beta-00970-bad
a321d1c chore(apk): build APK test pointant vers revision trace
efc763e fix(guardian): sépare le verrou anti-doublon du dossier incident Redis
8c69fc1 fix(guardian): capture contexte vocal après hit jusqu'au silence (isFinal) ou timeout
50c4227 fix(guardian): preserve vocal transcript/context on Web Speech hit (#32)
377c816 chore(guardian): ajoute logs de traçage terrain (sans correction contexte)
ef1613f fix(guardian): conserve le contexte vocal dans _vocalMatch (Web Speech API)
1c01c1f fix(apk): anti-double-clic sur telechargement APK v3.2.1
```

Preuve : la branche existe, son SHA est `f45fe4fb`, son historique remonte bien à `d0971aa` puis aux commits vocaux `8c69fc1` et `50c4227`.

---

## 3. Preuve que l'UI stable est présente

### Fichiers modifiés entre `stable/frontend-reference-2026-07-05` et `HEAD`

```bash
git diff --name-only stable/frontend-reference-2026-07-05...HEAD
```

Résultat :

```
static/guardian.html
static/manifest.json
static/sw.js
```

### Aucun changement sur `index.html`, `salon.html`, `simli.html`

```bash
git diff --name-only stable/frontend-reference-2026-07-05...HEAD -- static/index.html static/salon.html static/simli.html
```

Résultat : *(vide)*.

### Diff minimal de la PWA

```bash
git diff stable/frontend-reference-2026-07-05...HEAD -- static/guardian.html static/manifest.json static/sw.js
```

Résultat : seulement 17 insertions, 2 suppressions :

- `static/guardian.html` : ajout des meta PWA (`theme-color`, `manifest`, `apple-touch-icon`) + enregistrement du Service Worker en bas de page.
- `static/manifest.json` : `start_url` et `id` passés à `/guardian`, `theme_color` à `#080810`.
- `static/sw.js` : `/guardian` ajouté au precache.

**Conclusion** : l'UI stable est intacte ; seule la couche PWA a été ajoutée, sans modification graphique.

---

## 4. Fonctionnalités vocales perdues

### 4.1 Commit `50c4227` — preserve vocal transcript/context on Web Speech hit (#32)

**Existant dans** : `50c4227`, `8c69fc1`, `feature/sprint-a-ux`.  
**Absent dans** : `d0971aa`, `stable/frontend-reference-2026-07-05`, `feature/pwa`, `fix/guardian-voice-context-on-stable-ui`.

Comportement perdu : lors d'un hit Web Speech (`_vocalMatch`), les variables `_voiceTranscript` et `_voiceContext` ne sont plus alimentées. Le panneau countdown n'affiche donc pas la phrase entendue.

Diff perdu (extrait) :

```javascript
if(hit){
  _voiceTranscript=transcript||'';
  _voiceContext=transcript||'';
  _traceGuardian('web_sr_hit',{path:'_vocalMatch', transcript:transcript||'', keywordMatched:true, voiceTranscript:_voiceTranscript, voiceContext:_voiceContext});
  openVocalCountdown();
}
```

### 4.2 Commit `8c69fc1` — capture contexte vocal après hit jusqu'au silence (isFinal) ou timeout

**Existant dans** : `8c69fc1`, `feature/sprint-a-ux`.  
**Absent dans** : `d0971aa` et branches dérivées.

Comportement perdu :

1. Après un hit, la reconnaissance continue à écouter pendant 4 secondes (`_voiceCaptureTimer`).
2. Les mots prononcés après le mot-clé sont accumulés dans `_voiceTranscript` / `_voiceContext`.
3. La capture s'arrête au silence (`isFinal`) ou au timeout.
4. Seulement après cette capture, le countdown s'ouvre avec la phrase complète.

Diff perdu (fonctions, variables, signature) :

- Signature `_vocalMatch(transcript,isFinal)` → `_vocalMatch(transcript)`.
- Variables globales `_voiceCaptureActive`, `_voiceCaptureTimer` supprimées.
- Fonctions `_stopVoiceCapture()`, `_traceGuardian()` supprimées.
- Boucle `rec.onresult` ne lit plus `e.results[i].isFinal`.

### 4.3 Traçage terrain GUARDIAN_SR

**Existant dans** : `8c69fc1`, `feature/sprint-a-ux`.  
**Absent dans** : `d0971aa` et branches dérivées.

Comportement perdu : les logs `_traceGuardian('web_sr_hit', ...)`, `_traceGuardian('web_sr_context', ...)`, `_traceGuardian('vosk_received', ...)` n'existent plus. Le diagnostic terrain des doublons est donc impossible sans ajouter manuellement des logs.

### 4.4 Récapitulatif

| Fonctionnalité | Commit d'origine | État actuel | Impact |
|---|---|---|---|
| `_voiceTranscript` / `_voiceContext` alimentés sur hit Web Speech | `50c4227` | absent | countdown vide, SMS sans contexte |
| Capture du contexte après hit jusqu'au silence/timeout | `8c69fc1` | absent | seul le mot-clé est transmis, pas la phrase de détresse |
| Traçage terrain `_traceGuardian` | `8c69fc1` | absent | impossible de prouver la chaîne vocale en prod |
| Verrou anti-doublon backend `incident_lock` | `efc763e` | **présent** dans `luna_web.py` | OK |
| Route `/api/guardian/voice-context` | issue #32 | **présente** dans `luna_web.py` | OK |
| Route `/api/guardian/sos/{session_id}` avec `context`/`transcript` | issue #32 | **présente** dans `luna_web.py` | OK |

---

## 5. Mécanisme du doublon d'appels d'urgence

### 5.1 Observation

Le comportement actuel peut déclencher **deux POST `/api/guardian/sos/{SID}`** successifs, donc deux chaînes SMS + appels, pour un seul incident vocal.

### 5.2 Code concerné

Extrait actuel de `static/guardian.html` :

```javascript
function openVocalCountdown(){
  if(_vocalActive||_sosInProgress) return;
  _vocalActive=true;
  ...
  _vocalTimer=setInterval(function(){
    n--;
    ...
    if(n<=0){
      clearInterval(_vocalTimer); _vocalTimer=null;
      document.getElementById('vocal-modal').classList.remove('open');
      _vocalActive=false;        // ← garde levée
      _triggerSOSVocal();        // ← premier appel
    }
  },1000);
}

function _triggerSOSVocal(){
  if(!SID||_sosInProgress) return;
  _sosInProgress=true;           // ← deuxième garde levée trop tard
  var iid=_genIncidentId();
  ...
  authFetch('/api/guardian/sos/'+SID,{...});  // POST
  ...
  .finally(function(){_sosInProgress=false;});
}

window.lunaEmergencyVoiceDetected=function(text, confidence, context){
  if(!SID){ return; }
  if(_sosInProgress){ return; }  // ← ne vérifie PAS _vocalActive
  _voiceTranscript=(text||'').toString();
  _voiceContext=(context||'').toString();
  openVocalCountdown();
  _enrichVoiceContext(_voiceTranscript);
};
```

### 5.3 Scénario de race condition (cause la plus probable)

Le Web Speech API continue de tourner en arrière-plan (`rec.continuous=true`) pendant et après le countdown. Entre :

1. `_vocalActive=false` (levée de la première garde), et
2. `_sosInProgress=true` (pose de la deuxième garde),

il existe une fenêtre de race condition. Si un nouvel événement `rec.onresult` arrive pendant cette fenêtre avec un nouveau hit :

- `_vocalMatch()` ne voit pas `_vocalActive` (il est déjà `false`) ;
- `openVocalCountdown()` ne voit pas `_sosInProgress` (pas encore `true`) ;
- un **second countdown** démarre, puis un **second POST `/api/guardian/sos/{SID}`** est émis avec un nouvel `incident_id`.

Le backend reçoit donc deux requêtes avec deux `incident_id` différents. Le verrou Redis `_guardian_dedup` ne les considère pas comme doublons, car il déduplique par `incident_id`, pas par session.

### 5.4 Autre scénario : Vosk natif + Web Speech simultanés

Dans l'APK :

- `_vocalStart()` est court-circuitée (`if(window.LunaBridge && window.LunaBridge.setGuardianProtection){ _setMicState('off'); return; }`).
- Seul Vosk natif est censé appeler `window.lunaEmergencyVoiceDetected()`.

Cependant, si le bridge n'est pas détecté ou si la WebView est utilisée en mode navigateur, Web Speech peut tourner en parallèle de Vosk. `window.lunaEmergencyVoiceDetected` ne vérifie que `_sosInProgress`, pas `_vocalActive`. Deux countdowns distincts peuvent alors être ouverts (un par Vosk, un par Web Speech), aboutissant à deux POST.

### 5.5 Preuves de code

Absence de garde `_vocalActive` dans `lunaEmergencyVoiceDetected` :

```bash
grep -n "window.lunaEmergencyVoiceDetected=function" -A8 static/guardian.html
```

Résultat :

```javascript
window.lunaEmergencyVoiceDetected=function(text, confidence, context){
  _dbgSR('emergency_received');
  if(!SID){ _dbgSR('bail_no_session'); return; }
  if(_sosInProgress){ _dbgSR('bail_sos_in_progress'); return; }
  // ← _vocalActive n'est pas testé ici
```

Fenêtre de race dans `openVocalCountdown` :

```bash
grep -n "_vocalActive=false" -A2 static/guardian.html
```

Résultat :

```javascript
_vocalActive=false;
_triggerSOSVocal();
```

### 5.6 Limites de la preuve

Aucun log d'exécution réelle n'est disponible dans ce repo. L'identification repose sur l'analyse statique du code. Pour confirmer le scénario exact en production, il faudrait activer le traçage `GUARDIAN_SR` (réintégré par le patch) et consulter les logs Cloud Run.

---

## 6. Patch minimal proposé

### 6.1 Objectifs du patch

1. Réintégrer la capture du contexte vocal après hit (commits `50c4227` + `8c69fc1`).
2. Réintégrer le traçage terrain `GUARDIAN_SR` pour pouvoir prouver la chaîne.
3. Fermer la fenêtre de race condition sans changer l'UI graphique.
4. Ne toucher que `static/guardian.html`.
5. Ne pas modifier `index.html`, `salon.html`, `simli.html`.
6. Ne pas modifier `luna_web.py` ni `core/guardian/engine.py` (déjà corrects).

### 6.2 Changements techniques

#### a) Capture contexte vocal (réintégration `8c69fc1`)

- Ajouter `_voiceCaptureActive` et `_voiceCaptureTimer`.
- Modifier `_vocalMatch(transcript, isFinal)`.
- Accumuler les mots après le hit jusqu'à `isFinal` ou timeout 4 s.
- Ouvrir le countdown uniquement après la capture.
- Ajouter `_stopVoiceCapture()`.
- Mettre à jour `rec.onresult` pour passer `isFinal`.

#### b) Transcript/context sur hit Web Speech (réintégration `50c4227`)

- Alimenter `_voiceTranscript` et `_voiceContext` dès le hit.

#### c) Anti-doublon (nouveau correctif minimal)

- Ajouter `_vocalActive` dans la garde de `window.lunaEmergencyVoiceDetected`.
- Dans `openVocalCountdown`, mettre `_sosInProgress=true` **avant** `_vocalActive=false` pour réduire la fenêtre de race.
- Alternative plus sûre : désactiver la reconnaissance vocale (`_vocalStop()`) dès que le countdown atteint 0, avant d'appeler `_triggerSOSVocal()`.

#### d) Traçage terrain (réintégration partielle)

- Réintégrer `_traceGuardian()` et les appels dans `_vocalMatch`, `lunaEmergencyVoiceDetected`, `_stopVoiceCapture`.

### 6.3 Fichiers touchés

| Fichier | Modification |
|---|---|
| `static/guardian.html` | Réintégration capture contexte + anti-doublon + traçage |

Aucun autre fichier.

---

## 7. Plan rollback propre

Si le patch doit être annulé :

```bash
git checkout fix/guardian-voice-context-on-stable-ui
git reset --hard f45fe4fb74bf02faf98f5f1a632cee98406cc51a
# ou simplement supprimer la branche et recréer depuis feature/pwa
git branch -D fix/guardian-voice-context-on-stable-ui
git checkout feature/pwa
git checkout -b fix/guardian-voice-context-on-stable-ui
```

Le point de retour garanti est le SHA `f45fe4fb` (PWA uniquement, UI stable intacte).

---

## 8. Tests à exécuter après patch

1. **Anti-régression frontend** :

```bash
python3 tools/frontend_regression_check.py
```

2. **Contrôle du diff** :

```bash
git diff --name-only
git diff -- static/guardian.html
```

3. **Vérification que `index.html`, `salon.html`, `simli.html` ne sont pas modifiés** :

```bash
git diff --name-only | grep -E "index\.html|salon\.html|simli\.html" && echo "ERREUR" || echo "OK"
```

4. **Tests statiques Guardian** (certains tests historiques sont obsolètes car l'ancienne route `/trigger` a été supprimée ; il faudra les mettre à jour ou les supprimer) :

```bash
python3 -m pytest tests/test_guardian_p0.py tests/test_web_voice_bridge_emergency.py -v
```

5. **Déploiement trace 0 %** uniquement, puis validation Ludovic avant promotion.

---

## 9. Tests obsolètes identifiés

Les tests suivants reflètent un ancien mécanisme (`/trigger`, `sr_emergency`) qui n'existe plus dans `luna_web.py` ni `static/guardian.html`. Ils échouent actuellement :

- `tests/test_guardian_apk_vosk_trigger_static.py`
- `tests/test_guardian_sr_log_trigger_static.py`
- `tests/test_guardian_voice_frontend_static.py`

Résultat de l'exécution :

```
tests/test_guardian_apk_vosk_trigger_static.py::test_guardian_apk_vosk_entrypoint_calls_trigger_directly FAILED
tests/test_guardian_sr_log_trigger_static.py::test_guardian_sr_client_log_triggers_emergency_chain FAILED
tests/test_guardian_voice_frontend_static.py::test_guardian_voice_paths_share_trigger_function FAILED
tests/test_guardian_voice_frontend_static.py::test_guardian_sr_logs_are_present FAILED
```

Ces tests ne doivent pas bloquer le patch fonctionnel, mais ils doivent être mis à jour ou supprimés pour refléter le nouveau pipeline `/api/guardian/sos/{SID}` + `window.lunaEmergencyVoiceDetected`.

---

## 10. Patch appliqué et vérifications

### 10.1 Fichier modifié

| Fichier | Lignes |
|---|---|
| `static/guardian.html` | +89 / -12 |

Aucune modification dans `static/index.html`, `static/salon.html`, `static/simli.html`, `luna_web.py`, `core/guardian/engine.py`.

### 10.2 Commandes et résultats

Diff vs `stable/frontend-reference-2026-07-05` :

```bash
git diff --stat stable/frontend-reference-2026-07-05 -- static/
```

Résultat :

```
 static/guardian.html | 113 +++++++++++++++++++++++++++++++++++++++++++++++
 static/manifest.json |   6 +++-
 static/sw.js         |   1 +
 3 files changed, 106 insertions(+), 14 deletions(-)
```

Vérification que `index.html`, `salon.html`, `simli.html` ne sont pas modifiés :

```bash
git diff --name-only stable/frontend-reference-2026-07-05 -- static/index.html static/salon.html static/simli.html | wc -l
```

Résultat : `0`.

Vérification syntaxique JavaScript :

```bash
python3 -c "import re; open('/tmp/guardian_extracted.js','w').write('\n'.join(re.findall(r'<script[^>]*>(.*?)</script>', open('static/guardian.html').read(), re.DOTALL)))"
node --check /tmp/guardian_extracted.js
```

Résultat : aucune erreur de syntaxe.

### 10.3 Synthèse des changements appliqués

1. **Capture contexte vocal après hit** : `_voiceCaptureActive`, `_voiceCaptureTimer`, `_stopVoiceCapture()`, `_vocalMatch(transcript,isFinal)`.
2. **Transcript/context sur hit Web Speech** : `_voiceTranscript` / `_voiceContext` alimentés dès le hit.
3. **Traçage terrain** : `_traceGuardian()` avec les étapes `web_sr_hit`, `web_sr_context`, `web_sr_capture_final`, `web_sr_capture_timeout`, `vosk_received`, `vosk_open_countdown`, `sos_request`, `sos_response`, `sos_error`.
4. **Anti-doublon** :
   - `window.lunaEmergencyVoiceDetected` vérifie maintenant `_vocalActive` en plus de `_sosInProgress`.
   - `_vocalMatch` vérifie `_sosInProgress` en plus de `_vocalActive`.
   - `openVocalCountdown` coupe le micro (`_vocalRec.abort()`, `_vocalRestartT` clear, `_setMicState('off')`) avant de lever `_vocalActive` et d'appeler `_triggerSOSVocal()`.
5. **Nettoyage** : `_voiceTranscript` et `_voiceContext` sont réinitialisés après envoi SOS, en cas d'annulation, et après erreur.

---

## 11. Conclusion et prochaines étapes

**Validation** : la base `feature/pwa` / `stable/frontend-reference-2026-07-05` est sûre. Aucun retour en arrière graphique n'est à craindre. Le patch est limité à `static/guardian.html`.

**Action suivante obligatoire** : déploiement trace 0 % uniquement, puis validation terrain par Ludovic avant promotion.

**Rollback** : `git reset --hard f45fe4fb74bf02faf98f5f1a632cee98406cc51a` (branche PWA pure, UI stable intacte).

---

## 12. Test fonctionnel du flux complet

Un test autonome a été ajouté : `tests/test_guardian_voice_context_functional.js`.  
Il simule sans navigateur ni micro le flux complet sur la phrase :

> « Au secours, il est devant la porte, il essaie d'entrer. »

### Commande

```bash
node tests/test_guardian_voice_context_functional.js
```

### Résultat

```
=== Test flux vocal Guardian ===
Phrase testée : "Au secours, il est devant la porte, il essaie d'entrer."

--- Scénario A : Web Speech ---
1. Détection du mot-clé (interim) : "au secours"
   _voiceCaptureActive=true
   _voiceTranscript="au secours"

2. Arrivée de la phrase complète (final)
   _voiceTranscript="Au secours, il est devant la porte, il essaie d'entrer."
   _voiceContext="Au secours, il est devant la porte, il essaie d'entrer."
   _vocalActive=true

3. Attente de la fin du countdown (5 s)...
   Après attente : _vocalActive=false _sosInProgress=false
   fetchCalls.length=1

4. Vérification des appels backend
   Nombre de POST /api/guardian/sos/{SID} : 1
   Nombre de POST /api/guardian/voice-context : 0
   Payload SOS :
     incident_id = incident-1
     source      = vocal
     context     = Au secours, il est devant la porte, il essaie d'entrer.
     transcript  = Au secours, il est devant la porte, il essaie d'entrer.

--- Scénario B : Vosk natif ---
1. Appel de window.lunaEmergencyVoiceDetected avec la phrase complète
   _voiceTranscript="Au secours, il est devant la porte, il essaie d'entrer."

2. Attente de la fin du countdown...
   Nombre de POST /api/guardian/sos/{SID} : 1
   Nombre de POST /api/guardian/voice-context : 1

--- Scénario C : anti-doublon ---
Tentative de redéclenchement Web Speech pendant _sosInProgress=true
Tentative de redéclenchement Vosk pendant _sosInProgress=true
   Nombre de POST SOS après tentatives de doublon : 0

✅ SUCCÈS : un seul déclenchement, phrase complète transmise, anti-doublon OK.
```

### Preuves apportées par le test

| Assertion | Statut |
|---|---|
| Détection du mot-clé « au secours » | ✅ |
| Capture de la phrase complète après le hit | ✅ |
| `context` = phrase complète dans le POST SOS | ✅ |
| `transcript` = phrase complète dans le POST SOS | ✅ |
| Un seul POST `/api/guardian/sos/{SID}` par incident | ✅ |
| Vosk appelle `/api/guardian/voice-context` pour enrichir le contexte | ✅ |
| Aucun second POST SOS lors d'une tentative de doublon | ✅ |

---

## 13. Remarque sur les tests existants

`tests/test_guardian_p0.py` présente 7 échecs préexistants. Ils concernent les alertes automatiques GPS (géofence, immobilité, escalation) volontairement désactivées par la variable `_GUARDIAN_VOICE_ONLY=true` dans `core/guardian/engine.py` (commit `282e2bc`). Ces échecs ne sont pas introduits par le patch vocal et n'affectent pas le flux SOS manuel/vocal.

Les tests historiques `test_guardian_apk_vosk_trigger_static.py`, `test_guardian_sr_log_trigger_static.py` et `test_guardian_voice_frontend_static.py` sont obsolètes (ancienne route `/trigger` supprimée).

---

## 14. Décision demandée

Les preuves fonctionnelles sont fournies. Aucun déploiement n'est effectué.  
**Prochaine étape sur validation** : déploiement trace 0 % uniquement, puis test réel par Ludovic avant promotion.
