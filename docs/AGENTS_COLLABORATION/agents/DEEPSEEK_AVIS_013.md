# Avis DeepSeek — Audit Guardian Mode commit `6d89113`

**Date** : 2026-06-17  
**Agent** : DeepSeek  
**Scope** : commit `6d89113` sur `main` — Guardian Mode (caméra + GPS + perception)  
**Fichiers audités** :
- `static/guardian.html` (BehaviorEngine JS, check-in vocal)
- `luna_web.py` (endpoints `/api/guardian/anomaly`, `/checkin-miss`, `/frame`, `/stop`)
- `core/guardian/engine.py` (`_compute_risk`, `_handle_risk`, sessions)
- `core/perception/detector.py` (`analyze_frame_b64`, `analyze_sequence_b64`)
- `core/perception/analyzer.py` (`SceneAnalyzer`, `has_concern`)
- Référence : `docs/guardian/GUARDIAN_BEHAVIOR_POLICY_V2.md`

---

## 1. Résumé exécutif

Le commit `6d89113` améliore la robustesse technique (rate limit, nettoyage mémoire, retrait `speed_anomaly`, timeout check-in allongé), mais il ne corrige **pas** les écarts comportementaux fondamentaux entre Guardian Mode et la Policy V2.

**Verdict** : ❌ **Non conforme à la logique produit attendue pour une version fiable.**

Guardian Mode reste utilisable en **beta contrôlée**, mais il court-circuite encore la Policy V2 sur deux points critiques :
1. **Check-in automatique toutes les 10 min** qui dérange l'utilisateur indépendamment de tout signal de danger.
2. **Aucune atténuation de l'immobilité GPS par la caméra**, ce qui génère des faux positifs TV / canapé / lit de jour.

---

## 2. Évaluation des 6 règles produit

### 2.1 Ne pas déranger une personne qui dort ou se repose

| Exigence | État | Preuve code | Commentaire |
|---|---|---|---|
| Mode nuit suspend l'immobilité GPS (23h-7h, safe zone) | ✅ | `engine.py:461-468` et `:477` | Correct. Dormir dans son lit = Niveau 0. |
| Atténuation caméra pour repos de jour (canapé/lit) | ❌ | `engine.py::_compute_risk` ignore totalement `_guardian_scene_analyzers` | **Écart Policy V2 Scénario 2.** Une personne assise sur son canapé pendant 1h30 verra son immobilité GPS monter en Niveau 2. |
| Check-in automatique ne réveille pas | ⚠️ | `guardian.html:1412` déclenche `_doCheckIn()` toutes les 10 min | Si la caméra est active la nuit (ou si mode nuit mal configuré), l'utilisateur est réveillé par un contrôle périodique. |

**Conclusion partielle** : le sommeil nocturne est protégé, mais les repos de jour ne le sont pas. Le check-in périodique est intrusif.

---

### 2.2 Détecter les situations réellement suspectes

| Exigence | État | Preuve code | Commentaire |
|---|---|---|---|
| Chute / immobilité après chute | ⚠️ | `guardian.html:1225-1244` | Algorithme de motion basé sur la différence pixel 1/16. Très sensible aux ombres, lumière, reflets. Faux positifs probables. |
| Personne au sol > 5 min | ✅ | `analyzer.py:146-159` | `LYING_FLOOR` pendant 5 min = `concern`. Bon. |
| Sortie de zone sûre | ✅ | `engine.py:481-483` | Signal `geofence_exit` bien géré. |
| Vitesse anormale (proxy chute) | ✅ | `engine.py:489-492` (désactivé) | Conforme à la Policy V2. |
| Confirmation par Vision avant escalation | ⚠️ | `luna_web.py:15256-15257` | `has_concern = result.get("has_concern") or danger_score >= 5`. Un `danger_score` de 5 (inhabituel) suffit à déclencher un log + broadcast. Pas de seuil strict. |

**Conclusion partielle** : les signaux graves sont détectés, mais le déclencheur côté client est fragile (motion basique) et le seuil côté serveur est permissif.

