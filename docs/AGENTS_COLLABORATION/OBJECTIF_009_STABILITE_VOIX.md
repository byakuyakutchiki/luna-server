# Objectif 009 — Stabilité voix Luna : diagnostiquer et corriger les coupures

**Date** : 2026-05-25
**Statut** : ouvert — diagnostic multi-agents
**Priorité** : critique
**Lead** : Claude
**Décideur final** : Ludovic

## Constat

- ✅ Voix fonctionne avec `gpt-realtime-mini` (OpenAI Realtime)
- ⚠️ Luna s'arrête parfois de parler seule / coupe la réponse sans raison claire
- ⚠️ Les sessions vocales ne durent pas toujours jusqu'à la fin du message

## But

Identifier pourquoi la session vocale se coupe prématurement et corriger **uniquement** la cause minimale.

## Approche

1. **Ludovic** teste sur téléphone réel, note l'heure exacte et le comportement
2. **Claude** lit les logs serveur au moment du test
3. **DeepSeek** analyse la télémétrie APK et les événements associés
4. **Kimi** rédige les diagnostics cockpit clairs et non-culpabilisants
5. **Cursor** vérifie que l'UI mobile ne masque pas le problème
6. **Codex** coordonne et synthétise

## Missions par agent

### 🔴 LUDOVIC — Validation fondateur

**Tâche** : Test réel sur téléphone avec journalisation précise

