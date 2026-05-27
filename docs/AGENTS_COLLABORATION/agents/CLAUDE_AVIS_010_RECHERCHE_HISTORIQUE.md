# Claude — Avis Objectif 010 : Recherche historique et titres

**Date** : 2026-05-27  
**Statut sidebar UI** : validée — ne pas toucher  
**Mission** : titres intelligents + retrouver les anciennes conversations par sujet

---

## Audit du stockage réel

### Où sont les conversations ?

**Deux niveaux coexistent :**

**1. Redis (serveur) — source de vérité**
- Clé liste : `t:{tid}:conversations` (Redis SET)
- Métadonnées : `t:{tid}:conv:{id}:meta` (Redis HASH) → contient `summary` (= le titre)
- Messages : `t:{tid}:conv:{id}:messages` (Redis LIST de JSON)
- TTL : **30 jours** — les anciennes conversations disparaissent du serveur après 30 jours d'inactivité

**2. localStorage (navigateur/APK) — cache client**
- Métadonnées : clé `luna_conversations_meta` (tableau JSON avec `id`, `title`, `preview`, `last_activity`)
- Messages : clé `luna_conv_msgs_{id}` (tableau JSON)
- Aucun TTL — persiste jusqu'à vider le cache

Au démarrage, `loadConversationList()` charge depuis Redis via `GET /api/conversations`, qui retourne uniquement `id + title (=summary) + last_activity + message_count`. **Les messages ne descendent pas.**

---

## Ce que cherche la barre de recherche

`renderConvList(filter)` dans `static/index.html` ligne 6352 :

```
1. Titre (c.title)
2. Preview / dernier message (c.preview, 60 chars max)
3. Messages locaux complets (localStorage luna_conv_msgs_{id})
```

**Constat :** la recherche est déjà full-text sur les messages locaux. Si Ludovic tape "chocolat" et que les messages sont dans son localStorage, ça doit matcher.

### Pourquoi "chocolat" n'est pas trouvé

Plusieurs causes possibles :

**A. Les messages ne sont plus dans localStorage**
- Cache vidé, APK réinstallée, changement de téléphone, changement de compte → localStorage perdu
- C'est la cause la plus probable pour les "anciennes" conversations

**B. Les messages ne sont pas dans Redis non plus**
- TTL 30 jours dépassé : les conversations de il y a 2 mois ont expiré côté serveur
- `GET /api/conversations` ne retourne que le titre et le count, pas les messages

**C. Le titre ancien est mauvais**
- Anciennes conversations générées avant le fix du prompt ont des titres phrases ou "Nouvelle conversation"
- La recherche sur le titre rate donc même si le contenu existait

**D. `preview` trop court**
- Seulement 60 caractères du dernier message — "chocolat" peut ne pas être dans les 60 derniers chars

---

## Ce qu'il faudrait pour retrouver une conversation

### Option A — Repartir proprement sur les nouvelles (minimal, sans risque)

Ne rien migrer. Les nouvelles conversations auront :
- titre court et pertinent (déjà fait)
- messages stockés dans localStorage dès le premier échange
- recherche full-text qui fonctionnera sur ce localStorage

**Avantage** : zéro risque de casser quoi que ce soit.  
**Limite** : les anciennes conversations perdues restent perdues.

### Option B — Régénérer les titres des conversations existantes dans Redis

Parcourir toutes les conversations Redis dont `summary` est vide ou trop long (> 5 mots), récupérer leurs 2 premiers messages, régénérer un titre court via GPT-4o-mini.

**Implémentation** : endpoint admin `POST /api/admin/retitle-conversations` qui tourne en tâche de fond.  
**Risque** : faible si on ne modifie que `summary` dans les meta Redis.  
**Limite** : ne résout pas les conversations dont les messages ont expiré de Redis.

### Option C — Ajouter une recherche plein texte serveur (recommandée à terme)

Nouveau endpoint : `GET /api/conversations/search?q=chocolat`

Côté serveur, pour chaque conversation active dans Redis, on charge les messages Redis et on cherche le mot-clé. On retourne les IDs et les extraits correspondants.

**Avantage** : retrouve les conversations même si le titre est mauvais, même si le localStorage est vidé, tant que les messages sont dans Redis (≤ 30 jours).  
**Limite** : ne retrouve pas les conversations > 30 jours.  
**Risque** : requête potentiellement coûteuse si beaucoup de conversations — à limiter (max 50 conversations, timeout 2s).

---

## Ma recommandation

### Phase 1 (sans déploiement immédiat) : Option A

Les nouvelles conversations fonctionnent. On laisse les anciennes telles quelles.  
C'est ce que Ludovic a devant lui maintenant, et ça marche pour le futur.

### Phase 2 (si Ludovic valide) : Option B + C combinées

1. `POST /api/admin/retitle-conversations` — régénère les titres manquants des conversations Redis actives (pas les expirées)
2. `GET /api/conversations/search?q=...` — recherche serveur full-text sur les messages Redis récents
3. Côté frontend : si la recherche locale ne trouve rien, déclencher la recherche serveur (fallback)

### Ce qui ne changera pas

- Aucune modification de la sidebar UI
- Aucune modification du CSS ou du layout
- Pas de nouveau champ visible par défaut
- Pas de déploiement sans décision Ludovic

---

## Estimation de complexité

| Action | Fichiers touchés | Risque | Durée |
|---|---|---|---|
| Option A | rien | nul | 0 |
| Retitrage automatique (B) | `luna_web.py` (+1 route admin) | faible | 1h |
| Recherche serveur (C) | `luna_web.py` (+1 route) + `index.html` (fallback JS) | moyen | 2-3h |

---

## Question pour Ludovic

**Qu'est-ce qui compte le plus pour toi ?**

1. Retrouver les conversations récentes (< 30 jours) par mots-clés → Option C suffit
2. Retrouver avec un bon titre dans la sidebar → Option B en plus
3. Repartir proprement, ne pas s'embêter avec l'ancien → Option A

Une fois la décision prise, je code uniquement ce qui est validé.
