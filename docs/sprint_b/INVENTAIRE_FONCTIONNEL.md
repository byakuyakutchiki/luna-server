# Inventaire fonctionnel – YAWatch-Luna

**Projet** : `/home/ludo/luna-server-audit`  
**Fichier principal** : `luna_web.py` (FastAPI monolithique)  
**Pages statiques** : `static/*.html`  
**Date d’analyse** : 2026-06-15  
**Méthode** : analyse statique du code (pas de tests en runtime). L’état “Fonctionne ?” est déduit des vérifications de clés API, des `fallback`, des `TODO` et des commentaires du code.

Légende :

| État | Signification |
|------|---------------|
| **OK** | Code complet, dépendances vérifiées au boot, pas d’indication de régression majeure. |
| **Partiel** | Code présent mais nécessite une configuration externe ou a des limitations documentées. |
| **KO** | Non implémenté, volontairement désactivé ou cassé en l’état. |
| **Non testé** | Code présent mais impossible de statuer sans exécution réelle. |

---

## 1. Auth / Compte

| Fonction | URL (frontend / API) | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|----------------------|----------|--------------|------------|----------|
| Page d’accueil / login | `/` (`static/index.html`) | Oui | OK | `JWT_SECRET_KEY`, Redis (recommandé) | Critique |
| Inscription client | `POST /api/auth/register` | Oui | OK | Redis, `JWT_SECRET_KEY`, bcrypt | Critique |
| Connexion client | `POST /api/auth/login` | Oui | OK | Redis + fallback `.env` (`PROPRIO_EMAIL` / `PROPRIO_PASSWORD_HASH`) | Critique |
| Refresh token | `POST /api/auth/refresh` | Oui | OK | `JWT_SECRET_KEY`, Redis (lecture profil) | Critique |
| Profil JWT `/me` | `GET /api/auth/me` | Oui | OK | Redis | Haute |
| Changement de mot de passe | `POST /api/auth/change-password` | Oui | OK | Redis, bcrypt | Haute |
| Checkout Stripe (upgrade plan) | `POST /api/auth/checkout` | Oui | Partiel | `STRIPE_API_KEY`, `STRIPE_PRICE_*`, Redis | Haute |
| Enregistrement carte (setup) | `POST /api/auth/setup-card` | Oui | Partiel | `STRIPE_API_KEY`, Redis | Haute |
| Page client connecté | `/client` | Oui | OK | JWT valide | Critique |

**Remarques** :
- Le login a un fallback sur les variables d’environnement si Redis est indisponible.
- Le checkout et l’enregistrement de carte retournent une erreur 500 si `STRIPE_API_KEY` est absent.
- Le serveur ne démarre pas sans `JWT_SECRET_KEY`.

---

## 2. Chat / Assistant IA

| Fonction | URL (frontend / API) | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|----------------------|----------|--------------|------------|----------|
| Chat principal | `POST /api/chat` | Oui | OK / Partiel | OpenAI (`OPENAI_API_KEY` / `LLM_API_KEY`) ou Anthropic (`ANTHROPIC_API_KEY`), Redis | Critique |
| Greeting / salutation | `GET /api/greeting` | Oui | OK | OpenAI/Anthropic, Redis | Haute |
| Chat en streaming SSE | `POST /api/chat` (`stream=true`) | Oui | OK | Anthropic prioritaire, fallback OpenAI | Haute |
| Historique conversations | `GET /api/history` | Oui | OK | Redis | Haute |
| CRUD conversations | `GET/POST/PATCH/DELETE /api/conversations` | Oui | OK | Redis | Haute |
| Recherche conversations | `GET /api/conversations/search` | Oui | OK | Redis | Moyenne |
| Auto-titre conversation | interne (`gpt-4o-mini`) | Oui | OK | OpenAI | Moyenne |
| Mode secrétaire vs compagnon | `mode` dans `/api/chat` | Oui | OK | Aucune externe | Moyenne |

