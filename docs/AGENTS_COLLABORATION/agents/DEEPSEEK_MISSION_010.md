# DeepSeek — Mission Objectif 010

**Date** : 2026-05-26  
**De** : Claude (lead)  
**Pour** : DeepSeek  
**Urgence** : haute

---

## Contexte

Le menu historique existe dans l'APK (panneau gauche, bouton trois traits).
Les conversations s'affichent mais restent nommées "Nouvelle conversation".

Claude a tenté deux corrections serveur. Elles n'ont pas résolu le problème
sur l'APK réelle. Le problème est peut-être côté client (JS/APK) plutôt que serveur.

## Ta mission

Auditer `static/index.html` et répondre à ces questions précises :

### Question 1 — Chargement des conversations

Dans `loadConversations()` (autour ligne 6438), l'appel `GET /api/conversations`
retourne les conversations avec leur `summary` (le titre).

**Vérifie** : est-ce que ce résultat est appliqué à `conversationsMeta` AVANT
que `renderConvList()` soit appelé ? Est-ce que l'ordre des opérations garantit
que le titre est affiché au bon moment ?

### Question 2 — `auto_title` reçu mais non appliqué

Dans `_handleStreamResponse`, l'événement SSE `done` contient `auto_title`.
Code actuel (autour ligne 4453) :

```javascript
var _doneConv = conversationsMeta.find(function(c) { return c.id === currentConvId; });
if (_doneConv) {
  if (data.auto_title) { _doneConv.title = data.auto_title; }
  _doneConv.preview = fullText.substring(0, 100);
  _doneConv.last_activity = new Date().toISOString();
  saveConvMeta(); renderConvList();
}
```

**Vérifie** : est-ce que `conversationsMeta` contient bien une entrée avec
`id === currentConvId` au moment où cet événement est traité ?

**Hypothèse** : si la conversation a été créée localement en localStorage
avant que `POST /api/conversations` réponde, l'ID local peut différer de l'ID
serveur → `find()` ne trouve rien → `auto_title` est ignoré.

### Question 3 — Conversation "default"

La conversation par défaut a `id = "default"`. Elle n'est jamais supprimée.
Les utilisateurs envoient des messages dessus sans créer de nouvelle conversation.

**Vérifie** : est-ce que `GET /api/conversations` retourne la conversation "default"
avec son `summary` ? Si non, elle n'aura jamais de titre dans la liste.

### Question 4 — `saveConvMeta()` et `localStorage`

`saveConvMeta()` stocke `conversationsMeta` dans localStorage.
Mais au démarrage, `loadConversations()` charge depuis le serveur ET remplace
`conversationsMeta`. Si le serveur ne retourne pas le bon titre, le titre
local est écrasé.

**Vérifie** : l'ordre exact entre `loadConversations()` (serveur) et le
localStorage au démarrage.

## Livrable attendu

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_010.md`

Contenu :
- Réponses aux 4 questions avec numéros de lignes précis
- Proposition de correction minimale (snippet JS, pas de refonte)
- Risque de régression identifié

## Interdit

- Ne pas refondre le système de conversations
- Ne pas modifier `luna_web.py`
- Ne pas toucher au CSS ou au layout
