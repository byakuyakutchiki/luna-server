# Avis Kimi — Objectif 008 DeepSeek temps réel dans l'expérience APK

Agent : Kimi Code CLI (kimi-k2.6)
Mission : Textes cockpit fondateur pour les diagnostics DeepSeek
Date : 2026-05-25
Branche : `kimi/objectif-008-deepseek-temps-reel`
Contexte : DeepSeek API appelée côté serveur sur incident APK — diagnostic structuré affiché dans le cockpit

---

## 1. Principe rédactionnel pour DeepSeek

DeepSeek est une IA externe appelée par le serveur Luna. Elle n'est pas infaillible.
Le cockpit doit exprimer clairement :

- **Ce que DeepSeek a observé** (faits bruts, événements reçus)
- **Ce que DeepSeek conclut** (hypothèse, avec un niveau de confiance)
- **Ce que DeepSeek recommande** (action, jamais automatique)
- **Ce que DeepSeek ne peut pas** (limites, incertitudes)
- **Si Ludovic doit valider** (oui/non, avec pourquoi)

**Règle d'or :** Le cockpit ne doit jamais présenter un diagnostic DeepSeek comme une vérité absolue. Toujours utiliser "DeepSeek observe", "DeepSeek pense", jamais "Le problème est".

---

## 2. Libellés des zones de diagnostic

### Zones techniques → Libellés cockpit

| Zone technique | Libellé cockpit | Couleur proposée |
|---|---|---|
| `apk` | Problème côté application | #f87171 |
| `webview` | Problème côté WebView | #fbbf24 |
| `cache` | Problème de cache | #fbbf24 |
| `serveur` | Problème côté serveur Luna | #f87171 |
| `openai` | Problème côté OpenAI Realtime | #f87171 |
| `ui` | Problème d'affichage ou interface | #60a5fa |
| `inconnue` | Zone non déterminée | #a78bfa |

---

## 3. Libellés des niveaux de risque

| Risque technique | Libellé cockpit | Style |
|---|---|---|
| `faible` | Risque faible | Texte normal, icône ℹ️ |
| `moyen` | Risque moyen | Texte orange, icône ⚠️ |
| `élevé` | Risque élevé | Texte rouge, icône 🔴, possible alerte |

---

## 4. Textes cockpit par zone de diagnostic

### Format standard DeepSeek

```
🤖 Diagnostic DeepSeek — [Zone] — [Risque]
Déclenché à [heure] · Basé sur [X] événements sur [Y] secondes

DeepSeek observe :
[liste des faits bruts, événements reçus]

DeepSeek pense :
[diagnostic avec incertitude]

DeepSeek recommande :
[action minimale]

DeepSeek ne peut pas :
[limites]

[Validation Ludovic : OUI / NON]
[Si oui : pourquoi + bouton de validation]
```

---

### Zone `apk` — Problème côté application

**Exemple : APK obsolète détectée par DeepSeek**

```
🤖 Diagnostic DeepSeek — Application — Risque moyen
Déclenché à 13:04:22 · Basé sur 8 événements sur 15 secondes

DeepSeek observe :
• Heartbeat reçu il y a 12 secondes
• Version APK : 2.7
• Version attendue : 2.8
• Aucun événement vocal reçu

DeepSeek pense :
L'APK installée est probablement une version ancienne. La télémétrie
voix complète n'est peut-être pas active dans cette version.

DeepSeek recommande :
Installer la dernière APK depuis le serveur, puis refaire le test.

DeepSeek ne peut pas :
Forcer la mise à jour à distance.

Validation Ludovic requise : NON
Cette action peut être faite directement par Ludovic.
```

---

### Zone `webview` — Problème côté WebView

**Exemple : WebView Android bloque AudioWorklet**

