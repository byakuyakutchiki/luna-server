# AUDIT UX COHÉRENCE + AUDIT MÉTHODOLOGIQUE — IRIS WORKSPACE

**Date** : 11 juin 2026  
**Réalisé par** : Claude (analyse code statique + raisonnement)  
**Destinataires** : Ludo (PO), ChatGPT (analyse complémentaire), Kimi (audit terrain)  
**Fichier source analysé** : `static/team_workspace.html`  
**Révision Cloud Run** : `luna-beta-00647-r4r`

---

## PARTIE 1 — AUDIT UX COHÉRENCE

### Principe

Pour chaque élément : l'état visuel affiché est-il cohérent avec l'état réel du système ?

---

### 1.1 Caméra — BUG CRITIQUE CONFIRMÉ

**Localisation** : CSS ligne ~876, JS `_updateSeatCam()` ligne ~3070

**Anomalie** :
```css
.tw-online-badge { background: #10b981; } /* toujours vert — jamais modifié */
```

La fonction `_updateSeatCam(uid, cam, mic)` change uniquement la visibilité vidéo/avatar :
```js
if(v) v.style.display = cam ? 'block' : 'none';
if(av) av.style.display = cam ? 'none' : 'flex';
```
Elle ne touche jamais `.tw-online-badge`. Résultat : caméra coupée + voyant vert allumé = incohérence UX.

**Correction nécessaire** :
```js
function _updateSeatCam(uid, cam, mic){
  var v = document.getElementById('video-'+uid);
  var av = document.getElementById('av-'+uid);
  var badge = document.querySelector('#seat-'+uid+' .tw-online-badge');
  if(v) v.style.display = cam ? 'block' : 'none';
  if(av) av.style.display = cam ? 'none' : 'flex';
  if(badge) badge.classList.toggle('off', !cam && !mic); // gris si tout coupé
}
```
```css
.tw-online-badge.off { background: rgba(255,255,255,0.15); box-shadow: none; }
```

---

### 1.2 Micro — Partiellement cohérent

- Bouton `btnMic` reçoit `.off` (opacity 0.4) ✅
- Icône micro sur la tile mise à jour par `_updateMicIcon()` ✅
- Badge vert sur la tile : **jamais modifié selon l'état micro** ❌ (même bug que caméra)

---

### 1.3 Partage d'écran — Cohérent pour le partageur, absent pour les autres

- Bouton `btnScreen` passe en `.on` ✅
- Overlay `#twScreenZone` s'affiche ✅
- **Aucun indicateur sur la tile de la personne qui partage** ❌
  - Les autres participants ne savent pas qui partage l'écran
  - Correction : envoyer un `screen_share` WS + ajouter classe `.sharing` sur le seat + badge icône écran

---

### 1.4 Iris / IQ / Luna — État affiché vs réalité

**Ce qui fonctionne** :
- `renderAIStates()` applique `seat-active-iris/iq/luna` selon l'étape → border neon s'allume ✅
- Les labels "En attente / Active / Terminée" changent correctement par étape ✅

**Anomalie profonde** :
Les entités IA affichent `active` mais ne produisent **rien**. L'état visuel (`active`) ne correspond à aucun traitement réel. C'est un voyant décoratif sur un moteur vide.

La seule sortie réelle : `_buildSynthesisHtml()` = une synthèse par template string, pas par IA.

---

### 1.5 Actions — Cohérent

`_AL_STATUS_ICON` et `_AL_STATUS_COLOR` correctement mappés :
- `TODO` → ☐ gris
- `IN_PROGRESS` → ◐ amber
- `DONE` → ☑ vert
- `CANCELLED` → ⊘ rouge barré

✅ état visuel = état réel

**Point de friction** : icônes en emoji alors que le reste du système (P3) est passé aux SVG. Incohérence stylistique.

---

### 1.6 Réserves — Cohérent

Tags CSS `OPEN / ACKNOWLEDGED / OVERRIDDEN / RESOLVED` avec couleurs correctes.  
Boutons disponibles reflètent exactement le statut actuel.  
✅ état visuel = état réel

---

### 1.7 Workflow — Cohérent

Stepper, contexte bar L3, `applyCanvasState()` synchronisés sur `TW.step`. ✅

---

### Tableau de synthèse UX Cohérence

