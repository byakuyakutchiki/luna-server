# Luna — Cahier des Charges : Objectifs Fonctionnels & Monitoring

> **Version** : 1.0 — Mai 2026  
> **Auteur** : Ludo (Fondateur YAWatch)  
> **Périmètre** : Serveur fondateur `luna-beta` + package exploitant  
> **Principe** : Chaque onglet a un objectif mesurable. Le monitoring vérifie si l'objectif est **réellement atteint**, pas seulement si le serveur est actif.

---

## Philosophie

Luna n'est pas un chatbot. C'est un **compagnon de vie** : il agit, anticipe, protège et connecte. Chaque onglet représente un domaine de vie réel. Le monitoring doit répondre à une question simple :

> **"Est-ce que cette fonctionnalité tient sa promesse à l'utilisateur ?"**

Un onglet est **OK** seulement si l'utilisateur peut accomplir son objectif de bout en bout.

---

## Structure de chaque objectif

| Champ | Description |
|---|---|
| **Objectif** | Ce que l'utilisateur obtient concrètement |
| **Étapes obligatoires** | Ce qui doit fonctionner pour que l'objectif soit atteint |
| **Points de contrôle** | Métriques et vérifications du monitoring |
| **Erreurs possibles** | Causes de défaillance identifiées |
| **Réparation automatique** | Action déclenchée sans intervention humaine |
| **Réparation semi-auto** | Alerte avec suggestion de correction |

---

## 1. Système — Infrastructure

**Objectif** : Le serveur est opérationnel, la mémoire partagée est accessible, les boucles de fond tournent.

### Étapes obligatoires
- Redis Upstash connecté et répondant (`PING` → `PONG`)
- Variables d'environnement critiques chargées
- Boucles async actives (objectives monitor, vault reminders, TG alerts)

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| `Redis.ping()` | 30s (cachée) | Timeout > 2s |
| Mémoire process | 5 min | > 512 MB |
| Uptime Cloud Run | Continue (GCP) | Indisponibilité > 1 min |
| `/health` HTTP 200 | 60s (GCP Uptime Check) | 2 échecs consécutifs |

### Erreurs possibles
- Quota Upstash dépassé (500K req/mois gratuit)
- Cold start Cloud Run > 10s
- Fuite mémoire sur longue session SSE

### Réparation automatique
- `_redis_available()` cache 30s → évite les cascades d'échec
- GCP redémarre automatiquement les instances en erreur
- Circuit breaker sur toutes les routes Redis (`try/except` systématique)

---

## 2. Connexion — Authentification

**Objectif** : L'utilisateur se connecte à son espace Luna et son identité est reconnue sur tous ses appareils.

### Étapes obligatoires
- Compte (email + mot de passe hashé) stocké en Redis
- JWT signé avec `JWT_SECRET_KEY`
- Token valide 30 jours, renouvelé automatiquement
- Plan (`fondateur`, `premium`, `confort`, `essentiel`) attaché au token

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Compte proprio en Redis | À chaque check objectives | Absent |
| JWT décodable | À chaque requête | Erreur 401 |
| Plan cohérent dans le token | À chaque check | Plan inconnu |

### Erreurs possibles
- `JWT_SECRET_KEY` changée → tous les tokens invalidés
- Redis flush → compte perdu
- Mauvais email/password dans `.env`

### Réparation automatique
- Token expiré → refresh automatique côté client
- Compte manquant → alerte SMS fondateur immédiate

### Réparation semi-auto
- Alerte : "Compte proprio introuvable en Redis — relancer `wizard_install.py`"

---

## 3. Chat — Conversation IA

**Objectif** : L'utilisateur échange avec Luna en langage naturel, Luna comprend le contexte, la mémoire, et répond de façon personnalisée.