```
🤖 Diagnostic DeepSeek — WebView — Risque élevé
Déclenché à 13:04:46 · Basé sur 11 événements sur 24 secondes

DeepSeek observe :
• Bouton vocal pressé
• Token présent
• Microphone autorisé
• WebSocket ouvert
• Premier audio envoyé
• WebSocket fermé après 5 secondes
• User-Agent : LunaApp/2.8
• ScriptProcessorNode utilisé (fallback AudioWorklet)

DeepSeek pense :
La WebView Android utilise le fallback ScriptProcessorNode au lieu
d'AudioWorklet. Ce fallback peut être moins stable et provoquer des
fermetures WebSocket prématurées sous certaines versions Android.

DeepSeek recommande :
1. Tester la voix depuis Chrome desktop pour comparer
2. Si desktop fonctionne → problème WebView Android spécifique
3. Vérifier si une mise à jour Android WebView est disponible
4. Envisager un workaround côté serveur pour stabiliser le fallback

DeepSeek ne peut pas :
Modifier le comportement de la WebView Android.
Forcer l'utilisation d'AudioWorklet si la WebView ne le supporte pas.

Validation Ludovic requise : OUI
La correction nécessite un changement côté serveur (bridge vocal)
ou une mise à jour Android système. Ne pas corriger sans validation.
```

---

### Zone `cache` — Problème de cache

**Exemple : Frontend obsolète chargé**

```
🤖 Diagnostic DeepSeek — Cache — Risque moyen
Déclenché à 13:04:22 · Basé sur 5 événements sur 8 secondes

DeepSeek observe :
• Heartbeat reçu
• Build frontend vu : 2026-05-20-old-build
• Build attendu : 2026-05-25-voice-fix
• Cache WebView : non vidé depuis le dernier déploiement

DeepSeek pense :
L'APK charge un index.html obsolète depuis le cache de la WebView.
Les corrections vocales du dernier déploiement ne sont donc pas
appliquées sur ce téléphone.

DeepSeek recommande :
Utiliser le geste pull-to-refresh fondateur (swipe vers le bas)
pour forcer le vidage du cache et le rechargement de la page.

DeepSeek ne peut pas :
Vider le cache à distance sans action de l'utilisateur.

Validation Ludovic requise : NON
Le geste de maintenance APK est conçu pour être utilisé directement
par Ludovic sans validation technique.
```

---

### Zone `serveur` — Problème côté serveur Luna

**Exemple : Bridge vocal ne relaye pas la réponse**

```
🤖 Diagnostic DeepSeek — Serveur Luna — Risque élevé
Déclenché à 13:04:46 · Basé sur 11 événements sur 24 secondes

DeepSeek observe :
• Bouton vocal pressé
• Token présent
• Microphone autorisé
• WebSocket ouvert
• Premier audio envoyé
• WebSocket fermé après 5 secondes
• Aucun audio reçu du serveur
• Logs serveur : connexion OpenAI établie
• Logs serveur : réponse audio générée par OpenAI
• Logs serveur : tentative d'envoi au client

DeepSeek pense :
Le serveur Luna reçoit bien l'audio du téléphone, le transmet à
OpenAI, reçoit une réponse... mais ne parvient pas à la renvoyer
au téléphone avant la fermeture du WebSocket. Le timeout côté
serveur (5s) est peut-être trop court.

DeepSeek recommande :
1. Vérifier les logs serveur `/ws/luna-voice` à 13:04:25-30
2. Augmenter le timeout de relay audio côté serveur
3. Vérifier que le ping/pong WebSocket ne coupe pas la connexion
   pendant le traitement OpenAI

DeepSeek ne peut pas :
Accéder aux logs serveur en temps réel.
Modifier la configuration du bridge vocal.

Validation Ludovic requise : OUI
La correction nécessite une modification du code serveur
(web_voice_bridge.py) et un redéploiement Cloud Run.
```

---

### Zone `openai` — Problème côté OpenAI Realtime

**Exemple : Quota épuisé ou clé invalide**

