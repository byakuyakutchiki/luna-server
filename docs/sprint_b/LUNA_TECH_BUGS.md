# LUNA_TECH_BUGS.md — Audit technique Infrastructure / Backend / Intégrations

**Rôle :** Responsable Infrastructure / Backend / Intégrations  
**Mission :** Identifier les causes techniques des dysfonctionnements, proposer des correctifs.  
**Méthode :** lecture de code, démarrage local, tests d'endpoints, logs. Aucun code modifié.  
**Date :** 2026-06-14

---

## Synthèse technique

YAWatch-LUNA est un monolithe FastAPI très dense. La majorité des dysfonctionnements ne viennent pas d'une absence de code, mais de :

1. **Mauvais câblage entre modules** (noms de méthodes incorrects, services non injectés).
2. **Dépendances tierces non configurées** (OpenAI, Twilio, SendGrid, Tavus, Duffel, Serper, etc.).
3. **Gestion d'erreurs opaque** (OpenAI 401 masqué derrière "souci technique").
4. **Incohérences de packaging** (Dockerfile Cloud Run sans OpenCV/Ultralytics).
5. **Verrou central manquant** (module `pv_recette` absent).

---

## 1. OpenAI — Chat central et assistant IA

### 1.1 Chat texte mort en l'absence de clé valide

- **Fonction :** Chat texte (`POST /api/chat`) et greeting (`GET /api/greeting`).
- **Cause technique :** `luna_web.py` appelle `openai_client.chat.completions.create` sans vérifier préalablement la validité de la clé. Lorsque OpenAI retourne une `AuthenticationError`, le code capture l'exception et retourne un message générique "Luna a un souci technique". Le circuit breaker est incrémenté mais l'utilisateur n'a aucune information exploitable.
- **Fichier concerné :** `luna_web.py:6512-6516` et `:6579-6589`.
- **Correctif proposé :**
  1. Au démarrage, vérifier la clé OpenAI avec un appel de test léger (`/models` ou ping).
  2. Si la clé est invalide, logger critique ET exposer un statut `/health` dégradé.
  3. Dans `/api/chat`, retourner un message explicite du type : *"Luna n'est pas encore configurée. Veuillez vérifier la clé OpenAI."*
  4. Dégrader gracieusement : si OpenAI est KO, répondre avec les outils locaux (météo, profil, notes) sans génération LLM.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que l'application ne vérifie pas la validité de la clé OpenAI au démarrage et masque l'erreur 401 derrière un message générique.

### 1.2 Gestion des erreurs OpenAI non différenciée

- **Fonction :** Tous les appels OpenAI.
- **Cause technique :** Le code capture `openai.AuthenticationError`, `RateLimitError`, `APIConnectionError` séparément, mais toutes les autres erreurs (timeout, bad request, content filter) tombent dans le `except Exception` générique qui retourne "Luna a rencontre un petit probleme".
- **Fichier concerné :** `luna_web.py:6531-6537`.
- **Correctif proposé :** Ajouter la gestion explicite de `openai.BadRequestError`, `openai.APITimeoutError`, et loguer le `type(e).__name__` + le message tronqué côté serveur.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que les erreurs OpenAI non prévues sont englouties par un `except Exception` qui ne transmet aucune information diagnostique.

### 1.3 `openai_client` initialisé globalement sans fallback

