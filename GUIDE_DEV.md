# Guide Développeur — Luna IA (YAWatch)
> Carte complète du code. Pour chaque modification : fichier exact, ligne exacte, quoi changer.  
> Repo source : `byakuyakutchiki/luna-server`

---

## SOMMAIRE

1. [Architecture générale](#1-architecture-générale)
2. [Fichier central : luna_web.py](#2-fichier-central--luna_webpy)
3. [Voix de Luna](#3-voix-de-luna)
4. [Personnalité et comportement](#4-personnalité-et-comportement)
5. [Couleurs et interface](#5-couleurs-et-interface)
6. [Page Visio — simli.html](#6-page-visio--simlihtml)
7. [Cinématique d'intro](#7-cinématique-dintro)
8. [Page Chat — index.html](#8-page-chat--indexhtml)
9. [Outils / Conciergerie](#9-outils--conciergerie)
10. [SMS et appels Twilio](#10-sms-et-appels-twilio)
11. [Prise de notes et mémoire](#11-prise-de-notes-et-mémoire)
12. [Vision caméra](#12-vision-caméra)
13. [Sécurité Cortex](#13-sécurité-cortex)
14. [Plans, quotas et paiements Stripe](#14-plans-quotas-et-paiements-stripe)
15. [PV de recette et verrouillage](#15-pv-de-recette-et-verrouillage)
16. [Dashboard Admin](#16-dashboard-admin)
17. [Service Worker et cache PWA](#17-service-worker-et-cache-pwa)
18. [Variables d'environnement — liste complète](#18-variables-denvironnement--liste-complète)
19. [Toutes les routes API](#19-toutes-les-routes-api)
20. [Modules core/](#20-modules-core)
21. [Déploiement Cloud Run](#21-déploiement-cloud-run)
22. [Passer en anglais](#22-passer-en-anglais)
23. [Intégration Zoom](#23-intégration-zoom)

---

## 1. Architecture générale

### Repos GitHub (tous privés)

| Repo | Contenu | Dossier local |
|---|---|---|
| `byakuyakutchiki/luna-server` | **Tout le code applicatif** | `PROPRIO/serveur/` |
| `byakuyakutchiki/luna-proprio` | Contrats, CGU, archives juridiques | `PROPRIO/` |
| `byakuyakutchiki/luna-exploitants` | Package installable opérateurs | `EXPLOITANTS/` |
| `byakuyakutchiki/luna-docs` | Business plan, études marché | `DOCS/` |

### Arborescence complète du repo `luna-server`

```
luna-server/
│
├── luna_web.py                   ← Serveur FastAPI (~12 500 lignes) — tout tient ici
├── .env                          ← Clés API + config (JAMAIS committer)
├── Dockerfile                    ← Image Docker pour Cloud Run
├── docker-compose.yml            ← Dev local avec Redis
├── requirements.txt              ← Dépendances Python
├── GUIDE_DEV.md                  ← Ce fichier
├── GUIDE_OPERATIONNEL.md         ← Guide pour non-codeurs
│
├── static/                       ← Fichiers servis directement au navigateur
│   ├── index.html                ← Interface chat (page principale, ~5000 lignes)
│   ├── simli.html                ← Page visio Tavus + cinématique (~1850 lignes)
│   ├── admin.html                ← Dashboard admin
│   ├── admin_world.html          ← Dashboard world (features premium)
│   ├── setup.html                ← Wizard d'installation (exploitants)
│   ├── formulaires.html          ← Formulaires client
│   ├── salon.html                ← Salle de réunion multi-utilisateurs
│   ├── world.html                ← Interface "monde Luna"
│   ├── download.html             ← Page téléchargement APK
│   ├── sw.js                     ← Service Worker PWA (cache + notifications push)
│   ├── manifest.json             ← Config PWA (icône, nom, thème)
│   └── assets/
│       ├── backgrounds/*.svg     ← 9 décors SVG cinématiques (selon l'heure)
│       └── sounds/*.mp3          ← Sons ambient + téléphone (10 fichiers)
│
├── core/                         ← Modules métier internes
│   ├── actions/
│   │   ├── quota_guard.py        ← Vérification quotas par plan
│   │   └── executor.py           ← Exécution des actions planifiées
│   ├── cortex/
│   │   ├── brain.py              ← IA décisionnelle Cortex (boucle 30s)
│   │   ├── vigil.py              ← Détection menaces + ban IPs
│   │   ├── integration.py        ← Routes API /api/cortex/*
│   │   ├── signals.py            ← Types de signaux de sécurité
│   │   ├── emergency.py          ← Mode urgence (commandes SMS)
│   │   └── telegram_bot.py       ← Bot Telegram fondateur
│   ├── documents/
│   │   └── generator.py          ← Génération DOCX (comptes-rendus, contrats)
│   ├── memory/
│   │   ├── memory_manager.py     ← Gestionnaire mémoire long-terme
│   │   ├── redis_client.py       ← Client Redis (toutes les données persistées)
│   │   ├── schemas.py            ← Types de données (Conversation, Note, Contact…)
│   │   └── key_schema.md         ← Schéma des clés Redis
│   ├── notifications/            ← Moteur de notifications push
│   ├── perception/
│   │   ├── analyzer.py           ← Analyse GPT-4o vision (scène, posture)
│   │   └── detector.py           ← Détecteur d'anomalies (chutes, détresse)
│   ├── safety/                   ← Détection détresse + escalade famille
│   ├── secretary/                ← Module secrétariat (budget, agenda, dossiers)
│   ├── rooms/                    ← Salles de réunion multi-utilisateurs
│   ├── social/                   ← Réseau famille (groupe, messages, SOS)
│   ├── gamification/             ← Badges, missions, stats joueur
│   ├── instructions/             ← Instructions planifiées (créées par Luna)
│   ├── form_filler/              ← Remplissage automatique de formulaires
│   ├── license/                  ← Gestion licence exploitant
│   └── testing/                  ← Scénarios de test automatisés
│
└── integrations/
    ├── tavus/
    │   └── tavus_client.py       ← Client Tavus API (avatar visio) + prompt Luna
    ├── twilio/                   ← SMS et appels vocaux
    └── simli/                    ← Module Simli (non actif — remplacé par Tavus)
```

---

## 2. Fichier central : luna_web.py

Le fichier `luna_web.py` est le serveur FastAPI complet. Voici sa structure interne :

| Lignes | Zone |
|---|---|
| 1–155 | Imports, flags disponibilité modules, constantes globales |
| 155–480 | Initialisation : LUNA_MODE, auth, PV de recette, Tavus, OpenAI, Twilio… |
| 480–660 | Bootstrap : MemoryManager, QuotaGuard, Cortex, Perception… |
| 660–790 | Helpers auth : JWT, tokens clients, tokens admin |
| 787–1085 | **`LUNA_SYSTEM_PROMPT`** — le prompt principal de Luna |
| 1085–1350 | Rate limiting + Security middleware |
| 1350–1500 | Middleware d'auth (JWT client + admin) |
| 1500–1800 | Routes statiques : `/`, `/simli`, `/admin`, `/health`… |
| 1800–3175 | **`/api/chat`** — endpoint principal du chat (streaming) |
| 3175–3350 | Contexte temps réel (`_build_realtime_context`) |
| 3350–3670 | **`/api/call`** — démarrage visio Tavus |
| 3670–3895 | Visio : perception, notes, upload |
| 3895–4100 | Endpoints utilitaires (cache, config, profil) |
| 4098–4550 | **Appels vocaux Twilio** (TwiML, conférence) |
| 4550–5140 | Webhooks : Twilio voice entrant |
| 5140–5450 | **Webhooks SMS** entrants/sortants |
| 5450–5650 | Conversations, historique, statut |
| 5647–5940 | **Auth** : register, login, checkout Stripe |
| 5940–6250 | **Webhooks Stripe** + paiements |
| 6250–6820 | **Setup wizard** — 10 étapes exploitant |
| 6820–7150 | Profil, settings, géolocalisation |
| 7150–7900 | **Module famille** (groupe, membres, SOS, escalade) |
| 7900–8300 | Notes, instructions, contacts, documents |
| 8300–8900 | **Dashboard admin** : clients, quotas, revenus, alertes |
| 8900–9200 | **Webhook Tavus** + dispatcher outils |
| 9200–11400 | **Toutes les fonctions `_tool_*`** |
| 11400–12000 | Secrétariat, gamification, notifications |
| 12000–12500 | Démarrage serveur (uvicorn) |

---

## 3. Voix de Luna

Luna utilise **deux moteurs vocaux distincts** selon le contexte.

### Voix en mode Chat / Vocal (OpenAI TTS)

**Fichier :** `luna_web.py` — ligne ~4858  
**Contrôle :** variable d'env `OPENAI_VOICE_NAME`

```python
voice=os.getenv("OPENAI_VOICE_NAME", "alloy"),
```

**Voix OpenAI disponibles :**

| Voix | Caractère |
|---|---|
| `alloy` | Neutre, polyvalent (défaut) |
| `echo` | Masculin, profond |
| `fable` | Expressif, narratif |
| `onyx` | Masculin, chaleureux |
| `nova` | Féminin, énergique |
| `shimmer` | Féminin, doux |
| `coral` | Féminin, naturel (recommandé pour Luna FR) |

**Modifier :** `.env` → `OPENAI_VOICE_NAME=coral`

---

### Voix en mode Visio (Cartesia via Simli/Tavus)

**Fichier :** `luna_web.py` — ligne ~3261  
**Contrôle :** variable d'env `SIMLI_VOICE_ID`

```python
voice_id = os.getenv("SIMLI_VOICE_ID",
    "f9836c6e-a0bd-460e-9d3c-f7299fa60f94")  # Cartesia "Helpful Woman" multilingual
```

Pour changer : trouver un `voice_id` sur [play.cartesia.ai](https://play.cartesia.ai) → `.env` → `SIMLI_VOICE_ID=<id>`

---

### Modèle IA (intelligence du chat)

**Contrôle :** `.env` → `OPENAI_MODEL`

| Valeur | Usage |
|---|---|
| `gpt-4o-mini` | Défaut — rapide, économique (~0.001€/msg) |
| `gpt-4o` | Plus intelligent, plus lent, plus cher |

---

### STT (transcription parole → texte) en visio

**Fichier :** `static/simli.html` — ligne ~1661  
Utilise l'API `SpeechRecognition` du navigateur (gratuit, intégré Chrome/Edge).  
Langue : `_speechReco.lang = 'fr-FR';`

---

## 4. Personnalité et comportement

### Prompt principal (mode chat)

**Fichier :** `luna_web.py` — ligne **787** — constante `LUNA_SYSTEM_PROMPT`

Contient (dans l'ordre) :
- Identité de Luna ("Tu es Luna…")
- Règles de communication (tutoie, chaleur, concision)
- Liste des 30+ capacités déclarées
- Règles de sécurité (pas de médecin, confidentialité)
- Gestion des appels planifiés
- Instructions outils (quand utiliser quel tool)

**Durée :** ~200 lignes. Toute modification ici change le comportement global de Luna en chat.

---

### Prompt mode Visio (Tavus)

**Fichier :** `integrations/tavus/tavus_client.py` — fonction `build_tavus_context()` ligne **48**

Contient (dans l'ordre) :
- **Ligne 89** : identité et ton de Luna en visio
- **Ligne ~110** : liste des outils disponibles en visio
- **Ligne ~150** : mode réunion d'entreprise
- **Ligne ~170** : règles de discrétion multi-participants
- **Ligne 184** : prompt court de fallback

---

### Contexte temps réel (météo + actualités)

**Fichier :** `luna_web.py` — fonction `_build_realtime_context()` ligne **3178**

Appelée à chaque démarrage de visio et injectée dans le prompt système.  
Sources actuelles :
- Météo : wttr.in (gratuit, pas de clé)
- Actualités : RSS Le Monde (gratuit)
- Date/heure : système

Pour changer les sources, modifier cette fonction.

---

### Règle anti-hallucination

**Fichier :** `luna_web.py` — chercher `RÈGLE ANTI-HALLUCINATION`

Ce texte est injecté en visio pour interdire à Luna d'inventer des faits. Si Luna hallucine, vérifier que ce bloc est présent dans `_start_simli_visio()`.

---

## 5. Couleurs et interface

### Couleurs du chat (index.html)

**Fichier :** `static/index.html` — lignes **14–70** (bloc `<style>`)

| Élément | CSS | Valeur actuelle |
|---|---|---|
| Fond global | `body { background: … }` | `#0a0a1a` (noir bleuté) |
| Header | `.header { background: linear-gradient(…) }` | `#1a1a3e → #2d1b69` (violet) |
| Barre onglets | `.tabs { background: … }` | `#0d0d1f` |
| Bulle Luna | `.luna { background: … }` | fond sombre avec dégradé bleu |
| Bulle utilisateur | `.user { background: … }` | bleu/violet |
| Texte principal | `color: #e0e0e0` | gris clair |

**Mode Secrétaire** (palette verte) : lignes **53–70** — préfixe `body.mode-secretaire`

---

### Couleurs de la visio (simli.html)

**Fichier :** `static/simli.html` — lignes **10–390**

| Élément | Classe CSS | Couleur actuelle |
|---|---|---|
| Fond général | `html, body` | `#000` (noir pur) |
| Barre actions (haut) | `#visioActionsBar` | dégradé noir → transparent |
| Bouton muet (actif) | `#btnMuteLuna` | `#7cf8c8` (vert menthe) |
| Bouton muet (désactivé) | `#btnMuteLuna.muted` | `#f87c7c` (rouge) |
| Bouton upload | `#btnUpload` | `#f8b07c` (orange) |
| Bouton inviter | `#btnInvite` | `#a78bfa` (violet) |
| Bouton partager | `#btnShare` | `#7cf8c8` (vert) |
| Bouton notes | `#btnNotes` | `#f8d07c` (jaune) |
| Bouton raccrocher | `.btn-hangup` | `#e94560` (rouge vif) |
| Toasts | `#lunaToast` | fond sombre, bordure violette |
| Indicateur vision | `#visionStatus` | vert menthe |

---

### Icône et nom PWA

**Fichier :** `static/manifest.json`  
Champs à modifier : `"name"`, `"short_name"`, `"theme_color"`, `"background_color"`  
Icônes à remplacer : `static/assets/luna-icon-192.png` et `luna-icon-512.png`

---

## 6. Page Visio — simli.html

Fichier unique : `static/simli.html` (~1870 lignes après modifications)

### Plan du fichier

| Lignes | Contenu |
|---|---|
| 1–390 | **CSS complet** — tout le style, toutes les animations |
| 390–530 | **HTML** — structure DOM (écran démarrage, modals, barre actions, boutons) |
| 530–600 | Logging distant (`rLog` → `/api/debug/log`) |
| 552–600 | **Planning horaire** — 9 scènes selon l'heure du jour |
| 600–660 | Variables globales JavaScript |
| 660–715 | Utilitaires : `wait()`, `showToast()`, labels outils |
| 715–815 | Grain cinématique (canvas animé) |
| 815–1050 | **Cinématique 5 actes** : establishing shot, vibration, sonnerie, décrochage, zoom |
| 1050–1100 | `createSimliCall()` — fallback Simli si Tavus indisponible |
| 1100–1165 | `createVisioCall()` — appel Tavus principal |
| 1088–1145 | Météo badge + filtres météo sur décor |
| 1145–1230 | Auto-démarrage si `?duration=X` dans l'URL |
| 1165–1230 | Bouton Démarrer + orchestration cinématique |
| 1230–1315 | **Upload document/image** (`_handleUpload`, `/api/visio/upload`) |
| 1312–1345 | **Bouton Muet Luna** (soft-mute via `conversation.echo`) |
| 1345–1425 | **Modal Inviter** un contact |
| 1425–1500 | **Modal Partager** le lien de visio |
| 1497–1660 | **Vision caméra** — capture frame + `/api/visio/perception` toutes les 12s |
| 1655–1700 | **SpeechRecognition** — capture parole utilisateur pour notes |
| 1700–1795 | **Notes** — génération + sauvegarde via `/api/visio/notes` |
| 1793–1845 | **Hangup** + auto-save notes silencieux |

### Ajouter un bouton dans la barre d'actions

```html
<!-- HTML (ligne ~470) -->
<button class="vab-btn" id="btnNouvelleAction">🆕 Label</button>

<!-- CSS (après ligne ~232) -->
#btnNouvelleAction { color: #fff; border-color: rgba(255,255,255,0.3); }
#btnNouvelleAction:hover { background: rgba(255,255,255,0.1); }

<!-- JS (en bas du script, avant </script>) -->
var btnNouvelleAction = document.getElementById('btnNouvelleAction');
if (btnNouvelleAction) btnNouvelleAction.onclick = function() {
  if (!dailyCall) return;
  // votre logique ici
};
```

### Injecter du texte dans la conversation Luna (depuis JS)

```javascript
dailyCall.sendAppMessage({
  message_type: 'conversation',
  event_type: 'conversation.echo',
  conversation_id: currentConvId,
  properties: { modality: 'text', text: 'Votre message ici' }
}, '*');
```

---

## 7. Cinématique d'intro

### Les 9 scènes horaires

**Fichier :** `static/simli.html` — lignes **552–590**

| Heure | Scène | Fichier SVG | Son |
|---|---|---|---|
| 6h–8h | Chambre (réveil) | `bg_bedroom.svg` | `ambient_morning.mp3` |
| 8h–10h | Cuisine (petit-déj) | `bg_kitchen_morning.svg` | `ambient_kitchen.mp3` |
| 10h–12h | Salon (lecture) | `bg_livingroom_day.svg` | `ambient_calm.mp3` |
| 12h–14h | Cuisine (déjeuner) | `bg_kitchen_lunch.svg` | `ambient_cooking.mp3` |
| 14h–16h | Parc | `bg_park.svg` | `ambient_nature.mp3` |
| 16h–18h | Atelier (peinture) | `bg_workshop.svg` | `ambient_creative.mp3` |
| 18h–20h | Cuisine (dîner) | `bg_kitchen_dinner.svg` | `ambient_cooking.mp3` |
| 20h–22h | Salon (soirée) | `bg_livingroom_evening.svg` | `ambient_cozy.mp3` |
| 22h–6h | Nuit | `bg_night.svg` | `ambient_night.mp3` |

### Modifier la durée de la cinématique

| Phase | Fonction | Ligne | `wait(ms)` à modifier |
|---|---|---|---|
| Plan d'ensemble | `actEstablishingShot` | ~810 | `wait(600)`, `wait(2000)`, `wait(500)` |
| Vibration téléphone | `actPhoneVibrate` | ~810 | `wait(2500)`, `wait(800)` |
| Sonnerie | `actPhoneRing` | ~827 | `wait(3500)` |
| Décrochage | `actPhoneAnswer` | ~837 | `wait(300)`, `wait(2500)` |
| Zoom vers Tavus | `actCinematicZoom` | ~853 | `wait(2500)`, `wait(800)` |

### Ajouter un décor

1. Créer le SVG (format 16:9) et le mettre dans `static/assets/backgrounds/`
2. Créer le MP3 ambient et le mettre dans `static/assets/sounds/`
3. Ajouter une entrée dans `LUNA_SCHEDULE` (ligne ~552)

---

## 8. Page Chat — index.html

**Fichier :** `static/index.html` (~5000 lignes)

### Zones principales

| Zone | Sélecteur CSS | Description |
|---|---|---|
| Header | `.header` | Logo, nom Luna, onglets de navigation |
| Zone chat | `.chat-area` | Historique de la conversation |
| Input | `.input-area` | Champ texte + boutons micro/visio/menu |
| Sidebar conversations | `.conv-sidebar` | Historique multi-conversations |
| Onglet Secrétaire | `#tab-secretaire` | Budget, dépenses, agenda |
| Onglet Contacts | `#tab-contacts` | Carnet d'adresses Luna |
| Onglet Profil | `#tab-profil` | Abonnement, plan, quotas utilisés |

### Bouton démarrer la visio

Chercher `startCall()` ou `href.*simli` dans `index.html`.  
Ce bouton redirige vers `/simli?duration=X`.

### Modifier les bulles de message

- Bulle Luna : chercher `.luna` dans les styles de `index.html`
- Bulle utilisateur : chercher `.user`

---

## 9. Outils / Conciergerie

### Définition des outils disponibles en visio

**Fichier :** `luna_web.py` — variable `_SIMLI_TOOLS`  
Chercher `_SIMLI_TOOLS` dans le fichier (liste de dicts JSON, format OpenAI function-calling).

---

### Toutes les fonctions outil (`_tool_*`)

| Outil | Fonction Python | Ligne approx. | Description |
|---|---|---|---|
| Envoyer SMS | `_tool_send_sms` | 9199 | Twilio SMS vers contact |
| Envoyer email | `_tool_send_email` | 9276 | Email via SMTP/API |
| Inviter en visio | `_tool_invite_visio` | 9357 | SMS avec lien Daily.co |
| Envoyer conclusions | `_tool_send_conclusions` | 9502 | DOCX + SMS à tous les participants |
| Appeler un contact | `_tool_call_contact` | 9626 | Appel Twilio sortant |
| Créer instruction | `_tool_create_instruction` | 9776 | Action planifiée future |
| Rejoindre conférence | `_tool_join_conference` | 9857 | Rejoindre une salle de réunion |
| Créer note | `_tool_create_note` | 9906 | Sauvegarde en mémoire |
| Récupérer contacts | `_tool_get_contacts` | 9931 | Liste carnet d'adresses |
| Générer document | `_tool_generate_document` | 9946 | Création DOCX |
| Alerter contacts | `_tool_alert_contacts` | 10037 | SMS d'alerte à tous les contacts de confiance |
| Signaler observation | `_tool_report_observation` | 10087 | Observation caméra |
| Stats joueur | `_tool_get_player_stats` | 10116 | Gamification |
| Missions actives | `_tool_get_active_missions` | 10152 | Gamification |
| Badges | `_tool_get_badges` | 10183 | Gamification |
| Météo | `_tool_get_weather` | 10215 | wttr.in ou OpenWeather |
| Actualités | `_tool_get_news` | 10355 | RSS configurable |
| Recherche web | `_tool_search_web` | 10442 | Serper API |
| Chercher lieux | `_tool_search_places` | 10580 | Places API |
| Info page web | `_tool_get_page_info` | 10734 | Scraping URL |
| Demander paiement | `_tool_request_payment` | 10838 | Stripe PaymentIntent |
| Chercher vols | `_tool_search_flights` | 11042 | Duffel API (si configuré) |
| Chercher hôtels | `_tool_search_hotels` | 11095 | Duffel API |
| Réserver restaurant | `_tool_book_restaurant` | 11143 | Recherche restaurants |
| Budget secrétariat | `_tool_secretary_summary` | 11198 | Résumé budget du mois |
| Bilan budgetaire | `_tool_secretary_budget` | 11207 | Dépenses vs revenus |
| Peut-on se permettre | `_tool_secretary_afford` | 11217 | Analyse achats |
| Ajouter dépense | `_tool_secretary_add_expense` | 11248 | Enregistrement dépense |
| Rappels | `_tool_secretary_reminders` | ~11280 | Liste des rappels |
| Ajouter rappel | `_tool_secretary_add_reminder` | ~11300 | Nouveau rappel |
| Recherche docs | `_tool_secretary_search` | ~11320 | Recherche en mémoire |
| Dossiers | `_tool_secretary_folders` | ~11340 | Gestion dossiers |

### Dispatcher des tool calls (visio)

**Fichier :** `luna_web.py` — fonction `_handle_tavus_tool_call()` ligne **9035**

C'est le routeur qui reçoit les appels d'outils de Tavus et appelle la bonne fonction `_tool_*`.  
Pour ajouter un nouvel outil : ajouter la définition dans `_SIMLI_TOOLS`, le dispatcher dans `_handle_tavus_tool_call`, et créer la fonction `_tool_*` correspondante.

---

## 10. SMS et appels Twilio

### Configuration

Variables `.env` requises :
- `TWILIO_ACCOUNT_SID` — identifiant du compte Twilio
- `TWILIO_AUTH_TOKEN` — token secret Twilio
- `TWILIO_PHONE_NUMBER` — numéro sortant (format E.164 : +17173409138)

### Envoyer un SMS (code Python)

**Fonction :** `_tool_send_sms()` ligne **9199**  
Utilise `twilio.rest.Client` avec les vars d'env ci-dessus.

### Webhooks Twilio configurés

| Webhook | Route | Ligne | Usage |
|---|---|---|---|
| SMS entrant | `POST /api/webhook/sms` | 5232 | Luna répond aux SMS reçus |
| Statut SMS | `POST /api/webhook/sms-status` | 5352 | Suivi livraison SMS |
| Appel entrant | `POST /api/webhook/voice-incoming` | 5140 | Gestion appels entrants |
| TwiML appel sortant | `POST /api/voice-call/twiml` | 4130 | Script vocal Twilio |
| Conférence TwiML | `POST /api/voice-call/conference-twiml` | 4177 | Salle de conférence |

### Configurer les webhooks Twilio automatiquement

**Fonction :** `_configure_twilio_webhooks()` — appelée au démarrage.  
Configure automatiquement les webhooks sur le compte Twilio en utilisant `BASE_URL` + les routes ci-dessus.

---

## 11. Prise de notes et mémoire

### Notes de visio (frontend → backend)

**Frontend :** `static/simli.html` — `_openNotesModal()` ligne ~1709  
**Backend :** `POST /api/visio/notes` ligne **3771**  
**Sauvegarde :** `POST /api/visio/notes/save` ligne **3856**  
**Auto-save :** dans `doHangup()` si durée ≥ 1 min et transcript non vide

Le transcript envoyé au backend contient :
- `user.speech` — paroles captées via SpeechRecognition
- `luna.speech` — réponses de Luna si Tavus envoie des utterances
- `conversation.tool_call` — outils appelés par Luna
- `tool_result` — résultats des outils
- `participant.joined/left` — entrées/sorties de participants
- `vision.change` — changements de scène significatifs
- `upload.analysis` — analyses de documents partagés

### Mémoire long-terme (MemoryManager)

**Fichier :** `core/memory/memory_manager.py`  
**Backend Redis :** `core/memory/redis_client.py` — URL : `redis://localhost:6379/0`

Méthodes principales :

| Méthode | Usage |
|---|---|
| `add_note(content, context, tags)` | Ajouter une note en mémoire |
| `list_notes(limit, context)` | Lister les notes |
| `add_instruction(...)` | Créer une instruction planifiée |
| `list_active_instructions()` | Instructions en attente |
| `add_trusted_contact(...)` | Ajouter contact de confiance |
| `set_subscriber_profile(profile)` | Sauvegarder profil abonné |
| `get_subscriber_profile()` | Récupérer profil abonné |
| `add_message(...)` | Ajouter message à une conversation |
| `get_recent_context(conv_id)` | Contexte récent pour Luna |

---

## 12. Vision caméra

### Pipeline complet

1. **Capture (JS)** : `static/simli.html` — `_captureAndSend()` ligne ~1563
   - Capture une frame JPEG 320×240 depuis la caméra locale toutes les **12 secondes**
   - Envoie en base64 à `/api/visio/perception`

2. **Analyse (backend)** : `luna_web.py` — `POST /api/visio/perception` ligne **3669**
   - Appelle `_perception_analyzer.analyze_frame(image_data)`
   - Retourne : `description`, `changed`, `objects`, `posture`, `persons`

3. **Notification Luna (JS)** : si première frame → injecte via `conversation.echo` :
   > "Ta caméra est maintenant active. Description initiale : [desc]. Utilise get_vision_context si on te demande ce que tu vois."

4. **Outil `get_vision_context`** : quand Luna appelle cet outil → backend retourne le cache de la dernière analyse

### Anti-spam

**Rate limit vision :** `luna_web.py` ligne ~3681 → 429 si < 5 secondes entre deux frames

---

## 13. Sécurité Cortex

### Architecture

```
cortex/
├── brain.py      ← Boucle 30s : collecte signaux, analyse GPT, décide actions
├── vigil.py      ← Détection : analyse requêtes, calcul score menace, ban IPs
├── integration.py ← Routes API /api/cortex/* (admin uniquement)
├── signals.py    ← Types : HONEYPOT_HIT, BRUTE_FORCE, SCAN, SQL_INJECT…
└── emergency.py  ← Commandes SMS urgence (lockdown, shield, unban)
```

### Honeypot — chemins qui déclenchent le ban immédiat

**Fichier :** `core/cortex/vigil.py` — lignes ~122–130

Toute requête vers ces chemins → ban automatique :
- `/wp-admin`, `/wp-login`, `/phpmyadmin`
- `/.env`, `/.git`, `/.aws`, `/.docker`
- Et une dizaine d'autres

### Modes Cortex

| Mode | Effet | Activation |
|---|---|---|
| `normal` | Surveillance standard, ban si score > seuil | Par défaut |
| `shield` | Seules les IPs whitelist passent | SMS admin ou `/api/cortex/shield` |
| `lockdown` | Tout bloqué sauf `/health` | Urgence critique |
| `maintenance` | Seul `/api/admin` et `/api/cortex` passent | Maintenance planifiée |

### Protection fondateur — IPs permanentes

**Fichiers :** `core/cortex/brain.py` ET `core/cortex/vigil.py`

```python
_FOUNDER_IP_PREFIXES: tuple = (
    "2a02:8429:a9e4:f101:",  # Plage /64 de la box du fondateur (couvre les rotations IPv6)
)
_FOUNDER_IPS: frozenset = frozenset({
    "92.92.129.172",  # IPv4 fixe fondateur
})
```

Ces IPs bypass TOUT : lockdown, shield, ban, whitelist vide. Elles ne peuvent jamais être bannies.

### API de gestion Cortex

Toutes nécessitent `Authorization: Bearer <admin_jwt>`.

| Endpoint | Méthode | Action |
|---|---|---|
| `/api/cortex/status` | GET | État du Cortex (public, sans auth) |
| `/api/cortex/threats` | GET | Rapport menaces 24h + IPs bannies |
| `/api/cortex/ban/{ip}` | POST | Bannir une IP |
| `/api/cortex/ban/{ip}` | DELETE | Débannir une IP |
| `/api/cortex/whitelist/{ip}` | POST | Whitelister + débannir |
| `/api/cortex/whitelist/{ip}` | DELETE | Retirer de la whitelist |
| `/api/cortex/shield` | POST | Activer mode bouclier |
| `/api/cortex/lockdown` | POST | Activer lockdown |
| `/api/cortex/normalize` | POST | Retour au mode normal |

---

## 14. Plans, quotas et paiements Stripe

### Plans abonnements

**Fichier :** `core/actions/quota_guard.py` — lignes 38–59

| Plan | Prix | Chat | Voix | Visio | SMS | Budget API max |
|---|---|---|---|---|---|---|
| Essentiel | 79€/mois | Illimité | 40 min | 12 min | 25 | 8,15€ |
| Confort | 149€/mois | Illimité | 100 min | 28 min | 50 | 17,40€ |
| Premium | 249€/mois | Illimité | 180 min | 55 min | 100 | 32,10€ |
| Fondateur | — | ∞ | ∞ | ∞ | ∞ | — |

### Stripe — configuration

Variables `.env` :
- `STRIPE_API_KEY` ou `STRIPE_SECRET_KEY` — clé secrète Stripe (`sk_live_…`)
- `STRIPE_WEBHOOK_SECRET` — secret du webhook Stripe (`whsec_…`)
- `STRIPE_PRICE_ESSENTIEL` — ID du prix Stripe (`price_…`)
- `STRIPE_PRICE_CONFORT` — ID du prix Stripe
- `STRIPE_PRICE_PREMIUM` — ID du prix Stripe

### Créer les produits Stripe automatiquement

**Script :** `stripe_setup.py` (dans `EXPLOITANTS/`)  
Idempotent — cherche les produits existants avant de créer.

### Routes Stripe

| Route | Méthode | Ligne | Usage |
|---|---|---|---|
| `/api/auth/checkout` | POST | 5787 | Démarrage paiement (Stripe Checkout) |
| `/api/stripe/webhook` | POST | 5931 | Webhook Stripe (paiement confirmé, abonnement) |
| `/api/payment/confirm/{intent_id}` | POST | 6115 | Confirmer un paiement |
| `/api/payment/pending` | GET | 6184 | Paiements en attente |
| `/api/auth/setup-card` | POST | ~5860 | Enregistrer une carte bancaire |

---

## 15. PV de recette et verrouillage

### Concept

Le PV de recette est un système de verrouillage du serveur en 3 phases :
- **Phase A** : Vérifications techniques automatiques
- **Phase B** : Déclarations légales de l'exploitant
- **Phase C** : Vérifications opérationnelles

Avant signature → serveur en mode SETUP (affiche `setup.html`).  
Après signature → serveur verrouillé en mode exploitation, setup impossible.

### Fichiers clés

| Fichier | Rôle |
|---|---|
| `pv_lock.json` | Résultat signé du PV (HMAC, prioritaire sur `.env`) |
| `luna_web.py` ligne 181 | Vérification au démarrage |
| `luna_web.py` ligne 1396 | Middleware : si non signé → 503 sur toutes les routes sauf setup |
| `/api/setup/sign-pv` | Route qui crée `pv_lock.json` |
| `EXPLOITANTS/pv_recette.py` | Script de recette pour l'exploitant |
| `EXPLOITANTS/tools/factory_reset.py` | Reset usine (nécessite RESET_CODE) |

### Cycle de vie

```
Installation → setup.html (wizard 10 étapes) → PV signé → pv_lock.json créé
→ Serveur verrouillé → setup.html inaccessible → exploitation normale
→ (si besoin) factory_reset.py --code <RESET_CODE> → retour état initial
```

### Variables PV

- `PV_SIGNED` — dans `.env` : `"true"` ou `"false"` (contournable — ignoré si `pv_lock.json` présent)
- `pv_lock.json` — HMAC signé avec `JWT_SECRET_KEY`, prioritaire sur `.env`

---

## 16. Dashboard Admin

**URL :** `/admin`  
**Fichier HTML :** `static/admin.html`  
**Auth :** JWT admin (email `PROPRIO_EMAIL` + password `PROPRIO_PASSWORD`)

### Routes admin backend

| Route | Méthode | Ligne | Contenu |
|---|---|---|---|
| `/api/admin/login` | POST | ~8700 | Connexion admin |
| `/api/admin/dashboard` | GET | ~8720 | Vue globale |
| `/api/admin/clients` | GET | ~8750 | Liste de tous les abonnés |
| `/api/admin/clients/{id}` | GET/PUT/DELETE | ~8800 | Détail abonné |
| `/api/admin/quotas` | GET | ~8748 | Quotas utilisés par abonné |
| `/api/admin/revenue` | GET | ~8800 | CA du mois |
| `/api/admin/costs` | GET | ~8820 | Coûts API du mois |
| `/api/admin/alerts` | GET | ~8840 | Alertes actives |
| `/api/admin/commissions` | GET | ~8860 | Commissions Ambre |
| `/api/admin/certificate` | GET | ~8880 | Certificat d'autonomie DOCX |
| `/api/admin/health` | GET | ~8900 | Santé du serveur |
| `/api/admin/debug-logs` | GET/DELETE | ~8920 | Logs de débogage |

### Credentials admin

- Email : `PROPRIO_EMAIL` dans `.env`
- Password : `PROPRIO_PASSWORD` dans `.env`
- Aussi : `ADMIN_NUMBER` (téléphone pour alertes SMS)

---

## 17. Service Worker et cache PWA

**Fichier :** `static/sw.js`

### Règle fondamentale

**À chaque modification de `simli.html` ou `index.html` → incrémenter la version du cache.**

```javascript
var CACHE_NAME = "luna-v46";  // ← changer ce numéro à chaque déploiement frontend
```

### Stratégie de cache

| Type de ressource | Stratégie |
|---|---|
| Pages HTML (navigation) | Network-first (toujours la version fraîche) |
| Assets statiques (`/static/*`) | Cache-first (performance) |
| `/api/*`, `/ws/*`, `/simli` | Jamais caché (passthrough) |
| `/clear-cache` | Jamais caché |

### Forcer le rechargement côté client

Route : `GET /clear-cache` — efface tout le cache SW et recharge.  
Ou message SW : `PURGE_CACHE` via `postMessage`.

---

## 18. Variables d'environnement — liste complète

Fichier `.env` à la racine de `luna-server/`. **Ne jamais committer.**

### OpenAI

| Variable | Exemple | Description |
|---|---|---|
| `OPENAI_API_KEY` | `sk-proj-…` | Clé principale (chat, TTS, vision) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modèle IA du chat |
| `OPENAI_VOICE_NAME` | `coral` | Voix TTS du chat vocal |
| `SETUP_OPENAI_API_KEY` | `sk-proj-…` | Clé temporaire wizard (détruite après PV) |

### Tavus (visio avatar)

| Variable | Exemple | Description |
|---|---|---|
| `TAVUS_API_KEY` | `70cc…` | Clé API Tavus |
| `TAVUS_LUNA_PERSONA_ID` | `p10341f761ef` | ID persona Luna FR |
| `TAVUS_CALLBACK_URL` | `https://…/api/webhook/tavus` | URL webhook Tavus |
| `SIMLI_VOICE_ID` | `f9836c6e-…` | Voice ID Cartesia pour la visio |
| `SIMLI_API_KEY` | `61gtd…` | (Non utilisé actuellement) |
| `SIMLI_FACE_ID` | `b9e5f…` | (Non utilisé actuellement) |

### Twilio (SMS + appels)

| Variable | Exemple | Description |
|---|---|---|
| `TWILIO_ACCOUNT_SID` | `ACff…` | Identifiant compte Twilio |
| `TWILIO_AUTH_TOKEN` | `…` | Token secret Twilio |
| `TWILIO_PHONE_NUMBER` | `+17173409138` | Numéro sortant (E.164) |
| `VOICE_CALLBACK_URL` | `https://…/api/voice-call/twiml` | URL webhook voice Twilio |
| `VOICE_MAX_DURATION` | `600` | Durée max appel (secondes) |

### Stripe (paiements)

| Variable | Exemple | Description |
|---|---|---|
| `STRIPE_API_KEY` | `sk_live_…` | Clé secrète Stripe |
| `STRIPE_WEBHOOK_SECRET` | `whsec_…` | Secret webhook Stripe |
| `STRIPE_PRICE_ESSENTIEL` | `price_…` | ID prix Stripe plan Essentiel |
| `STRIPE_PRICE_CONFORT` | `price_…` | ID prix Stripe plan Confort |
| `STRIPE_PRICE_PREMIUM` | `price_…` | ID prix Stripe plan Premium |

### Auth et sécurité

| Variable | Exemple | Description |
|---|---|---|
| `JWT_SECRET_KEY` | `efe697…` | Clé de signature JWT — NE JAMAIS CHANGER EN PROD |
| `JWT_ALGORITHM` | `HS256` | Algorithme JWT |
| `REQUIRE_AUTH` | `true` | Activer l'authentification obligatoire |
| `PROPRIO_EMAIL` | `saintlouis.ludovic@gmail.com` | Email compte fondateur |
| `PROPRIO_PASSWORD` | `…` | Mot de passe compte fondateur |
| `ADMIN_PASSWORD` | `…` | Mot de passe dashboard admin |
| `ADMIN_NUMBER` | `+33658477952` | Téléphone fondateur (alertes SMS) |
| `ADMIN_PHONE` | `+33658477952` | Alias de ADMIN_NUMBER |

### Infrastructure

| Variable | Exemple | Description |
|---|---|---|
| `REDIS_URL` | `redis://localhost:6379/0` | URL Redis |
| `BASE_URL` | `https://luna-beta-674304336025…` | URL publique du serveur |
| `LUNA_BASE_URL` | idem | Alias |
| `LUNA_MODE` | `full` | `lite` (sans visio) ou `full` (avec visio Tavus) |
| `LUNA_PORT` | `8080` | Port d'écoute du serveur |
| `ENVIRONMENT` | `production` | `development` ou `production` |
| `CORS_ORIGINS` | `*` | Origines CORS autorisées |
| `MAX_CONCURRENT_CHATS` | `100` | Limite de sessions simultanées |

### APIs tierces

| Variable | Exemple | Description |
|---|---|---|
| `SERPER_API_KEY` | `…` | Clé Serper (recherche web) |
| `ELEVENLABS_API_KEY` | `…` | (Optionnel) Voix ElevenLabs |
| `ALERT_TELEGRAM_BOT_TOKEN` | `…` | Bot Telegram alertes fondateur |
| `FOUNDER_TELEGRAM_CHAT_ID` | `…` | Chat ID Telegram fondateur |

### PV de recette

| Variable | Exemple | Description |
|---|---|---|
| `PV_SIGNED` | `true` | PV signé ou non (ignoré si `pv_lock.json` existe) |
| `PV_SIGNATURE_HASH` | `sha256:…` | Hash SHA-256 du PV |
| `YAWATCH_LICENSE_KEY` | `…` | Clé de licence YAWatch |
| `YAWATCH_LICENSE_SERVER` | `https://…` | Serveur de licence |
| `VISIO_MAX_DURATION` | `240` | Durée max visio (minutes) |

---

## 19. Toutes les routes API

Classées par catégorie.

### Pages / Statique

| Route | Méthode | Description |
|---|---|---|
| `/` | GET | Page principale (chat ou setup selon PV) |
| `/simli` | GET | Page visio Tavus |
| `/admin` | GET | Dashboard admin |
| `/health` | GET | Santé serveur (public) |
| `/clear-cache` | GET | Purge cache SW |
| `/download` | GET | Page téléchargement |
| `/join/{token}` | GET | Rejoindre une visio (invité) |
| `/formulaires` | GET | Formulaires client |
| `/salon` | GET | Salle de réunion |
| `/world` | GET | Interface world |
| `/client` | GET | Interface client mobile |

### Chat et conversation

| Route | Méthode | Description |
|---|---|---|
| `/api/chat` | POST | Chat principal (streaming SSE) |
| `/api/greeting` | GET | Message d'accueil Luna |
| `/api/conversations` | GET/POST | Liste/créer conversations |
| `/api/conversations/{id}` | DELETE | Supprimer conversation |
| `/api/history` | GET | Historique messages |
| `/api/status` | GET | Statut Luna (online/setup) |

### Visio

| Route | Méthode | Description |
|---|---|---|
| `/api/call` | POST | Démarrer appel Tavus |
| `/api/call/end` | POST | Terminer l'appel |
| `/api/call/invite-guest` | POST | Inviter contact (SMS) |
| `/api/call/create-join-link` | POST | Créer lien d'invitation |
| `/api/simli/start` | POST | Démarrer appel Simli (fallback) |
| `/api/webhook/tavus` | POST | Webhook Tavus (tool calls) |
| `/api/visio/perception` | POST | Analyser frame caméra |
| `/api/visio/notes` | POST | Générer notes de session |
| `/api/visio/notes/save` | POST | Sauvegarder notes |
| `/api/visio/upload` | POST | Uploader document/image |

### Voix et SMS

| Route | Méthode | Description |
|---|---|---|
| `/api/voice-call` | POST | Lancer appel téléphonique |
| `/api/voice-call/twiml` | POST | Script TwiML (Twilio) |
| `/api/voice-call/conference` | POST | Créer conférence |
| `/api/voice-call/mute` | POST | Mute participant conférence |
| `/api/webhook/voice-incoming` | POST | Appel entrant Twilio |
| `/api/webhook/sms` | POST | SMS entrant Twilio |
| `/api/webhook/sms-status` | POST | Statut livraison SMS |
| `/api/sms/status` | GET | Statut SMS envoyés |
| `/api/invite-contact` | POST | Inviter contact Luna |

### Auth et profil

| Route | Méthode | Description |
|---|---|---|
| `/api/auth/register` | POST | Créer compte |
| `/api/auth/login` | POST | Connexion |
| `/api/auth/me` | GET | Profil JWT actuel |
| `/api/auth/change-password` | POST | Changer mot de passe |
| `/api/auth/checkout` | POST | Abonnement Stripe |
| `/api/auth/setup-card` | POST | Enregistrer carte |
| `/api/profile` | GET/POST | Profil abonné |
| `/api/settings` | GET/POST | Paramètres |
| `/api/quota` | GET | Quotas utilisés |

### Mémoire et données

| Route | Méthode | Description |
|---|---|---|
| `/api/notes` | GET/POST | Notes en mémoire |
| `/api/notes/{id}` | DELETE | Supprimer note |
| `/api/contacts` | GET/POST | Contacts de confiance |
| `/api/contacts/{phone}` | DELETE | Supprimer contact |
| `/api/instructions` | GET/POST | Instructions planifiées |
| `/api/instructions/{id}` | DELETE | Supprimer instruction |
| `/api/documents` | GET | Liste documents générés |
| `/api/documents/generate` | POST | Créer document |
| `/api/events` | GET | Journal d'événements |

### Stripe

| Route | Méthode | Description |
|---|---|---|
| `/api/stripe/webhook` | POST | Webhook Stripe (paiements) |
| `/api/payment/confirm/{id}` | POST | Confirmer paiement |
| `/api/payment/pending` | GET | Paiements en attente |

### Setup wizard

| Route | Méthode | Description |
|---|---|---|
| `/api/setup/status` | GET | État du wizard |
| `/api/setup/wizard-state` | GET | Étapes complétées |
| `/api/setup/save-config` | POST | Sauvegarder config |
| `/api/setup/check-phase-a` | POST | Vérifier phase A |
| `/api/setup/check-phase-b` | POST | Vérifier phase B |
| `/api/setup/check-phase-c` | POST | Vérifier phase C |
| `/api/setup/sign-pv` | POST | Signer le PV (verrouille le serveur) |
| `/api/setup/stripe-auto` | POST | Créer produits Stripe auto |
| `/api/setup/ai-chat` | POST | Chat avec Luna Setup |

### Admin

| Route | Méthode | Description |
|---|---|---|
| `/api/admin/login` | POST | Connexion admin |
| `/api/admin/dashboard` | GET | Vue globale |
| `/api/admin/clients` | GET/POST | Liste abonnés |
| `/api/admin/clients/{id}` | GET/PUT/DELETE | Gestion abonné |
| `/api/admin/quotas` | GET | Quotas tous abonnés |
| `/api/admin/revenue` | GET | Revenus |
| `/api/admin/costs` | GET | Coûts API |
| `/api/admin/alerts` | GET | Alertes système |
| `/api/admin/certificate` | GET | Certificat DOCX |
| `/api/admin/health` | GET | Santé détaillée |
| `/api/admin/debug-logs` | GET/DELETE | Logs debug |

### Cortex sécurité

| Route | Méthode | Description |
|---|---|---|
| `/api/cortex/status` | GET | Statut Cortex (public) |
| `/api/cortex/threats` | GET | Menaces et bans |
| `/api/cortex/ban/{ip}` | POST/DELETE | Bannir/débannir IP |
| `/api/cortex/whitelist/{ip}` | POST/DELETE | Whitelist IP |
| `/api/cortex/shield` | POST | Activer mode bouclier |
| `/api/cortex/lockdown` | POST | Activer lockdown |
| `/api/cortex/normalize` | POST | Mode normal |

### Modules avancés

| Route | Méthode | Description |
|---|---|---|
| `/api/family` | GET/POST | Groupe famille |
| `/api/family/members` | GET/POST | Membres famille |
| `/api/family/sos` | POST | Alerte SOS |
| `/api/meeting/join` | POST | Rejoindre réunion (bot) |
| `/api/rooms` | GET/POST | Salles de réunion |
| `/api/unified/send` | POST | Canal unifié (voix/SMS/chat) |
| `/api/weather` | GET | Météo actuelle |
| `/api/geolocation` | GET/POST | Géolocalisation |
| `/api/perception/frame` | POST | Frame perception (hors visio) |
| `/api/debug/log` | POST | Log distant depuis JS |

---

## 20. Modules core/

### `core/memory/`
Persistance Redis. Contient : conversations, messages, instructions, contacts, notes, profil, état perception.  
**Clé Redis principale :** préfixe `luna:` (voir `key_schema.md`)

### `core/cortex/`
IA de sécurité autonome. Boucle toutes les 30s, analyse avec GPT-4o-mini toutes les 5min, décide des actions (ban, alert, shield).

### `core/actions/quota_guard.py`
Vérifie les quotas avant chaque action (SMS, voix, visio). Retourne une erreur si quota dépassé.

### `core/perception/`
- `analyzer.py` — Analyse GPT-4o vision d'une frame JPEG
- `detector.py` — Détecte anomalies : chute, personne au sol, détresse

### `core/secretary/`
Secrétariat : budget, dépenses, rappels, dossiers. Accessible depuis le chat (onglet Secrétaire).

### `core/safety/`
Détection de détresse dans les messages. Escalade vers contacts de confiance si nécessaire.

### `core/documents/generator.py`
Génère des fichiers DOCX : comptes-rendus, contrats, certificat d'autonomie.

### `core/social/`
Réseau famille : groupe, messages famille, SOS, escalade en cas d'urgence.

### `core/gamification/`
Badges, missions, stats. Utilisé pour l'engagement abonné.

### `core/rooms/`
Salles de réunion multi-utilisateurs (Daily.co).

### `core/notifications/`
Moteur de notifications push (web push API).

---

## 21. Déploiement Cloud Run

**Projet GCP :** `crypto-parser-475411-k4`  
**Région :** `europe-west1`  
**Service :** `luna-beta`  
**URL stable :** `https://luna-beta-674304336025.europe-west1.run.app`  
**URL alternative :** `https://luna-beta-gly3g647na-ew.a.run.app` (même service)

### Commande de déploiement

```bash
# Depuis le dossier luna-server/
gcloud run deploy luna-beta \
  --source . \
  --project crypto-parser-475411-k4 \
  --region europe-west1 \
  --quiet
```

Durée : 4–8 minutes. Crée automatiquement une nouvelle révision.

### Dockerfile

Le `Dockerfile` à la racine définit l'image. Points clés :
- Base Python 3.11
- Redis installé en sidecar dans le container
- Le `.env` est injecté comme secret GCP (ne pas le mettre dans l'image)

### Variables d'env Cloud Run

Les variables `.env` sont injectées via les secrets GCP Cloud Run, pas via le fichier `.env` directement.  
Gérer via : GCP Console → Cloud Run → luna-beta → Variables et secrets.

### Rollback vers une version précédente

```bash
# Lister les révisions
gcloud run revisions list --service luna-beta --project crypto-parser-475411-k4 --region europe-west1

# Rerouter 100% du trafic vers une ancienne révision
gcloud run services update-traffic luna-beta \
  --to-revisions=luna-beta-00265-dc8=100 \
  --project crypto-parser-475411-k4 \
  --region europe-west1
```

---

## 22. Passer en anglais

Modifier dans cet ordre :

1. **Prompt chat** — `luna_web.py` ligne 787 : réécrire `LUNA_SYSTEM_PROMPT` en anglais
2. **Prompt visio** — `integrations/tavus/tavus_client.py` ligne 48 : réécrire `build_tavus_context()` en anglais
3. **STT visio** — `static/simli.html` : changer `_speechReco.lang = 'fr-FR'` → `'en-US'`
4. **Langue Tavus** — `luna_web.py` fonction `_start_simli_visio()` : paramètre `"language": "en"`
5. **Textes UI chat** — `static/index.html` : chercher/remplacer tous les textes FR
6. **Textes UI visio** — `static/simli.html` : scènes `LUNA_SCHEDULE` (champs `text:`), sous-titres actPhoneRing/actPhoneAnswer
7. **TTS** — OpenAI TTS détecte la langue automatiquement, rien à changer

---

## 23. Intégration Zoom

**Luna ne peut pas rejoindre une réunion Zoom.** Explication technique :

- Luna est basée sur **Daily.co** (WebRTC ouvert)
- Zoom utilise son propre protocole propriétaire
- Il n'existe pas de bridge officiel gratuit

**Alternatives possibles si c'est une priorité :**

| Solution | Complexité | Coût |
|---|---|---|
| Zoom API + webhook transcription | Élevée | Zoom Business+ requis |
| Enregistrement audio Zoom → upload Luna | Simple | 0€ |
| Bot Zoom (Meeting SDK) | Très élevée | Licence Zoom ISV |
| Utiliser Daily.co au lieu de Zoom | Simple | Daily.co gratuit jusqu'à 1000 min/mois |

**Recommandation :** utiliser le système d'invitation Luna (`/api/call/invite-guest`) pour que les participants rejoignent la visio Luna plutôt que Zoom.

---

*Dernière mise à jour : 17 mai 2026. Maintenir à jour après chaque refactoring majeur.*
