# Kimi — Audit granulaire Objectif 011 (9 points par service)

> Date : 2026-05-27
> Complément technique au KIMI_AVIS_011.md (UX humain)
> Format : 1 tableau = 1 service, 9 points obligatoires

---

## Méthode

Audit statique du code (static/index.html + luna_web.py).
Pas de test API externe. Pas d'action réelle déclenchee.

Légende :
- Handler JS = fonction frontend dans static/index.html
- Endpoint = route backend dans luna_web.py
- Tool = fonction Python exécutee cote serveur
- Cockpit = /api/admin/dashboard + /api/admin/alerts + /fondateur.html

---

## Section 1 — Recherche & Voyage

### 1.1 Météo

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Obtenir la meteo actuelle et previsions pour sa ville |
| 2 | Handler frontend | _concDirect("weather", {}, "Meteo", _renderWeather) — ligne ~3125 |
| 3 | Action backend / tool | _tool_get_weather() → wttr.in + fallback Open-Meteo |
| 4 | Cles/API necessaires | Aucune (APIs gratuites, pas de cle) |
| 5 | Type | Lecture seule — recherche externe |
| 6 | Si ca marche | Carte meteo avec temperature, description, previsions 3 jours |
| 7 | Si ca echoue | Message "Service meteo temporairement indisponible" |
| 8 | Remonte cockpit ? | Non — erreur logguee cote serveur mais pas remontee au dashboard |
| 9 | Correction minimale | Aucune — service fiable et sans risque |

### 1.2 Actualites

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Lire les dernieres actualites francaises |
| 2 | Handler frontend | _concDirect("news", {category, count}, "Actualites", _renderNews) — ligne ~3126 |
| 3 | Action backend / tool | _tool_get_news() → RSS France Info / Le Monde |
| 4 | Cles/API necessaires | Aucune (flux RSS publics) |
| 5 | Type | Lecture seule — recherche externe |
| 6 | Si ca marche | Liste d'articles avec titre, source, date, lien |
| 7 | Si ca echoue | Message "Actualites temporairement indisponibles" |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 1.3 Recherche web

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Chercher une information sur internet |
| 2 | Handler frontend | _concDirect("search_web", {query}, "Resultats", _renderWebResults) — ligne ~3292 |
| 3 | Action backend / tool | _tool_search_web() → Serper API |
| 4 | Cles/API necessaires | SERPER_API_KEY dans .env |
| 5 | Type | Lecture seule — recherche externe |
| 6 | Si ca marche | Liste de liens avec titre, snippet, URL |
| 7 | Si ca echoue | Message "Recherche web indisponible" |
| 8 | Remonte cockpit ? | Non — le dashboard verifie openai/twilio mais PAS Serper |
| 9 | Correction minimale | Ajouter serper dans la liste services du dashboard admin |

### 1.4 Autour de moi

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Trouver des commerces/services proches |
| 2 | Handler frontend | _concDirect("search_places", params, "Autour de moi", _renderPlaces) — ligne ~3124 |
| 3 | Action backend / tool | _tool_search_places() → Serper Places API |
| 4 | Cles/API necessaires | SERPER_API_KEY |
| 5 | Type | Lecture seule — recherche externe |
| 6 | Si ca marche | Carte avec lieux, adresses, distances, liens Maps |
| 7 | Si ca echoue | "Aucun resultat trouve" ou erreur Serper |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Ajouter serper dans le dashboard admin |

### 1.5 Vols

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Chercher un vol et eventuellement le reserver |
| 2 | Handler frontend | Recherche : _concDirect("search_flights", params, "Vols", _renderFlights) ~3256 ; Reservation : _concBookFlight(offerId, price) ~3538 |
| 3 | Action backend / tool | Recherche : _tool_search_flights() → Duffel/Amadeus ; Reservation : _conc_book_flight() → Duffel |
| 4 | Cles/API necessaires | DUFFEL_API_KEY ou AMADEUS_API_KEY + AMADEUS_SECRET |
| 5 | Type | Recherche = lecture seule ; Reservation = action sensible / payante |
| 6 | Si ca marche | Recherche : liste vols avec prix ; Reservation : "Reservation confirmee ! Ref: XXX" |
| 7 | Si ca echoue | Recherche : "Aucun vol trouve" ; Reservation : erreur Duffel ou profil incomplet |
| 8 | Remonte cockpit ? | Non — erreurs Duffel logguees mais pas comptabilisees dans le dashboard |
| 9 | Correction minimale | Sandbox obligatoire avant tout test exploitant |

