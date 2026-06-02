# Kimi — Refonte UI visio Iris V2 (premium) — Objectif 018

Date : 2026-06-02
Agent : Kimi
Type : refonte UX V2 / vision decor
Niveau : 2 (validation Ludovic requise)

Source : `docs/AGENTS_COLLABORATION/OBJECTIF_018_VISIO_IRIS_ORDRE_DE_BATAILLE.md`

---

## Principe V2

**Iris = assistante visio de Luna. Vive, technique, proactive, type Jarvis humain.**

Le decor visio n'est pas un habillage. C'est le cadre de credibilite d'Iris.
Si le cadre est moche, Iris ne sera jamais credible — meme avec la meilleure voix du monde.

---

## 1. Ce qui doit DISPARAITRE (liste definitive)

| Element | Raison |
|---|---|
| Barre blanche Daily/Simli en bas | Doublon, moche, confusion |
| Bouton camera du provider | Reglage, pas action principale |
| Bouton micro du provider | Gere par VAD |
| Nom "Chatbot" / "Participant" | Incohérence identitaire |
| `📝 Notes` | Inutilisable tant que transcript non valide (Phase 3) |
| `👥 Inviter` | Action sensible (SMS, cout). Menu uniquement |
| `🔗 Partager` | Rare. Menu uniquement |
| `📎 Analyser` | Action secondaire. Menu ou glisser |
| Cadre telephone `#phoneDevice` | Reduit avatar a 60%. Mobile = plein ecran |
| Selecteur duree au demarrage | Reglage, pas decision. Menu ou defaut 15 min |
| Cinematique "Luna decroche" | Luna n'est pas l'interlocutrice |
| Logo `L` ecran demarrage | Remplacer par identifiant Iris |
| Badge `Iris voit` par defaut | Mensonger. `Vision en attente` par defaut |
| Bouton `🎙 Iris active/muette` ambigu | Remplacer par toggle discret dans header |
| Grain video / letterbox | Obsolet, pas premium. Garder seulement si subtil |

---

## 2. Ce qui doit RESTER (ecran principal uniquement)

| Element | Role | Position | Style |
|---|---|---|---|
| **Avatar Iris** | Protagoniste. Plein cadre. | Tout l'escran sauf header + barre basse | Aucune bordure. Ratio preserve. Fond degrade subtil si pas d'avatar |
| **Header discret** | Identite + statut + contexte | Haut, sticky, 44px | Fond blur noir 40%. Texte blanc 14px. Pas de bordure |
| **Orb Parler / VAD** | Action principale vocale | Centre-bas, au-dessus du bouton rouge | Diametre 56px. Bordure 2px pulse. Couleur adaptee a l'etat |
| **Bouton raccrocher** | Securite | Bas, fixe, pleine largeur | Rouge `#ef4444`, 48px, radius 12px. Texte blanc gras |

---

## 3. Decor premium propose

### 3.1 Palette

| Role | Couleur | Usage |
|---|---|---|
| Fond principal | `#0a0a0f` | Ecran visio |
| Fond header | `rgba(10,10,15,0.65)` + blur(20px) | Header sticky |
| Accent Iris | `#a78bfa` | Violet doux = identite Iris |
| Accent Luna | `#6366f1` | Indigo = garde-fou marque |
| Actif / ecoute | `#4ade80` | Vert pulse |
| Traitement | `#fbbf24` | Orange pulse |
| Erreur | `#f87171` | Rouge bref |
| Raccrocher | `#ef4444` | Bouton securite |
| Texte | `#f0f0f5` | Principal |
| Texte mute | `#6b7280` | Secondaire |

### 3.2 Typographie

- **Iris** (nom) : Inter 600, 15px, letter-spacing -0.01em
- **Statut** : Inter 400, 12px, couleur adaptee
- **Timer** : Inter 500, 13px, chiffres tabulaires
- **Bouton raccrocher** : Inter 600, 15px

### 3.3 Animations

| Transition | Duree | Courbe |
|---|---|---|
| Header apparition | 300ms | ease-out |
| Avatar plein ecran | 400ms | cubic-bezier(0.4, 0, 0.2, 1) |
| Orb pulse ecoute | 1.2s infinite | ease-in-out |
| Orb pulse traitement | 0.6s infinite | ease-in-out |
| Bouton raccrocher press | 100ms | scale(0.97) |
| Toast / overlay | 250ms | ease-out |

---

## 4. Layout V2 detail (mobile < 768px)

```
+----------------------------------+
| ←  👤 Iris    ● en ligne    2:34 ⋮ |  Header 44px
|                                  |
|                                  |
|                                  |
|         AVATAR IRIS              |  Flex-grow, min 75% hauteur
|         (plein cadre)            |
|                                  |
|                                  |
|                                  |
+----------------------------------+
|           [⚪]                   |  Orb 56px
|         PARLER                   |  Label 11px sous l'orb
+----------------------------------+
|  [      🔴 RACCROCHER      ]     |  48px, sticky bottom
+----------------------------------+
```

### 4.1 Header detail

```
+----------------------------------+
| ←  👤  Iris       ● en ligne   2:34  ⋮ |
+----------------------------------+
```

| Zone | Element | Action tap |
|---|---|---|
| Gauche | Fleche ← | Raccrocher (double securite) |
| Centre-G | Mini avatar + "Iris" | Aucun (identite) |
| Centre | ● + statut | Aucun (info) |
| Centre-D | Timer `MM:SS` | Aucun (info) |
| Droite | ⋮ | Ouvre menu parametres |

