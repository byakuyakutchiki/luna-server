# Avis DeepSeek — Audit push `4fc9ed7` (Guardian Behavior Engine + Vision)

**Date** : 2026-06-17  
**Agent** : DeepSeek  
**Scope** : commit `4fc9ed7` sur `main` — fichiers Guardian  
**Fichiers audités** :
- `static/guardian.html` (BehaviorEngine JS)
- `core/perception/detector.py` (`analyze_sequence_b64`)
- `luna_web.py` (`/api/guardian/anomaly`, `_guardian_scene_analyzers`, `/api/guardian/checkin-miss`)
- `core/guardian/engine.py` (`speed_anomaly` désactivé)
- `tests/test_guardian_p0.py`

---

## 1. Résumé exécutif

Le push est **techniquement cohérent** avec la Policy V2. Les 6 scénarios P0 testés passent. La détection côté client (motion spike → immobilité) est simple mais fonctionnelle ; l'analyse serveur via GPT-4o-mini est bien isolée dans un executor. **Aucun risque critique de sécurité** n'a été identifié.

**Verdict** : ✅ Faisable en beta, **sous réserve d'un test terrain APK réel** et de 3 ajustements de robustesse ci-dessous.

---

## 2. Analyse fichier par fichier

### 2.1 `static/guardian.html` — BehaviorEngine

**Logique** :
- Capture 320×240 toutes les 2 s, qualité JPEG 0.65.
- Détection de "chute candidate" = pic de motion (`> 0.10`) suivi d'immobilité (`< 0.02`) sur les 2 dernières frames.
- Score danger client : 0 → 10 en ~25 s d'immobilité après chute candidate.
- Envoi serveur si `score >= 7`, cooldown 60 s.
- Baseline vers `/api/guardian/frame` toutes les 5 min.
- Check-in vocal toutes les **10 min** (Policy V2), timeout de réponse 60 s.

**Points forts** :
- `getUserMedia` appelé directement (sans `.then()` avant), respect des contraintes iOS/Android.
- Gestion des erreurs de permission propre avec messages adaptés.
- Reset complet du buffer au démarrage/arrêt.

**Risques / remarques** :
1. **Algorithme de motion très basique** : différence pixel rouge 1/16, sensible aux changements de luminosité, ombres, reflets. Peut générer des faux positifs dans une pièce mal éclairée ou avec des ombres mouvantes.
2. **Commentaire obsolète** ligne ~1406 : "Toutes les 60s" alors que le code est réglé à 10 min (`600000`).
3. **`_processCamTick` redimensionne le canvas à chaque tick** (`canvas.width=W; canvas.height=H;`). Ce n'est pas bloquant car on redessine juste après, mais c'est inutile et peut causer des micro-clignotements selon le navigateur.
4. **Payload anomaly** : envoie jusqu'à 5 frames JPEG base64 (~75–250 Ko/requête). Avec cooldown 60 s, c'est raisonnable, mais aucune compression dynamique ni vérification de taille côté client.

### 2.2 `core/perception/detector.py` — `analyze_sequence_b64`

**Logique** :
- Construit un prompt pour GPT-4o-mini avec le contexte motion + jusqu'à 5 images (`detail=low`, ~85 tokens/image).
- Retourne `{danger_score, has_concern, description, posture}`.

**Points forts** :
- Aucune image stockée ; seules les métadonnées sont conservées.
- Exécution asynchrone via executor dans `luna_web.py`.

**Risques / remarques** :
1. **Pas de validation stricte du JSON retourné** : si `danger_score` dépasse 10 ou est négatif, le cast `int()` l'acceptera sans clamping.
2. **Le prompt interne mentionne "10=urgence"** alors que les règles métier cherchent à éviter le mot "urgence" côté utilisateur. Ce n'est pas visible utilisateur, mais c'est une incohérence terminologique.
3. **Pas de structured output / JSON mode** : dépend de la bonne volonté du modèle. `gpt-4o-mini` est généralement fiable, mais un mode JSON renforcerait la robustesse.

