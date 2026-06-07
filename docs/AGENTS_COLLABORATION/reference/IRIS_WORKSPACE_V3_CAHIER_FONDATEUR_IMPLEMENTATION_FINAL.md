# IRIS WORKSPACE V3 - Cahier Fondateur Implementation Final

> Source de vérité active pour Iris Workspace V3. Cette V3 remplace la V2 comme référence de travail. Le .docx original contient les visuels intégrés, dont Luna et le logo YAWatch Industries. Média intégré détecté : 2 fichier(s).

IRIS WORKSPACE V3

Cahier fondateur complet - Produit, UX, Direction Artistique et Implémentation





Statut du document

Source de vérité officielle pour /team. À placer dans le dépôt GitHub. À transmettre intégralement à Codex, Claude, Kimi et tout intervenant technique. Ce document ne doit pas être remplacé par un résumé simplifié.



Propriétaire de la vision : Ludovic Saint-Louis / YAWatch Industries

Version : 3.1 - Référence visuelle intégrée : Luna CEO Corporate sans poupée.



Sommaire

Résumé exécutif

Vision produit

Décisions d’architecture

Univers YAWatch Industries

Rôles humains et IA

Workflow officiel séquencé

Boucle d’amélioration et mémoire vivante

Sources, documents et sécurité

Visio, Simli et présence humaine

Direction artistique officielle

Système d’ambiance vivante

Architecture spatiale des écrans

Composants et modèle de données

Critères d’acceptation

Roadmap d’implémentation

Instructions directes à Claude/Codex



1. Résumé exécutif

Phrase produit

Iris Workspace est la salle stratégique de YAWatch Industries où humains, Iris, IQ et Luna collaborent pour transformer des idées en décisions traçables et en livrables professionnels.



La V1/V2 observée a corrigé certains problèmes de lisibilité, mais reste trop proche d’un tableau de bord à cartes. La cible n’est pas Trello, Miro, Zoom ou un CRM avec IA. La cible est une salle de réflexion augmentée, premium, séquencée, vivante et directement exploitable par une entreprise.

L’enjeu principal n’est pas d’ajouter des boutons. L’enjeu est de construire un processus guidé : collecter les idées, analyser les sources, débattre, refondre la proposition, comparer les versions, recommander, valider, produire un livrable et archiver la mémoire de la décision.

Point

Décision officielle



Positionnement

Salle stratégique du siège numérique YAWatch Industries.



Visio

Simli est intégré comme composant de présence, mais ne doit pas dominer le produit.



Luna

Luna est la CEO / direction stratégique. Elle recommande et arbitre.



Iris

Iris est l’assistante exécutive / secrétaire opérationnelle. Elle organise, reformule, synthétise, produit.



IQ

IQ est une entité analytique non humaine. Il lit, compare, détecte les risques.



Abby

Abby appartient à l’univers narratif. Elle n’est pas présente dans la réunion standard.



Graphisme

Style YAWatch Industries Corporate : noir profond, métal, verre, violet, vert, cyan, halos. Aucun emoji métier.



2. Vision produit

Iris Workspace doit permettre à une équipe de gagner du temps sur une problématique. L’objectif n’est pas seulement de parler, mais de faire avancer une idée jusqu’à une décision exploitable. Chaque intervention d’un participant doit être utilisée : si un participant soulève un risque budget ou une cible oubliée, Iris doit intégrer cette remarque dans une version améliorée avant validation.

Principes absolus

Une réunion doit produire un résultat concret : décision, synthèse, plan d’action, document final ou tâche.

Chaque idée doit être conservée, versionnée et récupérable.

Chaque étape doit être compréhensible en quelques secondes.

Les IA assistent la réflexion, mais les humains gardent le contrôle de la validation.

Le travail doit occuper l’écran, pas le décor.

La qualité visuelle est une fonctionnalité produit : elle doit inspirer confiance à une entreprise.

Ce que le produit ne doit pas devenir

Un Trello avec des IA.

Un formulaire d’ajout de cartes.

Une simple visioconférence.

Un mindmap décoratif.

Une interface sombre illisible.

Une collection de boutons sans résultat final.

3. Décisions d’architecture

3.1 Simli : composant intégré, pas produit central

La question posée : faut-il construire Iris Workspace à l’intérieur de Simli ou faire un workspace à part ? Décision : Iris Workspace est le produit principal. Simli fournit la présence vidéo/avatar/micro, comme un composant spécialisé. Le travail, la décision, les sources, les versions et les exports restent pilotés par Iris Workspace.

Approche

Avantage

Risque

