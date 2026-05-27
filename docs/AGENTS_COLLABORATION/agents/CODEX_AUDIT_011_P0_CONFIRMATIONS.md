# Codex audit 011 - Confirmations P0 Appeler / Visio

Agent : Codex
Objectif : 011
Type : risque
Resume : Les confirmations existent deja via `_showConfirm()` pour SMS, email, SOS, reservations et suppressions. Les chemins Appeler/Visio contournent ce garde-fou sur certains boutons. Patch recommande : envelopper `_confirmCallContact()` et `startCall()` / `_concStartVisio()` dans `_showConfirm()` avant action.
Fichier concerne : `static/index.html`
Risque : moyen si non corrige, car appel vocal ou visio peuvent partir apres selection/duree sans dernier recapitulatif clair.
Decision Ludovic requise : non pour audit ; oui avant deploiement.
Action proposee : Kimi teste l'UX reelle, puis applique un patch minimal niveau 1 si valide.

## Points code

- `static/index.html:3427` : `_concStartVisio()` appelle directement `startCall()`.
- `static/index.html:4616` : `startCall()` ouvre seulement le choix de duree puis navigue vers `/simli`.
- `static/index.html:4703` : `_confirmCallContact()` ferme la modale et appelle `startVoiceCall(...)` sans confirmation finale recapitulant contact + duree.
- `static/index.html:4722` : le bouton `callBtn` appelle directement `startCall()`.
- `static/index.html:3949` : `_showConfirm()` existe deja et peut etre reutilise sans nouvelle UI.

## Patch minimal recommande

1. Appel vocal contact : dans `_confirmCallContact()`, afficher `_showConfirm("Lancer cet appel ?", "...", function(){ startVoiceCall(...) }, true/false)` avant l'appel.
2. Visio Luna : dans `_concStartVisio()` et le listener `callBtn`, afficher `_showConfirm("Lancer la visio Luna ?", "La session va ouvrir la camera/le micro selon autorisations.", startCall)`.
3. Auto-start `?video=1` : laisser tel quel ou le traiter separement, car il vient d'une intention explicite URL.

## Garde-fous

- Aucun appel reel execute pendant cet audit.
- Aucun endpoint appele.
- Aucun deploiement.
- Aucun changement graphique propose hors modale existante.
