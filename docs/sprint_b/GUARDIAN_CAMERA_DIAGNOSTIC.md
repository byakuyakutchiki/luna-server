# Guardian — Diagnostic Caméra
**Sprint B — Priorité #1**
**Date : 15 juin 2026**
**Auteur : Claude (Lead Technique)**
**Statut : DIAGNOSTIC UNIQUEMENT — aucune modification apportée**

---

## Question directrice

**Pourquoi la caméra Guardian ne démarre-t-elle pas ?**

---

## Résumé exécutif

La caméra Guardian échoue silencieusement avant même d'atteindre `getUserMedia()`.  
Il y a **deux causes racines primaires**, distinctes et cumulatives :

1. **Guardian ne peut pas démarrer sans contact d'urgence** → `SID` jamais obtenu → caméra bloquée à la première ligne de `cameraStart()`
2. **La modal "Autoriser" ne demande pas la caméra** → permission caméra jamais pré-accordée → Android refuse lors du clic "Activer caméra"

Les deux causes agissent de concert et expliquent que l'utilisateur voit soit "Démarrez Guardian d'abord", soit "Caméra refusée", sans jamais comprendre pourquoi.

---

## Carte des composants

```
APK (MainActivity.java)
├── AndroidManifest.xml          ← permissions déclarées
├── WebView + WebChromeClient    ← onPermissionRequest() pour caméra/micro
└── WebViewClient                ← navigation, erreurs SSL

Serveur (luna_web.py)
├── GET  /guardian               ← sert guardian.html (pas de Permissions-Policy)
├── POST /api/guardian/start     ← bloque si pas de contact d'urgence
└── POST /api/guardian/frame/:id ← jamais atteint (frames n'arrivent pas)

Frontend (guardian.html)
├── grantPermissions()           ← demande micro UNIQUEMENT (pas caméra)
├── guardianStart()              ← obtient SID (prérequis camera)
└── cameraStart()                ← appelle getUserMedia — POINT DE DÉFAILLANCE
```

---

## PROBLÈME #1 — Guardian bloqué sans contact d'urgence

**Sévérité : 🔴 CRITIQUE**
**Fichier : `luna_web.py` ligne 14363**

### Code responsable

```python
# luna_web.py:14363
if not emergency_contacts and not config.get("emergency_contacts"):
    return JSONResponse(status_code=422, content={
        "error": "Aucun contact d'urgence configuré. Ajoute au moins un contact...",
        "code": "no_emergency_contacts",
    })
```

### Conséquence

`guardianStart()` reçoit une erreur 422 → `SID` reste `null`.

Puis :

```js
// guardian.html:1199
async function cameraStart(){
  if(!SID){ showToast('Démarrez Guardian d\'abord'); return; }  // ← SORT ICI
  ...
}
```

**La caméra ne peut pas démarrer si Guardian n'est pas actif. Guardian ne peut pas démarrer sans contact d'urgence.**

L'utilisateur n'a aucune indication que le problème est l'absence de contacts — il voit juste le toast "Démarrez Guardian d'abord" sans comprendre pourquoi le démarrage a échoué.

### Chemin exact de l'échec

```
Clic "Démarrer" → POST /api/guardian/start → 422 no_emergency_contacts
    → guardianStart() catch → toast "❌ Aucun contact d'urgence configuré..."
    → SID = null, btn-start toujours visible
    → Clic "Activer caméra" → cameraStart() → SID null → toast "Démarrez Guardian d'abord"
```

---

## PROBLÈME #2 — Modal permissions ne demande pas la caméra

**Sévérité : 🔴 CRITIQUE**
**Fichier : `guardian.html` ligne 746**

### Code responsable

```js
// guardian.html:746
async function grantPermissions(){
  closePerm();
  if(navigator.mediaDevices && navigator.mediaDevices.getUserMedia){
    try{ await navigator.mediaDevices.getUserMedia({audio:true}); }catch(e){}
    // ↑ AUDIO SEULEMENT — la caméra n'est jamais pré-demandée ici
  }
  if(window.Notification && Notification.permission==='default')
    await Notification.requestPermission();
}
```