```
🤖 Diagnostic DeepSeek — OpenAI Realtime — Risque élevé
Déclenché à 13:04:46 · Basé sur 11 événements sur 24 secondes

DeepSeek observe :
• Bouton vocal pressé
• Token présent
• Microphone autorisé
• WebSocket ouvert
• Premier audio envoyé
• WebSocket fermé après 5 secondes
• Aucun audio reçu du serveur
• Logs serveur : erreur 401 sur connexion OpenAI

DeepSeek pense :
Le serveur ne parvient pas à s'authentifier auprès d'OpenAI
Realtime. La clé API est peut-être invalide, expirée, ou le quota
est épuisé.

DeepSeek recommande :
1. Vérifier la clé OPENAI_API_KEY dans l'onglet Clés
2. Vérifier le quota voix restant dans l'onglet Quotas
3. Vérifier le statut OpenAI sur status.openai.com
4. Si le quota est épuisé → attendre le renouvellement ou
   changer de clé

DeepSeek ne peut pas :
Vérifier la validité de la clé API OpenAI.
Renouveler le quota.

Validation Ludovic requise : NON (si clé à vérifier)
Validation Ludovic requise : OUI (si changement de clé ou quota)
```

---

### Zone `ui` — Problème d'affichage ou interface

**Exemple : Bouton Déconnexion coupé, bouton vocal invisible**

```
🤖 Diagnostic DeepSeek — Interface — Risque faible
Déclenché à 13:04:22 · Basé sur 3 événements sur 5 secondes

DeepSeek observe :
• Heartbeat reçu
• Écran actif : home
• Bouton vocal : détecté dans le DOM
• Bouton Déconnexion : tronqué (width insuffisante)
• Résolution écran : 360x780 (petit écran)

DeepSeek pense :
Le CSS de l'interface ne s'adapte pas correctement aux petits
écrans. Le bouton Déconnexion est coupé et le bouton vocal est
peut-être difficile à atteindre.

DeepSeek recommande :
1. Vérifier l'affichage sur le téléphone de Ludovic
2. Ajuster les media queries CSS pour les écrans < 400px
3. Tester le scroll horizontal si nécessaire

DeepSeek ne peut pas :
Modifier le CSS directement.
Voir l'écran du téléphone.

Validation Ludovic requise : OUI
La correction nécessite une modification du frontend
(static/index.html) et un déploiement.
```

---

### Zone `inconnue` — Zone non déterminée

**Exemple : Trop peu d'événements pour conclure**

```
🤖 Diagnostic DeepSeek — Zone non déterminée — Risque moyen
Déclenché à 13:04:22 · Basé sur 1 événement sur 2 secondes

DeepSeek observe :
• Heartbeat reçu
• Un seul événement reçu : voice_button_clicked
• Aucun événement suivant dans les 20 secondes suivantes

DeepSeek pense :
La télémétrie est insuffisante pour déterminer la zone exacte
du problème. Le clic a été enregistré mais aucun événement
suivant n'a été reçu.

DeepSeek recommande :
1. Vérifier que la télémétrie vocale est bien activée
   (version APK 2.8+ requise)
2. Si la version est correcte → le problème est probablement
   entre le clic et le démarrage de startVoice()
3. Consulter les logs console de la WebView si possible

DeepSeek ne peut pas :
Conclure sans suffisamment d'événements.
Accéder à la console JavaScript du téléphone.

Validation Ludovic requise : NON
Ce diagnostic est informatif. L'action recommandée est de
vérifier la version APK et d'activer les logs console.
```

---

## 5. Affichage de la validation Ludovic

### Format dans le cockpit

