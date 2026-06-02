# Objectif 019 — Luna compagnon / Iris opératrice / panneau d'action

Date : 2026-06-02
Lead coordination : Codex
Statut : cadrage produit actif
Priorité : haute

---

## Décision fondateur

Luna et Iris ne doivent plus être mélangées.

### Luna

Luna est la compagne conversationnelle et la PDG symbolique de YAWatch.

Elle sert à :
- discuter ;
- conseiller ;
- réfléchir avec Ludovic ;
- accompagner ;
- parler de culture, musique, vision, stratégie, quotidien ;
- reconnaître ses limites.

Quand la demande devient opérationnelle, administrative, technique ou documentaire, Luna doit orienter vers Iris.

Exemple attendu :

> Je peux t'aider à réfléchir à la stratégie. Pour rédiger le courrier et préparer le PDF, appelle Iris.

### Iris

Iris est la secrétaire opérationnelle, technique et administrative.

Elle sert à :
- produire ;
- rédiger ;
- structurer ;
- chercher ;
- organiser ;
- préparer un document ;
- préparer un tableau ;
- prendre des notes ;
- résumer une réunion ;
- déclencher des outils autorisés avec confirmation ;
- travailler avec plusieurs participants.

Iris n'est pas une simple voix. Elle doit donner l'impression qu'elle travaille réellement.

---

## État GitHub au moment du cadrage

Derniers commits importants :

- `943d3c4` : mode AUDIO-FIRST, Iris invisible présente par la voix.
- `7c768a5` : remplacement ElevenLabs par OpenAI TTS pour Iris Audio.
- `badedda` : cahier des charges audio + support multi-participants.
- `f773567` : migration OpenAI Realtime, objectif qualité proche Luna Voix.
- `cc6ee04` : transcription française + silence étendu.

Référence active actuelle :

- `docs/IRIS_CAHIER_DES_CHARGES_AUDIO.md`
- `docs/IRIS_AUDIO_QUALITY_AUDIT.md`
- `docs/ARCHITECTURE_AUDIO_AUDIT.md`

Important :

Le mode vidéo/avatar Simli/Daily est désactivé dans le flux actif. Le code ancien reste présent dans `static/simli.html`, mais `_launchVisioFlow()` bascule immédiatement en `AUDIO-FIRST`.

---

## Objectif produit V1

Créer une expérience où Iris semble active, utile et professionnelle, même sans avatar vidéo.

Quand Ludovic demande une action :

1. Iris écoute.
2. Iris reformule si nécessaire.
3. Iris confirme si l'action est engageante.
4. Un panneau de travail s'ouvre.
5. Le contenu apparaît progressivement : note, courrier, tableau, résumé, checklist.
6. Ludovic peut valider, modifier, télécharger ou sauvegarder.
7. Rien de sensible n'est envoyé sans confirmation.

---

## Iris Command Screen

Nom cible : **Iris Command Screen**.

Ancien nom provisoire : Iris Workbench.

Décision fondateur du 2026-06-02 :

Iris ne doit pas seulement écrire qu'elle peut faire un tableau, un document ou une analyse. Elle doit matérialiser son travail dans un écran virtuel visible.

La cible n'est pas un chatbot avec un panneau texte. La cible est un poste de commande futuriste et exploitable :

- un écran de travail qui s'allume quand Iris agit ;
- une interface qui donne l'impression que l'utilisateur est aux commandes ;
- des rendus visuels réels : tableau, carte, dossier, synthèse, checklist, document, plan d'action ;
- un contenu structuré qui peut ensuite être matérialisé en document numérique si Ludovic valide ;
- une capacité à croiser, organiser, afficher et mettre à jour les données pendant la conversation ;
- une expérience premium, lisible, dynamique, niveau outil professionnel ambitieux.

Règle produit :

> Si Iris dit "je prépare / j'affiche / je crée un tableau", alors quelque chose doit apparaître visuellement dans le Command Screen. Sinon, le travail n'est pas livré.

Phrase interdite pour Iris :

> Je ne peux pas afficher directement un tableau visuel.

Phrase attendue :

> J'ouvre l'écran de travail. Je te prépare une première structure, puis je te demanderai les informations manquantes.

### Composants visuels attendus V1

Le Command Screen V1 doit afficher au minimum :

- **Data Board** : vrai tableau visuel stylé, pas markdown brut ;
- **Document Draft** : brouillon de courrier ou note avec mise en page lisible ;
- **Action Board** : checklist / plan d'action avec statuts ;
- **Context Panel** : ce qu'Iris a compris de la demande ;
- **Missing Info Panel** : les informations qu'Iris doit demander avant de finaliser ;
- **Status Rail** : analyse, construction, prêt, validation requise, sauvegarde, terminé.

### Comportement attendu

Quand l'utilisateur demande :

- "affiche-moi un tableau" ;
- "croise ces données" ;
- "prépare un workspace" ;
- "fais un courrier" ;
- "organise-moi ça" ;
- "montre-moi ce que tu fais" ;

Iris doit :

1. ouvrir le Command Screen ;
2. choisir le bon type de rendu ;
3. afficher une première version visuelle immédiatement ;
4. poser une question uniquement si une information manque ;
5. mettre à jour l'écran après la réponse ;
6. ne jamais prétendre avoir fait une action qui n'a pas été matérialisée ;
7. ne jamais exécuter une action sensible sans validation.

