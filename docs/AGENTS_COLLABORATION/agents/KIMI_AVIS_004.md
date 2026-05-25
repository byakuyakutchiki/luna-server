# Avis Kimi — Objectif 004 API fondateur diagnostic

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Auditer les textes affichés à Ludovic, vérifier le ton, identifier les ambiguïtés
Date : 2026-05-25
Branche : `kimi/objectif-004-founder-diagnostics`

---

## 1. Audit des textes existants dans OBJECTIF_004

### Textes présents dans le cadrage

| Texte original | Problème identifié | Sévérité |
|---|---|---|
| "APK vivante mais version obsolète" | "obsolète" est un jugement technique. Pour Ludovic, c'est "pas à jour". | mineur |
| "Ancienne APK installée ou auto-update non appliqué" | Deux causes possibles sans indication de laquelle est la bonne. Ambiguïté : Luna suppose sans savoir. | moyen |
| "Installer la dernière APK" | Directif mais impersonnel. Qui installe ? Ludovic ? L'APK devrait s'auto-updater ? | mineur |
| "APK vue il y a 30 secondes" | OK. Factuel. Luna sait. | ✅ |
| "URL Cloud Run correcte" | **Ambiguïté majeure**. "Correcte" signifie "correspond à l'URL attendue par le serveur", pas "accessible depuis le téléphone". Luna suppose que si l'URL correspond, tout va bien. | moyen |
| "Version APK connue" | Ambigu : "connue" par qui ? Par le heartbeat ? Par le serveur ? Par Ludovic ? | mineur |
| "Demander un heartbeat détaillé" | Ambigu sur l'acteur. Qui demande ? Luna demande au téléphone ? Le serveur envoie une commande ? Ludovic doit faire une action ? | moyen |
| "Forcer refresh WebView au prochain lancement" | **"Forcer" est anxiogène**. Implique une action autoritaire sans consentement. | moyen |
| "Demander vidage cache APK au prochain démarrage" | "Demander" à qui ? Au téléphone ? À Ludovic ? | mineur |
| "Basculer un flag de diagnostic temporaire" | Jargon technique ("flag", "basculer"). Pas lisible pour un fondateur non-dev. | moyen |
| "Recommander installation d'une nouvelle APK" | OK si précédé de "Luna recommande". Seul, c'est impersonnel. | mineur |
| "APK Fondateur : WARNING" | Majuscules + anglais technique. À traduire en français pour l'affichage final. | mineur |
| "l'APK est vivante mais aucun test voix n'a encore été reçu" | **Ambiguïté majeure**. "Aucun test voix reçu" = le téléphone n'a jamais envoyé d'événement voix. Mais Ludovic pourrait avoir testé sans succès (bouton silencieux) et le téléphone n'a rien envoyé. Luna ne sait pas distinguer "pas testé" de "testé mais échoué silencieusement". | **critique** |
| "ouvrir Luna sur le téléphone et appuyer sur le bouton vocal" | OK, mais répétitif si Ludovic l'a déjà fait. Manque le cas "j'ai déjà essayé". | mineur |
| "Action automatique : aucune" | OK, rassurant. | ✅ |
| "Trace : diagnostic enregistré" | Jargon ("trace"). "Diagnostic sauvegardé" ou "Note enregistrée" serait plus humain. | mineur |

---

## 2. Anxiété et ton

### Textes anxiogènes identifiés

| Texte | Pourquoi c'est anxiogène | Proposition |
|---|---|---|
| "Forcer refresh WebView" | "Forcer" = violence. L'utilisateur n'a pas le contrôle. | "Proposer le refresh de la page au prochain lancement" |
| "APK version obsolète" | "Obsolète" = jugement négatif, presque moral. | "APK pas à jour" ou "Version différente de celle attendue" |
| "Aucun test voix n'a encore été reçu" | "Aucun" + "encore" = culpabilise l'utilisateur. Sous-entendu "tu n'as pas fait ce qu'il fallait". | "Luna n'a pas reçu de signalement vocal depuis le téléphone. Si tu as déjà essayé, le signal n'a pas remonté." |
| "WARNING" | Anglais technique en majuscules. | "Attention" ou "Avertissement" |
| "critical" | Anglais technique. | "Critique" ou "Problème important" |
| "degraded" | Anglais technique, ambigu (dégradé = quoi ?). | "Fonctionnement réduit" ou "Partiel" |

