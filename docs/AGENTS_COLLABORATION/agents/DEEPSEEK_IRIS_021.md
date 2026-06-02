# DeepSeek — Iris Inference Engine V2 — Objectif 021

Date : 2026-06-02
Agent : DeepSeek
Domaine : contrat technique JS + spec JSON render_type
Niveau : 0 — livrable technique pur

**Objectif : que chaque phrase d'Iris déclenche le bon écran. Toujours. Sans exception.**

---

## Contexte

`inferCommandRenderFromText` est la fonction JS dans `static/simli.html` (ligne ~3373).
Elle analyse le texte d'Iris pour choisir le bon `render_type`.
Actuellement elle détecte trop peu de patterns → Iris atterrit presque toujours sur `context_panel`.

Il faut la réécrire pour être fiable sur **20 types** (12 existants + 8 nouveaux).

---

## 1. Les 20 render_type cibles

### Existants (12) — améliorer la détection

| render_type | Déclencheur actuel | Problème |
|---|---|---|
| `kpi_cards` | 2+ chiffres | Trop large — confond avec n'importe quelle réponse chiffrée |
| `data_board` | "tableau", "liste" | Manque "compare", "classe", "trie" |
| `chart` | "graphique", "courbe" | Manque "évolution", "tendance", "historique" |
| `timeline` | dates | Manque "planning", "calendrier", "échéances" |
| `roadmap` | "phase", "étape" | OK |
| `comparison` | "vs", "versus" | Manque "lequel", "quelle option", "avantages" |
| `action_board` | "checklist", "tâches" | Manque "à faire", "plan d'action", "priorité" |
| `document_draft` | "rédige", "écris" | Manque "prépare", "courrier", "lettre", "note" |
| `document_insight` | "résumé", "analyse" | Manque "ce que ça dit", "explique ce document" |
| `context_panel` | fallback | OK — reste le fallback |
| `missing_info` | "j'ai besoin de" | Manque "pour ça il me faut", "peux-tu préciser" |
| `status_rail` | "état", "santé" | Manque "quotas", "crédits", "services" |

### Nouveaux (8) — définir la détection

| render_type | Déclencheurs |
|---|---|
| `kanban_board` | "kanban", "colonnes tâches", "à faire / en cours / terminé", "tableau de bord projets" |
| `contact_board` | prénom + nom reconnu, "fiche contact", "qui est", "coordonnées de" |
| `map_board` | "adresse", "où est", "itinéraire", "trajet", "localisation", "comment aller" |
| `decision_board` | "compare", "option A option B", "avantages inconvénients", "lequel choisir", "pour et contre" |
| `budget_board` | "budget", "dépenses", "combien j'ai", "mes finances", "solde", "reste" |
| `meeting_board` | "réunion", "compte-rendu", "ordre du jour", "PV", "note de réunion", "session" |
| `media_board` | "fichiers", "documents joints", "pièces jointes", "photos", "images", "captures" |
| `form_board` | "formulaire", "remplis", "complète ce formulaire", "besoin de tes infos" |

---

## 2. Règles de priorité

Les types sont testés dans cet ordre (premier match gagne) :

```
1. action_board      — SMS, email, appel, paiement, réservation (PRIORITAIRE : actions sensibles)
2. missing_info      — Iris dit explicitement qu'il manque quelque chose
3. form_board        — formulaire à remplir
4. decision_board    — comparaison d'options
5. kanban_board      — gestion de tâches en colonnes
6. meeting_board     — réunion, compte-rendu
7. contact_board     — fiche contact
8. budget_board      — finances, dépenses
9. map_board         — localisation, trajet
10. media_board      — fichiers, images
11. document_draft   — rédaction (courrier, lettre, note)
12. document_insight — analyse document existant
13. chart            — graphique, évolution, tendance
14. roadmap          — phases, étapes numérotées
15. timeline         — dates, planning, calendrier
16. kpi_cards        — métriques clés (3+ chiffres importants)
17. data_board       — tableau, liste, comparaison en grille
18. status_rail      — santé services, quotas, crédits
19. comparison       — vs, versus (si pas capturé par decision_board)
20. context_panel    — FALLBACK FINAL (tout ce qui ne matche pas)
```

