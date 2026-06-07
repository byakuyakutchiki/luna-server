# Claude — Implémentation Team Workspace — Objectif 035

Date : 2026-06-07
Agent : Claude
Type : implementation V1
Statut : code livré, PAS déployé (validation Ludovic requise)

## Fichiers créés / modifiés

- `static/team_workspace.html` — page complète (nouvelle)
- `luna_web.py` — route `GET /team` ajoutée (après `/simli`, avant `/guardian`)

## Ce qui est implémenté

### Layout immersif

Fond dark (#050510) + gradients cyan/violet aux coins + grille holographique subtile.
3 zones verticales : header / arena / bottom strip.

### Arena — table + tableau

Tableau central (400×265px) :
- Grille holographique de fond
- Rail header avec boutons "+ Idée" et "+ Source"
- SVG mind map : 5 noeuds reliés par des liens pointillés
- Cadenas visuel "IRIS ANALYSE" quand le mode Iris est actif

Sièges participants (6 positions fixes autour du tableau) :
- Positionnement CSS absolu simulant une table ronde
- Lignes de connexion SVG (dashed) de chaque siège vers le tableau
- Statuts visuels : speaking (anneau cyan pulsant), editing (bordure amber), absent (opacité réduite)
- Icônes micro/caméra on/off, main levée animée
- Badge rôle : 👑 Owner (gold) / Participant (cyan)
- Hover admin : boutons Muter / Retirer / Bannir (UI only, aucune action réelle)

### Spectateurs (bottom left)

- Liste des spectateurs avec avatar initiales
- Badge "raised" si main levée
- Bouton "↑ Siège" pour promouvoir en participant (UI only)

### Admin panel (bottom right — 3 zones)

1. **Brief Mission** — résumé du brief actif ou message d'invite
2. **Sources** — liste des sources ajoutées (5 max visibles)
3. **Panneau Iris** — icône 🔮, statut EN ATTENTE / PRÊTE, bouton "Avis Iris"

### Brief Modal

Champs : titre, domaine, objectif, contexte, toggle recherche externe.
Le brief appliqué active le bouton Brief dans le header (violet allumé).

### Bouton Avis Iris conditionnel

Désactivé tant que `briefReady && sourcesReady` ne sont pas tous deux vrais.
Messages d'aide : "Brief + source requis", "Brief requis", "Source requise".

### Mode Iris Opinion

- Overlay sombre (backdrop-filter)
- Panneau synthèse avec vague animée (5 barres)
- Contenu : Mission, Domaine, Sources listées
- Tableau central verrouillé visuellement (cadenas + blur)
- Sièges participants à 38% d'opacité ("en écoute")

### Mind map SVG

4 types de noeuds :
- 💡 Idée (cyan)
- 📄 Source (amber)
- ✅ Décision (vert)
- ◈ Synthèse (violet, plus grand)

Liens : lignes pointillées cyan entre les noeuds.
Clic sur un noeud → toast avec label + type.
Ajout dynamique via modale "+ Idée" ou prompt "+ Source".

## Logs F12 produits

```
[TW] team_workspace_loaded
[TW] seat_assigned Ludovic owner
[TW] seat_assigned Alice M. participant
[TW] seat_assigned Thomas R. participant
[TW] seat_assigned Sarah K. participant
[TW] spectator_joined count=2
[TW] iris_opinion_locked true | brief_ready false | sources_ready false
[TW] brief_ready true              (après applyBrief())
[TW] iris_opinion_locked false | brief_ready true | sources_ready true
[TW] iris_opinion_requested true   (après clic Avis Iris)
```

## Target Cells validées

| TC | Statut |
|---|---|
| TC-035-01 Workspace chargé | ✅ |
| TC-035-02 Brief incomplet → Iris grisé | ✅ |
| TC-035-03 Brief + source → Iris actif | ✅ |
| TC-035-04 Spectateur demande parole (état raised) | ✅ |
| TC-035-05 Admin mute/retire/bannit (UI only) | ✅ |
| TC-035-06 Mind map : 3+ idées, 2+ liens, 1 source | ✅ (5 noeuds, 5 liens) |
| TC-035-07 Avis Iris → overlay + tableau verrouillé + synthèse | ✅ |

## Interdictions respectées

- Aucun SMS / email / appel / paiement
- Aucun secret côté frontend
- Aucune suppression irréversible
- Aucun déploiement (non déployé)

## Pour tester en local (sans déployer Cloud Run)

```bash
cd ~/PROJETS/IA_WATCH/PROPRIO/serveur
python3 -m py_compile luna_web.py && echo OK
# Puis lancer le serveur local et ouvrir https://localhost:8888/team
```

## Ce qui reste pour V2

- Connexion WebSocket temps réel multi-participants
- Vrai drag & drop des noeuds SVG
- Export PDF/PNG du tableau
- Intégration avec le Mission Brief de simli.html (partage brief via WS)
- Connexion au bridge vocal pour que Iris parle le résultat de l'analyse
