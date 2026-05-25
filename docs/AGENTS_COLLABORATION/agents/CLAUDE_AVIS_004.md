# Avis Claude — Objectif 004

Agent : Claude (claude-sonnet-4-6)
Date : 2026-05-25
Rôle : Synthèse des 4 agents + décision d'architecture finale

---

## Lecture des avis reçus

| Agent | Fichier | Contribution |
|---|---|---|
| Codex | `OBJECTIF_004_API_FONDATEUR_DIAGNOSTIC.md` | Cadrage : 4 niveaux d'action, exclusions, rôles |
| DeepSeek | `DEEPSEEK_AVIS.md` | Schéma `_analyze_apk_state()`, action_level strings, 9 cas de test |
| Kimi | `KIMI_AVIS_004.md` | 16 textes audités, 6 reformulés, table "sait / suppose / ne sait pas" |
| Cursor | *(attendu)* | Cohérence UI fondateur.html / endpoints |

---

## Ce que je valide sans modification

### Schéma DeepSeek — adopté

```python
{
    "status": "ok" | "warning" | "critical" | "degraded",
    "diagnosis": str,          # code court : "heartbeat_old", "apk_version_obsolete"...
    "probable_cause": str,     # phrase humaine
    "recommended_action": str, # phrase actionnable
    "action_level": str,       # voir tableau ci-dessous
    "can_auto_fix": bool,
    "evidence": dict,          # données brutes limitées
}
```

### Niveaux d'action — noms DeepSeek conservés

| `action_level` | Niveau | Autorisé |
|---|---|---|
| `info_only` | 0 | Toujours |
| `safe_local_action` | 1 | Toujours, sans confirmation |
| `manual_validation_required` | 2 | Après test heartbeat réel, bouton Ludovic |
| `forbidden_without_claude_ludo` | 3 | Jamais automatique |

### Textes Kimi — adoptés pour l'affichage fondateur

Règle retenue : **Luna dit ce qu'elle sait, distingue ce qu'elle suppose, avoue ce qu'elle ignore.**

Exemple validé :
```
APK Fondateur — Attention
Téléphone vu il y a 4 min.
Luna observe : l'APK v2.7 est active, mais v2.8 est attendue.
Luna suppose : l'ancienne version est encore installée.
Luna recommande : installer la dernière APK depuis le lien ci-dessous.
Luna ne peut pas : faire cette mise à jour automatiquement.
```

---

## Mes décisions d'architecture

### 1. Statut `waiting_first_contact` ajouté

DeepSeek et Kimi ont tous deux souligné que "heartbeat absent = critical" est anxiogène avant le premier rebuild APK. J'ajoute un statut intermédiaire :

```python
if not heartbeat:
    # Jamais vu = situation normale avant premier rebuild
    status = "waiting_first_contact"
    diagnosis = "no_heartbeat_yet"
    action_level = "info_only"
```

`critical` sera réservé à : heartbeat déjà reçu, puis perdu depuis > 24h.

### 2. Journal Redis — écriture conditionnelle

Pour éviter le bruit (Kimi a signalé ce risque), le journal n'écrit que si :
- le statut change (ok → warning, warning → critical, etc.)
- ou si > 10 minutes se sont écoulées depuis la dernière entrée

Clé : `luna:founder:actions:log` — liste, max 200 entrées, TTL 30 jours.

### 3. Cas de test Phase 1 uniquement

DeepSeek propose 9 cas, dont `ws_voice_disconnected` et `no_audio_detected`. Ces deux-là sont Phase 2 (données voix non encore collectées). Phase 1 se limite à :

| Cas | Status | Diagnosis |
|---|---|---|
| Jamais de heartbeat | `waiting_first_contact` | `no_heartbeat_yet` |
| Heartbeat < 2h | `ok` | `apk_alive` |
| Heartbeat entre 2h et 24h | `warning` | `heartbeat_old` |
| Heartbeat > 24h | `critical` | `heartbeat_lost` |
| URL Cloud Run différente | `warning` | `cloudrun_url_mismatch` |
| Version APK inconnue | `warning` | `apk_version_unknown` |
| Version APK < attendue | `warning` | `apk_version_obsolete` |
| Redis indisponible | `degraded` | `redis_unavailable` |

### 4. API à exposer

- `GET /api/admin/apk-diagnosis` — auth fondateur, retourne diagnostic courant + derniers logs
- Intégration dans `/api/admin/objectives` déjà faite (section APK Fondateur)
- `fondateur.html` : section dans l'onglet Objectifs, pas un nouvel onglet

### 5. Ce que je n'implémente pas maintenant

- Actions niveau 2 (forcer refresh WebView, vider cache) : après test heartbeat réel sur téléphone
- Actions niveau 3 : jamais automatiques
- Diagnostics voix (ws_voice, audio_sent, audio_received) : Phase 2 seulement

---

## Implémentation prévue (après validation Ludovic)

```
luna_web.py
├── _analyze_apk_state(heartbeat: dict | None) -> dict
├── _write_founder_action_log(entry: dict) -> None
└── GET /api/admin/apk-diagnosis

fondateur.html
└── section "APK Fondateur" dans onglet Objectifs (textes Kimi)
```

Aucun changement `MainActivity.java` ni Cloud Run pour cette phase.

---

## Questions en attente de Ludovic

1. **Niveau 1 autorisé sans confirmation** ? (ex: afficher lien APK, proposer réouverture) → oui ou bouton quand même ?
2. **Journal 30 jours** → validé ?
3. **`waiting_first_contact`** plutôt que `critical` avant le premier rebuild → tu confirmes ?

Dès que tu valides ces 3 points, j'implémente `_analyze_apk_state()` et `/api/admin/apk-diagnosis`.

---

*Claude — 2026-05-25*
