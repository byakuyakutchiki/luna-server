# Kimi — Audit UI mobile réel — Objectif 017

**Agent** : Kimi (œil terrain + qualité visuelle)  
**Date** : 2026-06-01  
**Source** : Capture ADB réelle `phone_tests/codex-luna-20260601-182019/screen.png` (1220×2712px, Android)  
**Référence** : `OBJECTIF_017_BANC_TEST_REEL_TELEPHONE.md`

---

## Méthode

- Analyse visuelle de la capture écran réelle du téléphone Android de Ludovic
- Aucun test fonctionnel lancé, aucun crédit consommé
- Comparaison avec les standards qualité graphique établis (TASK-002-KIMI-VISUAL-QUALITY-GATE)

---

## Verdict global

| Critère | Note | Commentaire |
|---|---|---|
| **Header** | 8/10 | Propre, cohérent, avatar + nom + température bien alignés |
| **Onglets** | 7/10 | Lisibles, mais "Monde" est tronqué (scroll horizontal visible) |
| **Bulles messages** | 4/10 | **3 régressions visibles** : LUNA vertical, bulle étroite, pollution visio |
| **Input** | 7/10 | Standard, emoji + champ texte + envoi + menu action visibles |
| **Immersion** | 5/10 | La pollution "Visio lancée" casse la conversation. Le LUNA vertical est cheap. |

**Verdict** : La capture prouve que l'app fonctionne sur mobile, mais **3 bugs visuels régressent l'expérience**. Priorité P1 — corriger avant tout test visio.

---

## Bug 1 — "LUNA" s'empile verticalement (P1)

### Description visuelle

**Localisation** : ~65% de la hauteur de l'écran (y≈1760 sur 2712px)  
**Apparence** : Le nom "LUNA" est affiché lettre par lettre verticalement : "L" en haut, "U" dessous, "N", puis "A". Chaque lettre occupe sa propre ligne. L'avatar Luna (cercle avec photo) est à gauche, coupé/déformé.

### Capture

```
[avatar]  L
          U
          N
          A
   04:49
```

### Cause probable

**CSS** : `.luna-name` (ligne 346 + 1082 de `static/index.html`)

```css
.luna-name { 
  display: block; 
  position: absolute; 
  left: 48px; 
  top: -22px;
  text-transform: uppercase;
  letter-spacing: .1em;
}
.msg { max-width: 80%; word-break: break-word; }
.luna { position: relative; padding-top: 28px; margin-top: 32px; }
```

**Explication** :
1. `.luna` a `position: relative` → le `.luna-name` en `position: absolute` est contraint par la largeur de la bulle parente
2. Quand le message est vide ou très court, la bulle se rétrécit à ~80-100px de large (pas de `min-width` sur `.msg`)
3. Le texte "LUNA" + `letter-spacing: .1em` + `text-transform: uppercase` ne tient pas en horizontal dans 80-100px
4. `word-break: break-word` sur `.msg` hérite et force le retour à la ligne après chaque lettre
5. Résultat : "LUNA" vertical

### Correction proposée

**Option A — rapide (1 ligne CSS)** :
```css
.luna-name { white-space: nowrap; }
```
→ Force "LUNA" sur une seule ligne, même si ça dépasse la bulle.

**Option B — meilleure (2 lignes CSS)** :
```css
.luna { min-width: 160px; }
.luna-name { white-space: nowrap; }
```
→ La bulle ne peut plus se rétrécir en dessous de 160px. Le nom tient en horizontal.

**Option C — la meilleure (structure)** :
Placer `.luna-name` en dehors de la bulle `.msg`, au-dessus, pour qu'il ne soit jamais contraint par la largeur de la bulle. Nécessite modification du HTML dans `addMsg()`.

**Recommandation Kimi** : Option B pour un patch immédiat. Option C pour une correction durable.

---

## Bug 2 — Bulle/message trop étroite (P1)

### Description visuelle

C'est la **même bulle** que le Bug 1. La bulle contenant "LUNA" vertical a une largeur d'environ 80-100px, ce qui est insuffisant pour tout contenu texte lisible.

### Cause probable

`.msg` n'a pas de `min-width`. Quand le contenu est vide ou très court, la bulle se rétrécit jusqu'à la largeur du padding (12px + 16px = 28px) + la largeur du contenu minimal.

### Correction proposée

```css
.msg { min-width: 120px; }
```

Ou mieux, avec les media queries mobiles existantes :

```css
@media (max-width: 480px) {
  .msg { min-width: 140px; }
}
```

