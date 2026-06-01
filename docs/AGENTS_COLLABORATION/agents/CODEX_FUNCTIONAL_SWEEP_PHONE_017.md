# Codex — Sweep fonctionnel telephone reel — Objectif 017

Agent : Codex  
Objectif : 017  
Date : 2026-06-01  
Type : audit terrain

## Preuves

Dossier :

```text
docs/AGENTS_COLLABORATION/phone_tests/codex-functional-sweep-20260601-202016/
```

Fichiers principaux :

- `00-start.png`
- `01-chat-secretary.png`
- `02-services-secretary.png`
- `03-contacts-secretary.png`
- `04-instructions-secretary.png`
- `05-lasttab-secretary.png`
- `06-visio-10s.png`
- `07-visio-joined-20s.png`
- `08-visio-after-hangup.png`
- logs/focus associes

## Constats onglets

### Chat / Secretaire

- Luna s'ouvre bien en mode Secretaire.
- Palette verte coherente.
- `LUNA` vertical corrige.
- Anciennes bulles `Visio lancee (3 min prevues)` toujours presentes car deja sauvegardees avant le patch.
- Le haut de la grande bulle est partiellement masque par la barre d'onglets : risque lisibilite mobile.

### Services

- Onglet accessible.
- Cartes Recherche/Voyage, Temps reel, Communication visibles.
- Les boutons sensibles `Envoyer un SMS`, `Envoyer un email`, `Appeler`, `Visio Luna`, `Alerte urgence` sont visibles.
- Aucun bouton sensible n'a ete declenche pendant le sweep onglets final.

### Contacts

- Contacts de confiance visibles.
- Boutons `Inviter` et `Supprimer` sont tres visibles.
- Risque UX : `Supprimer` rouge est proche de `Inviter`, action destructive potentielle ; verifier confirmation obligatoire avant suppression.
- Les numeros sont visibles dans la capture : attention aux partages publics.

### Instructions

- Onglet accessible.
- Avertissement medical visible et clair.
- Les chips de modeles rapides sont lisibles.
- Le textarea `Nouvelle instruction` est partiellement recouvert par le panneau `Planification` en bas : a surveiller sur mobile.

### Documents

- Onglet accessible.
- Etats `Total`, `En attente`, `En retard`, `Regle` visibles.
- Bouton `Scanner` visible.
- RAS majeur visuel sur la capture initiale.

## Visio — test court

### Precheck

Capture `06-visio-10s.png` :

- Microphone : coche verte.
- Camera : coche verte.
- Bouton `Commencer la visio` disponible.

Conclusion : permissions micro/camera sont valides avant entree visio.

### Session joined

Capture `07-visio-joined-20s.png` :

- Avatar visio affiche.
- Indication `Luna active`.
- Indication `Luna voit`.
- Miniature camera utilisateur visible en haut.
- Barre Daily visible en bas.
- Bouton `Raccrocher` visible.

Conclusion : la session visio se lance reellement et le statut UI annonce que la vision est active.

### Raccrochage

Capture `08-visio-after-hangup.png` :

- retour a Luna OK.
- session courte terminee.

## Gap important logs

Logcat Android ne remonte pas les marqueurs JS attendus :

```text
speech_start
speech_end
stt_done
llm_start
llm_done
tts_start
tts_done
audio_play_start
audio_play_end
total_latency_ms
```

Probable raison : ces marqueurs sont actuellement emis dans la console JavaScript WebView, pas dans logcat Android.

Codex a verifie que DevTools WebView existe :

```text
webview_devtools_remote_3629
```

Forward local teste :

```text
adb forward tcp:9222 localabstract:webview_devtools_remote_3629
```

Mais apres raccrochage, la cible exposee etait `about:blank`. Prochain test visio : attacher DevTools pendant la session pour capturer la console JS en direct.

## Risques / anomalies

1. **Visio annonce `Luna voit`, mais on n'a pas encore la preuve textuelle de ce qu'elle voit.**
   - Il faut tester le bouton `Analyser` ou une phrase utilisateur du type "Est-ce que tu me vois ?" avec logs JS.

2. **STT/reponse non prouvee dans ce test.**
   - Aucun marqueur `speech_start` ou `total_latency_ms` dans logcat.
   - Besoin DevTools ou instrumentation qui bridge `rLog()` vers Android logcat.

3. **UI Daily non brandee Luna.**
   - Le label `Chatbot` et controles Daily generiques sont visibles.
   - A evaluer par Kimi avant exploitation premium.

4. **Contacts : action destructive proche.**
   - `Supprimer` doit avoir une confirmation forte.

5. **Instructions : panneau bas possiblement trop envahissant.**
   - Le champ est partiellement cache en mobile.

## Recommandations

### P0

- Ajouter un pont de logs visio WebView vers Android/logcat ou endpoint serveur debug non sensible, pour que Codex puisse capturer automatiquement les marqueurs.

### P1

- Tester `Analyser` dans la visio avec une capture et une reponse attendue, session tres courte.
- Verifier que `Supprimer` contact affiche confirmation.
- Verifier que le message `Visio lancee` n'est plus ajoute sur nouvelle session.

### P2

- Auditer le branding visio : `Chatbot`, controles Daily, avatar generique.
- Corriger l'overlap du haut de bulle Chat sous la barre d'onglets.
- Corriger l'espace Instructions si le panneau bas gene la saisie.