- **Fonction :** Client OpenAI.
- **Cause technique :** `openai_client = OpenAI(api_key=OPENAI_API_KEY)` est créé au chargement du module. Si `OPENAI_API_KEY` est vide, le client existe mais toutes les requêtes échoueront.
- **Fichier concerné :** `luna_web.py` (import initial d'`openai`).
- **Correctif proposé :** Initialiser le client de manière lazy, ou vérifier `OPENAI_API_KEY` au démarrage et passer l'application en mode dégradé si absent.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le client OpenAI est instancié avant toute validation de la clé, sans mode dégradé.

---

## 2. Twilio / SMS

### 2.1 `ActionDispatcher` appelle une méthode inexistante `send_sms`

- **Fonction :** Exécution d'une action SMS confirmée.
- **Cause technique :** `ActionDispatcher._execute_sms` appelle `await self.sms.send_sms(request.tenant_id, phone, body)`. Or `self.sms` est une instance de `TwilioSMSClient`, qui expose une méthode `send(to, body)` mais pas `send_sms`. De plus, `TwilioSMSClient.send` ne prend pas de paramètre `tenant_id`.
- **Fichier concerné :** `core/actions/dispatcher.py:234-238`.
- **Correctif proposé :** Remplacer par `success, result = await asyncio.to_thread(self.sms.send, phone, body)` (car `TwilioSMSClient.send` n'est pas async).
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le dispatcher appelle `send_sms()` sur `TwilioSMSClient`, qui ne possède que la méthode `send()`.

### 2.2 Vault reminders appellent aussi `send_sms` inexistant

- **Fonction :** Rappels SMS depuis le Vault (`_vault_reminders_loop`).
- **Cause technique :** `sms_client.send_sms(phone, f"Luna 📄 {msg}")` est appelé, mais `TwilioSMSClient` n'a pas de méthode `send_sms`.
- **Fichier concerné :** `luna_web.py:4410`.
- **Correctif proposé :** Remplacer par `sms_client.send(phone, f"Luna 📄 {msg}")`.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Même cause que 2.1 : appel à une méthode qui n'existe pas dans le client Twilio.

### 2.3 Méthode `send_sms` semble exister ailleurs mais n'est pas celle utilisée

- **Fonction :** Contrôle de cohérence.
- **Cause technique :** Un grep montre `sms_client.send_sms` dans `luna_web.py:4410` et `self.sms.send_sms` dans `core/actions/dispatcher.py:236`. Aucun autre endroit ne définit `send_sms` sur `TwilioSMSClient`. Il s'agit probablement d'un reliquat d'une ancienne interface.
- **Fichier concerné :** `core/actions/dispatcher.py`, `luna_web.py:4410`.
- **Correctif proposé :** Supprimer tous les appels `send_sms` et uniformiser sur `TwilioSMSClient.send()`.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que plusieurs développeurs ont écrit du code contre une ancienne interface SMS qui n'existe plus.

### 2.4 `_tracked_sms_send` n'est pas async mais est appelée avec `await`

- **Fonction :** Envoi de SMS traçable.
- **Cause technique :** `_tracked_sms_send` dans `luna_web.py:3766-3784` est une fonction synchrone (elle appelle `sms_client.send(to, body)`). Pourtant elle est parfois appelée avec `await` dans des contextes async (ex: `_tool_send_sms`).
- **Fichier concerné :** `luna_web.py:3766-3784`, `luna_web.py:5340-5337`.
- **Correctif proposé :** Soit rendre `_tracked_sms_send` async en utilisant `asyncio.to_thread`, soit supprimer les `await` dans les appelants.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce qu'une fonction synchrone est appelée comme si elle était asynchrone, ce qui peut provoquer des `TypeError`.

---

## 3. ActionConfirmation / Instructions planifiées

### 3.1 `InstructionExecutor` appelle une méthode inexistante `create_action_request`

- **Fonction :** Demande de confirmation avant exécution d'une instruction planifiée.
- **Cause technique :** `core/instructions/executor.py:212` appelle `self.action_service.create_action_request(...)`. Le service injecté est censé être `ConfirmationManager` (classe `core/actions/confirmation.py`), qui expose `propose_action(...)`, pas `create_action_request`.
- **Fichier concerné :** `core/instructions/executor.py:208-218`, `core/actions/confirmation.py:52-64`.
- **Correctif proposé :** Remplacer `create_action_request` par `propose_action`, en adaptant les paramètres (`action_type` doit être un `ActionType`, pas une string ; `message_body` optionnel).
- **Complexité :** Moyenne (changement de signature).
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que l'executor appelle `create_action_request()` sur `ConfirmationManager`, qui ne possède que `propose_action()`.

### 3.2 `action_service` n'est jamais injecté dans `InstructionExecutor`

- **Fonction :** Confirmation des instructions planifiées.
- **Cause technique :** Dans `luna_web.py:3868-3874`, `create_instruction_executor` est appelé sans paramètre `action_service`. Donc `self.action_service` reste `None` dans `InstructionExecutor`, et la logique de confirmation est désactivée.
- **Fichier concerné :** `luna_web.py:3868-3874`, `core/instructions/executor.py:66`, `:1043-1069`.
- **Correctif proposé :** Créer un `ConfirmationManager` et le passer en `action_service` lors de l'appel à `create_instruction_executor`.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le service de confirmation n'est jamais injecté dans l'executor, donc la confirmation est silencieusement désactivée.

### 3.3 `ConfirmationManager` stocke les demandes en mémoire volatile

- **Fonction :** Persistance des actions en attente de confirmation.
- **Cause technique :** `self._pending: Dict[int, Dict[str, ActionRequest]]` est un dictionnaire Python en mémoire. Un redémarrage du serveur efface toutes les confirmations en attente.
- **Fichier concerné :** `core/actions/confirmation.py:43-50`.
- **Correctif proposé :** Utiliser Redis (ou la mémoire du `MemoryManager`) pour persister les `ActionRequest` et les statuts.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que les confirmations sont stockées en RAM et disparaissent à chaque redémarrage du process.

---

## 4. Appels téléphoniques et visioconférence

### 4.1 Appels téléphoniques explicitement désactivés

- **Fonction :** `call_contact`.
- **Cause technique :** `ActionDispatcher._execute_call` retourne systématiquement `feature_not_available`. Il n'y a aucun backend Twilio Voice pour initier un appel.
- **Fichier concerné :** `core/actions/dispatcher.py:267-274`.
- **Correctif proposé :** Soit implémenter l'appel via Twilio Voice (`twilio.rest.api.v2010.account.call.CallList.create`), soit retirer l'outil `call_contact` du prompt système et du front.
- **Complexité :** Élevée si implémentation, faible si retrait.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le backend renvoie `feature_not_available` : il n'y a pas d'intégration Twilio Voice.

### 4.2 Visioconférence explicitement désactivée

- **Fonction :** `invite_visio`.
- **Cause technique :** `ActionDispatcher._execute_visio` retourne `feature_not_available`. `_tool_invite_visio` dans `luna_web.py` existe mais nécessite `tavus_client.is_configured`, ce qui est rarement le cas.
- **Fichier concerné :** `core/actions/dispatcher.py:350-357`, `luna_web.py:16214-16284`.
- **Correctif proposé :** Décider si Tavus/Simli est maintenu. Si non, supprimer les routes `/api/visio/*`, les pages `simli.html`, et les outils `invite_visio`.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le dispatcher désactive la visio et le client Tavus est rarement configuré.

---

## 5. Guardian — GPS

### 5.1 Guardian GPS fonctionne mais est couplé à Redis

- **Fonction :** Démarrage et suivi GPS (`POST /api/guardian/start`).
- **Cause technique :** Le moteur Guardian est bien écrit (`core/guardian/engine.py`), mais son état est partiellement géré dans `_guardian_sessions` (dict global dans `luna_web.py`). En cas de redémarrage du serveur, les sessions actives sont perdues.
- **Fichier concerné :** `luna_web.py` (variable `_guardian_sessions`), `core/guardian/engine.py`.
- **Correctif proposé :** Persister les sessions Guardian actives dans Redis avec un TTL, et les restaurer au démarrage.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas (après redémarrage) ?  
  → Parce que les sessions actives sont stockées en mémoire dans `luna_web.py` et disparaissent au redémarrage.

### 5.2 Pas de vérification de permission de géolocalisation côté navigateur

- **Fonction :** Suivi GPS front.
- **Cause technique :** Le front suppose que le navigateur fournit la géolocalisation, mais il n'y a pas de gestion explicite du refus de permission. Si l'utilisateur refuse, le backend ne reçoit jamais de positions mais considère peut-être la session comme active.
- **Fichier concerné :** `static/guardian.html` ou `static/index.html` (onglet Guardian).
- **Correctif proposé :** Détecter `error.code === 1` (Permission denied) et arrêter la session Guardian côté serveur.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le refus de géolocalisation du navigateur n'est pas propagé au backend.

---

## 6. Guardian — Caméra / Perception

### 6.1 Perception caméra non installable sur Cloud Run

- **Fonction :** Analyse de frame caméra (`POST /api/visio/perception`, `POST /api/guardian/frame/{session_id}`).
- **Cause technique :** `PerceptionDetector` et `SceneAnalyzer` dépendent probablement d'`ultralytics` (YOLO) et/ou `opencv-python`. Le Dockerfile Cloud Run et `requirements-cloudrun.txt` n'incluent pas ces dépendances, donc `_perception_detector` reste non initialisé.
- **Fichier concerné :** `Dockerfile`, `requirements-cloudrun.txt`, `core/perception/detector.py` (si existant).
- **Correctif proposé :**
  1. Ajouter `ultralytics` et `opencv-python-headless` aux dépendances Cloud Run.
  2. Ou désactiver la perception en Cloud Run et documenter cette limitation.
  3. Ou déporter l'analyse image vers une API externe (OpenAI Vision, GCP Vision API).
- **Complexité :** Élevée (changement d'architecture) à moyenne (ajout deps).
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que les dépendances de détection d'objets (YOLO/OpenCV) ne sont pas installées dans l'image Cloud Run.

### 6.2 Route `/api/guardian/frame/{session_id}` utilise `core.perception` au lieu du moteur GPS

- **Fonction :** Frame Guardian.
- **Cause technique :** Le docstring de `core/guardian/engine.py` indique que Guardian est "GPS-only" et remplace la caméra. Pourtant une route `/api/guardian/frame/{session_id}` existe et semble dépendre de `core.perception`.
- **Fichier concerné :** `luna_web.py` (route Guardian frame), `core/guardian/engine.py:1-6`.
- **Correctif proposé :** Supprimer la route frame si Guardian est GPS-only, ou la documenter comme une fonctionnalité expérimentale nécessitant une installation séparée.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que la route frame est incohérente avec l'architecture GPS-only de Guardian.

---

## 7. Email

### 7.1 Email SendGrid non configuré par défaut

- **Fonction :** Envoi d'email (`_tool_send_email`).
- **Cause technique :** `EmailClient.from_env()` nécessite `SENDGRID_API_KEY` et `LUNA_EMAIL_FROM`. Sans ces variables, `email_client.is_configured` est `False` et `_tool_send_email` retourne *"Aucun service email configure"*.
- **Fichier concerné :** `integrations/email/email_client.py:54-72`, `luna_web.py:16138-16140`.
- **Correctif proposé :** Documenter clairement les variables requises dans `.env.example`. En mode `FOUNDATION_TEST_MODE`, sauvegarder l'email localement (déjà fait) mais informer l'utilisateur.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que les variables d'environnement SendGrid ne sont pas configurées.

### 7.2 Gmail OAuth non configuré par défaut

- **Fonction :** Envoi d'email via Gmail OAuth.
- **Cause technique :** `_tool_send_email` tente d'utiliser `gmail_client` si une intégration email est stockée dans Redis. `gmail_client` est probablement `None` ou non configuré au démarrage.
- **Fichier concerné :** `luna_web.py:16138`, `integrations/google/gmail_client.py` (si existant).
- **Correctif proposé :** Uniformiser le fallback : si Gmail OAuth n'est pas configuré, utiliser SendGrid ; si SendGrid n'est pas configuré, mode brouillon local.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que Gmail OAuth nécessite un flux OAuth et une configuration Google Cloud non fournie par défaut.

---

## 8. Auth / JWT

### 8.1 JWT_SECRET_KEY obligatoire mais absent de `.env.example`

- **Fonction :** Création et vérification des tokens JWT.
- **Cause technique :** `JWT_SECRET_KEY` est requis au démarrage (`ERREUR FATALE: JWT_SECRET_KEY manquante dans .env`). Pourtant `.env.example` ne le contient pas.
- **Fichier concerné :** `.env.example`, `luna_web.py` (au chargement).
- **Correctif proposé :** Ajouter `JWT_SECRET_KEY=change-me-in-production` dans `.env.example` et documenter qu'il doit être long et aléatoire.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que la clé JWT n'est pas fournie dans le template `.env.example` et est exigée au démarrage.

### 8.2 Fallback fondateur basé sur un mot de passe en clair dans `.env`

- **Fonction :** Authentification admin/fondateur.
- **Cause technique :** Si Redis est indisponible, l'authentification fondateur utilise `PROPRIO_EMAIL` et `PROPRIO_PASSWORD` depuis `.env`. `PROPRIO_PASSWORD` est en clair.
- **Fichier concerné :** `luna_web.py:11690-11697`.
- **Correctif proposé :** Stocker un hash du mot de passe fondateur dans `.env` (`PROPRIO_PASSWORD_HASH`) et utiliser `_verify_password`. Conserver le fallback Redis comme primaire.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas (de manière sécurisée) ?  
  → Parce que le fallback fondateur lit un mot de passe en clair depuis les variables d'environnement.

### 8.3 Tokens JWT à durée de vie très longue

- **Fonction :** Sessions utilisateur.
- **Cause technique :** `_create_client_token` crée des tokens avec `timedelta(days=90)` (3 mois).
- **Fichier concerné :** `luna_web.py` (fonction `_create_client_token`).
- **Correctif proposé :** Réduire la durée à 24h-7j et implémenter un refresh token.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ce n'est pas sécurisé ?  
  → Parce que les tokens JWT sont valables 90 jours, ce qui augmente la fenêtre d'exposition en cas de fuite.

---

## 9. Redis

### 9.1 Redis fallback en mémoire sans persistance

- **Fonction :** Persistance des données utilisateur.
- **Cause technique :** Si `REDIS_URL` n'est pas configuré, l'application crée un `FakeRedis` en mémoire. Toutes les données (profils, contacts, conversations, sessions Guardian, instructions) disparaissent au redémarrage.
- **Fichier concerné :** `luna_web.py` (initialisation `_redis_client`), `core/memory/redis_client.py`.
- **Correctif proposé :** Soit rendre `REDIS_URL` obligatoire au démarrage, soit utiliser une base SQLite locale en fallback avec persistance sur disque.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas (après redémarrage) ?  
  → Parce qu'en l'absence de `REDIS_URL`, Luna utilise un Redis simulé en mémoire qui ne persiste rien.

### 9.2 Clés Redis non préfixées par environnement

- **Fonction :** Isolation des données.
- **Cause technique :** Les clés Redis utilisent un préfixe `luna:{tenant_id}:...` sans distinguer dev/staging/prod. Une mauvaise configuration peut faire croiser les données entre environnements.
- **Fichier concerné :** `core/memory/redis_client.py`, divers fichiers `core/**/redis_ops.py`.
- **Correctif proposé :** Ajouter un préfixe d'environnement (`LUNA_ENV` ou `SERVICE_NAME`) aux clés Redis.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ce n'est pas sûr ?  
  → Parce que les clés Redis n'indiquent pas l'environnement, risquant de mélanger dev/prod.

---

## 10. Cloud Run / Déploiement

### 10.1 `requirements-cloudrun.txt` ne contient pas les dépendances Guardian perception

- **Fonction :** Détection caméra / perception.
- **Cause technique :** `requirements-cloudrun.txt` est allégé pour Cloud Run et exclut `ultralytics`/`opencv-python-headless`. Par conséquent, `_perception_detector` ne s'initialise pas.
- **Fichier concerné :** `requirements-cloudrun.txt`, `Dockerfile`.
- **Correctif proposé :** Ajouter les dépendances perception dans `requirements-cloudrun.txt` OU supprimer la perception du build Cloud Run et la gérer via un service séparé.
- **Complexité :** Moyenne.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que l'image Cloud Run est construite sans les bibliothèques de vision nécessaires.

### 10.2 Dockerfile expose HTTP mais l'application démarre en HTTPS self-signed

- **Fonction :** Déploiement Cloud Run.
- **Cause technique :** `Dockerfile` expose le port 8080 et `luna_web.py` semble démarrer un serveur HTTPS avec certificats auto-signés (`ssl_keyfile`, `ssl_certfile`) si disponibles. Cloud Run attend du HTTP.
- **Fichier concerné :** `Dockerfile`, `luna_web.py` (appel `uvicorn.run`).
- **Correctif proposé :** S'assurer que le mode Cloud Run force le HTTP (terminaison TLS gérée par Cloud Run) ou utiliser `uvicorn` sans `ssl_keyfile`/`ssl_certfile`.
- **Complexité :** Faible.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le serveur démarre potentiellement en HTTPS self-signed alors que Cloud Run attend du HTTP.

### 10.3 Taille de l'image Docker potentiellement énorme

- **Fonction :** Build et déploiement.
- **Cause technique :** Le projet embarque beaucoup de dépendances lourdes (torch potentiel, opencv, ultralytics, transformers, etc.). L'image peut dépasser les limites Cloud Run.
- **Fichier concerné :** `Dockerfile`, `requirements-cloudrun.txt`.
- **Correctif proposé :** Audit des dépendances, utiliser des images de base légères, séparer les services lourds (vision) en microservices.
- **Complexité :** Élevée.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que l'image Docker risque d'être trop volumineuse pour Cloud Run si toutes les dépendances ML sont incluses.

---

## 11. APIs tierces / Conciergerie

### 11.1 `search_web` non configuré

- **Fonction :** Recherche web concierge.
- **Cause technique :** `POST /api/concierge/action` action `search_web` retourne "Service de recherche non configure". La clé `SERPER_API_KEY` ou `SERPAPI_API_KEY` n'est pas définie.
- **Fichier concerné :** `luna_web.py` (route concierge), `integrations/search/serper_client.py` (si existant).
- **Correctif proposé :** Ajouter `SERPER_API_KEY` dans `.env.example` et documenter le fournisseur requis.
- **Complexité :** Faible.

### 11.2 Réservations vols/hôtels/restaurants nécessitent des clés externes

- **Fonction :** Conciergerie réservation.
- **Cause technique :** Les actions `search_flights`, `search_hotels`, `book_restaurant` dépendent de Duffel, Booking/Affiliate, Google Places. Ces clés sont optionnelles.
- **Fichier concerné :** `core/concierge/services/`, `integrations/duffel/`, `integrations/google/places.py`.
- **Correctif proposé :** Implémenter un mode "brouillon" : l'outil recherche et prépare une réservation, mais affiche un récapitulatif à l'utilisateur sans appel API payant.
- **Complexité :** Moyenne.

### 11.3 API météo fonctionne mais sans clé explicite

- **Fonction :** Météo.
- **Cause technique :** L'endpoint `/api/weather` fonctionne (test réussi). Il utilise probablement un service public sans clé.
- **Fichier concerné :** `luna_web.py` (route weather).
- **Correctif proposé :** Aucun correctif critique, mais monitorer la disponibilité du service tiers.
- **Complexité :** N/A.

---

## 12. PV de recette / Setup

### 12.1 Module `pv_recette` absent

- **Fonction :** Verrouillage initial du serveur.
- **Cause technique :** Le code importe `pv_recette` au démarrage. Si le module n'est pas installé, il fallback sur `.env`. Le setup n'est jamais signable correctement.
- **Fichier concerné :** `luna_web.py` (import au démarrage), `core/pv_recette/` (absent).
- **Correctif proposé :** Livrer le module `pv_recette` OU remplacer le mécanisme par un simple flag `PV_SIGNED=true` en mode développement.
- **Complexité :** Faible si suppression du mécanisme, élevée si implémentation complète du PV.
- **Question unique :** Pourquoi ça ne fonctionne pas ?  
  → Parce que le module chargé de signer le PV de recette n'existe pas dans ce dépôt.

---

## 13. Tests et observabilité

### 13.1 Aucune suite de tests automatisée

- **Fonction :** Qualité et non-régression.
- **Cause technique :** Seuls 3 scripts de test isolés existent (`test_luna_sms.py`, `tools/test_iris_ws.py`, `tools/test_llm_providers.py`). Pas de `tests/`, pas de `pytest.ini`.
- **Fichier concerné :** Racine du projet.
- **Correctif proposé :** Créer une suite pytest couvrant les modules critiques : auth, guardian, instructions, actions, concierge.
- **Complexité :** Moyenne.

### 13.2 Logs mélangés et verbeux

- **Fonction :** Observabilité.
- **Cause technique :** Les logs contiennent des messages en français et en anglais, des niveaux mélangés, et certaines erreurs critiques sont loguées en `warning`.
- **Fichier concerné :** Tous les fichiers `core/` et `luna_web.py`.
- **Correctif proposé :** Standardiser les logs en anglais, utiliser des niveaux cohérents, structurer les logs JSON en production.
- **Complexité :** Faible.

---

## Tableau récapitulatif des correctifs prioritaires

| Priorité | Fonction | Fichier | Complexité | Correctif clé |
|----------|----------|---------|------------|---------------|
| P0 | Chat OpenAI | `luna_web.py` | Faible | Vérifier clé au démarrage, message d'erreur explicite |
| P0 | SMS dispatcher | `core/actions/dispatcher.py` | Faible | Remplacer `send_sms` par `send` |
| P0 | Vault reminders SMS | `luna_web.py:4410` | Faible | Remplacer `send_sms` par `send` |
| P0 | Confirmation instructions | `core/instructions/executor.py`, `luna_web.py` | Moyenne | Injecter `ConfirmationManager` et utiliser `propose_action` |
| P0 | PV de recette | `luna_web.py` | Faible | Supprimer ou livrer le module |
| P1 | Persistance Redis fallback | `luna_web.py` | Moyenne | Rendre Redis obligatoire ou utiliser SQLite |
| P1 | Perception caméra Cloud Run | `Dockerfile`, `requirements-cloudrun.txt` | Moyenne/Élevée | Ajouter deps ou séparer service |
| P1 | Tests | Racine | Moyenne | Créer suite pytest |
| P2 | JWT secret | `.env.example` | Faible | Ajouter `JWT_SECRET_KEY` |
| P2 | Password fondateur | `luna_web.py` | Faible | Utiliser un hash |
| P2 | TTL JWT | `luna_web.py` | Moyenne | Réduire à 24h-7j + refresh |

---

## Conclusion technique

Le produit a une **architecture solide** (FastAPI, Redis, scheduler, safety, guardian) mais souffre de **défauts d'intégration** et d'un **manque de robustesse aux dépendances externes**. Les correctifs P0 sont rapides (changements de noms de méthodes, injection de services, messages d'erreur). Les correctifs P1/P2 nécessitent des décisions produit (statut de la visio, persistance, découpage Cloud Run).

**La question centrale reste :** *Pourquoi ça ne fonctionne pas ?*  
Parce que le code est là, mais les pièces ne sont pas correctement assemblées ou configurées.
