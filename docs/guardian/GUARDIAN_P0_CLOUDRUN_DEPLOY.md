# Guardian P0 — Déploiement Cloud Run
**Date : 15 juin 2026 — 21h51 UTC**
**Révision : `luna-beta-00658-rwj`**
**Branch : `feature/sprint-a-ux`**

---

## Commits inclus (vérifiés avant déploiement)

| Commit | Description |
|---|---|
| `985e831` | docs(guardian): P0 terrain validation guide ✅ |
| `21cd8d2` | fix(guardian): implement policy v2 p0 behavior rules ✅ |
| `2f08e93` | docs(guardian): policy implementation gap analysis + roadmap |
| `72a4447` | docs(guardian): GUARDIAN_BEHAVIOR_POLICY_V2 + decision tree |
| `cabba33` | audit(guardian): behavior policy review |

---

## Déploiement

```
Service   : luna-beta
Région    : europe-west1
Projet    : crypto-parser-475411-k4
Révision  : luna-beta-00658-rwj
URL       : https://luna-beta-674304336025.europe-west1.run.app
Trafic    : 100%
```

---

## Vérifications post-déploiement

```
GET /health → {"status": "ok"}                                    ✅
GET /ready  → {"status": "ready",
               "checks": {"redis": "ok",
                          "JWT_SECRET_KEY": "ok",
                          "OPENAI_API_KEY": "ok"}}               ✅
```

Redis, JWT et OpenAI opérationnels.

---

## Action obligatoire : recréer la session Guardian

Les sessions Guardian stockées en Redis avant ce déploiement **ne contiennent pas `night_mode: True`** dans leur config. Elles ont été créées avec l'ancienne config (`_default_config()` sans `night_mode`).

**Sans cette action :** P0-01 (mode nuit) ne s'active pas sur les sessions existantes malgré le nouveau code.

**Procédure :**
1. Ouvrir l'app Guardian
2. Arrêter la session active (bouton "Arrêter")
3. Redémarrer une nouvelle session

La nouvelle session sera créée avec `_default_config()` mis à jour qui inclut `night_mode: True` pour SENIOR et BABY.

---

## Ce que ce déploiement change en production

| Comportement | Avant | Après |
|---|---|---|
| Dormir la nuit en safe zone | Alerte après 30 min | Silence total 23h–7h |
| BABY en sieste | Alerte après 5 min | Silence jusqu'à 120 min |
| Timeout vérification | 2 min | 10 min |
| SMS après "tout va bien" | Aucun | SMS d'annulation automatique |
| Spam SMS | Illimité (toutes les 5 min) | Max 3/24h + backoff 30→60→120 min |
| Après "tout va bien" | Nouvelle alerte immédiate possible | Grace period 2h |

---

## Révision précédente

`luna-beta-00078-nmt` (v38-tavus-cinema — dernière avant Sprint B/Guardian P0)

---

*Déploiement réalisé sans modification fonctionnelle. Seul le comportement Guardian est modifié.*