**Remarques** :
- Le chat injecte profil, contacts, géolocalisation, instructions, notes, météo, gamification, budget.
- Les tools (SMS, appel, email, notes, instructions, recherche web, vols, hôtels, restaurants) sont déclarés mais leur exécution réelle dépend de Twilio, Serper, Duffel, etc.
- Fallback textuel si OpenAI n’est pas configuré.

---

## 3. Contacts / Famille / Social

### 3.1 Contacts de confiance
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Liste contacts | `GET /api/contacts` | Oui | OK | Redis, MemoryManager | Haute |
| Ajout contact | `POST /api/contacts` | Oui | OK | Redis | Haute |
| Suppression contact | `DELETE /api/contacts/{phone}` | Oui | OK | Redis | Haute |
| Invitation SMS à rejoindre Luna | `POST /api/contacts/{phone}/invite` | Oui | Partiel | Twilio SMS configuré | Moyenne |

### 3.2 Famille (Family Pack)
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Groupe familial | `GET/POST /api/family` | Oui | OK | Redis | Moyenne |
| Membres famille | `GET/POST /api/family/members` | Oui | OK | Redis, Twilio (OTP) | Moyenne |
| Vérification membre OTP | `POST /api/family/members/{phone}/verify` | Oui | Partiel | Twilio SMS | Moyenne |
| Messages famille | `GET/POST /api/family/messages` | Oui | OK | Redis | Moyenne |
| Règles d’escalade | `GET/POST/DELETE /api/family/escalation` | Oui | OK | Redis | Moyenne |
| Détection détresse texte | `POST /api/family/detect-distress` | Oui | OK | Dictionnaire interne, Redis | Moyenne |
| Audit famille | `GET /api/family/audit` | Oui | OK | Redis | Basse |
| SOS famille | `POST /api/family/sos` | Oui | Partiel | Twilio SMS, contacts configurés | Haute |
| Protection ado | `POST /api/family/setup-teen-protection` | Oui | OK | Redis | Moyenne |

### 3.3 Social / Amis
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Code ami | `GET /api/social/friend-code` | Oui | OK | Redis | Moyenne |
| Utiliser code ami | `POST /api/social/friend-code/use` | Oui | OK | Redis | Moyenne |
| Liste amis | `GET /api/social/friends` | Oui | OK | Redis | Moyenne |
| Demandes d’amitié | `GET/POST /api/social/friends/requests` | Oui | OK | Redis | Moyenne |
| Amis externes (téléphone) | `GET/POST/DELETE /api/social/friend-extern` | Oui | Partiel | Redis, Twilio (optionnel) | Moyenne |
| DM / salons privés | `GET/POST /api/social/dm/...`, `WS /ws/dm/{room_id}` | Oui | OK | Redis | Moyenne |
| Heartbeat social | `POST /api/social/heartbeat` | Oui | OK | Redis | Basse |

**Remarques** :
- Le module social est monté via `social_router` (`core/social/routes.py`).
- Les invitations externes dépendent de Twilio pour l’envoi SMS.

---

## 4. Instructions / Scheduler

| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Liste instructions | `GET /api/instructions` | Oui | OK | Redis, `core.instructions` | Haute |
| Création instruction (NL) | `POST /api/instructions` | Oui | OK | Redis, `InstructionParser` | Haute |
| Détail / maj / suppression | `GET/PUT/DELETE /api/instructions/{id}` | Oui | OK | Redis | Haute |
| Prochaines exécutions | `GET /api/instructions/upcoming` | Oui | OK | Redis | Moyenne |
| Historique exécutions | `GET /api/instructions/history` | Oui | OK | Redis | Moyenne |
| Exécution immédiate | `POST /api/instructions/{id}/execute` | Oui | OK | Redis, `InstructionExecutor` | Haute |

**Remarques** :
- Le parser transforme le langage naturel en instruction structurée.
- `ENABLE_INSTRUCTIONS` permet de désactiver le scheduler au boot.

---

## 5. Guardian (surveillance géolocalisée)

| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Page Guardian | `/guardian` | Oui | OK | JWT | Haute |
| Démarrer session | `POST /api/guardian/start` | Oui | OK | Redis, GuardianEngine, contacts d’urgence | Haute |
| Arrêter session | `POST /api/guardian/stop/{session_id}` | Oui | OK | Redis | Haute |
| Statut session | `GET /api/guardian/status/{session_id}` | Oui | OK | Redis | Haute |
| Envoi position GPS | `POST /api/guardian/location/{session_id}` | Oui | OK | Redis, GuardianEngine | Haute |
| Refus géoloc | `POST /api/guardian/location-denied/{session_id}` | Oui | OK | Redis | Moyenne |
| Bouton SOS | `POST /api/guardian/sos/{session_id}` | Oui | Partiel | Twilio SMS, contacts d’urgence | Critique |
| WebSocket temps réel | `WS /api/guardian/ws/{session_id}` | Oui | OK | Redis, GuardianEngine | Haute |
| Partage position live | `GET /api/guardian/share/{session_id}` + `/guardian-live/{token}` | Oui | OK | Redis, Leaflet (frontend) | Haute |
| Position live publique | `GET /api/guardian/live-position/{token}` | Oui | OK | Redis | Haute |
| Frame caméra / perception | `POST /api/guardian/frame/{session_id}` | Oui | Partiel | OpenAI Vision, `PerceptionDetector` | Moyenne |
| Templates profils | `GET /api/guardian/config/profiles` | Oui | OK | GuardianEngine | Moyenne |

**Remarques** :
- Le SOS est silencieux si aucun contact d’urgence n’est configuré (422).
- Les alertes SMS passent par Twilio.
- L’analyse caméra dépend du module `core.perception` et d’OpenAI Vision.

---

## 6. Secrétaire / Documents

### 6.1 Secrétaire personnelle (`core/secretary/routes.py`)
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Scan document photo | `POST /api/secretary/scan` | Oui | OK | OpenAI Vision, Redis | Haute |
| Liste documents | `GET /api/secretary/documents` | Oui | OK | Redis | Haute |
| Détail document | `GET /api/secretary/documents/{doc_id}` | Oui | OK | Redis | Haute |
| Changement statut doc | `POST /api/secretary/documents/{doc_id}/status` | Oui | OK | Redis | Moyenne |
| Recherche documents | `GET /api/secretary/documents/search/{query}` | Oui | OK | Redis | Moyenne |
| Résumé documents | `GET /api/secretary/summary` | Oui | OK | Redis | Moyenne |
| Dossiers | `GET /api/secretary/folders` | Oui | OK | Redis | Moyenne |
| Budget / analyse | `GET /api/secretary/budget` | Oui | OK | Redis | Haute |
| Profil budget | `POST /api/secretary/budget/profile` | Oui | OK | Redis | Haute |
| Entrées budget | `GET/POST /api/secretary/budget/...` | Oui | OK | Redis | Haute |
| Rappels | `GET/POST /api/secretary/reminders` | Oui | OK | Redis | Haute |
| “Est-ce que je peux me le permettre ?” | `POST /api/secretary/can-i-afford` | Oui | OK | Redis | Moyenne |

### 6.2 Coffre-fort documentaire (`core/vault/routes.py`)
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Consentement RGPD | `GET/POST/DELETE /api/vault/consent` | Oui | OK | Redis | Haute |
| Scan + classification | `POST /api/vault/scan` | Oui | OK | OpenAI Vision (`gpt-4o`), Redis | Haute |
| Liste docs coffre | `GET /api/vault/docs` | Oui | OK | Redis | Haute |
| Détail doc | `GET /api/vault/doc/{doc_id}` | Oui | OK | Redis | Haute |
| Suppression doc | `DELETE /api/vault/doc/{doc_id}` | Oui | OK | Redis | Haute |
| Rappels docs | `GET /api/vault/reminders` | Oui | OK | Redis | Haute |
| Types documentaires | `GET /api/vault/types` | Oui | OK | `DOC_TYPES` interne | Moyenne |
| Profil unifié (vault → formulaires) | `GET /api/vault/profile-data` | Oui | OK | Redis | Haute |
| Appliquer doc au profil | `POST /api/vault/apply-to-profile` | Oui | OK | Redis | Haute |
| Page documents | `/documents`, `/vault` | Oui | OK | JWT | Haute |