### Étapes obligatoires
- Clé `ANTHROPIC_KEY_CHAT` valide et créditée
- Memory Manager chargé pour le tenant (historique, profil, instructions)
- Réponse en streaming SSE < 3s premier token
- Outils (météo, documents, rappels, actualités) exécutables depuis le chat

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Clé Anthropic initialisée | Chaque check | Absente |
| Memory Manager tenant actif | Chaque check | Non initialisé |
| Latence premier token | Monitoring Sentry | > 5s |
| Taux d'erreur 500 sur `/api/chat` | Sentry | > 1% sur 5 min |

### Erreurs possibles
- Quota Anthropic dépassé (HTTP 429)
- Contexte mémoire corrompu
- SSE coupé par Cloud Run (timeout 60s)

### Réparation automatique
- Fallback vers `gpt-4o-mini` si Anthropic KO (si clé OpenAI disponible)
- Retry automatique x3 sur 429

### Réparation semi-auto
- Alerte : "Anthropic 429 — vérifier quota sur console.anthropic.com"

---

## 4. Services / Concierge — Actions Déléguées

**Objectif** : Luna agit concrètement pour l'utilisateur depuis l'onglet Services / Conciergerie : contacter quelqu'un, rechercher une information, trouver un lieu, préparer un déplacement, produire un document, ou initier une transaction, avec confirmation et traçabilité.

Un service est **OK** seulement si Luna peut aller plus loin qu'une réponse texte : elle doit appeler le bon outil, recevoir un résultat exploitable, l'expliquer à l'utilisateur, et enregistrer l'action quand cela engage la mémoire, un contact, un paiement ou un déplacement.

### Sous-objectifs couverts

| Sous-service | Objectif utilisateur | Outil / dépendance | Preuve de réussite |
|---|---|---|---|
| SMS | Envoyer un message à un contact fiable | Twilio, contacts Redis | SID Twilio créé ou message mis en file d'attente |
| Appel vocal | Appeler un contact ou numéro autorisé | Twilio Voice | Call SID créé, numéros d'urgence bloqués |
| Email | Préparer ou envoyer un email | SMTP/API email, contacts | Email envoyé ou brouillon explicite si SMTP absent |
| Invitation visio | Inviter un contact dans une visio | SMS + lien session | Lien envoyé au bon contact |
| Compte-rendu / conclusions | Générer et transmettre un résumé structuré | DocumentGenerator + SMS/email | Document créé et destinataires notifiés |
| Note / mémoire | Sauvegarder une note utile | Memory Manager / Redis | Note persistée avec contexte et tags |
| Météo | Donner une météo actuelle et prévisionnelle | wttr.in + fallback Open-Meteo | Ville résolue, météo actuelle + 3 jours |
| Actualités | Donner des nouvelles récentes | Flux RSS | Articles datés et sourcés |
| Recherche web | Chercher une réponse vérifiable | Serper API | Résultats avec titres, extraits, liens |
| Lieux / commerces | Trouver restaurants, pharmacies, hôtels, services proches | Serper Places + géoloc/profil | Adresses, notes, téléphone, itinéraire |
| Page web | Résumer une URL donnée | HTTP fetch + parsing HTML | Titre, résumé, contenu lisible ou erreur claire |
| Paiement | Demander un paiement sécurisé | Stripe | PaymentIntent / Checkout créé ou Stripe déclaré optionnel |
| Vols | Rechercher des vols | Duffel API | Offres disponibles, prix, compagnie, horaires |
| Hôtels | Rechercher des hôtels | Duffel Stays API | Offres disponibles, prix, dates, conditions |
| Restaurant | Proposer un restaurant réservable | Places / recherche web | Options classées + téléphone/lien/réservation si disponible |
| Secrétariat | Lire budget, dépenses, rappels, documents | Secretary Redis ops | Données lues et action enregistrée |

### Étapes obligatoires

- Catalogue d'outils déclaré dans `_SIMLI_TOOLS` et cohérent avec le dispatcher Tavus / Simli.
- Chaque outil appelé doit retourner un JSON normalisé : `status`, `message`, et données métier (`results`, `places`, `articles`, `offers`, etc.).
- Les actions engageantes (SMS, appel, paiement, réservation, alerte contacts) doivent exiger confirmation ou respecter une règle de sécurité explicite.
- Les dépendances externes doivent être détectées séparément : Twilio, Serper, Stripe, Duffel, flux RSS, météo gratuite, Redis, DocumentGenerator.
- Les actions qui créent de la valeur durable doivent être persistées : note, recherche importante, paiement, document, invitation, instruction.
- Les services optionnels non configurés ne doivent pas faire tomber tout l'onglet : ils doivent remonter `warning` ou `degraded` avec solution.

