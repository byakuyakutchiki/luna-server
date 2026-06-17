# Audit Guardian — Caméra & Reconnaissance

**Date** : 2026-06-17  
**Auditeur** : Kimi Code CLI  
**Scope** : `static/guardian.html`, `core/perception/detector.py`, `core/perception/analyzer.py`, routes Guardian caméra dans `luna_web.py`, et interaction avec le moteur GPS `core/guardian/engine.py`.  
**Référence** : `docs/guardian/GUARDIAN_BEHAVIOR_POLICY_V2.md`, `docs/guardian/POLICY_IMPLEMENTATION_GAPS.md`.

---

## Résumé exécutif

| Thème | Verdict | Gravité |
|---|---|---|
| Caméra active (flux + envoi frames) | ⚠️ Partiellement fonctionnel | Moyenne |
| Reconnaissance visuelle (OpenAI Vision) | ⚠️ Fonctionnelle mais bruyante | Élevée |
| Faux positifs caméra | 🔴 Fréquents par conception | Élevée |
| Check-in automatique caméra | 🔴 Trop agressif | Critique |
| Intégration caméra ↔ moteur Guardian | ❌ Pas d'atténuation GPS | Élevée |
| Tests caméra / perception | ❌ Aucun test automatisé | Élevée |

**Conclusion en une phrase** : La caméra s'active côté navigateur et les frames atteignent le serveur, mais la reconnaissance repose entièrement sur un LLM vision non calibré, sans filtre temporel robuste, sans fusion avec le GPS, et le check-in automatique déclenche une alerte SMS après seulement 30 secondes de non-réponse — ce qui garantit des faux positifs.

---

## 1. Architecture caméra / reconnaissance

### 1.1 Chemin de données

```
static/guardian.html
  ├─ getUserMedia({video:true})  → flux local
  ├─ canvas.toDataURL('image/jpeg',0.65) → base64 320×240
  ├─ POST /api/guardian/frame/{sid} toutes les 10s
  └─ (check-in auto) POST /api/guardian/checkin-miss/{sid} si pas de réponse

luna_web.py
  ├─ _perception_detector.analyze_frame_b64(frame)   # OpenAI gpt-4o-mini
  ├─ SceneAnalyzer().analyze(frame_analysis)          # seuils temporels
  └─ log event + broadcast WS (+ SMS si checkin-miss)
```

### 1.2 Fichiers impactés

| Fichier | Rôle | Lignes clés |
|---|---|---|
| `static/guardian.html` | UI + capture + logique check-in | 1196–1378 |
| `core/perception/detector.py` | Analyse frame via OpenAI Vision | 72–225 |
| `core/perception/analyzer.py` | Analyse temporelle / seuils | 81–287 |
| `luna_web.py` | Routes `/api/guardian/frame/*`, `/api/guardian/checkin-miss/*`, `_perception_alert_contacts` | 15140–15308, 19551–19721, 19732–19881 |
| `core/guardian/engine.py` | Moteur GPS (ne reçoit pas les signaux caméra) | — |

---

## 2. Problème 1 — « La caméra ne fonctionne pas »

### 2.1 Symptômes observables

1. Bouton « Activer la caméra » visible seulement après démarrage Guardian.
2. Sur WebView Android / iOS, `getUserMedia` est souvent bloqué sans HTTPS avec caméra autorisée, ou dans une WebView sans permission explicite.
3. Si `OPENAI_API_KEY` n'est pas renseignée, la route `/api/guardian/frame/{sid}` retourne :
   ```json
   {"error":"Perception non disponible",
    "description":"Analyse caméra non disponible — clé OpenAI manquante."}
   ```
4. Le badge caméra passe à `unavailable` sans explication claire pour l'utilisateur final.

### 2.2 Causes racines

| # | Cause | Fichier + ligne | Impact |
|---|---|---|---|
| A | Dépendance stricte à `OPENAI_API_KEY` au démarrage | `luna_web.py:3900-3901` | Pas de fallback si clé absente ou quota épuisé. |
| B | Aucune détection précoce de la disponibilité caméra avant `getUserMedia` | `static/guardian.html:1215` | L'utilisateur clique, puis seulement découvre que ça ne marche pas. |
| C | Pas de test de connectivité `/api/perception/status` avant activation | `static/guardian.html` | Le frontend ne sait pas si le backend est prêt. |
| D | La frame est envoyée même si la caméra n'est pas prête (`video.readyState < 2`) | `static/guardian.html:1343` | Frames noires envoyées → analyse inutile ou fausse. |
| E | Pas de reprise automatique après une erreur réseau / WS | `static/guardian.html:1363` | Boucle caméra silencieusement arrêtée. |

### 2.3 Recommandations

1. **Pré-vérification backend** : avant d'appeler `getUserMedia`, faire un `GET /api/perception/status` et afficher un message clair si `available=false`.
2. **Vérifier `video.readyState`** avant `drawImage` ; ignorer la frame si `< HAVE_CURRENT_DATA`.
3. **Ajouter un mode dégradé** : si OpenAI n'est pas disponible, la caméra peut quand même servir de preuve locale (frame affichée, pas d'analyse IA) ou utiliser un modèle local léger.
4. **Loguer côté client** les erreurs `getUserMedia` avec `name` et `message` pour le support.
5. **Tester dans WebView Android** spécifiquement, car c'est le déploiement cible (APK v2.8).