---

### 2.3 Observer avant d'alerter

| Exigence | État | Preuve code | Commentaire |
|---|---|---|---|
| Buffer temporel avant envoi anomalie | ✅ | `guardian.html:1200-1210` | 15 frames × 2 s = ~30 s. Correct pour une chute. |
| Historique temporel côté serveur | ✅ | `analyzer.py:95` | `HISTORY_SIZE = 60`. |
| Observation avant check-in automatique | ❌ | `guardian.html:1419-1432` | Le check-in est déclenché par un timer fixe de 10 min, sans analyse préalable de la scène. |
| Reclassification DOUTE si caméra rassurante | ❌ | `engine.py` | Non implémenté. |

**Conclusion partielle** : l'observation avant alerte de chute fonctionne, mais le check-in automatique est aveugle.

---

### 2.4 Demander vocalement si tout va bien seulement en cas de danger probable

| Exigence | État | Preuve code | Commentaire |
|---|---|---|---|
| Vérification déclenchée par signal de risque | ⚠️ | `engine.py:538` | Côté GPS, la vérification est bien déclenchée par `risk.level == MEDIUM`. |
| Vérification déclenchée par anomalie caméra | ✅ | `guardian.html:1297-1298` | Si `danger_score >= 7`, `_doCheckIn()` est appelé. |
| Vérification périodique systématique | ❌ | `guardian.html:1412` | `_doCheckIn()` est aussi appelé toutes les 10 min, quelle que soit la situation. **Contredit directement la règle produit.** |

**Conclusion partielle** : cette règle est **partiellement respectée** pour les signaux GPS et les anomalies caméra graves, mais **violée** par le check-in périodique.

---

### 2.5 Alerter les contacts uniquement si la personne ne répond pas

| Exigence | État | Preuve code | Commentaire |
|---|---|---|---|
| Escalade GPS 10 min sans réponse → Niveau 4 | ✅ | `engine.py:606-610` | 10 min d'attente avant escalation. |
| Check-in caméra 5 min sans réponse → alerte | ⚠️ | `guardian.html:1429-1431` | Attend 5 min, mais **pas d'étape intermédiaire de 10 min**. |
| `/checkin-miss` envoie directement aux contacts | ❌ | `luna_web.py:15319-15344` | Dès l'appel, `alert_triggered` est loggé et les contacts sont alertés. Pas de Niveau 2 / Niveau 3 préalables. |

**Conclusion partielle** : la chaîne GPS respecte le principe, mais le check-in caméra court-circuite l'escalade et alerte directement après 5 min.

---

### 2.6 Éviter les faux positifs liés à l'immobilité, au repos, au canapé/lit, ou à une mauvaise détection

| Exigence | État | Preuve code | Commentaire |
|---|---|---|---|
| Tolérance immobilité profil senior : 45 min | ❌ | `engine.py:771` | `immobility_threshold_minutes: 30`. La Policy V2 demande 45 min. |
| Mode nuit suspend l'immobilité | ✅ | `engine.py:477` | OK. |
| Atténuation caméra (TV/canapé/lit) | ❌ | Absent de `engine.py` | **Écart majeur Policy V2 Scénario 2, 3, 4.** |
| Robustesse détection chute côté client | ⚠️ | `guardian.html:1213-1223` | Pixel diff 1/16. Pas de filtre de lumière, pas de détection de visage, pas de YOLO. |
| Mauvaise détection YOLO | N/A | `detector.py` utilise OpenAI Vision | Le risque YOLO est remplacé par les hallucinations/erreurs de Vision. Pas de mode JSON. |

**Conclusion partielle** : le risque de faux positifs liés au repos et à l'immobilité de jour reste élevé.

---

## 3. Analyse technique fichier par fichier

### 3.1 `static/guardian.html` — BehaviorEngine & check-in

**Points positifs :**
- `getUserMedia` appelé directement (ligne 1342) pour respecter les gestes utilisateurs iOS/Android.
- Reset complet des buffers au démarrage (`_startCamLoop`, ligne 1394-1399).
- Gestion des erreurs de permission détaillée.

