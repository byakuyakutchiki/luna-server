# ETAT DU PROJET LUNA - YAWatch (v3) - 31 janvier 2026

## Qu'est-ce que Luna ?

Luna est l'assistante IA personnelle de YAWatch, un service d'assistance par abonnement
pour les personnes agees ou isolees. Luna accompagne le souscripteur au quotidien :
chat texte, appels video avec avatar, envoi de SMS, rappels, generation de documents,
et perception visuelle de l'environnement.

---

## Architecture technique

- **Backend** : Python FastAPI/Uvicorn, HTTPS port 8888
- **LLM** : OpenAI GPT-4 Turbo (conversations texte + generation de contenu)
- **Video avatar** : Tavus CVI (persona Luna, appels video temps reel)
- **SMS/Appels** : Twilio
- **Memoire** : Redis (conversations, instructions, contacts, notes, profil)
- **Vision** : YOLOv8n + OpenCV (perception contextuelle webcam)
- **Documents** : python-docx (generation DOCX)
- **Frontend** : SPA HTML/JS vanilla (7 onglets)

---

## Ce qui est operationnel

### 1. Chat texte (web)
- Interface chat avec historique localStorage
- System prompt complet avec identite Luna, regles de securite, style
- Persistance des messages dans Redis
- Rate limiting, gestion des erreurs

