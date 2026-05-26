# Claude — Avis Objectif 011

**Date** : 2026-05-26  
**Objectif** : Audit complet onglet Services / Conciergerie  
**Statut** : audit terminé — en attente avis DeepSeek/Kimi/Cursor avant toute correction

---

## Architecture technique

### Flux complet

```
APK → _concDirect(action, params) → POST /api/concierge/action
     → DISPATCHERS[action] → _tool_xxx() → réponse JSON
     → renderer JS → affichage cartes/résultats
```

Un seul endpoint : `POST /api/concierge/action` (`luna_web.py` ligne 13558).  
19 actions enregistrées dans le dispatcher (ligne 13570–13594).

---

## Cartographie complète des services

### Services sans clé API (gratuits, toujours disponibles)

| Service | Action | Implémentation | Statut |
|---|---|---|---|
| Météo | `weather` | wttr.in + Open-Meteo (fallback) | ✅ fonctionnel |
| Actualités | `news` | Flux RSS français | ✅ fonctionnel |

### Services avec Serper (clé configurée)

| Service | Action | Statut |
|---|---|---|
| Recherche web | `search_web` | ✅ fonctionnel |
| Recherche lieux | `search_places` | ✅ fonctionnel |

### Services avec Duffel (clé configurée)

| Service | Action | Statut |
|---|---|---|
| Recherche vols | `search_flights` | ✅ fonctionnel |
| Recherche hôtels | `search_hotels` | ✅ fonctionnel |
| Réservation vol | `book_flight` | ⚠️ **SENSIBLE** — voir ci-dessous |
| Réservation hôtel | `book_hotel` | ⚠️ **SENSIBLE** — voir ci-dessous |

### Services avec Twilio (clé configurée)

| Service | Action | Statut |
|---|---|---|
| SMS | `send_sms` | ✅ / ⚠️ **SENSIBLE** |
| Alerte urgence | `alert_contacts` | ✅ / ⚠️ **SENSIBLE** |
| Appel contact | `call_contact` | ✅ / ⚠️ **SENSIBLE** |

### Service TheFork (clé NON configurée)

| Service | Action | Statut |
|---|---|---|
| Restaurant | `book_restaurant` | ⚠️ **DÉGRADÉ** — fallback sur `search_places` |

TheFork non configuré dans `.env` → le service tombe automatiquement sur Serper Places.  
L'utilisateur reçoit des résultats mais ne peut pas réserver directement.

### Services internes (Redis / MemoryManager)

| Service | Action | Statut |
|---|---|---|
| Contacts | `get_contacts` | ✅ si profil complet |
| Rappels | `get_reminders` / `add_reminder` | ✅ |
| Note | `create_note` | ✅ |
| Générer document | `generate_document` | ✅ (OpenAI) |
| Stats / Missions / Badges | `get_player_stats` etc. | ✅ |

---

## Garde-fous existants — ce qui est déjà protégé

### `alert_contacts` (alerte urgence)

Côté client : `_showConfirm()` avec dialog "Confirmer ?" avant exécution (ligne 3389).  
Côté serveur : vérifie Twilio configuré + liste contacts de confiance.  
**Verdict : correctement gardé.**

### `send_sms`

Côté serveur : quota SMS vérifié (`_quota_guard`), contact doit être dans la liste de confiance.  
Côté client : **PAS de confirmation** — le formulaire envoie directement après "Envoyer" (ligne 3294).  
**Risque** : SMS envoyé sans demande de confirmation à l'utilisateur.

### `book_flight` / `book_hotel` via Duffel

Duffel permet de rechercher ET de réserver (débiter). Le dispatcher expose `book_flight` et `book_hotel`.  
La recherche (`search_flights`, `search_hotels`) est safe. La réservation réelle :  
- Un bouton "Réserver" dans l'UI (ligne 3514) appelle `book_flight` avec un `offer_id`.  
- **Je ne sais pas si Duffel débite réellement ou juste confirme une intention.**  
- À vérifier avec Ludovic : est-ce que `book_flight` crée un ordre payant ?

### `send_email`

L'email du destinataire est saisi librement dans le formulaire (pas forcément un contact de confiance).  
Côté serveur, il faut vérifier si `_tool_send_email` valide le destinataire ou envoie vers n'importe quelle adresse.

---

## Risques classés

| Niveau | Action | Problème |
|---|---|---|
| 🔴 Critique | `book_flight` / `book_hotel` | Peut créer une commande Duffel payante — à clarifier |
| 🟠 Élevé | `send_sms` | Pas de confirmation côté client avant envoi réel |
| 🟠 Élevé | `send_email` | Destinataire libre — peut envoyer hors liste contacts |
| 🟡 Moyen | `call_contact` | Appel réel, mais déclenché via modale vocale (OK) |
| 🟡 Moyen | `book_restaurant` | Dégradé (TheFork absent) — résultats Serper sans réservation |
| 🟢 Faible | Tout le reste | Pas d'action irréversible |

---

---

## Architecture à deux couches (Clarification Ludovic)

### Contexte

Ludovic teste comme **fondateur**, pas comme entreprise exploitante.

Cela signifie :
- Ludovic ne doit pas engager de dépenses personnelles pour tester vols, hôtels, SMS, etc.
- Le but n'est pas de réserver réellement maintenant, mais de **prouver que le parcours sera opérationnel** quand un exploitant arrivera avec ses clés, ses moyens de paiement et son dashboard.