Statut



Tout dans Simli

Rapide pour l’avatar et la visio.

La visio impose sa logique. Le travail devient secondaire.

Rejeté.



Sans Simli

Contrôle total.

Trop coûteux de recréer toute la présence vidéo.

Rejeté pour le MVP.



Workspace principal + Simli intégré

Le travail reste central, Simli sert la présence.

Demande une intégration propre par composant.

Validé.



3.2 Architecture logique cible

Iris Workspace doit être organisé en quatre couches :

Couche

Responsabilité

Exemples



Présence

Participants humains et IA visibles, caméra/micro, prise de parole.

SimliVideoTile, ParticipantSeat, état micro/caméra.



Travail

Plan central, documents, idées, annotations, versions.

CentralCanvas, SourceCard, IdeaVersion.



Décision

Étapes, votes, recommandation, validation.

MeetingStepper, VotePanel, LunaRecommendation.



Mémoire

Historique, traces, exports, restauration.

VersionTimeline, SessionArchive, ExportLog.



4. Univers YAWatch Industries



Le style officiel de YAWatch Industries est premium, corporate, technologique et cinématographique. Le logo impose un langage visuel : métal brossé, noir profond, lumière froide, violet, précision, institution. Iris Workspace doit parler ce même langage.



Référence Luna officielle

La représentation “Luna CEO Corporate” ci-dessus est la référence visuelle officielle pour les interfaces professionnelles : Iris Workspace, dashboards, démos clients, présentations B2B. La poupée ne doit pas apparaître dans ces interfaces professionnelles.



Séparation univers professionnel / univers narratif

Élément

Usage professionnel

Usage narratif



Luna CEO sans poupée

Oui : workspace, dashboard, commercial, B2B.

Possible, mais pas obligatoire.



Luna Doll

Non : pas dans les réunions ni démos entreprise.

Oui : série, storytelling, émotion, enfance de Luna.



Abby

Non par défaut dans Iris Workspace.

Oui : série et narration YAWatch-LUNA.



Iris

Oui : secrétaire exécutive dans le workspace.

Oui : personnage de l’univers.



IQ

Oui : entité analytique.

Oui : moteur intelligent, abstraction.



5. Rôles humains et IA

Rôle

Nature

Mission

Droits MVP

Manifestation visuelle



Owner

Humain

Créer la session, lancer votes, valider étapes, clôturer.

Tous droits réunion.

Siège prioritaire, contrôles avancés.



Participant

Humain

Proposer, commenter, voter, annoter.

Créer idées/sources, voter, parler.

Caméra/avatar, micro, main levée, halo actif.



Spectateur

Humain

Observer et demander la parole.

Lecture + demande parole.

Zone séparée, présence réduite.



Iris

IA/personnage

Organiser, classer, reformuler, synthétiser, exporter.

Actions automatiques supervisées.

Vert émeraude, mouvements de classement.



IQ

IA analytique

Lire sources, extraire risques, comparer versions.

Analyse et rapports.

Cyan, graphes, lignes de connexion.



Luna

Direction

Recommander, arbitrer, conclure.

Avis stratégique.

Violet, halo décisionnel, focus.



Décision sur Iris

Iris ne doit pas être un robot générique. Elle peut être incarnée comme une assistante exécutive humaine ou semi-humaine, cohérente avec Luna, mais son design doit rester plus discret et opérationnel. Son identité : calme, précision, organisation. Couleur : vert émeraude. IQ, lui, doit rester plus abstrait et analytique pour ne pas confondre les rôles.

6. Workflow officiel séquencé

Le workspace doit fonctionner comme une réunion guidée. Une seule étape principale doit être active à la fois. Les outils affichés dépendent de l’étape. Cela évite le brouillon.

#

Étape

Objectif

Actions utilisateur

Sortie attendue



1

Entrée réunion

Configurer présence.

Activer caméra/micro, choisir siège, confirmer rôle.

Participants prêts.



2

Brief mission

Définir le sujet.

Owner écrit objectif, contexte, livrable attendu.

Brief validé.



3

Collecte

Rassembler idées et sources.

Ajouter idée, note, fichier, lien.

Matière brute.



4

Organisation Iris

Classer et regrouper.

Owner déclenche Iris, participants vérifient.

Thèmes structurés.



5

Vote priorité

Choisir l’axe à traiter.

Vote humain.

Sujet prioritaire.



6

Analyse IQ

Lire et analyser.

Demander analyse, sélectionner sources.

Risques/opportunités.



7

Débat humain

Réagir utilement.

Chaque participant donne avis/objection.

