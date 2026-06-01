# Claude — ADB Bridge Codex — Objectif 017

Agent : Claude  
Objectif : 017  
Date : 2026-06-01  
Type : validation  

---

**Agent :** Claude  
**Objectif :** 017  
**Type :** validation  
**Résumé :** ADB TCP activé sur le téléphone (192.168.1.98:5555). Codex peut se connecter depuis Windows avec `adb connect 192.168.1.98:5555`. Testé depuis la VM : `device` confirmé. Réseau local uniquement — aucun port public exposé.  
**Fichier concerné :** config ADB temporaire (volatile, pas de fichier modifié)  
**Risque :** Faible — port 5555 accessible sur le Wi-Fi local uniquement (192.168.1.x), pas routé vers Internet  
**Décision Ludovic requise :** Non  
**Action proposée :** Codex lance `adb connect 192.168.1.98:5555` → accès direct au téléphone depuis Windows  

---

## Commande pour Codex (Windows)

```powershell
& "C:\Users\saint\Documents\Codex\tools\android-platform-tools\platform-tools\adb.exe" connect 192.168.1.98:5555
& "C:\Users\saint\Documents\Codex\tools\android-platform-tools\platform-tools\adb.exe" devices
```

Résultat attendu :
```
connected to 192.168.1.98:5555
List of devices attached
192.168.1.98:5555    device
```

---

## Détails techniques

| Champ | Valeur |
|---|---|
| Téléphone IP Wi-Fi | `192.168.1.98` (wlan0) |
| Port ADB TCP | `5555` |
| Réseau | 192.168.1.0/24 (local uniquement) |
| Testé depuis VM | `connected to 192.168.1.98:5555` ✅ |

---

## Ce que Codex peut faire une fois connecté

```powershell
# Screenshot
& adb.exe exec-out screencap -p > screen.png

# Logcat filtré Luna
& adb.exe logcat -d -v time | Select-String "luna|WebView|speech|microphone"

# Info app
& adb.exe shell dumpsys package fr.yawatch.luna | Select-String "versionName|lastUpdate"
```

## ⚠️ Règles

- Ne pas cliquer dans l'app via `adb shell input tap`
- Ne pas déclencher SMS/appel/paiement
- Ne pas faire de session visio longue (< 30s)
- Désactiver ADB TCP après les tests : `adb usb`

---

## Désactivation ADB réseau (Claude, depuis la VM)

Une fois les tests Codex terminés, Ludovic demande à Claude :
```bash
adb -s 192.168.1.98:5555 usb
```
Ou directement depuis la VM pour repasser en USB uniquement.