**À faire** :
1. Appuyer sur le bouton vocal
2. **Noter l'heure exacte** du démarrage (HH:MM:SS)
3. Observer le comportement :
   - Luna coupe-t-elle **pendant qu'elle parle** ?
   - Luna coupe-t-elle **avant de parler** (pas d'audio) ?
   - Luna coupe-t-elle **après une phrase complète** ?
   - Luna s'arrête-t-elle **sans raison** ou après un délai fixe (~5s, ~10s, ~30s) ?
4. Attendre si la voix reprend seule
5. Noter l'heure exacte de l'arrêt
6. Appuyer sur le bouton d'arrêt si nécessaire
7. **Rapporter** :
   - Heure début test (HH:MM:SS)
   - Durée avant coupure
   - Comportement avant/après coupure
   - Si c'est reproductible (1ère fois, 2e fois, N° tentative)

**Validation** :
- [x] Un test réel en cours
- [ ] Heure exacte notée
- [ ] Comportement documenté
- [ ] Correction déployée
- [ ] Test de validation après correction

---

### 🔵 CLAUDE — Lead technique serveur

**Tâche** : Investiguer logs Cloud Run au moment exact du test

**À faire** :

1. **Attendre heure exacte de Ludovic** (ex: 19:47:15)
2. **Lire logs Cloud Run** dans la fenêtre correspondante (±2min)
   ```
   bash /home/ludo/PROJETS/IA_WATCH/PROPRIO/serveur/logs.sh | grep -A 20 "luna-voice.*19:47"
   ```

3. **Vérifier `/ws/luna-voice`** :
   - Quand la session a-t-elle été créée ?
   - Quand s'est-elle fermée ?
   - Code de fermeture WebSocket (1000 = normal, 1001 = going away, autre = erreur) ?
   - Qui a fermé : serveur ou client ?

4. **Vérifier OpenAI Realtime** :
   - `WARNING: WebVoice: OpenAI WS closed` — si present, quand ?
   - `ERROR: WebVoice: OpenAI error` — détails de l'erreur ?
   - Statut `response.audio.delta` — reçu jusqu'à quand ?
   - VAD (Voice Activity Detection) — a-t-il interrompu la génération ?
   - Timeout interne — combien de secondes avant auto-close ?

5. **Proposer cause probable** :
   - Timeout OpenAI côté serveur (ex: 30s max par session) ?
   - WebSocket fermé prématurément par client ?
   - OpenAI VAD a arrêté la génération (détection fin de voix utilisateur) ?
   - Buffer vide côté serveur (fin stream prématurément) ?
   - Erreur non-catchée qui ferme la session ?

6. **Proposer correction minimale**
   - Une ligne de code max si possible
   - Pas de refactor WebSocket
   - Pas de changement modèle OpenAI
   - Tester en local avant déploiement

7. **Ne pas déployer** sans validation Ludovic

**Livrables** :
- Heure exact fermeture WS
- Cause probable + preuve (logs)
- Correction proposée (fichier + ligne)
- Risques de régression
- Plan de test

---

### 🟠 DEEPSEEK — Agent diagnostic temps réel

**Tâche** : Analyser télémétrie APK et définir seuils incident

**À faire** :

1. **Analyser événements APK** liés à la coupure :
   - `voice_first_audio_chunk_received` — temps reçu ?
   - `voice_playback_started` — temps commencé ?
   - `voice_ws_closed` — temps fermé ?
   - `voice_session_ended` — temps fin session ?
   - `voice_no_audio_after_timeout` — timeout déclenché ?
   - Tous les autres événements dans la fenêtre de temps

2. **Proposer seuil incident** : "voice_cut_mid_response"
   - Déclenche si : `voice_playback_started` reçu ET `voice_ws_closed` < 10s après
   - Fenêtre compact : 60s max d'événements
   - Pas d'audio brut ni secret

3. **Définir format déploiement DeepSeek** pour cet incident :
   ```json
   {
     "incident_type": "voice_cut_mid_response",
     "time_since_playback_started_ms": 3500,
     "events_sequence": ["voice_playback_started", "voice_ws_closed"],
     "ws_close_code": 1006,
     "probable_cause": "server_terminated",
     "deepseek_diagnosis": "session forcée après ~3.5s de playback"
   }
   ```

4. **Proposer diagnostics type** pour chaque scénario :
   - **Scénario A** : WS ferme 1-2s après playback start → client timeout probable
   - **Scénario B** : WS ferme 5-10s après playback → timer serveur/OpenAI probable
   - **Scénario C** : WS ferme 30s+ après playback → session complète normal

5. **Ne pas modifier prod** — audit uniquement

**Livrables** :
- Format événement pour coupure
- Seuils déclenchement incident
- Diagnostics type par scénario
- Format JSON pour cockpit
- `agents/DEEPSEEK_AVIS_009_VOIX_COUPURE.md`

---

### 🟢 KIMI — Formulation cockpit fondateur

**Tâche** : Rédiger diagnostics cockpit clairs et non-culpabilisants

**À faire** :

1. **Observation des faits** : textes factuels
   ```
   "Luna a commencé à parler puis s'est arrêtée après 3.5 secondes"
   "La session WebSocket a été fermée pendant la génération"
   "Le serveur a coupé la connexion avant la fin de la réponse"
   ```

2. **Interprétation par zone** : textes explicatifs
   ```
   Zone Client (APK) :
   "Le téléphone attendait la réponse audio complète"

   Zone Serveur :
   "Luna a reçu votre question et a commencé la réponse"

   Zone OpenAI Realtime :
   "OpenAI a généré la réponse mais la session s'est fermée prématurément"

   Zone VAD (détection voix) :
   "Le serveur a peut-être interprété la fin de votre question avant le début"
   ```

3. **Recommandation neutre** : pas de reproche utilisateur
   ```
   ❌ "Luna n'a pas pu terminer"
   ✅ "La réponse a été interrompue. Réessayez ou vérifiez la connexion réseau."
   ```

4. **Non-culpabilisation**
   - Ne pas dire "erreur utilisateur"
   - Ne pas suggérer "APK cassée" si c'est serveur
   - Rester factuel et constructif

**Livrables** :
- Textes cockpit par zone (client, serveur, OpenAI, VAD)
- Recommandations claires
- Formulation adaptée mobile
- `agents/KIMI_AVIS_009_VOIX_COUPURE.md`

---

### 🟡 CURSOR — Vérification UI mobile

**Tâche** : Auditer l'interface pendant et après une coupure

**À faire** :

1. **Pendant la voix** :
   - L'overlay vocal affiche-t-il "Luna parle..." ?
   - Le bouton raccrocher est-il visible ?
   - Le bouton retour fonctionne-t-il sans stopper l'audio ?

2. **Pendant une coupure** :
   - L'UI affiche-t-elle toujours "Luna parle..." alors qu'aucun son ne sort ?
   - Y a-t-il un état "écoutant..." qui refuse de changer ?
   - Un spinner bloqué qui cache une erreur ?

3. **Après une coupure** :
   - Le bouton réessayer est-il visible et fonctionnel ?
   - Le cockpit montre-t-il le diagnostic ?
   - L'utilisateur peut-il réessayer immédiatement ?

4. **Non-régression** :
   - Les états vocaux existants ne sont pas masqués
   - L'affichage cockpit chronologie reste visible sur mobile
   - Les boutons restent cliquables

**Livrables** :
- Screenshot des états problématiques
- Propositions d'amélioration UI
- Pas de refactor, corrections minimales
- `agents/CURSOR_AVIS_009_VOIX_UI.md`

---

### ⚪ CODEX — Coordination et synthèse

**Tâche** : Orchestrer le diagnostic multi-agents et synthétiser

**À faire** :

1. **Coordination temporelle** :
   - Ludovic : test réel + heure exacte
   - Claude : logs serveur au moment exact
   - DeepSeek : télémétrie et seuils
   - Kimi : textes cockpit
   - Cursor : UI vérification

2. **Séparation des domaines** :
   - ✅ Stabilité voix (009) vs DeepSeek diagnostic (008)
   - ✅ Bug audio vs bug UI vs bug serveur
   - ✅ Correction minimale vs refactor large

3. **Traçabilité des décisions** :
   - Tous les avis dans `agents/<AGENT>_AVIS_009.md`
   - Synthèse finale dans `DECISION_FINALE_009.md`
   - Qui a décidé quoi et pourquoi

4. **Garde-fous** :
   - ❌ Pas de refactor WebSocket
   - ❌ Pas de changement modèle OpenAI
   - ❌ Pas de modification APK version
   - ❌ Pas de déploiement sans validation Ludovic

5. **Synthèse pour Claude** :
   - Tous les avis lus et validés
   - Cause probable consolidée
   - Correction minimale proposée
   - Risques de régression listés
   - Plan de test défini

**Livrables** :
- Synthèse dans `DECISION_FINALE_009.md`
- Checklist coordination
- Prêt pour validation Ludovic

---

## Critères de réussite

- [x] Ludovic a noté heure exacte et comportement du test
- [ ] Claude a identifié cause probable dans logs
- [ ] DeepSeek a proposé seuils incident et diagnostics type
- [ ] Kimi a rédigé textes cockpit clairs
- [ ] Cursor a vérifié UI mobile
- [ ] Codex a synthétisé l'ensemble
- [ ] Correction proposée est minimale (1-3 lignes max)
- [ ] Test réel après correction améliore la stabilité
- [ ] Une session vocale dure assez longtemps pour réponse complète

---

## Points à ne PAS faire

- ❌ Gros refactor du pipeline vocal
- ❌ Changement modèle OpenAI
- ❌ Modification APK sans validation
- ❌ Déploiement sans validation Ludovic
- ❌ Auto-correction sans diagnostic préalable
- ❌ Modification UI qui cache une erreur

---

## Timeline

| Étape | Responsable | Durée |
|---|---|---|
| Test réel + heure | Ludovic | 15min |
| Logs serveur + cause | Claude | 30min |
| Télémétrie + seuils | DeepSeek | 30min |
| Textes cockpit | Kimi | 20min |
| UI vérification | Cursor | 20min |
| Synthèse + correction | Codex + Claude | 30min |
| Validation Ludovic | Ludovic | 10min |
| **Total** | **Tous** | **~2h30** |

---

## Document de synthèse final

À créer après tous les avis : `docs/AGENTS_COLLABORATION/DECISION_FINALE_009_STABILITE_VOIX.md`

Contenu :
- Cause identifiée
- Correction proposée (fichier + ligne)
- Risques de régression
- Plan de test
- Validation Ludovic (oui / non / à revoir)
