# Claude — Méthode Canaliser Iris — Objectif 025

Date : 2026-06-04
Agent : Claude (lead technique)
Type : analyse / méthode — AUCUN CODE
Référence : `docs/AGENTS_COLLABORATION/OBJECTIF_025_CANALISER_IRIS.md`

---

## 1. Diagnostic honnête

### Le vrai problème

`gpt-realtime-mini` avec `tool_choice=required` oblige Iris à appeler un outil — mais ça ne résout pas le fond. Elle peut appeler l'outil `chat` (catch-all) et continuer à bavarder. Le problème n'est pas qu'elle ne veut pas appeler d'outil. C'est qu'elle ne sait pas **quel outil dans quel contexte**.

Le système prompt lui dit "tu es une secrétaire" mais il ne lui dit pas **ce que l'utilisateur est en train de faire**. Sans contexte de mission actif, le modèle revient à son comportement par défaut : répondre textuellement à ce qu'on lui demande.

### Cause racine

```
Iris reçoit le même system prompt pour toutes les situations.
→ Elle n'a pas de "mode opérationnel" injecté.
→ Elle improvise selon le modèle de base (IA généraliste).
→ tool_choice=required la force à appeler quelque chose.
→ Elle appelle chat ou iris_render avec un texte vague.
→ Le rendu est générique ou nul.
```

### Ce qui fonctionne déjà et qu'on ne doit pas casser

- `tool_choice=required` dans `web_voice_bridge.py` — correct, à conserver
- `handle_iris_tool` avec blocage des actions sensibles — solide
- `_iris_auto_render()` bridge tool → rendu — doit continuer à fonctionner
- `action_board` + `validation_required` — garde-fou opérationnel

---

## 2. Méthode recommandée — Hybride E concrétisé

Je recommande la **Méthode E** (hybride), mais traduite en architecture précise et sans sur-ingénierie.

### Principe en une phrase

> Iris reçoit un **contexte de mission actif** injecté dans son system prompt au moment de la connexion WebSocket, et la liste d'outils disponibles est filtrée selon ce contexte.

### Les trois couches

```
Couche 1 — Mode sélectionné par l'utilisateur (UX Kimi)
     ↓ transmis comme param à la connexion WS
Couche 2 — System prompt enrichi selon le mode (backend Claude)
     ↓ Iris sait exactement ce qu'elle doit faire et ne pas faire
Couche 3 — Outils filtrés selon le mode (realtime_bridge.py)
     ↓ tool_choice=required → Iris NE PEUT PAS appeler un outil hors scope
```

---

## 3. Modes à définir (V1)

| Mode | Déclencheur | Outils disponibles | Rendu attendu |
|---|---|---|---|
| `secretaire` | défaut | tous | context_panel, action_board |
| `analyse` | bouton Analyser ou "analyse ce document" | search_documents, get_documents_summary, analyze_document | document_insight, data_board |
| `redaction` | bouton Rédiger | generate_document | document_draft |
| `recherche` | bouton Rechercher ou "cherche" | search_web, get_news, get_page_info | research_board |
| `reunion` | bouton Réunion | get_reminders, create_note, get_contacts | meeting_board, timeline |
| `communication` | bouton Envoyer | send_sms, send_email, call_contact, get_contacts | action_board + validation |
| `budget` | bouton Budget | get_budget_analysis, check_affordability | budget_board |
| `carte` | bouton Carte ou "où est" | search_places | map_board |

En mode `secretaire` (défaut), tous les outils sont disponibles mais le prompt est moins spécialisé.

---

## 4. Où brancher dans le code (sans coder)

### 4.1 `simli.html` — Kimi définit l'UI

Le mode est sélectionné par l'utilisateur via l'interface (boutons, menu, ou geste). La page transmet le mode dans la connexion WebSocket :

```
wss://.../ws/iris/voice?token=...&mode=analyse
```

