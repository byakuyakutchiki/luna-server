# TASK-014-KIMI-REAL-VISIO-UX — Rapport terrain UX visio

**Agent** : Kimi (œil terrain + UX réelle)  
**Date** : 2026-05-30  
**Statut** : ✅ Livré — audit terrain contre vision finale Iris  
**Fichier** : `docs/AGENTS_COLLABORATION/agents/KIMI_REAL_VISIO_UX_014.md`

---

## 1. Méthode

- Screenshot navigateur headless (Chromium) de `simli.html` en mode mobile (390×844) et desktop (1280×720)
- Analyse du code CSS/HTML/JS de `static/simli.html` (commit `5413927`, barre Iris retirée)
- Aucun déploiement, aucune session Simli lancée, aucun crédit consommé

---

## 2. Verdict par target — vision finale Iris

### Target 1 — Présence crédible

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 À corriger |
| **Rendu réel** | Écran de démarrage propre (8/10) : dégradé sombre, typographie claire, bouton vert bien dimensionné. **Mais** : l'avatar Simli actuel (`SIMLI_FACE_ID=b9e5fba3-071a-4e35-896e-211c4d6eaa7b`) est un avatar générique, pas Luna. L'utilisateur ne voit pas "une assistante réelle", il voit un avatar 3D standard. |
| **Impact promesse** | "Parler à une assistante réelle" est faussé dès l'ouverture de la caméra. L'immersion texte est bonne, l'immersion visuelle est faible. |
| **Décision Ludovic** | **Oui** — choisir entre : (a) avatar Simli personnalisé Luna, (b) avatar généré cohérent, (c) garder l'actuel en attendant. |

### Target 2 — Voix féminine FR

| Item | Verdict |
|---|---|
| **Verdict** | 🔴 Régression (non prouvée) |
| **Rendu réel** | Impossible à vérifier par screenshot. Configuration existante : `ELEVENLABS_VOICE_ID=6BlZrFdruL4hpXFHmHUC` (Alice) + `elevenlabsLanguageCode=fr` dans le payload Simli. **Mais** Ludovic rapporte que la voix ne fonctionne pas en production. Sans preuve audio terrain, la target est non atteinte. |
| **Impact promesse** | Une secrétaire avec une voix masculine ou robotique casse immédiatement la crédibilité. C'est le problème le plus audible. |
| **Décision Ludovic** | **Non pour l'audit** (Kimi ne peut pas tester l'audio headless). **Oui pour le test** : DeepSeek doit vérifier les env vars Cloud Run, puis Ludovic doit faire un test audio court (< 30s). |

### Target 3 — Identité Ludovic

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 À corriger |
| **Rendu réel** | Le `firstMessage` inclut `subscriber_name` depuis `profile.first_name`. **Mais** : l'écran dit "Visio avec Luna" alors que le prompt et le message disent "Iris". L'utilisateur s'attend à Luna, se fait saluer par Iris. De plus, le prompt ne contient pas de contexte fondateur ("tu parles à Ludovic, fondateur de YAWatch"), juste un prénom. |
| **Impact promesse** | "Iris sait à qui elle parle" est partiel : elle sait le prénom, pas l'identité. L'incohérence nom Luna/Iris crée de la friction cognitive. |
| **Décision Ludovic** | **Oui** — décider : (a) tout nommer Luna, (b) tout nommer Iris (secrétaire de Luna) avec écran adapté, (c) laisser l'incohérence. |

### Target 4 — Compréhension vocale

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 À prouver |
| **Rendu réel** | Simli gère STT → gpt-4o-mini nativement. Aucun problème de code visible. **Mais** : pas de preuve terrain que "prends une note : appeler le garage demain" fonctionne en visio. Le transcript local `_visioTranscript` existe, mais on ne sait pas si Simli comprend et exécute. |
| **Impact promesse** | "Comprendre une phrase simple" est la base du secrétariat. Sans preuve, c'est une supposition. |
| **Décision Ludovic** | **Oui** — test court : lancer une visio, dire "prends une note de test", vérifier si la note est créée. |

### Target 5 — Vision caméra

| Item | Verdict |
|---|---|
| **Verdict** | 🔴 Régression (non prouvée) |
| **Rendu réel** | Le pipeline existe : capture canvas 320×240 toutes les 12s → POST `/api/visio/perception` → GPT-4o-mini Vision → injection `[Système vision]` via `sendAppMessage`. **Mais** : Ludovic dit qu'elle ne le voit pas, ne le reconnaît pas. Latence 12s = pas temps réel. Qualité 320×240 = faible pour la reconnaissance. |
| **Impact promesse** | "Répondre à une question visuelle simple" est techniquement branché mais non validé en conditions réelles. L'utilisateur ne ressent pas qu'on le voit. |
| **Décision Ludovic** | **Oui** — test terrain court : "Est-ce que tu me vois ?" + main levée. Si échec → DeepSeek audit pipeline. |

