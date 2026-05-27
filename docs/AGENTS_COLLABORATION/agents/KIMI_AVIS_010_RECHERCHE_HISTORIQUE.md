# Kimi — Avis : Recherche historique + Titres objectif 010

> Date : 2026-05-27
> Phase : recherche intelligente + titres courts
> Statut : avis UX + proposition d'implémentation minimale

---

## 1. Diagnostic UX du problème réel

### Le constat de Ludovic

> "J'ai parlé de chocolat dans d'anciennes conversations, mais la sidebar ne retrouve pas ces conversations."

Cela signifie que la recherche actuelle échoue sur trois cas fréquents :

| Cas | Pourquoi ça échoue aujourd'hui |
|---|---|
| Le titre est vague (« Conversation » ou « Nouvelle conversation ») | La recherche ne trouve pas « chocolat » dans le titre |
| Le titre est un ancien titre long / phrase | L'utilisateur ne pense pas à chercher « Résumé de notre discussion sur les desserts » |
| Le sujet est dans un message du milieu | Le `preview` ne contient que les 60 derniers caractères du **dernier** message |

### Ce que l'utilisateur attend en vrai

Quand Ludovic tape « chocolat » dans la recherche, il veut :
1. Voir les conversations dont le **titre** contient « chocolat »
2. Voir les conversations où un **message** contient « chocolat »
3. Ne pas avoir à se souvenir du titre exact
4. Que ce soit **instantané** (pas de spinner, pas d'attente serveur)

---

## 2. Règles UX des titres courts

### Principe

Un titre de conversation est un **label de répertoire**, pas une phrase.

| Bon | Mauvais |
|---|---|
| `Gâteau chocolat` | `Discussion sur la recette de gâteau au chocolat` |
| `Vols Paris Rome` | `Résumé de notre conversation sur les voyages` |
| `Urgence contact` | `Conversation du 26 mai 2026` |
| `Paramètres voix` | `Nouvelle conversation` |

### Garde-fou côté affichage

Même si le backend génère un titre trop long (dérive du modèle, ancienne conversation), le client doit **tronquer à l'affichage** :

- **Maximum affiché** : 4 mots ou 40 caractères
- **Coupe propre** : au dernier espace avant la limite, pas en plein milieu d'un mot
- **Indicateur de troncature** : `…` à la fin si coupé
- **Infobulle** (`title` HTML) : affiche le titre complet au survol

---

## 3. Logique de recherche côté humain

### Niveaux de recherche (par priorité)

```
Niveau 1 — Titre exact ou partiel
  Ex : "chocolat" → trouve "Gâteau chocolat"
  → Le plus rapide, le plus fiable

Niveau 2 — Contenu des messages (local)
  Ex : "chocolat" → trouve une conversation où Luna a dit "Tu veux du chocolat noir ?"
  → Nécessite de scanner les messages stockés localement

Niveau 3 — Mots-clés / sujets implicites (futur)
  Ex : "dessert" → trouve "Gâteau chocolat" même si le mot "dessert" n'apparaît nulle part
  → Nécessite une indexation sémantique, trop lourd pour maintenant
```

### Proposition pour cette phase

Implémenter **Niveau 1 + Niveau 2** côté client uniquement.

**Pourquoi client uniquement ?**
- Les messages sont déjà dans `localStorage` (fonction `saveHistory()`)
- Pas de latence réseau
- Pas de changement backend
- Pas de risque de fuite de données
- Fonctionne offline

**Limites acceptables :**
- Si l'utilisateur change d'appareil, la recherche ne trouvera que les conversations synchronisées depuis le serveur (via `/api/history`)
- Si le `localStorage` est vidé, l'index est perdu
- Ces limites sont acceptables pour une V1

---

## 4. Affichage des résultats sans alourdir la sidebar

### Comportement actuel

La sidebar affiche :
- Toutes les conversations groupées par date (Aujourd'hui, Hier, Cette semaine…)
- Une recherche qui filtre cette liste

### Comportement proposé

**Recherche vide** (comme aujourd'hui) :
```
Conversations        ✕
+ Nouvelle conversation
🔍 _______________

AUJOURD'HUI
  ▸ Gâteau chocolat
  ▸ Vols Paris Rome

HIER
  ▸ Urgence contact
```

**Recherche active** (`chocolat`) :
```
Conversations        ✕
+ Nouvelle conversation
🔍 chocolat________

RÉSULTATS (3)
  ▸ Gâteau chocolat
    — trouvé dans le titre
  ▸ Recette mardi
    — trouvé dans les messages
  ▸ Courses supermarché
    — trouvé dans les messages
```

### Règles d'affichage

1. **Grouper tous les résultats** sans distinction de date quand il y a une recherche active
2. **Indiquer la source** discrètement (titre vs messages) en dessous de chaque résultat, en gris clair
3. **Limiter à 20 résultats** pour éviter le scroll infini
4. **Ordre** : titres d'abord, puis messages, chacun trié par date décroissante
5. **Surlignage optionnel** : mettre en gras le mot recherché dans le titre (ex: `Gâteau **chocolat**`)

---

## 5. Gestion des anciennes conversations

### Option A — Ne rien toucher aux anciennes
- Les nouvelles conversations auront des titres courts
- Les anciennes gardent leurs titres longs/vagues
- La recherche plein texte les trouvera quand même via leur contenu
- ✅ **Recommandé pour cette phase** : pas de risque, pas de migration, pas de coût API

### Option B — Troncature purement côté client
- Afficher les anciens titres tronqués à 4 mots / 40 caractères
- Le titre réel reste stocké tel quel
- ✅ **Minimal, sans risque**

### Option C — Régénération serveur
- Envoyer chaque ancienne conversation à GPT-4o-mini pour un nouveau titre
- ⚠️ **Coût API** (1 appel par conversation ancienne)
- ⚠️ **Risque** : perte de l'ancien titre si le nouveau est pire
- ❌ **Pas recommandé maintenant** : trop lourd, trop risqué

### Option D — Indexation des mots-clés
- Lors de chaque nouveau message, extraire automatiquement 3-5 mots-clés
- Les stocker dans `conversationsMeta`
- La recherche scanne aussi ces mots-clés
- ✅ **Intéressant pour le futur** mais hors scope immédiat

---

## 6. Proposition d'implémentation minimale

### Étape 1 — Recherche plein texte client (10 lignes de JS)

Modifier `renderConvList(filter)` dans `static/index.html` :

```javascript
// Recherche dans les titres ET dans les messages stockés localement
if (filter) {
  var lower = filter.toLowerCase();
  filtered = filtered.filter(function(c) {
    // 1. Titre
    if ((c.title || "").toLowerCase().indexOf(lower) >= 0) return true;
    // 2. Preview (dernier message)
    if ((c.preview || "").toLowerCase().indexOf(lower) >= 0) return true;
    // 3. Messages complets stockés localement
    try {
      var msgs = JSON.parse(localStorage.getItem(convStorageKey(c.id)) || "[]");
      for (var i = 0; i < msgs.length; i++) {
        if ((msgs[i].text || "").toLowerCase().indexOf(lower) >= 0) return true;
      }
    } catch(e) {}
    return false;
  });
}
```

**Impact** : aucun changement backend, aucun changement UI visuel, juste la logique de filtre.

### Étape 2 — Troncature élégante des titres (5 lignes de JS)

Dans `renderConvList`, avant d'afficher le titre :

```javascript
var displayTitle = conv.title || (conv.preview ? conv.preview.substring(0, 40) + "…" : _convDateShort(conv.last_activity));
// Garde-fou : tronquer à 4 mots max pour l'affichage
var words = displayTitle.split(/\s+/);
if (words.length > 4) {
  displayTitle = words.slice(0, 4).join(" ") + "…";
}
```

**Impact** : les anciens titres longs seront affichés courts, mais le titre complet reste en `title` HTML (infobulle).

### Étape 3 — Distinguer les résultats (optionnel, ~15 lignes)

Ajouter une classe ou un petit label sous le titre quand la correspondance vient des messages et non du titre :

```javascript
var matchSource = "titre";
if ((c.title || "").toLowerCase().indexOf(lower) < 0) {
  matchSource = "messages";
}
// Afficher "— trouvé dans les messages" en dessous du titre
```

---

## 7. Ce qu'il ne faut PAS faire

| Interdit | Pourquoi |
|---|---|
| Refaire le design de la sidebar | Il est validé sur téléphone |
| Supprimer ou modifier les anciennes conversations | Risque de perte de données |
| Envoyer tout l'historique à l'API pour régénérer les titres | Coût inutile, risque de dégradation |
| Ajouter une base de données côté client (IndexedDB, etc.) | Trop lourd pour un besoin simple |
| Stocker des secrets ou données sensibles dans l'index | Violation des règles de sécurité |

---

## 8. Livrable attendu de ma part

Je peux implémenter les **Étapes 1 et 2** immédiatement dans `static/index.html` :
- Recherche plein texte dans les messages locaux
- Troncature élégante des titres à l'affichage

C'est **chirurgical** : ~15 lignes de JS, 0 changement backend, 0 changement CSS.

Validation requise de Ludovic avant déploiement.

---

*Avis écrit par Kimi — 2026-05-27*
