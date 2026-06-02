# DeepSeek — Direction artistique Iris Command Screen — Objectif 019

Date : 2026-06-02  
Agent : DeepSeek  
Type : direction artistique / proposition technique  
Niveau : 0  

## Résumé agent

Agent : DeepSeek  
Objectif : 019  
Type : TASK-019-DEEPSEEK-ARCHI-IRIS-COMMAND-SCREEN  
Résumé : Architecture intention -> rendu spécifiée. 6 types de rendu : Data Board, Document Draft, Action Board, Context Panel, Missing Info Panel, Status Rail. Règle absolue : Iris ne dit jamais "je ne peux pas afficher". Le backend doit toujours renvoyer un type structuré. Garde-fous : aucune action sans confirmation, aucune donnée modifiée sans utilisateur. Contrat backend -> frontend défini.  
Fichier concerné : `workbench.html` -> `iris-command-screen.html`, `luna_web.py` WebSocket  
Risque : si le backend continue de renvoyer du texte brut, l'expérience reste cassée.  
Décision Ludovic requise : oui — valider les 6 types de rendu.  
Action proposée :

1. Claude implémente le contrat backend avec 6 types JSON.
2. Kimi conçoit l'UX premium du Command Screen avec les 6 panneaux.
3. Codex vérifie que chaque intention produit le bon type de rendu.

---

## Cap fondateur

Ludovic veut que Luna / Iris devienne la meilleure application au monde visuellement, une expérience qui épate.

On ne vise pas seulement "joli". On vise iconique.

Référence d'ambition :

- Jarvis : données qui s'affichent dans l'espace, verre, holographique.
- Westworld : tablettes de contrôle, typographie pure, gestes.
- Minority Report : manipulation visuelle de données.
- Her : interface discrète, centrée sur l'humain et la voix.
- Tesla UI : minimalisme extrême, fluidité.
- Vision Pro : verre, profondeur, spatialité.

## Concept

Iris ne "s'affiche" pas. Iris s'allume.

L'écran n'est pas une page web. C'est une surface noire profonde. Quand Iris travaille, des panneaux de verre émergent, s'assemblent, présentent l'information, puis peuvent disparaître.

Rien n'est statique. Tout doit sembler vivant, utile et maîtrisé.

## Spécification visuelle proposée

### 1. Fond

- Noir OLED pur.
- Pas de bruit visuel inutile.
- Vide assumé comme espace de luxe.
- Marges généreuses.

### 2. Verre

- Panneaux en verre fumé.
- `backdrop-filter: blur(40px) saturate(180%)`.
- Bordures très fines.
- Lueur subtile seulement quand Iris parle ou travaille.
- Pas d'ombres portées classiques.

### 3. Lumière

- Iris écoute : halo violet doux.
- Iris réfléchit : lignes de données discrètes.
- Iris parle : bordures des panneaux légèrement éclairées.
- Transitions en fondus, jamais de coupure brutale.

### 4. Typographie

- Inter ou SF Pro Display.
- Corps léger, titres medium.
- Texte court, dense, lisible.
- Pas de phrases longues dans les composants visuels.

### 5. Couleur

Une seule couleur d'accent à la fois :

- violet Iris : état actif / confirmation ;
- cyan : données / lecture ;
- ambre : attention / action requise ;
- corail : erreur / annulation.

Règle : si plusieurs couleurs se battent, l'interface redevient ordinaire.

### 6. Mouvement

- Les panneaux émergent par fondu, léger scale et léger translate.
- Durée cible : 300 à 600 ms.
- Aucun élément ne bouge sans raison.
- Les données arrivent avec animation décalée courte.

## Variables CSS proposées

```css
:root {
  --void: #000000;
  --glass-bg: rgba(10, 10, 15, 0.75);
  --glass-border: rgba(255, 255, 255, 0.05);
  --glass-hover: rgba(15, 15, 22, 0.85);
  --glass-blur: 40px;
  --glass-saturate: 180%;

  --iris-violet: #8B74F7;
  --iris-violet-glow: rgba(139, 116, 247, 0.3);
  --data-cyan: #40E0FF;
  --data-cyan-glow: rgba(64, 224, 255, 0.25);
  --alert-amber: #FFB74D;
  --alert-amber-glow: rgba(255, 183, 77, 0.25);
  --error-coral: #FF6B7B;
  --error-coral-glow: rgba(255, 107, 123, 0.25);

  --text-primary: rgba(255, 255, 255, 0.9);
  --text-secondary: rgba(255, 255, 255, 0.55);
  --text-tertiary: rgba(255, 255, 255, 0.3);

  --font: 'Inter', -apple-system, BlinkMacSystemFont, 'SF Pro Display', sans-serif;
  --text-micro: 11px;
  --text-body: 15px;
  --text-title: 20px;
  --text-hero: 32px;
  --text-line-height: 1.6;
  --text-weight-light: 300;
  --text-weight-regular: 400;
  --text-weight-medium: 500;

  --ease-spring: cubic-bezier(0.22, 0.61, 0.36, 1);
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --duration-fast: 300ms;
  --duration-normal: 600ms;
  --duration-slow: 1000ms;

  --space-xs: 8px;
  --space-sm: 16px;
  --space-md: 24px;
  --space-lg: 40px;
  --space-xl: 64px;

  --radius-panel: 24px;
  --radius-button: 100px;
  --radius-orb: 50%;
}
```

## Interdits

- Émojis dans l'interface Command Screen.
- Ombres portées classiques.
- Bordures épaisses.
- Coins carrés.
- Plus de deux polices.
- Plus d'une couleur d'accent simultanée.
- Animations gratuites.
- Textes qui dépassent sans résumé.
- Écrans vides sans feedback.
- Messages d'erreur techniques visibles.
- Phrase "je ne peux pas afficher".

## Obligatoire

- Noir profond.
- Verre avec blur réel si performance acceptable.
- Une seule couleur d'accent à la fois.
- Chaque élément important a une animation d'entrée.
- Statut toujours visible.
- Transitions douces.
- Texte court, élégant, utile.
- L'espace vide est assumé.
- L'interface disparaît ou se calme quand Iris ne travaille pas.

## Position Codex

Cette proposition est acceptée comme base de discussion, pas comme validation finale.

Kimi doit challenger et transformer cette direction en UX concrète mobile/desktop.
DeepSeek doit compléter avec un contrat technique `intent -> render_type -> payload`.
Claude ne doit pas coder avant scope Codex/Ludovic, sauf patch documentaire ou prototype explicitement demandé.