### Textes rassurants à préserver

| Texte | Pourquoi c'est bien |
|---|---|
| "Action automatique : aucune" | Rassurant. Ludovic sait que Luna n'a rien fait sans lui. |
| "Téléphone vu il y a X min" | Factuel, neutre, pas de jugement. |
| "Diagnostic enregistré" | (moyennant amélioration) Indique que Luna trace, donc qu'on ne perd pas l'info. |

---

## 3. Ambiguïtés : quand Luna sait, suppose, ou ne sait pas

### Tableau de confiance par diagnostic

| Diagnostic | Ce que Luna sait vraiment | Ce que Luna suppose | Ce que Luna ne sait pas |
|---|---|---|---|
| "APK vue il y a 30s" | Un heartbeat a été reçu il y a 30s avec cet identifiant. | Que c'est bien le téléphone fondateur (si pas d'auth forte sur le heartbeat). | Si l'APK est réellement ouverte à l'écran ou juste en tâche de fond. |
| "URL Cloud Run correcte" | L'URL dans le heartbeat correspond à `LUNA_URL` serveur. | Que l'URL est accessible depuis le téléphone. | Si le DNS résout, si le certificat SSL passe, si le réseau mobile bloque l'URL. |
| "Version APK obsolète" | La version dans le heartbeat (ex: 2.7) est différente de la version attendue (2.8). | Que l'auto-update a échoué. | Si l'utilisateur a volontairement gardé l'ancienne version, si le téléphone a refusé la mise à jour, si l'APK store a un délai. |
| "Aucun test voix reçu" | Aucun événement `voice_button_clicked` n'a été reçu. | Que Ludovic n'a pas testé. | Si Ludovic a cliqué mais le téléphone n'a pas envoyé l'événement, si le bouton est silencieux, si la WebView a bloqué l'événement. |
| "Heartbeat ancien" | Dernier heartbeat > seuil (ex: 5 min). | Que le téléphone est hors ligne. | Si le téléphone est en avion, si l'APK a crash, si le réseau est coupé, si l'utilisateur a fermé l'app volontairement. |
| "Redis indisponible" | Le serveur ne peut pas se connecter à Redis. | Que les diagnostics sont dégradés. | Si c'est temporaire, si c'est un quota Upstash, si le réseau Cloud Run est instable. |

### Risque majeur identifié

**Le diagnostic "Aucun test voix reçu" est dangereux s'il est présenté comme une vérité.**

Scénario réel :
1. Ludovic ouvre Luna sur son téléphone.
2. Il clique sur le bouton vocal.
3. Le bouton est silencieux (bug connu objectif 001).
4. La WebView ne déclenche pas l'événement `voice_button_clicked` car `startVoice()` plante avant.
5. Objectif 004 affiche : "Aucun test voix n'a encore été reçu. Action : appuyer sur le bouton vocal."
6. Ludovic lit cela et pense : "J'ai déjà appuyé, pourquoi Luna me dit que je n'ai pas testé ?"
7. **Résultat : perte de confiance dans Luna.**

**Recommandation :** Toujours formuler ce diagnostic comme une absence de signal, pas comme une absence d'action utilisateur.

---

## 4. Propositions de textes corrigés

### Règles rédactionnelles proposées pour tous les diagnostics

1. **Jamais de jugement moral** : "obsolète" → "pas à jour", "ancienne" → "différente".
2. **Jamais de certitude sur la cause** : Toujours utiliser "peut-être", "probablement", ou lister les causes possibles.
3. **Distinguer absence de signal et absence d'action** : "Luna n'a pas reçu de signe" ≠ "Tu n'as pas fait l'action".
4. **Jamais d'anglais technique en affichage** : `WARNING` → `Attention`, `critical` → `Problème important`.
5. **Toujours indiquer le niveau de confiance** : "Luna sait que...", "Luna pense que...", "Luna ne sait pas si...".

### Textes fondateur corrigés par situation

#### Situation : Heartbeat absent (aucun signal)

