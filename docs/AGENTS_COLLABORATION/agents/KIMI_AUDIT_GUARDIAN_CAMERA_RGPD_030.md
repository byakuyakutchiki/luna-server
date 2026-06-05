# Audit Guardian Caméra / RGPD / Boutons — Objectif 030

**Agent** : Claude (reprise après quota Kimi épuisé)
**Objectif** : 030
**Type** : Audit Guardian caméra / RGPD / boutons
**Date** : 2026-06-05

---

## Résumé exécutif

Guardian est fonctionnel en tant que système de surveillance **100% GPS**. La caméra n'est pas intégrée dans Guardian — elle n'est jamais demandée, jamais active, jamais connectée aux routes `/api/guardian/*`. Le module de perception visuelle (`core/perception/`) existe mais est totalement isolé. Le GPS, le SOS et le stop fonctionnent correctement avec protections robustes. Un bug P0 concerne `auto_call_112` : accepté dans la config mais jamais exécuté.

---

## Fichiers inspectés

- `static/guardian.html` (1030 lignes)
- `luna_web.py` — routes `/api/guardian/*` (lignes 13879–14260)
- `core/guardian/engine.py` (795 lignes)
- `core/guardian/alerts.py` (108 lignes)
- `core/perception/detector.py` (227 lignes)
- `core/perception/analyzer.py` (288 lignes)

---

## Boutons réels

| Bouton | Handler JS | Endpoint API | Effet | Risque |
|--------|-----------|--------------|-------|--------|
| `▶ Démarrer` (`#btn-start`) | `guardianStart()` | `POST /api/guardian/start` | Crée session GPS, vérifie contacts d'urgence | 🟡 422 si aucun contact — bien |
| `⏹ Arrêter` (`#btn-stop`) | `guardianStop()` | `POST /api/guardian/stop/{sid}` | Stoppe session + `clearWatch()` GPS + ferme WS | ✅ propre |
| `🆘 SOS` (`#btn-sos`) | `openSosModal()` | — (ouvre modal) | Affiche modal de confirmation | ✅ pas d'envoi direct |
| `🆘 Confirmer` (`#sos-go`) | `triggerSOS()` | `POST /api/guardian/sos/{sid}` | SMS réel aux contacts avec position | 🔴 Action sensible — protégée par modal |
| `Annuler` (`#sos-no`) | `closeSosModal()` | — | Ferme modal sans action | ✅ |
| `Autoriser et démarrer` (`#perm-allow`) | `grantPermissions()` | — puis `guardianStart()` | Demande permissions audio + notification | 🟡 voir RGPD |
| `Plus tard` (`#perm-skip`) | `closePerm()` | — | Ferme banner RGPD sans permissions | ✅ |
| `📍 Utiliser ma position` (`#zone-btn`) | `captureZone()` | Mise à jour config locale | Enregistre position actuelle comme zone sûre | ✅ |
| `🔗 Partager` (`#btn-share`) | `sharePosition()` | `GET /api/guardian/share/{sid}` | Génère lien de partage position temps réel | 🟡 partage position = consentement implicite requis |
| `⚙️ Configuration` (`#cfg-toggle-btn`) | `toggleCfg()` | — | Affiche/masque panneau config | ✅ |
| `✅ Oui, ça va` | `verifyResponse(true)` | `POST /api/guardian/verify-response/{sid}` | Annule alerte en attente | ✅ |
| `❌ Besoin d'aide` | `verifyResponse(false)` | `POST /api/guardian/verify-response/{sid}` | Confirme alerte → SMS contacts | 🔴 Action sensible — bouton explicite |
| `Pourquoi ?` (`#rgpd-why`) | `openRgpdModal()` | — | Modal explication RGPD | ✅ bon |
| `📋 Événements` (`#ev-toggle`) | `toggleEvPanel()` | `GET /api/guardian/events/{sid}` | Liste événements de la session | ✅ |

---

## Caméra

**La caméra n'est PAS dans Guardian.**

Analyse de `guardian.html` :
```javascript
// grantPermissions() — seule demande media :
await navigator.mediaDevices.getUserMedia({audio: true});  // ← audio SEULEMENT
// Pas de {video: true}, pas de capture frames, pas de WebSocket vision
```

`core/perception/detector.py` et `core/perception/analyzer.py` existent et implémentent une analyse de scène via OpenAI Vision API (frames base64). Mais :
- **Aucun endpoint `/api/guardian/*` ne les appelle**
- **Aucun WebSocket Guardian ne reçoit de frames vidéo**
- Ces modules ne sont branchés à rien dans le serveur actuel

**Réponse à "Pourquoi la caméra ne s'allume pas côté Guardian" :**
Elle n'a jamais été intégrée. C'est un choix architectural : Guardian = GPS. La perception visuelle est un module distinct non connecté.

---

## GPS

| Aspect | Statut | Détail |
|--------|--------|--------|
| Démarrage | ✅ | `navigator.geolocation.watchPosition()` toutes les updates |
| Envoi serveur | ✅ | `POST /api/guardian/location/{sid}` avec lat, lng, accuracy, speed |
| Arrêt sur Stop | ✅ | `navigator.geolocation.clearWatch(GEO_ID)` dans `guardianStop()` |
| Arrêt WS | ✅ | `WS.close()` dans `guardianStop()` |
| Anti-spam alertes | ✅ | Cooldown 5 min entre deux alertes automatiques |
| Zones sûres | ✅ | Algorithme haversine côté serveur |

