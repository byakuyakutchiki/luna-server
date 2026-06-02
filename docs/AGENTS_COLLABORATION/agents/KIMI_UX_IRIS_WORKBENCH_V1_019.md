# Kimi — UX Iris Workbench V1 — Objectif 019

Date : 2026-06-02
Agent : Kimi
Type : refonte UX / vision produit
Niveau : 2 (validation Ludovic requise)

Source : `docs/AGENTS_COLLABORATION/OBJECTIF_019_LUNA_IRIS_ACTION_PANEL.md`

---

## Principe

**Iris ne parle pas dans le vide. Iris travaille dans un panneau.**

Quand Ludovic demande a Iris de rediger un courrier, resumer une reunion, ou preparer une checklist, le resultat doit apparaitre dans un espace de travail visible, propre et premium.

Ce n'est pas un chat. C'est un bureau de secretaire.

---

## 1. Separation Luna / Iris dans l'interface

### Luna — Ecran conversationnel (existant)

- Chat texte/vocal
- Conseil, discussion, accompagnement
- Pas d'action engageante
- Avatar/identite Luna (si presente)

### Iris — Ecran Workbench (nouveau)

- Voix + panneau de travail
- Production documentaire
- Actions avec confirmation
- Identite Iris distincte

**Regle d'or** : jamais les deux identites dans le meme espace sans transition claire.

---

## 2. Architecture ecran Iris Workbench V1

```
+------------------------------------------+
|  🌙 Luna          [🔊 Appeler Iris]      |  ← Header global Luna (persistent)
+------------------------------------------+
|                                          |
|         ZONE IRIS AUDIO                  |  ← Orbe + statut vocal
|         (plein ecran quand actif)        |     Orbe pulse = ecoute
|                                          |     Orbe fixe = silence
|                                          |
+------------------------------------------+
|  Iris prepare votre courrier...          |  ← Statut ligne (contextuel)
+------------------------------------------+
|  +------------------------------------+  |
|  |  📝 Brouillon de courrier          |  |  ← Workbench Panel
|  |                                    |  |
|  |  Objet : Demande de resiliation    |  |
|  |                                    |  |
|  |  Madame, Monsieur,                 |  |
|  |  Je vous ecris pour...             |  |
|  |  [..............................]  |  |
|  |                                    |  |
|  |  [✏ Modifier] [💾 Sauvegarder]     |  |
|  |  [📥 Telecharger] [❌ Annuler]     |  |
|  +------------------------------------+  |
+------------------------------------------+
```

---

## 3. Le Workbench Panel — detail

### 3.1 Apparition

Le panneau n'apparait pas tout le temps. Il s'affiche **uniquement** quand Iris produit quelque chose.

| Declencheur | Apparition |
|---|---|
| "Iris, prepare-moi un courrier" | Panneau courrier |
| "Iris, resume notre conversation" | Panneau resume |
| "Iris, fais une checklist" | Panneau checklist |
| "Iris, prepare un tableau" | Panneau tableau |
| Conversation generale | Pas de panneau, juste l'orbe |

### 3.2 Etats du panneau

| Etat | Visuel | Action utilisateur |
|---|---|---|
| **Analyse** | Bordure pulse orange + squelette | Attendre |
| **Redaction** | Bordure pulse violet + texte qui apparait ligne par ligne | Attendre / interrompre |
| **Pret** | Bordure verte fixe + contenu complet | Modifier, sauvegarder, telecharger, annuler |
| **Validation requise** | Bandeau jaune "Confirmer avant envoi" | Lire, confirmer, modifier, annuler |
| **Sauvegarde** | Spinner + "Sauvegarde dans Documents..." | Attendre |
| **Termine** | Check vert + "Sauvegarde dans Documents" | Fermer le panneau |

### 3.3 Types de contenu V1

#### A. Note / Resume

```
+------------------------------------+
|  📝  Resume de conversation        |
|      Genere par Iris               |
+------------------------------------+
|                                    |
|  Sujets abordes :                  |
|  • Demande de resiliation EDF      |
|  • Rappel rendez-vous dentiste     |
|  • Idee cadeau anniversaire        |
|                                    |
|  Actions a suivre :                |
|  ☐ Envoyer le courrier EDF         |
|  ☐ Confirmer le RDV dentiste       |
|                                    |
+------------------------------------+
```

#### B. Brouillon de courrier

```
+------------------------------------+
|  📄  Brouillon de courrier         |
|      A valider avant envoi         |
+------------------------------------+
|                                    |
|  Destinataire : EDF                |
|  Objet : Demande de resiliation    |
|                                    |
|  [Zone editable]                   |
|  Madame, Monsieur,                 |
|  Je vous ecris pour...             |
|  [..............................]  |
|                                    |
+------------------------------------+
```

#### C. Checklist

```
+------------------------------------+
|  ✓  Checklist : Preparer demenagement |
+------------------------------------+
|                                    |
|  ☐ Resilier EDF                    |
|  ☑ Resilier internet               |
|  ☐ Prevenir la poste               |
|  ☐ Reserver camion                 |
|                                    |
|  [➕ Ajouter un item]              |
+------------------------------------+
```

#### D. Tableau simple

```
+------------------------------------+
|  📊  Comparaison offres            |
+------------------------------------+
|  Fournisseur | Prix | Delai | Note |
|  EDF         | 89€  | 5j    |  ★★★ |
|  Engie       | 76€  | 3j    |  ★★★★ |
|  TotalEnergies| 72€ | 7j    |  ★★★ |
+------------------------------------+
```

---

## 4. Style premium

### 4.1 Palette Iris Workbench