Objections structurées.



8

Refonte Iris

Transformer remarques en meilleure version.

Owner demande refonte.

Proposition V2/V3.



9

Comparaison IQ

Comparer versions.

Analyser V1 vs V2 vs V3.

Comparatif robuste.



10

Recommandation Luna

Prendre de la hauteur.

Demander avis Luna.

Recommandation stratégique.



11

Validation

Choisir ou retourner en refonte.

Vote final.

Décision validée ou retour.



12

Livrable

Produire document final.

Générer PDF/Word/tâches.

Livrable professionnel.



13

Distribution

Partager et archiver.

Envoyer aux participants.

Mémoire conservée.



7. Boucle d’amélioration et mémoire vivante

La valeur du workspace vient du fait que les remarques améliorent réellement le résultat. Une objection n’est pas un commentaire perdu. Elle doit être capturée, classée, intégrée ou explicitement rejetée avec justification.

Règle de refonte

Après le débat humain, Iris doit générer une version améliorée avant la validation finale. La validation ne doit pas arriver directement après les avis, sinon la réunion n’a pas utilisé l’intelligence collective.



Objet

Champs à stocker

Pourquoi



Idée

id, auteur, titre, contenu, date, statut, version courante.

Ne jamais perdre l’origine de la proposition.



Version

id, idée, numéro V1/V2/V3, contenu, diff, justification.

Comparer et revenir en arrière.



Objection

auteur, texte, cible, importance, statut.

Transformer les critiques en amélioration.



Vote

votant, choix, étape, horodatage.

Traçabilité décisionnelle.



Analyse IQ

sources, résumé, risques, limites, score.

Ancrer l’analyse dans les données.



Avis Iris

synthèse, consensus, désaccords, refonte proposée.

Montrer comment les idées évoluent.



Avis Luna

recommandation, justification, conditions.

Donner la conclusion stratégique.



Actions obligatoires sur une version

Comparer avec version précédente.

Restaurer une ancienne version.

Fusionner deux versions.

Marquer comme écartée sans supprimer.

Promouvoir en version candidate.

Valider en décision finale.

8. Sources, documents et sécurité

Ajouter une source doit être complet dès le MVP. L’utilisateur doit pouvoir ajouter une source depuis son PC, son téléphone, un lien externe ou une note manuelle.

Mode source

MVP

État UI attendu



Fichier local

PDF, DOCX, XLSX, PPTX, TXT, PNG/JPG/WEBP.

Dropzone + bouton choisir fichier + progression upload.



Lien web

URL HTTPS.

Champ URL + titre + validation + statut scan.



YouTube

Lien YouTube traité comme URL.

Preview miniature/titre si possible, statut sécurité.



Note manuelle

Titre + texte + tags.

Création instantanée sur plan central.



Photo mobile

Image uploadée depuis téléphone.

Preview + OCR plus tard.



Workflow source obligatoire

Sélection ou saisie.

Validation type/URL.

Upload ou enregistrement.

Prévisualisation sur le plan central.

Extraction texte/métadonnées.

Analyse IQ disponible.

Annotation ou discussion.

Lien avec idée/version/décision.

Archivage avec session.

Sécurité minimale

Limiter les types MIME.

Refuser fichiers exécutables.

Normaliser les URLs.

Afficher “bloqué sécurité” si nécessaire.

Séparer upload brut, extraction et analyse IA.

Tracer auteur/date/source.

9. Visio, Simli et présence humaine

La réunion doit rappeler la simplicité de Zoom pour la caméra et le micro, mais dans un environnement plus avancé. Chaque participant doit avoir un emplacement clair dans la salle, avec caméra activable, micro activable, avatar si caméra désactivée, main levée et statut.

Fonction

Exigence UX

Implémentation recommandée



Caméra

Visible par siège, activable/désactivable.

Composant SimliVideoTile ou WebRTC tile.



Micro

Bouton proche du siège, état clair.

micState: muted/unmuted/speaking.



Avatar

Fallback si caméra off.

Initiales ou avatar corporate, pas emoji.



Prise de parole

Halo autour du siège + niveau audio.

activeSpeakerId + animation CSS.



Main levée

Demande parole visible.

raisedHand boolean + file d’attente.



Spectateur

Séparé des participants actifs.

SpectatorRail.



Règle visio

La visio doit soutenir la réunion, pas prendre toute la place. Le centre reste le plan de travail.



10. Direction artistique officielle

La qualité graphique doit être traitée comme une exigence fonctionnelle. Le produit doit impressionner une entreprise. Il ne doit pas ressembler à une maquette, une application scolaire ou un Trello blanc.