---

## 3. Problème 2 — « La reconnaissance délire / faux positifs »

### 3.1 Comment la reconnaissance fonctionne

`core/perception/detector.py` envoie chaque frame à `gpt-4o-mini` avec :
- `temperature=0.1`
- `max_tokens=300`
- `detail="low"` (85 tokens, rapide)
- Prompt demandant : `persons_count`, `posture`, `objects`, `scene_summary`.

`core/perception/analyzer.py` maintient un historique de 60 frames (~10 min à 10 s) et déclenche :
- `PERSON_ON_FLOOR` attention à 120 s, concern à 300 s.
- `EXTENDED_ABSENCE` attention à 3600 s (1 h).

### 3.2 Faux positifs identifiés

| Scénario | Pourquoi c'est un faux positif | Où dans le code |
|---|---|---|
| **Téléphone retourné** sur une table | La caméra voit une surface — le LLM peut interpréter « personne au sol ». | `detector.py:51-70` prompt ne demande pas de différencier surface et sol. |
| **Ombre / reflet / lumière changeante** | Classé comme personne ou objet. | Pas de filtre de confiance ni de validation multi-frame. |
| **Animal domestique** | Compté comme objet (OK), mais peut masquer une personne ou être pris pour une forme humaine. | `analyzer.py:98` compte uniquement `persons_count`. |
| **Canapé / lit vu de haut** | Confondu avec « personne allongée ». | `PersonPosture.LYING_BED` vs `LYING_FLOOR` dépend du LLM. |
| **Check-in automatique 60 s** | L'utilisateur n'a que 30 s pour répondre, même s'il est simplement absent du téléphone. | `static/guardian.html:1288-1333` |
| **Speed anomaly GPS** | `engine.py:490-492` déclenche HIGH si `speed > 5 m/s` (18 km/h) — perturbations GPS urbaines. | `core/guardian/engine.py:490-492` |

### 3.3 Problèmes spécifiques de l'analyseur

1. **Pas de calibrage par environnement** : la scène de nuit, le contre-jour, la faible luminosité ne sont pas détectés. Le prompt dit « si image floue/sombre → persons_count:0 » mais le LLM ne respecte pas toujours cette consigne.
2. **Seuils temporels courts** :
   - 2 min au sol → attention (médian entre une vraie chute et quelqu'un qui s'accroupit).
   - 5 min au sol → concern → SMS potentiel.
   - Ces seuils ne tiennent pas compte du contexte (sieste, yoga, réparation au sol).
3. **Aucune fusion avec le GPS** : la caméra et le GPS tournent en parallèle. Si le GPS bouge, la personne n'est pas immobile même si la caméra ne la voit pas. Inversement, si le GPS est fixe mais la caméra voit une personne assise, l'alerte immobilité GPS ne devrait pas monter.
4. **Reset de l'historique** : `SceneAnalyzer.reset()` existe mais n'est pas appelé automatiquement quand on change d'environnement ou quand la caméra est coupée/rallumée.

### 3.4 Recommandations

1. **Augmenter la robustesse de la détection** :
   - Demander au LLM une **confiance** par personne et ignorer les détections `confidence < 0.7`.
   - Exiger **2 frames consécutives** avec la même posture anormale avant de lever un signal.
2. **Contextualiser avec le GPS** :
   - Si `is_immobile=False` (GPS bouge), ne pas alerter sur `PERSON_ON_FLOOR` seul.
   - Si la caméra voit une personne vivante (assis/debout), atténuer le signal `immobility` GPS (Policy V2 scénario 2).
3. **Ajouter des modes de prudence** :
   - Mode « assistif » (défaut) : remonte `concern` seulement.
   - Mode « passif » : remonte `concern` uniquement si GPS confirme l'immobilité.
4. **Corriger le check-in automatique** :
   - Supprimer ou rendre **optionnel** le check-in vocal toutes les 60 s.
   - Si activé, délai de réponse minimum 2 min (Policy V2) et vérifier d'abord que la personne est visible immobile.
5. **Améliorer le prompt** :
   - Ajouter des exemples négatifs : téléphone retourné, animal, ombre.
   - Demander de distinguer « sol dur » vs « lit/canapé » explicitement.
6. **Ajouter des tests automatisés** :
   - Mock d'OpenAI Vision avec réponses prédéfinies.
   - Scénarios : personne au sol 1 min, personne au sol 6 min, téléphone retourné, animal, absence < 30 min.

---

## 4. Problème 3 — Check-in automatique (ligne de conduite critique)

### 4.1 Code actuel

