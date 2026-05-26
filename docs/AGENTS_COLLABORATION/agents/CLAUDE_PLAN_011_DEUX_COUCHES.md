# Claude — Plan deux couches Objectif 011

**Date** : 2026-05-26  
**Contexte** : réponse à `NOTE_011_MODE_FONDATEUR_EXPLOITANT.md`  
**Statut** : plan soumis à validation Ludovic — aucun code avant accord

---

## Principe

L'onglet Services expose deux types d'actions :

- **Lecture / recherche** : météo, actualités, recherche web, lieux, vols dispo, hôtels dispo — jamais de dépense, toujours auditables.
- **Action irréversible** : SMS réel, email réel, appel réel, réservation payante, alerte urgence — nécessitent soit une sandbox soit une validation explicite.

Le plan sépare ces deux couches sans refonte.

---

## Couche 1 — Audit / sandbox fondateur

**Objectif** : Ludovic peut valider chaque service sans engager de dépense, sans envoyer de message réel, sans réserver quoi que ce soit.

### Services sûrs à auditer maintenant (aucune action)

| Service | Risque | Ce qu'on valide |
|---|---|---|
| Météo | 0 | Données correctes, affichage carte |
| Actualités | 0 | Flux RSS reçus, catégories |
| Recherche web | 0 | Serper retourne des résultats |
| Recherche lieux | 0 | Serper Places, géolocalisation |
| Recherche vols | 0 | Duffel retourne des offres sans réserver |
| Recherche hôtels | 0 | Duffel retourne des chambres sans réserver |
| Recherche restaurant | 0 | Serper fallback (TheFork absent) |
| Contacts | 0 | Liste confiance affichée |
| Note | 0 | Stockée dans Redis |
| Rappel | 0 | Stocké dans Redis |
| Document | 0 | Généré par OpenAI, téléchargeable |
| Stats/Missions/Badges | 0 | Lecture Redis |

**Verdict** : 12 services sur 19 sont auditables sans aucune précaution supplémentaire.

### Services sensibles — ce que j'ai vérifié dans le code

| Service | Duffel/Twilio mode actuel | Sandbox disponible ? |
|---|---|---|
| `book_flight` | Duffel live (`_conc_book_flight`) | Duffel a un mode test — clé live dans `.env` actuel |
| `book_hotel` | Duffel live (`_conc_book_hotel`) | Idem |
| `send_sms` | Twilio live (numéro +17173409138) | Twilio a un mode test mais pas activé |
| `send_email` | À vérifier côté serveur | ? |
| `call_contact` | Twilio live | Pas de sandbox activé |
| `alert_contacts` | Twilio live | Déjà protégé par `_showConfirm` |

**Ce que je propose pour auditer sans dépenser :**

- Pour `send_sms` : le quota est vérifié. Les contacts de confiance sont limités (ton propre numéro). Un SMS de test vers ton numéro = quelques centimes Twilio. Pas bloquant.
- Pour `book_flight` / `book_hotel` : **ne pas cliquer "Réserver"**. La recherche est gratuite. Valider seulement que les offres s'affichent correctement.
- Pour `call_contact` / `alert_contacts` : **ne pas déclencher**. Valider que les modales et formulaires s'ouvrent correctement.

---

## Couche 2 — Activation exploitant

**Objectif** : quand un exploitant arrive, il branche ses clés et ses moyens de paiement sans toucher au code.

### Ce qui est déjà en place

- Clés dans `.env` côté serveur Cloud Run uniquement — jamais dans l'APK ni `index.html` ✅
- Twilio : compte exploitant → remplace `TWILIO_*` dans `.env` ✅
- Duffel : compte exploitant → remplace `DUFFEL_ACCESS_TOKEN` dans `.env` ✅
- Serper : compte exploitant → remplace `SERPER_API_KEY` ✅
- Quotas SMS/voix/visio : configurables par plan dans MemoryManager ✅

### Ce qui manque pour un exploitant autonome

| Manque | Impact | Priorité |
|---|---|---|
| Mode `dry_run` sur `book_flight` / `book_hotel` | Fondateur ne peut pas tester sans Duffel live | Moyen |
| Validation exploitant avant `send_email` hors contacts | Email vers n'importe qui | Élevé |
| Confirmation client sur `send_sms` | SMS envoyé sans dialog | Élevé |
| TheFork non configuré | Restaurant dégradé en Serper | Faible (fonctionnel) |
| Cockpit : trace des actions Services | Fondateur ne voit pas ce qui a été envoyé | Moyen |

---

## Réponses aux 4 questions Ludovic

| Question | Réponse |
|---|---|
| Est-ce testable sans dépense fondateur ? | Oui pour 12/19 services. Les 7 sensibles : recherche safe, action à ne pas déclencher en audit |
| Est-ce prêt pour exploitant avec ses moyens de paiement ? | Oui — clés dans `.env` Cloud Run, jamais exposées. L'exploitant remplace ses variables |
| Est-ce protégé contre l'exposition code/secrets ? | Oui — clés serveur uniquement, APK ne contient aucune clé |
| Est-ce observable dans cockpit ? | Partiellement — SMS/appel tracés. Actions conciergerie non tracées |

---

## Corrections que je propose (soumises à validation)

**Priorité haute — à faire avant exploitation :**

1. **`send_sms` côté client** : ajouter `_showConfirm()` avant envoi (1 ligne JS)
2. **`send_email` côté serveur** : vérifier que `_tool_send_email` n'envoie qu'à des contacts validés

**Priorité moyenne — à faire avant onboarding exploitant :**

3. **Mode `dry_run` `book_flight`/`book_hotel`** : flag env `DUFFEL_DRY_RUN=true` → retourner une réponse simulée sans appel Duffel
4. **Trace cockpit Services** : journaliser les actions conciergerie dans Redis (qui a fait quoi, quand)

**Priorité faible :**

5. **TheFork** : brancher la clé quand un compte TheFork sera disponible

---

## Je n'implémente rien avant

- Validation Ludovic sur ce plan
- Confirmation : `book_flight` en production Duffel = commande réelle ou intention seulement ?
