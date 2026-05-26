# Kimi — Avis Objectif 011 — Audit UX et promesse utilisateur

**Date** : 2026-05-26  
**Objectif** : Audit complet onglet Services / Conciergerie  
**Rôle** : Audit UX, promesse utilisateur, textes humains et clarté  
**Règle absolue** : L'utilisateur doit comprendre ce qui arrive à chaque action  

---

## Mission Kimi

Auditer la promesse utilisateur de chaque service :

1. Quel service promet-il à l'utilisateur ?
2. Que se passe-t-il réellement quand on clique ?
3. L'utilisateur sait-il si Luna a vraiment agi ou seulement préparé ?
4. Les textes d'erreur sont-ils compréhensibles ?
5. Les actions sensibles sont-elles suffisamment signalées ?

**Interdit** : Coder, tester actions réelles, déployer.

---

## Phase 1 — Audit de la promesse par service

### Pour chaque service, répondre

#### 1. Méteo
- **Promesse** : "Afficher la météo locale"
- **Réalité** : Récupère météo + l'affiche
- **Danger** : Aucun
- **Texte succès** : "☀️ Météo à [ville] : 22°C, ensoleillé"
- **Texte erreur** : "Impossible de récupérer la météo. Vérifiez votre connexion."
- **Amélioration UX** : Permettre changement de ville ? Historique ?

#### 2. Actualités
- **Promesse** : "Afficher l'actualité récente"
- **Réalité** : API news, affiche titres + résumés
- **Danger** : Aucun
- **Texte succès** : "📰 Voici 5 actualités récentes"
- **Texte erreur** : "Pas d'actualités disponibles en ce moment."
- **Amélioration UX** : Filtrer par sujet ? Liens cliquables ?

#### 3. Recherche web
- **Promesse** : "Chercher sur le web"
- **Réalité** : Serper API, 5-10 résultats
- **Danger** : Bas (lecture seule)
- **Texte succès** : "🔍 [N] résultats trouvés"
- **Texte erreur** : "Pas de résultats pour '[requête]'"
- **Amélioration UX** : Afficher URLs ? Permettre clic sur lien ?

#### 4. Vols
- **Promesse** : "Trouver un vol"
- **Réalité** : Interface Duffel, recherche multi-dates
- **Danger** : Moyen (requête externe, lente)
- **Texte succès** : "✈️ [N] vols trouvés. Cliquer pour détails."
- **Texte erreur** : "Aucun vol trouvé ou Duffel indisponible."
- **Amélioration UX** : Dates flexibles ? Meilleur prix mis en avant ?

#### 5. Hôtels
- **Promesse** : "Trouver un hôtel"
- **Réalité** : Interface Duffel, recherche multi-dates
- **Danger** : Moyen
- **Texte succès** : "🏨 [N] hôtels trouvés."
- **Texte erreur** : "Aucun hôtel disponible ou service indisponible."

#### 6. Restaurants
- **Promesse** : "Trouver un restaurant"
- **Réalité** : Serper API, affiche restaurants + avis
- **Danger** : Bas
- **Texte succès** : "🍽️ [N] restaurants trouvés"
- **Texte erreur** : "Aucun restaurant trouvé près de vous."

#### 7. Autour de moi
- **Promesse** : "Afficher commerces, lieux publics proches"
- **Réalité** : Serper API, géolocalisation
- **Danger** : Bas
- **Texte succès** : "📍 [N] lieux trouvés près de vous"
- **Texte erreur** : "Impossible de localiser ou aucun lieu trouvé."

#### 8. SMS
- **Promesse** : "Envoyer un SMS"
- **Réalité** : SMS RÉEL envoyé via Twilio
- **Danger** : CRITIQUE — Action réelle
- **Texte succès** : "✅ SMS envoyé à [contact]"
- **Texte erreur** : "❌ Impossible d'envoyer. Vérifiez le numéro et essayez."
- **Garde-fou** : **MODALE DE CONFIRMATION OBLIGATOIRE**
  ```
  "Envoyer SMS à : +33 6 12 34 56 78 ?"
  Message: "[texte prévisualité]"
  [Annuler] [Envoyer]
  ```
- **Journal audit** : Chaque SMS doit être enregistré (date, contact, texte, statut)

