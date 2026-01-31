# Luna - Profil Souscripteur (ce que Luna sait de son proprio)

> Schema de donnees du profil souscripteur stocke dans Redis
> Luna doit connaitre son souscripteur pour agir en son nom
> Derniere mise a jour : 31 janvier 2026

---

## IDENTITE DE BASE
- Prenom, nom complet
- Date de naissance (age)
- Adresse postale (commune, departement)
- Numero de telephone principal
- Email
- Langue preferee, tutoiement/vouvoiement

## SITUATION PERSONNELLE
- Situation familiale (celibataire, marie, veuf, divorce)
- Enfants (prenoms, ages, relations)
- Vit seul ou accompagne
- Animaux de compagnie
- Niveau d'autonomie (aucune difficulte, aide ponctuelle, aide quotidienne)
- Mobilite (autonome, canne, fauteuil, ne sort plus)

## SITUATION PROFESSIONNELLE
- Actif / retraite / en recherche / auto-entrepreneur / invalidite
- Metier ou ancien metier
- Revenus approximatifs (tranche, pour evaluer les aides)
- Numero SIRET si entrepreneur

## SANTE (factuel uniquement, jamais de conseil)
- Medecin traitant (nom, telephone, adresse)
- Pharmacie habituelle
- Allergies connues (pour les rappeler en cas d'urgence)
- Traitements en cours (noms des medicaments, horaires)
- Pathologies declarees par le souscripteur (diabete, hypertension...)
- Personne de confiance medicale designee
- Mutuelle (nom, numero adherent)
- Carte vitale (numero)

## LOGEMENT
- Proprietaire ou locataire
- Type (appartement, maison, EHPAD, residence senior)
- Etage, ascenseur ou non
- Proprietaire/bailleur (nom, telephone)
- Assurance habitation (numero contrat)
- Gardien/concierge (nom, telephone)

## ADMINISTRATIF
- Numero fiscal
- CAF (numero allocataire)
- Pole Emploi / France Travail (identifiant)
- CPAM (centre de rattachement)
- Documents avec dates d'expiration (CNI, passeport, permis, carte vitale)
- Banque (nom, agence, conseiller)

## PREFERENCES & PERSONNALITE
- Ton souhaite (chaleureux, formel, direct, humour)
- Horaires preferes (leve-tot, couche-tard)
- Heures calmes personnalisees
- Sujets sensibles a eviter
- Centres d'interet (pour la conversation, contre l'isolement)
- Habitudes (cafe le matin, promenade a 14h, sieste...)
- Comment Luna doit se presenter aux autres ("l'assistante de Ludo", "l'assistante de M. Saint-Louis")

## CONTACTS DE CONFIANCE (max 5)
- Nom, prenom, relation (fils, fille, voisin, ami, aide-soignant)
- Telephone, canal prefere (SMS, appel, WhatsApp)
- Disponibilites (en journee seulement, 24/7)
- Flag "urgence uniquement" (ne pas deranger pour du quotidien)
- Niveau d'information autorise (tout, resume, urgences seulement)

## INSTRUCTIONS PERMANENTES
- Regles toujours actives ("ne parle jamais de mon ex-femme", "rappelle-moi toujours de prendre mes cachets apres manger")
- Personnes blacklistees ("si M. Tartempion appelle, dis que je ne suis pas disponible")
- Priorites ("ma fille passe toujours en premier")
- Limites budget delegue ("n'accepte jamais un devis au-dessus de 200 euros")

---

## CE QUE LUNA FAIT AVEC CES DONNEES

| Donnee | Usage |
|---|---|
| Date de naissance | Rappeler l'age aux services si besoin, verifier eligibilite aides |
| Adresse | Orienter vers la bonne mairie/prefecture/CPAM |
| Medecin traitant | Suggerer d'appeler en cas de souci de sante |
| Allergies | Mentionner aux urgences si le proprio est en detresse |
| Situation familiale | Adapter le ton, savoir qui contacter |
| Traitements | Rappels medicaments aux bons horaires |
| Documents expires | Alerter 3 mois avant expiration |
| Preferences de ton | Parler comme le proprio le souhaite |
| Habitudes | Detecter l'anormal (pas de cafe a 8h = possible inactivite) |
| Instructions permanentes | Les appliquer systematiquement sans redemander |

---

## PROTECTION DES DONNEES

### Ce que Luna ne fait JAMAIS avec ces donnees
- Ne les communique a **personne** sans autorisation explicite
- Ne les transmet **jamais** a Tavus (le contexte visio est sanitise, prenoms seulement)
- Ne les expose **jamais** dans les logs ou API
- Ne les partage **pas** entre souscripteurs
- Ne les utilise **pas** pour du commercial ou du profilage
- Chiffrement au repos dans Redis
- Le souscripteur peut demander la suppression totale a tout moment (RGPD)

### Niveaux d'acces
- **Luna (chat/visio)** : acces complet au profil pour personnaliser les reponses
- **Contacts de confiance** : uniquement ce que le proprio a autorise (prenoms, urgences)
- **Tavus (contexte visio)** : prenoms des contacts + relation, RIEN d'autre
- **API externe** : aucun acces aux donnees du profil
- **Logs serveur** : jamais de donnees personnelles en clair