**Problèmes critiques :**

1. **Check-in automatique toutes les 10 min** (`_startCheckInLoop`, ligne 1410-1413). Ce n'est pas une escalation Policy V2, c'est un contrôle périodique. Il dérange l'utilisateur même en l'absence de tout signal de danger.

2. **Motion detection très basique** (`_measureMotion`, ligne 1213-1223) :
   - Différence pixel 1/16 sur le canal rouge uniquement.
   - Aucune compensation de luminosité.
   - Aucune détection de visage / personne avant de déclarer une chute candidate.
   - Faux positifs probables : ombre mouvante, passage d'un animal, changement de lumière.

3. **Sélection des frames envoyées** (`_sendAnomalyToServer`, ligne 1272-1279) :
   - Si le buffer > 5, on prend 5 frames espacées par `step = buf.length / 5`.
   - Le pic de motion (chute) peut se produire entre deux frames sélectionnées.
   - Les 5 frames envoyées à OpenAI peuvent ne pas contenir l'événement réel.

4. **Anomalie consommée avant réponse serveur** (`_sendAnomalyToServer`, ligne 1281-1291) :
   - `_beh.lastAnomalySend` et `_beh.score = 0` sont mis à jour **avant** la réponse.
   - En cas de 429 ou d'erreur réseau, l'anomalie est perdue sans retry.

5. **Check-in déclenché sans contexte** (`_doCheckIn`, ligne 1419-1432) :
   - Aucune analyse de la scène avant de demander "Tout va bien ?".
   - Si la personne est visible et va bien, on la dérange quand même.

---

### 3.2 `luna_web.py` — Endpoints Guardian

**Points positifs :**
- Rate limit serveur 50 s sur `/anomaly` (ligne 15214-15220).
- Nettoyage `_guardian_scene_analyzers` et `_anomaly_last_call` au stop (ligne 14812-14813).
- Analyse Vision dans un executor (ligne 15249-15251).

**Problèmes critiques :**

1. **`/api/guardian/checkin-miss` alerter directement** (ligne 15282 et suivantes) :
   - Log `alert_triggered` + SMS/DM immédiats.
   - Pas de Niveau 2 (10 min) ni Niveau 3 (5 min) préalables.
   - `has_concern = True` par défaut (ligne 15304), même si la personne dort ou est sous la douche.

2. **Rate limit mal géré côté client** :
   - Le 429 est renvoyé (ligne 15217-15219), mais `guardian.html` ne le traite pas.
   - L'anomalie est perdue.

3. **Fuite mémoire hors stop propre** :
   - `_guardian_scene_analyzers` et `_anomaly_last_call` ne sont nettoyés que dans `guardian_stop`.
   - Pas de TTL, pas de nettoyage sur inactivité.

4. **Seuil `has_concern` permissif** (ligne 15257) :
   - `has_concern = result.get("has_concern") or danger_score >= 5`.
   - Un `danger_score` de 5 est défini comme "inhabituel" dans le prompt, pas préoccupant. Il ne devrait pas suffire à logguer un `perception_concern`.

---

### 3.3 `core/guardian/engine.py` — Moteur de risque

**Points positifs :**
- Mode nuit bien géré (ligne 461-468).
- Grace period 2 h après réponse OK (ligne 284).
- Backoff anti-spam progressif (ligne 142) et plafond 3 alertes/24h (ligne 145).
- SMS d'annulation si fausse alerte (ligne 292-312).

**Problèmes critiques :**

1. **Tolérance immobilité senior = 30 min au lieu de 45 min** (ligne 771-772).
   - La Policy V2 §4.2 demande 45 min pour le profil SENIOR.
   - Cela augmente les faux positifs.

2. **Aucune atténuation caméra de l'immobilité GPS** (`_compute_risk`, ligne 456-510).
   - `_guardian_scene_analyzers` existe côté `luna_web.py`, mais `engine.py` ne l'utilise pas.
   - Scénario TV / canapé / lit de jour = Niveau 2 inutile.