#### 9. Email
- **Promesse** : "Envoyer un email"
- **Réalité** : Email RÉEL envoyé via Sendgrid/SMTP
- **Danger** : CRITIQUE — Action réelle
- **Texte succès** : "✅ Email envoyé à [adresse]"
- **Texte erreur** : "❌ Impossible d'envoyer. Vérifiez l'adresse email."
- **Garde-fou** : **MODALE DE CONFIRMATION OBLIGATOIRE**
  ```
  "Envoyer email à : [adresse] ?"
  Objet: "[texte]"
  [Aperçu] [Annuler] [Envoyer]
  ```
- **Journal audit** : Chaque email doit être enregistré

#### 10. Appel
- **Promesse** : "Appeler un contact"
- **Réalité** : Appel RÉEL via Twilio
- **Danger** : CRITIQUE — Action réelle
- **Texte succès** : "📞 Appel lancé à [contact]..."
- **Texte erreur** : "❌ Impossible d'appeler. Vérifiez que l'appareil a le réseau."
- **Garde-fou** : **CONFIRMATION VOCALE OBLIGATOIRE**
  ```
  "Luna va appeler [contact]. Êtes-vous sûr(e) ?"
  [Annuler] [Appeler]
  ```
- **Journal audit** : Chaque appel doit être enregistré (durée, statut)

#### 11. Visio Luna
- **Promesse** : "Inviter quelqu'un en visio avec Luna"
- **Réalité** : Invitation envoyée + lien générée
- **Danger** : CRITIQUE — Invite un tiers
- **Texte succès** : "✅ Invitation visio envoyée à [contact]"
- **Texte erreur** : "❌ Impossible d'envoyer l'invitation. L'utilisateur doit avoir Luna."
- **Garde-fou** : **CONFIRMATION AVANT ENVOI**
  ```
  "Inviter [contact] en visio ?"
  Luna partagera l'accès à la conversation.
  [Annuler] [Envoyer]
  ```

#### 12. Alerte urgence
- **Promesse** : "Alerter mes contacts d'urgence"
- **Réalité** : SMS/Email/Notification à 50+ contacts
- **Danger** : CRITIQUE EXTRÊME — Alerte massive
- **Texte avant** : "⚠️ ATTENTION : Luna va contacter [N] contacts d'urgence."
- **Texte succès** : "✅ Alerte envoyée à [N] contacts"
- **Texte erreur** : "❌ Alerte partiellement envoyée. [N] contacts n'ont pas pu être atteints."
- **Garde-fou** : **CONFIRMATION 2x OBLIGATOIRE**
  ```
  Confirmation 1 : "Déclarer une urgence ?"
  [Annuler] [Continuer]
  
  Confirmation 2 (avec compte à rebours) :
  "DERNIÈRE CHANCE : Alerter [N] contacts d'urgence.
   Cette action ne peut pas être annulée une fois lancée.
   Luna alerte tous les contacts maintenant ?
   Annuler dans : 5... 4... 3..."
  [Annuler] [OUI, ALERTER]
  ```
- **Journal audit** : OBLIGATOIRE — Trace complète pour Ludovic

#### 13. Rappel
- **Promesse** : "Créer un rappel"
- **Réalité** : Créé localement ou en DB, affiche date/heure
- **Danger** : Aucun
- **Texte succès** : "✅ Rappel créé pour [date] à [heure]"
- **Texte erreur** : "❌ Impossible de créer le rappel. Essayez à nouveau."

#### 14. Note
- **Promesse** : "Créer une note"
- **Réalité** : Créé localement ou en DB
- **Danger** : Aucun
- **Texte succès** : "✅ Note créée"
- **Texte erreur** : "❌ Impossible de créer la note. Essayez à nouveau."

#### 15. Document
- **Promesse** : "Générer un document"
- **Réalité** : LLM générer + fichier PDF/Word créé
- **Danger** : Bas (long, peut échouer)
- **Texte succès** : "✅ Document généré. Télécharger ?"
- **Texte erreur** : "❌ Génération échouée. Essayez à nouveau."

#### 16. Contacts
- **Promesse** : "Afficher mes contacts"
- **Réalité** : Liste depuis la DB
- **Danger** : Aucun
- **Texte succès** : "📇 [N] contacts trouvés"
- **Texte erreur** : "Aucun contact pour l'instant."

#### 17. Formulaires
- **Promesse** : "Accéder aux formulaires"
- **Réalité** : Redirection vers l'onglet Formulaires
- **Danger** : Aucun
- **Texte succès** : (Non applicable, redirection)

