# Claude — Phone Access — Objectif 017

Agent : Claude  
Objectif : 017  
Date : 2026-06-01  
Type : validation  

---

## Format obligatoire

**Agent :** Claude  
**Objectif :** 017  
**Type :** validation  
**Résumé :** Téléphone Xiaomi (Android 16, SDK 36) connecté en ADB depuis la VM Linux. Luna v2.8 installée. WebView Chrome 148. Captures screen/logcat/app_info générées et prêtes pour push GitHub. Aucune action sensible effectuée. Script réutilisable créé.  
**Fichier concerné :** `docs/AGENTS_COLLABORATION/phone_tests/2026-06-01_18-11/`  
**Risque :** Faible — capture observe uniquement, aucun déclenchement d'action  
**Décision Ludovic requise :** Non  
**Action proposée :** Push sur GitHub → Codex/Kimi/DeepSeek consultent les preuves directement sur le repo  

---

## Preuves capturées

| Fichier | Taille | Contenu |
|---|---|---|
| `adb_devices.txt` | — | `c7750037  device` ✅ |
| `screen.png` | 278 Ko | Screenshot état actuel téléphone |
| `logcat_tail.txt` | 200 lignes | Logs système récents |
| `logcat_luna.txt` | filtré | Logs Luna/WebView/Speech uniquement |
| `app_info.txt` | — | Version APK + device + WebView |

---

## Informations téléphone

| Champ | Valeur |
|---|---|
| Appareil | Xiaomi 24115RA8EG |
| Android | 16 (SDK 36) |
| WebView | Google WebView 148.0.7778.178 |
| Chrome | 148.0.7778.215 |
| Luna | v2.8 (versionCode 19) — installé 2026-05-25 |

---

## Observations logcat

- Luna WebView charge correctement (`WebViewFactory loading 148.0.7778.178`)
- Aucun crash Luna détecté dans les logs
- APK en mode `verify` (non optimisé speed-profile) → performance peut être affectée
- Pas de log `SpeechRecognition` visible → le test terrain doit être lancé depuis la visio pour capturer ces logs

---

## Script de capture (réutilisable)

`tools/agents/phone_snapshot.sh` — à lancer depuis la VM :
```bash
cd ~/PROJETS/IA_WATCH/PROPRIO/serveur
./tools/agents/phone_snapshot.sh
```
Génère un nouveau dossier horodaté dans `phone_tests/`.

---

## Pour Codex — accès aux preuves

**Pas d'ADB depuis Windows** (USB sur VM Linux — pas partageable proprement sans risque).  
**Accès autorisé** : consulter les fichiers pushés sur GitHub :  
`byakuyakutchiki/luna-server` → `docs/AGENTS_COLLABORATION/phone_tests/`

---

## Prochaine capture recommandée

Capturer un logcat **pendant une session visio** pour voir :
- `speech_start`, `speech_err`, `total_latency_ms`
- Erreurs WebView (`getUserMedia`, `NotAllowedError`)

Commande :
```bash
adb logcat -v time | grep -iE "fr\.yawatch|luna|speech|microphone|visio|getUserMedia"
```
