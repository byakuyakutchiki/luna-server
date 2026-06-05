# Codex — Mission Kimi Guardian — Objectif 030

Date : 2026-06-05
Agent : Codex
Type : mission / cadrage

## Message à Kimi

```text
Kimi, nouvelle mission autonome pendant que Claude termine Iris.

Objectif 030 — Guardian Audit caméra / surveillance / RGPD

Va lire :
docs/AGENTS_COLLABORATION/OBJECTIF_030_GUARDIAN_AUDIT_CAMERA_RGPD.md

But :
Auditer la partie Guardian de Luna. Guardian est censé surveiller/protéger, suivre la position, comprendre ce qui se passe, et potentiellement utiliser la caméra avec consentement. Ludovic constate que la caméra ne s'allume pas ou n'est pas clairement reliée à Guardian.

Tu dois auditer, pas déployer.
Tu ne déclenches aucun SOS réel, aucun SMS, aucun appel.

Fichiers à inspecter en priorité :
- static/guardian.html
- luna_web.py routes /api/guardian/*
- core/guardian/engine.py
- core/guardian/alerts.py
- core/perception/detector.py
- core/perception/analyzer.py
- docs/AGENTS_COLLABORATION/agents/KIMI_BUTTON_TARGET_SWEEP.md

Questions à trancher :
1. Quels boutons réels existent dans Guardian ?
2. Chaque bouton va vers quel handler JS et quel endpoint ?
3. La caméra est-elle demandée dans Guardian, ou seulement dans Iris/Simli ?
4. Pourquoi la caméra ne s'allume pas côté Guardian ?
5. La géolocalisation démarre-t-elle vraiment ?
6. Le stop coupe-t-il bien GPS/caméra/timers ?
7. SOS peut-il envoyer un SMS réel ? Avec quelles protections ?
8. Le consentement RGPD caméra/GPS est-il clair ?
9. Aucune image n'est-elle stockée ?
10. Quelles corrections P0/P1 proposes-tu ?

Livrable obligatoire :
docs/AGENTS_COLLABORATION/agents/KIMI_AUDIT_GUARDIAN_CAMERA_RGPD_030.md

Format :
Agent : Kimi
Objectif : 030
Type : audit Guardian caméra / RGPD / boutons
Résumé : ...
Fichiers inspectés : ...
Boutons réels : bouton -> handler -> endpoint -> effet -> risque
Caméra : ...
GPS : ...
SOS : ...
RGPD : ...
P0 : ...
P1 : ...
Décision Ludovic requise : oui/non
Actions proposées : ...

Règle :
Si ce n'est pas poussé sur GitHub, ce n'est pas livré.
```

## Position Codex

Guardian doit être traité comme un module sensible.

Les priorités ne sont pas seulement UX :

1. sécurité utilisateur ;
2. consentement clair ;
3. arrêt garanti ;
4. pas de stockage image ;
5. pas d'alerte silencieuse ;
6. preuve terrain.

La caméra Guardian ne doit pas être activée par surprise. Elle doit être demandée, affichée, expliquée et stoppable.
