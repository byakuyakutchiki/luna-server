# Plan — Refonte onglet Documents (issue #22)

**Date :** 2026-06-26 · **Lead :** Claude · **Statut :** plan en attente d'arbitrage Ludo (1 décision bloquante)

---

## 1. Ce qui existe déjà (état réel, vérifié dans le code)

Le module est **bien plus avancé** qu'un simple stockage :

- **Scan + analyse IA** (`core/vault/classifier.py`, GPT-4o vision) : détecte 15 types de docs, extrait
  émetteur, dates, montants, références, échéances, champs profil. Calcule urgence/expiration.
- **Stockage Redis** (`core/vault/redis_ops.py`) : métadonnées + texte OCR, TTL 1 an, par tenant.
- **Moteur d'actions** (`core/documents/actions_engine.py`) : payer, contester, relancer, renouveler, expliquer…
- **Chat Iris contextuel** (`POST /api/documents/v2/chat`).
- **Catégories par type** + 5 piliers (Identité/Santé/Banque/Impôts/Assurance) avec score de complétude.
- **Bridge profil** : les pièces d'identité pré-remplissent le profil.
- **RGPD** : consentement, suppression en cascade, **originaux non stockés**.
- **Frontend** `static/documents.html` (1585 l.) : bibliothèque, recherche en place (#dsearch), workspace
  viewer+chat (#docws), modales détail/scan/création.

## 2. Ce que demande #22 vs ce qui existe (gap)

| Demande #22 | État | Implémentable sans nouvelle décision ? |
|---|---|---|
| **Afficher le document original** (zoom, rotation, pages, plein écran) | ❌ original **non stocké** (RGPD) | 🔴 **NON — décision bloquante (§4)** |
| Analyse IA (type, émetteur, dates, montants, échéances…) | ✅ existe | — |
| **Arborescence auto** (Identité, Banque, Logement…) avec sous-dossiers | ⚠️ catégories à plat par type, pas d'arbre | 🟢 OUI (métadonnées seules) |
| **Classement auto par contenu** (facture EDF → Logement/Électricité) | ⚠️ classé par type, pas en arbre logique | 🟢 OUI |
| **Renommage intelligent** (« Facture EDF – Juin 2026 ») | ⚠️ `titre` auto existe, pas de format normalisé | 🟢 OUI |
| **Édition utilisateur** : déplacer, renommer, créer/renommer/fusionner/supprimer dossier | ❌ absent | 🟢 OUI |
| **Navigation arborescente** (compteurs, dernière modif, icône par dossier) | ❌ absent | 🟢 OUI |
| **Recherche intelligente** (langage naturel) | ✅ basique (PR #23) | 🟢 amélioration possible |
| « L'IA apprend des choix de l'utilisateur » | ❌ absent | 🟡 OUI (simple : règles émetteur→dossier mémorisées) |

**Conclusion :** ~70 % de #22 (toute la partie **organisation/arborescence/édition/recherche**) est
implémentable **dès maintenant** sur les métadonnées existantes, **sans toucher au RGPD**.
Les 30 % restants (**afficher l'original**) exigent une décision d'architecture/légale.

## 3. Plan d'implémentation — partie NON bloquante (additive)

> 100 % additif, ne retire rien (cf. CLAUDE.md). Objectif validé un par un.

**Lot A — Modèle d'arborescence (backend)**
- Mapping `doc_type → (Dossier, Sous-dossier)` (ex. `facture_energie → Logement/Énergie`,
  `releve_bancaire → Banque/Relevés`, `cni → Identité`). Table de correspondance par défaut.
- Stockage Redis additif : champ `folder_path` par doc + set `luna:{tenant}:vault:folders` (dossiers custom).
- Routes : `GET /api/documents/v2/tree` (arbre + compteurs + dernière modif), `POST .../move`,
  `POST .../folder` (créer/renommer/fusionner/supprimer), `POST .../rename` (doc).
- Règles apprises : `luna:{tenant}:vault:rules` (émetteur → dossier choisi par l'utilisateur).

**Lot B — Renommage normalisé**
- Générer un nom lisible standard à partir des champs (`{label} – {emetteur} – {mois année}`),
  éditable. Ne pas écraser un titre déjà personnalisé.

**Lot C — Navigation arborescente (frontend)**
- Vue arbre repliable dans documents.html (dossiers avec icône, compteur, dernière modif).
- Drag-and-drop ou menu « déplacer vers… » ; CRUD dossiers ; fil d'Ariane.
- 100 % additif au-dessus de la bibliothèque actuelle (l'existant reste accessible).

**Lot D — Recherche intelligente +**
- Étendre la recherche existante au contenu OCR + langage naturel (déjà partiellement là).

Chaque lot : testé Playwright, zéro régression, validé avant le suivant.

## 4. 🔴 DÉCISION BLOQUANTE — afficher le document original

L'archi actuelle **ne stocke pas** les originaux scannés (RGPD, `routes.py:95`). Pour répondre à
« le document original toujours affiché » il faut **stocker l'original**. Options :

| Option | Description | RGPD / risque | Coût |
|---|---|---|---|
| **A. Statu quo** | On garde l'archi : viewer = fiche métadonnées + texte OCR (pas d'image). On documente que « l'original n'est pas conservé pour ta sécurité ». | ✅ minimisation maximale | nul |
| **B. Stockage chiffré opt-in** | Stocker l'original (image/PDF) **chiffré au repos** dans GCS, **consentement explicite**, TTL + droit à l'effacement en cascade (déjà en place). Viewer complet (zoom/rotation/pages/plein écran). | ⚠️ acceptable si chiffrement + consentement + effacement | moyen (GCS + crypto + UI consentement) |
| **C. Hybride par sensibilité** | Stocker l'original seulement pour les types **non sensibles** ; pour RIB/CNI/avis d'imposition → fiche seule. | 🟡 compromis | moyen |
| **D. Affichage transitoire** | Ne jamais persister : afficher l'original **uniquement** au moment du scan/import (jamais re-téléchargeable). | ✅ pas de stockage | faible mais ne répond pas à « rouvrir un doc existant » |

> Mon avis (lead technique) : **B avec consentement explicite + chiffrement** répond vraiment à la vision
> #22, mais c'est une décision **légale + sécurité + coût** qui t'appartient (fondateur). Tant qu'elle n'est
> pas prise, je peux livrer **tous les lots A→D du §3** (organisation/arborescence/édition/recherche) qui
> apportent déjà l'essentiel du « véritable gestionnaire documentaire ».

## 5. Proposition de séquencement

1. **Maintenant (sans décision)** : implémenter Lot A → B → C → D (§3).
2. **En parallèle** : Ludo tranche la décision §4 (stockage des originaux).
3. **Ensuite** : si option B/C → ajouter le stockage chiffré + le viewer original complet.

---

*En attente du feu vert sur le §3 (je peux démarrer le Lot A tout de suite) et de l'arbitrage §4.*
