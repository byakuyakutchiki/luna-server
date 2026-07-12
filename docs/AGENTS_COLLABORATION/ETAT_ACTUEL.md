# État actuel — Luna production

Dernière mise à jour : 2026-07-12 (Kimi)

## Architecture déployée

| Couche | État | Détail |
|---|---|---|
| GitHub `main` | ✅ À jour | luna_web.py + index.html + monitoring 11 objectifs |
| Google Cloud Run | ✅ Déployé | `luna-beta`, region `europe-west1`, projet `crypto-parser-475411-k4` |
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

## Points d'attention actifs

- Voix dans APK : fix AudioWorklet déployé mais à valider sur appareil réel
- Stripe absent : volontaire sur serveur fondateur, ne pas marquer critical
- Duffel : mode test (`duffel_test_*`), pas de vraies réservations
- `ENVIRONMENT=cloudrun` dans `.env` local → override obligatoire au lancement : `ENVIRONMENT= PORT=8888 python3 luna_web.py`

## Ressources documentaires

- **Référentiel technique Android Luna/Guardian** : `docs/ANDROID_REFERENTIEL/` — 17 chapitres fondés sur la documentation officielle Android Developers et AOSP, destinés à servir de source de vérité aux agents travaillant sur l'APK et Guardian.
- **Architecture de collaboration Codex ↔ Kimi ↔ DeepSeek ↔ n8n** : `docs/AGENT_EXCHANGE/` — spécifications, règles de sécurité, scripts d'audit en lecture seule, consignes agents et intégration DeepSeek API. En attente de validation par Ludovic avant déploiement.

## Points d'attention actifs — collaboration agents

- **ADB détecté** : `c7750037 device`, `fr.yawatch.luna` actif (PID 29649).
- **SSH Codex → VM** : service actif, mais l'authentification depuis Windows n'a pas encore été testée.
- **Worktrees Kimi2/Codex** : non créés. Nécessitent validation avant exécution.
- **Workflow n8n** : spécifié mais non activé. Nécessite validation et tests.
- **DeepSeek API** : intégration spécifiée. Nécessite une `DEEPSEEK_API_KEY` dans les credentials n8n.

## Prochains chantiers

- Audit fonctionnel onglets (tester chaque bouton sur APK réelle)
- Monitoring Voix : améliorer détection expérience utilisateur réelle (pas seulement téchnique)
- Tests automatisés bout-en-bout