### Points de contrôle globaux

| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Catalogue `_SIMLI_TOOLS` chargé | Chaque check | Absent ou vide |
| Dispatcher tool-call actif | Chaque check | Erreur import / route KO |
| Memory Manager disponible | Chaque check | Non initialisé |
| Redis disponible pour logs/actions | Chaque check | Erreur Redis |
| Format JSON des outils | À chaque appel outil | Pas de `status` |
| Taux d'erreur outil global | Sentry / logs | > 5% sur 15 min |
| Latence outil globale | Sentry / logs | > 10s hors vols/hôtels |

### Points de contrôle par sous-service

| Sous-service | Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|---|
| SMS | Credentials Twilio + numéro émetteur | Chaque check | Manquant |
| SMS | Taux livraison SMS | 15 min / webhook | > 5% failed |
| Appel vocal | Twilio Voice configuré | Chaque check | Manquant |
| Appel vocal | Blocage numéros d'urgence | Test quotidien | Échec blocage |
| Email | SMTP/API configuré ou mode brouillon assumé | Chaque check | Ambigu |
| Invitation visio | Lien session disponible + SMS OK | Chaque check | Lien/SMS KO |
| Conclusions | Générateur document disponible | Chaque check | Import KO |
| Météo | wttr.in répond ou Open-Meteo fallback répond | 15 min | 2 échecs consécutifs |
| Actualités | Au moins un flux RSS répond | 30 min | 0 article |
| Recherche web | `SERPER_API_KEY` présente | Chaque check | Manquante |
| Recherche web | Appel Serper search réussi | 15 min | 2 échecs consécutifs |
| Lieux/restaurants | Appel Serper Places réussi | 15 min | 2 échecs consécutifs |
| Page web | HTTP fetch + parsing HTML | À chaque appel | Timeout / contenu vide |
| Paiement | Stripe configuré selon environnement | Chaque check | Manquant en mode exploitant |
| Vols | `DUFFEL_ACCESS_TOKEN` présent si service activé | Chaque check | Manquant |
| Vols | Ratio search/order Duffel | Quotidien | > 1500:1 |
| Hôtels | Duffel Stays disponible si activé | Chaque check | Manquant |
| Restaurant | Options avec téléphone/lien/adresse | À chaque appel | 0 option exploitable |
| Secrétariat | Budget/rappels/docs lisibles | Chaque check | Erreur Redis |

### Règles de statut

| Statut | Condition |
|---|---|
| `ok` | Tous les services critiques configurés, et les services gratuits/fallback répondent |
| `warning` | Service optionnel absent mais l'utilisateur reçoit une explication claire |
| `degraded` | Sous-service disponible partiellement (ex : recherche lieux OK mais réservation directe absente) |
| `critical` | Action essentielle impossible : Redis KO, dispatcher KO, Twilio KO pour SMS/appels, ou outil engageant sans garde-fou |

### Erreurs possibles

- `SERPER_API_KEY` absente → recherche web, lieux et restaurants indisponibles.
- Twilio configuré partiellement → SMS/appels échouent après validation utilisateur.
- Flux RSS indisponibles → actualités vides.
- wttr.in lent ou bloqué → bascule nécessaire vers Open-Meteo.
- Duffel absent ou KYC non finalisé → vols/hôtels limités à une recherche simulée ou désactivés.
- Stripe absent sur serveur fondateur → normal si pas en mode exploitant, KO si paiement client attendu.
- Géolocalisation absente → restaurants/lieux moins pertinents.
- Tool-call halluciné par l'IA → nom d'outil inconnu ou arguments incomplets.
- Réservation/paiement déclenché sans confirmation → risque critique.
- Résultat externe vide → Luna doit l'expliquer, pas inventer.

