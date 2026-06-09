# MISSION STATUS — Audit UX YAWatch-LUNA
**Dernière mise à jour** : 2026-06-09  
**Responsable** : Kimi (Auditeur UX / Terrain)

---

## OBJECTIF GLOBAL

Mettre en place un audit UX automatique post-déploiement pour Iris Workspace.

Pipeline cible :
```
Déploiement Cloud Run
    ↓
Playwright → Screenshots
    ↓
GPT-4o Vision → Rapport UX
    ↓
Claude → Correctifs
    ↓
Nouveau déploiement
```

---

## ÉTAT ACTUEL

| Phase | Statut | Responsable |
|---|---|---|
| 1. Vision produit | ✅ Gelée | Ludovic |
| 2. Architecture | ✅ Gelée | ChatGPT |
| 3. Audit UX (avant code) | ⏭️ À faire (prochaine feature) | Kimi |
| 4. Validation | ✅ Gelée | Ludovic |
| 5. Implémentation | ✅ Faite | Claude |
| 6. Audit terrain | ✅ **Fait** (2026-06-09) | Kimi |
| 7. Correctifs | ⏳ **En attente** | Claude |
| 8. Validation globale | ⏳ À faire | ChatGPT + Ludovic |

---

## LIVRABLES DE L'AUDIT (2026-06-09)

Dossier : `docs/audit_ux/2026-06-09/`

| Fichier | Description |
|---|---|
| `BRIEF_CORRECTION.md` | Brief de correction pour Claude (CRITIQUE/MAJEUR/MINEUR) |
| `audit_report.md` | Rapport UX complet généré par GPT-4o + enrichissement Kimi |
| `screenshots/*.png` | 6 captures du workflow déployé |

---

## PROBLÈMES DÉTECTÉS (résumé)

### 🔴 CRITIQUE
1. **Doublon `twActiveCard`** — Proposition active affichée en 3 endroits (header L2, carte canvas, section PROPOSITIONS)
2. **Empty state menteur** — Canvas référence un bouton "Proposition" supprimé de la barre d'actions

### 🟠 MAJEUR
3. **Canvas sous-utilisé** — Propositions éparpillées (canvas + section en bas)
4. **Stepper illisible** — 13 étapes en points minuscules

### 🟡 MINEUR
5. **"BRIEF MISSION" persistant** après validation du brief
6. **"IRIS AUDIO"** = distraction de navigation en session

---

## COMMANDE D'AUDIT (à exécuter après chaque déploiement)

```bash
source /tmp/browser_use_env/bin/activate && \
IRIS_AUDIT_URL="https://luna-beta-674304336025.europe-west1.run.app/team?room=audit-$(date +%Y%m%d-%H%M%S)" \
python /tmp/iris_audit/yawatch_audit.py && \
python /tmp/iris_audit/analyze_with_gpt4o.py
```

**Résultat** : Screenshots dans `/tmp/iris_audit/YYYYMMDD_HHMMSS/` + rapport dans `/tmp/iris_audit/audit_report.md`

---

## PROCHAINES ACTIONS

1. **Claude** corrige les écarts dans `static/team_workspace.html` (voir `BRIEF_CORRECTION.md`)
2. **Kimi** relance l'audit terrain après le correctif
3. **ChatGPT** valide la cohérence globale
4. **Ludovic** donne le feu vert pour passer à la feature suivante

---

## RÔLES OFFICIELS (à conserver en mémoire)

| IA | Rôle |
|---|---|
| **ChatGPT** | Architecte produit — Vision, workflow, objets métier |
| **Kimi** | Auditeur UX / Terrain — Screenshots, doublons, hiérarchie visuelle |
| **Claude** | Implémentation — Code, patchs, stabilité |
| **Ludovic** | Product Owner — Décisions finales, validation |
