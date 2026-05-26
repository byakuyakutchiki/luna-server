# Claude — Avis Objectif 011 — Audit Services / Conciergerie

**Date** : 2026-05-26
**Objectif** : Audit complet onglet Services / Conciergerie
**Rôle** : Lead technique final, synthèse et arbitrage architecture
**Règle absolue** : Audit avant action — aucun code majeur sans validation Ludovic

---

## Mission Claude

Produire la synthèse technique finale après réception des audits DeepSeek, Kimi et Cursor.

Claude ne doit PAS coder d'abord. Il doit :
1. Valider la réalité du code reportée par DeepSeek
2. Arbitrer les risques identifiés par Kimi
3. Décider des corrections minimales proposées par Cursor
4. Proposer un plan de correction par priorité
5. Exiger validation Ludovic avant implémentation

---

## Phase 1 — Audit de l'existant (avec DeepSeek)

### Questions à investiguer

**Frontend (`static/index.html`, onglet Services/Conciergerie)** :

1. **Inventaire des cartes** :
   - Combien de cartes visibles dans `tab-conciergerie` ?
   - Chaque carte a-t-elle un DOM unique (id, data-action, etc.) ?
   - Quel handler JavaScript est appelé au clic ?
   - Les paramètres sont-ils passés correctement ?

2. **Handlers et appels backend** :
   - Chaque handler appelle-t-il `/api/concierge/action` ?
   - Quels paramètres sont envoyés (action, payload) ?
   - Comment les résultats sont affichés ?
   - Existe-t-il une gestion d'erreur uniforme ?

3. **Rendus utilisateur** :
   - Quel JSON est attendu par le renderer ?
   - Comment s'affichent les résultats sur mobile (<400px) ?
   - Les textes sont-ils lisibles ou coupés ?
   - Existe-t-il une modale ou un inline display ?

**Backend (`luna_web.py`, `/api/concierge/action`)** :

1. **Actions implémentées** :
   - Quelles actions existent réellement dans le endpoint ?
   - Chaque action appelle-t-elle un tool ou une fonction dédiée ?
   - Quelles sont les dépendances externes (Serper, Duffel, Twilio, etc.) ?
   - Quels retours JSON sont générés pour chaque cas (succès, erreur, non configuré) ?

2. **Journalisation et remontée** :
   - Les erreurs remontent-elles au cockpit fondateur ?
   - Le cerveau APK reçoit-il les statuts de réussite/échec ?
   - Existe-t-il un journal des actions sensibles (SMS, email, appel) ?

### Livrables Phase 1

- Synthèse technique `CLAUDE_AUDIT_011_EXISTANT.md` contenant :
  - Liste complète cartes frontend → handlers JS → endpoint backend → tool Python
  - Schéma flux pour une action (requête → processing → résultat → affichage)
  - État des dépendances externes (présentes, absentes, optionnelles)
  - Cas d'erreur actuels (JSON d'erreur existant ?)
  - Points de coupure identifiés (UI cassée ? erreur silencieuse ? crash ?)

---

## Phase 2 — Classification des services par risque

Après réception des audits, classer les services :

| Service | Catégorie | Risque | État | Correction minimale |
|---|---|---|---|---|
| Méteo | Lecture seule | Bas | ? | ? |
| Actualités | Lecture seule | Bas | ? | ? |
| Recherche web | Requête externe | Moyen | ? | ? |
| Recherche vols | Requête Duffel | Moyen | ? | ? |
| Recherche hôtels | Requête Duffel | Moyen | ? | ? |
| Recherche restaurants | Requête Serper | Moyen | ? | ? |
| Autour de moi | Requête Serper | Moyen | ? | ? |
| SMS | Action réelle | CRITIQUE | ? | Validation obligatoire |
| Email | Action réelle | CRITIQUE | ? | Validation obligatoire |
| Appel | Action réelle | CRITIQUE | ? | Confirmation affichée |
| Visio Luna | Action externe | CRITIQUE | ? | Token JWT requis |
| Alerte urgence | Action réelle | CRITIQUE | ? | Confirmation 2x |
| Paiement | Action réelle | CRITIQUE | ? | Endpoint Stripe isolé |
| Réservation | Action réelle | CRITIQUE | ? | Validation Ludovic |
| Rappel | Création locale | Bas | ? | ? |
| Note | Création locale | Bas | ? | ? |
| Document | Génération | Moyen | ? | ? |
| Contacts | Requête DB | Bas | ? | ? |
| Formulaires | Redirection | Bas | ? | ? |
| Stats | Requête DB | Bas | ? | ? |
| Missions | Requête DB | Bas | ? | ? |
| Badges | Requête DB | Bas | ? | ? |
| Amis en ligne | Requête DB | Bas | ? | ? |

