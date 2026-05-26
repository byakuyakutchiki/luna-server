# DeepSeek — Mission 010 + Bug Mobile

**Date** : 2026-05-26  
**De** : Claude (lead)  
**Pour** : DeepSeek  
**Urgence** : haute

---

## Partie 1 — Valider Objectif 010 : titres ChatGPT + loupe

### Ce qui a été changé (commit 0d030c5)

**`luna_web.py`** — prompt de génération de titre corrigé à 2 endroits :

Avant :
```
"Résume cette conversation en un titre français très court, 3 à 6 mots..."
```

Après :
```
"Donne un titre de répertoire en français, 2 à 4 mots maximum.
Comme ChatGPT : un label court et scannable, pas une phrase.
Sans guillemets, sans ponctuation finale, sans date, sans 'Nouvelle conversation'.
Exemples OK : 'Voix Luna', 'Bouton connexion', 'Services exploitant', 'Recherche hôtels'.
Exemples refusés : 'Résumé de notre conversation', 'Discussion autour de', 'Conversation du 26 mai'."
```

Garde-fou ajouté : si le modèle retourne plus de 5 mots → coupe à 4 mots.

**`static/index.html`** — loupe 🔍 ajoutée devant le champ de recherche de la sidebar.

### Ce que tu dois vérifier

**Question 1 — Chaîne complète auto_title**

Dans `luna_web.py`, localise les deux blocs `auto_title` (cherche `# Auto-title`).
Vérifie que le titre généré est bien :
1. Stocké dans `meta["summary"]` via `mgr.redis.set_conversation_meta()`
2. Retourné dans `done_data["auto_title"]` (SSE) ou `resp["auto_title"]` (HTTP)

**Question 2 — Réception côté JS**

Dans `static/index.html`, cherche la gestion de `auto_title` dans l'événement `done` du SSE.
Vérifie que :
1. `_doneConv.title = data.auto_title` est bien exécuté
2. `renderConvList()` est appelé après
3. Le titre est visible dans la liste gauche sans rechargement de page

**Question 3 — Loupe visible**

Cherche `.conv-search-wrap` dans le CSS.
Vérifie que le `::before` avec `content: "🔍"` ne risque pas d'être écrasé par une règle
CSS plus spécifique plus bas dans le fichier (notamment la surcharge mobile autour
de `.conv-search` avec `!important`).

### Livrable Partie 1

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_010_VALIDATION.md`

Contenu attendu :
- Chaîne auto_title : OK ou numéros de lignes du problème
- Réception JS : OK ou snippet de correction minimal
- Loupe CSS : OK ou règle conflictuelle identifiée
- Verdict global : **VALIDÉ** ou **BLOQUÉ + raison**

---

## Partie 2 — Bug mobile : bouton Déconnexion coupé

### Symptôme

Sur téléphone (375px), le bouton "Déconnexion" dans le header est coupé.
Le "n" final n'est pas visible. Le header droit est surchargé :
bouton MAJ + logo + wakeword + déconnexion → pas assez de place.

Les corrections CSS précédentes (white-space: nowrap, safe-area) n'ont pas suffi.

### Ce que tu dois analyser

1. Cherche le bouton Déconnexion dans `static/index.html` (cherche `Déconnexion` ou `deconnect` ou `logout`)
2. Cherche la même chose dans `static/fondateur.html`
3. Identifie le header qui contient ces boutons
4. Compte combien d'éléments sont dans ce header sur mobile
5. Mesure en DevTools (ou à l'œil dans le code) si la largeur totale dépasse 375px

### Solutions attendues (propose UNE, au choix)

**Option A — Texte court sur mobile**
```css
@media (max-width: 480px) {
  .logout-btn .btn-text { display: none; }
  .logout-btn::after { content: "Sortir"; }
}
```

**Option B — Icône seule sur mobile**
Remplacer "Déconnexion" par une icône SVG porte de sortie sur petit écran.

**Option C — Menu compte**
Regrouper les actions utilisateur (Profil, Déconnexion) dans un menu déroulant
accessible via un bouton ⚙️ ou avatar, pour libérer de la place dans le header.

### Contraintes

- Ne pas casser le header sur desktop/tablette
- Garder le style premium (pas de bouton moche ou trop simple)
- Ne pas toucher à `luna_web.py`
- Tester à 375px ET 768px

### Livrable Partie 2

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AVIS_BUG_DECONNEXION.md`

Contenu attendu :
- Fichier(s) concerné(s) + numéros de lignes
- Option choisie + snippet CSS/HTML minimal
- Raison du choix
- Risque de régression identifié

---

## Règles générales

- Ne pas refondre : corrections chirurgicales uniquement
- Ne pas modifier le backend (`luna_web.py`) pour le bug mobile
- Ne pas toucher aux fichiers de monitoring ou de PV
- Signaler si une correction risque de casser l'APK Android (WebView)
