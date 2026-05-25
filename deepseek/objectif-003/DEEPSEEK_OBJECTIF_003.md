# DeepSeek — Mission Objectif 003

## Contexte immédiat

Ludovic a validé une idée importante : Luna doit avoir un "cerveau APK" minimal.

But : l'APK Android ne doit pas être une WebView passive. Elle doit remonter au serveur ce que le téléphone vit réellement : version APK, URL Cloud Run chargée, build frontend, WebView, permissions, état vocal, WebSocket, audio reçu ou non, erreurs JS.

La branche de cadrage créée par Codex est :

```text
codex/objectif-003-apk-telemetry
```

PR GitHub :

```text
https://github.com/byakuyakutchiki/luna-server/pull/new/codex/objectif-003-apk-telemetry
```

Le document principal à lire est :

```text
docs/AGENTS_COLLABORATION/OBJECTIF_003_CERVEAU_APK.md
```

## Ce que tu dois faire

1. Récupérer les dernières branches sans écraser tes fichiers locaux.
2. Lire le cadrage de l'objectif 003.
3. Proposer ta partie technique : schéma heartbeat + événements APK.
4. Ne pas déployer, ne pas modifier Cloud Run, ne pas toucher aux secrets.

## Commandes sûres à lancer depuis VS Code

```bash
git fetch origin
git switch -c ds/objectif-003-apk-telemetry origin/main
git merge --no-commit --no-ff origin/codex/objectif-003-apk-telemetry
```

Si Git refuse à cause de fichiers locaux non committés, ne force rien. Préviens Ludovic ou Claude.

## Ta mission précise

Créer une proposition dans :

```text
docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS.md
```

Section à ajouter :

```md
## Objectif 003 — Cerveau APK / télémétrie appareil réel

### Schéma heartbeat proposé

### Événements APK critiques proposés

### Fichiers Android / WebView à inspecter

### Endpoint serveur proposé

### Stockage proposé

### Affichage admin proposé

### Risques

### Correction minimale recommandée

### Validation Ludovic nécessaire
```

## Signaux prioritaires à proposer

- version APK installée ;
- URL Cloud Run réellement chargée ;
- User-Agent WebView ;
- build frontend vu par le téléphone ;
- écran actif ;
- permission micro accordée/refusée ;
- bouton vocal cliqué ;
- WebSocket voix ouvert/fermé ;
- audio envoyé ;
- audio reçu ;
- absence d'audio après timeout ;
- erreur JavaScript WebView ;
- dernier contact serveur.

## Garde-fous absolus

- Pas d'audio brut.
- Pas de transcript privé.
- Pas de position exacte.
- Pas de clé API, token, cookie ou secret.
- Pas de capacité de déployer depuis l'APK.
- Pas de commande Cloud Run.
- Pas de push direct sur `main`.
- Travail uniquement sur branche `ds/objectif-003-apk-telemetry`.

## Philosophie

Cloud Run sait ce qu'il sert.
L'APK sait ce que l'utilisateur vit.
Luna doit comparer les deux.

Ton rôle est de proposer comment le téléphone peut observer et rapporter son état réel, sans jamais devenir un outil d'administration production.