```javascript
if (d.validation_ludovic_requise) {
  html += '<div style="margin-top:12px;padding:12px;border:1px solid #fbbf2440;border-radius:8px;background:#1a0e00;">';
  html += '<div style="color:#fbbf24;font-size:0.82em;font-weight:600;margin-bottom:6px;">⚠️ Validation Ludovic requise</div>';
  html += '<div style="color:#aaa;font-size:0.78em;">';
  html += 'Cette correction nécessite une modification du code ou un déploiement. ';
  html += 'Ne pas appliquer sans accord explicite.';
  html += '</div>';
  html += '<button class="btn btn-outline btn-yellow" style="margin-top:8px;font-size:0.75em;" onclick="validateDeepSeekAction(\'' + d.diagnostic_id + '\')">✓ Je valide cette action</button>';
  html += '</div>';
}
```

### Textes par type d'action requise

| Type d'action | Texte validation |
|---|---|
| Déploiement Cloud Run | "Cette correction nécessite un déploiement Cloud Run. Valider uniquement si le test a été fait en local." |
| Rebuild APK | "Cette correction nécessite de reconstruire l'APK. Valider uniquement si le test APK a été validé." |
| Modification serveur | "Cette correction touche au serveur Luna. Valider uniquement après revue du code." |
| Modification frontend | "Cette correction touche à l'interface. Valider uniquement si le rendu mobile a été vérifié." |
| Changement clé API | "Cette correction nécessite de modifier une clé API. Valider uniquement si la nouvelle clé est testée." |
| Action utilisateur directe | "Cette action peut être faite directement par Ludovic sans validation technique." |

---

## 6. Textes pour le journal fondateur

### Format d'entrée journal

```json
{
  "ts": "2026-05-25 18:47:05",
  "source": "deepseek_diagnostic",
  "zone": "serveur",
  "risque": "élevé",
  "diagnostic": "Timeout bridge vocal côté serveur",
  "validation_requise": true,
  "valide_par": null,
  "statut": "en_attente"
}
```

### Texte lisible dans le journal

```
18:47:05 — 🤖 DeepSeek — Serveur — Risque élevé
Diagnostic : Timeout bridge vocal côté serveur
Action : En attente de validation Ludovic
```

Après validation :
```
18:47:05 — 🤖 DeepSeek — Serveur — Risque élevé
Diagnostic : Timeout bridge vocal côté serveur
Validé par Ludovic à 18:52:12 — Action appliquée
```

---

## 7. Règles anti-gaspillage tokens (affichage cockpit)

DeepSeek ne doit pas être appelé inutilement. Le cockpit doit afficher :

```
🤖 DeepSeek — Mode veille
Dernier diagnostic : il y a 45 minutes
Prochains déclencheurs possibles :
• WebSocket fermé prématurément
• Aucun audio reçu après envoi
• Erreur JS critique
• Mismatch version APK
```

Et quand DeepSeek est appelé :
```
🤖 DeepSeek — Diagnostic en cours...
Analyse de 11 événements sur 24 secondes...
```

---

## 8. Synthèse et livrables

### Ce document apporte

1. **7 zones de diagnostic** avec libellés français et couleurs
2. **3 niveaux de risque** avec libellés et icônes
3. **7 scénarios complets** DeepSeek observe/pense/recommande/ne peut pas
4. **Format validation Ludovic** avec 6 types d'actions
5. **Format journal fondateur** lisible
6. **Règles anti-gaspillage** pour l'affichage mode veille/incident

### Coché pour l'objectif 008

- [x] Textes cockpit pour DeepSeek observe
- [x] Textes cockpit pour DeepSeek suppose
- [x] Textes cockpit pour DeepSeek recommande
- [x] Textes cockpit pour DeepSeek ne peut pas
- [x] Textes pour validation Ludovic requise
- [x] Libellés zones (apk, webview, cache, serveur, openai, ui, inconnue)
- [x] Libellés risques (faible, moyen, élevé)
- [x] Journal fondateur formaté
- [x] Règles anti-gaspillage tokens

---

*Document produit par Kimi Code CLI pour l'objectif 008 — branche `kimi/objectif-008-deepseek-temps-reel`*
