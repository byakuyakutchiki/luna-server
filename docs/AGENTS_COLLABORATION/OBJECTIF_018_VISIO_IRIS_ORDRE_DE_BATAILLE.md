# Objectif 018 — Visio Iris : ordre de bataille produit

Date : 2026-06-02
Coordinateur : Codex
Décideur : Ludovic

## Verdict fondateur

La visio Iris commence enfin à répondre, mais elle n'est pas validée.

Le problème n'est pas seulement technique. L'expérience globale est encore trop loin de la promesse :

- audio trop lent ou pas assez naturel ;
- vidéo/vision utile mais pas encore exploitée comme une vraie capacité ;
- tâches visio non prouvées de bout en bout ;
- décor et interface visio non acceptables : boutons superposés, contrôles inutiles, hiérarchie confuse, rendu pas premium.

Règle : on ne déclare pas la visio réussie parce qu'Iris parle. Elle doit être fluide, utile, belle et capable.

## Ordre de travail obligatoire

### Phase 1 — Audio conversationnel

Objectif : Iris doit répondre vite, naturellement, avec une voix jeune et dynamique.

Cibles :

- `time_to_first_audio_ms` sous 3000 ms sur phrase simple ;
- réponse courte par défaut ;
- voix féminine française jeune, pas pâteuse ;
- pas de phrase dépressive ou administrative ;
- persona : Iris = assistante visio de Luna, vive, technique, proactive, type Jarvis humain.

Responsables :

- Claude : déploiement et intégration backend/frontend.
- DeepSeek : audit latence par maillon STT / LLM / TTS / lecture audio.
- Kimi : choix voix, naturel, débit, énergie.
- Codex : synthèse logs et arbitrage.

Décisions Ludovic :

- choix voix ElevenLabs définitif ;
- validation si changement env Cloud Run `ELEVENLABS_VOICE_ID`.

### Phase 2 — Vidéo / vision réelle

Objectif : Iris doit voir réellement et utiliser ce qu'elle voit.

Cibles :

- badge honnête : jamais "Iris voit" si la vision n'est pas active ;
- Iris répond correctement à "qu'est-ce que tu vois ?";
- description caméra intégrée dans `/api/visio/chat` ;
- contexte visuel utile en notes et conversation ;
- pas de mensonge produit.

Responsables :

- Claude : intégration vision côté code.
- DeepSeek : audit flux caméra / perception / contexte transmis.
- Kimi : validation terrain de la cohérence visuelle.
- Codex : matrice target -> preuve.

### Phase 3 — Capacités pendant la visio

Objectif : Iris doit devenir une vraie concierge visio, pas un lecteur audio.

Targets à prouver :

- prendre des notes ;
- résumer une visio ;
- identifier contexte personnel / professionnel / projet / invité ;
- suivre qui participe ;
- proposer des actions selon le contexte ;
- retrouver ou citer les contacts de confiance ;
- préparer SMS/email/appel sans exécution réelle non confirmée ;
- inviter un participant ;
- travailler sur un document ou un projet commun.

Interdits pendant tests :

- pas de SMS réel sans validation ;
- pas d'appel réel sans validation ;
- pas d'email réel sans validation ;
- pas de paiement/réservation ;
- pas de suppression de données.

### Phase 4 — Décor / UI / expérience visuelle

Objectif : refaire l'environnement visio pour un rendu premium, clair et exploitable.

Constat actuel :

- boutons trop nombreux ;
- contrôles Daily/Simli inutiles visibles ;
- superpositions ;
- gros bouton central mal intégré ;
- hiérarchie confuse ;
- décor non premium ;
- interface non alignée avec Iris.

Direction cible :

- avatar plein cadre, respirant ;
- header discret : Iris + statut + timer ;
- action vocale simple et lisible ;
- raccrocher visible et fiable ;
- actions secondaires dans menu compact ;
- aucun bouton sans target prouvée ;
- aucun élément qui ment sur la fonctionnalité réelle.

Responsable visionnaire :

- Kimi est référent UX/graphisme/décor.

Claude ne code pas une refonte graphique majeure tant que Kimi n'a pas livré la proposition et que Ludovic ne valide pas.

## Règle de validation

Pour chaque bouton ou capacité :

1. target exacte ;
2. preuve terrain ;
3. log ou capture ;
4. risque ;
5. décision Ludovic si niveau 2/3 ;
6. commit GitHub.

Si une fonctionnalité n'a pas de target claire, elle sort de l'écran principal.

## Consignes agents

### Kimi

Tu es le visionnaire UX/décor.

Mission immédiate :

- relire `KIMI_REFONTE_UI_VISIO_IRIS_V1_017.md` ;
- proposer une V2 décor/UI premium ;
- lister chaque élément à retirer, garder, déplacer ;
- ne pas refaire l'app entière ;
- préserver la beauté et augmenter la clarté.

### DeepSeek

Tu es l'auditeur technique.

Mission immédiate :

- auditer la latence post patch `540d2d6` ;
- découper STT / LLM / TTS / audio ;
- dire si `eleven_flash_v2_5` améliore ou casse ;
- vérifier que les capacités visio peuvent être prouvées sans actions sensibles.

### Claude

Tu es intégrateur.

Mission immédiate :

- déployer le dernier main demandé ;
- ne pas lancer de refonte UI majeure seul ;
- attendre Kimi pour décor/UI ;
- implémenter seulement les patches niveau 1 validés par Codex/Ludovic.

### Codex

Tu coordonnes.

Mission immédiate :

- maintenir l'ordre : audio -> vidéo -> capacités -> décor ;
- refuser les validations prématurées ;
- transformer chaque retour terrain Ludovic en target vérifiable.