### 2.3 `luna_web.py` — Endpoints Guardian

#### `/api/guardian/anomaly/{session_id}`
- Vérifie engine + session + perception detector initialisé.
- Appelle `_perception_detector.analyze_sequence_b64` dans executor.
- Loggue un événement `perception_concern` si `has_concern` **ou** `behavior_score >= 7`.
- Broadcast WebSocket.

**Risques / remarques** :
1. **Pas de rate limiting** sur cet endpoint (contrairement à `/api/guardian/frame` qui utilise `_vision_last_call`). Un client malveillant ou un bug client pourrait spammer l'analyse vision. Le cooldown client de 60 s limite le risque, mais ne le supprime pas côté serveur.
2. **`_guardian_scene_analyzers` jamais nettoyé** : dict global en mémoire. Si une session est arrêtée ou inactive, l'analyseur reste en mémoire. Risque de fuite mémoire à long terme sur un serveur de production avec beaucoup de sessions.
3. **Analyseurs en mémoire uniquement** : l'historique temporel est perdu au redémarrage du serveur. Acceptable pour une feature beta, mais à documenter.

#### `/api/guardian/checkin-miss/{session_id}`
- Capture une frame, l'analyse, loggue `alert_triggered`, alerte les contacts de confiance (SMS et/ou DM Luna).
- `has_concern` initialisé à `True` par défaut : "pas de réponse = préoccupant par défaut". C'est une décision produit défendable.
- Gestion des canaux d'alerte via Redis settings (`sms`, `luna`, `both`).

**Risques / remarques** :
1. Si `_perception_detector` n'est pas initialisé, l'alerte est quand même envoyée avec la description par défaut "Pas de réponse au contrôle Guardian". C'est le comportement attendu (ne pas bloquer une alerte réelle à cause d'une indisponibilité OpenAI).
2. `session.profile_type.value if session else "senior"` : `session` est déjà vérifié plus haut, le `else` est redondant mais inoffensif.

### 2.4 `core/guardian/engine.py` — `speed_anomaly` désactivé

**Constats** :
- Le signal est correctement commenté avec la raison (trop de faux positifs, Policy V2).
- `_risk_description` garde une branche `if "speed_anomaly" in signals` : code mort, mais pas dangereux.
- **Incohérence** : `get_profile_templates()` pour le profil `senior` inclut toujours `"speed_anomaly"` dans la liste `signals`. Si cette liste est exposée dans l'UI, l'utilisateur verra un signal annoncé comme actif qui ne se déclenche jamais.

**Recommandation** : retirer `"speed_anomaly"` de la liste des signaux du template senior, ou ajouter un champ `enabled: false` si l'UI supporte l'affichage grisé.

---

## 3. Tests

- `tests/test_guardian_p0.py` : **30/30 PASS** ✅
- Scénarios couverts : mode nuit, TV 45 min, ignore 3 min, ignore 15 min, réponse OK, anti-spam 3 alertes/24h.

**Manque à tester** :
- BehaviorEngine JS (pas de tests JS identifiés).
- Endpoint `/api/guardian/anomaly` (sans appel OpenAI réel).
- Endpoint `/api/guardian/checkin-miss`.
- Fuite mémoire des `_guardian_scene_analyzers`.
- Scénarios de faux positifs motion (lumière, ombre, animal).

---

## 4. Risques de régression

| Cible | Risque | Niveau |
|---|---|---|
| APK / WebView | Consommation batterie, chauffe, freeze si caméra active longtemps + capture toutes les 2 s | Moyen |
| APK / WebView | Permissions caméra sur iOS/Android WebView à valider sur appareil réel | Moyen |
| Coût OpenAI | Pas de rate limit serveur sur anomaly ; risque de spam si bug client | Moyen |
| Mémoire serveur | `_guardian_scene_analyzers` jamais nettoyé | Faible-Moyen |
| UX | Signal `speed_anomaly` annoncé mais désactivé | Faible |
| Données | Frames transient par OpenAI (pas stockées localement) — conforme à la doc mais à rappeler | Faible |

