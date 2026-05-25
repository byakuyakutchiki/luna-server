# Objectif 008 — DeepSeek temps réel dans l'expérience APK

**Date** : 2026-05-25
**Décideur** : Ludovic
**IA désignée pour l'intérieur APK** : DeepSeek
**Statut** : consigne d'architecture à appliquer à partir de l'objectif 008
**Priorité** : critique

## Décision Ludovic

Pour les tests APK, boutons et onglets à venir, l'équipe ne doit plus seulement
observer de loin avec des scripts incomplets.

Ludovic désigne DeepSeek comme IA envoyée "dans le téléphone", c'est-à-dire dans
l'expérience réelle APK, pour diagnostiquer ce qui se passe au moment du problème.

But : quand un bouton, un onglet ou la voix échoue, DeepSeek doit recevoir les
signaux utiles immédiatement et produire un diagnostic exploitable.

## Formulation opérationnelle

DeepSeek doit être dans le téléphone **fonctionnellement** :

- il voit les événements de l'APK en temps réel ;
- il reçoit un contexte compact quand un incident apparaît ;
- il dit ce qui se passe dans l'expérience réelle ;
- il renvoie une conclusion au cerveau Luna ;
- il ne tourne pas en permanence inutilement.

## Architecture imposée

```
APK téléphone Ludovic
  → flux diagnostic temps réel
Serveur Luna sécurisé
  → appel DeepSeek API côté serveur
DeepSeek
  → diagnostic structuré
Serveur Luna
  → cockpit fondateur / journal / éventuellement retour APK
```

## Règle de sécurité

La clé DeepSeek ne doit pas être embarquée dans l'APK.

Raison : une clé dans une APK peut être extraite. Elle exposerait les crédits, les
appels API et le contrôle du diagnostic.

Donc DeepSeek est "dans le téléphone" par le flux temps réel, mais la clé reste dans
le serveur Luna.

## Modes de fonctionnement

### Mode veille

Toujours actif, très léger, sans appel IA coûteux.

Signaux :

- heartbeat APK ;
- version APK ;
- URL Cloud Run ;
- build frontend ;
- onglet actif ;
- événements bouton ;
- erreurs JS critiques ;
- WebSocket ouvert/fermé ;
- cache/version suspect ;
- statut micro ;
- dernier événement vocal.

### Mode incident

Déclenche DeepSeek automatiquement.

Déclencheurs :

- bouton pressé mais aucune action visible ;
- WebSocket fermé trop tôt ;
- premier audio envoyé mais aucune réponse ;
- aucun événement après clic ;
- erreur JS critique ;
- mismatch version APK / frontend ;
- cache WebView suspect ;
- heartbeat perdu ou trop ancien ;
- onglet bloqué ;
- crash WebView ;
- action utilisateur qui échoue deux fois de suite.

Fenêtre envoyée à DeepSeek :

- 30 à 60 secondes d'événements maximum ;
- résumé compact ;
- dernier écran/onglet ;
- version APK/frontend ;
- derniers codes d'erreur ;
- aucun audio brut ;
- aucun transcript privé ;
- aucun token ;
- aucun secret.

## Sortie attendue de DeepSeek

DeepSeek doit répondre en JSON ou structure équivalente :

```json
{
  "diagnostic": "ce qui se passe",
  "preuve": ["événements observés"],
  "cause_probable": "cause la plus probable",
  "zone": "apk | webview | cache | serveur | openai | ui | inconnue",
  "action_recommandee": "action minimale",
  "risque": "faible | moyen | élevé",
  "validation_ludovic_requise": true
}
```

## Ce que DeepSeek doit couvrir dès l'objectif 008

1. Voix APK :
   - premier audio envoyé ;
   - WebSocket fermé ;
   - aucune réponse audio reçue.
2. Cache/WebView :
   - vérifier si l'APK charge bien le bon `index.html` ;
   - détecter frontend obsolète ;
   - proposer clear cache / reload si nécessaire.
3. Boutons et onglets futurs :
   - chaque bouton testé doit pouvoir déclencher un diagnostic DeepSeek si l'action échoue.
4. UI mobile :
   - détecter et rapporter les régressions visibles, comme le bouton `Déconnexion` coupé.

## Rôles

### DeepSeek

IA désignée à l'intérieur de l'expérience APK.

Il doit concevoir :

- le format d'événement minimal ;
- les seuils de déclenchement incident ;
- la stratégie anti-gaspillage tokens ;
- les diagnostics type ;
- les preuves à remonter au cockpit ;
- les risques de cache/rebuild APK.

Livrable :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_008_TEMPS_REEL_APK.md`

### Claude

Intégrateur final côté serveur.

Il doit concevoir :

- l'endpoint serveur qui déclenche DeepSeek ;
- la protection de la clé DeepSeek côté serveur ;
- la limitation de fréquence ;
- le stockage journalisé des diagnostics ;
- l'affichage cockpit.

Il ne doit pas déployer sans validation Ludovic.

### Kimi

Responsable formulation fondateur.

Il doit proposer les textes cockpit pour :

- DeepSeek observe ;
- DeepSeek suppose ;
- DeepSeek recommande ;
- DeepSeek ne peut pas ;
- validation Ludovic requise.

### Codex

Coordination et garde-fous.

Il doit empêcher :

- clé DeepSeek dans l'APK ;
- appels IA à chaque événement normal ;
- collecte audio/transcript privé ;
- correction automatique non validée ;
- mélange entre diagnostic APK, serveur voix et UI mobile.

## Critères de réussite

- [ ] DeepSeek est déclenché automatiquement sur incident réel.
- [ ] Aucun appel DeepSeek n'est fait en navigation normale sans anomalie.
- [ ] Le diagnostic est visible dans le cockpit fondateur.
- [ ] Le journal garde la trace de l'intervention DeepSeek.
- [ ] Ludovic peut valider ou refuser l'action proposée.
- [ ] Aucun secret n'est présent dans l'APK.
- [ ] Aucun audio brut ou transcript privé n'est envoyé.
- [ ] Le coût token est borné par seuils et fenêtres compactes.

## Message court

DeepSeek est désigné comme IA embarquée dans l'expérience téléphone.

Il ne doit pas être un simple rapport externe après coup. Il doit recevoir les
signaux en temps réel quand l'APK vit une anomalie et produire un diagnostic.

La clé DeepSeek reste côté serveur Luna. Le téléphone envoie les faits, le serveur
appelle DeepSeek, le cockpit affiche le diagnostic, Ludovic valide l'action.
