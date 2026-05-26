# Avis Kimi — Objectif 011 Audit complet onglet Services / Conciergerie

**Agent** : Kimi Code CLI (kimi-k2.6)  
**Mission** : UX, promesse utilisateur, textes humains, actions sensibles  
**Date** : 2026-05-26  
**Branche** : `kimi/objectif-011-audit-services`  

---

## 1. Résumé Kimi

L'onglet **Services** contient **22 cartes** réparties en 5 sections.  
**Problème central** : l'utilisateur ne sait pas toujours si Luna a *vraiment* agi ou seulement *préparé* une action.

| Section | Cartes | Dont sensibles |
|---|---|---|
| Recherche & Voyage | 5 | 2 (réservation vol, hôtel) |
| Infos en temps réel | 2 | 0 |
| Communication | 5 | 5 (SMS, email, appel, visio, alerte) |
| Organisation | 5 | 0 |
| Mon Monde Luna | 4 | 0 |

**Verdict UX** : 7 actions sur 22 sont sensibles. Seules 3 ont une confirmation dialog.  
**Priorité immédiate** : ajouter une confirmation aux 4 actions sensibles sans garde-fou dialog.

---

## 2. Promesse utilisateur vs réalité — Cartographie par carte

### 2.1 Recherche & Voyage

| Carte | Promesse utilisateur | Réalité technique | Risque | État UX |
|---|---|---|---|---|
| **Vols** | "Luna trouve un vol avec prix" | `search_flights` → Duffel/Amadeus → fallback web | Aucun | ✅ OK — lecture seule |
| **Hôtels** | "Luna trouve un hébergement" | `search_hotels` → Duffel/Amadeus → fallback web | Aucun | ✅ OK — lecture seule |
| **Restaurants** | "Luna trouve où manger" | `book_restaurant` → TheFork → fallback `search_places` | Aucun | ⚠️ **Trompeur** — le nom "Restaurants" suggère une réservation, mais c'est une recherche. Le texte de fallback dit *"je peux appeler le restaurant"* sans expliquer que l'appel déclenchera un vrai coup de fil. |
| **Recherche web** | "Luna cherche sur internet" | `search_web` → Serper API | Aucun | ✅ OK — lecture seule |
| **Autour de moi** | "Luna trouve des commerces proches" | `search_places` → Serper Places | Aucun | ✅ OK — lecture seule |

### 2.2 Infos en temps réel

| Carte | Promesse utilisateur | Réalité technique | Risque | État UX |
|---|---|---|---|---|
| **Météo** | "Luna me donne la météo" | `get_weather` → wttr.in / Open-Meteo | Aucun | ✅ OK — lecture seule, fiable |
| **Actualités** | "Luna me résume l'actualité" | `get_news` → RSS France Info / Le Monde | Aucun | ✅ OK — lecture seule |

### 2.3 Communication — **SECTION SENSIBLE**

| Carte | Promesse utilisateur | Réalité technique | Risque | État UX |
|---|---|---|---|---|
| **Envoyer un SMS** | "Luna envoie un SMS à mon contact" | `send_sms` → Twilio — **SMS réel** | 🔴 **Haut** | ❌ **Dangereux** — pas de confirmation dialog. L'utilisateur sélectionne un contact, tape un message, clique "Envoyer" → SMS part immédiatement. |
| **Envoyer un email** | "Luna envoie un email à mon contact" | `send_email` → Gmail OAuth / SendGrid — **email réel** | 🔴 **Haut** | ❌ **Dangereux** — pas de confirmation dialog. Même flux que SMS. |
| **Appeler** | "Luna passe un appel vocal à mon contact" | `call_contact` → Twilio voice — **appel téléphonique réel** | 🔴 **Haut** | ❌ **Dangereux** — pas de confirmation dialog. Sélection contact → choix durée → appel immédiat. Le texte affiché est *"Luna appelle {name} ({minutes} min)…"* mais l'appel est déjà lancé. |
| **Visio Luna** | "Luna fait un appel vidéo" | `invite_visio` → Tavus + Twilio SMS — **SMS réel + visio** | 🔴 **Haut** | ❌ **Dangereux** — pas de confirmation dialog. La carte `onclick="startCall()"` ouvre un sélecteur de durée puis navigue vers `/simli`. Aucune confirmation avant l'envoi du SMS. |
| **Alerte urgence** | "Luna prévient mes proches en urgence" | `alert_contacts` → Twilio SMS à **tous** les contacts — **SMS réel** | 🔴 **Haut** | ✅ **Protégé** — **confirmation dialog présente** : *"Tous tes contacts de confiance vont recevoir un SMS d'alerte. Confirmer ?"* |

### 2.4 Organisation