Référence visuelle principale

Référence : Luna CEO Corporate sans poupée, bureau futuriste YAWatch Industries, hologrammes professionnels, city skyline, noir profond, bleu nuit, cyan, violet, métal, verre. Cette image est la base d’ambiance du produit B2B.



Palette

Usage

Couleur

Rôle émotionnel



Base

Noir profond / bleu nuit

Profondeur, sérieux, institution.



YAWatch

Argent métal

Premium, technologie.



Luna

Violet lumineux

Stratégie, décision, autorité calme.



Iris

Vert émeraude

Organisation, fluidité, assistance.



IQ

Cyan analytique

Données, analyse, logique.



Alerte faible

Ambre discret

Point à surveiller.



Erreur

Rouge sobre

Blocage, sécurité.



Interdictions visuelles

Aucun emoji métier comme icône principale : pas d’ampoule, papier, coche, éclair ou cerveau en pictogrammes texte.

Pas de couleurs aléatoires par carte.

Pas de style Trello/CRM.

Pas de badges enfantins.

Pas de surcharge de bordures.

Pas de fond blanc plat sans identité.

Pas d’interface “prototype rapide”.

Remplacements attendus

À éviter

Remplacement



Emoji ampoule / Idée

Libellé “PROPOSITION” + icône SVG lineaire premium.



Emoji papier / Source

Libellé “SOURCE” + pictogramme document sobre.



Emoji coche / Décision

Libellé “DÉCISION” + sceau minimal.



Emoji éclair / Action

Libellé “ACTION” + pictogramme workflow.



Emoji cerveau / IQ

Noyau analytique cyan ou symbole abstrait.



11. Système d’ambiance vivante

Les IA ne doivent pas seulement être listées. Leur intervention doit modifier subtilement l’ambiance de la salle. Le produit doit être vivant sans devenir gadget.

Intervenant

Ambiance

Animations attendues

But



Humain

Halo discret autour du siège.

Pulsation audio, bordure active.

Savoir qui parle.



Iris

Vert émeraude.

Cartes qui se rangent, groupes qui se forment, synthèse qui apparaît.

Ressentir l’organisation.



IQ

Cyan analytique.

Lignes entre sources, surlignages, graphes, scanning doux.

Ressentir l’analyse.



Luna

Violet stratégique.

Focus central, réduction du bruit visuel, recommandation mise en scène.

Ressentir la décision.



Ces effets doivent rester subtils : transitions lentes, lumière douce, pas de clignotement agressif.

12. Architecture spatiale des écrans

Vue cible

Le plan central doit être la zone dominante. Les participants gravitent autour comme une orbite, avec des caméras/avatars. La progression de réunion doit être visible. Les actions doivent être contextuelles selon l’étape.

Schéma conceptuel :

┌──────────────────────────────────────────────────────────────┐ │ YAWatch Industries / Iris Workspace Étape : Collecte │ ├──────────────────────────────────────────────────────────────┤ │ Sarah cam Thomas cam Alice cam Luna │ │ │ │ ┌────────────────────────────────────────────┐ │ │ │ │ │ │ │ PLAN CENTRAL VIVANT │ │ │ │ idées, sources, documents, versions, │ │ │ │ annotations, analyses, votes, décisions │ │ │ │ │ │ │ └────────────────────────────────────────────┘ │ │ │ │ Owner cam Iris secrétaire IQ analyste │ ├──────────────────────────────────────────────────────────────┤ │ Actions contextuelles : Ajouter idée | Source | Voter | ... │ └──────────────────────────────────────────────────────────────┘

Modes

Mode

Quand

Focus UI



Accueil

Début réunion.

Caméras, brief, rôles, préparation.



Collecte

Idées/sources.

Plan central + boutons ajout.



Organisation Iris

Classement.

Groupes, thèmes, synthèse verte.



Analyse IQ

Analyse documents.

Connexions, risques, données cyan.



Débat

Avis humains.

Caméras + objections structurées.



Refonte

Iris améliore.

Diff V1/V2, objections intégrées.



Luna

Recommandation.

Carte stratégique violette.



Vote

Choix final.

Options + résultats.



Export

Livrable.

PDF/Word/tâches + destinataires.



13. Composants et modèle de données

Composants frontend recommandés

Composant

Responsabilité



IrisWorkspacePage

Shell global.



MeetingStepper

Étape active, règles de passage.



CentralCanvas

Plan central avec objets.



ParticipantOrbit

Placement des sièges autour du plan.



ParticipantSeat

Caméra/avatar/micro/statut.