**Impact** : Aucune bulle ne pourra plus être aussi étroite. Cela corrige à la fois le Bug 1 et le Bug 2.

---

## Bug 3 — "Visio lancée (3 min prévues)" pollue l'historique (P1)

### Description visuelle

**3 occurrences** dans l'historique visible :
- `04:47` — "Visio lancée (3 min prévues)"
- `04:55` — "Visio lancée (3 min prévues)"
- `00:14` — "Visio lancée (3 min prévues)"

Ces messages système polluent la conversation texte. Ils ont le même style visuel que les messages Luna normaux (bulle violette, avatar, nom "LUNA"), ce qui les rend indiscernables des vraies réponses de Luna.

### Cause

**Code** : `static/index.html` ligne 4621

```javascript
addMsg("Visio lancee (" + minutes + " min prevues)", "luna");
```

Chaque lancement de visio appelle `addMsg()` avec la classe `"luna"`, ce qui affiche la bulle exactement comme un message de conversation.

### Impact produit

1. **Pollution cognitive** : l'utilisateur voit 3 fois le même message système dans son historique
2. **Indiscernable** : le message a le même style visuel qu'une vraie réponse de Luna
3. **Historique gonflé** : chaque visio = +1 message persistant (sauf si `skipSave=true`)
4. **Non premium** : une app premium sépare les notifications système des messages conversationnels

### Correction proposée

**Option A — style différent (CSS uniquement)** :
Créer une classe `.msg-system` ou utiliser `addMsg(..., "system")` avec un style discret (texte centré, gris, sans avatar, sans bulle) :

```css
.msg-system {
  align-self: center;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #888;
  font-size: 0.8em;
  padding: 4px 12px;
  max-width: 100%;
}
.msg-system::before { display: none; } /* pas d'avatar */
.msg-system .luna-name { display: none; }
```

**Option B — ne pas persister (1 ligne JS)** :
```javascript
addMsg("Visio lancee (" + minutes + " min prevues)", "luna", undefined, true); // skipSave=true
```
→ Le message apparaît mais n'est pas sauvegardé dans l'historique. Il disparaît au rechargement.

**Option C — ne pas afficher du tout** :
La visio a déjà sa propre page (`simli.html`). Informer l'utilisateur dans l'interface visio, pas dans le chat texte.

**Recommandation Kimi** : Option A + B combinées. Style discret + non persistant.

---

## Autres observations (non bloquantes)

### Onglet "Monde" tronqué
L'onglet "Monde" à droite de la barre d'onglets est partiellement visible/tronqué. Le scroll horizontal des onglets est fonctionnel mais donne l'impression que quelque chose est coupé.

**Recommandation** : Ajouter un padding droit sur le conteneur d'onglets pour que le dernier onglet ne soit pas collé au bord.

### Avatar dans le header
L'avatar Luna dans le header (en haut à gauche) est bien rendu, propre, avec le badge vert de présence. C'est un point fort.

### Bulle principale Luna (04:47)
La grande bulle de texte Luna en haut est correctement dimensionnée, bien lisible, couleurs cohérentes. Le texte est bien wrapé. C'est le standard à atteindre pour toutes les bulles.

---

## Synthèse actionnable

| Priorité | Bug | Correction | Qui | Fichier | Lignes |
|---|---|---|---|---|---|
| P1 | LUNA vertical + bulle étroite | `min-width: 140px` sur `.msg` + `white-space: nowrap` sur `.luna-name` | Claude | `static/index.html` | ~296, ~346, ~1082 |
| P1 | Visio pollue historique | Classe `.msg-system` discrète + `skipSave=true` | Claude | `static/index.html` | ~4621 |
| P2 | Onglet "Monde" tronqué | Padding droit sur conteneur onglets | Claude | `static/index.html` | ~onglets |

---

## Position Kimi

**Je ne valide pas l'expérience mobile** tant que :
1. Le Bug 1 (LUNA vertical) n'est pas corrigé — c'est visuellement cheap et immédiatement visible
2. Le Bug 3 (pollution visio) n'est pas corrigé — ça gâche l'historique conversationnel

**Le Bug 2 (bulle étroite)** est corrigé par la même patch que le Bug 1.

**Recommandation** : patcher ces 2 bugs P1 avant tout test visio. Un utilisateur qui ouvre l'app et voit "LUNA" vertical + 3 messages "Visio lancée" ne percevra pas une app premium.

---

*Kimi — œil terrain. Aucun test fonctionnel lancé. Aucun crédit consommé.*
