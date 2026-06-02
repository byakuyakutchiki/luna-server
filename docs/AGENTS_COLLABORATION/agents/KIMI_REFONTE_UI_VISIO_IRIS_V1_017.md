# Kimi — Refonte UI visio Iris V1 — Objectif 017

Date : 2026-06-01
Agent : Kimi
Type : refonte UX / proposition V1
Niveau : 2 (refonte visible = validation fondateur requise)

Sources :
- `docs/AGENTS_COLLABORATION/agents/CODEX_MISSION_COLLECTIVE_VISIO_IRIS_017.md`
- `docs/AGENTS_COLLABORATION/agents/CODEX_F12_LOGS_BRUTS_VISIO_IRIS_017.md`
- `docs/AGENTS_COLLABORATION/agents/KIMI_AUDIT_UX_IRIS_REFONTE_VISIO_017.md`

---

## Principe

**Iris = protagoniste. Tout le reste = secondaire ou invisible.**

L'ecran visio n'est pas un tableau de bord. C'est un ecran d'appel video.
Un seul objet merite l'attention : l'avatar d'Iris qui parle, ecoute et reagit.
Tout ce qui distrait de cet objet doit etre cache, deplace ou supprime.

---

## 1. Ce qui doit DISPARAITRE de l'ecran principal

### 1.1 Controles Daily/Simli natifs (provider)

| Element | Pourquoi disparaitre | Alternative |
|---|---|---|
| Barre de controle Daily en bas de l'iframe | Boutons blancs moches, doublons avec nos propres controles, confusion utilisateur | Options SDK `showLeaveButton: false`, `showFullscreenButton: false`, `showLocalVideo: false`, masquer via CSS overlay ou iframe sandbox |
| Bouton camera du provider | L'utilisateur ne doit pas couper sa camera par erreur. C'est un reglage, pas une action principale | Menu parametres (⋮) en haut a droite |
| Bouton micro du provider | Meme raison. Le micro est gere par VAD/PTT, pas par un toggle brut | Menu parametres |
| Nom "Chatbot" ou "Participant" dans l'interface Daily | Incohérence identitaire | Option SDK `userName: 'Iris'` ou masquage CSS |

### 1.2 Boutons Luna secondaires (notre propre UI)

| Bouton | Pourquoi disparaitre de l'ecran principal | Ou le mettre |
|---|---|---|
| `📎 Analyser` (upload) | Action utile mais pas centrale pendant un appel vocal. Risque de couper le fil de la conversation | Menu secondaire ⋮ ou glisser depuis le bord |
| `👥 Inviter` | Action sensible (SMS, cout). Ne doit jamais etre declenchee par un tap accidentel | Menu secondaire ⋮ avec confirmation |
| `🔗 Partager` | Utile mais rare. Pas prioritaire en plein appel | Menu secondaire ⋮ |
| `📝 Notes` | Inutilisable tant que STT non valide. Afficher un bouton inactif = frustration | **Supprimer completement** jusqu'a preuve STT. Reintegrer plus tard dans le menu. |
| `🎙 Iris active` (mute sortant) | Le libelle est ambigu : est-ce le micro de Ludovic ou la voix d'Iris ? | Remplacer par un toggle discret dans le header ou le menu parametres |

### 1.3 Elements visuels parasites

| Element | Probleme | Action |
|---|---|---|
| Badge vision `Iris voit` en bas | Incoherent si la perception n'est pas active. L'observation visuelle montre que le badge dit "Iris voit" alors que la vision n'est pas prouvee | Deplacer en haut a droite, texte honnete : `Vision en attente` → `Iris observe` (seulement apres description reelle) |
| Cadre telephone `#phoneDevice` | Reduit l'avatar a 60% de l'ecran en mobile. Trop petit, trop moche | **Masquer en mobile** (< 768px). Garder eventuellement en desktop si retravaille. |
| Cinematique `Luna decroche...` avec lettres `L` | Reference Luna, pas Iris | `Iris decroche...` + logo Iris (ou avatar miniature) |
| Selecteur duree 15min/30min/1h/2h/Illimite | Trop de choix pour un demarrage rapide. La duree est un reglage, pas une decision principale | Defaut 15 min. Reglage dans menu ⋮ avant ou pendant l'appel. |
| PTT Orb trop gros et central | Recouvre l'avatar. Design lourd. | Orb plus petit, position bas-centre mais z-index sous le bouton raccrocher |

---

## 2. Ce qui doit RESTER visible

### 2.1 Elements obligatoires (ecran principal)

