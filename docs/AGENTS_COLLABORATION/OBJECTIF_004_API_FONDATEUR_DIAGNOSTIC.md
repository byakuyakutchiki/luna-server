# Objectif 004 — API fondateur : diagnostic APK + journal des actions

## Intention fondateur

Après Objectif 003, Luna reçoit l'état réel de l'APK via heartbeat.

Objectif 004 ajoute la couche suivante : interpréter cet état, proposer une
action lisible, corriger seulement ce qui est autorisé, et conserver une trace.

L'idée n'est pas encore de donner à Luna les clés de la production. L'idée est
de créer un cockpit fondateur : observation, diagnostic, recommandation,
validation, journal.

## Principe central

```text
Observer -> Interpréter -> Proposer / agir -> Tracer
```

## Périmètre

### Inclus

- Diagnostic serveur basé sur le heartbeat APK.
- Statuts lisibles pour Ludovic.
- Actions recommandées classées par niveau de risque.
- Journal des diagnostics et actions proposées.
- Intégration API fondateur / dashboard.
- Tests sans action production destructrice.

### Exclu pour cette phase

- Déploiement Cloud Run automatique.
- Rebuild APK automatique.
- Modification automatique de secrets ou variables Cloud Run.
- Reset Redis global automatique.
- Correction vocale complexe sans validation.
- Collecte audio, transcript, position exacte ou données privées.

## Diagnostic attendu

Fonction serveur envisagée :

```python
def _analyze_apk_state(heartbeat: dict, recent_events: list | None = None) -> dict:
    ...
```

Sortie envisagée :

```json
{
  "status": "warning",
  "diagnosis": "APK vivante mais version obsolète",
  "probable_cause": "Ancienne APK installée ou auto-update non appliqué",
  "recommended_action": "Installer la dernière APK",
  "action_level": "manual_validation_required",
  "can_auto_fix": false,
  "evidence": {
    "apk_version": "2.7",
    "expected_apk_version": "2.8",
    "last_seen_seconds": 42
  }
}
```

## Niveaux d'action

### Niveau 0 — information seulement

Luna affiche un diagnostic, sans action.

Exemples :

- APK vue il y a 30 secondes.
- URL Cloud Run correcte.
- Version APK connue.

### Niveau 1 — action sûre et locale

Action non destructive, sans accès production.

Exemples :

- Demander un heartbeat détaillé.
- Marquer un test voix à refaire.
- Afficher un lien de téléchargement APK.
- Proposer de fermer/réouvrir l'APK.

### Niveau 2 — action proposée avec validation Ludovic

Action utile mais pouvant avoir un impact utilisateur.

Exemples :

- Forcer refresh WebView au prochain lancement.
- Demander vidage cache APK au prochain démarrage.
- Basculer un flag de diagnostic temporaire.
- Recommander installation d'une nouvelle APK.

### Niveau 3 — action interdite sans Claude + Ludovic

Action production ou infrastructure.

Exemples :

- Rebuild APK.
- Déploiement Cloud Run.
- Modification `.env`.
- Changement modèle OpenAI.
- Reset Redis.
- Modification auth, Stripe, quotas, données utilisateur.

## Journal des actions

Chaque diagnostic ou action proposée doit écrire une trace.

Clé Redis envisagée :

```text
luna:founder:actions:log
```

Entrée envisagée :

```json
{
  "ts": "2026-05-25T12:45:00+02:00",
  "source": "apk_heartbeat_analyzer",
  "status": "warning",
  "diagnosis": "APK version obsolète",
  "probable_cause": "APK 2.7 vue alors que 2.8 attendue",
  "action_proposed": "installer dernière APK",
  "action_level": "manual_validation_required",
  "action_taken": "none",
  "validated_by": null,
  "result": "pending"
}
```

## Affichage API fondateur

Dans `fondateur.html` ou l'API admin, afficher :

- état APK actuel ;
- dernier heartbeat ;
- diagnostic ;
- cause probable ;
- action recommandée ;
- niveau de validation requis ;
- bouton de validation uniquement pour actions autorisées ;
- historique des diagnostics/actions.

Exemple texte fondateur :

```text
APK Fondateur : WARNING
Téléphone vu il y a 4 min.
Diagnostic : l'APK est vivante mais aucun test voix n'a encore été reçu.
Action recommandée : ouvrir Luna sur le téléphone et appuyer sur le bouton vocal.
Action automatique : aucune.
Trace : diagnostic enregistré.
```

## Rôles par agent

### Claude

- Valider l'architecture finale.
- Définir quelles actions sont autorisées ou interdites.
- Implémenter ou reviewer l'API fondateur.
- Déployer seulement après validation Ludovic.

### DeepSeek

- Proposer le moteur de règles `_analyze_apk_state()`.
- Définir un schéma `diagnosis/action/evidence`.
- Proposer tests unitaires sur cas heartbeat : absent, ancien, URL fausse, version obsolète.
- Ne pas implémenter d'action production.

### Kimi

- Auditer les textes affichés à Ludovic.
- Vérifier que les diagnostics sont compréhensibles et non anxiogènes.
- Identifier les ambiguïtés : quand Luna sait, quand Luna suppose, quand elle ne sait pas.

### Codex

- Maintenir le cadrage GitHub.
- Proposer le découpage PR.
- Vérifier les garde-fous.
- Relire les tests et risques.

### Cursor

- Vérifier cohérence `fondateur.html`, routes API, noms de statuts et état visuel.
- Signaler les erreurs de navigation UI ou chevauchements.

## Tests proposés

Sans téléphone :

- heartbeat absent -> critical ;
- heartbeat récent -> ok ;
- heartbeat ancien -> warning ;
- URL Cloud Run différente -> warning ;
- version APK absente -> warning ;
- version APK inférieure à attendue -> warning ;
- Redis indisponible -> diagnostic dégradé sans crash.

Avec téléphone fondateur :

- ouvrir APK -> heartbeat visible ;
- fermer APK > seuil -> warning ;
- rouvrir APK -> retour ok ;
- vérifier que chaque diagnostic crée une trace.

## Décision à demander à Ludovic

- [ ] Valider diagnostic + journal seulement.
- [ ] Autoriser actions sûres niveau 1.
- [ ] Autoriser actions niveau 2 après confirmation bouton.
- [ ] Refuser toute auto-correction pour l'instant.

Commentaire Ludovic :