### 1.6 Hotels

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Chercher un hotel et eventuellement le reserver |
| 2 | Handler frontend | Recherche : _concDirect("search_hotels", params, "Hotels", _renderHotels) ~3268 ; Reservation : _concBookHotel(rateId, hotelName) ~3591 |
| 3 | Action backend / tool | Recherche : _tool_search_hotels() → Duffel ; Reservation : _conc_book_hotel() → Duffel |
| 4 | Cles/API necessaires | DUFFEL_API_KEY ou AMADEUS_API_KEY |
| 5 | Type | Recherche = lecture seule ; Reservation = action sensible / payante |
| 6 | Si ca marche | Recherche : liste hotels ; Reservation : "Hotel reserve !" |
| 7 | Si ca echoue | Meme pattern que Vols |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Sandbox obligatoire |

### 1.7 Restaurants

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Chercher un restaurant (et potentiellement reserver) |
| 2 | Handler frontend | _concDirect("book_restaurant", params, "Restaurants", _renderRestaurants) ~3285 |
| 3 | Action backend / tool | _tool_book_restaurant() → TheFork (si configure) → fallback search_places |
| 4 | Cles/API necessaires | THEFORK_API_KEY (optionnel — fallback Serper si absent) |
| 5 | Type | Lecture seule (recherche) — pas de reservation directe |
| 6 | Si ca marche | Liste de restaurants avec adresse, telephone, liens |
| 7 | Si ca echoue | Fallback sur search_places |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Renommer la carte "Restaurants" → "Chercher un restaurant" |


---

## Section 2 — Communication (5 services)

### 2.1 SMS

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Envoyer un SMS a un contact de confiance |
| 2 | Handler frontend | _concDirect("send_sms", params, "SMS", renderer) ~3305 ; MAJ 2026-05-26 : _showConfirm() ajoute avant envoi (commit cadfa43) |
| 3 | Action backend / tool | _tool_send_sms() → Twilio _tracked_sms_send() |
| 4 | Cles/API necessaires | Twilio SID + Auth Token + numero emetteur |
| 5 | Type | Action reelle sensible — SMS reel debitant le compte Twilio |
| 6 | Si ca marche | "SMS envoye a {name}" + log memoire |
| 7 | Si ca echoue | Quota atteint / contact introuvable / service non configure |
| 8 | Remonte cockpit ? | Oui partiellement — log memoire + quota SMS visible dans /api/admin/quotas. Mais pas d'alerte temps reel si un SMS echoue. |
| 9 | Correction minimale | Confirmation client deja ajoutee. Verifier que le dialog affiche le message complet avant envoi. |

### 2.2 Email

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Envoyer un email a un contact de confiance |
| 2 | Handler frontend | _concDirect("send_email", params, "Email", renderer) ~3324 ; MAJ 2026-05-26 : _showConfirm() ajoute avant envoi (commit cadfa43) |
| 3 | Action backend / tool | _tool_send_email() → Gmail OAuth (par tenant) ou SendGrid fallback |
| 4 | Cles/API necessaires | Gmail OAuth (par tenant) ou SENDGRID_API_KEY |
| 5 | Type | Action reelle sensible — email reel |
| 6 | Si ca marche | "Email envoye a {name}" + log memoire |
| 7 | Si ca echoue | "Aucun service email configure" / contact hors liste de confiance |
| 8 | Remonte cockpit ? | Oui partiellement — log memoire. Mais pas de metrique email dans le dashboard admin. |
| 9 | Correction minimale | Confirmation client deja ajoutee. Corriger le texte d'erreur technique. |

### 2.3 Appeler

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Passer un appel vocal via Luna a un contact |
| 2 | Handler frontend | _concStartVoice() → _showCallContactModal() ~3410 ; _confirmCallContact() → startVoiceCall() ~3484 |
| 3 | Action backend / tool | POST /api/voice-call → Twilio voice API |
| 4 | Cles/API necessaires | Twilio SID + Auth Token + VOICE_CALLBACK_URL |
| 5 | Type | Action reelle sensible — appel telephonique reel debitant Twilio |
| 6 | Si ca marche | "Luna appelle {name} ({minutes} min)…" |
| 7 | Si ca echoue | "Service d'appels vocaux non configure" / numero urgence bloque |
| 8 | Remonte cockpit ? | Oui — _remoteLog("info/error", "voice", ...) remonte au serveur. Mais pas d'alerte admin temps reel. |
| 9 | Correction minimale | Ajouter _showConfirm() avant startVoiceCall() dans _confirmCallContact(). Inclure nom, numero, duree. |