### Réparation automatique

- Météo : fallback automatique wttr.in → Open-Meteo.
- SMS : mise en file Redis si Twilio momentanément indisponible.
- Recherche locale : enrichissement automatique par ville du profil ou dernière géolocalisation.
- Tool-call incomplet : demander les champs manquants avant action.
- Page web : timeout court + résumé d'erreur propre au lieu d'un crash.
- Service optionnel absent : désactiver seulement le sous-service concerné, pas tout l'onglet.
- Vols/hôtels : si Duffel absent, retourner `degraded` avec "recherche non configurée" et ne jamais inventer de prix.

### Réparation semi-auto

- Alerte : "SERPER_API_KEY absente — recherche web, lieux et restaurants indisponibles."
- Alerte : "Solde Twilio critique — recharger sur twilio.com."
- Alerte : "Duffel non configuré ou KYC absent — vols/hôtels non réservables."
- Alerte : "Stripe absent — paiement indisponible en mode exploitant."
- Alerte : "SMTP absent — email limité aux brouillons."
- Alerte : "Flux RSS tous indisponibles — vérifier les sources d'actualités."

### Monitoring attendu pour `/api/admin/objectives`

Le bloc `services` doit être structuré pour afficher une vue globale et un détail par sous-service :

```json
{
  "services": {
    "status": "degraded",
    "goal": "Luna agit pour l'utilisateur via les services de conciergerie.",
    "checks": [
      {"name": "tools_catalog_loaded", "status": "ok"},
      {"name": "tool_dispatcher_available", "status": "ok"},
      {"name": "redis_available", "status": "ok"}
    ],
    "subservices": {
      "weather": {"status": "ok", "critical": false},
      "news": {"status": "ok", "critical": false},
      "web_search": {"status": "warning", "critical": false, "missing": ["SERPER_API_KEY"]},
      "places_restaurants": {"status": "warning", "critical": false, "missing": ["SERPER_API_KEY"]},
      "sms": {"status": "ok", "critical": true},
      "voice_call": {"status": "ok", "critical": true},
      "email": {"status": "warning", "critical": false, "mode": "draft_only"},
      "payments": {"status": "warning", "critical": false, "mode": "founder_optional"},
      "flights": {"status": "degraded", "critical": false, "missing": ["DUFFEL_ACCESS_TOKEN"]},
      "hotels": {"status": "degraded", "critical": false, "missing": ["DUFFEL_ACCESS_TOKEN"]}
    },
    "metrics": {
      "tools_declared": 0,
      "tools_available": 0,
      "last_tool_error": null,
      "sms_failed_rate": null,
      "duffel_search_order_ratio": null
    },
    "auto_heal": [
      {"condition": "weather_primary_down", "action": "fallback_open_meteo", "available": true},
      {"condition": "twilio_transient_failure", "action": "queue_sms_in_redis", "available": true},
      {"condition": "missing_location", "action": "fallback_profile_city", "available": true}
    ]
  }
}
```

---

## 5. Instructions — Automatisation Planifiée

**Objectif** : L'utilisateur crée des instructions que Luna exécute automatiquement (quotidiennes, conditionnelles, récurrentes) sans aucune intervention.

### Étapes obligatoires
- `InstructionScheduler` démarré et chargé
- `InstructionExecutor` connecté aux services (Twilio, OpenAI, Cortex)
- Instructions persistées en Redis par tenant
- Exécution à l'heure prévue (tolérance ±2 min)

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Scheduler actif | Chaque check | Non initialisé |
| Executor actif | Chaque check | Non initialisé |
| Instructions lisibles | Chaque check | Erreur Redis |
| Exécution dans les temps | Après chaque run | Délai > 5 min |

### Erreurs possibles
- Instruction bloquée sur exception non gérée
- Scheduler arrêté par redémarrage Cloud Run
- Quota SMS/voix épuisé lors de l'exécution