SimliVideoTile

Intégration Simli/WebRTC.



SourceImportModal

Fichier, lien, note.



WorkspaceObject

Objet générique : idée/source/version/analyse.



VersionTimeline

Versions récupérables.



IrisRefactorPanel

Objections -> V2.



IQAnalysisPanel

Risques/opportunités.



LunaRecommendationPanel

Conclusion stratégique.



VotePanel

Vote priorité/final.



ExportPanel

Génération et distribution.



Modèle de données minimal

Entité

Champs



Session

id, title, brief, ownerId, currentStep, status, createdAt, updatedAt.



Participant

id, sessionId, name, role, permissions, cameraState, micState, seatPosition.



Source

id, sessionId, type, title, url, filePath, mimeType, status, extractedText, metadata, authorId.



Idea

id, sessionId, title, status, authorId, currentVersionId.



IdeaVersion

id, ideaId, versionNumber, content, diffSummary, basedOnVersionId, createdBy.



Objection

id, targetId, authorId, content, severity, status.



Vote

id, sessionId, targetId, voterId, choice, step, createdAt.



AIOutput

id, sessionId, aiRole, targetId, content, sourceIds, createdAt.



Export

id, sessionId, format, path, recipients, createdAt.



14. Critères d’acceptation

En 3 secondes, on comprend qu’on est dans Iris Workspace, salle stratégique YAWatch Industries.

En 3 secondes, on voit qui est présent : humains, Iris, IQ, Luna.

En 3 secondes, on comprend l’étape actuelle de la réunion.

Le plan central domine l’écran.

Chaque participant a une caméra/micro/présence claire.

Le bouton source permet fichier local, lien et note.

Aucun emoji métier dans l’UI principale.

Le style est aligné sur Luna CEO Corporate et logo YAWatch.

Les remarques humaines déclenchent une refonte Iris avant validation.

Les idées et versions sont conservées et récupérables.

La décision finale génère un livrable exportable.

L’interface est présentable à une entreprise sans excuse.

15. Roadmap d’implémentation

Phase

Objectif

Livrables



P0.1

Refonte visuelle

Layout YAWatch, suppression emojis, plan central, orbite participants.



P0.2

Présence humaine

SimliVideoTile, caméra/micro par siège, speaker halo.



P0.3

Sources complètes

Upload fichier, URL, note, statuts de traitement.



P0.4

Stepper réunion

Étapes visibles, actions contextuelles, validation owner.



P1.1

Mémoire vivante

IdeaVersion, VersionTimeline, restaurer/comparer.



P1.2

Refonte Iris

Objections structurées -> proposition V2.



P1.3

Analyse IQ

Rapport lié aux sources.



P1.4

Recommandation Luna

Carte stratégique + vote final.



P2

Exports

PDF/Word, compte-rendu, plan d’action, distribution.



16. Instructions directes à Codex et Claude

Source de vérité

Ce document doit être transmis complet. Ne pas le remplacer par un résumé. Toute implémentation qui contredit ce document doit être revue.



À faire

À ne pas faire



Coder des blocs complets du workflow.

Ajouter des boutons isolés sans résultat.



Respecter la DA YAWatch Corporate.

Inventer une nouvelle DA SaaS générique.



Intégrer Simli comme composant.

Faire de la visio le centre du produit.



Créer un plan central vivant.

Créer une simple liste de cartes.



Prévoir upload fichier/lien/note.

Limiter source à du texte.



Versionner les idées.

Écraser ou supprimer les anciennes propositions.



Utiliser SVG/animations/lumière.

Utiliser emojis comme icônes métier.



Definition of Done développeur

Screenshot final comparé à la référence Luna CEO Corporate.

Aucun emoji métier visible.

Les caméras/micros ont des emplacements clairs.

SourceImportModal possède trois modes : fichier, lien, note.

MeetingStepper affiche l’étape et limite les actions au contexte.

CentralCanvas occupe la majorité de la valeur visuelle.

Iris/IQ/Luna ont des états visuels distincts.

Modèle de données prêt pour versions et historique.

Le résultat est montrable à un dirigeant.

17. Conclusion

Iris Workspace doit être traité comme un produit premium central de YAWatch Industries. Il ne s’agit pas de corriger une maquette, mais de créer une salle stratégique où humains et IA collaborent réellement. Le code doit servir cette vision : présence humaine, plan central, séquence de décision, mémoire vivante, refonte intelligente et livrable final.

Règle finale

La technologie sert la vision. La vision ne doit pas être réduite pour s’adapter à une implémentation pauvre.
