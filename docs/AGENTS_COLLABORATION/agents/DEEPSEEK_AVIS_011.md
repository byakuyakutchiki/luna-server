# DeepSeek — Avis Objectif 011 — Audit technique Services

**Date** : 2026-05-26
**Objectif** : Audit complet onglet Services / Conciergerie
**Rôle** : Audit technique frontend/backend, réalité du code
**Règle absolue** : Tester, observer, remonter — Ne pas coder

---

## Mission DeepSeek

Auditer la chaîne complète :
```
Carte HTML → Handler JS → /api/concierge/action → Tool Python → Service externe → Retour utilisateur
```

Répondre aux questions exactes : Ça fonctionne ou pas ? Où ça casse ? Quelles dépendances manquent ?

**Interdit** : Coder directement, tester actions réelles, déployer.

---

## Phase 1 — Inventaire des cartes frontend

### À investiguer dans `static/index.html`

1. **Localiser le panneau Services**
   ```
   Chercher : <div id="tab-conciergerie"> ou équivalent
   Chercher : class="conc-card" ou data-action
   ```
   - Combien de cartes visibles ?
   - Chaque carte a-t-elle un DOM unique (id, data-*) ?
   - Quelle structure : `<button>` vs `<div onclick>` vs card clickable ?

2. **Pour chaque carte**
   - Texte affiché à l'utilisateur
   - ID ou data-action
   - Quel handler JavaScript est appelé
   - Quels paramètres sont passés

3. **Exemple à documenter**
   ```html
   <div class="conc-card" data-action="search-flights">
     <h3>Vols</h3>
     <p>Trouver un vol</p>
   </div>
   <!-- Handler ? searchFlights() ou postConciergeAction('search-flights') ? -->
   ```

### Livrables Phase 1

Tableau frontend complet :

| Carte | ID/Selector | Handler JS | Paramètres | Endpoint appelé |
|---|---|---|---|---|
| Vols | ? | ? | ? | ? |
| Hôtels | ? | ? | ? | ? |
| Restaurants | ? | ? | ? | ? |
| Recherche web | ? | ? | ? | ? |
| Autour de moi | ? | ? | ? | ? |
| Météo | ? | ? | ? | ? |
| Actualités | ? | ? | ? | ? |
| SMS | ? | ? | ? | ? |
| Email | ? | ? | ? | ? |
| Appel | ? | ? | ? | ? |
| Visio | ? | ? | ? | ? |
| Alerte urgence | ? | ? | ? | ? |
| Rappel | ? | ? | ? | ? |
| Note | ? | ? | ? | ? |
| Document | ? | ? | ? | ? |
| Contacts | ? | ? | ? | ? |
| Formulaires | ? | ? | ? | ? |
| Stats | ? | ? | ? | ? |
| Missions | ? | ? | ? | ? |
| Badges | ? | ? | ? | ? |
| Amis en ligne | ? | ? | ? | ? |

---

## Phase 2 — Audit des handlers JavaScript

### Questions pour chaque handler

1. **Existe-t-il** dans `static/index.html` ou un fichier JS séparé ?
2. **Appelle-t-il** `/api/concierge/action` ou un endpoint différent ?
3. **Paramètres envoyés** :
   ```javascript
   // Exemple attendu ?
   fetch('/api/concierge/action', {
     method: 'POST',
     body: JSON.stringify({
       action: 'search_flights',
       payload: { origin: 'CDG', destination: 'NYC', date: '2026-06-01' }
     })
   })
   ```
   - L'action correspond-elle à ce qu'attend le backend ?
   - Le payload est-il correct ?
   - Existe-t-il un timeout ?

4. **Affichage résultat** :
   - Où s'affiche le résultat (modale, inline, nouveau tab) ?
   - Quel JSON est attendu en retour ?
   - Comment s'affiche-t-il si succès ? si erreur ?

### Cas à tester en audit

**Non destructif** (OK de tester) :
- Clic sur "Météo" → Affiche-t-il la météo locale ?
- Clic sur "Actualités" → Affiche-t-il les titres ?
- Clic sur "Recherche web" → Popup de saisie ?

**Destructif** (NE PAS TESTER) :
- SMS / Email / Appel
- Alerte urgence
- Paiement / Réservation

---

## Phase 3 — Audit du backend

### Endpoint `/api/concierge/action`

Dans `luna_web.py`, chercher :

```python
@app.post("/api/concierge/action")
def concierge_action(request):
    # Quelle structure ?
    # Quels paramètres attendus ?
```

1. **Actions implémentées**
   - Quelles actions sont gérées par le endpoint ?
   - Y a-t-il un switch/case ou dictionnaire d'actions ?
   - Chaque action existe-t-elle ou retourne-t-elle `action_not_found` ?

2. **Pour chaque action, vérifier**
   ```python
   if action == 'search_flights':
       # Appelleune fonction dédiée ?
       result = search_flights(payload)
   elif action == 'send_sms':
       # Appelleun tool Twilio ?
       result = send_sms_action(payload)
   else:
       # Retour erreur ?
       return {"error": "Unknown action"}
   ```