### Réparation automatique
- Rechargement instructions au démarrage (`_load_instructions_to_scheduler()`)
- Instructions manquées → log + alerte fondateur (pas re-tentative silencieuse)

---

## 6. Documents — Vault IA

**Objectif** : L'utilisateur scanne, classe et retrouve tous ses documents importants (identité, santé, factures, contrats, famille). Luna sait quels documents existent pour les utiliser dans ses réponses.

### Étapes obligatoires
- Module Vault chargé (`core.vault`)
- Consentement utilisateur donné (`has_consent()`)
- Documents indexés en Redis avec métadonnées (type, date, expiration, résumé IA)
- Catégories disponibles : identité, santé, factures, contrats, administratif, famille, urgence
- Luna peut répondre "tu as un passeport expirant le JJ/MM/AAAA" depuis le chat

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Module Vault disponible | Chaque check | Import échoué |
| Documents lisibles en Redis | Chaque check | Erreur |
| Consentement donné | Chaque check | Non (avertissement) |
| Rappels documents actifs | Hebdomadaire | Expirations non détectées |

### Erreurs possibles
- Consentement non donné → aucun document scanné
- PDF illisible (OCR échoué)
- Document classé dans mauvaise catégorie

### Réparation automatique
- Relance OCR si résultat vide
- Reclassement via IA si catégorie = `unknown`

### Réparation semi-auto
- Alerte : "Consentement Vault non donné — demander à l'utilisateur d'autoriser le scan"

---

## 7. Rapports — Génération Automatique

**Objectif** : Luna génère automatiquement des rapports structurés (compte-rendu d'appel, rapport d'activité, bilan de santé, rapport théocratique) téléchargeables en PDF.

### Étapes obligatoires
- Clé `ANTHROPIC_KEY_ANALYSIS` valide
- `DocumentGenerator` initialisé avec répertoire de sortie
- Génération PDF opérationnelle
- Rapports accessibles via `/api/documents`

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Clé Analysis initialisée | Chaque check | Absente |
| DocumentGenerator actif | Chaque check | Non initialisé |
| Génération PDF < 10s | Sentry | Timeout |
| Répertoire sortie accessible | Chaque check | Permission denied |

### Erreurs possibles
- Bibliothèque PDF (`reportlab` / `docx`) manquante
- Répertoire `/static/documents` en lecture seule sur Cloud Run
- Rapport vide (appel trop court)

### Réparation automatique
- Stockage rapport en Redis si système de fichiers indisponible

---

## 8. Formulaires — Remplissage Intelligent

**Objectif** : L'utilisateur soumet un formulaire PDF, Luna le remplit automatiquement avec les données du profil, et retourne un PDF signé prêt à envoyer.

### Étapes obligatoires
- Module `form_filler` monté
- Profil pré-remplissage complet (nom, adresse, date de naissance, etc.)
- Analyse PDF des champs (via IA)
- Remplissage + signature numérique si requise
- Téléchargement du PDF final

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Router form-filler monté | Chaque check | Import échoué |
| Profil pré-remplissage | Chaque check | Vide (avertissement) |
| Historique formulaires accessible | Chaque check | Erreur Redis |
| Taux completion bout-en-bout | Sentry | < 80% |

### Erreurs possibles
- PDF non-remplissable (image scannée sans champs)
- Champ non reconnu par l'IA
- Signature numérique non supportée par le PDF

### Réparation automatique
- OCR + extraction de champs si PDF image
- Champs non reconnus → liste pour remplissage manuel

---

## 9. Guardian — Protection & SOS

**Objectif** : Luna surveille l'activité de l'utilisateur. Si inactivité suspecte ou SOS déclenché, elle alerte immédiatement les contacts de confiance.

### Étapes obligatoires
- Clé `ANTHROPIC_KEY_GUARDIAN` valide
- `GuardianEngine` initialisé
- Au moins 1 contact de confiance configuré
- SOS déclenche alerte SMS + appel en < 60s
- Partage de position GPS opérationnel

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Clé Guardian initialisée | Chaque check | Absente |
| Engine disponible | Chaque check | Non init |
| Contacts d'urgence | Chaque check | 0 contact → **critique** |
| Délai alerte SOS | Test mensuel | > 90s |

