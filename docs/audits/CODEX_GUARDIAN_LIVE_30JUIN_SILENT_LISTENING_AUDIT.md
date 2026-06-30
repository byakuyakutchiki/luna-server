# Codex Audit - Guardian Live 30 Juin

Branche auditee: `audit/guardian-live-30juin`
Revision observee: `a4d7827`
Date: 2026-06-30

Mode: audit lecture seule initial. Ce fichier publie l'avis Codex sur GitHub a la demande de l'utilisateur. Aucun correctif code n'est inclus dans ce commit.

## Avis Codex

La cause principale du bruit permanent n'est pas un unique bug TTS. Le probleme est architectural: Guardian ecoute et parle en meme temps, avec deux detecteurs vocaux paralleles, Web Speech et Android natif, et des mots-cles trop larges. Pour une fonction de securite personnelle, l'ecoute permanente doit etre silencieuse par defaut. Le son doit devenir une option explicite, pas un comportement d'urgence automatique.

Principe produit a appliquer: ecouter ne veut pas dire emettre du son. Une personne peut etre en danger et devoir rester discrete.

## Constats principaux

### 1. TTS Guardian bruyant par conception

Evidence:

- `static/guardian.html:976-979` indique que `force:true` parle meme si le setting vocal est desactive.
- `static/guardian.html:1671` force une annonce vocale au debut du countdown.
- `static/guardian.html:1679` force les chiffres vocaux du compte a rebours.
- `static/guardian.html:1703` force l'annonce d'annulation.
- `static/guardian.html:1710` force une annonce au declenchement SOS vocal.
- `static/guardian.html:1725` force une confirmation vocale apres alerte.

Recommandation:

- Supprimer le TTS force par defaut dans Guardian.
- Remplacer par UI visuelle, vibration discrete et notification systeme.
- Garder une option utilisateur explicite pour activer les annonces vocales.

### 2. Risque de larsen Web TTS vers Android SpeechRecognizer

Evidence:

- `static/guardian.html:982-999` met en pause uniquement `_vocalRec`, donc la reconnaissance Web Speech.
- `static/guardian.html:1133-1134` lance aussi `LunaBridge.startNativeVoiceGuardian()`.
- `android-app/java/fr/yawatch/luna/GuardianService.java:232-236` matche les mots-cles avec `contains()`.
- `android-app/java/fr/yawatch/luna/GuardianService.java:299-307` declenche aussi sur resultats partiels.

Risque:

Guardian peut parler, le micro Android peut entendre la voix de Guardian, puis redeclencher une urgence.

Recommandation:

- Ne pas parler pendant l'ecoute permanente.
- Si un son est absolument necessaire, ajouter un bridge Android `pauseNativeVoiceGuardian()` / `resumeNativeVoiceGuardian()` autour de tout playback audio.

### 3. Mots-cles Web et Android trop larges

Evidence Web:

- `static/guardian.html:1514-1530` contient notamment `aide moi`, `urgence`, `help`, `secours`, `sos`.

Evidence Android:

- `android-app/java/fr/yawatch/luna/GuardianService.java:52-61` contient aussi `urgence`, `help`, `secours`, `a laide`.

Contraste serveur:

- `core/safety/voice_emergency.py:39-43` explique que `aide-moi`, `aidez-moi` et `a l'aide` ont ete retires des declencheurs immediats car trop ambigus.

Recommandation:

- Aligner Web et Android sur la politique serveur.
- Immediat uniquement pour formulations fortes et explicites.
- Formulations ambigues: confirmation silencieuse avant alerte.

### 4. Widget always-on present, mais pas encore silencieux autour

Evidence:

- Widget: `static/guardian.html:250-316`.
- Affichage session active: `static/guardian.html:1124` et `static/guardian.html:2025`.
- Diagnostic TTS au demarrage: `static/guardian.html:1126`.
- Message vocal au demarrage: `static/guardian.html:1147`.

Recommandation:

