# Registre Target — Suivi fonctionnel

Ce fichier sert a suivre les targets actives. Il doit etre mis a jour quand une fonctionnalite importante est ouverte, codee, testee ou livree.

---

## Objectif 021 — Iris Capability Gateway

| Fonctionnalite | Target exacte | Statut | Preuve attendue | Agent lead |
|---|---|---|---|---|
| Recherche externe Iris | Iris cherche dehors, affiche sources + synthese exploitable dans Command Screen | code non prouve | test "cherche Base Legacy" avec sources visibles | DeepSeek + Claude |
| Porte-documents Iris | Iris retrouve, analyse et compare des documents internes avec consentement | non code / a verifier | test upload + recherche + document_insight | DeepSeek + Claude |
| Action Twilio | Iris prepare appel/SMS, affiche action_board, execute seulement apres validation owner | non code / a verifier | test action_board sans appel reel | Claude + Codex |
| Map / Monde | Iris affiche lieu/itineraire/contexte dans map_board sans fuite position | non code / a verifier | test "montre ce lieu" | Kimi + Claude |
| Teams interne | Iris affiche participants, roles, mute/kick, validation actions invite | partiel / a prouver | session avec owner + invite | Claude + Kimi |
| Command Screen visuel | Iris projette tableaux, graphiques, documents, decisions, statuts, pas du texte brut | partiel | capture rendu visuel + logs render_type | Kimi + Codex |
| Feedback préparation Iris | Quand Iris dit qu'elle prépare/crée/rédige, un état de travail visible s'affiche, le transcript reste discret, puis timeout clair à 10s si rien ne revient | code non prouvé | capture "Iris prépare" puis rendu ou "Préparation trop longue" ; vérifier absence de pavé texte | Codex |

### Mise à jour DeepSeek/Codex — 2026-06-02

| Capacité | Statut DeepSeek | Arbitrage Codex |
|---|---|---|
| Recherche web | non code / à vérifier | Vérifier d'abord les tools existants `search_web`, puis brancher rendu `research_board` |
| Porte-documents | partiel | Brancher vault/documents au Command Screen |
| Upload / Analyse | partiel | Brancher `document_insight`, vérifier type/taille/consentement |
| Carte / Map | non code | Créer `map_board` avec consentement avant géoloc |
| SMS | code non prouvé | P0 = `action_board` sans SMS réel, pas activation directe |
| Appel | non code | P1 = `action_board` sans appel réel tant que non prouvé |
| Email | non code | P1 = brouillon + validation, pas envoi réel |
| Teams | atteint selon DeepSeek | À prouver terrain : participants, roles, mute/kick, pending action |
| Rendu visuel | partiel | Prouver intégration WS + `render_type` |
| Garde-fous | partiel | Quota, consentement géoloc, filtres docs à vérifier |

---

## Objectif 019 — Iris Command Screen

| Fonctionnalite | Target exacte | Statut | Preuve attendue | Agent lead |
|---|---|---|---|---|
| Tableau visuel | Tableau HTML premium exploitable, pas markdown, pas texte imaginaire | partiel | capture table + contenu structure | Kimi |
| Graphique | Graphique lisible et utile quand chiffres/tendances | partiel | capture chart + donnees | Kimi + DeepSeek |
| Document Draft | Brouillon type document, editable, copiable/telechargeable | partiel | test courrier exploitant | Claude |
| Action Board | Validation claire avant action sensible | partiel | test "envoie SMS" sans SMS reel | DeepSeek |

---

## Objectif 020 — Iris Teams

| Fonctionnalite | Target exacte | Statut | Preuve attendue | Agent lead |
|---|---|---|---|---|
| Invitation | Owner genere lien invite court et scope | code non prouve | test lien /join | Claude |
| Participants | Liste visible style Teams/Zoom | non code / a verifier | capture overlay | Kimi |
| Mute/Kick | Owner peut muter/exclure un invite | non prouve | test non destructif | Claude + DeepSeek |
| Actions invite | Invite ne peut pas declencher action sensible sans validation owner | a prouver | pending action board | DeepSeek |
