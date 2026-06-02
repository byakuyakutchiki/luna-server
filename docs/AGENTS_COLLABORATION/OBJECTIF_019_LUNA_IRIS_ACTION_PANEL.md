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

## Panneau d'action Iris

Nom provisoire : **Iris Workbench**.

Fonctions attendues :

- afficher ce qu'Iris prépare ;
- montrer un brouillon de document ;
- montrer un tableau ou une checklist ;
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

### Phase 3 — Panneau d'action V1

Créer un panneau de travail non destructif.

Actions V1 autorisées :

- brouillon de note ;
- brouillon de courrier ;
- brouillon de checklist ;
- aperçu tableau simple ;
- sauvegarde uniquement si Ludovic valide.

Interdit V1 :

- envoi email réel ;
- SMS réel ;
- appel réel ;
- paiement ;
- réservation ;
- suppression de document.

Niveau : 2, validation Ludovic obligatoire avant déploiement visible.

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

### Claude

- intégration technique ;
- stabilisation `/ws/iris-voice` ;
- implémentation propre du panneau d'action quand Ludovic valide ;
- pas de déploiement visible majeur sans feu vert.

### Kimi

- vision UX ;
- qualité graphique ;
- panneau Iris premium ;
- vérifier que Luna et Iris ont chacune une identité claire.

### DeepSeek

- audit technique ;
- sécurité outils/actions ;
- vérifier que les tool calls ne déclenchent rien de sensible sans confirmation ;
- cartographier les endpoints documents/outils utilisables par Iris.

---

## Critères de validation

Iris V1 est validée seulement si :

- elle répond vite et naturellement ;
- elle se tait quand on ne lui parle pas ;
- elle n'exécute rien de sensible sans confirmation ;
- elle peut produire au moins un brouillon visible dans le panneau d'action ;
- Ludovic peut comprendre ce qu'elle fait sans ouvrir F12 ;
- l'expérience est plus belle, plus fluide et plus fonctionnelle que l'ancien empilement visio.

---

## Prochaine action

1. Chaque agent lit ce document.
2. Claude vérifie l'état exact du dernier déploiement Cloud Run.
3. Kimi propose l'UX du panneau Iris Workbench V1.
4. DeepSeek audite les outils/action documents disponibles et les garde-fous.
5. Codex synthétise avant toute implémentation visible.