---

## 5. Recommandations priorisées

### À faire avant déploiement production (P1)
1. **Test terrain APK réel** : vérifier que la caméra ne fige pas, que la batterie tient, que les alertes se déclenchent correctement.

### À faire rapidement (P2)
2. **Ajouter un rate limit serveur** sur `/api/guardian/anomaly` (même mécanisme que `_vision_last_call` ou par session_id).
3. **Nettoyer `_guardian_scene_analyzers`** : supprimer l'entrée quand la session est inactive/arrêtée, ou ajouter un TTL.

### À faire dès que possible (P3)
4. Corriger l'incohérence `speed_anomaly` dans `get_profile_templates`.
5. Mettre à jour le commentaire "60s" obsolète dans `guardian.html`.
6. Ajouter des tests mockés pour `/api/guardian/anomaly` et `/api/guardian/checkin-miss`.
7. Envisager `response_format={"type":"json_object"}` pour `analyze_sequence_b64`.

---

## 6. Décision proposée

**Approuver le merge sur `main` tel quel**, car :
- Les tests P0 passent.
- La Policy V2 est respectée.
- Aucune régression identifiée sur les fonctionnalités existantes.

**Condition** : ne pas déployer sur Cloud Run / ne pas rebuilder l'APK sans un test terrain réel et la validation de Ludovic, conformément aux règles de coordination.

---

## 7. Confrontation avec l’avis ChatGPT et écarts à la POLICY V2

L’avis ChatGPT souligne des risques réels (confusion repos/malaise, besoin de logique temporelle, tracking, buffer, fallback, journal). Plusieurs de ces points sont **déjà partiellement couverts** par le code ou la POLICY V2, mais des écarts importants subsistent.

### 7.1 Points déjà couverts

| Besoin ChatGPT | État actuel |
|---|---|
| Logique temporelle | ✅ `SceneAnalyzer` avec `_floor_start`, `_last_person_seen`, durées seuils. |
| Différence lit / sol / canapé | ✅ `PersonPosture` distingue `LYING_BED`, `LYING_FLOOR`, `SITTING`. Le prompt Vision demande la distinction. |
| Timeout vocal avant alerte | ⚠️ Partiel : un mécanisme existe (`_doCheckIn` modal + 60 s), mais il est **trop court** et **indépendant** de l’escalade Policy V2. |
| Mode nuit / sieste | ✅ Mode nuit suspend l’immobilité GPS entre 23h–7h en safe zone. Tolérances par profil définies. |
| Fallback si Vision échoue | ⚠️ Partiel : `checkin_miss` envoie l’alerte sans Vision, mais `guardian_anomaly` retourne danger_score=0 sans logique prudente. |
| Journal d’événements | ✅ `engine._log_event` existe. Pas d’image/vidéo stockée (conforme RGPD). |

### 7.2 Écarts significatifs par rapport à la POLICY V2

#### A. Le check-in automatique caméra n’honore pas les délais de la Policy V2

La POLICY V2 prévoit une escalade progressive :
- Niveau 2 → attente réponse **10 min**
- Niveau 3 → attente réponse **5 min**
- Niveau 4 → SMS

Or `guardian.html` déclenche `_doCheckIn()` toutes les **10 min** avec un timeout de seulement **60 s**. Si l’utilisateur ne répond pas dans la minute, l’alerte est envoyée. C’est beaucoup trop agressif par rapport à la policy et risque de générer des fausses alertes lors de :
- sieste,
- douche,
- téléphone en silencieux / dans une autre pièce,
- conversation.

**Recommandation** : aligner le check-in automatique sur l’escalade Policy V2 (10 min + 5 min), ou le désactiver temporairement tant que l’escalade par signaux n’est pas pleinement opérationnelle.

#### B. Aucune atténuation caméra de l’immobilité GPS