Ou en premier message WS après connexion :
```json
{"type": "set_mode", "mode": "analyse"}
```

### 4.2 `luna_web.py` — `ws_iris_voice` (lignes ~9234)

Le mode est extrait du query param ou du premier message WS.
Un dictionnaire `_MODE_SYSTEM_PROMPTS` contient le segment de context supplémentaire par mode.
Ce segment est **ajouté** au system prompt existant — il ne le remplace pas.

Exemple pour mode `analyse` :
```
=== MODE ACTIF : ANALYSE DE DOCUMENT ===
Tu es en mode analyse. Ta seule mission est d'analyser les documents
que l'utilisateur t'a fournis ou demandés.
Tu DOIS appeler search_documents ou get_documents_summary immédiatement.
Tu DOIS afficher le résultat dans un document_insight.
Tu ne discutes pas. Tu analyses et tu projettes.
```

### 4.3 `realtime_bridge.py` — `VOICE_TOOLS_BY_MODE`

Un nouveau dictionnaire filtre la liste des outils selon le mode :

```
VOICE_TOOLS_BY_MODE = {
  "analyse":       ["search_documents", "get_documents_summary", "iris_render"],
  "redaction":     ["generate_document", "iris_render"],
  "recherche":     ["search_web", "get_news", "get_page_info", "iris_render"],
  "reunion":       ["get_reminders", "create_note", "get_contacts", "iris_render"],
  "communication": ["get_contacts", "send_sms", "send_email", "call_contact", "iris_render"],
  "budget":        ["get_budget_analysis", "check_affordability", "iris_render"],
  "carte":         ["search_places", "iris_render"],
  "secretaire":    VOICE_TOOLS  # liste complète
}
```

Avec `tool_choice=required`, en mode `analyse`, Iris **ne peut appeler que** les outils d'analyse. Elle ne peut plus partir en discussion libre.

### 4.4 Le garde-fou "promettre sans faire"

Problème identifié : Iris dit "je vais chercher" sans appeler l'outil.

Fix sans code complexe : dans le segment de prompt mode, ajouter explicitement :

```
INTERDIT : dire "je vais chercher", "je peux analyser", "je vais le faire".
OBLIGATOIRE : appeler immédiatement l'outil correspondant AVANT de parler.
```

Et avec `tool_choice=required`, si Iris parle sans avoir appelé d'outil, le bridge ne reçoit pas de tool call — le fallback `_icsFallbackTimer` affichera un `context_panel` avec son texte. Ce n'est pas parfait mais c'est visible et traçable.

---

## 5. Réponses aux 10 questions

**1. Fonctionnalités V1 absolument maîtrisées**

Analyse document, Recherche web, Rédaction (brouillon), Prise de notes réunion, Budget. Ce sont les 5 cas d'usage productifs sans risque d'action réelle.

**2. Fonctionnalités en brouillon/validation**

Communication (SMS/email/appel), Export PDF, Carte (consentement géoloc requis), Upload fichier externe. Toutes nécessitent soit un garde-fou technique soit un backend non encore prouvé.

**3. Méthode qui canalise le mieux sans casser l'expérience**

**Méthode E** : mode sélectionné explicitement + prompt enrichi + outils filtrés. Le mode par défaut `secretaire` préserve la conversation naturelle. Les modes spécialisés forcent le comportement productif.

**4. Boutons ou modes visibles**

Kimi doit décider du design. Proposition fonctionnelle : 6-7 icônes compactes dans la barre basse ou un sélecteur de mode dans le header du Command Screen.

**5. Mots déclencheurs qui forcent un outil**

Liste minimale à valider avec DeepSeek :
- "analyse", "résume", "extrais" → mode analyse
- "cherche", "actualités", "qu'en dit" → mode recherche
- "rédige", "écris", "courrier" → mode rédaction
- "réunion", "compte-rendu", "décisions" → mode réunion
- "envoie", "SMS", "appelle", "email" → mode communication (action_board)
- "budget", "dépenses", "solde" → mode budget
- "où est", "adresse", "trajet" → mode carte