#### 18. Stats
- **Promesse** : "Voir mes statistiques Luna"
- **Réalité** : Affiche usage, temps, interactions
- **Danger** : Aucun
- **Texte succès** : "📊 Voici vos stats Luna"
- **Texte erreur** : "Aucune statistique disponible encore."

#### 19. Missions
- **Promesse** : "Voir mes missions en cours"
- **Réalité** : Affiche missions actives + progress
- **Danger** : Aucun
- **Texte succès** : "🎯 [N] missions en cours"
- **Texte erreur** : "Aucune mission en cours."

#### 20. Badges
- **Promesse** : "Voir mes badges gagnés"
- **Réalité** : Affiche badges + critères
- **Danger** : Aucun
- **Texte succès** : "🏆 [N] badges gagnés"
- **Texte erreur** : "Aucun badge pour l'instant. Continuez !"

#### 21. Amis en ligne
- **Promesse** : "Voir mes amis en ligne"
- **Réalité** : Affiche liste amis + statut
- **Danger** : Aucun
- **Texte succès** : "👥 [N] amis en ligne"
- **Texte erreur** : "Aucun ami en ligne maintenant."

---

## Phase 2 — Audit des textes existants

Pour chaque service, vérifier si l'APK affiche actuellement :

| Service | Texte actuel | Clair ? | À améliorer |
|---|---|---|---|
| SMS | ? | ✓/❌ | ? |
| Email | ? | ✓/❌ | ? |
| Appel | ? | ✓/❌ | ? |
| Alerte | ? | ✓/❌ | ? |
| Vols | ? | ✓/❌ | ? |
| ... | | | |

---

## Phase 3 — Classification par niveau de protection

### 🟢 Vert — Aucun risque, afficher directement
- Météo, Actualités, Recherche web, Autour de moi
- Stats, Missions, Badges, Amis en ligne
- Rappel, Note, Contacts, Formulaires

### 🟡 Jaune — Risque moyen, vérifier message d'erreur
- Vols, Hôtels, Restaurants, Documents
- Dégradation acceptable si service externe down

### 🔴 Rouge — Actions réelles, confirmation OBLIGATOIRE
- SMS → Modale "Envoyer SMS à [contact] ?"
- Email → Modale "Envoyer email à [adresse] ?"
- Appel → Modale "Appeler [contact] ?"
- Visio → Modale "Inviter [contact] ?"

### 🔴🔴 Rouge extrême — Actions massives, confirmation 2x
- **Alerte urgence** → Confirmation 2x avec compte à rebours
  - Risque : alerter 50+ contacts de l'utilisateur par erreur

---

## Phase 4 — Ordre priorité pour Ludovic

1. **Immédiat** — Sécuriser actions critiques (SMS, Email, Appel, Urgence)
   - Ajouter confirmations
   - Améliorer textes d'erreur

2. **Court terme** — Améliorer messages d'erreur services externes
   - Vols/Hôtels/Restaurants
   - Afficher "Service indisponible" au lieu de rien

3. **Moyen terme** — Enrichir UX lecture seule
   - Améliorer textes stats/missions
   - Meilleure navigation

---

## Livrables Kimi

1. **Audit promesse utilisateur**
   - Pour chaque service : promesse vs réalité vs danger
   - Textes succès/erreur proposés
   - Améliorations UX identifiées

2. **Classification par risque**
   - 🟢 Vert (0 risque)
   - 🟡 Jaune (risque moyen)
   - 🔴 Rouge (risque critique)
   - 🔴🔴 Rouge extrême

3. **Textes d'interface améliorés**
   - Confirmations pour actions réelles
   - Messages erreur lisibles
   - Distinctions "Luna a trouvé" vs "Luna envoie réellement"

4. **Propositions garde-fou**
   - Modales confirmation pour SMS/Email/Appel
   - Confirmation 2x pour Alerte urgence
   - Journal audit obligatoire pour actions sensibles

---

## Interdictions

❌ Ne pas envoyer SMS/email/appel réels.  
❌ Ne pas tester Alerte urgence.  
❌ Ne pas coder directement.  
✅ Juste proposer textes et confirmations.  

---

## Statut

⏳ En attente du contexte code DeepSeek.

**Prochaines étapes** :
- Claude synthétise audit technique + UX
- Cursor améliore UI mobile
- Ludovic valide avant code

**Status** : 📝 Audit promesse utilisateur en cours