---

## SOS

| Aspect | Statut | Détail |
|--------|--------|--------|
| Protection double-clic | ✅ | Modal de confirmation obligatoire |
| Contacts requis avant démarrage | ✅ | 422 si aucun contact d'urgence |
| SMS réel | ✅ | `send_guardian_alerts()` → Twilio réel si `sms_client` présent |
| Contenu SMS | ✅ | Position Google Maps + adresse Nominatim + instructions |
| Limite SMS | 🟡 | Cooldown seulement sur alertes AUTO — SOS manuel pas de limite |
| `auto_call_112` | 🔴 **BUG P0** | Accepté dans config, commentaire dit "Luna tente d'appeler le 112", mais le code ne l'implémente jamais |

```python
# alerts.py ligne 83 :
results = {"sent": [], "failed": [], "call_112_attempted": False}
# auto_call_112 est reçu comme paramètre mais jamais utilisé dans le corps de la fonction
# → call_112_attempted reste toujours False
```

---

## RGPD

| Aspect | Statut | Détail |
|--------|--------|--------|
| Consentement explicite | ✅ | Banner au premier accès, bouton "Pourquoi ?" |
| Données audio demandées | ✅ | `getUserMedia({audio:true})` — vérification vocale |
| Données vidéo demandées | ✅ | Aucune — caméra non demandée |
| Positions GPS stockées | 🟡 | Redis TTL 7 jours — commentaire en tête du fichier dit "24h" = **incohérence** |
| Images stockées | ✅ | Jamais — `detector.py` explicite : "Aucune image n'est stockée" |
| Partage position | 🟡 | `#btn-share` visible sans confirmation RGPD explicite pour le partage |
| Minimisation | ✅ | Seuls lat/lng/accuracy/speed envoyés |
| Droit à l'oubli | 🟡 | Pas de route `DELETE /api/guardian/data/{tenant_id}` |

---

## P0 — Critique (action requise)

### P0.1 — `auto_call_112` non implémenté mais promis

**Fichier** : `core/guardian/alerts.py` ligne 77  
**Risque** : Utilisateur pense que Luna appelle le 112 si `auto_call_112=True` en config. Ce n'est jamais fait. Faux sentiment de sécurité.

**Correction** : Soit implémenter (via Twilio `calls.create` vers "112" — légalement risqué), soit :
```python
# Supprimer auto_call_112 de la config par défaut
# Modifier le commentaire en tête de alerts.py :
# "Luna ne peut PAS appeler le 112 directement. Le SMS indique aux contacts d'appeler le 112."
```

---

## P1 — Important

### P1.1 — Incohérence TTL Redis RGPD

**Fichier** : `core/guardian/alerts.py` ligne 10 dit "jamais au-delà de 24h", mais `engine.py` fait `expire(key, 86400 * 7)` = 7 jours.  
**Correction** : Aligner sur 24h (`86400`) ou sur 7j avec mise à jour de la documentation.

### P1.2 — Banner RGPD ne mentionne pas l'envoi GPS serveur toutes les 10s

`grantPermissions()` demande le micro mais le texte du banner ne dit pas explicitement que les coordonnées GPS sont envoyées à un serveur toutes les mises à jour. À mentionner explicitement.

### P1.3 — Module perception non connecté

`core/perception/detector.py` + `analyzer.py` implémentent une analyse caméra via OpenAI Vision. Si la vision est une feature souhaitée pour Guardian (Ludo a mentionné "caméra ne s'allume pas"), il faut :
1. Décider si la caméra doit être dans Guardian ou rester séparée
2. Si oui : ajouter `getUserMedia({video:true})` avec consentement RGPD spécifique caméra
3. Connecter via WebSocket ou endpoint dédié `POST /api/guardian/frame/{sid}`

---

## Décision Ludovic requise

**Oui.** Deux questions à trancher :

1. **`auto_call_112`** : À supprimer silencieusement (config seulement) ou à implémenter vraiment ? (Twilio peut appeler le 112 en France — mais cela implique une responsabilité légale forte)

2. **Caméra dans Guardian** : La désactivation est-elle intentionnelle ou souhaitez-vous connecter `core/perception/` à Guardian ? Si oui, quel périmètre (vision + GPS, consentement caméra explicite) ?

---

## Actions proposées (sans attendre décision Ludovic)

| Priorité | Action | Fichier | Effort |
|----------|--------|---------|--------|
| P0 | Retirer `auto_call_112` de config senior/home OU ajouter note "non implémenté" | `engine.py` | 5 min |
| P0 | Corriger commentaire `alerts.py` : pas d'appel 112 | `alerts.py` | 2 min |
| P1 | Aligner TTL Redis sur 24h ou corriger commentaire | `engine.py` | 5 min |
| P1 | Ajouter mention GPS dans le texte RGPD banner | `guardian.html` | 10 min |