| Élément | Cohérence | Bug | Priorité fix |
|---|---|---|---|
| Badge caméra (online-badge) | ❌ | Toujours vert même cam off | 🔴 immédiat |
| Bouton caméra | ✅ | — | — |
| Icône micro tile | ✅ | — | — |
| Badge micro (online-badge) | ❌ | Toujours vert même mic off | 🔴 immédiat |
| Bouton micro | ✅ | — | — |
| Bouton partage écran | ✅ | — | — |
| Indicateur partage sur tile | ❌ | Absent pour les autres | 🟠 court terme |
| États IA (active/waiting) | ✅ partiel | Affiché mais vide | 🔴 structurel |
| Actions status | ✅ | Emoji vs SVG | 🟡 cosmétique |
| Réserves status | ✅ | — | — |
| Workflow steps | ✅ | — | — |

---

## PARTIE 2 — AUDIT MÉTHODOLOGIQUE

### Principe

Si une équipe utilise Iris pendant 2 heures pour résoudre un problème complexe, est-ce que le système les aide réellement à prendre une meilleure décision ? Ou seulement à remplir des écrans ?

---

### 2.1 Valeur réelle de chaque étape

| Étape | Raison d'être | Perte si supprimée | Verdict |
|---|---|---|---|
| Mission | Cadrer la question principale | Dérive thématique garantie | ✅ essentielle |
| Question | Formuler le problème précis | Souvent redondant avec Mission | ⚠️ redondante — à fusionner ou distinguer clairement |
| Propositions | Forcer la formalisation écrite | Décision sans alternatives = intuition déguisée | ✅ core |
| Proposition active | Forcer un choix | Sans sélection, on reste dans le flou collectif | ✅ core |
| Sources | Ancrer dans des faits | Aucune vérification de qualité — risque de faux sentiment de rigueur | ⚠️ insuffisante |
| Décision | Dater et formaliser | Décision verbale = décision fantôme | ✅ essentielle |
| Actions | Transformer en exécution | Sans suite, la décision meurt | ✅ mais trop légère |
| Réserves | Formaliser les désaccords | C'est la feature la plus unique du système | ✅ différenciante |
| Dossier final | Mémoire et traçabilité | Perte de la preuve de due diligence | ✅ mais lacunaire |

---

### 2.2 Informations jamais capturées

Ces éléments sont indispensables à une vraie décision et **n'ont aucun endroit dans Iris** :

- **Contraintes** : budget, délai, ressources disponibles
- **Hypothèses** : sur quoi repose le raisonnement ?
- **Critères de réussite** : comment savoir dans 6 mois que c'était la bonne décision ?
- **Urgence et priorité des actions** : pas de deadline, pas de niveau de priorité
- **Deadlines par action** : le champ n'existe pas
- **Contexte extérieur** : marché, réglementation, concurrents
- **Alternatives rejetées et pourquoi** : la décision finale est tracée, pas le processus d'élimination
- **Responsable clair par action** : `assigned_to` est un champ texte libre non vérifié

---

### 2.3 Cassures du processus — où Iris peut donner un faux sentiment de sécurité

1. **Une seule proposition suffit** pour activer et décider. L'owner peut activer sa propre idée sans débat réel.
2. **Sources non vérifiées** : n'importe qui peut écrire "Étude McKinsey 2024" sans lien ni preuve.
3. **Une réserve rouge ne bloque pas** : l'owner peut cliquer "Continuer malgré" et progresser. Risque enregistré mais non bloquant.
4. **La décision est saisie manuellement** sans lien forcé avec les propositions. Elle peut contredire tout le travail précédent.
5. **Actions sans deadline** = intentions, pas des engagements. Aucun rappel, aucun suivi.
6. **13 étapes librement sautables** : rien n'empêche de passer de l'Entrée à la Décision en 2 clics.

---

### 2.4 Les IA — Décoratives ou utiles ?

| Entité | Ce qu'elle devrait faire | Ce qu'elle fait réellement |
|---|---|---|
| Iris | Analyser les propositions, identifier les angles faibles | Badge "active" selon l'étape. Rien de plus. |
| IQ | Comparer les sources, extraire des données factuelles | Badge "active" selon l'étape. Rien de plus. |
| Luna | Formuler une recommandation finale argumentée | Badge "active" selon l'étape. Rien de plus. |

**Seule vraie sortie IA** : `_buildSynthesisHtml()` — une phrase par template :
> "Après X propositions et Y sources, la proposition Z a été retenue."

C'est de la mise en forme, pas de l'intelligence.

**Conséquence** : l'état visuel "Iris active" correspond à zéro traitement réel. C'est une promesse que le système ne tient pas encore.

---

### 2.5 Le centre du workspace — ce que l'utilisateur comprend

**Comprend immédiatement** :
- L'étape en cours ✅
- La question de session ✅ (depuis P2)

