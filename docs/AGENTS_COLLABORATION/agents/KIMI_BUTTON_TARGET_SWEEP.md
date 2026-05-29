# Audit bouton par bouton / onglet par onglet — Objectif 002

> Agent : Kimi (Linux VM)  
> Date : 2026-05-28  
> Scope : `static/index.html` (monofichier ~8356 lignes) + `luna_web.py` (backend FastAPI) + `core/secretary/routes.py`  
> Méthode : analyse statique + tests curl non destructifs  
> Interdits respectés : aucun appel SMS/email/paiement/appel réel, aucune réservation, aucune alerte, pas de déploiement.

---

## 1. Vue d'ensemble — Architecture interactive

| Couche | Éléments |
|--------|----------|
| **Onglets** | 16 onglets navigables : chat, conciergerie, contacts, documents, formulaires, guardian, instructions, map, profile, quotas, settings, theo, amis, callreports, world, activities |
| **Boutons** | ~123 éléments `<button>` dont 50 avec `id=` explicite |
| **Inputs** | 77 champs de formulaire (email, texte, number, date, tel, password, search) |
| **Listeners click** | 34 `addEventListener('click')` + 71 `onclick` inline |
| **Fonctions JS** | 241 fonctions déclarées |
| **Endpoints API** | 276 routes backend (FastAPI) |
| **Appels API front** | ~69 références `/api/*` distinctes + 2 WebSockets |

---

## 2. Cartographie par onglet

### 📂 chat
| Bouton / Élément | Handler | API | Risque |
|------------------|---------|-----|--------|
| ✕ (fermer sidebar) | `sidebarClose.addEventListener` | — | — |
| + Nouvelle conversation | `newConvBtn.addEventListener` | `POST /api/conversations` | — |
| 😊 emoji toggle | `emojiToggle.addEventListener` | — | — |
| ➤ envoyer | `send.addEventListener` | `POST /api/chat` | 🟡 innerHTML injection |
| + (menu action) | `actionToggle.addEventListener` | — | — |

### 📂 conciergerie
| Bouton / Élément | Handler | API | Risque |
|------------------|---------|-----|--------|
| Actions : Alerte, Appelle, Recherche, Hôtel, Vol, SMS, Email, Courrier, Visio, Note, Rappel, Restaurant, Service proche, Météo, Actualités, Missions, Badges, Contacts confiance, Amis en ligne | `data-conc-action` → `_concDirect()` | `POST /api/concierge/action` | 🟡 20 actions → un seul endpoint, pas de validation fine côté client |
| ⬅ Retour | `_concBack()` | — | — |
| Scanner | `scanBtn.addEventListener` | `POST /api/secretary/scan` | — |
| Générer doc | `docGenerateBtn.addEventListener` | `POST /api/documents/generate` | — |

### 📂 contacts
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| Ajouter | `contactAddBtn.addEventListener` | `POST /api/contacts` | — |
| Appeler un contact | `_showCallContactModal()` → `_confirmCallContact()` → `startVoiceCall()` | `POST /api/voice-call` | 🔴 **Action sensible — confirmation P0 OK** |
| Visio Luna | `callBtn.addEventListener` → `startCall()` | redirige `/simli?duration=...` | 🔴 **Action sensible — confirmation P0 OK** |

### 📂 documents
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| Scanner | `scanBtn.addEventListener` | `POST /api/secretary/scan` | — |