| Role | Couleur | Code |
|---|---|---|
| Fond panneau | Gris tres froid | `#0f0f1a` |
| Bordure panneau | Violet Iris subtil | `rgba(167,139,250,0.15)` |
| Bordure active (analyse) | Orange pulse | `#fbbf24` |
| Bordure active (redaction) | Violet pulse | `#a78bfa` |
| Bordure pret | Vert fixe | `#4ade80` |
| Texte principal | Blanc casse | `#f0f0f5` |
| Texte secondaire | Gris clair | `#9ca3af` |
| Bouton primaire | Violet Iris | `#a78bfa` |
| Bouton secondaire | Gris surface | `#1e1e2e` |
| Bouton danger | Rouge doux | `#f87171` |

### 4.2 Typographie

- **Titre panneau** : Inter 600, 16px, letter-spacing -0.01em
- **Sous-titre** : Inter 400, 12px, gris
- **Contenu** : Inter 400, 14px, line-height 1.6
- **Boutons** : Inter 500, 13px

### 4.3 Animations

| Transition | Duree | Effet |
|---|---|---|
| Apparition panneau | 300ms | Slide up + fade |
| Texte qui s'ecrit | 20ms/char | Apparition progressive |
| Bordure pulse | 1.5s | Box-shadow pulse |
| Bouton hover | 150ms | Background lighten |
| Fermeture panneau | 200ms | Fade out + slide down |

### 4.4 Orbe Iris Audio

L'orbe remplace l'avatar video.

```
    +--------+
    |   ⚪   |   ← Orbe central, 80px
    |        |     Pulse doux quand ecoute
    |  Iris  |     Pulse rapide quand parle
    +--------+
```

**Couleurs orbe** :
- Attente : gris `#6b7280`, glow faible
- Ecoute : vert `#4ade80`, pulse 2s
- Reflexion : orange `#fbbf24`, pulse 1s
- Parole : violet `#a78bfa`, glow fort
- Erreur : rouge `#f87171`, pulse 3x rapide

---

## 5. Comportements critiques

### 5.1 Confirmation avant action engageante

Quand Iris propose d'envoyer un email, SMS, ou effectuer une reservation :

```
+------------------------------------+
|  ⚠️  Action a confirmer            |
+------------------------------------+
|                                    |
|  Iris suggere d'envoyer :          |
|                                    |
|  A : contact@edf.fr                |
|  Objet : Demande de resiliation    |
|                                    |
|  [📄 Voir le brouillon]            |
|                                    |
|  [✅ Confirmer l'envoi]            |
|  [✏ Modifier] [❌ Annuler]         |
|                                    |
+------------------------------------+
```

**Jamais d'envoi automatique.** Toujours un panneau intermediaire.

### 5.2 Interruption

Ludovic peut interrompre Iris a tout moment :
- Bouton "Stop" sur l'orbe
- Parole "Stop Iris" ou "Annule"
- Le panneau en cours reste en etat "Interrompu" avec option "Reprendre" ou "Annuler"

### 5.3 Historique Workbench

Un historique des productions Iris est accessible :
- Icône 📋 dans le header
- Liste des derniers brouillons/courriers/checklists
- Filtre par type et date
- Possibilite de rouvrir un ancien brouillon

---

## 6. Mobile (< 768px)

```
+----------------------------------+
|  🌙 Luna    [🔊]                |  ← Header compact
+----------------------------------+
|                                  |
|           [⚪]                   |  ← Orbe Iris 64px
|          Iris                    |
|                                  |
+----------------------------------+
|  Iris prepare votre courrier...  |
+----------------------------------+
|  +------------------------------+|
|  | 📝 Brouillon de courrier     ||
|  |                              ||
|  | [Scrollable content]         ||
|  |                              ||
|  | [✏] [💾] [📥] [❌]          ||
|  +------------------------------+|
+----------------------------------+
```

- Panneau = plein largeur, border-radius haut 20px
- Boutons d'action en ligne scrollable
- Contenu scrollable dans le panneau
- Orbe toujours visible au-dessus

---

## 7. Checklist validation UX Kimi

### Avant deploiement V1

- [ ] Orbe Iris visible et reactif (4 etats)
- [ ] Panneau apparait uniquement sur production
- [ ] 4 types de contenu V1 testes : note, courrier, checklist, tableau
- [ ] Etats visuels : analyse, redaction, pret, validation, sauvegarde, termine
- [ ] Confirmation obligatoire avant toute action engageante
- [ ] Bouton "Stop" fonctionnel
- [ ] Mobile : orbe + panneau utilisables
- [ ] Historique Workbench accessible
- [ ] Zero confusion Luna / Iris dans les labels
- [ ] Style premium applique (palette, typo, animations)

### Interdit V1
- [ ] Pas d'envoi automatique sans confirmation
- [ ] Pas de panneau vide ou sans contenu
- [ ] Pas de melange Luna/Iris dans le meme espace
- [ ] Pas de dependance video/avatar

---

## 8. Phasage et dependances

| Phase | Quoi | Qui | Validation |
|---|---|---|---|
| 1 | Stabiliser /ws/iris-voice (audio) | Claude | Codex capture |
| 2 | Orbe Iris + statuts visuels | Claude | Kimi |
| 3 | Workbench Panel V1 (HTML/CSS/JS) | Claude | Kimi + Ludovic |
| 4 | Connexion backend (brouillon, sauvegarde) | Claude + DeepSeek | Codex |
| 5 | Historique Workbench | Claude | Kimi |

---

*Reference : OBJECTIF_019_LUNA_IRIS_ACTION_PANEL.md, IRIS_CAHIER_DES_CHARGES_AUDIO.md*
