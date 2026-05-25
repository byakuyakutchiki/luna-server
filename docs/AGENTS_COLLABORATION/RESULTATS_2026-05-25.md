# Résultats journée — 2026-05-25

**Auteur** : Claude  
**Validateur** : Ludovic (tests téléphone réel)

---

## Objectif 006 — Heartbeat APK ✅ VALIDÉ

**Problème** : `/api/apk/heartbeat` retournait 401 — bloqué par le middleware d'auth.  
**Fix** : ajout de `/api/apk/heartbeat` dans `_PUBLIC_PATHS` (`luna_web.py`).  
**Commit** : `ce26b5e`  
**Résultat** : téléphone fondateur vu en temps réel dans le cockpit.

---

## Objectif 007 — Télémétrie vocale APK ✅ VALIDÉ

**Problème** : seul `voice_session_ended` apparaissait dans le cockpit — les autres événements se dispersaient en micro-sessions.  
**Causes** :
1. `session_ts = 0` est falsy en Python → chaque événement créait sa propre session
2. `_apkEventCount >= 10` trop bas (19 événements nécessaires)
3. `_voiceStartTime` non défini au moment du clic → `session_ts = 0`

**Fix** :
- Nouveau `_voiceSessionStartTs` fixé au clic avant tout `sendApkEvent()`
- Plafond porté à 30
- Fix groupement Python : `raw_sid != 0 and raw_sid != "0"`
- 19 événements instrumentés dans `index.html`
- `luna_web.py` : 21 événements autorisés, 28 labels français, 7 scénarios

**Commit** : `01ac7a5`  
**Résultat** : 11 événements reçus sur test téléphone réel Ludovic — chronologie complète.

---

## Objectif 008 — Correction voix OpenAI Realtime ✅ VALIDÉ

**Problème** : Luna muette — le WS OpenAI se fermait pendant `_configure_session()`.

**Diagnostics successifs** :
- `gpt-4o-realtime-preview-2024-12-17` : WS fermé pendant `session.update` (quota épuisé silencieux)
- `gpt-4o-realtime-preview` : `model_not_found` — ce modèle n'existe plus sur ce compte
- `gpt-realtime-mini` : `insufficient_quota` (rate limit temporaire) → OK après délai

**Corrections déployées** :
| Correction | Commit | Révision |
|---|---|---|
| Correction B : bridge lit `session.created` avant `session.update` | `97d2f82` | 00440-gbz |
| Fix régression `session_ts` (`_voiceWsClosedSent`) | `aa12e0e` | 00441-dg5 |
| Modèle `gpt-realtime-mini` | `.env` local | 00442-7gg |

**Révision active** : `luna-beta-00442-7gg`  
**Résultat** : Ludovic entend la voix de Luna sur téléphone réel (~20h30 CEST).

**Cause finale quota** : le compte OpenAI avait $9.90 de crédit — pas un problème de solde. C'était un rate limit temporaire Realtime épuisé par les tests répétés.

---

## Objectif 009 — Stabilité voix (ouvert)

**Constat** : Luna s'arrête parfois de parler seule mid-response.  
**Suspect principal** : VAD barge-in — micro actif pendant playback, écho acoustique → `response.cancel`.  
**Bug secondaire** : `vad_eagerness` accepté en paramètre mais jamais transmis à `session.update`.  
**En attente** : test téléphone Ludovic avec heure exacte → lecture logs Cloud Run.

---

## Infrastructure mise en place

| Élément | Statut |
|---|---|
| Sentry tracé dans le cerveau Luna (lecture filtrée) | ✅ |
| `NOTE_SENTRY_CERVEAU_LUNA.md` | ✅ |
| Architecture DeepSeek temps réel APK cadrée | ✅ |
| `OBJECTIF_008_DEEPSEEK_TEMPS_REEL_APK.md` | ✅ |
| `CLAUDE_AVIS_008_INTEGRATION_DEEPSEEK.md` | ✅ |
| Bug UI mobile bouton "Déconnexion" coupé tracé | ✅ `BUG_UI_MOBILE_DECONNEXION.md` |
| Rapports Cloud Run 008 centralisés | ✅ |

---

## Modèles OpenAI Realtime disponibles sur ce compte

```
gpt-realtime          (alias principal)
gpt-realtime-mini     (actif — 00442-7gg)
gpt-realtime-1.5
gpt-realtime-2
gpt-realtime-2025-08-28
gpt-realtime-mini-2025-10-06
gpt-realtime-mini-2025-12-15
gpt-realtime-translate
gpt-realtime-whisper
```

Les anciens `gpt-4o-realtime-preview-*` ne sont plus accessibles sur ce compte.

---

## Règles établies / rappels

- Branches DeepSeek/Kimi : **jamais merger directement** — prendre docs uniquement
- `OPENAI_API_KEY` : jamais modifiée sans validation Ludovic
- Déploiement : `bash deploy.sh` — validé par Ludovic avant exécution
- Sentry : lecture filtrée uniquement, aucun secret dans GitHub
- DeepSeek : clé côté serveur uniquement, jamais dans l'APK
- Quota Realtime : rate limit temporaire → attendre avant de retester

---

## Prochaines actions

| Priorité | Action | Responsable |
|---|---|---|
| 1 | Test téléphone 009 + heure exacte | Ludovic |
| 2 | Logs Cloud Run 009 → confirmer VAD barge-in | Claude |
| 3 | Correction VAD (threshold 0.8 si confirmé) | Claude → validation Ludovic |
| 4 | `DEEPSEEK_AVIS_008_TEMPS_REEL_APK.md` | DeepSeek |
| 5 | Intégration serveur DeepSeek (`/api/deepseek/diagnose`) | Claude (après avis DeepSeek) |
| 6 | Bug UI mobile bouton Déconnexion | Claude (branche isolée) |
| 7 | Comparaison `gpt-realtime` vs `gpt-realtime-mini` pour qualité voix | Après 009 stable |