| Element | Role | Position | Style |
|---|---|---|---|
| **Avatar Iris** | Protagoniste. Simli ou Tavus plein ecran. | Tout l'espace entre header et barre basse | Pas de cadre, pas de bordure, ratio preserve |
| **Bouton raccrocher** | Securite. Quitter l'appel doit etre evident. | Bas, fixe, pleine largeur (moins padding) | Rouge `#ef4444`, hauteur 48px, border-radius 12px, texte blanc |
| **Orb Parler / Indicateur VAD** | Action principale vocale. | Centre-bas, au-dessus du bouton rouge | Diametre 64px max, bordure pulse quand ecoute, z-index sous raccrocher |
| **Header** | Identite + statut | Haut, sticky, hauteur 48px | Nom "Iris", statut (● en ligne), minuteur |

### 2.2 Elements contextuels (visibles seulement quand pertinent)

| Element | Quand visible | Ou |
|---|---|---|
| `Iris ecoute...` | Quand VAD detecte parole | Overlay discret sur l'avatar (bordure pulse verte) |
| `Iris reflechit...` | Entre fin parole et debut reponse | Overlay discret (bordure pulse orange) |
| `Iris parle` | Pendant lecture audio TTS | Overlay discret (bordure bleue + waveform mini) |
| `Vision en attente` | Par defaut | Coin haut droit, gris discret |
| `Iris observe : [description]` | Seulement apres reponse vision reelle | Coin haut droit, texte court |

---

## 3. Layout V1 propose (mobile < 768px)

```
+----------------------------------+
| 🔙  Iris    ● en ligne      ⏱ ⋮ |  ← Header 48px
|                                  |
|                                  |
|                                  |
|         ZONE AVATAR              |  ← Iris plein ecran
|         (Simli/Tavus)            |     100% width
|                                  |     flex-grow
|                                  |
|                                  |
|                                  |
+----------------------------------+
|  [⚪]  PARLER                    |  ← Orb VAD/PTT
|       (pulse vert = ecoute)      |     Centre, 64px
+----------------------------------+
|  [     🔴 RACCROCHER      ]      |  ← Bouton securite
|                                  |     Rouge, 48px, sticky
+----------------------------------+
```

### 3.1 Header detail

```
+----------------------------------+
| ←  👤 Iris    ● en ligne    2:34 ⋮ |
+----------------------------------+
```

- **←** (gauche) : retour = raccrocher aussi. Securite double.
- **👤 Iris** (centre-gauche) : nom + mini avatar.
- **● en ligne** (centre) : statut connexion.
- **2:34** (centre-droite) : duree ecoulee.
- **⋮** (droite) : menu parametres (duree, camera, micro, upload, inviter, partager).

### 3.2 Menu parametres (drawer/glisser depuis ⋮)

Quand on tape ⋮, un drawer s'ouvre par le haut ou le bas :

```
+----------------------------------+
|  Parametres de la visio          |
|  ─────────────────────────────   |
|  ⏱  Duree : [15 min ▼]          |
|  📷 Camera : [on ▼]              |
|  🎙 Micro : [auto ▼]             |
|  📎 Analyser un document         |
|  👥 Inviter quelqu'un            |
|  🔗 Partager le lien             |
|  ─────────────────────────────   |
|  [  Fermer  ]                    |
+----------------------------------+
```

**Pourquoi cacher tout ca dans un menu ?**
- Parce que 90% du temps de l'appel, l'utilisateur ne change ni la duree, ni la camera, ni n'invite personne.
- Ces actions sont des reglages, pas des actions conversationnelles.
- Un ecran propre = un ecran ou l'utilisateur parle a Iris sans distraction.

---

## 4. Etats visuels honnetes

### 4.1 Etat "Vision" — la correction la plus importante

**Actuel** : `Iris voit` des le demarrage. Faux. La vision renvoie parfois une description, parfois rien.

**Propose** :

| Etat reel | Texte affiche | Couleur |
|---|---|---|
| Camera non autorisee | `Camera non autorisee` | Rouge discret |
| Camera autorisee, pas encore d'analyse | `Vision en attente` | Gris `#888` |
| Analyse en cours | `Iris regarde...` | Jaune/orange |
| Description recue | `Iris observe : [texte court]` | Vert clair |
| Vision desactivee | `Vision inactive` | Gris transparent |

**Regle** : le texte `Iris voit` ne doit JAMAIS apparaitre sans une description concrete a cote.

### 4.2 Etat audio — feedback utilisateur

