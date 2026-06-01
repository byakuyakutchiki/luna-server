# Objectif 017 — Banc de test réel téléphone

Date : 2026-06-01  
Propriétaire : Ludovic  
Coordinateur : Claude  
Validateurs : Codex (terrain), Kimi (UX), DeepSeek (audit risques)

---

## But

Créer un accès de preuve téléphone partageable entre les 4 IAs via GitHub,  
sans casser l'app, sans actions sensibles, sans exposer de secrets.

---

## Contraintes absolues

- ❌ Pas de SMS, appel, email, paiement, réservation
- ❌ Pas de test Simli long (> 30s)
- ❌ Pas d'ouverture de port public
- ❌ Pas de clés API dans les captures
- ✅ Captures push GitHub = seul mode de partage validé

---

## Preuves à capturer par session

| Fichier | Commande ADB | Contenu |
|---|---|---|
| `adb_devices.txt` | `adb devices` | Statut connexion |
| `screen.png` | `adb exec-out screencap -p` | Screenshot |
| `logcat_tail.txt` | `adb logcat -d -v time \| tail -200` | Logs récents |
| `app_info.txt` | `adb shell dumpsys package com.luna.app` | Version APK |

---

## Dossier de preuves

```
docs/AGENTS_COLLABORATION/phone_tests/<YYYY-MM-DD_HH-MM>/
├── adb_devices.txt
├── screen.png
├── logcat_tail.txt
└── app_info.txt
```

---

## Script de capture

`tools/agents/phone_snapshot.sh` — à lancer depuis la VM Linux (ADB disponible).

---

## Accès Codex depuis Windows

Codex ne peut pas accéder à ADB directement (USB sur VM Linux).  
Seul accès autorisé : **consulter les captures pushées sur GitHub**.

Option avancée (non activée) : ADB over TCP — documenter si besoin.

---

## Rapport de chaque IA

Chaque IA publie dans `docs/AGENTS_COLLABORATION/agents/` :
- `CLAUDE_PHONE_ACCESS_017.md` — capture + diagnostic
- `CODEX_PHONE_REVIEW_017.md` — lecture captures GitHub
- `KIMI_PHONE_UX_017.md` — audit UX depuis captures
- `DEEPSEEK_PHONE_RISK_017.md` — audit risques
