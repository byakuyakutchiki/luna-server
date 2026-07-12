# Kimi — Patch coupe-circuit SMS Guardian

Date : 2026-06-17
Agent : Kimi
Type : patch technique / sécurité SMS
Niveau : 2 (correction de cohérence, pas d'urgence de forfait)

---

## Contexte

La variable `GUARDIAN_SMS_ENABLED=false` est posée sur Cloud Run (`luna-beta-00684-zfr`) pour bloquer les SMS d'urgence (Guardian, SOS famille, alertes contacts urgence) en environnement beta/staging sans couper les autres SMS (invitations, OTP, comptes-rendus d'appel...).

## Problèmes corrigés

1. **Faux positif du coupe-circuit** : `_tracked_sms_send()` retournait `True` quand le SMS était bloqué. Les appelants comptaient le SMS comme "envoyé" et l'API retournait "SOS envoyé à N contact(s)" alors qu'aucun SMS réel n'était parti.
2. **Filtre sensible à la casse et trop étroit** : le test `"Guardian" in label` ne bloquait pas un label écrit en minuscules (`"alerte guardian"`) ni les autres alertes d'urgence (`"Alerte SOS"`, `"Alerte contacts urgence"`).
3. **Documentation / état désynchronisés** : `.env.example` ne documentait pas la variable ; `ETAT_ACTUEL.md` indiquait encore l'ancienne révision Cloud Run (`00680-fhz` au lieu de `00683-p7v`).
4. **Test P0 obsolète** : le test de grace period attendait 2h alors que le code en met 30 min ; aucun test ne couvrait le coupe-circuit SMS.
5. **Bug cleanup tracking SMS** : `_cleanup_sessions()` utilisait `_ts` pour détecter les SMS stale, mais `_tracked_sms_send()` ne stockait jamais `_ts`. Tous les SMS tracking étaient supprimés dès le premier cleanup.
6. **SMS compte-rendu d'appel en dehors du pipeline** : `luna_web.py:9148` appelait `sms_client.send()` directement, sans test mode, sans tracking, sans garde-fou.
7. **Log faux positif SMS d'annulation** : `core/guardian/engine.py` loguait « SMS d'annulation envoyé à X contact(s) » sans vérifier si le coupe-circuit les avait bloqués.
8. **`_tracked_sms_send` fragile** : plantait si `sms_client` était `None` (Twilio non configuré).

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `luna_web.py` | `_tracked_sms_send()` : filtre insensible à la casse + flag `blocked: True` + robustesse `sms_client=None` + stockage `_ts` ; SMS compte-rendu d'appel routé via `_tracked_sms_send` ; `guardian_location()` et `guardian_sos()` exposent `guardian_sms_enabled` / `sms_blocked` |
| `core/guardian/alerts.py` | `send_guardian_alerts()` distingue `sent`, `failed` et `blocked` ; ne compte plus un SMS bloqué comme envoyé |
| `core/guardian/engine.py` | Log SMS d'annulation corrige (envoyes / bloques / echoues) |
| `tests/test_guardian_p0.py` | Ajout TEST 8 (coupe-circuit SMS Guardian) ; correction du test grace period (30 min) |
| `.env.example` | Documentation de `GUARDIAN_SMS_ENABLED` |
| `docs/AGENTS_COLLABORATION/ETAT_ACTUEL.md` | Mise à jour de la révision Cloud Run (`luna-beta-00683-p7v`) |

## Validation

- `python3 -m py_compile luna_web.py core/guardian/engine.py core/guardian/alerts.py tests/test_guardian_p0.py` ✅
- `python3 tests/test_guardian_p0.py` → 45/45 PASS ✅

## Notes

- Les SMS non-urgence (invitations visio, OTP famille, comptes-rendus d'appel, etc.) ne sont pas affectés.
- Les DM Luna (`send_guardian_dm_alerts`) continuent de partir même si `GUARDIAN_SMS_ENABLED=false` ; c'est le comportement attendu car le coupe-circuit concerne uniquement les SMS.
- Pour réactiver les SMS d'urgence en prod : `gcloud run services update luna-beta --update-env-vars GUARDIAN_SMS_ENABLED=true` (validation Ludovic requise avant déploiement).
