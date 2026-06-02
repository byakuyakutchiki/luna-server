# Kimi — Audit UX Iris Workbench V1 — Objectif 019

Date : 2026-06-02
Agent : Kimi
Type : audit UX / validation rendu
Niveau : 0

Source commit : `9b376b2` — `feat(019): ajouter Iris Workbench V1 non destructif`

---

## Verdict global

**Acceptable V1 — avec 5 correctifs à apporter.**

Le Workbench V1 est fonctionnel, non destructif, et respecte la séparation Luna/Iris.
Il ne ressemble pas à un chatbot ajouté au hasard. La structure est propre.
Mais il y a des écarts avec la cible premium et quelques risques mobile.

---

## 1. Ce qui est BIEN ✅

| Critere | Observation | Verdict |
|---|---|---|
| **Separation Luna/Iris** | Kicker "Iris Workbench", titre dynamique par type, pas de mention Luna | ✅ |
| **Non destructif** | Brouillons generiques, pas d'envoi automatique, actions locales (copie, download) | ✅ |
| **Apparition conditionnelle** | S'ouvre uniquement sur mots-cles detects (tableau, courrier, checklist, resume, workbench) | ✅ |
| **Template honnete** | Iris dit "prepare" et demande confirmation, ne pretend pas avoir fini | ✅ |
| **Desktop** | Position haut-droite, orbe pousse a gauche avec translateX(-16vw), elegant | ✅ |
| **Mobile responsive** | Passe en bas pleine largeur, boutons wrap 2x2, max-height 42vh | ✅ |
| **Accessibilite** | aria-live="polite", aria-label="Iris Workbench" | ✅ |
| **Transcript masque** | `#afTranscript { display: none; }` en mobile quand workbench ouvert — bon choix | ✅ |
| **Logs** | `workbench_open`, `workbench_close`, `workbench_copy`, `workbench_download` instrumentes | ✅ |
| **4 types de contenu** | table, letter, checklist, summary + workspace fallback | ✅ |

---

## 2. Ce qui doit etre CORRIGE 🔧

### A. Superposition mobile — risque bloquant

**Probleme** :
```css
.af-inputbar { bottom: calc(92px + env(safe-area-inset-bottom)); }
.af-workbench { bottom: calc(150px + env(safe-area-inset-bottom)); }
```

Sur mobile, la barre d'input est a 92px du bas. Le workbench est a 150px du bas.
Ecart = 58px.

Si le workbench atteint sa `max-height: 42vh`, il peut depasser les 58px d'ecart et **recouvrir la barre d'input** sur un ecran court (iPhone SE 375x667, ratio 16:9).

**Preuve** :
- iPhone SE : hauteur utile ~ 560px. 42vh = 235px. Le workbench part du bas a 150px, donc il monte jusqu'a ~385px depuis le haut. La barre d'input est a 92px du bas = ~468px depuis le haut. Theoriquement pas de recouvrement... mais avec du contenu long et le scroll interne, l'experience est serree.
- Android petit (320x568) : hauteur utile ~ 460px. 42vh = 193px. Workbench du bas a 150px = monte a ~257px depuis le haut. Barre a 92px = ~368px depuis le haut. Ca passe, mais c'est tres juste.

**Correction proposee** :
```css
@media (max-width: 820px) {
  .af-workbench {
    left: 14px; right: 14px; top: auto;
    bottom: calc(156px + env(safe-area-inset-bottom)); /* etait 150px → 156px pour marge */
    width: auto; max-height: 38vh; /* etait 42vh → 38vh pour marge */
    border-radius: 16px;
  }
}
```

### B. Palette — ecart avec l'identite Iris

**Probleme** : Le workbench utilise du **vert menthe** (`rgba(0,220,170,...)`) comme couleur d'accent.

Cette couleur vient de l'heritage Daily/Simli (le vert etait la couleur du provider Simli).
Iris doit avoir sa propre identite visuelle, distincte de Luna (indigo) et de Simli (vert).

**Ma proposition V1** : violet Iris `#a78bfa` comme accent principal.

**Ou on en est** :
- Bordure workbench : vert menthe
- Bouton primary (Copier) : vert menthe
- Bouton Envoyer (inputbar) : vert menthe

**Correction proposee** :
```css
.af-workbench { border: 1px solid rgba(167,139,250,0.22); } /* violet Iris */
.af-workbench-actions button.primary {
  border-color: rgba(167,139,250,0.35);
  background: rgba(139,92,246,0.18);
  color: rgba(196,181,253,0.95);
}
#afTextSend {
  border-color: rgba(167,139,250,0.3);
  background: rgba(139,92,246,0.15);
  color: rgba(196,181,253,0.92);
}
.af-workbench-kicker { color: rgba(196,181,253,0.75); }
```

### C. Etats visuels manquants

**Probleme** : Le workbench n'a qu'un seul etat visuel : "Brouillon prêt" / "En cours" / "En attente".
Pas de pulse, pas de couleur d'etat, pas de difference entre :
- Analyse
- Redaction
- Pret
- Validation requise
- Sauvegarde
- Termine