| Etat technique | Feedback visuel | Feedback audio |
|---|---|---|
| VAD detecte parole | Bordure avatar pulse vert doux | Aucun (silence respecte) |
| Blob envoye, STT en cours | Bordure pulse orange rapide | Aucun |
| STT reponse recue | Bordure pulse bleu | Aucun |
| TTS lecture | Waveform mini sous avatar | Voix Iris |
| Erreur STT | Bordure rouge breve + toast discret | "Je n'ai pas bien entendu, peux-tu repeter ?" |

---

## 5. Transitions et cinematique

### 5.1 Demarrage

**Actuel** :
1. Logo `L`
2. "Visio avec Luna"
3. Selecteur duree
4. Bouton gris "Demarrer"
5. Ecran pre-test micro/camera

**Propose V1** :
1. Avatar Iris miniature (cercle, style secrétaire) + "Iris"
2. "Iris vous attend en visio"
3. Bouton `🎥 Demarrer` (bleu/violet Luna, pas gris)
4. Pre-test micro/camera en overlay leger (pas un ecran complet)
5. Transition fade vers l'avatar plein ecran

### 5.2 Fin d'appel

**Actuel** : retour abrupt ou reload.

**Propose V1** :
1. Fade out avatar
2. "Iris a raccroche. A bientot."
3. Resume : duree, sujets abordes (si transcript OK)
4. Bouton `Retour au chat`

---

## 6. Checklist validation UX Kimi pour V1

Avant de valider ce layout, je verifierai :

### Identite (bloquant)
- [ ] Zero "Luna" visible
- [ ] Zero "Chatbot" visible
- [ ] Titre = "Iris — Visio"

### Layout (bloquant)
- [ ] Avatar >= 75% hauteur ecran mobile
- [ ] Bouton raccrocher toujours visible, toujours accessible
- [ ] Orb Parler < 64px, ne recouvre pas l'avatar
- [ ] Pas de barre d'actions avec 5 boutons
- [ ] Pas de cadre telephone en mobile
- [ ] Pas de superposition z-index

### Honnetete (bloquant)
- [ ] Badge vision ne dit jamais "Iris voit" sans description
- [ ] Bouton Notes absent tant que STT non valide
- [ ] Bouton Inviter dans menu, pas ecran principal
- [ ] Bouton Analyser dans menu, pas ecran principal

### Feedback (bloquant pour validation visio)
- [ ] Indicateur "Iris ecoute" visible
- [ ] Indicateur "Iris reflechit" visible
- [ ] Indicateur "Iris parle" visible
- [ ] Indicateur erreur STT visible (pas de silence mort)

### Style (bloquant)
- [ ] Pas de bordure grossiere
- [ ] Pas de gris mort
- [ ] Typographie >= 14px
- [ ] Contraste WCAG AA

---

## 7. Decision proposee

### Phase 1 — Niveau 1 (labels + micro-fixs)

Claude ou DeepSeek peut faire sans validation Ludovic :
- Remplacer tous les labels Luna par Iris (22 occurrences cartographiees)
- Corriger le badge vision pour dire "Vision en attente" par defaut
- Masquer le bouton Notes
- Deplacer Analyser/Inviter/Partager dans un menu

### Phase 2 — Niveau 2 (refonte layout)

Requiert validation Ludovic :
- Restructurer le HTML/CSS de simli.html selon le layout V1 ci-dessus
- Supprimer cadre telephone en mobile
- Creer le header sticky + menu parametres
- Repositionner orb PTT + bouton raccrocher
- Ajouter les feedbacks d'etat (ecoute/reflechit/parle)

### Phase 3 — Validation

- Codex capture terrain avec le nouveau layout
- Test phrase : "Iris, est-ce que tu m'entends ?"
- Si STT 200 + reponse pertinente + layout propre → validation UX Kimi possible

---

## 8. Resumé pour l'equipe

| Qui | Action | Niveau |
|---|---|---|
| Claude | Patch labels Luna→Iris + masquer Notes + corriger badge vision | 1 |
| DeepSeek | Verifier qu'aucun handler ancien ne bloque le nouveau layout | 0 |
| Kimi | Valider Phase 1, puis valider Phase 2 apres deploy | 0 |
| Codex | Capture terrain post-Phase 1, puis post-Phase 2 | 0 |
| Ludovic | Valider Phase 2 (refonte layout visible) | 2 |

---

*Reference : CODEX_MISSION_COLLECTIVE_VISIO_IRIS_017.md, CODEX_F12_LOGS_BRUTS_VISIO_IRIS_017.md, KIMI_AUDIT_UX_IRIS_REFONTE_VISIO_017.md*