**Avant :**
```
APK Fondateur : CRITICAL
Téléphone non vu depuis 10 min.
Diagnostic : l'APK ne répond pas.
Action recommandée : vérifier que Luna est ouverte.
```

**Après (proposition Kimi) :**
```
📱 Téléphone fondateur
Dernière vue : il y a plus de 10 minutes.
Statut : Problème important

Ce que Luna sait : aucun signal n'a été reçu depuis 10 min.
Ce que Luna ne sait pas : si le téléphone est éteint, en mode avion,
si Luna est fermée, ou si le réseau est coupé.

Actions possibles :
• Ouvrir Luna sur le téléphone (si elle est fermée)
• Vérifier la connexion WiFi ou mobile
• Si le problème persiste, redémarrer l'application

Action automatique : aucune.
Note enregistrée.
```

#### Situation : Version APK différente

**Avant :**
```
APK vivante mais version obsolète.
Probable cause : ancienne APK installée.
Action : installer la dernière APK.
```

**Après (proposition Kimi) :**
```
📱 Téléphone fondateur
Dernière vue : il y a 42 secondes.
Version APK sur le téléphone : 2.7
Version attendue : 2.8
Statut : Attention

Ce que Luna sait : le téléphone envoie des signaux, mais avec une
version différente de celle attendue.
Ce que Luna ne sait pas : pourquoi la mise à jour ne s'est pas faite
(échec auto-update, téléchargement non lancé, installation refusée).

Actions possibles :
• Fermer complètement Luna (swipe up) et la rouvrir
• Si l'auto-update ne se déclenche pas, télécharger manuellement la dernière APK
• Vérifier dans Paramètres Android que les installations d'APK sont autorisées

Action automatique : aucune pour l'instant.
Niveau requis : confirmation Ludovic pour forcer une action.
Note enregistrée.
```

#### Situation : Aucun événement voix reçu (le plus critique)

**Avant :**
```
Diagnostic : l'APK est vivante mais aucun test voix n'a encore été reçu.
Action recommandée : ouvrir Luna sur le téléphone et appuyer sur le bouton vocal.
```

**Après (proposition Kimi) :**
```
📱 Téléphone fondateur — Voix
Dernière vue : il y a 2 minutes.
Statut : Information

Ce que Luna sait : le téléphone envoie des signaux réguliers, mais
Luna n'a pas reçu d'événement vocal depuis le téléphone.

Ce que cela peut signifier :
• Tu n'as pas encore testé le bouton vocal → c'est normal
• Tu as testé mais rien ne s'est passé (bouton silencieux) → le signal
  n'a pas pu être envoyé car l'application s'est arrêtée avant
• Tu as testé et ça a marché, mais le téléphone n'a pas remonté l'info
  → problème de télémétrie (objectif 003 en cours)

Si tu as déjà essayé et que le bouton était silencieux : ce diagnostic
confirme le bug connu. Pas besoin de réessayer pour l'instant.

Si tu veux tester : ouvre Luna, appuie sur le bouton vocal, dis "Bonjour",
et attends 5 secondes. Même si tu n'entends rien, le signal nous aidera.

Action automatique : aucune.
Note enregistrée.
```

#### Situation : URL Cloud Run différente

**Avant :**
```
URL Cloud Run différente -> warning
```

**Après (proposition Kimi) :**
```
📱 Téléphone fondateur — Connexion
Dernière vue : il y a 15 secondes.
Statut : Attention

Ce que Luna sait : le téléphone charge une URL différente de celle
attendue par le serveur.
URL sur le téléphone : https://ancienne-url.run.app
URL attendue : https://luna-beta-...run.app

Ce que Luna ne sait pas : si l'ancienne URL fonctionne encore, si c'est
volontaire (test), ou si le téléphone est sur une ancienne configuration.

Risque : le téléphone pourrait ne pas recevoir les dernières corrections.

Action recommandée : fermer complètement Luna et la rouvrir pour
forcer le chargement de la bonne URL.

Action automatique : aucune.
Note enregistrée.
```

#### Situation : Redis indisponible (diagnostic dégradé)

**Avant :**
```
Redis indisponible -> diagnostic dégradé sans crash
```