### 2. Appels video (Tavus)
- Avatar Luna en visio temps reel
- Invitation de contacts de confiance par SMS (lien pour rejoindre l'appel)
- Contexte personnalise envoye a Tavus (profil, contacts, instructions)

### 3. Tool Calling depuis la visio (7 tools)
Luna peut AGIR concretement pendant un appel video :
- `send_sms` : envoyer un SMS a un contact de confiance
- `create_instruction` : creer un rappel/instruction
- `create_note` : prendre une note
- `get_contacts` : lister les contacts de confiance
- `generate_document` : generer un courrier/document DOCX
- `alert_contacts` : alerter tous les contacts d'urgence
- `report_observation` : noter une observation visuelle (Raven)

Webhook `POST /api/webhook/tavus` recoit les events tool_call de Tavus.
Les tools sont configures sur la Persona via PATCH API (JSON Patch RFC 6902).

### 4. Tavus Raven Perception (visio)
Pendant les appels video, le modele Raven de Tavus analyse :
- Fatigue / somnolence
- Signes de detresse / inconfort
- Posture (assis, debout, inhabituelle)
- Presence d'autres personnes
- Etat emotionnel (heureux, triste, neutre)

Les observations sont logguees via le tool `report_observation`.

### 5. Profil souscripteur (40+ champs)
Stocke dans Redis, accessible via API et onglet Profil :
- Identite, adresse, telephone, email
- Situation familiale, autonomie, mobilite
- Sante : medecin, pharmacie, allergies, traitements, pathologies, mutuelle
- Logement, statut professionnel
- Preferences Luna : ton, tutoiement, horaires, centres d'interet
- Instructions permanentes, blacklist, priorites, budget delegue

### 6. Contacts de confiance (max 5)
- Nom, relation, telephone, canal prefere, flag urgence-seulement
- CRUD complet via API et onglet Contacts
- Utilises par Luna pour envoyer SMS, alertes, invitations visio

### 7. Instructions (moteur NLP)
- Parser en langage naturel : "Rappelle-moi de prendre mes cachets tous les jours a 8h"
- Types : one_time, daily, recurring
- Actions : reminder, sms_contact, call_contact, note, alert, surveillance
- Scheduler avec calcul de prochaine execution
- Executor en boucle asyncio (30s)
- Persistance Redis, CRUD via API et onglet Instructions

### 8. Generation de documents DOCX
- Courrier administratif (CAF, impots, bailleur...)
- Lettre de resiliation
- Fiche sante (depuis le profil)
- Export des notes
- Liste des contacts
- Resume hebdomadaire
- GPT-4 genere le contenu, python-docx structure le document
- Telechargement direct depuis l'onglet Documents

### 9. Perception YOLO (aide contextuelle)
- YOLOv8n (nano, CPU) + OpenCV pour capture webcam
- Detection : personnes, posture (debout/assis/sol/lit), objets (chaise, lit, TV, etc.)
- Analyse temporelle : personne au sol > 5min = concern, absence > 1h = attention
- Boucle asyncio 10s, opt-in (off par defaut)
- Aucune image stockee, seules les metadonnees dans Redis
- Contexte injecte dans les conversations Luna
- **LEGAL** : aide contextuelle, PAS surveillance garantie. Luna dit "j'ai remarque que...", jamais "je surveille". Aucune promesse au client.

### 10. Securite
- Safety Guardian : detection de detresse dans le texte
- Content Filter : filtrage de contenu inapproprie
- Emergency Handler : gestion des situations critiques
- Legal Knowledge : base de connaissances juridiques
- Luna ne donne aucun conseil medical/juridique/financier
- Luna ne peut pas appeler les urgences (suggere les numeros)
- Confirmation obligatoire avant toute action consommant du quota

### 11. Quotas & Plans
- Essentiel (139 EUR/mois) : 20 SMS, 15 min visio, 100 MB memoire
- Confort (229 EUR/mois) : 50 SMS, 45 min visio, 500 MB memoire
- Premium (399 EUR/mois) : 100 SMS, 90 min visio, 2 GB memoire
- QuotaGuard avec alertes 80%/90%/100%

---

## Structure du code

```
serveur/
  luna_web.py                  # Serveur principal FastAPI (65 Ko, ~1500 lignes)
  luna_chat.py                 # Interface CLI chat
  requirements.txt             # Dependencies
  static/
    index.html                 # Frontend SPA (54 Ko, 7 onglets)
    documents/{tenant_id}/     # Documents DOCX generes
  core/
    perception/                # YOLO + analyse scene
      detector.py              # YOLOv8n + webcam
      analyzer.py              # Analyse temporelle + anomalies
    documents/
      generator.py             # Generation DOCX (python-docx)
    instructions/
      parser.py                # NLP parser (langage naturel → instruction)
      scheduler.py             # Planification des instructions
      executor.py              # Execution des instructions
      templates.py             # Templates de messages
    memory/
      redis_client.py          # Client Redis avec cles prefixees
      memory_manager.py        # Gestionnaire memoire haut niveau
      schemas.py               # Modeles Pydantic (40+ champs profil)
    safety/
      guardian.py              # Detection detresse + securite + legal compliance
      emergency_handler.py     # Gestion urgences
      content_filter.py        # Filtrage contenu
      legal_knowledge.py       # Base juridique
    testing/
      simulator.py             # Simulateur de scenarios (4 scenarios predefinis)
    actions/
      dispatcher.py            # Routage des actions
      confirmation.py          # Systeme de confirmation
      quota_guard.py           # Gestion des quotas
      models.py                # Modeles d'actions
  integrations/
    tavus/
      tavus_client.py          # Client Tavus (7 tools, Raven, conversations)
    twilio/
      sms_client.py            # Client Twilio (SMS, appels)
    openai/
      __init__.py              # Config OpenAI
  docs/
    LUNA_CAPACITES_COMPLETES.md
    LUNA_ACTIONS_DELEGUEES.md
    LUNA_PROFIL_SOUSCRIPTEUR.md
```

---

## Endpoints API

### Chat & Visio
- `POST /api/chat` - Chat texte avec Luna
- `GET /api/greeting` - Message d'accueil
- `POST /api/call` - Demarrer un appel video Tavus
- `POST /api/invite-contact` - Inviter un contact dans l'appel
- `POST /api/webhook/tavus` - Webhook Tavus (tool_call, transcription)

### Profil
- `GET /api/profile` - Lire le profil
- `POST /api/profile` - Sauvegarder le profil
- `PATCH /api/profile` - Modifier des champs

### Contacts
- `GET /api/contacts` - Lister les contacts
- `POST /api/contacts` - Ajouter un contact
- `DELETE /api/contacts/{phone}` - Supprimer un contact

### Instructions
- `GET /api/instructions` - Lister les instructions
- `POST /api/instructions` - Creer (texte naturel)
- `DELETE /api/instructions/{id}` - Desactiver

### Notes
- `GET /api/notes` - Lister les notes
- `POST /api/notes` - Ajouter une note

### Documents
- `POST /api/documents/generate` - Generer un document
- `GET /api/documents` - Lister les documents
- `GET /static/documents/{tid}/{filename}` - Telecharger

### Perception
- `POST /api/perception/start` - Activer la camera
- `POST /api/perception/stop` - Desactiver
- `GET /api/perception/status` - Statut + scene
- `GET /api/perception/scene` - Scene actuelle

### Journal d'evenements
- `GET /api/events` - Journal chronologique (paginable)
- `GET /api/events/export` - Export texte brut

### Test / Simulateur
- `GET /api/test/scenarios` - Liste les scenarios disponibles
- `POST /api/test/scenario` - Execute un scenario (protege par cle admin)

### Systeme
- `GET /api/status` - Statut complet (legal_mode, caution_mode inclus)
- `GET /api/quota` - Quotas et usage

---

## Blindage comportemental (7 ameliorations - 31 jan 2026)

### 12. legal_mode = assistance_only
- Variable globale `LEGAL_MODE` verifiee partout
- `SafetyGuardian.check_legal_compliance()` : 13 expressions interdites
- Disclaimer legal dans les alertes SMS
- Visible dans `/api/status`

### 13. Prudence verbale (perception)
- Banlist de mots : surveillance, diagnostic, chute, urgence medicale...
- Remplacements automatiques (chute → situation au sol, etc.)
- `_sanitize_description()` dans `SceneAnalyzer`
- Consignes dans le system prompt (chat + Tavus)

### 14. Memoire comportementale verrouillee
- `identity_core` + `behavior_rules` dans Redis
- Injectes comme message systeme AVANT chaque reponse
- Initialises au demarrage si absents

### 15. Mode prudence configurable
- Champ `caution_mode` dans le profil (passif/assistif/proactif/urgence_only)
- Modulation du comportement selon le mode
- Filtrage perception adapte au mode

### 16. Explicabilite des actions
- Champ `reasoning_explanation` sur ActionRequest, ActionResult, ActionLog
- Tous les tool handlers logguent le reasoning
- Tracabilite complete de chaque decision

### 17. Journal d'evenements humain
- Redis LIST chronologique (cap 500, TTL 90j)
- `log_event()` appele dans chat, tools, perception, instructions
- `GET /api/events` + `GET /api/events/export`

### 18. Simulateur de scenarios
- 4 scenarios predefinis (distress, medical_advice, person_on_floor, normal_day)
- `GET /api/test/scenarios` + `POST /api/test/scenario`
- Mode test : SMS non envoyes

### 19. Preparation multi-exploitant
- Nom du souscripteur lu depuis le profil Redis (plus de "Ludo" en dur)
- Validation au demarrage : OPENAI_API_KEY et ADMIN_NUMBER obligatoires
- `.env.example` complet avec toutes les variables documentees
- Aucun fichier sensible (.env, .pem) sur le Drive

---

## Ce qui reste a faire / ameliorer

- Tests automatises (pytest)
- OTP SMS pour verification des contacts de confiance
- WhatsApp integration (Twilio WhatsApp API)
- Dashboard famille (interface pour les proches)
- Multi-tenant reel (actuellement TENANT_ID=1 en dur)
- Deploiement cloud (Docker, reverse proxy, SSL)
- Rate limiting plus fin par endpoint
- Logs structures (JSON) pour monitoring
- Historique perception plus riche (graphiques activite)
- Pose estimation (MediaPipe) pour ameliorer la detection de chutes
- Integration calendrier (Google Calendar, rappels RDV)
- Reconnaissance vocale directe (STT) pour commandes sans Tavus
