# Note priorité — fermer le heartbeat APK avant validation Objectif 005

Date : 2026-05-25

## Résumé

L'objectif 005 peut être préparé en parallèle, mais il ne doit pas être validé
ni déployé comme observation fiable tant que l'objectif 003/004 n'a pas reçu
le premier heartbeat réel depuis le téléphone de Ludovic.

## État confirmé

Claude a répondu aux quatre questions de contrôle :

1. APK rebuildée avec `sendHeartbeat()` : **non**.
2. APK installée sur le téléphone : **non**.
3. `/api/admin/apk-diagnosis` reçoit le premier heartbeat : **non**.
4. `fondateur.html` affiche le téléphone vu récemment : **non**.

Donc la boucle heartbeat n'est pas encore fermée.

## Priorité immédiate

Avant validation réelle de l'objectif 005 :

1. rebuilder l'APK avec les commits heartbeat (`sendHeartbeat()` + User-Agent `LunaApp/...`) ;
2. installer cette APK sur le téléphone de Ludovic ;
3. ouvrir Luna ;
4. vérifier `/api/admin/apk-diagnosis` ;
5. vérifier `fondateur.html` ;
6. constater le passage de `waiting_first_contact` à `ok`.

## Ce que l'équipe peut faire maintenant

### Autorisé

- DeepSeek peut préparer les points d'injection dans `startVoice()`.
- Kimi peut préparer les textes cockpit voix.
- Cursor peut vérifier les risques UI / JS.
- Claude peut préparer `POST /api/apk/event` sans déploiement.
- Codex peut vérifier le cadrage et les garde-fous.

### Non autorisé tant que heartbeat réel absent

- Dire que la boucle APK est validée.
- Déployer l'objectif 005 comme diagnostic réel.
- Confondre `heartbeat OK` avec `voix OK`.
- Lancer une correction automatique voix.

## Règle

```text
Heartbeat réel d'abord.
Événements voix ensuite.
Diagnostic voix fiable seulement après les deux.
```