---

## 3. La fonction complète à livrer

DeepSeek doit livrer cette fonction réécrite de A à Z :

```javascript
function inferCommandRenderFromText(text) {
  // text = texte d'Iris (string, peut être multi-phrases)
  // retourne : string render_type OU null si context_panel
  
  var t = text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  
  // ── 1. action_board ─────────────────────────────────────────────────────
  // ...
  
  // ── 2. missing_info ─────────────────────────────────────────────────────
  // ...
  
  // ... etc pour les 20 types
  
  return null; // → context_panel
}
```

**Contraintes techniques :**
- Pas de dépendances externes (pur JS vanille)
- Les regex doivent supporter l'UTF-8 et les accents via normalize NFD
- Chaque bloc doit être commenté avec le type qu'il détecte
- Faux positifs : mieux vaut rater un type (→ context_panel) que de déclencher le mauvais
- La fonction ne modifie aucune variable globale

---

## 4. `_icsBuildPayload` — extraction de données réelles

Fonction actuelle : produit des payloads génériques (titre + corps).
Version cible : extraire les données du texte pour construire un payload riche.

DeepSeek doit livrer une version améliorée de `_icsBuildPayload` pour ces types prioritaires :

### 4.1 kpi_cards — extraire métriques

```javascript
// Input : "Vous avez 1 240 euros de solde, 892 euros de dépenses et 3 contrats actifs"
// Output :
{
  render_type: "kpi_cards",
  payload: {
    cards: [
      { label: "Solde", value: "1 240 €", trend: null },
      { label: "Dépenses", value: "892 €", trend: null },
      { label: "Contrats", value: "3", trend: null }
    ]
  }
}
```

Regex suggérée : `/(\d[\d\s,.]*)\s*(€|euro|client|contrat|%|km|kg|min|h)\b/gi`
Puis regex label précédent : `/([a-zÀ-ÿ\s]{2,20})\s*:\s*(\d[\d\s,.]*)/gi`

### 4.2 timeline — extraire dates

```javascript
// Input : "Voici vos échéances : EDF le 15 juin, SFR le 12 juin, AXA le 1er juillet"
// Output :
{
  render_type: "timeline",
  payload: {
    events: [
      { label: "EDF", date: "15/06/2026", urgent: true },
      { label: "SFR", date: "12/06/2026", urgent: true },
      { label: "AXA", date: "01/07/2026", urgent: false }
    ]
  }
}
```

Regex dates : `/(\d{1,2}(?:er)?\s+(?:jan|fév|mars|avr|mai|juin|juil|août|sep|oct|nov|déc)\w*)/gi`
Plus : "la semaine prochaine" → date calculée à J+7

### 4.3 chart — extraire séries numériques

```javascript
// Input : "En janvier 1200€, février 980€, mars 1450€, avril 1100€"
// Output :
{
  render_type: "chart",
  payload: {
    type: "bar",
    labels: ["Janvier", "Février", "Mars", "Avril"],
    datasets: [{
      label: "Montant (€)",
      data: [1200, 980, 1450, 1100]
    }]
  }
}
```

### 4.4 decision_board — extraire options

```javascript
// Input : "EDF coûte 89€/mois avec fibre incluse mais engagement 12 mois.
//          Engie coûte 95€/mois sans engagement mais fibre en option."
// Output :
{
  render_type: "decision_board",
  payload: {
    options: [
      {
        name: "EDF",
        pros: ["89€/mois", "Fibre incluse"],
        cons: ["Engagement 12 mois"],
        recommended: true
      },
      {
        name: "Engie",
        pros: ["Sans engagement"],
        cons: ["95€/mois", "Fibre en option"],
        recommended: false
      }
    ],
    recommendation: "EDF — moins cher avec fibre incluse"
  }
}
```

---

## 5. Spec JSON complète — 8 nouveaux render_type

### 5.1 kanban_board

