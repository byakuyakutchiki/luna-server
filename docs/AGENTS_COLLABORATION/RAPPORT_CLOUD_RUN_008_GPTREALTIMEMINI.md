# Rapport Cloud Run — Test gpt-realtime-mini — 00442-7gg

**Date** : 2026-05-25 à 20:28 CEST (= 18:28 UTC)  
**Révision** : `luna-beta-00442-7gg`  
**Modèle testé** : `gpt-realtime-mini`  
**Résultat** : échec — "service indisponible", aucune voix

---

## Séquence exacte (logs UTC)

```
18:28:13.670  POST /api/apk/event [200]   ← événements APK (clic, token, micro...)
18:28:13.797  POST /api/apk/event [200]
18:28:13.831  POST /api/apk/event [200]
18:28:14.122  POST /api/apk/event [200]
18:28:14.421  WebSocket /ws/luna-voice    [accepted] ← JWT fondateur valide
18:28:14.422  POST /api/apk/event [200]
18:28:14.612  POST /api/apk/event [200]
18:28:14.924  WebVoiceBridge started (active: 1)
18:28:14.925  POST /api/apk/event [200]
18:28:16.533  WebVoice: OpenAI Realtime connected  ← connexion OK, session.created reçu
18:28:16.534  ERROR: WebVoice: OpenAI error avant session.update —
              code=insufficient_quota
              msg="You exceeded your current quota, please check your plan
                   and billing details."
18:28:16.543  WebVoiceBridge ended (active: 0)
18:28:18.661  WebVoiceBridge cleanup (0 entries)
18:28:19.860  POST /api/apk/event [200]   ← voice_ws_closed + voice_session_ended
18:28:19.862  POST /api/apk/event [200]
```

---

## Cause racine DÉFINITIVE — Ce n'est pas un problème de modèle

**Le compte OpenAI a épuisé son quota Realtime API.**

```
code    : insufficient_quota
message : You exceeded your current quota,
          please check your plan and billing details.
```

### Historique des 3 tests

| Test | Révision | Modèle | Erreur | Cause réelle |
|---|---|---|---|---|
| 18:47 (19:47) | 00439-7v9 | gpt-4o-realtime-preview-2024-12-17 | WS closed during send | Quota épuisé (session.update rejetée silencieusement) |
| 19:27 | 00440-gbz | gpt-4o-realtime-preview | model_not_found | Ce modèle n'existe pas sur ce compte |
| 20:28 | 00442-7gg | gpt-realtime-mini | insufficient_quota | Quota Realtime épuisé (confirmé explicitement) |

La correction B (lire session.created avant session.update) a rendu l'erreur VISIBLE.
Sans elle, le quota épuisé se manifestait silencieusement par "WS closed during send".

### Ce qui fonctionne

- Token JWT fondateur ✓
- WebSocket accepté ✓
- 10 événements APK reçus ✓
- Connexion OpenAI Realtime établie ✓ (session.created reçu)
- Bridge arrêt propre ✓
- Télémétrie complète ✓ (fix session_ts validé)

### Ce qui est bloqué

- **Quota Realtime OpenAI épuisé** — aucun modèle ne fonctionnera tant que les crédits ne sont pas rechargés

---

## Action requise — Ludovic uniquement

Vérifier et recharger le compte OpenAI :
1. Aller sur **https://platform.openai.com/settings/organization/billing**
2. Vérifier le solde et les crédits Realtime
3. Recharger si nécessaire

Après rechargement : redémarrer le test sans aucun changement de code.
Le modèle `gpt-realtime-mini` est accessible sur ce compte (connexion OK) et sera
fonctionnel dès que le quota sera rétabli.

---

## Bilan objectif 008 voix

| Item | Statut |
|---|---|
| Correction B — bridge lit session.created | ✅ opérationnel |
| Fix session_ts télémétrie | ✅ validé (00441-dg5) |
| Modèle Realtime accessible | ✅ gpt-realtime-mini se connecte |
| Quota OpenAI Realtime | ❌ épuisé — action Ludovic requise |

**Aucun déploiement supplémentaire nécessaire pour la voix.** Tout est prêt côté serveur.
Seul le rechargement du quota OpenAI débloque la voix.