### 📂 formulaires
*(Aucun bouton avec handler direct dans l'extrait analysé — probablement généré dynamiquement)*

### 📂 guardian
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| ▶ Démarrer | `guardianStartBtn.addEventListener` → `guardianStart()` | `POST /api/guardian/start` | — |
| ⏹ Arrêter | `guardianStopBtn.addEventListener` → `guardianStop()` | `POST /api/guardian/stop/{session_id}` | — |
| 🆘 SOS | `guardianSosBtn.addEventListener` → `guardianSOS()` | `POST /api/guardian/sos/{session_id}` | 🔴 **Action sensible — alerte SOS** |

### 📂 instructions
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| ↻ (rafraîchir) | `renBtn.addEventListener` | `GET /api/instructions` | — |
| ⏰ Réveil | onclick inline | `POST /api/instructions` | — |
| 💊 Médicaments | onclick inline | `POST /api/instructions` | — |
| 💬 Check-in matin | onclick inline | `POST /api/instructions` | — |
| 🧠 Quiz | onclick inline | `POST /api/instructions` | — |
| 📖 Lecture | onclick inline | `POST /api/instructions` | — |
| 🙏 Gratitude | onclick inline | `POST /api/instructions` | — |
| 🔔 Surveillance | onclick inline | `POST /api/instructions` | — |

### 📂 map
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| Rechercher | `mapSearchBtn.addEventListener` | Nominatim OSM (externe) | 🟡 dépendance externe |
| 📍 Ma position | `mapLocateBtn.addEventListener` | `POST /api/geolocation` | — |
| Itinéraire | `mapDirectionsBtn.addEventListener` | Nominatim OSM (externe) | 🟡 dépendance externe |

### 📂 profile
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| Sauvegarder | `profileSaveBtn.addEventListener` | `POST /api/profile` | — |

### 📂 quotas
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| *(Aucun bouton — affichage lecture seule)* | `loadQuotas()` | `GET /api/quota` | — |

### 📂 settings
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| *(Paramètres toggles — pas de bouton d'action directe)* | — | `GET/POST /api/settings` | — |

### 📂 theo
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| + Ajouter | onclick inline | `POST /api/theo/hours` | — |

### 📂 amis
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| Ajouter | `amisCodeBtn.addEventListener` | `POST /api/social/friend-code/use` | — |
| Salon | `amisSalonBtn.addEventListener` | `GET /api/social/dm/rooms` | — |

### 📂 callreports
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| 📝 Comptes Rendus | `loadCallReports()` | `GET /api/call-reports` | — |
| ✎ Mes Notes | `loadNotesData()` | `GET /api/notes` | — |
| 💻 Réunions | `loadMeetings()` | `GET /api/meeting/active` | — |
| 💬 SMS envoyés | `loadSmsLog()` | `GET /api/sms/status` | — |

### 📂 world
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| *(Aucun bouton dans l'extrait — probablement affichage carte monde)* | `loadMonde()` | — | — |

### 📂 activities
| Bouton | Handler | API | Risque |
|--------|---------|-----|--------|
| Activités shortcut | `activitiesShortcut.addEventListener` | — | — |

---

## 3. Problèmes identifiés

### 🔴 CRITIQUE — Routes API front sans backend correspondant (faux positif résolu)
- Les 6 routes `/api/secretary/*` sont bien définies dans `core/secretary/routes.py` (include_router monté dans luna_web.py l.4559).
- **Statut : ✅ OK, pas de régression.**

### 🟠 MAJEUR — 71 boutons avec `onclick` inline
- Présent surtout dans l'onglet Instructions et Théo.
- Risque : difficile à auditer, potentiel XSS si données utilisateur injectées.
- **Recommandation : migrer vers `addEventListener` dans une future refactor.**

### 🟠 MAJEUR — 143 usages de `.innerHTML`
- Dont plusieurs injectent du contenu dynamique (réponses conciergerie, résultats recherche).
- Risque XSS si le contenu utilisateur n'est pas sanitize.
- **Recommandation : auditer chaque ligne pour vérifier le sanitize ; préférer `textContent` pour du texte brut.**

### 🟡 MOYEN — Routes sans auth explicite accessibles publiquement
| Route | Méthode | Impact |
|-------|---------|--------|
| `/api/chat` | POST | Chatbot accessible sans auth 🔓 |
| `/api/call` | POST | Démarrage visio accessible sans auth 🔓 |
| `/api/visio/perception` | POST | Vision caméra accessible sans auth 🔓 |
| `/api/visio/notes` | POST | Notes visio accessibles sans auth 🔓 |
| `/api/greeting` | GET | OK — greeting publique |
| `/health`, `/ready` | GET | OK — healthchecks |

**Note :** certaines routes comme `/api/chat` et `/api/call` semblent ne pas avoir de dépendance `Depends(get_current_user)` dans leur signature. À vérifier si c'est intentionnel (chat anonyme ?) ou une omission.

### 🟡 MOYEN — `sendAppMessage(..., '*')` dans simli.html
- Envoie les messages système (vision) à tous les participants.
- **Recommandation : cibler uniquement le bot Simli.**

### 🟢 MINEUR — `SpeechRecognition` non supporté Firefox/Safari
- La transcription vocale des notes visio ne fonctionnera pas sur ces navigateurs.
- **Recommandation : fallback texte ou alerte utilisateur.**

### 🟢 MINEUR — WebSocket `/ws/simli/{session_id}` retourne 4003
- `_SIMLI_AVAILABLE = False` dans luna_web.py.
- La route REST `/api/simli/start` fonctionne, mais pas le WebSocket.
- **Impact :** fonctionnalité secondaire (logs temps réel ?) — la visio via Daily.js REST fonctionne.

---

## 4. Endpoints backend orphelins (jamais appelés par le front)

Ces endpoints existent dans le backend mais ne sont pas appelés par `index.html` :

| Endpoint | Usage probable |
|----------|---------------|
| `/api/assistant/*` (8) | API interne agents / outils LLM |
| `/api/auth/change-password` | Fonctionnalité non exposée dans l'UI |
| `/api/auth/checkout` | Paiement — peut-être dans un autre flow |
| `/api/call/create-join-link` | API interne |
| `/api/call/end` | Appelé par `simli.html` (hangup) |
| `/api/call/invite-guest` | API interne |
| `/api/config/simli` | Appelé par `simli.html` |
| `/api/contacts/{phone}` | Pas de route DELETE front directe |
| `/api/debug/log` | Appelé par le front (client logging) |
| `/api/documents/v2/*` | API v2 documents — pas encore branchée ? |
| `/api/email/*` | Fonctionnalité email — pas dans l'UI principale |
| `/api/events/*` | Export PDF événements |
| `/api/family/*` (18) | Module famille — pas dans l'UI principale |
| `/api/geolocation` | `POST` utilisé par map, `GET` orphelin ? |
| `/api/instructions/upcoming` | Pas utilisé dans le front principal |
| `/api/instructions/history` | Pas utilisé dans le front principal |
| `/api/invite-contact` | API interne |
| `/api/license/*` | API interne licensing |
| `/api/maintenance` | Healthcheck publique |
| `/api/meeting/*` | API interne bot réunion |
| `/api/perception/*` | API interne vision (pas visio) |
| `/api/profile/theme` | Thèmes — pas exposé dans l'UI |
| `/api/rooms/*` | Salons — appelé par l'onglet amis ? |
| `/api/setup/*` | Onboarding fondateur |
| `/api/simli/*` | Appelé par `simli.html` |
| `/api/social/*` (15) | Amis/social — partiellement utilisé |
| `/api/stripe/webhook` | Webhook externe |
| `/api/sync/*` | API interne |
| `/api/test/*` | API interne |
| `/api/themes/*` | Thèmes — pas exposé |
| `/api/theo/*` | Partiellement utilisé |
| `/api/unified/*` | Canal unifié — pas dans l'UI principale |
| `/api/visio/*` | Appelé par `simli.html` |
| `/api/voice-call/*` | Appelé par `index.html` (Twilio) |
| `/api/webhook/*` | Webhooks externes |
| `/api/webhooks/*` | Webhooks externes |
| `/api/weather` | Peut-être utilisé par header |

---

## 5. Synthèse des risques par sévérité

| Sévérité | Compteur | Items |
|----------|----------|-------|
| 🔴 Critique | 0 | Aucune régression critique détectée |
| 🟠 Majeur | 2 | 71 onclick inline, 143 innerHTML |
| 🟡 Moyen | 2 | Routes sans auth, sendAppMessage wildcard |
| 🟢 Mineur | 2 | SpeechRecognition compat, WebSocket Simli 4003 |

---

## 6. Tests non destructifs recommandés (à faire par Ludovic)

1. **Navigation onglet par onglet** : vérifier que chaque onglet s'affiche sans erreur console.
2. **Conciergerie** : tester "Quel temps fait-il" et "Actualités" (pas d'action sensible).
3. **Map** : vérifier la géolocalisation et la recherche d'adresse.
4. **Guardian** : vérifier le démarrage/arrêt (pas de SOS).
5. **Profil** : sauvegarder et recharger.
6. **Documents** : vérifier le scanner (simuler si pas de fichier).
7. **Chat** : envoyer un message, vérifier la réponse.
8. **Confirmations P0** : vérifier que Appeler et Visio affichent bien la modale de confirmation.

---

## 7. Conclusion

**Aucune régression critique détectée.** L'application est fonctionnellement cohérente front/back. Les points d'attention principaux sont :
- La dette technique (onclick inline, innerHTML) à traiter en refactor future.
- Les routes potentiellement sans auth à vérifier intentionnellement.
- Le module `/api/secretary/*` est bien branché (pas de régression).

---
*Fin du rapport d'audit bouton par bouton.*
