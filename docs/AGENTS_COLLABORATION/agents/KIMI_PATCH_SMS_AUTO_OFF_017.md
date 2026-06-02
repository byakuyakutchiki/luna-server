# Kimi — Patch arret SMS automatiques — Urgence forfait Twilio

Date : 2026-06-02
Agent : Kimi
Type : patch urgence / couts
Niveau : 1 (desactivation immediate demandee par fondateur)

---

## Probleme

Forfait Twilio de Ludovic bouffe par des SMS automatiques de rappels d'objectifs/missions.
Les SMS partaient sans action explicite de l'utilisateur.

---

## Sources coupees

| Fichier | Ligne | Description | Raison |
|---|---|---|---|
| `core/notifications/engine.py` | 237-247 | `_deliver()` envoyait SMS pour `streak_risk`, `reminder`, `alert` vers `ADMIN_PHONE` | Notification auto sans action utilisateur |
| `core/instructions/executor.py` | 313-325 | `_handle_reminder()` envoyait SMS a chaque rappel d'instruction vers `subscriber_phone` | Rappel auto sans action utilisateur |

---

## Ce qui reste actif

| Source | Statut | Justification |
|---|---|---|
| `core/safety/emergency_handler.py` | ✅ Actif | Urgence seulement |
| `core/guardian/alerts.py` | ✅ Actif | Alerte securite seulement |
| Tool `send_sms` explicite (LLM/user) | ✅ Actif | Action demandee explicitement |
| Invitation visio par SMS | ✅ Actif | Action demandee explicitement |
| `core/cortex/briefing.py` | ✅ Actif | Rapports fondateur/exploitant (frequence faible) |

---

## Patch applique

Les blocs SMS automatiques sont commentes avec explication :
```
# DESACTIVE temporairement : consommation excessive forfait Twilio (2026-06-02)
# Reactivation uniquement sur demande explicite Ludovic avec garde-fou frequence.
```

Les rappels restent disponibles **in-app** (notification push/dans l'application).
Seul le canal SMS a ete coupe.

---

## Reactivation future

Si Ludovic veut reactiver les SMS de rappel :
1. Ajouter un garde-fou de frequence stricte (max 1 SMS/semaine par type)
2. Option utilisateur explicite "Autoriser les SMS de rappel"
3. Capping budget Twilio mensuel avec alerte a 80%
4. Validation Kimi/DeepSeek du nouveau garde-fou

---

*Urgence traitee sur demande directe Ludovic.*