| Carte | Promesse utilisateur | Réalité technique | Risque | État UX |
|---|---|---|---|---|
| **Rappel** | "Luna crée un rappel" | `add_reminder` → Redis-backed secretary | Aucun | ✅ OK — action interne, pas d'effet externe |
| **Prendre une note** | "Luna retient une information" | `create_note` → memory manager | Aucun | ✅ OK — action interne |
| **Document** | "Luna génère un courrier" | `generate_document` → GPT + PDF | Aucun | ✅ OK — génération locale, pas d'envoi automatique |
| **Mes contacts** | "Luna liste mes proches" | `get_contacts` → memory manager | Aucun | ✅ OK — lecture seule |
| **Formulaires** | "Luna me redirige vers les formulaires" | Hard link vers `/formulaires` | Aucun | ✅ OK — simple redirection |

### 2.5 Mon Monde Luna

| Carte | Promesse utilisateur | Réalité technique | Risque | État UX |
|---|---|---|---|---|
| **Mes stats** | "Luna montre mon niveau et mes XP" | `get_player_stats` → Redis gamification | Aucun | ✅ OK — lecture seule |
| **Missions** | "Luna montre mes objectifs en cours" | `get_active_missions` → Redis gamification | Aucun | ✅ OK — lecture seule |
| **Badges** | "Luna montre mes récompenses" | `get_badges` → Redis gamification | Aucun | ✅ OK — lecture seule |
| **Amis en ligne** | "Luna montre qui est connecté" | `get_friends_online` → Redis presence | Aucun | ✅ OK — lecture seule |

---

## 3. Les trois états d'action — Ce que Luna dit vs ce qu'elle fait

### Principe

L'utilisateur doit toujours comprendre si Luna :
- **a trouvé** (lecture, recherche)
- **a préparé** (généré un document, pré-rempli un formulaire)
- **a vraiment envoyé/appelé** (action irréversible)

### Tableau de vérité