**Dans le code** :
```javascript
function _afSetWorkbenchState(text) {
  var state = document.getElementById('afWorkbenchState');
  if (state) state.textContent = text || 'En cours';
}
```

Juste un changement de texte. Pas de classe CSS, pas de couleur, pas d'animation.

**Correction proposee** :
Ajouter des classes d'etat :
```css
#afWorkbenchState.state-analyse { color: #fbbf24; border-color: rgba(251,191,36,0.3); }
#afWorkbenchState.state-ready { color: #4ade80; border-color: rgba(74,222,128,0.3); }
#afWorkbenchState.state-error { color: #f87171; border-color: rgba(248,113,113,0.3); }
```

Et dans JS :
```javascript
function _afSetWorkbenchState(text, stateClass) {
  var state = document.getElementById('afWorkbenchState');
  if (state) {
    state.textContent = text || 'En cours';
    state.className = stateClass || '';
  }
}
```

### D. Bouton "Modifier" — non fonctionnel

**Probleme** : Le bouton "Modifier" est affiche mais je ne vois pas de handler attaché dans le code lu.

**Dans le code** :
```javascript
// Bouton Edit — pas de handler visible dans les lignes lues
// Il y a afWorkbenchEdit, afWorkbenchCopy, afWorkbenchDownload, afWorkbenchClose
// Seuls Copy, Download, Close ont des handlers (lines 3255-3282)
```

Verifier si un handler existe ailleurs. Si non, le bouton doit soit fonctionner (contentEditable), soit etre masque.

**Correction proposee** : Rendre le contenu editable :
```javascript
function _afEditWorkbench() {
  var content = document.getElementById('afWorkbenchContent');
  if (content) {
    content.contentEditable = true;
    content.focus();
    _afSetWorkbenchState('En edition');
  }
}
// + ecouteur sur afWorkbenchEdit
```

### E. Cohérence "secretaire opératrice" — le contenu est trop generique

**Probleme** : Les templates sont des placeholders tres generiques :

```
"Iris prepare un courrier a partir de ta demande. Avant de finaliser, 
il faut confirmer : le destinataire, l'objectif exact, le ton souhaite..."
```

C'est honnete, mais ça ne donne pas l'impression qu'**Iris travaille reellement**. C'est un panneau qui dit "je pourrais travailler" plutot que "je travaille".

**Pour V1 c'est acceptable** car le backend de generation de contenu n'est pas encore branche.
**Mais pour V2** : le contenu doit apparaitre progressivement, ligne par ligne, comme si Iris tapait.

---

## 3. Checklist validation UX Kimi — Workbench V1

| Critere | Etat | Commentaire |
|---|---|---|
| Orbe Iris visible et reactif | ✅ | 4 etats dans le code audio-first |
| Panneau apparait uniquement sur production | ✅ | Detection par mots-cles |
| 4 types de contenu V1 | ✅ | table, letter, checklist, summary |
| Zero confusion Luna/Iris dans les labels | ✅ | "Iris Workbench" |
| Pas de superposition desktop | ✅ | Position haut-droite propre |
| Pas de superposition mobile | ⚠️ | Tres juste, corriger bottom + max-height |
| Style premium applique | ⚠️ | Herite du vert Simli, pas du violet Iris |
| Etats visuels clairs | ❌ | Texte seulement, pas de couleur/animation |
| Bouton "Modifier" fonctionnel | ❌ | Non branche (a verifier) |
| Confirmation avant action engageante | ✅ | Pas d'action engageante dans V1 |
| Mobile orbe + panneau utilisables | ⚠️ | Panneau en bas, serre mais fonctionnel |
| Historique Workbench | ❌ | Non present en V1 (OK pour V1) |

---

## 4. Recommandations priorisees

| Priorite | Correction | Niveau | Qui |
|---|---|---|---|
| P1 | Fixer superposition mobile (bottom 156px, max-height 38vh) | 1 | Claude/DeepSeek |
| P1 | Passer la palette vert → violet Iris | 1 | Claude/DeepSeek |
| P2 | Ajouter classes d'etat visuel (analyse, pret, erreur) | 1 | Claude/DeepSeek |
| P2 | Brancher bouton "Modifier" (contentEditable) | 1 | Claude/DeepSeek |
| P3 | Contenu progressif "Iris tape" pour V2 | 2 | Future iteration |
| P3 | Historique Workbench | 2 | Future iteration |

---

## 5. Position finale

**Je valide le Workbench V1 comme base fonctionnelle et non destructif.**

Mais je ne valide pas le rendu comme "premium" tant que :
1. La palette n'est pas passe au violet Iris
2. Le mobile n'a pas de marge de securite corrigee
3. Les etats visuels ne sont pas materialises par des couleurs

**Decision** : Corriger les 4 points P1-P2, puis re-soumettre a validation Kimi.

---

*Reference : KIMI_UX_IRIS_WORKBENCH_V1_019.md, OBJECTIF_019_LUNA_IRIS_ACTION_PANEL.md*
