# Audit Objectif 011 — Services / Conciergerie

> Date : 2026-05-26
> Auteur : Kimi (audit code)
> Portée : `luna_web.py` (serveur) + `static/index.html` (client)

---

## Méthode

Audit statique du code. Pas de test téléphone. Pas de test API externe.
Objectif : classifier les services par niveau de risque et vérifier la présence de garde-fous côté client et serveur.

---

## 1. Services non sensibles — lecture seule, testables sans risque

Ces services ne modifient aucune donnée externe ni interne critique. Ils peuvent être testés librement.

| Service | Type | Effet de bord | Garde-fou client | Garde-fou serveur | Statut |
|---|---|---|---|---|---|
| `get_weather` | API externe (wttr.in / Open-Meteo) | Aucun | N/A | Timeout 10s, fallback | ✅ Sûr |
| `get_news` | RSS (France Info / Le Monde) | Aucun | N/A | Timeout 10s, limité à 10 articles | ✅ Sûr |
| `search_web` | API externe | Aucun | N/A | Timeout, rate limit implicite | ✅ Sûr |
| `search_places` | API externe | Aucun | N/A | Timeout, catégorie contrôlée | ✅ Sûr |
| `get_page_info` | Scraping web | Aucun | N/A | Timeout, length limit | ✅ Sûr |
| `get_player_stats` | Lecture Redis | Aucun | N/A | Check `_GAMIFICATION_AVAILABLE` | ✅ Sûr |
| `get_active_missions` | Lecture Redis | Aucun | N/A | Check `_GAMIFICATION_AVAILABLE` | ✅ Sûr |
| `get_badges` | Lecture Redis | Aucun | N/A | Check `_GAMIFICATION_AVAILABLE` | ✅ Sûr |
| `get_contacts` | Lecture Redis | Aucun | N/A | Via `mgr.list_trusted_contacts()` | ✅ Sûr |
| `get_friends_online` | Lecture Redis | Aucun | N/A | Via gamification | ✅ Sûr |

**Recommandation** : ces services peuvent être validés dès maintenant par tests fonctionnels simples.

---

## 2. Services sensibles — garde-fous déjà en place

Ces services déclenchent des actions réelles. Ils ont déjà des protections.

| Service | Type | Confirmation client | Garde-fou serveur | Log/trace | Statut |
|---|---|---|---|---|---|
| `send_sms` | Action Twilio | ✅ `_showConfirm` (contact + contenu) | Contact de confiance requis ; numéros d'urgence bloqués | `mgr.log_event` + `_tracked_sms_send` | ✅ Protégé |
| `send_email` | Action SMTP/SendGrid | ✅ `_showConfirm` (contact + objet + contenu) | Refus si `contact_name` absent de la liste de confiance ; log warning email tronqué | `mgr.log_event` | ✅ Protégé |
| `alert_contacts` | SMS massif urgence | ✅ `_showConfirm` (message explicite) | Limité aux contacts de confiance ; ajout GPS + heure | `_tracked_sms_send` + log | ✅ Protégé |
| `book_flight` | Réservation Duffel | ✅ `_showConfirm` (prix + infos profil) | Pré-remplissage profil ; vérification nom/email | `logger.info` | ⚠️ **Pas de sandbox** |
| `book_hotel` | Réservation Duffel | ✅ `_showConfirm` (nom hôtel + infos profil) | Pré-remplissage profil ; vérification nom/email | `logger.info` | ⚠️ **Pas de sandbox** |
| `request_payment` | Paiement Stripe | ❌ **Pas de confirmation client directe** (appelé par LLM) | Plafond mensuel + budget max + vérification carte Stripe + clé Stripe requise | `logger.info` | ⚠️ **Pas de sandbox** |

**Points d'attention** :
- `book_flight` et `book_hotel` : malgré la confirmation client, il n'y a **aucun mode sandbox/dry-run**. En mode test/exploitation, une réservation réelle peut être créée chez Duffel.
- `request_payment` : la confirmation repose sur le LLM (il doit demander au souscripteur). Il n'y a pas de `_showConfirm` côté frontend. Le plafond budgétaire est le seul garde-fou automatique.

---

## 3. Services sensibles — garde-fous À RENFORCER

Ces services manquent de confirmations explicites ou de traces d'audit uniformes.