### 6.3 Générateur de documents
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Générer document | `POST /api/documents/generate` | Oui | OK | OpenAI, `DocumentGenerator`, FPDF | Haute |
| Liste documents générés | `GET /api/documents` | Oui | OK | disque | Moyenne |
| Téléchargement | `GET /api/documents/download/{filename}` | Oui | OK | disque | Moyenne |
| Dashboard documents v2 | `GET /api/documents/v2/...` | Oui | OK | Redis | Moyenne |

**Remarques** :
- Le scan nécessite une clé OpenAI avec accès Vision.
- Le vault ne stocke pas les images, seulement les métadonnées extraites (RGPD).

---

## 7. Visio / Appels

### 7.1 Visio avatar (Tavus / Simli)
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Santé visio | `GET /api/visio/health` | Oui | OK | `TAVUS_API_KEY`, `SIMLI_API_KEY` | Haute |
| Démarrer visio | `POST /api/call` | Oui | Partiel | Tavus (premium/fondateur) ou Simli, Redis | Haute |
| Terminer visio Tavus | `POST /api/call/end` | Oui | Partiel | Tavus configuré | Haute |
| Config Simli | `GET /api/config/simli` | Oui | OK | `.env` | Moyenne |
| Démarrer Simli | `POST /api/simli/start` | Oui | KO | Simli désactivé (`_SIMLI_AVAILABLE = False`) | Haute |
| WebSocket Simli | `WS /ws/simli/{session_id}` | Oui | KO | Simli non disponible | Moyenne |
| Perception visio | `POST /api/visio/perception` | Oui | Partiel | OpenAI Vision / PerceptionDetector | Moyenne |
| Notes visio auto | `POST /api/visio/notes` | Oui | OK | OpenAI (`gpt-4o-mini`) | Moyenne |
| Sauvegarde notes visio | `POST /api/visio/notes/save` | Oui | OK | Redis | Moyenne |
| Chat texte visio | `POST /api/visio/chat` | Oui | OK | OpenAI | Moyenne |
| TTS visio | `POST /api/visio/tts` | Oui | OK | OpenAI | Moyenne |
| Transcription visio | `POST /api/visio/transcribe` | Oui | OK | OpenAI Whisper | Moyenne |
| Upload visio | `POST /api/visio/upload` | Oui | OK | OpenAI Vision | Moyenne |
| Invitation invité visio | `POST /api/call/invite-guest` | Oui | Partiel | Twilio SMS | Moyenne |
| Lien d’invitation | `POST /api/call/create-join-link` | Oui | OK | Redis | Moyenne |
| Page invitation | `/join/{token}` | Oui | OK | Redis | Moyenne |
| Page Simli | `/simli` | Oui | OK | JWT | Haute |

**Remarques** :
- Simli est volontairement désactivé dans `luna_web.py` (`_SIMLI_AVAILABLE = False`) : Tavus est le fournisseur principal.
- Le routing Tavus/Simli dépend du plan (`premium`/`fondateur` → Tavus ; `essentiel`/`confort` → Simli). Comme Simli est KO, les plans non-premium tombent en erreur 503 si Tavus n’est pas configuré.
- `LUNA_MODE=lite` désactive la visio.

### 7.2 Appels vocaux (Twilio + OpenAI Realtime)
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Appel vocal sortant | `POST /api/voice-call` | Oui | Partiel | Twilio Voice, `OPENAI_API_KEY` | Haute |
| TwiML appel | `POST /api/voice-call/twiml` | Oui | OK | Twilio Voice | Haute |
| Conférence téléphonique | `POST /api/voice-call/conference` | Oui | Partiel | Twilio Voice, OpenAI Realtime | Moyenne |
| WebSocket media stream | `WS /api/voice-call/media-stream` | Oui | Partiel | Twilio, OpenAI Realtime | Haute |
| Mute forcé | `POST /api/voice-call/mute` | Oui | OK | bridge actif | Moyenne |
| Luna Voice navigateur | `WS /ws/luna-voice` | Oui | Partiel | OpenAI Realtime, JWT | Haute |