```javascript
// static/guardian.html:1288-1333
function _startCheckInLoop(){
  _checkInTimer=setInterval(_doCheckIn, 60000);  // toutes les 60s
}
function _doCheckIn(){
  if(CAM_STATE!=='active') return;
  maybeSpeak('Contrôle Guardian. Tout va bien ? Appuyez sur Oui si vous allez bien.');
  openVerifyModal('🎥 Contrôle automatique — Tout va bien ?');
  _checkInWait=setTimeout(function(){
    if(_checkInPending) _checkInMissed();
  }, 30000);  // 30s d'attente
}
function _checkInMissed(){
  // → POST /api/guardian/checkin-miss/{sid}
  // → envoie un SMS HIGH aux contacts immédiatement
}
```

### 4.2 Pourquoi c'est critique

- **30 secondes de non-réponse = SMS aux contacts**. Cela contredit totalement la Policy V2 (10 min avant escalade).
- Même si la personne est en bonne santé mais simplement hors de portée du téléphone (cuisine, toilettes, jardin), les contacts reçoivent un SMS d'alerte.
- Cela crée un effet « loup » : les contacts reçoivent des alertes constantes et finissent par les ignorer.

### 4.3 Recommandation immédiate

**Désactiver le check-in automatique par défaut.** Le transformer en option explicite avec :
- intervalle configurable (minimum 10 min)
- délai de réponse configurable (minimum 2 min)
- vérification préalable : si la caméra détecte une personne visible et vivante, ne pas déclencher le check-in.

---

## 5. Écarts par rapport à la Policy V2 (focus caméra)

| Règle Policy V2 | Implémentation actuelle | Statut |
|---|---|---|
| Caméra signal **auxiliaire**, jamais principal | La caméra déclenche des alertes SMS directement via checkin-miss et perception concern | 🔴 Non conforme |
| Personne au sol 2 min → vérification, 5 min → suspicion, 10 min → alerte | 2 min attention, 5 min concern (peut alerter), check-in 30 s | 🔴 Non conforme |
| Tolérance absence caméra 30 min (profil senior) | `EXTENDED_ABSENCE` à 60 min | 🟡 Écart mineur |
| Atténuation GPS si caméra voit personne vivante | Non implémenté | 🔴 Non conforme |
| Animal = objet, pas personne | Implémenté (persons_count uniquement) | ✅ Conforme |
| Téléphone retourné ≠ personne au sol | Non différencié | 🔴 Non conforme |
| Perte caméra seule → Niveau 1 | Pas de signal `camera_lost` dans le moteur | ⚠️ Partiel |

---

## 6. Tests

### 6.1 Tests Guardian P0 existants

Le fichier `tests/test_guardian_p0.py` couvre uniquement la logique GPS (mode nuit, vérification, annulation, anti-spam).  
**Résultat** : 30/30 PASS (le 2026-06-17).

### 6.2 Tests perception manquants

Aucun test n'existe pour :
- `PerceptionDetector.analyze_frame_b64`
- `SceneAnalyzer.analyze`
- Les routes `/api/guardian/frame/*` et `/api/guardian/checkin-miss/*`
- L'intégration caméra ↔ GPS.

---

## 7. Plan d'action recommandé

### Actions immédiates (bloquant pour production)

1. **Désactiver le check-in automatique** dans `static/guardian.html` (lignes 1285–1333) ou le mettre derrière un flag `false` par défaut.
2. **Supprimer / neutraliser `speed_anomaly`** dans `core/guardian/engine.py:490-492` comme indicateur de chute (conformément à la Policy V2 §Scénario 5).
3. **Ajouter une vérification `video.readyState`** avant chaque envoi de frame.

### Actions courtes (1–2 jours)

4. **Ajouter un test de disponibilité backend** (`/api/perception/status`) avant d'activer la caméra.
5. **Augmenter la robustesse** de `SceneAnalyzer` :
   - confiance minimale,
   - 2 frames consécutives,
   - filtre nuit / faible luminosité.
6. **Fusionner les signaux caméra et GPS** dans `core/guardian/engine.py` :
   - si caméra active et personne visible vivante → atténuer `immobility`.
   - si GPS bouge → ignorer `PERSON_ON_FLOOR` caméra seul.
7. **Écrire des tests mockés** pour la perception.

### Actions moyennes (1 semaine)

8. **Refaire le prompt Vision** avec des exemples de faux positifs.
9. **Ajouter un mode caméra local / offline** sans OpenAI.
10. **Documenter le comportement caméra** dans `docs/guardian/GUARDIAN_CAMERA_BEHAVIOR.md`.

---

## 8. Verdict Kimi

| Question | Réponse |
|---|---|
| La caméra fonctionne-t-elle techniquement ? | Oui, mais fragile (dépend OpenAI, WebView, permissions). |
| La reconnaissance est-elle fiable ? | Non — trop de faux positifs par conception actuelle. |
| Guardian est-il utilisable en production avec la caméra ? | **Non**, à cause du check-in automatique 60 s / 30 s et de l'absence de fusion GPS. |
| Quelle est la priorité ? | **Critique** : désactiver le check-in auto, puis calibrer la reconnaissance. |

---

*Audit réalisé sans modification de code. Aucun secret (.env, clés API) n'a été lu.*