3. **Code mort `speed_anomaly`** (ligne 856-857).
   - `_risk_description` garde une branche inatteignable.

4. **`register_verification_response(ok=False)` ne déclenche pas immédiatement d'alerte** (ligne 315-318).
   - Il met juste `alert_pending = True` et persiste.
   - C'est l'appel suivant à `process_location` qui escalera. Si le GPS ne bouge pas, l'alerte peut être retardée.

---

### 3.4 `core/perception/detector.py` & `analyzer.py` — Vision

**Points positifs :**
- Aucune image stockée, conforme RGPD.
- Différenciation `LYING_BED` / `LYING_FLOOR` / `SITTING` / `STANDING`.
- Mots interdits remplacés dans `analyzer.py:98-111`.

**Problèmes critiques :**

1. **Pas de mode JSON structuré** (`detector.py:114-133` et `:244-249`).
   - Dépend de la fiabilité de GPT-4o-mini pour retourner du JSON valide.
   - Pas de `response_format={"type":"json_object"}`.

2. **Pas de clamping de `danger_score`** (`detector.py:264`).
   - `int(data.get("danger_score", 0))` accepte n'importe quelle valeur entière, y compris négative ou > 10.

3. **Incohérence terminologique** (`detector.py:226`).
   - Le prompt interne mentionne "10=urgence" alors que les messages utilisateur doivent éviter ce mot.

4. **Scène analyzer sans notion de "normalité"** :
   - Une personne allongée sur un lit est classée `LYING_BED` mais n'est pas distinguée d'une personne au sol en termes de risque.
   - Le behavior engine client n'a pas accès à cette information pour atténuer le check-in périodique.

---

## 4. Scénarios critiques testés mentalement

### Scénario A — Personne qui regarde la télévision (Policy V2 Scénario 2)
- 20h, utilisateur assis sur canapé, GPS fixe depuis 1h30, caméra voit "assis".
- `engine.py` : immobility déclenchée à 30 min, score = 0.4 + 0.4*(60/30) = 0.8 → `HIGH`.
- **Comportement attendu** : Niveau 1 DOUTE, aucun message.
- **Comportement réel** : Niveau 2 MEDIUM (vérification) ou HIGH (alerte directe) selon le score exact. **Faux positif.**

### Scénario B — Sieste de jour (Policy V2 Scénario 4)
- 14h, utilisateur allongé sur son lit, GPS fixe, caméra voit `LYING_BED`.
- `engine.py` : immobility à 30 min, puis `prolonged_immobility` à 60 min.
- Check-in automatique à 10 min déclenche "Tout va bien ?".
- Si l'utilisateur dort profondément et ne répond pas dans 5 min → `/checkin-miss` alerte les contacts.
- **Comportement attendu** : Niveau 2 à 45 min, puis 10 min d'attente, puis Niveau 3, puis 5 min, puis Niveau 4.
- **Comportement réel** : Check-in périodique + alerte directe après 5 min de silence. **Faux positif probable.**

### Scénario C — Chute puis reprise (Policy V2 Scénario 5)
- Utilisateur trébuche, 15 s au sol, se relève.
- BehaviorEngine : pic de motion + immobilité < 2 min → `score` peut atteindre 4-5 mais pas 7.
- Si `score < 7`, pas d'envoi serveur.
- **Comportement attendu** : Niveau 0.
- **Comportement réel** : probablement Niveau 0, mais dépend de la sensibilité du motion diff. OK.

### Scénario D — Chute et immobilité (Policy V2 Scénario 6)
- Utilisateur tombe, reste au sol.
- BehaviorEngine : envoie une anomalie après ~25 s d'immobilité (score = 10).
- OpenAI Vision analyse les 5 frames.
- Si Vision détecte `LYING_FLOOR` → analyzer retourne `concern` après 5 min.
- **Comportement attendu** : Niveau 2 à 2 min, Niveau 3 à 5 min, Niveau 4 à 10 min sans réponse.
- **Comportement réel** : le check-in est déclenché dès `danger_score >= 7` (ligne 1298), sans attendre les 2 min de confirmation au sol. **Plus rapide que la Policy V2, donc plus de faux positifs.**