### 7.3 Iris (visio collaborative / team)
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Créer session Iris | `POST /api/iris/session/create` | Oui | OK | Redis, IrisSessionManager | Haute |
| Statut session | `GET /api/iris/session/{id}/status` | Oui | OK | Redis | Haute |
| Inviter participant | `POST /api/iris/session/{id}/invite` | Oui | OK | Redis | Haute |
| Rejoindre session | `/join/{invite_token}`, `POST /api/iris/session/join` | Oui | OK | Redis, JWT participant | Haute |
| WebSocket voix Iris | `WS /ws/iris-voice` | Oui | Partiel | OpenAI Realtime, Redis | Haute |
| Approuver/rejeter action | `POST /api/iris/session/{id}/approve|reject/{action_id}` | Oui | OK | Redis | Haute |
| Page équipe | `/team` | Oui | OK | JWT | Moyenne |
| Workspace legacy | `/workspace`, `/dashboard`, `/prospects` | Oui | OK | JWT | Basse |

**Remarques** :
- Les appels vocaux et visio temps réel sont complexes : ils nécessitent Twilio + OpenAI Realtime + URL publique pour les callbacks.
- Le mode “Foundation test” simule les appels externes sans les déclencher réellement.

---

## 8. Paiements / Stripe

| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Webhook Stripe | `POST /api/stripe/webhook` | Oui | Partiel | `STRIPE_WEBHOOK_SECRET`, `STRIPE_API_KEY` | Haute |
| Confirmation paiement conciergerie | `POST /api/payment/confirm/{intent_id}` | Oui | Partiel | `STRIPE_SECRET_KEY` | Haute |
| Paiements en attente | `GET /api/payment/pending` | Oui | Partiel | `STRIPE_SECRET_KEY` | Haute |
| Commissions admin | `GET /api/admin/commissions` | Oui | OK | Redis | Moyenne |
| Statut webhook Stripe | `GET /api/setup/stripe-webhook-status` | Oui | OK | Mémoire serveur | Moyenne |
| Création auto produits Stripe | `POST /api/setup/stripe-auto` | Oui | Partiel | `STRIPE_API_KEY`, module `stripe_setup` | Moyenne |

**Remarques** :
- Le webhook gère `checkout.session.completed`, `subscription.updated/deleted`, `payment_intent.succeeded`, etc.
- Sans `STRIPE_WEBHOOK_SECRET`, le webhook retourne 500.
- Le mode “Foundation test” désactive les vrais paiements.

---

## 9. Admin / Setup / Licenses

### 9.1 Admin fondateur
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Page admin | `/admin` | Oui | OK | `ADMIN_PASSWORD` | Haute |
| Login admin | `POST /api/admin/login` | Oui | OK | `ADMIN_PASSWORD` | Haute |
| Dashboard admin | `GET /api/admin/dashboard` | Oui | OK | Redis | Haute |
| Liste clients | `GET /api/admin/clients` | Oui | OK | Redis | Haute |
| Détail / création / maj / suppression client | `GET/POST/PATCH/DELETE /api/admin/clients/{id}` | Oui | OK | Redis | Haute |
| Reset password client | `POST /api/admin/reset-password/{id}` | Oui | OK | Redis, bcrypt | Haute |
| Quotas clients | `GET /api/admin/quotas` | Oui | OK | Redis, Cortex | Haute |
| Coûts API | `GET /api/admin/costs` | Oui | OK | Redis, Cortex | Haute |
| Alertes | `GET /api/admin/alerts` | Oui | OK | Redis | Moyenne |
| Objectifs / diagnostic | `GET /api/admin/objectives` | Oui | OK | Redis, tous les services | Haute |
| Santé détaillée | `GET /api/admin/health` | Oui | OK | Redis, services | Haute |
| Test Sentry | `GET /api/admin/sentry-test` | Oui | OK | `SENTRY_DSN` | Basse |
| Certificat d’autonomie | `GET /api/admin/certificate` | Oui | OK | disque (`data/certificates`) | Moyenne |

