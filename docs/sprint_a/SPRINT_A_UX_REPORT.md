# Sprint A — UX Report
**Lead Frontend + QA : Claude**
**Date : 15 juin 2026**
**Branche : feature/sprint-a-ux**
**URL déployée : https://luna-beta-674304336025.europe-west1.run.app**
**Révision Cloud Run : luna-beta-00655-d46**

---

## Question directrice

**Qu'est-ce qui empêche aujourd'hui l'utilisateur de faire confiance à Luna dès les 5 premières minutes ?**

Réponse synthétique :
1. Il arrive sur un écran d'activités vide et ne sait pas comment revenir (piège nav)
2. Le workspace lui dit qu'il y a "4 participants en session" alors qu'il est seul (bruit fantôme)
3. Les boutons de suggestion ne correspondent pas à ce qu'il vient de dire (désynchronisation)
4. Il ne trouve pas le bouton micro (la promesse vocale est invisible)
5. Il voit un message d'erreur technique avant d'avoir dit un mot ("serveur tourne")

---

## FIX-01 — Activités : barre de retour sticky

**Priorité : 🔴 CRITIQUE**

### Problème
L'onglet Activités navigue vers `/salon` — page séparée sans navigation principale. Le seul retour possible était un petit lien "← Retour" en haut à droite, introuvable sur mobile. L'utilisateur était **piégé**.

### Reproduction
1. Se connecter → Chat
2. Cliquer "Activités" dans la nav
3. Observer : page séparée "Aucune activite en cours"
4. Essayer de revenir au Chat → aucun onglet visible

### Capture avant
`screenshots/BUG-01-before.png` *(situation documentée dans LUNA_UI_BUGS.md)*

### Capture après
`screenshots/FIX-01-salon-retour.png`

### Impact utilisateur
L'utilisateur qui explore Activités par curiosité se retrouvait bloqué sur une page vide. Il fermait l'app.

### Correctif effectué
Ajout d'une barre sticky fixe en bas d'écran (`#embedBackBar`) sur `/salon` lorsque `embed=1` est dans l'URL. La barre affiche **"← Retour au Chat"** en violet, pleine largeur, toujours visible.

**Fichier modifié : `static/salon.html`**
```html
<div id="embedBackBar" style="display:none;position:fixed;bottom:0;...">
  <a href="/">← Retour au Chat</a>
</div>
```
Le JS active la barre et ajoute `padding-bottom:60px` au container pour qu'elle ne masque pas le contenu.

### Validation Playwright
```
BUG01_back_bar: VISIBLE (w=390, h=45, top=799, text="Retour au Chat")
```

---

## FIX-02 — Workspace : session fantôme éliminée

**Priorité : 🔴 CRITIQUE**

### Problème
À l'ouverture de `/team`, le header affichait **"EN SESSION · 4 participants"** en données demo issues de `SEATS_TOP/SEATS_BOT` (fixtures de développement jamais nettoyées). L'utilisateur pensait entrer dans la session de quelqu'un d'autre.

### Reproduction
1. Aller sur `/team`
2. Observer la modal d'entrée : badge "EN SESSION · 4 participants" visible en arrière-plan
3. La phase "Brief" était déjà cochée

### Capture avant
`screenshots/BUG-02-before.png` *(documenté dans LUNA_UI_BUGS.md, capture C6)*

### Capture après
`screenshots/FIX-02-workspace-propre.png`

### Impact utilisateur
Doute sur la confidentialité. "D'autres personnes sont dans mon espace." Il ne crée pas sa session.

### Correctif effectué
**Fichier modifié : `static/team_workspace.html`**

1. HTML : `<strong>4</strong>` → `<strong>0</strong>` dans `#twPStat`
2. Status label : `"En session"` → `id="twStatusLbl"` avec texte initial `"En attente"`
3. `updateStats()` : branche `else` (WS non connecté) retourne `tot=0` au lieu de `SEATS_TOP.length + SEATS_BOT.filter(!ai).length` = 4

```js
} else {
  tot = 0; /* Pas encore connecté — ne pas afficher les données de démo */
}
// Mise à jour dynamique du label
var lbl = document.getElementById('twStatusLbl');
if (lbl) lbl.textContent = TW.wsConnected ? 'En session' : 'En attente';
```

### Validation Playwright
```
participants: "0 participants"
status: "En attente"
```
Bascule vers "En session" uniquement après `state_sync` WebSocket.

---

## FIX-03 — Chips contextuelles (basées sur la conversation)

**Priorité : 🟠 HAUTE**

