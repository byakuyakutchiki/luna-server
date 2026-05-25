# Consigne — Investigation interne APK / voix

**Date** : 2026-05-25  
**Auteur** : Codex, sur consigne Ludovic  
**Priorité** : critique  
**Statut** : à exécuter avant toute nouvelle correction non validée  

## Décision Ludovic

Ludovic demande une investigation plus profonde. Les quatre agents ne doivent plus
rester en surface.

Un agent doit être explicitement responsable de l'intérieur APK/WebView/cache/build,
pendant que les autres couvrent serveur, cockpit et lisibilité.

Objectif : arrêter de supposer, prouver ce qui se passe réellement.

## Constat réel Ludovic

Test cockpit après restauration télémétrie :

- APK Fondateur : OK, téléphone vu récemment.
- APK v2.8 active et à jour.
- Chronologie voix revenue avec 11 événements.
- Clic OK.
- Token OK.
- Micro OK.
- Capture micro active.
- WebSocket créé et ouvert.
- Premier audio envoyé vers Luna.
- WebSocket fermé.
- Session terminée.
- Toujours aucune voix entendue.

Conclusion : le client APK sait démarrer la voix et envoyer le premier audio, mais
aucun audio de retour n'est entendu.

## Règle de travail

Avant toute nouvelle correction :

1. chaque agent doit dire précisément ce qu'il observe ;
2. aucun agent ne doit garder une information dans son silo ;
3. tout signal Cloud Run, Sentry, APK, cockpit ou build doit être résumé dans GitHub ;
4. pas de déploiement ou rebuild sans validation Ludovic ;
5. ne pas négliger le cache, la WebView, ni la reconstruction APK.

## Attribution stricte des rôles

### DeepSeek — Responsable intérieur APK / WebView / cache / build

DeepSeek est désigné comme agent principal pour aller "à l'intérieur de l'APK".

Mission :

- auditer `android-app/java/fr/yawatch/luna/MainActivity.java` ;
- vérifier WebView settings, cache, permissions micro, clearCache, reload ;
- vérifier que l'APK installée contient bien le code attendu ;
- vérifier si `static/index.html` chargé dans la WebView est bien la version Cloud Run active ;
- vérifier si un cache WebView, service worker, asset cache ou localStorage peut garder un ancien état ;
- vérifier si un rebuild APK est nécessaire ou non ;
- proposer un protocole de preuve : comment confirmer depuis le téléphone que l'APK exécute la bonne version ;
- proposer, si nécessaire, un geste maintenance APK : pull-to-refresh / clear cache / reload / heartbeat.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_008_APK_INTERNE.md`

Interdictions :

- pas de déploiement Cloud Run ;
- pas de modification Google Cloud ;
- pas de secrets ;
- pas de rebuild APK sans validation Ludovic.

### Claude — Responsable serveur voix / Cloud Run / OpenAI

Claude reste responsable du serveur et de l'intégration finale.

Mission :

- vérifier les logs `/ws/luna-voice` au moment du test réel ;
- dire si `gpt-realtime-mini` a réellement été déployé ou non ;
- donner la révision Cloud Run active ;
- confirmer le modèle réellement chargé par le process ;
- vérifier si le premier audio arrive côté serveur ;
- vérifier si OpenAI Realtime accepte la session ;
- vérifier si `response.audio.delta` revient ;
- donner le code de fermeture WebSocket et l'erreur exacte ;
- centraliser Cloud Run et Sentry dans GitHub.

Livrables :

- `docs/AGENTS_COLLABORATION/RAPPORT_CLOUD_RUN_008.md`
- `docs/AGENTS_COLLABORATION/RAPPORT_SENTRY_OBJECTIF_008.md`
- mise à jour de `docs/AGENTS_COLLABORATION/agents/CLAUDE_AVIS_008.md`

Interdictions :

- pas de nouvelle correction sans validation Ludovic ;
- pas de mélange UI mobile / modèle OpenAI / cache APK dans un même changement ;
- pas de déploiement "pour voir" sans résumé clair.

### Kimi — Responsable lisibilité cockpit / diagnostic humain

Mission :

- traduire la situation actuelle en diagnostic humain clair ;
- proposer les textes cockpit pour :
  - audio envoyé mais aucune réponse ;
  - WebSocket fermé après premier audio ;
  - modèle OpenAI indisponible ;
  - cache APK suspect ;
  - build APK possiblement obsolète ;
- éviter toute formulation qui accuse Ludovic ;
- dire ce que le cockpit doit afficher maintenant.

Livrable :

`docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_008_DIAGNOSTIC_HUMAIN.md`

### Codex — Responsable coordination / garde-fous

Mission :

- maintenir la séparation des responsabilités ;
- empêcher les corrections mélangées ;
- préparer la synthèse de validation Ludovic ;
- vérifier que les rapports utiles sont dans GitHub ;
- rappeler que l'objectif n'est pas validé tant que Ludovic n'entend pas Luna.

Livrable :

`docs/AGENTS_COLLABORATION/agents/CODEX_AVIS_008_COORDINATION.md`

## Questions à résoudre

1. Le modèle `gpt-realtime-mini` est-il réellement actif en production ?
2. Le serveur reçoit-il le premier audio après `voice_first_audio_chunk_sent` ?
3. OpenAI Realtime renvoie-t-il une erreur ou ferme-t-il la session ?
4. Le client reçoit-il une erreur serveur avant `voice_ws_closed` ?
5. La WebView charge-t-elle bien la dernière version `static/index.html` ?
6. Le cache WebView peut-il expliquer une partie des incohérences ?
7. Faut-il rebuilder l'APK ou seulement recharger la WebView ?
8. Le cockpit affiche-t-il le bon scénario ou encore un libellé trop vague "Session partielle" ?

## Décision attendue après avis

Une fois les avis rendus, Ludovic décidera :

- test modèle suivant ;
- correction serveur ;
- correction APK/cache ;
- rebuild APK ;
- correction cockpit ;
- ou pause diagnostic.

Rien ne doit être fait en production sans cette validation.