### 9.2 Setup exploitant
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Page setup | `/setup` | Oui | OK | Aucune | Haute |
| État setup / PV | `GET /api/setup/status` | Oui | OK | `pv_recette` | Haute |
| Vérification phase A | `POST /api/setup/check-phase-a` | Oui | OK | `pv_recette` | Haute |
| Déclarations phase B | `POST /api/setup/check-phase-b` | Oui | OK | `pv_recette` | Haute |
| Vérification phase C | `POST /api/setup/check-phase-c` | Oui | OK | `pv_recette` | Haute |
| Vérification SIRET | `POST /api/setup/check-siret` | Oui | OK | API gouv.fr | Haute |
| Signer PV | `POST /api/setup/sign-pv` | Oui | OK | `pv_recette`, `.env` | Critique |
| Chat Setup AI | `POST /api/setup/ai-chat` | Oui | Partiel | `SETUP_OPENAI_API_KEY` | Moyenne |
| Sauvegarde config | `POST /api/setup/save-config` | Oui | OK | `.env`, `pv_recette` | Haute |
| État wizard | `GET /api/setup/wizard-state` | Oui | OK | `.wizard_state.json` | Moyenne |
| Test service | `POST /api/setup/test-service` | Oui | OK | `pv_recette` | Moyenne |
| Génération sécurité (JWT + SSL) | `POST /api/setup/generate-security` | Oui | OK | openssl, `.env` | Haute |

### 9.3 Licenses exploitant
| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Activation licence | `POST /api/license/activate` | Oui | OK | `JWT_SECRET_KEY`, fichier licence | Haute |
| Heartbeat licence | `POST /api/license/heartbeat` | Oui | OK | `JWT_SECRET_KEY`, fichier licence | Haute |
| Liste licences admin | `GET /api/admin/licenses` | Oui | OK | `ADMIN_PASSWORD` | Haute |
| Création licence | `POST /api/admin/licenses` | Oui | OK | `ADMIN_PASSWORD` | Haute |
| Bloquer / débloquer licence | `POST /api/admin/licenses/{email}/block|unblock` | Oui | OK | `ADMIN_PASSWORD` | Haute |
| Supprimer licence | `DELETE /api/admin/licenses/{email}` | Oui | OK | `ADMIN_PASSWORD` | Haute |

**Remarques** :
- Le serveur est en mode “setup only” (`_pv_locked`) tant que le PV n’est pas signé.
- `SETUP_OPENAI_API_KEY` est détruite après signature du PV.
- La licence est optionnelle sur l’instance fondateur mais bloquante si `_license_heartbeat.is_blocked()`.

---

## 10. Health / Monitoring

| Fonction | URL | Existe ? | Fonctionne ? | Dépendance | Priorité |
|----------|-----|----------|--------------|------------|----------|
| Healthcheck léger | `GET /health` | Oui | OK | Aucune | Critique |
| Readiness (Redis + secrets) | `GET /ready` | Oui | OK | Redis, `JWT_SECRET_KEY`, OpenAI | Critique |
| Mode maintenance | `GET /api/maintenance`, `POST /api/admin/maintenance` | Oui | OK | Redis | Haute |
| Logs client | `POST /api/logs/client` | Oui | OK | Aucune | Moyenne |
| Stream logs | `GET /api/logs/stream` | Oui | OK | Mémoire interne | Moyenne |
| Buffer logs | `GET/DELETE /api/logs/buffer` | Oui | OK | Mémoire interne | Moyenne |
| Page logs | `/logs` | Oui | OK | JWT admin | Moyenne |
| État services (debug) | `GET /api/debug/services-mode` | Oui | OK | Intégrations | Haute |
| Sessions Iris debug | `GET /api/debug/iris/sessions`, `/api/debug/iris/session/{filename}` | Oui | OK | `/tmp/iris_sessions` | Moyenne |
| Objectifs auto-diagnostic | `GET /api/admin/objectives` | Oui | OK | Redis, tous les modules | Haute |
| Alertes admin automatiques | `_notify_admin_health` | Oui | Partiel | Telegram (`ALERT_TELEGRAM_BOT_TOKEN`) | Haute |