### Problème
`_getSmartChips()` générait des suggestions basées **uniquement sur l'heure** — identiques après "Vol Paris Rome" et après "Bonne nuit Luna". L'utilisateur comprenait immédiatement que Luna ne l'écoutait pas.

### Reproduction
1. Chat → "Vol Paris Rome jeudi prochain"
2. Attendre réponse Luna
3. Observer les chips : "🌙 Bonne nuit / 😌 Relaxation / 📝 Gratitude / 🎤 Parler"

### Capture avant
`screenshots/BUG-03-before.png` *(documenté LUNA_UI_BUGS.md)*

### Captures après
`screenshots/FIX-03-chips-vol.png`
`screenshots/FIX-03-chips-medecin.png`

### Impact utilisateur
Les chips sont le seul feedback immédiat que Luna a compris. Si elles ne correspondent pas, la confiance est perdue sans que l'utilisateur sache pourquoi.

### Correctif effectué
**Fichier modifié : `static/index.html`** — fonction `_getSmartChips()` complètement réécrite.

La fonction lit maintenant les derniers messages dans le DOM via `.msg .msg-text` et détecte des patterns par regex :

| Contexte détecté | Chips affichées |
|---|---|
| vol, avion, flight, aéroport | ✈️ Chercher un vol / 🏨 Trouver un hôtel / 📋 Mes voyages |
| médecin, docteur, rdv, santé | 📅 Prendre RDV / 💊 Mes médicaments / 🏥 Médecin proche |
| restaurant, manger, déjeuner | 🍽️ Restaurant proche / ⭐ Mieux noté / 📍 Itinéraire |
| musique, chanson, playlist | 🎵 Autre chanson / 😌 Relaxation / 🎸 Par genre |
| météo, pluie, soleil | 📅 Semaine entière / 👔 Que mettre ? / 🌍 Autre ville |
| actualité, news, info | 🌍 International / 💼 Économie / 🔄 Rafraîchir |
| appel, famille, SMS | 📞 Appeler / 💬 Envoyer SMS / 👥 Mes contacts |
| *(aucun)* | Repli horaire (comportement original) |

Toujours suivi de `🎤 Parler`.

### Validation Playwright
```
chips_vol:     ["✈️ Chercher un vol", "🏨 Trouver un hôtel", "📋 Mes voyages", "🎤 Parler"]
chips_medecin: ["📅 Prendre RDV", "💊 Mes médicaments", "🏥 Médecin proche", "🎤 Parler"]
```

---

## FIX-04 — Bouton micro visible dans la zone de saisie

**Priorité : 🟠 HAUTE**

### Problème
Le bouton voix (`#lunaVoiceBtn`) était un bouton flottant caché (`display:none`) accessible uniquement via wake word ou menu `+`. La voix — promesse centrale du produit — était **invisible**.

### Reproduction
1. Chat → observer la barre de saisie
2. `[ 😊 ][ Message pour Luna...       ][ ➤ ][ + ]`
3. Aucun micro visible

### Capture avant
`screenshots/BUG-04-before.png` *(documenté LUNA_UI_BUGS.md, capture C8b)*

### Capture après
`screenshots/FIX-04-mic-input-zone.png`

### Impact utilisateur
La voix n'est jamais découverte. L'utilisateur n'utilise que le chat texte et manque l'expérience différenciante.

### Correctif effectué
**Fichier modifié : `static/index.html`**

Ajout d'un bouton `#micInputBtn` directement dans `.input-row`, entre le textarea et le bouton send :

```html
<button class="mic-input-btn" id="micInputBtn" type="button" title="Parler à Luna"
  onclick="var vb=document.getElementById('lunaVoiceBtn');if(vb)vb.click();">
  <svg><!-- icône micro --></svg>
</button>
```

CSS ajouté :
```css
.mic-input-btn { background:none; border:none; cursor:pointer; color:#888; ... }
.mic-input-btn:hover { color:#a78bfa; background:rgba(124,58,237,0.1); }
.mic-input-btn.active { color:#4ade80; animation:pulse 1.5s infinite; }
```

Le clic délègue à `#lunaVoiceBtn.click()` — le système vocal existant est déclenché sans duplication de code.

### Validation Playwright
```
mic_visible: true  (w=36, h=40, top=795, left=263)
```
Zone input : `[ 😊 ][ Message pour Luna...    ][ 🎤 ][ ➤ ][ + ]`

---

## FIX-05 — Messages d'erreur utilisateur

**Priorité : 🟠 HAUTE**