---

## Panneau d'action Iris V1

Fonctions attendues :

- afficher ce qu'Iris prépare ;
- montrer un brouillon de document avec mise en page ;
- montrer un tableau visuel ou une checklist interactive ;
- indiquer l'état : analyse, rédaction, prêt, validation requise ;
- proposer les actions : modifier, télécharger, sauvegarder dans Documents, annuler ;
- ne jamais ressembler à un chatbot ajouté au hasard.

Le panneau doit être sobre, premium, lisible et compatible mobile.

---

## Phasage

### Phase 1 — Clarification identité

- Luna = conversation / conseil / compagnon.
- Iris = action / documents / technique / administratif.
- Les prompts doivent respecter cette séparation.
- Les libellés UI doivent arrêter de mélanger Luna et Iris.

Niveau : 1 si textes/prompts seulement, 2 si modification visible majeure.

### Phase 2 — Stabilisation Iris Realtime

Valider sur navigateur et APK :

- `iris_ws_open`
- `iris_ws_ready`
- transcription utilisateur correcte ;
- réponse audio rapide ;
- interruption/barge-in acceptable ;
- raccrocher immédiat ;
- pas de SMS/appel/email automatique.

Niveau : 1 pour logs/garde-fous, 2 pour refonte pipeline.

### Phase 3 — Command Screen V1

Créer un écran de travail visuel non destructif.

Actions V1 autorisées :

- brouillon de note avec rendu visuel ;
- brouillon de courrier avec rendu document ;
- brouillon de checklist avec cases/statuts ;
- tableau visuel stylé, lisible, non markdown brut ;
- contexte compris + informations manquantes ;
- sauvegarde uniquement si Ludovic valide.

Interdit V1 :

- envoi email réel ;
- SMS réel ;
- appel réel ;
- paiement ;
- réservation ;
- suppression de document.

Niveau : 2, validation Ludovic obligatoire avant déploiement visible.

Critères "pas de fausse livraison" :

- ne pas dire "c'est bon" si le tableau est seulement du texte ;
- ne pas demander à Ludovic de tester si le Command Screen n'affiche pas au moins un rendu visuel réel ;
- ne pas valider tant qu'Iris répond "je ne peux pas afficher" ;
- ne pas valider tant que l'utilisateur ne peut pas voir ce qu'Iris produit sans ouvrir F12 ;
- ne pas valider tant que la version mobile superpose les contrôles.

### Phase 4 — Porte-documents

Brancher le panneau Iris au vrai module Documents.

Cible :

- sauvegarder un brouillon ;
- retrouver un document ;
- afficher un statut clair ;
- télécharger PDF/Word quand disponible.

Niveau : 2/3 selon stockage et données.

### Phase 5 — Multi-participants

Permettre à plusieurs personnes de participer à une session Iris.

Cible V1 :

- session partagée ;
- historique partagé ;
- Iris sait qu'il y a plusieurs personnes ;
- elle ne coupe pas la parole ;
- elle résume qui a demandé quoi si le contexte le permet.

Pas de diarisation obligatoire en V1.

---

## Rôles agents

### Codex

- lead coordination ;
- tenir la séparation Luna/Iris ;
- transformer les retours terrain en objectifs vérifiables ;
- ne pas laisser l'équipe repartir sur Simli/avatar si ce n'est pas la priorité validée.
- cadrer le Command Screen et empêcher les livrables à moitié finis.

### Claude

- intégration technique ;
- stabilisation `/ws/iris-voice` ;
- implémentation propre du Command Screen ;
- rendre les composants visuels réels : table, document, checklist, contexte, infos manquantes ;
- empêcher Iris de dire qu'elle ne peut pas afficher si le frontend sait l'afficher ;
- pas de déploiement visible majeur sans feu vert.

### Kimi

- vision UX ;
- qualité graphique ;
- Command Screen premium, futuriste, professionnel ;
- vérifier que le rendu donne l'impression d'un poste de commande, pas d'un bloc texte ;
- vérifier que Luna et Iris ont chacune une identité claire.

### DeepSeek

- audit technique ;
- sécurité outils/actions ;
- vérifier que les tool calls ne déclenchent rien de sensible sans confirmation ;
- cartographier les endpoints documents/outils utilisables par Iris.
- auditer le flux intention utilisateur -> type de rendu -> affichage -> action autorisée.

---

## Critères de validation

Iris V1 est validée seulement si :

- elle répond vite et naturellement ;
- elle se tait quand on ne lui parle pas ;
- elle n'exécute rien de sensible sans confirmation ;
- elle peut produire au moins un rendu visuel réel dans le Command Screen ;
- elle affiche un tableau visuel stylé quand on lui demande un tableau ;
- elle affiche ce qu'elle comprend et ce qui manque avant de finaliser ;
- Ludovic peut comprendre ce qu'elle fait sans ouvrir F12 ;
- l'expérience est plus belle, plus fluide et plus fonctionnelle que l'ancien empilement visio.

---

## Prochaine action

1. Chaque agent lit ce document.
2. Claude vérifie l'état exact du dernier déploiement Cloud Run.
3. Kimi propose l'UX du panneau Iris Workbench V1.
4. DeepSeek audite les outils/action documents disponibles et les garde-fous.
5. Codex synthétise avant toute implémentation visible.