| Service | Type | Confirmation client | Garde-fou serveur | Log/trace | Risque | Action demandée |
|---|---|---|---|---|---|---|
| `call_contact` | Appel Twilio vocal | ⚠️ **Modal 2 étapes** (sélection contact + clic) mais **pas de `_showConfirm` explicite** avant l'appel | Numéros d'urgence bloqués ; contact de confiance ou numéro direct avec flag `is_admin_call` | `logger.info` + `_remoteLog` | Moyen | Ajouter `_showConfirm` dans `_confirmCallContact` |
| `invite_visio` | Visio Tavus/Simli | ⚠️ **Picker durée puis redirection immédiate** — pas de confirmation explicite | Génération URL limitée | `_remoteLog` | Moyen | Ajouter `_showConfirm` avant `window.location.replace` |
| `book_restaurant` | Recherche TheFork / fallback | Pas de réservation directe (fallback `search_places`) | N/A | `logger.info` | Faible | OK en l'état — ne réserve pas directement |

---

## 4. Services secrétariat (mode Secrétaire)

Ces services modifient des données internes (documents, budget, rappels). Ils ne touchent pas à des tiers.

| Service | Type | Risque | Statut |
|---|---|---|---|
| `get_documents_summary` | Lecture Redis | Faible | ✅ |
| `search_documents` | Lecture Redis | Faible | ✅ |
| `list_folders` | Lecture Redis | Faible | ✅ |
| `secretary_budget` | Lecture Redis | Faible | ✅ |
| `secretary_afford` | Calcul interne | Faible | ✅ |
| `secretary_add_expense` | Écriture Redis | Faible (données internes) | ✅ |
| `secretary_reminders` | Lecture Redis | Faible | ✅ |
| `secretary_add_reminder` | Écriture Redis | Faible (données internes) | ✅ |
| `secretary_search` | Recherche interne | Faible | ✅ |

---

## 5. Synthèse des risques critiques

| Risque | Gravité | Explication | Correctif proposé |
|---|---|---|---|
| **Pas de mode sandbox** | 🔴 Haute | `book_flight`, `book_hotel`, `request_payment` peuvent déclencher des actions réelles en mode test/exploitant | Ajouter `LUNA_SANDBOX_MODE=true` dans `.env` + wrapper qui simule les appels Duffel/Stripe au lieu de les exécuter |
| **Confirmation manquante call_contact** | 🟡 Moyenne | L'utilisateur peut appeler par inadvertance après avoir juste sélectionné un contact | Ajouter `_showConfirm` dans `_confirmCallContact` avant `startVoiceCall` |
| **Confirmation manquante invite_visio** | 🟡 Moyenne | La visio démarre immédiatement après choix de la durée | Ajouter `_showConfirm` dans `startCall` avant redirection |
| **Pas de log uniforme** | 🟡 Moyenne | Chaque service logge différemment (logger, _remoteLog, mgr.log_event) | Standardiser via `mgr.log_event` pour toutes les actions sensibles |

---

## 6. Plan de validation par lots (non destructifs)

### Lot A — Immédiat (aucun risque)
1. Tester `get_weather` avec et sans ville
2. Tester `get_news` par catégorie
3. Tester `search_web` avec requête simple
4. Tester `search_places` (autour de moi)
5. Tester `get_player_stats`, `get_active_missions`, `get_badges`

### Lot B — Actions protégées (avec confirmation)
6. Tester `send_sms` — vérifier que la confirmation s'affiche, vérifier le log serveur
7. Tester `send_email` — vérifier que la confirmation s'affiche, vérifier le refus hors contacts de confiance
8. Tester `alert_contacts` — vérifier la confirmation et le contenu du SMS

### Lot C — Réservations (nécessite sandbox)
9. ⚠️ **NE PAS TESTER** `book_flight` / `book_hotel` sans `LUNA_SANDBOX_MODE=true`
10. ⚠️ **NE PAS TESTER** `request_payment` sans `LUNA_SANDBOX_MODE=true`

### Lot D — Voix / Visio
11. Tester `call_contact` — vérifier le modal et le blocage des numéros d'urgence
12. Tester `invite_visio` — vérifier la durée et la redirection

---

## 7. Décisions attendues

1. **Valider le mode sandbox** : faut-il implémenter `LUNA_SANDBOX_MODE` maintenant ?
2. **Valider les confirmations manquantes** : faut-il ajouter `_showConfirm` sur `call_contact` et `invite_visio` ?
3. **Priorité** : Lot A d'abord, puis Lot B, puis sandbox avant Lot C.

---

*Ce document doit être mis à jour après chaque correction ou test réel.*
