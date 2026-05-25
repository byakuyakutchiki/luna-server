# Claude — Avis Objectif 010

**Date** : 2026-05-25  
**Objectif** : Historique intelligent des conversations + mémoire Luna  
**Statut** : audit complet — en attente avis DeepSeek/Kimi/Cursor avant implémentation

---

## Résumé

L'historique de conversations et la mémoire Luna sont déjà largement implémentés.
Le vrai travail de code de l'objectif 010 se réduit au bug CSS du bouton Déconnexion.

---

## Audit : ce qui existe déjà

### Historique conversations — 100 % implémenté

| Fonctionnalité | Statut | Emplacement |
|---|---|---|
| Menu trois traits (sidebarToggle) | ✅ | `index.html` ligne 1555 |
| Bouton nouvelle conversation | ✅ | `index.html` ligne 1569 (`newChatBtn`) |
| Liste des conversations (`conv-item`) | ✅ | `index.html` lignes 6303–6430 |
| Création de conversation | ✅ | `POST /api/conversations` (`luna_web.py` ligne 9451) |
| Titre automatique IA | ✅ | `luna_web.py` lignes 6299–6328 (après 3ème msg) |
| Renommage | ✅ | `PATCH /api/conversations/{id}` |
| Suppression | ✅ | `DELETE /api/conversations/{id}` |
| Vidage des messages | ✅ | `DELETE /api/conversations/{id}/messages` |
| Stockage hybride localStorage + Redis | ✅ | `luna_web.py` MemoryManager + `index.html` |
| Reprise conversation | ✅ | `GET /api/conversations` → rechargement localStorage |
| Fallback localStorage si serveur KO | ✅ | `index.html` ligne 6453 |

**Conclusion : zéro développement nécessaire sur l'historique.** Tout fonctionne.

### Mémoire Luna — déjà riche

`LUNA_SYSTEM_PROMPT` (`luna_web.py` ligne 3971) contient :

- Identité complète de Luna
- Profil du souscripteur injecté à chaque conversation
- Architecture YAWatch (confidentielle — jamais révélée à l'utilisateur)
- Toutes les capacités (22 fonctions)
- Règles de comportement conciergerie, vie privée, sécurité
- Date du jour injectée dynamiquement

Ce prompt est injecté à chaque appel `/api/chat`.

**Ce que je ne recommande PAS d'injecter** : l'état des objectifs techniques
(010 ouvert, 008 validé, etc.). Ces informations sont du jargon interne sans valeur
pour l'utilisateur final. La mémoire utile pour l'utilisateur est déjà en place.

---

## Seul vrai travail : bug bouton Déconnexion coupé

### Symptôme

Sur mobile, le header est `display:flex;justify-content:space-between` avec :
- À gauche : `sidebarToggle` + avatar + titre "Luna"
- À droite : `newChatBtn` + `wakewordBtn` + `updateAppBtn` (conditionnel) + logo YAWatch + bouton `Déconnexion`

Sur petit écran (< 380px environ), le logo YAWatch + bouton se serrent et le `n` de
"Déconnexion" peut être coupé par le bord droit / safe-area du téléphone.

### Cause

Le bouton n'a pas `white-space:nowrap` et le header n'a pas de `padding-right` pour
respecter la safe-area iOS/Android (env variable CSS `safe-area-inset-right`).

### Correction minimale proposée

1. Ajouter `white-space: nowrap` sur `.logout-btn`
2. Ajouter `padding-right: env(safe-area-inset-right, 8px)` sur le container droit du header

Risque : quasi-nul. Aucune dépendance fonctionnelle.

**J'attends le retour de Cursor (UI mobile) avant d'implémenter** pour ne pas
faire doublon ou rater un cas que Cursor aurait identifié.

---

## Questions résolues

| Question Codex | Réponse |
|---|---|
| Où sont stockés les messages ? | Redis (MemoryManager) + localStorage client (hybride) |
| localStorage vs serveur vs Redis ? | Hybride déjà en place — ne pas changer |
| Comment générer les titres automatiquement ? | Déjà fait via GPT après 3ème message |
| Quelle mémoire globale/conversation/projet ? | Prompt système global, Redis par session, localStorage backup |
| Comment Luna sait l'état des objectifs ? | Elle ne sait pas — intentionnel. Objectifs = jargon interne. |
| Comment éviter les données sensibles en mémoire ? | Le prompt interdit déjà de révéler architecture/clés/fournisseurs |
| Comment corriger le bouton mobile ? | CSS `white-space:nowrap` + safe-area-inset — voir ci-dessus |

---

## Ce que j'attends des autres agents

| Agent | Livrable | Impact sur mon implémentation |
|---|---|---|
| **DeepSeek** | `DEEPSEEK_AVIS_010.md` | Confirmer que le menu trois-traits fonctionne dans le WebView APK |
| **Kimi** | `KIMI_AVIS_010.md` | Textes d'interface conversations (boutons, titres, états vides) |
| **Cursor** | `CURSOR_AVIS_010.md` | Diagnostic précis du bouton Déconnexion coupé + proposition CSS |

---

## Ma recommandation

**L'objectif 010 ne nécessite pas de nouveau développement backend.**

Travail réel :
1. **Bug CSS bouton Déconnexion** — correction mineure, 2 lignes CSS (après avis Cursor)
2. **Vérification WebView APK** — confirmer que le menu conversations s'affiche (après avis DeepSeek)
3. **Textes interface** — peut-être améliorer les labels (après avis Kimi)

**Je n'implémente rien avant** :
- Avis Cursor sur le bug mobile
- Validation Ludovic sur ce que je vais modifier exactement
