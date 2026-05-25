# Rapport Sentry — Objectif 008

**Statut** : partiellement rempli (Sentry API non accessible sans auth token — voir ci-dessous)
**Source** : Sentry Free Ludovic + Cloud Run logs  
**Règle** : données filtrées uniquement, aucun secret  
**Mis à jour** : 2026-05-25 par Claude

---

## Accès Sentry

Le DSN Sentry est configuré dans `.env` Cloud Run (collecte active, masqué ici).
Il n'y a pas de **Sentry Auth Token** dans `.env` — Claude ne peut pas interroger
l'API Sentry sans lui.

Pour que Claude ou un autre agent lise Sentry :
- Ludovic crée un token sur **Sentry → Settings → Auth Tokens** (scope : read)
- Ajoute `SENTRY_AUTH_TOKEN=...` dans `.env` local (pas dans GitHub)
- OU fournit une capture d'écran filtrée des erreurs pertinentes

---

## Ce que Cloud Run montre (substitut partiel à Sentry)

### Test téléphone — 2026-05-25 à 19:27 CEST (= 17:27 UTC)

Séquence exacte extraite des logs Cloud Run (révision `luna-beta-00440-gbz`) :

```
17:27:55.669  POST /api/apk/event [200]   ← voice_click_received (estimé)
17:27:55.733  POST /api/apk/event [200]   ← voice_token_present (estimé)
17:27:55.793  POST /api/apk/event [200]   ← voice_start_entered (estimé)
17:27:55.794  POST /api/apk/event [200]   ← voice_micro_request_started (estimé)
17:27:56.531  POST /api/apk/event [200]   ← voice_capture_started (estimé)
17:27:56.578  WebSocket /ws/luna-voice    [accepted] ← JWT fondateur valide
17:27:56.701  POST /api/apk/event [200]   ← voice_ws_create_started (estimé)
17:27:56.900  WebVoiceBridge started (active: 1)
17:27:57.109  POST /api/apk/event [200]   ← voice_ws_opened (estimé)
17:27:57.109  POST /api/apk/event [200]   ← événement supplémentaire
17:27:57.731  WebVoice: OpenAI Realtime connected
17:27:57.731  ERROR: WebVoice: OpenAI error avant session.update —
              code=model_not_found
              msg="The model `gpt-4o-realtime-preview` does not exist
                   or you do not have access to it."
17:27:57.737  WebVoiceBridge ended (active: 0)
17:27:59.859  WebVoiceBridge cleanup (0 entries)
17:28:00.929  POST /api/apk/event [200]   ← voice_session_ended (estimé)
17:28:02.218  POST /api/apk/event [200]   ← voice_ws_closed (estimé)
```

Note : les noms d'événements APK sont estimés par ordre chronologique standard.
Sentry ou un log Redis détaillé permettrait de les confirmer.

### Ce que Sentry devrait contenir (à vérifier)

| Zone | Type attendu | Heure Europe/Paris |
|---|---|---|
| Frontend JS (WebView) | Erreur JS — WS fermé prématurément | ~19:27:57 |
| Frontend JS (WebView) | Éventuellement : erreur handler `{"type":"error"}` | ~19:27:57 |
| Python server | Peut-être rien (bridge gère proprement) | ~19:27:57 |
| UI mobile | Éventuel repaint / overflow bouton Déconnexion | à déterminer |

---

## Entrées Sentry confirmées

| Heure Europe/Paris | Projet | Message | Fichier/Route | Hypothèse | Action recommandée |
|---|---|---|---|---|---|
| À confirmer via auth token ou capture | — | — | — | — | — |

---

## Deux bugs identifiés (Cloud Run, pas encore Sentry)

### Bug 1 — Modèle Realtime inaccessible (BLOQUANT voix)

L'alias `gpt-4o-realtime-preview` donne `model_not_found` sur ce compte OpenAI.
La version datée `gpt-4o-realtime-preview-2024-12-17` se connectait (session.created
reçu) mais OpenAI fermait le WS pendant `session.update`.

Hypothèse : l'alias pointe vers une version 2025+ non accessible sur le tier actuel.
Action recommandée : tester `gpt-4o-realtime-preview-2024-10-01` ou `gpt-4o-mini-realtime-preview`. Décision Ludovic requise avant déploiement.

### Bug 2 — Régression session_ts télémétrie (BLOQUANT cockpit)

La correction B envoie `{"type":"error"}` au client → JS appelle `stopVoice()` →
reset `_voiceSessionStartTs = 0` → puis `onclose` fire → `voice_ws_closed` envoyé
avec `session_ts = 0` → micro-session orpheline → cockpit n'affiche qu'un événement.

Les 10 événements APK arrivent bien au serveur (confirmé : 10 × POST [200]).
C'est l'analyse / l'affichage qui les sépare.

Action recommandée : fix dans `index.html` — envoyer `voice_ws_closed` depuis
`onclose` avant d'appeler `stopVoice()`, ou déplacer le reset dans `onclose`.
Décision Ludovic requise avant déploiement.

### Bug 3 — UI mobile : bouton "Déconnexion" coupé (RÉGRESSION UI)

Constaté après les changements récents. Tracé séparément.
Voir `docs/AGENTS_COLLABORATION/BUG_UI_MOBILE_DECONNEXION.md`.

---

## Ce que Sentry ajouterait à cette analyse

- Noms exacts des événements APK reçus (confirmer les estimés ci-dessus)
- Stack trace JS si le handler d'erreur lève une exception dans WebView
- Confirmation que `stopVoice()` est appelé avant `onclose` (timing exact)
- Erreurs CSS/layout pour le bug bouton Déconnexion
- Éventuellement : messages réseau supplémentaires non logués côté serveur

---

## Données à ne jamais copier dans GitHub

- token Sentry, DSN, clé auth
- cookie de session
- clé API OpenAI, Twilio, Tavus
- email privé utilisateur
- contenu audio ou transcript
- identifiant personnel non nécessaire