**Après (proposition Kimi) :**
```
📱 Téléphone fondateur
Statut : Fonctionnement réduit

Ce que Luna sait : le serveur ne peut pas accéder à sa mémoire (Redis)
pour lire l'historique ou sauvegarder les diagnostics.

Ce que cela signifie pour toi :
• Luna continue de fonctionner normalement sur le téléphone
• Les conversations et la voix marchent toujours
• Mais le tableau de bord fondateur n'est pas à jour
• Les diagnostics et actions ne sont pas sauvegardés pour l'instant

Ce que Luna ne sait pas : si c'est temporaire (quelques secondes) ou
prolongé. Le serveur réessaie automatiquement.

Pas d'action requise de ta part.
Action automatique : le serveur réessaie de se reconnecter.
Note enregistrée (en local, en attendant Redis).
```

---

## 5. Vocabulaire proposé pour l'affichage fondateur

### Statuts (français uniquement)

| Technique (code) | Affichage Ludovic | Usage |
|---|---|---|
| `ok` | `Tout va bien` | Tout est nominal |
| `warning` | `Attention` | Quelque chose mérite le regard, pas d'urgence |
| `degraded` | `Fonctionnement réduit` | Service partiel, pas de panique |
| `critical` | `Problème important` | Action humaine probablement nécessaire |

### Verbes d'action (impersonnel → personnel)

| À éviter | Parce que | Proposition |
|---|---|---|
| "Forcer" | Anxiogène, violent | "Proposer", "Suggérer" |
| "Demander" (à qui ?) | Ambigu | "Tu peux...", "Luna te propose de..." |
| "Basculer un flag" | Jargon dev | "Activer temporairement" |
| "Vidage cache" | Technique brut | "Vider la mémoire temporaire" |
| "Rebuild" | Anglais technique | "Reconstruire" ou "Regénérer" |
| "Deploy" | Anglais technique | "Mettre en ligne" |

### Structure de phrase recommandée pour chaque diagnostic

```
[Emoji] Sujet
Dernière vue : X.
Statut : [français]

Ce que Luna sait : [faits réels].
Ce que Luna pense : [hypothèse la plus probable].
Ce que Luna ne sait pas : [incertitudes].

Actions possibles :
• [action 1]
• [action 2]

Action automatique : [aucune / description si applicable].
Niveau requis : [info seule / confirmation Ludovic / interdit auto].
Note enregistrée.
```

---

## 6. Synthèse des recommandations Kimi

### À corriger immédiatement dans le cadrage

1. **Remplacer tous les statuts anglais** (`WARNING`, `critical`, `degraded`) par leur équivalent français dans les exemples d'affichage.
2. **Corriger le diagnostic "aucun test voix reçu"** pour qu'il ne culpabilise pas l'utilisateur et qu'il mentionne le cas "j'ai déjà essayé mais c'était silencieux".
3. **Supprimer ou atténuer "Forcer refresh WebView"** → "Proposer le refresh de la page".
4. **Ajouter systématiquement la structure "Ce que Luna sait / pense / ne sait pas"** dans chaque exemple de diagnostic.
5. **Distinguer clairement l'absence de signal de l'absence d'action utilisateur** — c'est le risque de confiance le plus élevé.

### À ajouter dans le cadrage

1. **Règle rédactionnelle** : "Jamais de certitude affirmée sans preuve. Toujours indiquer le niveau de confiance."
2. **Glossaire fondateur** : un tableau traduisant les termes techniques (flag, degraded, heartbeat) en langage humain.
3. **Exemple de diagnostic "faux positif"** : montrer comment Luna réagit quand un diagnostic était basé sur une supposition erronée (ex: "Luna pensait que le téléphone était hors ligne, mais en fait le réseau WiFi avait juste changé").

### Risque principal identifié

> **Si Luna présente une supposition comme une vérité, et que Ludovic sait que cette supposition est fausse (parce qu'il a vécu autre chose sur son téléphone), la confiance dans le système entier s'érode.**

L'Objectif 004 est un cockpit. Un cockpit qui ment ou qui suppose trop devient inutilisable.

---

*Document produit par Kimi Code CLI pour l'objectif 004 — branche `kimi/objectif-004-founder-diagnostics`*
