# État actuel — Luna production

Dernière mise à jour : 2026-06-17 (DeepSeek, validation Ludovic)

## Architecture déployée

| Couche | État | Détail |
|---|---|---|
| GitHub `main` | ✅ À jour | luna_web.py + Guardian Policy V2 (Niveau 3 + seuils) |
| Google Cloud Run | ✅ Déployé | `luna-beta`, revision `luna-beta-00680-fhz`, region `europe-west1`, projet `crypto-parser-475411-k4` |
| URL production | ✅ | `https://luna-beta-674304336025.europe-west1.run.app` |
| Redis (Upstash) | ✅ Connecté | `genuine-mammal-135122.upstash.io:6379` |
| APK Android | ✅ v2.8 | WebView → Cloud Run URL, User-Agent `LunaApp/2.8` |

## Monitoring `/api/admin/objectives` — État Cloud Run

| Objectif | Statut | Note |
|---|---|---|
| services | warning | Twilio/Duffel/Serper optionnels — normal sur serveur fondateur |
| documents | warning | Vault optionnel |
| formulaires | warning | Services optionnels |
| cartes | warning | Géolocalisation optionnelle |
| amis | warning | Réseau social optionnel |
| activites | ok | Gamification opérationnelle |
| monde | ok | Social world opérationnel |
| profil | warning | Pas de profil souscripteur en Upstash — normal (fondateur) |
| quotas | ok | QuotaGuard actif, limites configurées |
| reglages | warning | Stripe absent sur serveur fondateur — non critique |
| voix | ok | OpenAI Realtime actif, voix coral (féminine) |

## Fonctionnalités récemment livrées (25 mai 2026)

- **Monitoring voix** : 16 sous-services, détection voix féminine (`coral`), WebView audio fix
- **AudioWorklet fix APK** : détection `LunaApp/` UA → `ScriptProcessorNode` (pas AudioWorklet)
- **Voix coral** : `OPENAI_VOICE_NAME=coral` dans `.env` et Cloud Run
- **Pas de branding AI visible** : mentions Claude/Anthropic supprimées de `index.html`
- **Monitoring 11 objectifs** : tous implémentés dans `GET /api/admin/objectives`

## Fonctionnalités récemment livrées (17 juin 2026)

- **Guardian Policy V2 — Niveau 3 backend** : 1re vérification → 10 min → 2e vérification → 5 min → alerte contacts
- **Guardian Policy V2 — Seuils immobilité** : senior 45 min, DOG 90 min, HOME 240 min (alignés sur §4.2)
- **Guardian Policy V2 — Atténuation caméra** : annulation automatique des signaux immobilité GPS si personne visible en posture normale
- **Guardian Policy V2 — Check-in caméra** : `/api/guardian/checkin-miss/` déléguée au moteur, cycle Niveau 2→3→4 respecté
- **Tests Guardian P0** : 43/43 pass, conformité Policy V2 validée

## Points d'attention actifs

- Voix dans APK : fix AudioWorklet déployé mais à valider sur appareil réel
- Stripe absent : volontaire sur serveur fondateur, ne pas marquer critical
- Duffel : mode test (`duffel_test_*`), pas de vraies réservations
- `ENVIRONMENT=cloudrun` dans `.env` local → override obligatoire au lancement : `ENVIRONMENT= PORT=8888 python3 luna_web.py`

## Prochains chantiers

- Audit fonctionnel onglets (tester chaque bouton sur APK réelle)
- Monitoring Voix : améliorer détection expérience utilisateur réelle (pas seulement téchnique)
- Tests automatisés bout-en-bout