- Garder le widget permanent.
- Supprimer `_ttsTest` automatique.
- Supprimer le message vocal de demarrage.
- Le widget doit signaler l'etat par couleur, texte, icone et eventuellement vibration, sans son.

### 5. Plusieurs chemins non urgents emettent du son

Evidence:

- `static/guardian.html:1147`: demarrage Guardian parle.
- `static/guardian.html:1390`: retour zone sure parle.
- `static/guardian.html:1430`: alerte websocket parle.
- `static/guardian.html:1446`: chute parlee.
- `static/guardian.html:1745`: verification parlee.
- `static/guardian.html:1759`: reprise surveillance parlee.
- `static/guardian.html:1907`: chute detectee parlee.

Recommandation:

- Tous ces chemins doivent etre silencieux par defaut.
- Les annonces vocales doivent dependre d'un reglage explicite.

### 6. All-clear existe cote backend, mais doit etre expose clairement cote produit

Evidence:

- `luna_web.py:15754-15776`: route `/api/guardian/verify-response/{session_id}`.
- `core/guardian/engine.py:357-414`: `register_verification_response(ok=True)` remet l'alerte a LOW, active une grace period et peut envoyer un SMS d'annulation.
- `core/guardian/alerts.py:96-103`: construction du SMS d'annulation.
- `luna_web.py:15779-15840`: route `/api/guardian/incident/{session_id}/resolve`.

Recommandation:

- Apres une alerte envoyee, afficher un bouton clair: `Tout va bien - prevenir mes proches`.
- Appeler la route de resolution d'incident pour fermer l'incident et envoyer l'all-clear lorsque necessaire.

### 7. Zone safe existe, mais ne doit pas bloquer les vrais SOS

Evidence:

- UI zone sure: `static/guardian.html:671-681` et `static/guardian.html:1107-1108`.
- Moteur geofence: `core/guardian/engine.py:677-707`.
- Statut expose: `luna_web.py:15259-15260`.
- SOS et chute escaladent directement: `core/guardian/engine.py:263-291` et `core/guardian/engine.py:295-353`.

Recommandation:

- Ne pas bloquer un SOS explicite sous pretexte que la personne est en zone safe.
- Utiliser la zone safe pour reduire les alertes ambigues, contextualiser les decisions et faciliter l'all-clear.

### 8. Iris Realtime semble correctement migre en GA PCM 24 kHz

Evidence:

- `integrations/openai/web_voice_bridge.py:933-964`: session GA avec `audio.input` et `audio.output` en `audio/pcm` a `rate: 24000`.
- `static/simli.html:5891-5894`: AudioContext lecture a 24000 Hz.
- `static/simli.html:5941-5944`: playback audio Iris.

Risque restant:

- En contexte Guardian/securite, Iris et Simli peuvent quand meme produire du son ou des sons decoratifs.
- Exemples sons decoratifs: `static/simli.html:2822-2875`.

Recommandation:

- En contexte Guardian, desactiver sons decoratifs et playback non sollicite.
- L'audio Iris doit etre volontaire, pas associe a l'ecoute de securite permanente.

## Priorite de correction proposee

1. Rendre Guardian muet par defaut: aucun `guardianSpeak(...,{force:true})` pendant l'ecoute permanente.
2. Aligner les mots-cles Web/Android sur `core/safety/voice_emergency.py`.
3. Ajouter un etat global `GUARDIAN_SILENT_MODE = true` ou equivalent produit.
4. Supprimer `_ttsTest` automatique au demarrage.
5. Exposer clairement le bouton all-clear apres incident.
6. Utiliser la zone safe comme contexte de decision, pas comme blocage absolu.
7. Tester sur APK reel avec micro ouvert, ecran verrouille, session active et mots ambigus.

## Decision produit recommandee

La bonne cible n'est pas `TTS plus robuste`.

La bonne cible est `Guardian discret`: ecoute permanente visible, rassurante, mais silencieuse. Les proches doivent etre alertes quand c'est necessaire; la personne protegee ne doit pas etre mise en danger par des annonces sonores automatiques.