### Scénario E — Téléphone posé sur table (Policy V2 Scénario 7)
- Utilisateur pose le téléphone, va sous la douche 20 min.
- Caméra : aucune personne visible.
- Check-in automatique à 10 min → pas de réponse dans 5 min → `/checkin-miss` alerte les contacts.
- **Comportement attendu** : Niveau 1 DOUTE (< 30 min), puis Niveau 2 à 30 min si absence caméra persiste.
- **Comportement réel** : alerte directe après 15 min (10 min timer + 5 min timeout). **Faux positif.**

---

## 5. Ce qui manque avant une version fiable

### Bloquant (doit être corrigé avant production)

1. **Supprimer ou rendre conditionnel le check-in automatique toutes les 10 min.**
   - Option A : le déclencher uniquement si la caméra détecte une anomalie confirmée.
   - Option B : l'aligner sur l'escalade Policy V2 (Niveau 2 après 45 min d'immobilité, etc.).
   - Option C : le désactiver temporairement dans l'interface.

2. **Atténuer l'immobilité GPS par la caméra.**
   - Si `_guardian_scene_analyzers[session_id]` voit une personne vivante en posture normale (assis, debout, lit) dans les X dernières minutes, reclasser `immobility` en DOUTE (Niveau 1) au lieu de VÉRIFICATION (Niveau 2).
   - C'est l'écart le plus grave par rapport à la Policy V2 Scénario 2.

3. **Aligner `/checkin-miss` sur l'escalade Policy V2.**
   - Niveau 2 = message in-app, 10 min d'attente.
   - Niveau 3 = deuxième message + son, 5 min d'attente.
   - Niveau 4 = SMS contacts.
   - Actuellement, `/checkin-miss` passe directement au Niveau 4.

4. **Corriger le seuil d'immobilité senior à 45 min.**
   - `engine.py:772` doit passer de 30 à 45.

### Important (fortement recommandé)

5. **Améliorer la détection de chute côté client.**
   - Ajouter un filtre de luminosité / mouvement de fond.
   - Ou utiliser un modèle de détection de personne / pose côté client si faisable.
   - Au minimum, ne pas déclencher d'anomalie si aucune personne n'est détectée dans les frames.

6. **Gérer le 429 côté client.**
   - Conserver le score et retenter après `retry_after`.

7. **Ajouter un TTL / nettoyage auto des analyseurs.**
   - Supprimer `_guardian_scene_analyzers[session_id]` si aucune frame reçue depuis 30 min.

8. **Utiliser `response_format={"type":"json_object"}`** pour OpenAI Vision.

9. **Clamper `danger_score`** entre 0 et 10 côté serveur.

### À faire dès que possible

10. **Retirer le code mort `speed_anomaly`** dans `_risk_description`.
11. **Ajouter des tests mockés** pour `/anomaly` et `/checkin-miss`.
12. **Documenter le choix "pas d'image stockée"** et s'assurer que les logs textuels suffisent à auditer.

---

## 6. Décision recommandée

**Ne pas déployer Guardian Mode en production** avec le commit `6d89113` tel quel.

**Actions avant toute mise en production :**
1. Corriger le check-in automatique périodique.
2. Implémenter l'atténuation caméra de l'immobilité GPS.
3. Aligner `/checkin-miss` sur l'escalade Policy V2.
4. Passer le seuil senior à 45 min.
5. Valider par un test terrain APK réel.

**Actions avant beta publique :**
- Gérer le 429 côté client.
- Ajouter TTL/nettoyage auto des analyseurs.
- Améliorer la robustesse de la détection motion côté client.
- Ajouter des tests mockés.

**Conformément aux règles de coordination**, toute décision de déploiement doit être validée par Ludovic.

---

*Avis rédigé par DeepSeek. Ne pas modifier ce fichier sans en avertir l'auteur.*