### 2.4 Visio Luna

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Lancer un appel video avec Luna |
| 2 | Handler frontend | _concStartVisio() → startCall() ~3413 ; startCall() → _showDurationPicker() → window.location.replace("/simli?duration=...") ~4602 |
| 3 | Action backend / tool | Aucun appel API direct — redirection vers /simli qui charge Tavus cote client. Le SMS d'invitation est envoye par Tavus cote serveur. |
| 4 | Cles/API necessaires | Tavus API Key + Twilio (pour SMS invitation) |
| 5 | Type | Action reelle sensible — SMS reel envoye au contact pour l'inviter |
| 6 | Si ca marche | Redirection vers /simli avec l'avatar Luna en visio |
| 7 | Si ca echoue | Pas de gestion d'erreur visible — redirection immediate |
| 8 | Remonte cockpit ? | Non — aucun log explicite cote client avant redirection. Le serveur Tavus logge mais le fondateur ne le voit pas. |
| 9 | Correction minimale | Ajouter _showConfirm() avant window.location.replace(). Message : "Luna va creer un appel video. Confirmer ?" |

### 2.5 Alerte urgence

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Prevenir ses contacts de confiance en cas d'urgence |
| 2 | Handler frontend | _concAlertUrgence() ~3417 ; _showConfirm("Alerte urgence", "Tous tes contacts...", ...) |
| 3 | Action backend / tool | _tool_alert_contacts() → Twilio SMS a tous les contacts de confiance |
| 4 | Cles/API necessaires | Twilio SID + Auth Token |
| 5 | Type | Action reelle sensible — SMS massif a tous les contacts |
| 6 | Si ca marche | "Alerte envoyee a {sent} contact(s)" |
| 7 | Si ca echoue | "Aucun contact de confiance enregistre" / "Service SMS non disponible" |
| 8 | Remonte cockpit ? | Oui — log memoire + safety event. Le dashboard admin compte alerts_today. |
| 9 | Correction minimale | Deja protege correctement. Aucune correction necessaire. |

---

## Section 3 — Organisation (5 services)

### 3.1 Rappel

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Creer un rappel pour plus tard |
| 2 | Handler frontend | _concDirect("add_reminder", {text, datetime}, "Rappel", renderer) |
| 3 | Action backend / tool | _tool_secretary_add_reminder() → Redis (SecretaryRedisOps) |
| 4 | Cles/API necessaires | Aucune externe — Redis interne |
| 5 | Type | Action interne — pas d'effet externe |
| 6 | Si ca marche | "Rappel cree pour {datetime}" |
| 7 | Si ca echoue | "Module secretaire non disponible" |
| 8 | Remonte cockpit ? | Non — erreur interne Redis, pas remontee au dashboard |
| 9 | Correction minimale | Aucune |

### 3.2 Note

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Prendre une note que Luna retient |
| 2 | Handler frontend | _concDirect("create_note", {title, content}, "Note", renderer) |
| 3 | Action backend / tool | _tool_create_note() → MemoryManager / Redis |
| 4 | Cles/API necessaires | Aucune externe |
| 5 | Type | Action interne |
| 6 | Si ca marche | "Note enregistree" |
| 7 | Si ca echoue | Erreur memoire |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 3.3 Document

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Generer un document (courrier, attestation…) |
| 2 | Handler frontend | _concDirect("generate_document", {type, recipient, subject}, "Document", renderer) |
| 3 | Action backend / tool | _tool_generate_document() → OpenAI GPT + generation PDF |
| 4 | Cles/API necessaires | OPENAI_API_KEY |
| 5 | Type | Preparation — generation locale, pas d'envoi automatique |
| 6 | Si ca marche | Document genere, telechargeable via lien |
| 7 | Si ca echoue | Erreur generation ou OpenAI non configure |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 3.4 Mes contacts

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Voir et gerer ses contacts de confiance |
| 2 | Handler frontend | _concDirect("get_contacts", {}, "Mes contacts", _renderContacts) ~3135 |
| 3 | Action backend / tool | _tool_get_contacts() → MemoryManager |
| 4 | Cles/API necessaires | Aucune externe |
| 5 | Type | Lecture seule — interne |
| 6 | Si ca marche | Liste des contacts avec nom, relation, telephone, adresse |
| 7 | Si ca echoue | "Aucun contact enregistre" |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 3.5 Formulaires

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Acceder aux formulaires CERFA/PDF |
| 2 | Handler frontend | Redirection directe window.location.href = "/formulaires" ~3140 |
| 3 | Action backend / tool | Aucune — page statique static/formulaires.html |
| 4 | Cles/API necessaires | Aucune |
| 5 | Type | Redirection — interne |
| 6 | Si ca marche | Page formulaires s'affiche |
| 7 | Si ca echoue | 404 si la page n'existe pas |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

---

## Section 4 — Mon Monde Luna (4 services)

