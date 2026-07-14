# PHONE-ADB-SMOKE-001 — Rapport de verification ADB

- **mission_id**: PHONE-ADB-SMOKE-001
- **date/heure**: 2026-07-14 01:14 UTC
- **runner_id**: luna-vm-01
- **device_id**: 192.168.1.62:5555 (Wi-Fi)

## Resultats ADB

| Element | Valeur |
|---------|--------|
| Modele | LLY-NX1 |
| Android version | 16 |
| Etat ADB | device |
| Batterie | 70% |
| Temperature | 33.0 C |
| Package Luna/Yawatch | fr.yawatch.luna |
| versionName | 3.3.0-guardian-restore |
| versionCode | 25 |

## Commandes executees

```bash
adb devices -l
adb -s 192.168.1.62:5555 shell getprop ro.product.model
adb -s 192.168.1.62:5555 shell dumpsys battery | head -30
adb -s 192.168.1.62:5555 shell pm list packages | grep -Ei 'yawatch|luna|guardian'
adb -s 192.168.1.62:5555 shell dumpsys package fr.yawatch.luna | grep -E 'versionName|versionCode'
```

## Preuves collectees

Repertoire local : `/home/ludo/luna-server/runs/PHONE-ADB-SMOKE-001/20260713_231401/`

- screenshot.png
- ui-hierarchy.xml
- logcat-full.txt
- logcat-errors.txt
- dumpsys-activity.txt
- dumpsys-package.txt
- adb-devices.txt
- device-info.txt

## Conclusion

GO_AUDIT_APP

Le telephone est accessible en ADB Wi-Fi, le package `fr.yawatch.luna` est installe et actif. Aucune modification n'a ete effectuee sur l'appareil.

## Prochaine action recommandee

Poursuivre avec une mission d'audit ou de correction ciblee sur Guardian, par exemple `GUARDIAN-AUDIT-VOICE-002`, en utilisant les preuves collectees.

## Statut final

needs_audit

## Budget consomme

- 1 appel Kimi operator pour PHONE-ADB-SMOKE-001.
- Total jour : 2 appels Kimi sur 6 autorises.