3. **Dépendances externes**
   - Quels services sont appelés (Duffel, Serper, Twilio, etc.) ?
   - Sont-ils configurés (variables d'environnement) ?
   - Existe-t-il un fallback si indisponibles ?

### Retours JSON attendus

Vérifier la structure :

```python
# Succès
{"ok": True, "result": {...}, "action": "search_flights"}

# Erreur
{"ok": False, "error": "No API key for Duffel", "action": "search_flights"}

# Non configuré
{"ok": False, "status": "not_configured", "action": "search_flights"}
```

---

## Phase 4 — Audit tools et intégrations

### Chercher les tools

1. **Dans `integrations/`** :
   - Y a-t-il des fichiers pour Serper, Duffel, Twilio, etc. ?
   - Chaque tool appelle-t-il correctement son API ?
   - Gèrent-ils les erreurs (timeout, rate limit, 401 unauthorized) ?

2. **Dans `core/`** :
   - Des functions pour générer documents, créer rappels, etc. ?

### Vérifier les dépendances

Pour chaque service, noter :
- Clé API requise (présente ou absente ?)
- Endpoint utilisé
- Limitation connue (rate limit, quota)
- Fallback ou dégradation si service down

---

## Phase 5 — Identifier les points de rupture

### Questions critiques

1. **Si le service externe est down** (ex: Duffel indisponible)
   - Que voit l'utilisateur ? Erreur lisible ou crash silent ?
   - Le cerveau APK remonte-t-il l'erreur ?
   - Existe-t-il un cache ou fallback ?

2. **Si les paramètres sont mauvais** (ex: aucun hôtel trouvé)
   - Que retourne le backend ? `{"ok": false}` ou exception ?
   - Affichage : "Aucun hôtel disponible" ou rien ?

3. **Si l'action est sensible** (ex: SMS)
   - Comment vérifie-t-on que la permission utilisateur existe ?
   - Existe-t-il une trace audit (journalisation) ?
   - Confirmation affichée avant envoi ?

---

## Tableau de synthèse déjà à remplir

### Audit rapide par catégorie

| Catégorie | Service | Frontend OK ? | Handler OK ? | Backend implémenté ? | Dépendance | État |
|---|---|---|---|---|---|---|
| Lecture seule | Météo | ? | ? | ? | OpenWeather ? | ? |
| Lecture seule | Actualités | ? | ? | ? | NewsAPI ? | ? |
| Requête externe | Recherche web | ? | ? | ? | Serper | ? |
| Requête externe | Vols | ? | ? | ? | Duffel | ? |
| Requête externe | Hôtels | ? | ? | ? | Duffel | ? |
| Requête externe | Restaurants | ? | ? | ? | Serper | ? |
| Requête externe | Autour de moi | ? | ? | ? | Serper | ? |
| Action réelle | SMS | ? | ? | ? | Twilio | ? |
| Action réelle | Email | ? | ? | ? | SMTP/Sendgrid | ? |
| Action réelle | Appel | ? | ? | ? | Twilio | ? |
| Action réelle | Visio | ? | ? | ? | API custom | ? |
| Action réelle | Alerte urgence | ? | ? | ? | DB + notifications | ? |
| Création locale | Rappel | ? | ? | ? | DB | ? |
| Création locale | Note | ? | ? | ? | DB | ? |
| Génération | Document | ? | ? | ? | LLM + File storage | ? |
| Requête DB | Contacts | ? | ? | ? | DB | ? |
| Redirection | Formulaires | ? | ? | ? | /formulaires | ? |
| Requête DB | Stats | ? | ? | ? | DB | ? |
| Requête DB | Missions | ? | ? | ? | DB | ? |
| Requête DB | Badges | ? | ? | ? | DB | ? |
| Requête DB | Amis en ligne | ? | ? | ? | Websocket ? | ? |

---

## Livrables DeepSeek

1. **Inventaire frontend**
   - Toutes les cartes listées avec sélecteurs DOM
   - Handlers JavaScript documentés
   - Paramètres passés au backend

2. **Tableau actions backend**
   - Actions implémentées vs manquantes
   - Dépendances externes identifiées
   - Retours JSON documentés

3. **Points de rupture identifiés**
   - Services qui crashent l'interface
   - Erreurs silencieuses
   - Timeouts non gérés
   - Permissions manquantes

4. **Recommandations de test**
   - Quoi tester en non destructif
   - Quoi ne JAMAIS tester sans validation
   - Cas limites à vérifier

---

## Interdictions

❌ Ne pas appeler `/api/concierge/action` pour envoyer SMS/email/appel réels.
❌ Ne pas refondre le code.
❌ Ne pas tester sur le terrain.
❌ Ne pas déployer.
✅ Juste observer et remonter.

---

## Statut

⏳ En attente d'investigation dans le code.

**Prochaines étapes** :
- Claude utilise cet audit pour synthèse
- Kimi utilise pour audit UX
- Cursor utilise pour audit mobile

**Status** : 🔍 Investigation technique en cours