### Problème
Deux messages d'erreur avec un ton développeur étaient visibles par les utilisateurs finaux :

1. **Premier écran (cold start)** : `"Luna est temporairement injoignable. Verifie que le serveur tourne."` — apparaît si le Cloud Run cold start dépasse le timeout de `/api/greeting`
2. **Échec d'envoi** : `"Erreur : Failed to fetch"` — message d'exception JavaScript brut

### Reproduction
1. Ouvrir l'app après un cold start Cloud Run (instance non chauffée)
2. Le message apparaît dans le chat avant toute interaction utilisateur

### Impact utilisateur
Le premier message qu'un utilisateur voit depuis Luna est une alerte technique. La confiance est perdue avant d'avoir commencé.

### Correctif effectué
**Fichier modifié : `static/index.html`**

**Greeting failure** (ligne ~6810) :
- Avant : `addMsg("Luna est temporairement injoignable. Verifie que le serveur tourne.", "luna")`
- Après : Message bienveillant + retry automatique dans 4s qui remplace le message si succès

```js
.catch(function() {
  addMsg("Je me réveille… Un instant ☀️", "luna");
  setTimeout(function() {
    authFetch("/api/greeting?...").then(...)
    .then(function(data) {
      // retire le message "réveille" et affiche la vraie réponse
    }).catch(function(){});
  }, 4000);
});
```

**Send failure** (ligne ~4543) :
- Avant : `"Erreur : " + (e.message || "connexion perdue")`
- Après : `"Je n'ai pas pu répondre. Vérifie ta connexion."`

---

## FIX-08 — Workspace : placeholder développeur remplacé

**Priorité : 🟡 MOYENNE**

### Problème
`placeholder="Comment rendre Luna rentable ?"` — une question produit interne exposée à tous les utilisateurs dans le champ "Titre de la session".

### Correctif effectué
**Fichier modifié : `static/team_workspace.html`**
```
Avant : placeholder="Comment rendre Luna rentable ?"
Après : placeholder="Ex : Stratégie de lancement, Analyse concurrentielle…"
```

### Validation Playwright
```
placeholder: "Ex : Stratégie de lancement, Analyse concurrentielle…"
```

---

## Résumé des correctifs

| Fix | Priorité | Fichier | Validation |
|---|---|---|---|
| FIX-01 Activités barre retour | 🔴 CRITIQUE | salon.html | ✅ Playwright |
| FIX-02 Workspace fantôme | 🔴 CRITIQUE | team_workspace.html | ✅ Playwright |
| FIX-03 Chips contextuelles | 🟠 HAUTE | index.html | ✅ Playwright |
| FIX-04 Micro visible | 🟠 HAUTE | index.html | ✅ Playwright |
| FIX-05 Messages d'erreur | 🟠 HAUTE | index.html | ✅ Code review |
| FIX-08 Placeholder workspace | 🟡 MOYENNE | team_workspace.html | ✅ Playwright |

---

## Bugs non adressés en Sprint A (scope Kimi ou Sprint B)

| Bug | Scope | Note |
|---|---|---|
| BUG-05 Guardian page séparée | Sprint B | Le "← App" fonctionne, sévérité moyenne |
| BUG-06 Iris Visio desktop fond SVG | Sprint B | CSS positioning sur grand écran |
| BUG-07 "Appel entrant..." dans DOM /simli | Sprint B | Nettoyage résidu UI, accessibilité |
| BUG-09 Rapports sans pagination | Sprint B | 31 entrées OK pour maintenant |
| BUG-10 Desktop sidebar conversations sans titre | Sprint B | Faible impact |
| BUG-11 "Iris Workspace" dans Services | Sprint B | Architecture menu |

---

## Navigation : état post-Sprint A

Tous les onglets SPA restent sur `/` URL après navigation (navigation interne correcte).

| Onglet | URL après clic | État |
|---|---|---|
| Chat | / | ✅ SPA |
| Services | / | ✅ SPA |
| Amis | / | ✅ SPA |
| Monde | / | ✅ SPA |
| Rapports | / | ✅ SPA |
| Réglages | / | ✅ SPA |
| Activités | /salon | ⚠️ Page séparée — retour visible maintenant |
| Guardian | /guardian | ⚠️ Page séparée — "← App" fonctionne |

---

*Méthode : Playwright E2E, mobile 390×844 + desktop 1440×900*
*Commit : feature/sprint-a-ux*
*Révision déployée : luna-beta-00655-d46 (5 fixes) → luna-beta-00656-xxx (FIX-05 ajouté)*
