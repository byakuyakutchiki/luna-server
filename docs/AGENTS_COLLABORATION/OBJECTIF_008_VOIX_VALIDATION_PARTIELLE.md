# Objectif 008 — Voix APK : Validation partielle (2026-05-25 19:30)

**Status** : ✅ Pipeline validé — Cause OpenAI quota insuffisant identifiée
**Priorité** : critique
**Lead** : Claude

## Problème initial

WebSocket fermé après ~5s, aucune réponse audio reçue sur APK Ludovic.

## Résultat test réel

**Cause identifiée : Solde OpenAI insuffisant / insufficient_quota**

Après recharge du compte OpenAI :
- ✅ Voix Luna fonctionne sur l'APK
- ✅ Audio reçu correctement
- ✅ Playback fonctionne
- ✅ Pipeline complètement validé

## Pipeline confirmé

```
APK Ludovic (appui bouton vocal)
  ↓
Serveur Luna (/ws/luna-voice)
  ↓
OpenAI Realtime API (gpt-4o-realtime-preview-2024-12-17)
  ↓
Audio réponse généré
  ↓
WebSocket → APK
  ↓
Playback audio dans la WebView
✅ Fonctionne
```

## Modèle actif

**Modèle** : `gpt-4o-realtime-preview-2024-12-17` (alias : gpt-realtime-mini)
**Format audio** : PCM16 24kHz (bidirectionnel)
**Durée session** : Jusqu'à ~5min avant timeout (comportement normal)

## Ce qui était faux

❌ **Hypothèse écartée** : Problème APK principal
❌ **Hypothèse écartée** : Problème cache WebView
❌ **Hypothèse écartée** : Problème fermeture WS côté serveur

✅ **Vrai problème** : Quotas OpenAI insuffisants
✅ **Solution** : Recharge de crédits OpenAI

## Apprentissages

1. Objectif 007 (télémétrie) a bien permis de localiser le blocage à "après audio envoyé"
2. Logs serveur et diagnostics structurés auraient accéléré identification du quota
3. Monitoring OpenAI quota côté serveur manquant → ajouter à Objective 009

## Statut points de validation

- [x] Heartbeat APK reçu
- [x] Télémétrie voix reçue (11 événements)
- [x] Audio envoyé côté client
- [x] Pipeline serveur → OpenAI validé
- [x] Audio réponse reçu côté client
- [x] Playback fonctionne
- [x] Cause identifiée et corrigée (quota OpenAI)

## Problème restant : Stabilité voix

**Symptôme** : Luna commence à parler mais coupe/s'arrête sans raison claire

**Prochaine étape** : Objective 008-stabilité

## Points à ne plus chercher

- Cause principale de l'absence de voix n'est PAS l'APK
- Cause principale n'est PAS le cache
- Cause principale n'est PAS le WebSocket côté client
- Pipeline APK → serveur → OpenAI est fonctionnel ✅