**Ne comprend pas** :
- Ce qui est attendu de lui précisément (l'empty state reste vague)
- Pourquoi l'IA "active" ne réagit pas à ce qu'il vient d'écrire
- L'état de la décision collective en un coup d'œil (nécessite de scroller)

---

### 2.6 Le dossier final — suffisant pour une personne externe dans 6 mois ?

**Non.**

Ce qui est présent : décision, propositions, sources (titres), actions, réserves, synthèse.

Ce qui manque pour qu'une personne externe comprenne la décision 6 mois plus tard :
- Les hypothèses de départ
- Les contraintes qui ont pesé sur le choix
- Pourquoi les autres propositions ont été écartées
- Les deadlines des actions
- Les critères de succès (comment évaluer la décision a posteriori)
- La qualité réelle des sources (titre uniquement, pas de lien, pas de date)

**Verdict** : le dossier prouve qu'une décision a été prise. Il ne prouve pas que c'était la bonne décision ni comment on le saurait.

---

### 2.7 Question ultime — pourquoi Iris plutôt qu'un chat, Notion ou un document partagé ?

**Ce que Iris fait mieux :**
- Structure d'une décision collective en temps réel — chat et Notion ne cadrent pas le raisonnement
- **Réserves formalisées avec statuts** — unique sur le marché, un chat perd les désaccords dans le fil
- **Dossier final daté** — preuve de due diligence pour les décisions importantes
- Traçabilité de qui a proposé quoi et quand

**Ce que Iris ne fait pas encore et qui justifierait de payer :**
- L'IA ne lit pas les propositions et ne les analyse pas réellement
- Aucune alerte si on avance sans sources suffisantes
- Aucun suivi post-décision (les actions disparaissent dans l'interface)
- Aucune mémoire entre sessions (chaque session repart de zéro)
- Pas d'intégration avec des outils d'exécution (Jira, Notion, calendar)

**Verdict honnête** : Iris est un outil de structuration de réunion de qualité, pas encore un outil d'intelligence augmentée. Sa valeur actuelle est réelle pour les équipes qui ont besoin de formaliser leurs décisions et de garder une trace des réserves. Elle n'est pas encore supérieure à Notion + template pour les équipes qui n'ont pas ces besoins.

La vraie proposition de valeur — les IA qui analysent vraiment — n'existe pas encore dans le système.

---

## PRIORITÉS DE CORRECTION

### Corrections UX immédiates (cohérence état réel / état affiché)

| # | Anomalie | Gravité | Effort estimé |
|---|---|---|---|
| 1 | `.tw-online-badge` toujours vert (cam/mic off) | 🔴 haute | 30 min |
| 2 | Pas d'indicateur "partage écran" sur la tile distante | 🟠 moyenne | 1h |
| 3 | Icônes actions en emoji (incohérent avec SVG P3) | 🟡 faible | 30 min |

### Corrections métier (valeur réelle de la décision)

| # | Manque | Impact | Effort estimé |
|---|---|---|---|
| 4 | Deadline + priorité sur les actions | 🔴 fort | 2-3h |
| 5 | Champ "Critères de réussite" dans le brief | 🔴 fort | 1h |
| 6 | Champ "Contraintes" dans le brief | 🟠 moyen | 1h |
| 7 | Qualité/lien sur les sources | 🟠 moyen | 1h |

### Correction structurelle (proposition de valeur)

| # | Manque | Impact | Effort estimé |
|---|---|---|---|
| 8 | IA réelles : Iris analyse les propositions via LLM | 🔴 critique | majeur |
| 9 | Mémoire inter-sessions | 🟠 moyen | majeur |
| 10 | Suivi actions post-session | 🟠 moyen | 3-4h |

---

## INSTRUCTION POUR CHATGPT

ChatGPT, ce fichier contient un audit complet réalisé par Claude sur Iris Workspace.

Tu trouveras dans ce repo GitHub (`byakuyakutchiki/luna-server`) :

- Ce fichier : `docs/audit_ux/AUDIT_COHERENCE_ET_METHODOLOGIQUE.md`
- L'interface auditée : `static/team_workspace.html`
- Les briefs des évolutions précédentes : `docs/audit_ux/P2_BRIEF_HIERARCHIE_VISUELLE.md` et `docs/audit_ux/P3_BRIEF_DOSSIER_FINAL_PREMIUM.md`
- L'application live : `https://luna-beta-674304336025.europe-west1.run.app/team`

**Ce que Ludo te demande :**

1. Valider ou contredire l'analyse de Claude — es-tu d'accord avec les priorités ?
2. Proposer des solutions concrètes pour les points 4 à 7 (corrections métier)
3. Répondre honnêtement à la question ultime : qu'est-ce qui rendrait Iris indispensable ?
4. Identifier des angles que Claude a manqués

Pas de complaisance. Pas de validation automatique.