**Remarques** :
- L’alerte admin est envoyée par Telegram en priorité ; le fallback SMS est désactivé pour protéger le crédit Twilio.
- Sentry est initialisé si `SENTRY_DSN` est présent.

---

## Synthèse par module

| Module | État global | Risques principaux |
|--------|-------------|--------------------|
| **Auth / Compte** | ✅ OK | Checkout Stripe optionnel. |
| **Chat / Assistant IA** | ✅ OK / ⚠️ Partiel | Dépend fortement d’OpenAI/Anthropic ; les tools actionnent des services externes parfois non configurés. |
| **Contacts / Famille / Social** | ✅ OK / ⚠️ Partiel | Fonctionne en interne ; invitations SMS et OTP famille nécessitent Twilio. |
| **Instructions / Scheduler** | ✅ OK | Nécessite Redis et le module `core`. |
| **Guardian** | ✅ OK / ⚠️ Partiel | Core OK ; SOS et alertes SMS dépendent de Twilio et de contacts d’urgence. |
| **Secrétaire / Documents** | ✅ OK / ⚠️ Partiel | Vault + secretary fonctionnels ; scan IA dépend d’OpenAI Vision. |
| **Visio / Appels** | ⚠️ Partiel / ❌ Simli KO | Tavus fonctionne si configuré ; Simli désactivé ; voice-call et Iris temps réel nécessitent Twilio + OpenAI Realtime + URLs publiques. |
| **Paiements / Stripe** | ⚠️ Partiel | Webhooks + clés requises ; non fonctionnel sans configuration Stripe. |
| **Admin / Setup / Licenses** | ✅ OK / ⚠️ Partiel | Setup dépend du module `pv_recette` ; licences fonctionnent si le serveur est déverrouillé. |
| **Health / Monitoring** | ✅ OK | Peut alerter via Telegram ; fallback SMS désactivé. |

---

## Dépendances critiques récapitulatives

| Dépendance | Utilisée par | Obligatoire au boot ? |
|------------|--------------|-----------------------|
| `JWT_SECRET_KEY` | Auth, admin, licences | Oui (SystemExit si manquant) |
| `OPENAI_API_KEY` / `LLM_API_KEY` | Chat, greeting, visio, documents, voice | Oui en mode production |
| `REDIS_URL` | Mémoire, auth, guardian, social, etc. | Non (graceful fallback) |
| `ADMIN_NUMBER` | Appels, SMS admin | Oui en mode production |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | SMS, appels vocaux | Non (optionnel) |
| `TAVUS_API_KEY`, `TAVUS_LUNA_PERSONA_ID` | Visio premium | Non (mode `lite` possible) |
| `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET` | Paiements | Non |
| `SENTRY_DSN` | Monitoring | Non |
| `ALERT_TELEGRAM_BOT_TOKEN` | Alertes admin | Non |

---

## Recommandations prioritaires

1. **Valider la chaîne Twilio** (SMS + Voice + webhooks publics) : c’est le socle des alertes Guardian, des invitations et des appels vocaux.
2. **Tester `/api/call` et `/api/voice-call` en conditions réelles** : les dépendances OpenAI Realtime + Twilio + URLs publiques sont nombreuses.
3. **Activer ou retirer Simli** : actuellement désactivé mais toujours référencé comme fallback dans `/api/call`, ce qui peut créer des erreurs 503 pour les plans non-premium.
4. **Configurer Stripe** (clés + webhooks) avant tout lancement commercial.
5. **Vérifier le module `pv_recette`** : le setup et la signature du PV en dépendent ; s’il est manquant, le setup est inutilisable.
6. **Surveiller le health auto-diagnostic** via `/api/admin/objectives` : il donne une vue rapide de l’état de chaque domaine.
