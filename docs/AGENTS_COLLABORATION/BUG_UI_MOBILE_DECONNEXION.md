# Bug UI Mobile — Bouton "Déconnexion" coupé

**Date** : 2026-05-25  
**Signalé par** : Ludovic (test téléphone, post-déploiement 00440-gbz)  
**Statut** : tracé — à corriger en branche isolée  
**Priorité** : secondaire (ne bloque pas la voix)  

---

## Symptôme

Sur téléphone, le bouton "Déconnexion" n'est plus entièrement lisible.
Le "n" final est mangé / coupé sur le bord droit de l'écran.

---

## Zones à vérifier

- `static/fondateur.html` — bouton Déconnexion : width, padding, overflow
- `static/index.html` — si le bouton existe aussi dans l'interface client
- Conteneur parent : flex, grid, max-width
- Media query mobile manquante ou changée
- `font-size` trop grande sur petit écran
- `white-space: nowrap` sans `overflow: hidden + text-overflow: ellipsis`
- Changement CSS récent depuis le dernier déploiement fonctionnel

---

## À faire

- [ ] Identifier le commit qui a introduit le changement (git log fondateur.html)
- [ ] Reproduire sur DevTools en vue mobile (375px)
- [ ] Corriger dans une branche isolée (`claude/bug-ui-mobile-deconnexion`)
- [ ] Vérifier non-régression des autres boutons
- [ ] Valider Ludovic avant merge

---

## Règle

Ne pas corriger en même temps que l'objectif 008 serveur voix.
Les deux corrections doivent rester séparées pour ne pas mélanger les diagnostics.