### Erreurs possibles
- Aucun contact → SOS silencieux (critique)
- Twilio KO → alerte SMS impossible
- GPS non partagé par l'utilisateur

### Réparation automatique
- Si Twilio KO lors SOS → tentative appel via API alternative
- Log immédiat Sentry sur tout échec SOS

### Réparation semi-auto
- **Alerte critique** : "0 contact d'urgence configuré — SOS non fonctionnel"

---

## 10. Cartes — Localisation Temps Réel

**Objectif** : L'utilisateur peut partager sa position en temps réel avec ses contacts de confiance, et les contacts peuvent voir sa position sur une carte.

### Étapes obligatoires
- GuardianEngine actif (même engine que Guardian)
- Session Guardian créée avec token de partage
- Position GPS mise à jour en Redis en temps réel
- Page `/guardian-live/{token}` accessible sans login
- Lien de partage transmis par SMS au contact

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Engine Guardian actif | Chaque check | Non init |
| Sessions Redis accessibles | Chaque check | Erreur |
| Délai mise à jour position | Par session active | > 30s |

### Erreurs possibles
- GPS bloqué par le navigateur (permissions)
- Token de partage expiré
- Carte non chargée (Leaflet.js CDN KO)

### Réparation automatique
- Token de partage auto-renouvelé si expiré pendant session active

---

## 11. Amis — Réseau Social

**Objectif** : L'utilisateur se connecte avec d'autres utilisateurs Luna via un code ami, échange des messages et partage des moments.

### Étapes obligatoires
- `SocialRedisOps` disponible
- Friend code unique généré pour le tenant
- Ajout ami par code fonctionnel
- Liste amis lisible
- Messages entre amis transmis en temps réel

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Friend code généré | Chaque check | Absent |
| Liste amis accessible | Chaque check | Erreur Redis |
| Module Social disponible | Chaque check | Import échoué |

### Erreurs possibles
- Collision de codes amis (rare)
- Redis flush → relations amis perdues

### Réparation automatique
- Régénération friend code si absent au démarrage

---

## 12. Voix — Appel Vocal IA

**Objectif** : L'utilisateur parle à Luna en temps réel, Luna répond avec une voix naturelle, la conversation est transcrite et mémorisée.

### Étapes obligatoires
- OpenAI Realtime API configuré
- TTS OpenAI (voix `coral`) fonctionnel
- Connexion WebSocket stable < 2s
- Transcription sauvegardée en mémoire après l'appel
- Quota voix non dépassé

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| OpenAI configuré | Chaque check | Absent |
| Quota voix restant | Chaque check | < 10% |
| Latence connexion WS | Sentry | > 3s |
| Taux déconnexion WS | Sentry | > 10% |

### Erreurs possibles
- Micro bloqué navigateur (permissions)
- WebSocket coupé par Cloud Run timeout
- Quota voix épuisé

### Réparation automatique
- Reconnexion WebSocket automatique x3
- Alerte quota < 10% restant

---

## 13. Visio Avatar — Simli & Tavus

**Objectif** : L'utilisateur voit et parle à l'avatar vidéo de Luna en temps réel, avec lip-sync et expressions naturelles.

### Étapes obligatoires

#### Simli (principal — Essentiel, Confort, Fondateur fallback)
- `SIMLI_API_KEY` + `SIMLI_FACE_ID` configurés
- `POST https://api.simli.ai/auto/start/configurable` → Daily.co room URL
- Latence démarrage visio < 5s

#### Tavus (Premium + Fondateur)
- `TAVUS_API_KEY` + `TAVUS_LUNA_PERSONA_ID` configurés
- Crédits Tavus disponibles (> 0)
- `POST /api/call` → Daily.co conversation URL
- Latence démarrage < 3s

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Simli clés configurées | Chaque check | Absentes |
| Tavus clés configurées | Chaque check | Absentes |
| Crédits Tavus | Quotidien | Épuisés (402) |
| Latence démarrage visio | Sentry | > 8s |
| Taux d'échec `/api/call` | Sentry | > 5% |