La POLICY V2 Scénario 2 (TV) stipule :
> Si la caméra confirme une présence vivante dans une posture normale (assis, debout), l’immobility GPS est reclassée DOUTE et non VÉRIFICATION.

Le moteur `engine.py::_compute_risk` ne tient **pas compte** de l’état caméra pour atténuer `immobility`. Seul le mode nuit suspend ce signal. Résultat : une personne immobile mais visible à la caméra peut quand même déclencher un Niveau 2/MEDIUM.

**Recommandation** : intégrer `_guardian_scene_analyzers[session_id]` dans `_compute_risk` pour atténuer l’immobilité GPS quand la caméra voit une personne vivante en posture normale.

#### C. `speed_anomaly` toujours listé comme actif pour le profil senior

ChatGPT ne l’a pas cité, mais c’est un écart documenté en section 2.4.

#### D. Pas de journal enrichi avec preuves visuelles

La POLICY V2 impose une journalisation horodatée des alertes, mais ne mentionne pas le stockage d’images. L’avis ChatGPT demande un journal avec image/vidéo. Le code actuel ne stocke **aucune image** (conforme RGPD). C’est un choix légitime, mais il faut s’assurer que les logs textuels sont suffisants pour auditer une alerte.

### 7.3 Pistes techniques de ChatGPT à évaluer avec prudence

| Piste ChatGPT | Faisabilité | Commentaire |
|---|---|---|
| YOLO Pose + tracking | Moyenne | Nécessite un modèle local ou service tiers, poids de modèle, latence, coût. La POLICY V2 n’impose pas YOLO. OpenAI Vision actuel suffit pour une v1. |
| Buffer 10–20 s avant événement | Élevée | Déjà partiellement en place côté client (`_frameBuffer` 30 s). Il faudrait envoyer ce buffer systématiquement, pas seulement en anomalie. |
| Reconnaissance lit / canapé / sol | Moyenne | Dépend de la qualité Vision. Le prompt demande déjà `lying_bed` vs `lying_floor`. Le canapé n’est pas un cas distinct dans le code actuel. |
| Alerte progressive | Élevée | Déjà dans la POLICY V2, mais **pas pleinement implémentée** côté check-in caméra. |

### 7.4 Synthèse comparative

- **ChatGPT** a raison sur le diagnostic : Guardian n’est pas encore fiable production à cause du risque de confusion repos/malaise.
- **Le code actuel** est plus avancé que ce que ChatGPT semble croire sur certains points (mode nuit, différenciation lit/sol, logique temporelle basique).
- **L’écart le plus critique** reste le **check-in automatique caméra avec timeout 60 s**, qui court-circuite la Policy V2 et risque de produire des faux positifs fréquents.
- **La POLICY V2 reste la référence** : tout écart entre ce document et le code est un bug comportemental à corriger.

---

## 8. Position finale consolidée

**Pour que Guardian passe en production fiable, il faut impérativement :**

1. **Corriger le check-in automatique** : passer le timeout de 60 s à une escalade 10 min + 5 min conforme à la Policy V2, ou désactiver le check-in automatique tant que l’escalade par signaux n’est pas fiable.
2. **Atténuer l’immobilité GPS par la caméra** : si la caméra voit une personne vivante en posture normale, ne pas monter au Niveau 2.
3. **Ajouter un rate limit serveur** sur `/api/guardian/anomaly`.
4. **Nettoyer les `_guardian_scene_analyzers`** inactifs.
5. **Corriger l’incohérence `speed_anomaly`** dans le template senior.
6. **Tester terrain APK réel** avant tout rebuild/déploiement.

Sans ces corrections, le risque de faux positifs répétés est élevé — ce qui contredit directement le principe cardinal de la Policy V2 : *"L'ennemi numéro un de Guardian n'est pas le faux négatif. C'est le faux positif répété."*

---

*Avis rédigé par DeepSeek. Ne pas modifier ce fichier sans en avertir l’auteur.*