```json
{
  "render_type": "kanban_board",
  "payload": {
    "title": "Tâches projet BESS",
    "columns": [
      {
        "id": "todo",
        "label": "À faire",
        "color": "#8B74F7",
        "cards": [
          { "id": "t1", "title": "Bilan Q1", "tag": "Urgent", "tag_color": "coral" },
          { "id": "t2", "title": "Préparer slides", "tag": null }
        ]
      },
      {
        "id": "doing",
        "label": "En cours",
        "color": "#40E0FF",
        "cards": [
          { "id": "t3", "title": "Analyse concurrence", "tag": "En cours", "tag_color": "cyan" }
        ]
      },
      {
        "id": "blocked",
        "label": "Bloqué",
        "color": "#FF6B7B",
        "cards": [
          { "id": "t4", "title": "Budget validé", "tag": "Attend validation", "tag_color": "amber" }
        ]
      },
      {
        "id": "done",
        "label": "Terminé",
        "color": "#4ade80",
        "cards": [
          { "id": "t5", "title": "Kickoff réunion", "tag": "Terminé", "tag_color": "green" }
        ]
      }
    ]
  }
}
```

### 5.2 contact_board

```json
{
  "render_type": "contact_board",
  "payload": {
    "contact": {
      "id": "c1",
      "name": "Marie Dupont",
      "initials": "MD",
      "company": "BESS",
      "role": "Ingénieure projet",
      "phone": "+33 6 12 34 56 78",
      "email": "marie@bess.fr",
      "trust_level": 4,
      "last_interaction": "il y a 3 jours"
    },
    "history": [
      { "type": "sms", "preview": "Réunion confirmée", "date": "28/05" },
      { "type": "call", "preview": "Appel — 12 min", "date": "20/05" }
    ],
    "actions": [
      { "label": "Appeler", "intent": "call_contact", "requires_confirmation": true },
      { "label": "Email", "intent": "send_email", "requires_confirmation": true },
      { "label": "SMS", "intent": "send_sms", "requires_confirmation": true }
    ]
  }
}
```

### 5.3 map_board

```json
{
  "render_type": "map_board",
  "payload": {
    "address": "12 rue de la Paix, 75002 Paris",
    "label": "Cabinet Dr. Martin",
    "lat": 48.8698,
    "lng": 2.3310,
    "distance_km": 2.4,
    "duration_walk_min": 8,
    "duration_car_min": 12,
    "maps_url": "https://maps.google.com/?q=12+rue+de+la+Paix+Paris"
  }
}
```

### 5.4 decision_board

```json
{
  "render_type": "decision_board",
  "payload": {
    "title": "Comparer les offres énergie",
    "options": [
      {
        "name": "EDF",
        "pros": ["89€/mois", "Fibre incluse", "App mobile"],
        "cons": ["Engagement 12 mois"],
        "recommended": true,
        "score": 82
      },
      {
        "name": "Engie",
        "pros": ["Sans engagement", "App mobile"],
        "cons": ["95€/mois", "Fibre en option"],
        "recommended": false,
        "score": 67
      }
    ],
    "recommendation": "EDF — meilleur rapport qualité/prix avec fibre incluse",
    "actions": [
      { "label": "Choisir EDF", "intent": "select_option_a", "requires_confirmation": true },
      { "label": "Choisir Engie", "intent": "select_option_b", "requires_confirmation": true }
    ]
  }
}
```

### 5.5 budget_board

```json
{
  "render_type": "budget_board",
  "payload": {
    "period": "Juin 2026",
    "kpis": [
      { "label": "Solde estimé", "value": "1 240 €", "alert": false },
      { "label": "Dépenses", "value": "892 €", "alert": false },
      { "label": "Reste", "value": "348 €", "alert": true, "alert_msg": "< 30% du budget" }
    ],
    "categories": [
      { "name": "Loyer", "amount": 650, "percent": 73 },
      { "name": "Énergie", "amount": 89, "percent": 10 },
      { "name": "Alimentation", "amount": 65, "percent": 7 },
      { "name": "Autres", "amount": 88, "percent": 10 }
    ],
    "actions": [
      { "label": "Voir détail", "intent": "show_budget_detail" },
      { "label": "Alertes budget", "intent": "manage_budget_alerts" }
    ]
  }
}
```