### Routing par plan
| Plan | Provider visio |
|---|---|
| Essentiel / Confort | Simli |
| Premium / Fondateur | Tavus → fallback Simli si 402 |

### Erreurs possibles
- Tavus 402 (crédits épuisés) → fallback Simli automatique
- Simli API indisponible
- Daily.co room expirée (> 1h)

### Réparation automatique
- Tavus 402 → bascule Simli immédiate
- Retry Simli x2 si timeout

### Réparation semi-auto
- Alerte : "Crédits Tavus épuisés — recharger sur tavus.io"

---

## 14. Activités — Gamification

**Objectif** : L'utilisateur gagne des points XP, des badges et monte de niveau en interagissant avec Luna. Cela encourage l'engagement quotidien.

### Étapes obligatoires
- `GamificationRedisOps` connecté à Redis
- Joueur initialisé pour le tenant (XP, niveau, badges)
- XP attribué sur chaque action (chat, voix, visio, login)
- Badges débloqués automatiquement selon critères
- Missions disponibles et progressables

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Gamification Redis ops actif | Chaque check | Erreur |
| Profil joueur lisible | Chaque check | Absent |
| Badges accessibles | Chaque check | Erreur |
| XP enregistré après action | Post-action | Non incrémenté |

### Erreurs possibles
- Redis flush → historique XP perdu
- Double attribution XP (bug idempotence)

### Réparation automatique
- Initialisation joueur au premier login si absent

---

## 15. Monde — Espace Social Global

**Objectif** : L'utilisateur existe dans un espace social Luna : avatar visible, invitations d'amis, présence dans des mondes virtuels partagés.

### Étapes obligatoires
- Module `core.world` chargé
- `WorldRedisOps` connecté
- Paramètres vie privée définis (visibilité carte, accepte invitations)
- Avatar configurable
- Invitations envoyables et recevables entre tenants

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Module World social disponible | Chaque check | Import échoué |
| Paramètres vie privée lisibles | Chaque check | Erreur Redis |
| Avatar accessible | Chaque check | Erreur |
| Invitations transmises | Sentry | Taux d'échec > 5% |

### Erreurs possibles
- Monde vide si aucun autre utilisateur
- Invitation expirée (TTL Redis)

---

## 16. Profil — Identité Souscripteur

**Objectif** : Luna connaît l'utilisateur en profondeur (préférences, habitudes, famille, santé, centres d'intérêt) pour personnaliser chaque interaction.

### Étapes obligatoires
- `TenantManager` / `MemoryManager` initialisé
- Profil complet (nom, prénom, date de naissance, contacts, préférences)
- Profil injecté dans chaque conversation
- Modifications profil persistées immédiatement

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| TenantManager actif | Chaque check | Non init |
| Profil lisible | Chaque check | Vide → avertissement |
| Persistance modification | Post-edit | Non sauvegardé |

---

## 17. Quotas — Maîtrise de la Consommation

**Objectif** : L'utilisateur sait combien il lui reste de minutes voix, visio, SMS. Il ne peut jamais dépasser son forfait sans être prévenu.

### Étapes obligatoires
- `get_quota_status()` retourne un dict complet
- Limites par plan appliquées strictement
- Alerte à 80% de consommation
- Blocage à 100% (graceful : message explicatif)

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Système quotas opérationnel | Chaque check | Erreur |
| Quotas voix, visio, SMS lisibles | Chaque check | Données manquantes |
| Dépassement détecté | En temps réel | Immédiat |

### Plans & limites
| Plan | Chat | Voix | Visio | SMS |
|---|---|---|---|---|
| Essentiel 79€ | Illimité | 40 min | 12 min | 25 |
| Confort 149€ | Illimité | 100 min | 28 min | 50 |
| Premium 249€ | Illimité | 180 min | 55 min | 100 |

---

## 18. Réglages — Configuration Exploitant

**Objectif** : L'exploitant configure Luna via un dashboard (Stripe, personnalisation, branding, limites) sans toucher au code.

