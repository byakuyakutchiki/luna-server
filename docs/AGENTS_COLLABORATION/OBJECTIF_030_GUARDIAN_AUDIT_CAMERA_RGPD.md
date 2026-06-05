# Objectif 030 — Guardian Audit caméra / surveillance / RGPD

Date : 2026-06-05
Statut : ouvert
Priorité : P1

## Contexte

Pendant que Claude termine Iris Audio / Command Screen, Kimi doit auditer une autre partie de l'application : Guardian.

Guardian existe déjà :

- page `static/guardian.html` ;
- routes `/api/guardian/*` ;
- moteur `core/guardian/engine.py` ;
- alertes `core/guardian/alerts.py` ;
- perception caméra `core/perception/*`.

Mais Ludovic constate :

```text
Guardian est censé surveiller et reconnaître ce qui se passe.
La caméra devrait pouvoir s'allumer avec consentement.
Aujourd'hui, on constate que la caméra ne s'allume pas ou n'est pas clairement reliée à Guardian.
```

## Objectif final

Guardian doit devenir un module de protection fiable, compréhensible et conforme :

```text
Je démarre une session Guardian.
Je sais ce que Guardian surveille.
Je sais si la caméra est active ou non.
Je sais si la géolocalisation est active ou non.
Je comprends les risques détectés.
Je peux arrêter la session.
Je peux déclencher SOS uniquement volontairement.
Mes données et images sont protégées.
```

## Targets Guardian

### Target 1 — Démarrer / arrêter Guardian

Le bouton de démarrage doit :

- vérifier les contacts d'urgence ;
- demander les permissions nécessaires ;
- créer une session ;
- afficher clairement l'état actif.

Le bouton d'arrêt doit :

- stopper la session ;
- stopper les boucles GPS/caméra ;
- couper les timers ;
- confirmer visuellement que Guardian est arrêté.

### Target 2 — Caméra Guardian

Guardian doit clarifier son rapport à la caméra :

- caméra inactive par défaut ;
- consentement explicite avant activation ;
- état visible : `Caméra inactive`, `Demande permission`, `Caméra active`, `Caméra refusée`, `Caméra indisponible` ;
- aucune image stockée ;
- envoi uniquement de frames temporaires si perception active ;
- arrêt caméra garanti à la fin de session.

### Target 3 — Perception / reconnaissance

Si caméra active :

- capturer une frame courte ;
- envoyer à `/api/perception/frame` ou endpoint équivalent ;
- recevoir une description factuelle ;
- afficher ce que Guardian comprend : personne visible, posture, objets, scène peu lisible ;
- ne jamais présenter cela comme un diagnostic médical ou une certitude.

### Target 4 — Géolocalisation

Guardian doit :

- demander permission position ;
- envoyer position à `/api/guardian/location/{session_id}` ;
- afficher risque, safe zone, dernière position, précision ;
- ne pas géolocaliser sans consentement.

### Target 5 — SOS / alertes

SOS est une action sensible.

Audit uniquement, aucun test réel d'envoi.

À vérifier :

- bouton SOS visible seulement en session active ;
- confirmation ou appui volontaire clair ;
- contacts d'urgence obligatoires ;
- pas d'alerte silencieuse ;
- anti-spam ;
- logs lisibles ;
- pas d'appel automatique aux secours sans cadre légal validé.

### Target 6 — RGPD / devoirs / précautions

Guardian doit avoir un cahier de précautions :

- consentement explicite caméra / GPS ;
- finalité claire : sécurité et assistance ;
- minimisation : pas de stockage image ;
- arrêt facile ;
- droit à l'oubli / suppression données ;
- traçabilité des alertes ;
- transparence : ce qui est capturé, quand, pourquoi ;
- interdiction d'utiliser Guardian pour espionner quelqu'un ;
- pas de diagnostic médical ;
- pas de décision automatique dangereuse sans confirmation humaine.

## Tests non destructifs demandés à Kimi

### TC-030-01 — Inventaire boutons

Lister les boutons réels de `guardian.html` :

```text
Démarrer
Arrêter
SOS
Partager
Événements
Configuration
Zone sûre
Voix / vérification
```

Pour chacun :

```text
bouton -> handler JS -> endpoint -> effet attendu -> risque -> preuve
```

### TC-030-02 — Caméra

Auditer le code pour répondre :

```text
Guardian demande-t-il vraiment getUserMedia({video:true}) ?
Si oui, où ?
Si non, pourquoi la caméra ne peut pas s'allumer ?
La perception caméra est-elle seulement dans Iris/Simli ou aussi dans Guardian ?
```

### TC-030-03 — GPS

Vérifier :

```text
navigator.geolocation.watchPosition/start ?
POST /api/guardian/location/{session_id} ?
fréquence d'envoi ?
arrêt watchPosition à stop ?
```

### TC-030-04 — RGPD

Vérifier dans l'UI :

```text
Consentement clair avant GPS/caméra ?
Message "aucune image stockée" ?
Bouton arrêter visible ?
Explication finalité Guardian ?
```

### TC-030-05 — SOS sans déclencher

Audit code uniquement :

```text
Le bouton SOS peut-il envoyer SMS réel ?
Y a-t-il confirmation ?
Y a-t-il cooldown ?
Quels contacts sont utilisés ?
```

Ne pas cliquer / ne pas envoyer de SOS réel.

## Livrable attendu Kimi

Créer :

```text
docs/AGENTS_COLLABORATION/agents/KIMI_AUDIT_GUARDIAN_CAMERA_RGPD_030.md
```

Format obligatoire :

```text
Agent : Kimi
Objectif : 030
Type : audit Guardian caméra / RGPD / boutons
Résumé : ...
Fichiers inspectés : ...
Boutons réels : ...
Caméra : ...
GPS : ...
SOS : ...
RGPD : ...
P0 : ...
P1 : ...
Décision Ludovic requise : oui/non
Actions proposées : ...
```

## Interdits

- Ne pas déclencher SOS réel.
- Ne pas envoyer SMS.
- Ne pas appeler.
- Ne pas modifier secrets.
- Ne pas déployer.
- Ne pas activer une boucle caméra longue.
- Ne pas stocker d'image.

## Validation

Guardian ne sera pas validé tant que :

```text
start_ok + stop_ok + camera_state_visible + gps_state_visible
+ consentement clair + no_image_storage + SOS_safe
```

ne sont pas prouvés.
