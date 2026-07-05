# État actuel — Luna production

Dernière mise à jour : 2026-07-05 (Kimi, validation Ludovic)

## Architecture déployée

| Couche | État | Détail |
|---|---|---|
| GitHub `main` | ✅ À jour | `luna_web.py` + Guardian Policy V2 (Niveau 3 + seuils) |
| Branche stable frontend | ✅ Créée | `stable/frontend-reference-2026-07-05` (SHA `d0971aa`) — référence officielle du frontend |
| Branche PWA | ✅ En validation | `feature/pwa` (SHA `f45fe4f`) — snapshot + patch PWA 3 fichiers |
| Branche governance | ✅ Créée | `feature/frontend-governance-tools` (SHA `e935897`) — outil anti-régression |
| Snapshot frontend | ✅ Poussé | `snapshot/prod-frontend-00970-bad` (SHA `d0971aa`) — frontend identique à la production |
| Google Cloud Run production | ✅ | `luna-beta`, revision `luna-beta-00970-bad`, 100 % trafic |
| Google Cloud Run trace PWA | ✅ 0 % | `luna-beta`, revision `luna-beta-00983-kal`, tag `trace` |
| Google Cloud Run trace frontend | ✅ 0 % | `luna-beta`, revision `luna-beta-00982-jub`, tag `trace-frontend` |
| URL production | ✅ | `https://luna-beta-674304336025.europe-west1.run.app` |
| URL trace PWA | ✅ | `https://trace---luna-beta-gly3g647na-ew.a.run.app` |
| URL trace frontend | ✅ | `https://trace-frontend---luna-beta-gly3g647na-ew.a.run.app` |
| Redis (Upstash) | ✅ Connecté | `genuine-mammal-135122.upstash.io:6379` |
| APK Android | ✅ v3.8 (29) | WebView → Cloud Run trace URL, User-Agent `LunaApp/3.8`, auth JWT standard |

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

## Fonctionnalités récemment livrées (04 juillet 2026)

- **Authentification JWT dans l'APK** : l'APK passe par `/` pour le login, puis `index.html` redirige automatiquement vers `/guardian` quand `User-Agent` contient `LunaApp/`
- **Navigation WebView corrigée** : `MainActivity.java` autorise tout le domaine Luna, pas seulement `/guardian`, évitant les sorties vers Chrome
- **Permissions WebView corrigées** : micro/caméra/GPS acceptés sur tout le domaine Luna, pas seulement sur `/guardian`
- **Guardian — capture vocale** : fix `isFinal` pour conserver le contexte complet dans `TRACE_sos_request`
- **Guardian — Redis 409** : séparation du verrou de déduplication (`guardian:incident_lock:{id}`) et du dossier incident (`guardian:incident:{id}`)
- **`guardian.html` reste générique** : aucune modification spécifique à l'APK ; compatible avec futur pairing device (Option C)

## Gouvernance frontend — mise en place 05 juillet 2026

### Problème résolu

La production ne correspondait plus à un commit Git unique. Des modifications
étaient présentes dans le working directory au moment de certains déploiements,
ce qui provoquait des régressions graphiques quand on repartait d'anciens commits.

### Référence officielle

- Branche : `stable/frontend-reference-2026-07-05`
- SHA : `d0971aa`
- Contenu : frontend identique à la production `luna-beta-00970-bad`
- Règle : **aucun développement direct**, modifications uniquement via PR

### Cycle de développement obligatoire

```
stable/frontend-reference
        │
        ▼
feature/...
        │
        ▼
trace (0 % trafic)
        │
        ▼
validation terrain
        │
        ▼
audit anti-régression
        │
        ▼
production
```

### Outil anti-régression

- Script : `tools/frontend_regression_check.py`
- Branche : `feature/frontend-governance-tools`
- Vérifie automatiquement :
  - `git status` propre
  - branche et SHA identifiés
  - comparaison des routes `/`, `/guardian`, `/static/index.html`,
    `/static/guardian.html`, `/static/salon.html`, `/static/simli.html`,
    `/static/manifest.json`, `/static/sw.js` avec la référence

Usage :
```bash
# Avant déploiement
python3 tools/frontend_regression_check.py --strict

# Après déploiement trace
python3 tools/frontend_regression_check.py --trace https://trace---....a.run.app
```

### Protection GitHub à configurer

Pour `stable/frontend-reference-2026-07-05` :

1. Aller sur `https://github.com/byakuyakutchiki/luna-server/settings/branches`
2. Cliquer **Add rule**
3. Branch name pattern : `stable/frontend-reference-2026-07-05`
4. Cocher :
   - ☑ **Require a pull request before merging**
   - ☑ **Require approvals** (minimum 1)
   - ☑ **Dismiss stale PR approvals when new commits are pushed**
   - ☑ **Require status checks to pass before merging** (si GitHub Actions ajouté)
   - ☑ **Restrict pushes that create files larger than 100 MB**
5. Dans **Restrict who can push to matching branches**, ajouter uniquement les
   administrateurs
6. Cliquer **Create**

### Checklist avant tout déploiement

- [ ] `git branch --show-current` correcte
- [ ] `git rev-parse HEAD` identifié
- [ ] `git status --short` propre (ou `--strict` du script)
- [ ] `git diff --stat` relu
- [ ] `python3 tools/frontend_regression_check.py --strict` passe
- [ ] déploiement uniquement avec `--no-traffic` sur trace
- [ ] validation terrain OK
- [ ] audit Codex OK

## Prochains chantiers

- Validation terrain du flux APK complet : login → Guardian → SOS → SMS/appel
- Audit fonctionnel onglets (tester chaque bouton sur APK réelle)
- Monitoring Voix : améliorer détection expérience utilisateur réelle (pas seulement téchnique)
- Tests automatisés bout-en-bout
