# DeepSeek — Contrat technique Iris Command Screen V1 — Objectif 019

Date : 2026-06-02  
Agent : DeepSeek  
Type : contrat technique Iris Command Screen V1  
Niveau : 0  

## Résumé agent

Agent : DeepSeek  
Objectif : 019  
Type : contrat technique Iris Command Screen V1  
Résumé : Spécification complète des 6 `render_type` : `data_board`, `document_draft`, `action_board`, `context_panel`, `missing_info`, `status_rail`. Format JSON exact pour chaque type. Contrat WebSocket client/serveur. Garde-fous : actions avec `requires_confirmation` obligatoire. Règles interdites définies. Prêt pour implémentation par Claude après maquettes Kimi.  
Fichier concerné : `luna_web.py` WebSocket, `static/iris-command-screen.html` ou `static/simli.html`  
Risque : si le LLM renvoie du texte brut au lieu du JSON structuré, le contrat est cassé.  
Décision Ludovic requise : oui — valider le contrat technique.  
Action proposée :

1. Kimi maquette les 6 panneaux.
2. Codex synthétise et tranche le scope V1.
3. Claude implémente le contrat.

---

## 1. Architecture du flux

Flux cible :

```text
Utilisateur parle ou écrit
-> STT / texte
-> LLM analyse intention
-> payload structuré
-> frontend affiche dans le bon panneau
```

Règle absolue :

Le LLM ne doit pas répondre en texte brut quand un rendu est attendu. Il doit produire un `render_type` et un `payload`.

## 2. Les 6 render_type

### 2.1 data_board

Quand : montrer, afficher, lister, comparer, présenter.

```json
{
  "render_type": "data_board",
  "payload": {
    "title": "Mes documents",
    "layout": "grid",
    "columns": ["Nom", "Date", "Catégorie", "Statut"],
    "rows": [
      ["Facture EDF", "15/05/2026", "Énergie", "À payer"],
      ["Contrat assurance", "01/01/2026", "Maison", "Actif"],
      ["Devis plombier", "20/05/2026", "Travaux", "En attente"]
    ],
    "summary": "3 documents. 1 à payer, 1 en attente.",
    "actions": [
      { "label": "Trier", "intent": "trier_documents" },
      { "label": "Filtrer", "intent": "filtrer_documents" }
    ]
  }
}
```

Rendu attendu : tableau ou grille de verre, lignes espacées, statut avec pastille, résumé en bas.

### 2.2 document_draft

Quand : rédiger, écrire, préparer, créer.

```json
{
  "render_type": "document_draft",
  "payload": {
    "title": "Courrier CAF",
    "format": "letter",
    "recipient": "CAF de Paris",
    "body": "Madame, Monsieur,\n\nJe vous écris concernant mon dossier...",
    "placeholders": ["[NOM]", "[NUMÉRO ALLOCATAIRE]"],
    "actions": [
      { "label": "Modifier", "intent": "modifier_brouillon" },
      { "label": "Sauvegarder", "intent": "sauvegarder_document" },
      { "label": "Télécharger", "intent": "telecharger_document" },
      { "label": "Envoyer", "intent": "envoyer_document", "requires_confirmation": true }
    ]
  }
}
```

Rendu attendu : page de document lisible, placeholders en surbrillance, barre d'actions.

### 2.3 action_board

Quand : envoyer, programmer, confirmer, exécuter.

```json
{
  "render_type": "action_board",
  "payload": {
    "action_type": "send_sms",
    "summary": "Envoyer un SMS à Marie : \"Je serai là à 20h\"",
    "details": {
      "recipient": "Marie",
      "message": "Je serai là à 20h",
      "cost": "1 SMS"
    },
    "requires_confirmation": true,
    "deadline": null,
    "actions": [
      { "label": "Confirmer", "intent": "confirmer_action", "style": "primary" },
      { "label": "Modifier", "intent": "modifier_action" },
      { "label": "Annuler", "intent": "annuler_action", "style": "danger" }
    ]
  }
}
```

Rendu attendu : carte action claire, confirmation obligatoire, aucun déclenchement automatique.

### 2.4 context_panel

Quand : expliquer, résumer, analyser, décrire.