| Carte | État correct | Texte actuel | Problème |
|---|---|---|---|
| Recherche web | **Trouvé** | Résultats affichés inline | ✅ Clair |
| Météo | **Trouvé** | Température affichée | ✅ Clair |
| Rappel | **Préparé** | "Rappel créé pour 20h" | ✅ Clair (action interne) |
| Note | **Préparé** | "Note enregistrée" | ✅ Clair (action interne) |
| Document | **Préparé** | Document généré, téléchargeable | ✅ Clair (pas d'envoi auto) |
| SMS | **Envoyé** | "SMS envoyé à {name}" | ⚠️ OK, mais **pas de confirmation avant** |
| Email | **Envoyé** | "Email envoyé à {name}" | ⚠️ OK, mais **pas de confirmation avant** |
| Appeler | **Appelé** | "Luna appelle {name}…" | ❌ **L'appel est déjà lancé quand le texte s'affiche** |
| Visio | **Envoyé + Appelé** | Aucun texte explicite | ❌ **Le SMS est envoyé silencieusement** |
| Alerte urgence | **Envoyé** | "Alerte envoyée à {sent} contact(s)" | ✅ Clair **grâce à la confirmation dialog** |
| Vols (réservation) | **Réservé** | "Réservation confirmée !" | ✅ Clair **grâce à la confirmation dialog** |
| Hôtels (réservation) | **Réservé** | "Hôtel réservé !" | ✅ Clair **grâce à la confirmation dialog** |

---

## 4. Actions sensibles — Audit des garde-fous

### 4.1 Ce qui est protégé ✅

| Garde-fou | Actions concernées | État |
|---|---|---|
| Confirmation dialog | Alerte urgence, Réservation vol, Réservation hôtel | ✅ Présent |
| Blocage license dégradée | SMS, email, appel, visio | ✅ Présent côté serveur |
| Quota SMS | SMS, alerte | ✅ Présent |
| Blocage numéros d'urgence | Appel vocal | ✅ Présent (15, 17, 18, 112, etc.) |
| Match fuzzy contacts de confiance | SMS, email, appel, visio | ✅ Présent |
| Préfixe SMS identifiant | Tous les SMS | ✅ "[Luna pour {sub_name}]" |
| Journal mémoire | SMS, email, appel, visio, alerte | ✅ Loggué |
| Protection Tavus guest | Paiement, vols, hôtels, resto, email, alerte | ✅ Bloqué si invités présents |
| Budget mensuel | Paiement | ✅ Vérifié |

### 4.2 Ce qui manque ❌

| Manque | Actions concernées | Sévérité |
|---|---|---|
| **Pas de confirmation dialog avant envoi** | SMS, email, appel, visio | 🔴 **Critique** |
| **Pas de récapitulatif de l'action** | SMS, email, appel, visio | 🔴 **Critique** — l'utilisateur ne revoit pas ce qu'il s'apprête à envoyer/dire |
| **Pas de double confirmation pour l'appel** | Appel vocal | 🔴 **Critique** — un appel téléphonique réel est hautement intrusif |
| **Pas d'indicateur "action réelle" sur les cartes** | Toutes les cartes Communication | 🟡 **Moyen** — l'utilisateur ne distingue pas visuellement une recherche d'un envoi réel |
| **Pas de confirmation SMS après envoi** | SMS, email | 🟡 **Moyen** — aucun accusé de réception visible longtemps |
| **Pas d'annulation possible** | Toutes les actions sensibles | 🟡 **Moyen** — une fois lancée, aucun bouton "Annuler" |

---

## 5. Textes de réussite / échec — Audit des formulations

### 5.1 Textes actuels analysés

| Scénario | Texte actuel | Problème | Texte proposé |
|---|---|---|---|
| SMS envoyé | `"SMS envoyé à {name}"` | ✅ Correct | — |
| SMS échoué — service indisponible | `"Service SMS non disponible"` | ✅ Correct | — |
| SMS échoué — quota atteint | `"Quota SMS atteint pour ce mois"` | ✅ Correct | — |
| SMS échoué — contact introuvable | `"Contact '{name}' introuvable. Contacts disponibles : ..."` | ⚠️ Trop technique | `"Je ne trouve pas '{name}' dans tes contacts. Voici ceux que je connais : ..."` |
| Email échoué — non configuré | `"Aucun service email configuré. Connectez Gmail ou configurez SendGrid."` | ❌ **Instructif technique** | `"Luna ne peut pas envoyer d'email pour l'instant. Demande à l'exploitant de configurer l'envoi d'emails."` |
| Appel échoué — non configuré | `"Service d'appels vocaux non configuré"` | ✅ Correct | — |
| Appel — numéro d'urgence | `"Luna ne peut pas appeler les numéros d'urgence. Suggère au souscripteur de composer le {number} lui-même."` | ❌ **Trop technique** — "souscripteur" n'est pas le vocabulaire utilisateur | `"Luna ne peut pas appeler les numéros d'urgence. Tu peux composer le {number} toi-même."` |
| Alerte urgence — aucun contact | `"Aucun contact de confiance enregistré"` | ✅ Correct | — |
| Réservation vol — profil incomplet | `"Nom et prénom requis. Complète ton profil d'abord."` | ✅ Correct | — |
| Réservation hôtel — profil incomplet | `"Nom et prénom requis. Complète ton profil."` | ✅ Correct | — |
| Recherche sans résultat | `"Aucun résultat trouvé."` | ✅ Correct | — |

### 5.2 Textes manquants

| Scénario | Texte proposé |
|---|---|
| **Avant envoi SMS** (confirmation dialog) | `"Tu vas envoyer un SMS à {name} :\n\n\"{message}\"\n\nConfirmer ?"` |
| **Avant envoi email** (confirmation dialog) | `"Tu vas envoyer un email à {name} :\n\nObjet : {subject}\n\nConfirmer ?"` |
| **Avant appel** (confirmation dialog) | `"Luna va appeler {name} au {numero} pendant {minutes} minutes.\n\nConfirmer ?"` |
| **Avant visio** (confirmation dialog) | `"Luna va créer un appel vidéo et envoyer le lien par SMS à {name}.\n\nConfirmer ?"` |
| **Appel en cours** | `"Luna appelle {name}… Appui sur le haut-parleur pour écouter."` |
| **Visio en cours** | `"Appel vidéo avec {name} en préparation…"` |
| **Action annulée par l'utilisateur** | `"Action annulée. Rien n'a été envoyé."` |

---

## 6. Distinction visuelle des cartes — Proposition UX

### Problème
Les 22 cartes ont le même aspect visuel. L'utilisateur ne distingue pas :
- une recherche (sans risque) d'un envoi réel (irréversible)
- une action interne (rappel) d'une action externe (SMS)

### Proposition minimale

Ajouter un indicateur discret mais visible sur les cartes sensibles :

```
┌─────────────┐
│  💬         │
│  SMS        │
│  → externe  │  ← petit badge orange "→ externe"
└─────────────┘
```

| Type de carte | Badge | Couleur |
|---|---|---|
| Recherche / Info | 🔍 | Gris (aucun badge) |
| Action interne (rappel, note) | 📝 | Vert discret |
| Action externe sensible (SMS, email, appel) | → externe | Orange |
| Action externe critique (alerte, visio) | ⚠️ externe | Rouge |

**Alternative plus simple** : un petit point de couleur en bas à droite de la carte :
- 🟢 = action interne, sans risque
- 🔵 = recherche, lecture seule
- 🟠 = action externe, confirmation recommandée
- 🔴 = action externe critique, confirmation obligatoire

---

## 7. Priorités UX pour Ludovic

### Phase 1 — Tester sans risque (actions lecture seule)

| Ordre | Carte | Pourquoi tester d'abord |
|---|---|---|
| 1 | **Météo** | Fiable, API gratuite, résultat immédiat |
| 2 | **Actualités** | Fiable, RSS, résultat immédiat |
| 3 | **Recherche web** | Dépend de Serper, mais sans risque |
| 4 | **Autour de moi** | Dépend de Serper, sans risque |
| 5 | **Mes stats / Missions / Badges / Amis** | 100% interne Redis, doit toujours marcher |
| 6 | **Rappel / Note / Document** | Actions internes, testent le stockage |
| 7 | **Mes contacts** | Lecture seule, teste la mémoire |
| 8 | **Formulaires** | Simple redirection |

### Phase 2 — Tester avec précaution (actions sensibles avec confirmation)

| Ordre | Carte | Garde-fou existant |
|---|---|---|
| 9 | **Alerte urgence** | ✅ Confirmation dialog présente. Tester avec un faux contact. |
| 10 | **Réservation vol** | ✅ Confirmation dialog présente. Nécessite Duffel configuré + profil complet. |
| 11 | **Réservation hôtel** | ✅ Confirmation dialog présente. Même conditions. |

### Phase 3 — Ne PAS tester seul (actions sensibles SANS confirmation)

| Ordre | Carte | Risque | Action requise avant test |
|---|---|---|---|
| 12 | **SMS** | 🔴 SMS réel à un vrai numéro | **Ajouter confirmation dialog d'abord** |
| 13 | **Email** | 🔴 Email réel à une vraie adresse | **Ajouter confirmation dialog d'abord** |
| 14 | **Appeler** | 🔴 Appel téléphonique réel | **Ajouter confirmation dialog d'abord** |
| 15 | **Visio Luna** | 🔴 SMS réel + visio | **Ajouter confirmation dialog d'abord** |

---

## 8. Synthèse des problèmes UX critiques

### 🔴 Problème 1 — 4 actions sensibles sans confirmation

**SMS, email, appel, visio** partent immédiatement sans que l'utilisateur ne confirme.

**Correction minimale** : ajouter `_showConfirm()` avant l'appel API pour ces 4 actions.

### 🔴 Problème 2 — Pas de récapitulatif avant envoi

L'utilisateur ne revoit pas le message/email qu'il s'apprête à envoyer.

**Correction minimale** : inclure le contenu du message dans le dialog de confirmation.

### 🟡 Problème 3 — Texte "souscripteur" dans le message d'erreur appel

`"Suggère au souscripteur de composer le {number} lui-même"` — terme technique inapproprié.

**Correction minimale** : remplacer par `"Tu peux composer le {number} toi-même."`

### 🟡 Problème 4 — Texte technique email non configuré

`"Connectez Gmail ou configurez SendGrid"` — instruction destinée à l'admin, pas à l'utilisateur.

**Correction minimale** : remplacer par `"Luna ne peut pas envoyer d'email pour l'instant."`

### 🟡 Problème 5 — Carte "Restaurants" trompeuse

Le nom suggère une réservation, mais c'est une recherche. Le fallback dit *"je peux appeler le restaurant"* sans avertissement.

**Correction minimale** : renommer "Restaurants" en "Chercher un restaurant", et ajouter un avertissement si l'appel est proposé.

### 🟢 Bon point — Alerte urgence bien protégée

Confirmation dialog, message clair, numéros d'urgence inclus dans le SMS. ✅

### 🟢 Bon point — Réservations vol/hôtel bien protégées

Confirmation dialog, affichage du prix, mention du profil utilisé. ✅

---

## 9. Recommandations Kimi

### À implémenter avant tout test sensible

1. **Ajouter `_showConfirm()` aux 4 actions sans garde-fou** : SMS, email, appel, visio.
2. **Inclure le récapitulatif dans le dialog** : message, destinataire, action.
3. **Corriger les 2 textes techniques** : "souscripteur" et "Connectez Gmail".
4. **Renommer "Restaurants" en "Chercher un restaurant"** pour éviter la confusion.
5. **Ajouter un indicateur visuel** sur les cartes sensibles (badge orange/rouge).

### À ne PAS faire sans validation Ludovic

- Tester SMS, email, appel ou visio sur un numéro/destinataire réel.
- Modifier les garde-fous serveur (quota, license, blocage numéros d'urgence).
- Supprimer ou désactiver une carte sans audit préalable.

---

## 10. Message à l'équipe

> Objectif 011 = rendre l'onglet Services digne de confiance.  
> 7 actions sur 22 sont sensibles. 3 sont bien protégées. 4 ne le sont pas.  
> Priorité : ajouter une confirmation aux 4 actions sans garde-fou avant tout test réel.

---

*Document produit par Kimi Code CLI pour l'objectif 011 — branche `kimi/objectif-011-audit-services`*
