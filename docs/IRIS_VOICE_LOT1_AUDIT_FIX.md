# Audit & correctif Mode Vocal IRIS — Lot 1 (Fonctionnel)

Date : 28 juin 2026 · Branche : `feature/sprint-a-ux` · **Non déployé** (validation Ludo requise)

## 1. Problème signalé
À l'ouverture du mode vocal, IRIS se met à parler la première et évoque un « panneau virtuel »,
ses limitations et d'anciennes fonctionnalités. Comportement « prototype ».

## 2. Causes identifiées (audit)
Ce n'est ni un cache ni une boucle de réinjection. Tout est codé en dur dans le prompt système et le bridge.

| # | Cause | Emplacement |
|---|---|---|
| 1 | Greeting auto à l'ouverture (force IRIS à parler en premier) | `luna_web.py` `_IRIS_GREETINGS` + `_send_greeting` (`web_voice_bridge.py`) |
| 2 | Prompt système `_IRIS_SYSTEM` 100 % « centre de commande / Iris Command Screen », force `iris_render` avant chaque réponse | `luna_web.py` `_IRIS_SYSTEM` |
| 3 | Q&R injectée en dur dans l'historique (« Oui j'ai l'Iris Command Screen… ») | `web_voice_bridge.py` `_configure_session` |
| 4 | Auto-correcteur qui force IRIS à affirmer qu'elle a un panneau quand elle le nie | `web_voice_bridge.py` `_auto_correct_denial` + détection déni |
| 5 | `tool_choice="required"` → un tool (iris_render) appelé à CHAQUE tour | `web_voice_bridge.py` `session.update` |
| 6 | Action Router qui force un rendu panneau si IRIS « promet » sans tool call | `web_voice_bridge.py` `_IrisActionRouter` |

## 3. Décisions (validées par Ludo)
- **Suppression totale** du panneau Iris Command Screen en mode vocal → voix pure (orbe + transcription).
- **Fonctionnel d'abord**, refonte UI premium ensuite (Lot 2).

## 4. Correctifs appliqués (Lot 1)
Approche : flag `command_screen: bool` sur `WebVoiceBridge` (défaut `True` → **voix Luna inchangée**).
Le handler `/ws/iris-voice` passe désormais `command_screen=False`.

Quand `command_screen=False` :
- **Silence à l'ouverture** : `_greeting = ""` → `_send_greeting` ne se déclenche jamais.
- **Nouveau prompt `_IRIS_SYSTEM`** : assistante IA du quotidien / secrétaire intelligente / copilote
  numérique. Reste silencieuse, ne parle jamais de panneau/écran/limites, ne se justifie jamais,
  répond uniquement à ce que dit l'utilisateur. Aucune référence à `iris_render`, aux modes, aux render_types.
- **`tool_choice="auto"`** (au lieu de `required`) : IRIS parle librement, n'appelle un outil que si utile.
- **Outils panneau retirés** du toolset : `iris_render`, `start_meeting`, `organize_kanban` → IRIS ne
  peut physiquement plus projeter de panneau. Outils utiles conservés : `search_web`, `get_news`,
  `get_weather`, `get_contacts`, `add_reminder`, `get_reminders`, `create_note`.
- **Désactivés** : Q&R d'ancrage, state-block panneau, contexte de mode, auto-bascule de mode,
  orchestrateur de rendu, détection/auto-correction du déni, Action Router, rendus à l'upload de document.

## 5. Fichiers modifiés
- `integrations/openai/web_voice_bridge.py` — flag `command_screen`, gardes sur tous les chemins panneau, filtrage des outils.
- `luna_web.py` — réécriture `_IRIS_SYSTEM`, greeting silencieux, `command_screen=False` sur le bridge Iris.

## 6. Vérifications
- `py_compile` OK sur les 2 fichiers.
- Test runtime : `command_screen=False` retire bien `iris_render`/`start_meeting`/`organize_kanban`,
  conserve les outils utiles. Voix Luna (`command_screen=True` par défaut) strictement inchangée.

## 7. Reste à faire
- **Validation Ludo** du comportement (test vocal réel) avant déploiement.
- **Lot 2 — Refonte UI premium** de `static/simli.html` : orbe vivant multi-états (écoute/réflexion/
  réponse/traitement/erreur/connexion), visualiseur audio réactif, transcription en carte typographiée
  (user vs IRIS distingués), fond profond, contrôles (mute/annuler/relancer/fermer/retour chat), 60 fps.
- Question de marque à trancher : l'app est nommée « MyLand » dans le brief mais « Luna/YAWatch » dans le
  code. Le prompt utilise « l'application » de façon neutre pour l'instant.