### 4.2 Menu parametres (drawer haut)

Quand on tape ⋮, un drawer glisse depuis le haut :

```
+----------------------------------+
|  Parametres          [✕]         |
|  ─────────────────────────────   |
|  ⏱  Duree restante : 12 min      |
|  📷 Camera [on ▼]                |
|  🎙 Micro [auto ▼]               |
|  👁 Vision [active ▼]             |
|  ─────────────────────────────   |
|  📎 Analyser un document         |
|  👥 Inviter un participant       |
|  🔗 Partager le lien             |
|  📝 Notes (bientot)              |  ← Grise, non cliquable
|  ─────────────────────────────   |
|  [  Fermer  ]                    |
+----------------------------------+
```

**Regle** : tout element non disponible est grise avec raison claire.

### 4.3 Etats de l'orb

| Etat technique | Apparence orb | Label |
|---|---|---|
| Silence / attente | Bordure grise statique | `Appuyez pour parler` |
| VAD detecte parole | Bordure verte pulse 1.2s | `Iris ecoute...` |
| Blob envoye, STT | Bordure orange pulse 0.6s | `Iris reflechit...` |
| TTS lecture | Bordure bleue + waveform mini | `Iris repond...` |
| Erreur STT | Bordure rouge pulse 2x puis gris | `Reessayez` |

### 4.4 Vision — badge honnete

| Etat reel | Badge header | Couleur |
|---|---|---|
| Camera non autorisee | `Camera bloquee` | Rouge |
| Autorisee, pas d'analyse | `Vision en attente` | Gris |
| Analyse en cours | `Iris regarde...` | Orange |
| Description recue | `Iris observe : [texte]` | Vert |
| Desactivee | `Vision off` | Gris transparent |

**Position** : coin haut droit, sous le header, 12px, fond blur.

---

## 5. Ecran demarrage V2

### 5.1 Actuel (problemes)

- Logo `L` = Luna, pas Iris
- "Visio avec Luna"
- Selecteur duree trop prominent
- Bouton gris

### 5.2 Propose V2

```
+----------------------------------+
|                                  |
|          [👤 Avatar Iris]        |  Cercle 120px, animation subtile
|                                  |
|        Iris vous attend          |  Inter 600, 18px
|     en visio conversationnelle   |  Inter 400, 14px, #888
|                                  |
|        ⏱ 15 minutes              |  Texte discret, changeable via ⋮
|                                  |
|     [   🎥  Demarrer   ]         |  Accent Iris #a78bfa, 48px
|                                  |
|         ← Retour au chat         |  Lien discret
|                                  |
+----------------------------------+
```

**Changements** :
- Avatar Iris au centre (meme source que l'avatar Simli/Tavus ou illustration)
- Pas de logo Luna
- Duree = texte discret, pas selecteur
- Bouton = accent Iris, pas gris neutre

---

## 6. Fin d'appel

### 6.1 Actuel

Retour abrupt ou reload.

### 6.2 Propose V2

```
+----------------------------------+
|                                  |
|          [👤 Avatar Iris]        |
|                                  |
|        Iris a raccroche          |
|         A bientot, Ludovic       |
|                                  |
|        Duree : 4 min 32s         |
|                                  |
|     [  Retour au chat  ]         |
|                                  |
+----------------------------------+
```

**Si transcript disponible** (Phase 3) :
- Resume 2-3 lignes des sujets abordes
- Bouton `Voir le resume`

---

## 7. Phasage et dependances

| Phase | Quoi | Qui | Depend de |
|---|---|---|---|
| 1a | Labels Luna→Iris + badge vision corrige | Claude | Rien |
| 1b | Voix ElevenLabs jeune/rapide + latence < 3s | Claude + DeepSeek | Deploy |
| 2 | Vision honnete + description integree | Claude + DeepSeek | Phase 1 |
| 3 | Notes + resume + contexte + actions | Claude | Phase 2 |
| 4a | Refonte layout V2 (HTML/CSS) | Claude | Validation Kimi + Ludovic |
| 4b | Decor premium (palette, animations, typographie) | Claude | Phase 4a |

**Kimi valide chaque phase avant passage a la suivante.**

---

## 8. Checklist validation V2

### Avant Phase 4 (decor)
- [ ] Phase 1 audio validee (voix jeune, < 3s, naturelle)
- [ ] Phase 2 vision validee (badge honnete, description reelle)
- [ ] Phase 3 capacites validees (notes, resume, contexte)

### Phase 4 — Decor
- [ ] Avatar >= 75% hauteur ecran
- [ ] Header 44px, discret, blur
- [ ] Zero bouton sans target sur ecran principal
- [ ] Menu parametres compact
- [ ] Orb 56px, etats clairs
- [ ] Bouton raccrocher rouge, toujours visible
- [ ] Badge vision honnete
- [ ] Palette premium appliquée
- [ ] Animations fluides
- [ ] Zero "Luna" visible
- [ ] Zero "Chatbot" visible
- [ ] Persona Iris = vive, proactive, Jarvis humain

---

*Reference : OBJECTIF_018_VISIO_IRIS_ORDRE_DE_BATAILLE.md, KIMI_REFONTE_UI_VISIO_IRIS_V1_017.md*
