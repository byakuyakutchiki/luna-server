# Avis UX — YAWatch-LUNA

**Auteur :** Kimi Code CLI  
**Date :** 2026-06-14  
**Dépôt audité :** https://github.com/byakuyakutchiki/luna-server

---

## Verdict global

Luna ressemble à une **démo très avancée**, pas à un produit prêt pour des utilisateurs réels. L'interface est soignée, la promesse est forte, mais l'expérience utilisateur est compromises par des blocages dès le premier contact, des promesses non tenues et une confusion constante entre ce qui est affiché et ce qui fonctionne.

**Note UX : 3,5 / 10**

---

## Ce qui me rassure

- **Guardian** : le flow de démarrage GPS/SOS est clair, le consentement est explicite, le besoin d'un contact d'urgence rassure. C'est le pilier le plus abouti en termes d'UX.
- **L'interface visuelle** : dark mode cohérent, ton chaleureux, animations soignées. On sent une intention produit forte.
- **Profil souscripteur** : la richesse des champs donne l'impression que Luna peut vraiment apprendre à connaître l'utilisateur.
- **Vault et Form filler** : promesses concrètes, routes fonctionnelles, expérience documentaire crédible.

---

## Ce qui me fait douter

### 1. On ne peut rien tester au démarrage

Le serveur est verrouillé par un **PV de recette** que l'utilisateur ne peut pas signer, car le module `pv_recette` n'est pas livré. Résultat : au premier lancement, presque tous les endpoints retournent "Installation en cours". C'est un mur dès la première seconde.

### 2. Luna ne répond pas

Le chat central — le cœur du produit — est **mort sans une clé OpenAI valide**. Au lieu d'un message honnête ("Clé OpenAI invalide"), l'utilisateur reçoit "Luna a un souci technique". Cela détruit la confiance instantanément.

### 3. Promesses contradictoires

- La vision produit dit que la **visio n'est plus un pilier**, mais le front propose toujours "Iris Audio" qui redirige vers `/simli` (visio avatar).
- Le README promet **appels et visioconférences**, mais le backend refuse ces actions.
- Les prix et quotas changent selon le document consulté : entre 79 € et 399 €, entre 20 et 50 SMS, entre 12 et 60 minutes de visio.

### 4. Beaucoup de boutons, peu d'actions

- Des pages entières (`dashboard.html`, `prospects.html`, `workspace.html`, `team_workspace.html`) sont des **maquettes hardcodées** sans donnée réelle.
- Des boutons affichent "disponible en Phase P0.x" au lieu de faire quelque chose.
- Des actions sont proposées sans contexte : "Créer un rappel médicaments à 20h" sans prescription, "Appelle ma famille" sans contact, "Envoie un SMS à" sans destinataire.

### 5. Confusion navigationnelle

Trop de concepts s'empilent sans hiérarchie claire : Luna, Days Legacy, YAWatch Industries, Monde, Salon, Iris, Simli, Guardian, Vault, Formulaires, Documents. L'utilisateur ne sait pas où il est, ni pourquoi tel ou tel écran existe.

---

## Les 3 problèmes UX les plus bloquants

1. **Verrouillage initial absolu** — impossible de découvrir la valeur sans signer un PV inaccessible.
2. **Chat mort sans OpenAI** — le cœur du produit est silencieux.
3. **Boutons factices et actions sans contexte** — l'interface promet plus qu'elle ne tient.

---

## Recommandation finale

Avant de penser à de nouvelles fonctionnalités, Luna a besoin d'une **phase de cohérence** :

1. Permettre un mode découverte fonctionnel sans PV de recette.
2. Rendre le chat robuste avec une gestion claire des erreurs OpenAI.
3. Retirer du front tout ce qui n'est pas réellement implémenté (visio, appels, pages de démo).
4. Harmoniser prix, quotas et message produit.
5. Ne proposer des actions contextuelles que quand le contexte existe.

En l'état, un nouvel utilisateur quitterait probablement l'application en moins de 5 minutes. La surface est belle, mais le fond est trop fragile pour inspirer confiance.

---

*Avis produit / UX. Aucun code modifié.*
