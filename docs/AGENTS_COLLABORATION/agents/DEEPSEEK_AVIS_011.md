# DeepSeek avis 011 - Audit code Appeler / Visio

Agent : DeepSeek
Objectif : 011 - Services / Conciergerie
Type : risque
Resume : Appeler et Visio contournent `_showConfirm()`, ce qui expose a des declenchements non confirmes. `startCall()` et `_concStartVisio()` lancent le flux visio sans garde-fou final. `_confirmCallContact()` ferme la modale avant `startVoiceCall()`, ce qui peut interrompre le contexte utilisateur.
Fichier concerne : `static/index.html:3427`, `static/index.html:4616`, `static/index.html:4630`, `static/index.html:4703`, `static/index.html:4722`
Risque : declenchement intempestif d'appel/visio sans confirmation utilisateur, perte de contexte modal.
Decision Ludovic requise : oui avant deploiement ; non pour audit et patch local faible risque.
Action proposee : reutiliser `_showConfirm()` avant `startCall()` et avant `startVoiceCall()`.

## Points techniques DeepSeek

- Handler `_concStartVisio()` : wrapper `_showConfirm()` avant `startCall()`.
- Handler `callBtn` : wrapper `_showConfirm()` avant `startCall()`.
- Handler `_confirmCallContact()` : garder les infos contact/duree, demander confirmation, puis fermer la modale et lancer `startVoiceCall()`.
- Patch minimal : reutiliser la modale existante, sans nouvelle UI et sans endpoint nouveau.
- Test non destructif : verifier que la modale de confirmation s'affiche avant chaque appel/visio, sans declencher appel reel.

## Convergence avec Codex

DeepSeek confirme l'audit Codex : la correction P0 recommandee est chirurgicale et doit se limiter aux confirmations finales Appeler / Visio.