### 4.1 Stats

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Voir son niveau, XP, etoiles, stabilite |
| 2 | Handler frontend | _concDirect("get_player_stats", {}, "Mes statistiques", _renderStats) ~3136 |
| 3 | Action backend / tool | _tool_get_player_stats() → GamificationRedisOps |
| 4 | Cles/API necessaires | Aucune externe — Redis interne |
| 5 | Type | Lecture seule — interne |
| 6 | Si ca marche | Carte avec niveau, titre, XP, progression, etoiles, stabilite |
| 7 | Si ca echoue | "Monde IA Watch non disponible" |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 4.2 Missions

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Voir ses missions actives et leur progression |
| 2 | Handler frontend | _concDirect("get_active_missions", {}, "Missions actives", _renderMissions) ~3137 |
| 3 | Action backend / tool | _tool_get_active_missions() → GamificationRedisOps |
| 4 | Cles/API necessaires | Aucune externe |
| 5 | Type | Lecture seule — interne |
| 6 | Si ca marche | Liste des missions avec titre, description, progression |
| 7 | Si ca echoue | "Aucune mission active pour le moment" |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 4.3 Badges

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Voir ses badges obtenus |
| 2 | Handler frontend | _concDirect("get_badges", {}, "Mes badges", _renderBadges) ~3138 |
| 3 | Action backend / tool | _tool_get_badges() → GamificationRedisOps |
| 4 | Cles/API necessaires | Aucune externe |
| 5 | Type | Lecture seule — interne |
| 6 | Si ca marche | Grille de badges avec icones et descriptions |
| 7 | Si ca echoue | "Aucun badge obtenu pour l'instant" |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

### 4.4 Amis en ligne

| # | Question | Reponse |
|---|---|---|
| 1 | Ce que l'utilisateur croit pouvoir faire | Voir qui de ses amis est connecte |
| 2 | Handler frontend | _concDirect("get_friends_online", {}, "Amis en ligne", _renderFriends) ~3139 |
| 3 | Action backend / tool | _tool_get_friends_online() → GamificationRedisOps / presence |
| 4 | Cles/API necessaires | Aucune externe |
| 5 | Type | Lecture seule — interne |
| 6 | Si ca marche | Liste des amis avec statut en ligne/hors ligne |
| 7 | Si ca echoue | "Aucun ami enregistre" |
| 8 | Remonte cockpit ? | Non |
| 9 | Correction minimale | Aucune |

---

## Synthese des remontees cockpit (point 8)

### Ce qui remonte AUJOURD'HUI

| Source | Ou | Quoi |
|---|---|---|
| Dashboard admin | /api/admin/dashboard | Statut services (OpenAI, Twilio, Tavus, Redis) |
| Dashboard admin | /api/admin/dashboard | Nombre d'alertes safety aujourd'hui |
| Dashboard admin | /api/admin/quotas | Quotas SMS/email par tenant |
| Dashboard admin | /api/admin/costs | Couts/consommation |
| Logs client | _remoteLog → /api/logs/client | Erreurs JS, appels voice, clics concierge |
| Memoire | mgr.log_event | SMS envoyes, appels, alertes (dans Redis) |

### Ce qui NE remonte PAS

| Manque | Impact |
|---|---|
| Erreur concierge specifique | Si une recherche vol echoue, le fondateur ne le voit pas dans le dashboard |
| Serper dans le dashboard | Le dashboard ne verifie pas si Serper est configure |
| Alerte temps reel SMS/email echoue | Le fondateur n'est pas notifie si un SMS n'arrive pas |
| Metrique reservations Duffel | Aucun compteur de recherches/reservations dans le dashboard |
| Erreur Twilio voice | Les echecs d'appel sont loggues mais pas agreges pour le fondateur |

---

## Synthese des corrections minimales prioritaires

| Priorite | Service | Correction | Fichier |
|---|---|---|---|
| P0 | Appeler | Ajouter _showConfirm() | static/index.html |
| P0 | Visio Luna | Ajouter _showConfirm() | static/index.html |
| P1 | Recherche web/lieux | Ajouter serper dans dashboard admin | luna_web.py |
| P1 | Restaurants | Renommer carte + avertissement | static/index.html |
| P1 | Texte erreur email | Corriger message utilisateur | luna_web.py |
| P1 | Texte erreur appel | Corriger "souscripteur" | luna_web.py |
| P2 | Cockpit | Ajouter metriques concierge | luna_web.py + fondateur.html |

---

*Document produit par Kimi Code CLI — 2026-05-27*
*Complete KIMI_AVIS_011.md (UX humain, 412 lignes) avec les 9 points techniques demandes.*
