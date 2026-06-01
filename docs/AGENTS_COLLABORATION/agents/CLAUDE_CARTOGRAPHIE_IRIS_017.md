# Claude — Cartographie labels Iris + Auth audit — Objectif 017

Agent : Claude  
Objectif : 017  
Date : 2026-06-01  
Commit : en cours  
Type : cartographie / patch labels Niveau 1

---

## Résultat

Tous les labels visibles "Luna" remplacés par "Iris" dans `static/simli.html`.  
Layout refonte = Niveau 2 — en attente validation Kimi/Codex.  
Auth JWT = OK sur tous les endpoints `/api/visio/*`.

---

## Carte complète Luna → Iris (surface visio)

| Ligne | Avant | Après | Statut |
|---|---|---|---|
| 9 | `<title>Luna IA — Visio</title>` | `<title>Iris — Visio</title>` | ✅ |
| 511 | `Visio avec Luna` | `Visio avec Iris` | ✅ |
| 583 | `caller-name: Luna` | `caller-name: Iris` | ✅ |
| 632 | `Luna voit` (visionLabel) | `Iris voit` | ✅ |
| 636 | `🎙 Luna active` (btnMuteLuna) | `🎙 Iris active` | ✅ |
| 637 | titre `à Luna` (btnUpload) | `à Iris` | ✅ |
| 666 | `Luna est une IA` (share warning) | `Iris est une IA` | ✅ |
| 734–766 | 9 scènes : `Luna se réveille…` etc. | `Iris se réveille…` etc. | ✅ |
| 1023 | `rejoindre Luna` (ready toast) | `rejoindre Iris` | ✅ |
| 1103 | `👁 Luna regarde…` (tool label) | `👁 Iris regarde…` | ✅ |
| 1257 | `Luna décroche…` (cinématique) | `Iris décroche…` | ✅ |
| 1797 | `📎 Luna prend connaissance…` | `📎 Iris prend connaissance…` | ✅ |
| 1821 | `✓ Luna a analysé…` | `✓ Iris a analysé…` | ✅ |
| 1882 | `🔇 Luna muette / 🎙 Luna active` | `🔇 Iris muette / 🎙 Iris active` | ✅ |
| 1884 | toasts mute/unmute | `Iris écoute… / Iris peut parler…` | ✅ |
| 2034 | `Rejoindre la visio Luna` (share) | `Rejoindre la visio Iris` | ✅ |
| 2035 | `visio avec Luna IA` (share) | `visio avec Iris (Luna YAWatch)` | ✅ |
| 2056 | `Luna note sans en parler` | `Iris note sans en parler` | ✅ |
| 2057 | `Luna voit et peut en parler` | `Iris voit et peut en parler` | ✅ |
| 2069 | `_visionLabelEl: Luna voit` | `Iris voit` | ✅ |

**Total : 20 occurrences corrigées.**

---

## Luna conservé intentionnellement

| Ligne | Raison |
|---|---|
| 1702 | `retourne sur Luna pour te connecter` — message d'erreur guest, "Luna" = app brand, pas interlocutrice |
| Variables internes | `_lunaMuted`, `btnMuteLuna`, `lunaToast` — IDs non visibles utilisateur |
| Commentaires | Non visibles utilisateur |

---

## "Chatbot" Daily.js — hors code

Le label "Chatbot" visible dans la capture Codex vient du **nom du persona Tavus** dans le dashboard Tavus.  
Ce n'est pas dans le code — il faut aller dans `app.tavus.io → Personas → p10341f761ef → changer le nom en "Iris"`.  
Aucune modification code nécessaire pour ce point.

---

## Audit Auth JWT

**Résultat : OK.**

- `/api/visio/transcribe` — JWT requis (hors `_PUBLIC_PATHS`)
- `/api/visio/chat` — JWT requis
- `/api/visio/tts` — JWT requis

La liste `_PUBLIC_PATHS` (luna_web.py:3546) ne contient aucun chemin `/api/visio/`.  
Le middleware `_is_public_path()` couvre ces trois endpoints → authentification obligatoire.

Le frontend `simli.html` passe le token via :
- `authFetch()` (pour `/api/visio/chat`, `/api/visio/tts`, `/api/visio/upload`)
- `localStorage.getItem('luna_token')` dans `_sendVADAudio()` pour `/api/visio/transcribe`

**Point de vigilance** : si `luna_token` absent dans localStorage (session expirée), `/api/visio/transcribe` retourne 401 silencieux.  
Log à surveiller : `vad_transcribe_err` → cause probable = 401 JWT expiré.

---

## Ce que Claude n'a PAS fait (Niveau 2)

- Refonte layout visio mobile (en attente Kimi)
- Réorganisation boutons / hiérarchie visuelle
- Correction superposition orbe VAD / barre actions
- Diagnostic rupture pipeline voix (en attente DeepSeek)

---

## Prochaines étapes

| Qui | Quoi |
|---|---|
| **Tavus dashboard** | Renommer persona `p10341f761ef` en "Iris" → élimine le label "Chatbot" Daily |
| **Kimi** | Proposer layout mobile visio Iris → validation Ludovic requise (Niveau 2) |
| **DeepSeek** | Audit rupture voix : VAD → MediaRecorder → blob → transcribe → chat → TTS → player |
| **Codex** | Test terrain post-deploy : vérifier tous les labels, confirmer "Chatbot" disparu |