Ces mots peuvent déclencher un **changement de mode automatique** si Iris est en mode `secretaire`. C'est l'intent router de la Méthode C, greffé sur le sélecteur de mode.

**6. Placement des garde-fous**

| Garde-fou | Emplacement |
|---|---|
| Actions sensibles (SMS/appel/email) | `handle_iris_tool` — déjà en place |
| Horaires 22h-7h | `_check_time_restriction()` — déjà en place |
| Quota mensuel | `_quota_guard` — déjà en place |
| Géolocalisation | `_icsGrantGeoloc()` localStorage — en place depuis 021 |
| Outil hors scope | `VOICE_TOOLS_BY_MODE` filtrage — à implémenter |
| Promesse sans action | Segment prompt mode + fallback visible — à implémenter |
| Données invité | `_participant_role` check dans `handle_iris_tool` — à renforcer |

**7. Comment prouver qu'une fonctionnalité atteint sa target**

Méthode TARGET_CELL existante (Objectif 021) : phrase test → render_type observé → rendu visible → outil appelé prouvé dans les logs. Chaque mode a une phrase test obligatoire.

**8. Éviter "je vais faire" sans faire**

Deux mesures cumulées :
1. Dans le prompt mode : INTERDIT de promettre sans appeler l'outil
2. Dans les logs : tracer les `tool_call` manquants quand le transcript contient "je vais"

**9. Gérer documents et exports proprement**

Flux propre : `upload → scan (POST /api/documents/v2/scan) → document_insight → export (GET /api/documents/download/{filename})`. Ce flux existe côté backend. Il manque le raccordement vocal dans le mode `analyse`.

**10. Endpoints manquants ou risqués**

| Endpoint | Statut | Note |
|---|---|---|
| `POST /api/capability/search` | Absent | search_web passe par Serper directement — OK |
| `GET /api/map/geocode` | Absent | map_board fait Google Maps redirect — acceptable V1 |
| `POST /api/call/make` | Non prouvé | call_contact existe dans luna_web.py mais Twilio Voice non testé en prod |
| `POST /api/email/send` | Non prouvé | send_email existe mais SMTP non configuré sur Cloud Run |
| Upload fichier vocal | Absent | L'utilisateur ne peut pas encore envoyer un PDF pendant la session vocale |

---

## 6. Complexité et risques

| Élément | Complexité | Risque |
|---|---|---|
| Segment prompt par mode | Faible | Faible — texte seulement |
| VOICE_TOOLS_BY_MODE | Faible | Moyen — si mode mal détecté, outils manquants |
| Mode selector UI (Kimi) | Moyenne | Faible — côté client uniquement |
| Intent router auto (Méthode C) | Moyenne | Moyen — faux positifs si triggers trop larges |
| Mode switching en cours de session | Élevée | Élevé — risque de rupture de contexte |
| Export PDF | Élevée | Moyen — dépend de wkhtmltopdf ou pdfkit |

**Recommandation** : implémenter les 3 premiers uniquement en V1. Le reste en V2 après validation Codex.

---

## 7. Ce que j'attends de Kimi et DeepSeek

**De Kimi** :
- Quels boutons/modes sont visibles, dans quel ordre, avec quelle icône
- Comment l'utilisateur change de mode en cours de session sans perdre le contexte
- Design du sélecteur : barre basse, header ICS, ou drawer latéral

**De DeepSeek** :
- Liste exhaustive des mots déclencheurs par mode (regex prêtes)
- Audit des endpoints risqués avec niveau de risque
- Proposition de tests d'acceptation automatisables

---

## 8. Livrable attendu après arbitrage Codex

Un fichier TARGET_CELL par mode, avec :
- phrase test
- tool attendu
- render_type attendu
- garde-fou listé
- statut initial

Aucun code avant que Codex valide la méthode et les modes V1.