### Ce que voit la modal

```html
<!-- guardian.html:550 -->
<li id="perm-mic" style="display:none;">🎤 Microphone — vérification vocale</li>
<!-- Pas de ligne pour la caméra -->
```

La modal "Autoriser et démarrer" annonce le microphone uniquement. La caméra n'est pas mentionnée.

### Conséquence sur Android

1. Utilisateur clique "Autoriser" → Android demande le **micro** → accordé
2. Plus tard, utilisateur clique "Activer caméra" → `getUserMedia({video:...})` → Android WebView déclenche `onPermissionRequest(RESOURCE_VIDEO_CAPTURE)`
3. `MainActivity.onPermissionRequest()` vérifie `checkSelfPermission(CAMERA)` :
   - Si jamais accordé → `requestPermissions([CAMERA])` → dialog Android s'affiche
   - Si précédemment refusé avec "Ne plus demander" → dialog ne s'affiche PLUS → `grantResults = [DENIED]` → `req.deny()` → JS reçoit `NotAllowedError`

Le comportement varie selon l'historique de permission du téléphone.

---

## PROBLÈME #3 — Refus permanent de caméra Android (cas fréquent)

**Sévérité : 🟠 HAUTE**
**Fichier : `MainActivity.java` ligne 780**

### Comportement Android

Sur Android 11+ :
- 1ère demande : dialog "Autoriser / Refuser"
- 2ème demande (si refusé) : dialog "Autoriser / Refuser / Ne plus demander"
- 3ème demande (si "Ne plus demander" coché) : **aucun dialog, refus silencieux immédiat**

### Code concerné

```java
// MainActivity.java:257–266
if (cameraOk && audioOk) {
    runOnUiThread(() -> request.grant(request.getResources()));
} else {
    pendingPermissionRequest = request;
    String[] perms = needCamera ? new String[]{ Manifest.permission.CAMERA } : ...;
    requestPermissions(perms, PERMISSION_REQUEST_CODE);
    // ↑ Si "Ne plus demander" coché : onRequestPermissionsResult() reçoit DENIED immédiatement
}
```

```java
// MainActivity.java:788–792
if (allGranted) {
    runOnUiThread(() -> req.grant(req.getResources()));
} else {
    runOnUiThread(() -> req.deny());  // ← silencieux, pas de toast, pas de redirect
}
```

Le code appelle `req.deny()` sans toast ni instruction pour l'utilisateur. Côté JS :

```js
// guardian.html:1233
} catch(e) {
  if(e.name==='NotAllowedError'||e.name==='PermissionDeniedError'){
    _setCamState('refused'); showToast('Caméra refusée',3000);  // ← toast vague
  }
}
```

L'utilisateur voit "Caméra refusée" sans savoir qu'il doit aller dans Paramètres > Luna > Autorisations.

---

## PROBLÈME #4 — Contrainte `facingMode` non flexible

**Sévérité : 🟠 HAUTE**
**Fichier : `guardian.html` ligne 1225**

### Code responsable

```js
_camStream = await navigator.mediaDevices.getUserMedia({
  video: { facingMode: 'environment', width:{ideal:320}, height:{ideal:240} },
  audio: false
});
```

`facingMode: 'environment'` est une contrainte **exacte** (`advanced` sans `ideal`). Si le WebView Android ne peut pas accorder la caméra arrière spécifiquement (certains modèles, versions WebView), cela lève `OverconstrainedError` au lieu de tomber sur la caméra disponible.

La forme correcte pour une contrainte préférentielle : `{ facingMode: { ideal: 'environment' } }`.

---

## PROBLÈME #5 — Absence du header `Permissions-Policy`

**Sévérité : 🟡 MOYENNE**
**Fichier : `luna_web.py` ligne 8553**

### Code actuel