### Les 4 questions clés pour chaque service sensible

Pour chaque action sensible (SMS, Email, Appel, Urgence, Vol, Hôtel, Paiement) :

1. **Est-ce testable sans dépense fondateur ?**
   - Mode sandbox ou dry-run disponible ?
   - Confirmation avant action réelle ?
   - Trace observable ?

2. **Est-ce prêt pour un exploitant avec ses moyens de paiement ?**
   - Endpoint prêt à recevoir clés exploitant ?
   - Configuration Stripe/Duffel/Twilio par exploitant ?
   - Dashboard pour exploitant (logs, quotas, monitoring) ?

3. **Est-ce protégé contre l'exposition du code et des secrets ?**
   - Secrets jamais envoyés en frontend ou APK ?
   - Code opaque pour l'exploitant (pas de fork possible) ?
   - Clés stockées côté serveur uniquement ?

4. **Est-ce observable dans le monitoring/cockpit ?**
   - Chaque action journalisée ?
   - Cockpit fondateur voit les erreurs ?
   - Cockpit exploitant voit ses transactions et quotas ?

### Plan d'implémentation à deux couches

#### 1. Couche audit/sandbox fondateur

**Objectif** : Ludovic teste sans débiter, sans action irréversible.

Pour chaque service payant ou sensible :
- Recherche → OK (aucune charge)
- Panier / intention → OK si sandbox garanti
- Confirmation finale / débit → BLOQUÉ (Ludovic ne paie pas)

Services OK en audit :
- ✅ Météo, Actualités, Recherche web/lieux
- ✅ Recherche vols/hôtels (affichage seulement)
- ✅ Stats, Missions, Badges, Contacts, Rappels, Notes

Services à tester avec confirmation :
- ⚠️ SMS / Email / Appel (modale de confirmation)
- ⚠️ Alerte urgence (confirmation 2x)

Services à tester en sandbox seulement :
- 🔴 Réservation vol / hôtel (si Duffel sandbox disponible)
- 🔴 Paiement (si Stripe dev mode)
- 🔴 Réservation restaurant (si TheFork sandbox)

#### 2. Couche exploitation/production exploitant

**Objectif** : Entreprise exploitante connecte ses moyens et fonctionne indépendamment.

Structure recommandée :
```
1. Exploitant reçoit accès dashboard Luna
2. Exploitant configure ses clés (Stripe, Twilio, Duffel, Serper)
3. Exploitant définit quotas et confirmations (SMS/jour, appels/jour, etc.)
4. Exploitant voit tous les logs et transactions
5. Luna exécute actions avec clés exploitant, jamais clés fondateur
```

**Code requiert :**
- Configuration par tenant/exploitant (multi-tenant)
- Séparation secrets fondateur vs exploitant
- Endpoint de gestion des clés pour exploitant (sécurisé)
- Dashboard exploitant distinct (cockpit alternatif)

---

## Ce que Claude doit proposer

**Plan de correction par priorité et par couche :**

### Lot 1 — Audit/Sandbox (Ludovic test maintenant)

- SMS : ajouter confirmation modale (1 ligne JS)
- Email : valider destinataire côté serveur
- Alerte urgence : garder confirmation 2x existante
- Tous les autres services : vérifier affichage/erreurs

**Livrable** : Ludovic peut tester sans débiter.

### Lot 2 — Infrastructure exploitant (préparation future)

- Ajouter gestion tenant/clés par exploitant
- Créer endpoint config clés exploitant
- Documenter étapes activation exploitant

**Livrable** : Route prête pour futur exploitant.

### Lot 3 — Optimisations (après Ludovic valide)

- Cache résultats recherches
- Amélioration messages erreur
- Monitoring détaillé transactions

---

## Ce que je propose maintenant

**Corrections prioritaires (Lot 1, mode audit):**

1. **`send_sms` — ajouter confirmation client** : même pattern que `alert_contacts` (`_showConfirm`). Une ligne JS.  
2. **`send_email` — valider côté serveur** : vérifier que `_tool_send_email` ne permet pas d'envoyer à une adresse hors contacts.  
3. **`book_flight` — clarifier Duffel** : documenter si c'est une commande réelle ou une réservation test. Si réel, créer un mode sandbox.
4. **Tous les services — vérifier message d'erreur** : existe-t-il un fallback lisible si API externe down ?

**Pas de correction nécessaire (Lot 1):**
- Météo, actualités, recherche web, recherche lieux : 100 % safe.
- `alert_contacts` : déjà protégé.
- Services internes Redis : aucun risque.

**Infrastructure exploitant (Lot 2, futur):**
- Configuration par tenant (clés, quotas, moyens de paiement)
- Dashboard exploitant séparé
- API gestion clés

---

## Validation avant implémentation

1. ✅ Avis DeepSeek : flux JS complet (cartes → handlers → résultats)
2. ✅ Avis Kimi : promesse utilisateur et textes sensibles
3. ✅ Avis Cursor : UI mobile cartes et modales
4. ⏳ Ludovic : valide le plan à deux couches (audit vs exploitation)
5. ⏳ Ludovic : approuve Lot 1 avant code