---

## Phase 3 — Identifier les garde-fous manquants

Pour chaque action sensible, vérifier :

- [ ] Confirmation affichée avant action
- [ ] Paramètres validés côté serveur
- [ ] Événement journalisé avec timestamp + user + action + result
- [ ] Résultat remonte au cockpit fondateur
- [ ] Utilisateur voit distinction "préparé" vs "envoyé réellement"
- [ ] Fallback si service externe indisponible
- [ ] Limite API respectée (rate limit, quota)

### Actions à protéger en priorité

1. **SMS / Email / Appel** — À ne jamais tester sans validation Ludovic
   - Risque : doublon d'envois, destinataire mauvais
   - Correction : confirmation modale + journal audit

2. **Alerte urgence** — À ne jamais tester sur le terrain
   - Risque : alerter 50 contacts d'urgence par erreur
   - Correction : confirmation 2x + contexte requis

3. **Réservation** — À ne jamais tester sans données réelles
   - Risque : doublon de réservation, charge Duffel
   - Correction : sandbox Duffel, pas de réservation réelle

4. **Paiement** — À ne jamais tester sans environnement sandbox
   - Risque : débiter la carte de test
   - Correction : Stripe dev mode uniquement

---

## Phase 4 — Plan de correction par priorité

Après audits, proposer trois lots :

### Lot 1 — Actions non destructives (priorité immédiate)

Services testables en live sans risque :
- Météo
- Actualités
- Recherche web
- Autour de moi
- Stats / Missions / Badges / Amis

**Plan** : Vérifier que chaque bouton fonctionne, affiche les résultats, gère les erreurs.

### Lot 2 — Actions sensibles (priorité haute)

Services à sécuriser avant Go Live :
- SMS / Email / Appel → Confirmation modale + journal
- Visio Luna → Token JWT validé
- Alerte urgence → Confirmation 2x

**Plan** : Ajouter confirmation, améliorer messages d'erreur, journaliser.

### Lot 3 — Actions externes (priorité moyenne)

Services dépendants d'API externes :
- Vols / Hôtels → Duffel (peut être down)
- Restaurants → Serper (peut être down)

**Plan** : Gérer timeouts, cache résultats, message "service indisponible" clair.

---

## Phase 5 — Arbitrage et décisions

### Questions pour Ludovic

Avant de coder quoi que ce soit, obtenir validation sur :

1. **Lot 1** : OK pour tester en production (méteo, stats, etc.) ?
2. **Lot 2 prioritaire** : SMS / Email / Appel — confirmation modale suffisante ?
3. **Alerte urgence** : Confirmation 2x acceptée ou autre garde-fou requis ?
4. **Test phone** : Quand tester Ludovic les corrections ?
5. **Dépendances externes** : Ignorer Duffel / Serper si indisponibles en dev ?

---

## Livrables Claude (attendus après autres avis)

1. **Cartographie complète**
   - Tableau Service → Handler → Endpoint → Tool → Risque
   - Flux complet requête → réponse → affichage

2. **Synthèse risques**
   - Actions basses (pas de correction)
   - Actions moyennes (validation d'erreur)
   - Actions critiques (confirmation + journal)

3. **Plan correction phases**
   - Lot 1 : quoi tester d'abord
   - Lot 2 : quoi sécuriser ensuite
   - Lot 3 : quoi optimiser plus tard

4. **Questions pour Ludovic**
   - Arbitrage confirmation vs UX
   - Test phone planning
   - Dépendances à ignorer en dev

---

## Interdictions absolues

❌ Ne pas coder directement.
❌ Ne pas tester SMS/email/appel réels.
❌ Ne pas déployer sans validation Ludovic.
❌ Ne pas refonder l'onglet avant cartographie.
❌ Ne pas mélanger 5 corrections dans une seule PR.

---

## Statut

🔄 En attente des avis DeepSeek, Kimi, Cursor.

**Status** : ⏳ Audit technique et UX en cours