### Target 6 — Secrétariat (note, résumé, rappel, recherche)

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 Partiellement branché, non prouvé |
| **Rendu réel** | Code présent : `/api/visio/notes`, `_visioTranscript`, `_tool_create_instruction`, tools `get_weather`, `get_news`, `search_web`. **Mais** : aucune preuve terrain que ces fonctions répondent correctement en visio. La modal notes existe (slide-up), le bouton est visible. |
| **Impact promesse** | "Prendre une note, résumer, créer un rappel" est la vocation d'Iris. Si ça ne marche pas, Iris n'est pas une secrétaire. |
| **Décision Ludovic** | **Oui** — matrice de 5 tâches à tester : note, résumé, météo, rappel, recherche. |

### Target 7 — Protection actions sensibles

| Item | Verdict |
|---|---|
| **Verdict** | 🟢 Validé (code) |
| **Rendu réel** | Guard `_ACTION_TOOLS` présent. Le code demande confirmation pour SMS/appel/email/paiement/réservation. **Mais** : non testé en visio. Le bouton "Inviter" est présent (avec modal contact list). |
| **Impact promesse** | Protection correcte en code. Le risque est le non-test en visio. |
| **Décision Ludovic** | **Non** — le code est correct, le test peut attendre. |

### Target 8 — Canal texte secours

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 À décider |
| **Rendu réel** | Barre Iris retirée (bon). **Mais** : aucune alternative. Si STT échoue, l'utilisateur est bloqué sans recours. |
| **Impact promesse** | "Sans demander à l'utilisateur de taper sauf secours" — le secours n'existe pas encore. |
| **Proposition UX** | **Swipe-up mini-drawer** (ou bouton ✏️ discret dans la barre d'actions top) : apparaît uniquement sur demande, un seul champ texte, envoi, auto-fermeture. Pas de chat, pas d'historique, pas de bulles. Voir section 4. |
| **Décision Ludovic** | **Oui** — valider le principe "secours discret" et le format (swipe-up vs bouton). |

### Target 9 — UI premium / sobriété

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 À corriger (deux points) |
| **Rendu réel** | Pas de barre intrusive ✓. Bouton raccrocher bien placé ✓. Toast non intrusif ✓. **Mais** : (1) **5 boutons en haut** (`#visioActionsBar`) sur 390px mobile vont wrap ou tronquer. Calcul : ~490px de contenu pour 390px d'écran. (2) **Sélecteur `<select>` natif** pour la durée casse le premium sur Android. |
| **Impact promesse** | "L'écran visio reste immersif" — la barre top surcharge l'expérience visuelle. Le sélecteur cheap rappelle un formulaire web, pas une app premium. |
| **Décision Ludovic** | **Non pour l'audit** — ce sont des corrections niveau 1/2 que Kimi peut proposer sans validation. **Mais** si réduction à 3 boutons + icônes seules sur mobile = UI visible modifiée → validation Ludovic recommandée. |

### Target 10 — Économie crédits

| Item | Verdict |
|---|---|
| **Verdict** | 🟡 Partiel |
| **Rendu réel** | `maxIdleTime=60s` ✓, confirmation hangup ✓, barre retirée (évite les messages accidentels) ✓. **Mais** : vision capture toutes les 12s en permanence = appels API GPT-4o-mini Vision coûteux. Si l'utilisateur oublie de couper la caméra, la boucle continue. |
| **Impact promesse** | "Chaque test réel est court, mesuré" — la vision ne s'arrête pas automatiquement si l'utilisateur reste immobile. |
| **Décision Ludovic** | **Non** — Kimi signale le risque, DeepSeek peut évaluer le coût. |

---

## 3. Synthèse verdicts

| Target | Verdict | Preuve terrain | Décision Ludovic |
|---|---|---|---|
| 1. Présence | 🟡 À corriger | Avatar générique | **Oui** |
| 2. Voix FR | 🔴 Non prouvée | Configuration existe, audio non testé | **Oui (test)** |
| 3. Identité | 🟡 À corriger | Incohérence Luna/Iris, prénom sans contexte | **Oui** |
| 4. Compréhension | 🟡 À prouver | Code OK, test manquant | **Oui (test)** |
| 5. Vision | 🔴 Non prouvée | Pipeline existe, Ludovic dit que non | **Oui (test)** |
| 6. Secrétariat | 🟡 Partiel | Code OK, tests manquants | **Oui (test)** |
| 7. Protection | 🟢 Validé (code) | Guard présent | Non |
| 8. Texte secours | 🟡 À décider | Barre retirée, rien en remplacement | **Oui** |
| 9. UI premium | 🟡 À corriger | 5 boutons top mobile, sélecteur natif | Non (niveau 1) |
| 10. Économie | 🟡 Partiel | maxIdleTime OK, vision continue | Non |

---

## 4. Proposition UX premium — canal texte secours

### Option recommandée : "Panneau temporaire swipe-up"

| Aspect | Détails |
|---|---|
| **Déclenchement** | Swipe up depuis le bas de l'écran (geste natif mobile) OU bouton "✏️" dans la barre d'actions top (si swipe trop complexe à implémenter) |
| **Apparence** | Drawer slide-up depuis le bas, hauteur ~180px, fond `rgba(10,10,20,0.92)` + `backdrop-filter: blur(16px)`. Bords supérieurs arrondis (`border-radius: 20px 20px 0 0`). |
| **Contenu** | Un seul `<input type="text">`, fond transparent, bordure 1px `rgba(124,140,248,0.3)`, placeholder `"Écrire si le micro ne passe pas…"`, max 300 caractères. |
| **Envoi** | Icône ➤ ou touche Entrée. Le message est envoyé via `sendAppMessage` au bot uniquement (pas wildcard). |
| **Fermeture** | Auto après envoi (500ms), swipe down, clic sur le fond noir, ou touche Échap. |
| **Règle d'or** | Le drawer ne reste **jamais** ouvert. C'est un outil de secours d'urgence, pas un canal de conversation. Pas d'historique, pas de bulles, pas de scroll. |

### Pourquoi c'est premium (et pas la barre Iris)

1. **Invisible par défaut** — zéro intrusion dans l'immersion vidéo
2. **Geste natif** — swipe up est un pattern mobile universel (iOS/Android)
3. **Contexte explicite** — le placeholder dit pourquoi ça existe
4. **Pas de conversation** — un seul message, un seul envoi, fin. Pas de chat.
5. **Aligné matrice 014** : "Sobriété UI = rien ne couvre inutilement l'expérience visio"

### Alternative simple si swipe complexe

**Bouton "✏️" dans `#visioActionsBar`** à la place d'un des 5 boutons existants (par exemple fusionner "🔗 Partager" et "👥 Inviter" en un seul bouton "🔗 Partager/Inviter"). Clique → même drawer slide-up.

---

## 5. Problème bloquant immédiat — surcharge mobile top bar

### Le problème

5 boutons texte + emoji dans `#visioActionsBar` sur un viewport mobile de 390px :

- "🎙 Luna active" ≈ 110px
- "📎 Analyser" ≈ 90px
- "👥 Inviter" ≈ 85px
- "🔗 Partager" ≈ 90px
- "📝 Notes" ≈ 85px
- Gaps (8px × 4) = 32px
- **Total ≈ 492px > 390px**

Résultat : sur iPhone SE (375px) ou tout téléphone en portrait, les boutons vont **wrap à 2 lignes** ou le texte sera **tronqué** (`text-overflow: ellipsis`). C'est visuellement cheap et fonctionnellement risqué (clics accidentels).

### Recommandation Kimi (niveau 1, pas de validation requise pour la proposition)

Sur mobile (`@media (max-width: 480px)` et `orientation: portrait`) :
- Réduire `#visioActionsBar` à **3 boutons max** : "🎙" (micro), "📝" (notes), "⋯" (menu overflow avec Analyser/Partager/Inviter)
- Ou : icônes seules sans texte pour tous les boutons (tooltip au long-press)

---

## 6. Screenshots terrain

- **Mobile** : `/tmp/simli_mobile.png` (390×844) — écran démarrage propre, sans barre Iris
- **Desktop** : `/tmp/simli_desktop.png` (1280×720) — même rendu, centré, cohérent

Ces captures prouvent l'état actuel post-retrait barre. Elles ne peuvent pas prouver la voix, la vision ou la compréhension vocale.

---

## 7. Ce que Kimi ne peut pas vérifier seul

| Élément | Pourquoi | Qui peut le faire |
|---|---|---|
| Voix féminine FR | Pas de haut-parleur sur VM headless | Ludovic (test 30s) + DeepSeek (audit env vars) |
| Vision caméra réelle | Pas de caméra sur VM, pas de scène réelle | Ludovic (test "tu me vois ?" + main levée) |
| Compréhension vocale | Pas de micro, pas d'API Simli appelée | Ludovic (test phrase simple) |
| Avatar en mouvement | Screenshot statique, pas de session Daily.js | Ludovic (test visuel) |
| Wrap mobile des 5 boutons | Screenshot headless ne montre pas l'état post-cinématique | Ludovic (test sur téléphone) ou Kimi (DevTools responsive) |

---

## 8. Actions recommandées — ordre de priorité

### Immédiat (avant tout déploiement)
1. **Décider Luna vs Iris** — aligner écran, prompt, firstMessage, barre d'actions
2. **Tester voix** — DeepSeek vérifie env vars Cloud Run → Ludovic test audio 30s
3. **Tester vision** — Ludovic : "Est-ce que tu me vois ?" + main levée

### Court terme (après tests terrain)
4. **Canal texte secours** — implémenter le drawer swipe-up si Ludovic valide le principe
5. **Réduire barre top mobile** — 3 boutons max ou icônes seules
6. **Styliser sélecteur durée** — remplacer `<select>` natif par composant custom

### Moyen terme
7. **Avatar Luna** — créer/personnaliser un avatar Simli cohérent
8. **Optimiser vision** — fréquence, qualité, ou passer en mode "sur demande" plutôt que 12s auto

---

*Kimi — œil terrain. Aucun code déployé. Aucune session Simli lancée. Aucun crédit consommé.*