### Étapes obligatoires
- Stripe configuré et webhook actif (paiements automatiques)
- Identifiants admin sécurisés
- Plans et tarifs cohérents avec Stripe

### Points de contrôle
| Contrôle | Fréquence | Seuil d'alerte |
|---|---|---|
| Stripe secret key présente | Chaque check | Absente |
| Webhook Stripe actif | Quotidien | KO |
| Identifiants admin configurés | Chaque check | Absents |

### Note fondateur
> Sur le serveur fondateur, Stripe n'est pas configuré — c'est intentionnel. Ce point est marqué **optionnel** pour le fondateur, **obligatoire** pour l'exploitant.

---

## Matrice de criticité

| Niveau | Description | Action |
|---|---|---|
| 🔴 **CRITIQUE** | Fonctionnalité totalement inutilisable (SOS sans contacts, Redis KO) | Alerte immédiate SMS + Telegram |
| 🟠 **DÉGRADÉ** | Fonctionnalité partielle (Tavus KO → Simli actif) | Alerte Telegram, log Sentry |
| 🟡 **AVERTISSEMENT** | Fonctionnalité active mais sous-optimale (profil vide, consentement absent) | Log Sentry uniquement |
| 🟢 **OK** | Objectif atteint à 100% | — |

---

## Plan de monitoring automatique

### Architecture proposée
```
Cloud Run (luna_web.py)
  └── _check_all_objectives()          ← vérifie tous les objectifs toutes les 5 min
        └── _send_objectives_alert()   ← SMS + Telegram si échec critique
              └── Sentry               ← log erreurs + traces
GCP Uptime Check                       ← ping /health toutes les 60s → email si KO
```

### Niveaux d'alerte
```
Objectif KO → Sentry log (toujours)
           → Telegram si 🔴 ou 🟠
           → SMS si 🔴 critique (SOS, Redis, Auth)
           → Email GCP si serveur down
```

### Réparations automatiques implémentées
| Situation | Réparation auto |
|---|---|
| Tavus 402 | Fallback Simli immédiat |
| Redis indisponible | `_redis_available()` 30s cache + try/except partout |
| Licences perdues (scale-out) | Reload depuis Redis au démarrage |
| Instructions manquantes | Rechargement scheduler au démarrage |
| Joueur gamification absent | Initialisation au premier login |
| WebSocket vocal coupé | Reconnexion auto x3 |

### Réparations semi-automatiques (alertes avec solution)
| Alerte | Solution suggérée |
|---|---|
| Stripe absent | "Configurer STRIPE_SECRET_KEY dans deploy.sh" |
| Consentement Vault absent | "Demander à l'utilisateur d'autoriser le scan" |
| Crédits Tavus épuisés | "Recharger sur tavus.io" |
| Solde Twilio critique | "Recharger sur twilio.com" |
| Quota Anthropic 429 | "Vérifier quota sur console.anthropic.com" |
| 0 contact Guardian | "Ajouter un contact d'urgence dans l'app" |

---

## Score actuel (24 mai 2026)

```
Score global : 30/31
Seul échec   : Stripe non configuré (intentionnel — serveur fondateur)
```

| Domaine | Score |
|---|---|
| Infrastructure | ✓ 1/1 |
| Connexion | ✓ 1/1 |
| Chat | ✓ 2/2 |
| Services | ✓ 2/2 |
| Instructions | ✓ 2/2 |
| Documents | ✓ 2/2 |
| Rapports | ✓ 2/2 |
| Formulaires | ✓ 2/2 |
| Cartes | ✓ 2/2 |
| Guardian | ✓ 3/3 |
| Amis | ✓ 2/2 |
| Voix·Visio | ✓ 1/1 |
| Visio Avatar | ✓ 2/2 |
| Activités | ✓ 1/1 |
| Monde | ✓ 2/2 |
| Profil | ✓ 1/1 |
| Quotas | ✓ 1/1 |
| Réglages | ✗ 1/2 (Stripe intentionnellement absent) |
