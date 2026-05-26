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

## Ce que je propose (après avis équipe)

**Corrections prioritaires :**

1. **`send_sms` — ajouter confirmation client** : même pattern que `alert_contacts` (`_showConfirm`). Une ligne JS.  
2. **`send_email` — valider côté serveur** : vérifier que `_tool_send_email` ne permet pas d'envoyer à une adresse hors contacts.  
3. **`book_flight` — clarifier Duffel** : documenter si c'est une commande réelle ou une réservation test.

**Pas de correction nécessaire :**
- Météo, actualités, recherche web, recherche lieux : 100 % safe, rien à faire.
- `alert_contacts` : déjà protégé correctement.
- Services internes Redis : aucun risque.

---

## Je n'agis pas avant

1. Avis DeepSeek sur le flux JS complet (cartes → handlers → résultats)
2. Avis Kimi sur la promesse utilisateur et les textes des actions sensibles
3. Avis Cursor sur l'UI mobile des cartes et modales
4. Clarification Ludovic sur `book_flight` / Duffel réel ou test
5. Validation Ludovic sur les corrections à implémenter