```json
{
  "render_type": "context_panel",
  "payload": {
    "title": "Facture EDF du 15/05/2026",
    "source": "document_123",
    "sections": [
      { "heading": "Montant", "body": "142,50 € TTC" },
      { "heading": "Échéance", "body": "15 juin 2026" },
      { "heading": "Consommation", "body": "245 kWh, en baisse de 12 % par rapport au mois dernier" }
    ],
    "summary": "Cette facture est dans la norme. Votre consommation baisse.",
    "actions": [
      { "label": "Approfondir", "intent": "expliquer_plus" },
      { "label": "Comparer", "intent": "comparer_factures" }
    ]
  }
}
```

Rendu attendu : sections empilées, résumé clair, actions non sensibles.

### 2.5 missing_info

Quand : question incomplète, intention floue, paramètres manquants.

```json
{
  "render_type": "missing_info",
  "payload": {
    "question": "À qui voulez-vous envoyer ce message ?",
    "missing_fields": ["destinataire"],
    "provided_fields": {
      "message": "Je serai là à 20h"
    },
    "suggestions": [
      { "label": "Marie", "intent": "selectionner_marie" },
      { "label": "Pierre", "intent": "selectionner_pierre" }
    ]
  }
}
```

Rendu attendu : question visible, champs fournis, suggestions en boutons.

### 2.6 status_rail

Quand : état, santé, diagnostic, quotas.

```json
{
  "render_type": "status_rail",
  "payload": {
    "services": [
      { "name": "Voix", "status": "active", "detail": "OpenAI Realtime" },
      { "name": "Documents", "status": "active", "detail": "3 documents" },
      { "name": "SMS", "status": "active", "detail": "12 restants ce mois" },
      { "name": "Agenda", "status": "syncing", "detail": "Dernière synchro : 08:32" }
    ],
    "summary": "Tous les services sont opérationnels."
  }
}
```

Rendu attendu : rail de services, pastilles de statut, détails discrets.

## 3. Contrat WebSocket cible

### Message client vers serveur

```json
{
  "type": "transcript",
  "text": "Montre-moi mes documents",
  "session_id": "abc123",
  "timestamp": "2026-06-02T13:40:00Z"
}
```

### Message serveur vers client

```json
{
  "type": "render",
  "render_type": "data_board",
  "payload": {},
  "iris_spoken_response": "Voici vos 3 documents. La facture EDF est à payer avant le 15 juin.",
  "metadata": {
    "intent": "show_documents",
    "confidence": 0.95,
    "processing_time_ms": 1200
  }
}
```

### Message de validation

```json
{
  "type": "validation_response",
  "action_id": "action_456",
  "decision": "confirmed",
  "session_id": "abc123"
}
```

## 4. Garde-fous

| render_type | Actions autorisées | Validation requise |
|---|---|---|
| data_board | Trier, filtrer, ouvrir | Non |
| document_draft | Modifier, sauvegarder, télécharger | Non |
| document_draft | Envoyer | Oui — double confirmation |
| action_board | Toute action | Oui — obligatoire |
| context_panel | Approfondir, comparer | Non |
| missing_info | Sélectionner suggestion | Non |
| status_rail | Aucune action | Non |

Règle :

Si `requires_confirmation: true`, le frontend affiche obligatoirement un bouton de confirmation et attend une réponse de validation avant toute action réelle.

## 5. Interdits payload

### Texte brut interdit

```json
{
  "render_type": "text",
  "text": "Je ne peux pas afficher..."
}
```

### Action sans confirmation interdite

```json
{
  "render_type": "action_board",
  "payload": {
    "requires_confirmation": false
  }
}
```

### Données sensibles non filtrées interdites

```json
{
  "render_type": "data_board",
  "payload": {
    "rows": [["mot_de_passe", "12345"]]
  }
}
```

## 6. Synthèse pour Claude

Quand Claude codera :

1. Le backend doit transformer l'intention LLM en payload JSON structuré.
2. Les 6 `render_type` sont obligatoires.
3. Pas de fallback texte quand un affichage est demandé.
4. Le WebSocket ou le bridge Iris doit accepter un transcript et renvoyer un `render`.
5. Les actions sensibles doivent avoir `requires_confirmation: true`.
6. Le frontend doit gérer les 6 `render_type`.
7. Le design suit Kimi + DeepSeek.
