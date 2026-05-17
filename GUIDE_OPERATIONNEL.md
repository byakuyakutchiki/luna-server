# Guide Opérationnel — Luna IA
> Pour les non-développeurs. Ce guide explique quoi faire quand ça ne marche pas, quoi vérifier avant de paniquer, et quoi ne jamais oublier quand on touche au code. Complet, exhaustif, sans jargon inutile.

---

## SOMMAIRE

1. [Les questions à poser avant tout](#1-les-questions-à-poser-avant-tout)
2. [Comprendre l'architecture en 2 minutes](#2-comprendre-larchitecture-en-2-minutes)
3. [Les variables de configuration (.env)](#3-les-variables-de-configuration-env)
4. [Lire les logs Cloud Run pas à pas](#4-lire-les-logs-cloud-run-pas-à-pas)
5. [Générer un token admin](#5-générer-un-token-admin)
6. [Le dashboard admin — tous les onglets](#6-le-dashboard-admin--tous-les-onglets)
7. [Checklist avant de faire une modification](#7-checklist-avant-de-faire-une-modification)
8. [Checklist après un déploiement](#8-checklist-après-un-déploiement)
9. [Quand le serveur ne répond plus](#9-quand-le-serveur-ne-répond-plus)
10. [Quand Luna dit des choses fausses](#10-quand-luna-dit-des-choses-fausses)
11. [Quand la visio ne fonctionne pas](#11-quand-la-visio-ne-fonctionne-pas)
12. [Quand les SMS ne partent pas](#12-quand-les-sms-ne-partent-pas)
13. [Quand les paiements Stripe ne fonctionnent pas](#13-quand-les-paiements-stripe-ne-fonctionnent-pas)
14. [IP bannie — débannissement rapide](#14-ip-bannie--débannissement-rapide)
15. [Gestion des quotas clients](#15-gestion-des-quotas-clients)
16. [Redis — sauvegarde, restauration, nettoyage](#16-redis--sauvegarde-restauration-nettoyage)
17. [Procédures d'urgence](#17-procédures-durgence)
18. [Maintenance mensuelle](#18-maintenance-mensuelle)
19. [Règles à ne jamais oublier](#19-règles-à-ne-jamais-oublier)
20. [Journal des incidents](#20-journal-des-incidents)

---

## 1. Les questions à poser avant tout

Avant d'appeler un dev ou de paniquer, répondre à ces 5 questions :

### Question 1 — Ça marchait avant ?
- **Oui** → quelque chose a changé. Qui a touché quoi et quand ? Vérifier les derniers commits git et le dernier déploiement.
- **Non** → bug de configuration initiale, probablement une clé API manquante ou mal saisie.

### Question 2 — C'est quoi exactement le problème ?
- Luna ne répond pas du tout → **problème de serveur** (section 9)
- Luna répond mais dit n'importe quoi → **problème de prompt ou de données** (section 10)
- La visio ne s'ouvre pas → **problème Tavus ou Daily.co** (section 11)
- Les SMS ne partent pas → **problème Twilio** (section 12)
- Les paiements échouent → **problème Stripe** (section 13)
- Accès refusé / IP bannie → **problème de sécurité Cortex** (section 14)
- Les quotas sont bloqués → **problème de quota** (section 15)

### Question 3 — Le problème arrive sur quel appareil / navigateur ?
- Sur tous → problème côté **serveur**
- Sur un seul → problème côté **client** (cache, navigateur, réseau)
- Sur mobile seulement → problème de **compatibilité mobile** (vérifier Chrome vs Safari)

### Question 4 — Y a-t-il eu un déploiement récent ?
- **Oui** → la nouvelle version a peut-être cassé quelque chose. Voir comment revenir en arrière (section 9).
- **Non** → le problème vient d'ailleurs : clé API expirée, quota dépassé, service tiers en panne.

### Question 5 — Y a-t-il des erreurs visibles ?
- Ouvrir F12 → Console dans le navigateur — y a-t-il des lignes rouges ?
- Ouvrir les logs Cloud Run (section 4) — y a-t-il des lignes `ERROR` ?

---

## 2. Comprendre l'architecture en 2 minutes

```
UTILISATEUR
    │
    ▼
CLOUD RUN (Google) — luna-beta
    │
    ├── luna_web.py        → Le cerveau : gère TOUT (routes, chat, outils)
    ├── core/cortex/       → Sécurité (Cortex : bloque les attaques, gère les IPs)
    ├── core/memory/       → Mémoire long-terme de Luna (stockée dans Redis)
    ├── integrations/tavus/ → Visio avatar (Tavus + Daily.co)
    ├── static/            → Pages web (index.html, simli.html, admin.html)
    └── .env               → Toutes les clés API et configurations
         │
         ▼
    REDIS (base de données en mémoire)
    → Stocke : sessions, mémoire Luna, quotas, whitelist IPs
```

**Services externes utilisés :**
| Service | À quoi ça sert | Si ça tombe |
|---|---|---|
| OpenAI (gpt-4o-mini) | Cerveau de Luna, génère les réponses | Luna ne répond plus |
| Tavus | Visio avatar (voix + visage) | Visio impossible |
| Daily.co | WebRTC (transport vidéo) | Visio impossible |
| Twilio | Envoi et réception SMS | SMS impossibles |
| Stripe | Paiements | Abonnements impossibles |
| Redis | Mémoire et sessions | Luna oublie tout, quotas KO |
| Google Cloud Run | Hébergement du serveur | Tout tombe |

---

## 3. Les variables de configuration (.env)

Le fichier `.env` est le tableau de bord de Luna. **Ne jamais mettre ce fichier sur GitHub.**  
Il se trouve sur le serveur Cloud Run sous forme de secrets — pour le modifier : Google Cloud Console → Cloud Run → luna-beta → Modifier et déployer → Variables et secrets.

### Clés obligatoires

| Variable | Ce que c'est | Où la trouver |
|---|---|---|
| `OPENAI_API_KEY` | Clé pour les réponses de Luna | platform.openai.com → API Keys |
| `JWT_SECRET_KEY` | Mot de passe interne (tokens de session) | **Ne jamais changer en prod** |
| `ADMIN_PHONE` | Numéro de téléphone de l'admin (format +336...) | Renseigner au setup |

### Clés pour la visio

| Variable | Ce que c'est |
|---|---|
| `TAVUS_API_KEY` | Clé Tavus pour le visage/voix de Luna |
| `TAVUS_REPLICA_ID` | Identifiant du visage Luna (`r79e1c033f`) |
| `TAVUS_PERSONA_ID` | Personnalité Tavus de Luna (`p10341f761ef`) |
| `DAILY_API_KEY` | Clé Daily.co pour le WebRTC (transport vidéo) |

### Clés pour les SMS

| Variable | Ce que c'est |
|---|---|
| `TWILIO_ACCOUNT_SID` | Identifiant Twilio (commence par `AC`) |
| `TWILIO_AUTH_TOKEN` | Mot de passe Twilio |
| `TWILIO_PHONE_NUMBER` | Numéro d'envoi Twilio (`+17173409138`) |

### Clés pour les paiements

| Variable | Ce que c'est |
|---|---|
| `STRIPE_SECRET_KEY` | Clé secrète Stripe (commence par `sk_live_` ou `sk_test_`) |
| `STRIPE_PUBLISHABLE_KEY` | Clé publique Stripe (commence par `pk_live_` ou `pk_test_`) |
| `STRIPE_WEBHOOK_SECRET` | Secret pour valider les webhooks Stripe |

### Configuration système

| Variable | Ce que c'est | Valeur |
|---|---|---|
| `LUNA_MODE` | Mode lite (chat+voix+SMS) ou full (+ visio) | `lite` ou `full` |
| `PORT` | Port du serveur | `8080` (Cloud Run) |
| `TTS_ENGINE` | Moteur de synthèse vocale | `openai` |
| `TTS_VOICE` | Voix utilisée | `coral` (femme, français) |
| `REDIS_URL` | Adresse Redis | `redis://localhost:6379` |
| `PV_SIGNED` | PV de recette signé ? | `true` ou vide |

### Comment modifier une variable sans redéployer

Sur Google Cloud Console :
1. Cloud Run → luna-beta → **Modifier et déployer une nouvelle révision**
2. Section "Variables d'environnement" → modifier la valeur
3. Cliquer "Déployer" — la révision sera créée avec la nouvelle valeur

---

## 4. Lire les logs Cloud Run pas à pas

Les logs sont le "journal de bord" du serveur. Indispensable pour diagnostiquer.

### Accéder aux logs

1. Aller sur **console.cloud.google.com**
2. Menu hamburger (≡) → **Cloud Run**
3. Cliquer sur **luna-beta**
4. Onglet **Logs**

### Comprendre les couleurs et niveaux

| Couleur | Niveau | Signification |
|---|---|---|
| Gris / blanc | INFO | Normal, tout va bien |
| Jaune | WARNING | Attention, quelque chose d'inhabituel |
| Rouge | ERROR | Erreur, quelque chose a planté |
| Rouge foncé | CRITICAL | Crash du serveur |

### Filtrer les logs utiles

Dans la barre de recherche, taper :
- `severity=ERROR` → voir uniquement les erreurs
- `_tool_send_sms` → voir les SMS envoyés
- `cortex` → voir les actions de sécurité
- `luna_mute` → voir si le bouton muet fonctionne
- `tavus` → voir les appels visio

### Lire une ligne de log

```
2026-05-17 14:23:01  INFO  [simli] vision_notify: ok
│                    │     │        │               │
│                    │     │        │               └─ Résultat
│                    │     │        └─ Action
│                    │     └─ Module
│                    └─ Niveau
└─ Date et heure
```

### Erreurs fréquentes et ce qu'elles signifient

| Message d'erreur | Cause | Solution |
|---|---|---|
| `OpenAI API error 401` | Clé OpenAI invalide ou expirée | Renouveler la clé sur platform.openai.com |
| `OpenAI API error 429` | Quota OpenAI dépassé | Acheter des crédits ou attendre |
| `Tavus API error 403` | Clé Tavus invalide | Vérifier TAVUS_API_KEY |
| `Redis connection refused` | Redis pas démarré | Vérifier le service Redis |
| `JWT decode error` | Token de session invalide | L'utilisateur doit se reconnecter |
| `Stripe signature invalid` | Webhook mal configuré | Vérifier STRIPE_WEBHOOK_SECRET |
| `ModuleNotFoundError` | Dépendance Python manquante | Vérifier requirements.txt |

---

## 5. Générer un token admin

Le token admin permet d'appeler les endpoints `/api/admin/*` (débannir une IP, voir les quotas, etc.).  
**Le token expire au bout d'un certain temps** — il faut en regénérer un si l'ancien ne fonctionne plus.

### Via l'interface web

1. Ouvrir `https://luna-beta-674304336025.europe-west1.run.app/admin`
2. Se connecter avec les identifiants admin
3. Le token est géré automatiquement par le navigateur

### Via ligne de commande (pour un dev)

```bash
# Générer un token avec Python (dans le dossier du projet)
python3 -c "
import jwt, datetime, os
secret = os.environ.get('JWT_SECRET_KEY', 'REMPLACER_PAR_LA_VRAIE_CLE')
token = jwt.encode({
    'sub': 'admin',
    'role': 'admin',
    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
}, secret, algorithm='HS256')
print(token)
"
```

### Utiliser le token dans curl

```bash
TOKEN="le_token_généré_ci_dessus"
curl -H "Authorization: Bearer $TOKEN" \
  https://luna-beta-674304336025.europe-west1.run.app/api/admin/stats
```

---

## 6. Le dashboard admin — tous les onglets

Accès : `https://luna-beta-674304336025.europe-west1.run.app/admin`

### Onglet 1 — Vue d'ensemble

- **Statut du serveur** : vert = OK, rouge = problème
- **Nombre d'utilisateurs actifs** : connectés aujourd'hui
- **Requêtes en cours** : appels API actifs
- **Uptime** : depuis combien de temps le serveur tourne

### Onglet 2 — Clients

- Liste de tous les comptes utilisateurs
- Pour chaque client : email, plan, date d'inscription, statut
- **Actions disponibles** :
  - Voir les quotas restants d'un client
  - Réinitialiser les quotas manuellement
  - Suspendre / réactiver un compte
  - Voir l'historique des SMS envoyés

### Onglet 3 — Quotas

- Vue globale de la consommation par plan
- **Quotas par plan** (rappel) :

| Plan | Voix | Visio | SMS | Prix |
|---|---|---|---|---|
| Essentiel | 40 min/mois | 12 min/mois | 25/mois | 79€ |
| Confort | 100 min/mois | 28 min/mois | 50/mois | 149€ |
| Premium | 180 min/mois | 55 min/mois | 100/mois | 249€ |
| Chat | Illimité | Illimité | Illimité | Tous |

- **Comment réinitialiser un quota** : cliquer sur le client → "Réinitialiser les quotas"
- **Quand les quotas se réinitialisent** : automatiquement au 1er de chaque mois (date de facturation Stripe)

### Onglet 4 — Alertes Cortex

- Liste des IPs bannies
- Liste des IPs sur liste blanche (whitelist)
- Tentatives d'intrusion détectées
- **Actions** :
  - Débannir une IP manuellement
  - Ajouter une IP à la whitelist permanente
  - Voir le détail d'une alerte

### Onglet 5 — Chiffre d'affaires

- CA du mois en cours (Stripe)
- CA des 12 derniers mois
- Répartition par plan
- Clients actifs vs inactifs
- **Exporter en CSV** : bouton en haut à droite

### Onglet 6 — Serveur (si présent)

- CPU et mémoire en temps réel
- Logs récents (dernières 50 lignes)
- Version déployée
- Bouton "Redémarrer" (redémarre le container sans redéployer)

---

## 7. Checklist avant de faire une modification

> À compléter AVANT de donner du code à modifier à un développeur.

- [ ] **Sauvegarder l'état actuel** → `git add -A && git commit -m "État stable avant : [décrire la modif]"`
- [ ] **Noter la révision Cloud Run active** → Cloud Run → luna-beta → Révision active (ex: `luna-beta-00267-fx8`)
- [ ] **Tester que tout fonctionne AVANT la modif** : chat, visio, SMS (au moins 1 test chacun)
- [ ] **Identifier le fichier exact à modifier** (voir `GUIDE_DEV.md`)
- [ ] **Avoir une clé de secours** → si la modif casse tout, savoir comment revenir en arrière
- [ ] **Si on touche au prompt** → relire section 19, Règle 6
- [ ] **Si on touche à `simli.html` ou `index.html`** → bumper `sw.js` (Règle 1)
- [ ] **Si on touche à Stripe** → tester en mode `sk_test_` d'abord
- [ ] **Si on touche à Cortex** → ne pas modifier les IPs fondateur (Règle 5)

---

## 8. Checklist après un déploiement

> À vérifier SYSTÉMATIQUEMENT après chaque déploiement, sans exception.

### Obligatoire (10 minutes max)

- [ ] **Santé du serveur** → Ouvrir `/health` → doit afficher `{"status":"ok"}`
- [ ] **La page principale s'affiche** → Ouvrir `/` → l'interface chat est visible
- [ ] **Luna répond au chat** → Envoyer "Bonjour" → une réponse arrive
- [ ] **Pas d'erreurs 404** → F12 → Réseau → recharger → aucune ligne rouge
- [ ] **Les images et sons se chargent** → la page ne montre pas de zones vides

### Si la visio a été modifiée

- [ ] **La page visio s'ouvre** → Aller sur `/simli` → la cinématique démarre
- [ ] **L'appel démarre** → cliquer "Démarrer" → le visage de Luna apparaît
- [ ] **Les boutons d'action apparaissent** après le démarrage de l'appel (Muet, Prise de notes, etc.)
- [ ] **Le bouton Muet fonctionne** → Luna se tait en quelques secondes
- [ ] **La vision fonctionne** → demander à Luna "que vois-tu ?" → elle décrit la scène
- [ ] **Bumper `sw.js`** → version `luna-vXX` incrémentée (sinon les users gardent l'ancien code)

### Si le prompt de Luna a été modifié

- [ ] **Luna se comporte correctement** → tester : demander quelque chose d'impossible, tester la mémoire
- [ ] **Luna ne hallucine pas** → demander la météo → elle doit dire qu'elle ne sait pas (pas inventer)
- [ ] **Luna n'est pas trop restrictive** → lui demander quelque chose de normal → elle répond sans blocage
- [ ] **La liste des capacités est complète** → lui demander "qu'est-ce que tu peux faire ?"

### Si les outils ont été modifiés

- [ ] **Tester chaque outil modifié** : SMS test, météo, recherche, agenda
- [ ] **Vérifier les logs** → Cloud Run Logs → chercher des erreurs `ERROR` ou `WARNING`
- [ ] **Vérifier qu'aucun outil ne timeout** → les outils doivent répondre en moins de 10 secondes

### Si Stripe a été modifié

- [ ] **Le webhook répond** → Stripe Dashboard → Webhooks → dernier événement → "Livraison réussie"
- [ ] **Les plans s'affichent correctement** → page de tarification → 3 plans visibles avec les bons prix
- [ ] **Un paiement test réussit** → utiliser la carte test `4242 4242 4242 4242`

---

## 9. Quand le serveur ne répond plus

### Diagnostic en 5 étapes

**Étape 1 — Vérifier si le serveur est vivant**
```
Ouvrir dans le navigateur :
https://luna-beta-674304336025.europe-west1.run.app/health
```
- Réponse `{"status":"ok"}` → serveur OK, le problème est ailleurs (cache ? réseau ?)
- Timeout (plus de 30 secondes sans réponse) → passer à l'étape 2
- Erreur 503 → container planté, aller à l'étape 3

**Étape 2 — Tester depuis un autre réseau**
- Essayer depuis son téléphone en 4G (pas le Wi-Fi habituel)
- Si ça marche en 4G → problème de réseau local ou de cache navigateur
  - Solution : vider le cache (navigation privée, ou ouvrir `/clear-cache`)
- Si ça ne marche pas non plus → passer à l'étape 3

**Étape 3 — Vérifier Cloud Run**
1. Aller sur console.cloud.google.com
2. Navigation → Cloud Run → **luna-beta**
3. Onglet "Révisions" → la révision active est-elle en vert ?
4. Onglet "Logs" → y a-t-il des erreurs rouges dans les 10 dernières minutes ?

**Étape 4 — Identifier la cause dans les logs**

| Message dans les logs | Cause | Solution |
|---|---|---|
| `Container failed to start` | Erreur Python au démarrage | Voir log complet, corriger le code |
| `Memory limit exceeded` | Serveur à court de mémoire | Augmenter la mémoire dans Cloud Run |
| `CPU throttled` | Surcharge | Augmenter les ressources ou attendre |
| `OpenAI error 429` | Quota OpenAI épuisé | Acheter des crédits OpenAI |
| `Redis connection failed` | Redis planté | Voir section 16 |
| Aucune erreur | Redémarrage automatique | Attendre 2 minutes et retester |

**Étape 5 — Redéployer si tout le reste échoue**
```bash
# Depuis le dossier luna-server/ sur la machine de développement
gcloud run deploy luna-beta \
  --source . \
  --project crypto-parser-475411-k4 \
  --region europe-west1 \
  --quiet
```
Le redéploiement prend environ 5-7 minutes.

### Revenir à une révision précédente

Si la nouvelle version casse tout et que le redéploiement ne suffit pas :
1. Cloud Run → luna-beta → onglet **Révisions**
2. Trouver la dernière révision qui fonctionnait (ex: `luna-beta-00265-xxx`)
3. Cliquer sur les 3 points → **Rediriger le trafic**
4. Mettre 100% sur l'ancienne révision → Enregistrer

---

## 10. Quand Luna dit des choses fausses

### Luna invente de la météo, des actualités ou des informations

**Cause :** L'IA "hallucine" — elle invente plutôt que d'admettre qu'elle ne sait pas.  
**Vérifier :** Le prompt contient-il la règle anti-hallucination ?

```bash
# Dans luna_web.py, chercher ce texte — il doit être présent :
RÈGLE ANTI-HALLUCINATION
```

**Solution immédiate :** Dans la conversation, dire à Luna "tu es en train d'inventer". Elle se recadre.  
**Solution permanente :** Renforcer le prompt dans `luna_web.py` ligne 787 — ajouter ou renforcer la règle.

---

### Luna refuse de faire quelque chose qu'elle devrait faire

**Exemple :** Luna refuse d'envoyer un SMS alors qu'elle le devrait.

**Cause probable 1 :** La capacité n'est pas déclarée dans son prompt.  
→ `luna_web.py` ligne 787 — ajouter la capacité dans la liste.

**Cause probable 2 :** L'outil est déclaré mais pas fonctionnel.  
→ Tester l'outil directement via l'API : `POST /api/test/sms`  
→ Vérifier les logs : chercher `_tool_send_sms`

**Cause probable 3 :** Le quota du client est épuisé.  
→ Voir section 15.

---

### Luna fait la même réponse à tout le monde (perd la personnalisation)

**Cause :** La mémoire Redis est vide (container redémarré, Redis flushé).  
**Vérifier :**  
1. Logs → chercher `MemoryManager` ou `Redis`
2. `redis-cli DBSIZE` → si 0, la base est vide

**Solution :** La mémoire se reconstruit progressivement au fil des conversations. On ne peut pas la restaurer automatiquement sans sauvegarde préalable.

---

### Luna oublie ce qui a été dit dans la même conversation

**Cause :** Le contexte de conversation est trop long (limite de tokens OpenAI).  
**Solution :** C'est géré automatiquement par le serveur (tronque les anciens messages). Si le problème persiste, réduire `MAX_CONTEXT_MESSAGES` dans `luna_web.py`.

---

### Luna parle en anglais au lieu de français

**Cause :** Le prompt système a été modifié ou une partie du code génère du contenu en anglais.  
**Vérifier :**  
1. `luna_web.py` ligne 787 → le prompt commence-t-il par "Tu es Luna, une assistante francophone" ?
2. `TAVUS_PERSONA_ID` → le persona Tavus est-il configuré en français (`p10341f761ef`) ?

**Solution :** Restaurer le prompt français dans `luna_web.py` et dans la configuration Tavus.

---

## 11. Quand la visio ne fonctionne pas

### La page `/simli` ne s'ouvre pas (erreur 404 ou 500)

**Cause probable :** `simli.html` n'est pas dans `static/` ou le serveur a planté.  
**Vérifier :** Logs Cloud Run → chercher des erreurs liées à `simli`.

---

### La cinématique démarre mais l'appel ne se connecte pas

**Cause probable 1 :** Tavus est en panne ou la clé API est invalide.  
**Vérifier :**
1. Aller sur dashboard.tavus.io — le compte est-il actif ?
2. Vérifier `TAVUS_API_KEY` dans la configuration
3. Logs Cloud Run → chercher `tavus_error` ou `Tavus API`

**Cause probable 2 :** Daily.co est en panne.  
→ Vérifier le statut sur status.daily.co

---

### L'image de Luna ne s'affiche pas (écran noir)

**Cause :** Daily.co n'a pas pu établir la connexion WebRTC.  
**Vérifier dans l'ordre :**
1. Le navigateur a-t-il accès à la caméra et au micro ? (pop-up de permission doit apparaître)
2. Le réseau bloque-t-il WebRTC ? → tester sans VPN
3. Sur mobile : utiliser **Chrome** uniquement (pas Safari, pas Firefox)
4. Un firewall d'entreprise bloque-t-il les ports UDP ? → tester depuis un autre réseau

---

### Les boutons de la barre d'actions n'apparaissent pas

**Cause 1 :** Service Worker sert une ancienne version de `simli.html`.  
**Solution :** Aller sur `/clear-cache`, puis recharger la page.

**Cause 2 :** Le Service Worker (`sw.js`) n'a pas été mis à jour après la dernière modification.  
**Solution dev :** Vérifier que `CACHE_NAME` dans `sw.js` a été incrémenté.

---

### Luna ne peut pas voir à travers la caméra

**Comportement attendu :** 12 secondes après le début de l'appel, Luna est automatiquement informée que sa caméra est active. Elle peut ensuite répondre à "que vois-tu ?".

**Si ça ne marche pas :**
1. Attendre 15 secondes (la vision prend du temps)
2. Demander explicitement "que vois-tu ?" ou "décris ce que tu vois"
3. Logs → chercher `vision_notify` — est-ce que c'est marqué `ok` ?
4. Si absent : la permission caméra du navigateur a peut-être été refusée

**Vérifier les permissions navigateur :**
- Chrome : cliquer sur le cadenas à gauche de l'URL → Caméra → Autoriser
- Firefox : cliquer sur le cadenas → Permissions → Caméra → Autoriser

---

### Le bouton Muet ne fonctionne pas

**Comportement attendu :** Le bouton envoie une instruction à Luna. Elle se tait en quelques secondes (pas instantané — elle finit sa phrase en cours).

**Si ça ne marche pas :**
1. Logs navigateur (F12 → Console) → chercher `luna_mute`
2. Logs Cloud Run → chercher `luna_mute: on`
3. Si absent : la connexion `conversation.echo` avec Tavus est perdue
4. Solution : raccrocher et rappeler

---

### La prise de notes automatique ne fonctionne pas

**Comportement attendu :**
- Le bouton Notes 📝 affiche un point jaune clignotant quand le micro est actif
- Les échanges sont capturés en temps réel
- À la fin de l'appel, un résumé est généré

**Si le point jaune n'apparaît pas :**
- Le navigateur a bloqué l'accès au micro pour la reconnaissance vocale
- Chrome : URL → cadenas → Microphone → Autoriser

**Si les notes sont vides après l'appel :**
- La transcription a été filtrée (trop courte, moins de 5 mots par phrase)
- Parler plus clairement et en phrases complètes

**Navigateurs compatibles :** Chrome (recommandé). Firefox et Safari peuvent ne pas supporter `SpeechRecognition`.

---

### Luna ne répond pas dans la visio (silence total)

**Cause probable 1 :** Tavus traite la réponse (latence normale : 2-3 secondes).  
**Cause probable 2 :** Le quota visio est épuisé → voir section 15.  
**Cause probable 3 :** L'appel s'est déconnecté côté Tavus → raccrocher et rappeler.

---

## 12. Quand les SMS ne partent pas

### Diagnostic étape par étape

**Étape 1 — Vérifier le compte Twilio**
1. Aller sur console.twilio.com
2. Rubrique "Balance" → quel est le solde ? (0$ = SMS bloqués)
3. Si le solde est faible → recharger

**Étape 2 — Vérifier le numéro sortant**
1. Twilio Console → Phone Numbers → Manage → Active Numbers
2. Le numéro `+17173409138` est-il actif et en vert ?
3. Si rouge ou absent → le numéro a été suspendu ou supprimé

**Étape 3 — Vérifier les logs d'envoi**
1. Cloud Run Logs → chercher `_tool_send_sms`
2. Y a-t-il une erreur Twilio (code 21608, 21211, etc.) ?

**Étape 4 — Vérifier le destinataire**
- Certains opérateurs français bloquent les SMS venant de numéros américains
- Le destinataire a peut-être bloqué le numéro Twilio
- Solution si systématique : acheter un numéro français sur Twilio Console

### Codes d'erreur Twilio courants

| Code | Signification | Solution |
|---|---|---|
| 21608 | Numéro non autorisé à envoyer en France | Vérifier les restrictions géographiques Twilio |
| 21211 | Numéro destinataire invalide | Vérifier le format (+336... pour France) |
| 21610 | Destinataire a bloqué les SMS | Rien à faire côté serveur |
| 20003 | Clé Twilio invalide | Vérifier TWILIO_AUTH_TOKEN |
| 30001 | File d'attente pleine | Attendre et réessayer |

### Tester l'envoi d'un SMS manuellement

```bash
# Via l'API (avec un token admin valide)
curl -X POST \
  "https://luna-beta-674304336025.europe-west1.run.app/api/test/sms" \
  -H "Authorization: Bearer TOKEN_ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"to": "+336XXXXXXXX", "body": "Test SMS Luna"}'
```

### Numéros importants

- **Numéro Twilio sortant :** +17173409138 (US)
- Si les SMS France échouent systématiquement : acheter un numéro français via Twilio Console

---

## 13. Quand les paiements Stripe ne fonctionnent pas

### Stripe ne reçoit pas les paiements

**Étape 1 — Vérifier le mode (test vs live)**
- Clé `sk_test_...` = mode test, les vrais paiements ne passent pas
- Clé `sk_live_...` = mode production
- Vérifier `STRIPE_SECRET_KEY` dans la configuration

**Étape 2 — Vérifier le Dashboard Stripe**
1. Aller sur dashboard.stripe.com
2. Paiements → voir si des paiements sont en attente ou échoués
3. Y a-t-il des messages d'alerte en rouge ?

**Étape 3 — Vérifier le webhook Stripe**
1. Stripe Dashboard → Développeurs → Webhooks
2. Cliquer sur l'endpoint luna-beta → voir les dernières livraisons
3. Des livraisons échouées (rouge) indiquent un problème côté serveur
4. Vérifier `STRIPE_WEBHOOK_SECRET` — doit correspondre exactement

### Le client a payé mais son compte n'est pas activé

**Cause :** Le webhook Stripe n'a pas été reçu ou traité.

**Diagnostic :**
1. Stripe Dashboard → Webhooks → endpoint luna-beta → onglet "Livraisons"
2. Trouver l'événement `customer.subscription.created` ou `invoice.payment_succeeded`
3. Si "Échec de livraison" → cliquer sur "Renvoyer"
4. Si le renvoi échoue → vérifier que le serveur répond bien sur `/api/stripe/webhook`

**Activation manuelle via l'admin :**
1. Dashboard admin → onglet Clients
2. Trouver le client → modifier son plan manuellement

### Les plans n'apparaissent pas sur la page de tarification

**Cause :** Les produits Stripe n'ont pas été créés, ou les IDs sont mauvais.

**Solution :**
```bash
# Recréer les plans Stripe (idempotent — ne crée pas en double)
python3 stripe_setup.py
```
Ce script crée automatiquement les 3 plans (Essentiel 79€, Confort 149€, Premium 249€) et met à jour les IDs dans la configuration.

### Tester un paiement sans carte réelle

Utiliser la carte de test Stripe :
- Numéro : `4242 4242 4242 4242`
- Date : n'importe quelle date future (ex: `12/30`)
- CVC : n'importe quel code 3 chiffres (ex: `123`)
- Ce paiement est gratuit et ne débite rien

---

## 14. IP bannie — débannissement rapide

### Si c'est ton IP (fondateur)

Ton IPv6 peut changer automatiquement (c'est normal avec une box). La protection est basée sur le préfixe `2a02:8429:a9e4:f101:` — toute IP commençant par ces chiffres est immunisée contre tout ban, pour toujours.

**Si tu vois "IP bannie" malgré tout :**
→ **Tu es sur un réseau différent** (4G, réseau d'un ami, VPN). Repasser sur ton Wi-Fi habituel résout le problème immédiatement.

### Débannir une IP manuellement (via l'API)

```bash
# Remplacer XXX.XXX.XXX.XXX par l'IP à débannir
TOKEN="ton_token_admin"
curl -X POST \
  "https://luna-beta-674304336025.europe-west1.run.app/api/cortex/whitelist/XXX.XXX.XXX.XXX" \
  -H "Authorization: Bearer $TOKEN"
```

Cet appel débloque l'IP ET l'ajoute à la whitelist pour la durée de vie du container.

### Débannir via le dashboard admin

1. Dashboard admin → onglet **Alertes Cortex**
2. Trouver l'IP bannie dans la liste
3. Cliquer sur **Débannir**

### Trouver son IP actuelle

Aller sur `https://whatismyip.com` ou taper dans le navigateur : `https://api.ipify.org`

### Ajouter une IP à la protection permanente (dans le code)

Si une IP professionnelle doit être protégée définitivement (au-delà d'un redémarrage de container) :

1. Ouvrir `core/cortex/brain.py`
2. Trouver `_FOUNDER_IPS: frozenset = frozenset({`
3. Ajouter l'IP entre guillemets dans l'ensemble
4. Faire la même modification dans `core/cortex/vigil.py`
5. Redéployer

---

## 15. Gestion des quotas clients

### Vérifier le quota d'un client

Via le dashboard admin :
1. Admin → onglet **Clients** → chercher le client
2. Cliquer sur son nom → voir les quotas restants

Via l'API :
```bash
curl -H "Authorization: Bearer TOKEN_ADMIN" \
  "https://luna-beta-674304336025.europe-west1.run.app/api/admin/quota/EMAIL_CLIENT"
```

### Réinitialiser manuellement les quotas d'un client

**Cas d'usage :** Le client a eu un problème technique et a perdu ses minutes injustement.

Via le dashboard admin :
1. Admin → onglet Clients → trouver le client
2. Cliquer → **Réinitialiser les quotas**

Via l'API :
```bash
curl -X POST \
  "https://luna-beta-674304336025.europe-west1.run.app/api/admin/quota/reset/EMAIL_CLIENT" \
  -H "Authorization: Bearer TOKEN_ADMIN"
```

### Modifier les limites de quota globalement

Les limites sont définies dans `luna_web.py` — chercher `QUOTA_PLANS` ou `QuotaGuard`. Modifier les valeurs et redéployer.

| Plan | Voix (secondes) | Visio (secondes) | SMS |
|---|---|---|---|
| essentiel | 2400 (40 min) | 720 (12 min) | 25 |
| confort | 6000 (100 min) | 1680 (28 min) | 50 |
| premium | 10800 (180 min) | 3300 (55 min) | 100 |

**Attention :** Modifier les quotas affecte TOUS les clients de ce plan.

### Quand un client dit "mes quotas sont épuisés trop vite"

1. Vérifier s'il y a eu des appels anormalement longs (logs → `visio_session`)
2. Vérifier si le compteur a été correctement décrémenté (parfois une reconnexion compte double)
3. En cas de doute → réinitialiser et surveiller

### Réinitialisation automatique mensuelle

Les quotas se réinitialisent automatiquement via le webhook Stripe à chaque renouvellement d'abonnement. Si un client renouvelle mais que ses quotas ne se réinitialisent pas :
1. Stripe Dashboard → Webhooks → chercher `invoice.payment_succeeded` pour ce client
2. Renvoyer l'événement manuellement

---

## 16. Redis — sauvegarde, restauration, nettoyage

Redis stocke : les sessions utilisateurs, la mémoire long-terme de Luna, les quotas, les IPs whitelistées.  
**Redis se vide à chaque redémarrage du container** (sauf si configuré avec persistence).

### Vérifier l'état de Redis

```bash
# Connexion Redis CLI (sur le serveur ou en local si tunnel)
redis-cli ping
# Réponse attendue : PONG

# Voir la taille de la base
redis-cli DBSIZE
# Exemple : 247 (nombre de clés stockées)

# Voir les 10 premières clés
redis-cli KEYS "*" | head -10
```

### Sauvegarder Redis manuellement

```bash
# Déclencher une sauvegarde immédiate
redis-cli BGSAVE
# Redis sauvegarde dans /var/lib/redis/dump.rdb (ou le chemin configuré)

# Copier le fichier de sauvegarde
cp /var/lib/redis/dump.rdb /backup/redis-$(date +%Y%m%d).rdb
```

### Restaurer Redis depuis une sauvegarde

```bash
# Arrêter Redis
sudo systemctl stop redis

# Remplacer le dump
cp /backup/redis-YYYYMMDD.rdb /var/lib/redis/dump.rdb

# Redémarrer Redis
sudo systemctl start redis
```

### Nettoyer Redis (vider une clé spécifique)

```bash
# Voir le contenu d'une clé
redis-cli GET "session:EMAIL_UTILISATEUR"

# Supprimer une clé spécifique
redis-cli DEL "session:EMAIL_UTILISATEUR"

# Supprimer toutes les sessions (⚠️ déconnecte tout le monde)
redis-cli KEYS "session:*" | xargs redis-cli DEL
```

### Vider toute la base Redis (⚠️ DANGER)

```bash
# ATTENTION : supprime TOUT (sessions, mémoire, quotas, whitelist IPs)
redis-cli FLUSHALL
```
→ Utiliser uniquement en cas d'urgence ou pour repartir de zéro. Luna oubliera tous ses clients.

### Problème : Redis refuse les connexions

```bash
# Vérifier que Redis tourne
sudo systemctl status redis

# Redémarrer Redis
sudo systemctl restart redis

# Vérifier le port
redis-cli -p 6379 ping
```

---

## 17. Procédures d'urgence

### Urgence 1 — Le serveur est attaqué (DDoS ou scan massif)

**Symptômes :** Logs saturés d'erreurs Cortex, serveur lent ou non réactif, centaines de requêtes suspectes par seconde.

**Procédure :**
1. **Ne pas paniquer** — Cortex gère automatiquement la plupart des attaques
2. Vérifier les logs → les IPs d'attaque sont-elles déjà bannies ?
3. Si l'attaque continue → activer le **mode bouclier** (Shield Mode) :
```bash
curl -X POST \
  "https://luna-beta-674304336025.europe-west1.run.app/api/cortex/shield/on" \
  -H "Authorization: Bearer TOKEN_ADMIN"
```
En mode bouclier, seules les IPs whitelistées peuvent accéder au serveur.
4. Une fois l'attaque passée, désactiver :
```bash
curl -X POST \
  "https://luna-beta-674304336025.europe-west1.run.app/api/cortex/shield/off" \
  -H "Authorization: Bearer TOKEN_ADMIN"
```

---

### Urgence 2 — Une clé API a été compromise (volée ou exposée)

**Si une clé est exposée sur GitHub ou ailleurs :**

1. **Révoquer immédiatement** la clé sur le service concerné :
   - OpenAI : platform.openai.com → API Keys → Delete
   - Tavus : dashboard.tavus.io → Settings → API Keys
   - Twilio : console.twilio.com → Account → Auth Tokens
   - Stripe : dashboard.stripe.com → Developers → API Keys

2. **Générer une nouvelle clé** sur le même service

3. **Mettre à jour la configuration** Cloud Run :
   - Cloud Run → luna-beta → Modifier et déployer → Variables d'environnement

4. **Vérifier les logs Stripe** s'il s'agit de la clé Stripe — des paiements frauduleux ont-ils eu lieu ?

5. **Vérifier la facturation OpenAI** — des requêtes non autorisées ont-elles été effectuées ?

---

### Urgence 3 — La version en production est cassée

**Symptôme :** Le dernier déploiement a cassé quelque chose d'important.

**Procédure de rollback en 2 minutes :**
1. Cloud Run → luna-beta → onglet **Révisions**
2. Identifier la dernière révision stable (avant le déploiement cassé)
3. Cliquer sur les 3 points → **Modifier le trafic**
4. Mettre 100% sur l'ancienne révision → **Enregistrer**

Le rollback est instantané (moins de 30 secondes).

---

### Urgence 4 — Quelqu'un a accès à l'admin sans autorisation

1. **Changer `JWT_SECRET_KEY`** immédiatement (invalide tous les tokens existants) :
   - Cloud Run → luna-beta → Modifier et déployer → Variables d'environnement → `JWT_SECRET_KEY`
   - Générer une nouvelle clé : `openssl rand -hex 32`
   - **Attention :** cela déconnecte aussi les utilisateurs légitimes
2. **Changer le mot de passe admin** dans la configuration
3. **Vérifier les logs** pour voir ce qui a été fait avec l'accès non autorisé

---

### Urgence 5 — Factory Reset (repartir de zéro)

**Cas d'usage :** L'exploitant veut transférer le serveur ou repartir entièrement.

**Prérequis :** Avoir le `RESET_CODE` (affiché une seule fois lors de la signature du PV de recette — dans le certificat DOCX).

```bash
# Sur la machine de développement, dans le dossier luna-server/
python3 tools/factory_reset.py --code VOTRE_RESET_CODE_ICI
```

**Ce que ça fait :**
- Supprime `pv_lock.json` (déverrouille le serveur)
- Le serveur repasse en mode setup (page setup.html)
- La clé fondateur (SETUP_OPENAI_API_KEY) peut être réutilisée

---

## 18. Maintenance mensuelle

### À faire le 1er de chaque mois

**Vérifications financières (5 minutes)**
- [ ] Consulter dashboard.stripe.com → CA du mois → noter le chiffre
- [ ] Vérifier le solde Twilio → recharger si < 10$
- [ ] Vérifier les crédits OpenAI → recharger si < 20$
- [ ] Vérifier que les webhooks Stripe fonctionnent (onglet Webhooks → dernières livraisons)

**Vérifications techniques (10 minutes)**
- [ ] Ouvrir `/health` → vérifier `{"status":"ok"}`
- [ ] Envoyer "Bonjour" à Luna → vérifier que la réponse arrive
- [ ] Vérifier les logs Cloud Run des 7 derniers jours → y a-t-il des erreurs récurrentes ?
- [ ] Vérifier la version déployée → est-elle à jour avec le code git ?
- [ ] Vérifier que Redis répond → `redis-cli ping` doit répondre `PONG`

**Sécurité (5 minutes)**
- [ ] Vérifier les logs Cortex → y a-t-il des patterns d'attaque nouveaux ?
- [ ] Vérifier les IPs bannies → en a-t-on banni par erreur une IP légitime ?
- [ ] Vérifier que les IPs fondateur sont toujours dans le code (`core/cortex/brain.py`)

**Sauvegarde (5 minutes)**
- [ ] `git add -A && git commit -m "État stable [mois/année]"` → sauvegarder le code
- [ ] `redis-cli BGSAVE` → sauvegarder Redis
- [ ] Copier le `pv_lock.json` en lieu sûr (contient la preuve de signature)

---

### À faire après chaque déploiement (voir section 8)

---

## 19. Règles à ne jamais oublier

### Règle 1 — Toujours bumper le Service Worker après avoir modifié `simli.html` ou `index.html`

**Fichier :** `static/sw.js` — ligne 2  
```javascript
var CACHE_NAME = "luna-v46";  // ← incrémenter ce numéro à chaque modification
```
**Pourquoi ?** Si on oublie, les utilisateurs gardent l'ancienne version en cache pendant des jours et ne voient pas les changements.  
**Comment ?** Remplacer `v46` par `v47`, `v48`, etc. à chaque modification de `simli.html` ou `index.html`.

---

### Règle 2 — Ne jamais committer le fichier `.env`

**Pourquoi ?** Le `.env` contient toutes les clés API (OpenAI, Tavus, Twilio, Stripe...). Le mettre sur GitHub = brèche de sécurité immédiate. Si cela arrive : révoquer TOUTES les clés dans la minute.  
**Vérification :** `.env` doit être dans `.gitignore`. Vérifier avant chaque commit.

---

### Règle 3 — Ne jamais modifier `JWT_SECRET_KEY` en production sans prévenir

**Pourquoi ?** Cette clé signe tous les tokens d'authentification. La changer en production déconnecte instantanément tous les utilisateurs actifs (leurs tokens deviennent invalides).  
**Exception :** En cas de compromission de la clé (section 17, Urgence 4).

---

### Règle 4 — Toujours tester après un déploiement

**Pourquoi ?** Un déploiement peut réussir techniquement (Cloud Run dit "OK") mais casser une fonctionnalité.  
**Combien de temps ?** 10 minutes suffisent pour faire la checklist de base (section 8).

---

### Règle 5 — Les IPs fondateur doivent être dans le code, pas seulement en base

**Pourquoi ?** La whitelist Redis disparaît à chaque redémarrage du container.  
**Où ?** Les protections permanentes doivent être dans `core/cortex/vigil.py` et `core/cortex/brain.py`.  
**Comment vérifier ?** Chercher `_FOUNDER_IP_PREFIXES` dans ces deux fichiers.

---

### Règle 6 — Ne pas toucher au prompt système sans tester

**Pourquoi ?** Le prompt de Luna (`luna_web.py` ligne 787) est très sensible. Une petite modification peut rendre Luna incohérente, trop restrictive, ou au contraire trop permissive.  
**Quoi tester après ?** Au minimum 5 conversations différentes avec des cas limites.

---

### Règle 7 — Sauvegarder avant toute modification importante

```bash
git add -A
git commit -m "Sauvegarde avant modification : [décrire ce qu'on va changer]"
```
**Pourquoi ?** En cas de problème, on peut revenir à cet état avec `git revert`.  
**Et la révision Cloud Run ?** La noter aussi (section 7) pour pouvoir faire un rollback rapide.

---

### Règle 8 — Luna ne peut pas rejoindre Zoom

**Pourquoi ?** Luna est basée sur Daily.co (WebRTC). Zoom utilise son propre protocole fermé. Il n'existe pas d'intégration directe sans développement spécifique de plusieurs mois.  
**Conséquence :** Ne pas promettre cette fonctionnalité aux clients.

---

### Règle 9 — Ne jamais utiliser `redis-cli FLUSHALL` en production sans sauvegarde

**Pourquoi ?** Cette commande supprime TOUT : sessions, mémoire de Luna, quotas, whitelist IPs.  
**Si c'est indispensable :** Faire un `BGSAVE` d'abord et conserver le fichier `dump.rdb`.

---

### Règle 10 — Les quotas sont en secondes dans le code, en minutes dans la doc

**Pourquoi ?** Le code stocke les quotas en secondes (2400 = 40 minutes). Si on modifie une valeur dans le code sans faire la conversion, les quotas seront complètement faux.  
**Formule :** minutes × 60 = secondes à entrer dans le code.

---

### Règle 11 — Toujours vérifier le mode Stripe (test vs live) avant de déployer

**Pourquoi ?** `sk_test_...` = les vrais clients ne peuvent pas payer. `sk_live_...` = production.  
**Risque inverse :** Développer et tester avec `sk_live_` peut créer de vrais paiements accidentels.

---

### Règle 12 — Le PV de recette est irréversible (sauf RESET_CODE)

**Pourquoi ?** Une fois signé, le serveur se verrouille. La seule façon de "déverrouiller" est le `RESET_CODE` (un code 32 caractères, généré une seule fois et jamais ré-affichable).  
**Où est-il ?** Dans le certificat DOCX téléchargé lors de la signature du PV (`/api/admin/certificate`).  
**Si on l'a perdu :** Contacter le fondateur — factory reset nécessite le code.

---

## 20. Journal des incidents

> À compléter avec les incidents rencontrés au fil du temps. Format : Date — Symptôme — Cause — Solution.

| Date | Symptôme | Cause | Solution |
|---|---|---|---|
| 2026-05-16 | IP fondateur bannie | IPv6 rotation → nouvelle adresse non reconnue | Ajout protection par préfixe `/64` dans `vigil.py` et `brain.py` |
| 2026-05-16 | Prise de notes vide | Filtre `confidence > 0.4` trop strict sur Firefox/Safari | Suppression du filtre confidence dans `simli.html` |
| 2026-05-16 | Luna ne sait pas qu'elle peut voir | `_captureAndSend()` ne notifiait pas Luna via `conversation.echo` | Ajout notification `_visionNotified` (1 fois par appel) |
| 2026-05-16 | Bouton muet ne fonctionne plus | Contexte de conversation Tavus perdu | Fix via `conversation.echo` + reconnexion en cas d'échec |

---

*Document créé le 17 mai 2026. À compléter avec les incidents rencontrés au fil du temps.*