```python
# luna_web.py:8553
return FileResponse(path, headers={
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
    # ← pas de Permissions-Policy
})
```

Chrome 88+ et WebView Android récents respectent `Permissions-Policy: camera=(self)`. Sans ce header, la politique par défaut s'applique — généralement permissive pour les top-level documents, mais des configurations Enterprise MDM ou des paramètres WebView stricts peuvent bloquer.

**Header manquant :**
```
Permissions-Policy: camera=(self), microphone=(self), geolocation=(self)
```

---

## PROBLÈME #6 — Video element non dimensionné

**Sévérité : 🟢 INFO**
**Fichier : `guardian.html` ligne 432**

```html
<video id="cam-video" muted playsinline
  style="display:none; position:fixed; width:1px; height:1px; opacity:0; pointer-events:none;">
</video>
```

Certaines versions de WebView Android ont des difficultés à décoder un flux vidéo sur un élément `display:none` même si `srcObject` est défini et `play()` est appelé. Le canvas `drawImage()` sur un élément non rendu peut retourner une frame noire.

La frame noire est détectée mais filtrée :
```js
var frame = canvas.toDataURL('image/jpeg', 0.65).split(',')[1];
if (!frame || frame.length < 200) return; // frame noire/vide
```

Les frames ne partent jamais au serveur → pas de logs Cloud Run pour `/api/guardian/frame/`.

---

## Vérification Cloud Run

**Requête :** `gcloud logging read ... guardian|camera|frame`
**Résultat :** Aucune entrée

Confirme que `POST /api/guardian/frame/:id` n'est **jamais appelé**.  
Le problème est entièrement côté client (WebView Android), pas côté serveur.

---

## Synthèse des causes

| # | Problème | Sévérité | Localisation | Bloquant ? |
|---|---|---|---|---|
| 1 | Pas de SID sans contact d'urgence | 🔴 CRITIQUE | `luna_web.py:14363` | ✅ OUI |
| 2 | `grantPermissions()` ne demande pas la caméra | 🔴 CRITIQUE | `guardian.html:748` | ✅ OUI |
| 3 | Refus permanent Android (`Ne plus demander`) | 🟠 HAUTE | `MainActivity.java:788` | ✅ OUI (si déjà refusé) |
| 4 | `facingMode: 'environment'` contrainte exacte | 🟠 HAUTE | `guardian.html:1225` | Sur certains appareils |
| 5 | Pas de `Permissions-Policy` header | 🟡 MOYENNE | `luna_web.py:8553` | Rare |
| 6 | `<video>` 1px et display:none | 🟢 INFO | `guardian.html:432` | Frame noire possible |

---

## Chemin de défaillance le plus probable

```
Utilisateur ouvre /guardian
    → clique "Autoriser" → modal demande MICRO seulement (pas caméra)
    → clique "Démarrer" → POST /api/guardian/start
        → si pas de contact d'urgence : 422 → SID=null → BLOQUÉ ici
        → si contacts OK : SID obtenu, Guardian actif
    → clique "Activer caméra" → cameraStart()
        → getUserMedia({video: {facingMode:'environment'}})
        → Android WebView déclenche onPermissionRequest
            → si 1ère fois : dialog Android → accordé → caméra démarre
            → si déjà refusé 1x : dialog "Ne plus demander" → peut être refusé
            → si "Ne plus demander" coché : refus silencieux → NotAllowedError
                → toast "Caméra refusée" sans explication
    → si caméra accordée mais video 1px : frames noires → filtrées → serveur jamais appelé
```

---

## Périmètre non modifié

Conformément à la mission : **aucune ligne de code n'a été modifiée.**

Ce rapport est purement analytique. Les corrections relèvent de Sprint B.

---

*Méthode : lecture source + analyse statique Android/WebView/JS*
*Fichiers lus : `guardian.html`, `MainActivity.java`, `AndroidManifest.xml`, `network_security_config.xml`, `luna_web.py`*
*Logs Cloud Run : aucune trace guardian/camera*