### 5.6 meeting_board

```json
{
  "render_type": "meeting_board",
  "payload": {
    "title": "Session VoltAI",
    "date": "02/06/2026",
    "time": "14h30",
    "participants": [
      { "name": "Ludovic", "role": "owner", "initials": "L" },
      { "name": "Marie", "role": "trusted", "initials": "M" },
      { "name": "M. Dupont", "role": "guest", "initials": "D" }
    ],
    "agenda": [
      { "item": "Bilan BESS Q1", "done": true },
      { "item": "Budget 2027", "done": false },
      { "item": "Recrutement", "done": false }
    ],
    "decisions": [
      "Budget approuvé : 240 000€",
      "Prochain point : 15/06"
    ],
    "actions": [
      { "label": "Exporter CR", "intent": "export_meeting_notes" },
      { "label": "Envoyer aux participants", "intent": "send_meeting_notes", "requires_confirmation": true }
    ]
  }
}
```

### 5.7 media_board

```json
{
  "render_type": "media_board",
  "payload": {
    "title": "Fichiers (3)",
    "files": [
      { "name": "Compte-rendu.pdf", "type": "pdf", "size": "245 Ko", "url": null },
      { "name": "Plan_BESS.png", "type": "image", "size": "1,2 Mo", "url": null },
      { "name": "Budget_2027.xlsx", "type": "spreadsheet", "size": "89 Ko", "url": null }
    ],
    "actions": [
      { "label": "Tout télécharger", "intent": "download_all_files" }
    ]
  }
}
```

### 5.8 form_board

```json
{
  "render_type": "form_board",
  "payload": {
    "title": "Demande CAF",
    "description": "Remplissez ce formulaire pour votre démarche",
    "fields": [
      {
        "id": "nom",
        "label": "Nom complet",
        "type": "text",
        "required": true,
        "prefill": "Ludovic Saint-Louis",
        "placeholder": "Votre nom"
      },
      {
        "id": "allocataire",
        "label": "Numéro allocataire",
        "type": "text",
        "required": true,
        "prefill": null,
        "placeholder": "Ex : 1234567A"
      },
      {
        "id": "motif",
        "label": "Motif",
        "type": "radio",
        "required": false,
        "options": ["Changement de situation", "Demande d'aide", "Autre"]
      }
    ],
    "actions": [
      { "label": "Remplir automatiquement", "intent": "autofill_form" },
      { "label": "Envoyer", "intent": "submit_form", "requires_confirmation": true }
    ]
  }
}
```

---

## 6. Ce que DeepSeek doit livrer

Fichier de livraison : `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_IRIS_021_LIVRABLE.md`

Contenu attendu :

### 6.1 `inferCommandRenderFromText` — version complète

Bloc JavaScript autonome, prêt à remplacer l'existant dans `static/simli.html`.
20 types. Regex commentées. Pas de dépendances.

### 6.2 `_icsBuildPayload` — version améliorée

Extrait les données réelles du texte pour les 8 types prioritaires :
`kpi_cards`, `timeline`, `chart`, `decision_board`, `budget_board`, `kanban_board`, `meeting_board`, `contact_board`

### 6.3 Matrice de test

Tableau de 40 phrases test → render_type attendu.

Format :

| Phrase | render_type attendu | Règle qui déclenche |
|---|---|---|
| "Voici vos 3 factures impayées..." | kpi_cards | 3+ métriques numériques |
| "Comparons EDF et Engie..." | decision_board | "comparons" + 2 entités |
| ... | ... | ... |

---

## Règles non-négociables

- Ne pas modifier `luna_web.py`, `web_voice_bridge.py`, `session_manager.py`
- Ne pas déployer
- Ne pas changer la signature de fonction (entrée/sortie identiques)
- Les faux négatifs (→ context_panel) sont tolérables. Les faux positifs (mauvais type) ne le sont pas.
- Chaque regex doit être testée mentalement sur 3 exemples positifs + 1 négatif avant d'être livrée

---

*Lead technique : Claude — 2 juin 2026*
*Domaine DeepSeek : contrat technique JS uniquement*
