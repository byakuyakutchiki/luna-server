# Objectif 017 — Banc de test reel telephone Luna

Date : 2026-06-01  
Statut : ouvert  
Priorite : haute, mais non destructive

## But

Utiliser le telephone Android de Ludovic en mode developpeur comme banc de test reel Luna, pour eviter que les agents travaillent uniquement depuis le code ou l'imagination.

Le but n'est pas d'ajouter du bruit. Le but est d'aller plus vite :

- voir l'application reelle ;
- tester bouton par bouton ;
- capturer les logs utiles ;
- proposer des corrections ciblees ;
- ne pas casser le code existant ;
- ne pas consommer inutilement les credits Twilio, Simli, ElevenLabs ou OpenAI.

## Principe de controle

Un seul agent pilote le telephone a la fois.

Les autres agents ne pilotent pas directement. Ils lisent :

- captures ecran ;
- logs Android/logcat ;
- logs navigateur/F12 si disponibles ;
- rapports courts publies sur GitHub.

## Roles

### Codex

- coordonne le banc de test ;
- definit la target avant chaque test ;
- capture ou demande les preuves minimales ;
- met a jour GitHub ;
- bloque les tests inutiles ou trop couteux.

### Claude

- code les correctifs apres preuve ;
- peut deployer uniquement apres feu vert Ludovic ;
- ne doit pas inventer l'UX sans preuve terrain.

### Kimi

- regarde les captures et le rendu reel ;
- juge la qualite visuelle, la fluidite, la coherence Luna ;
- signale toute regression graphique.

### DeepSeek

- audite les logs et les causes techniques ;
- verifie les risques : permissions Android, WebView, ADB, micro/camera, auth, couts, crashs ;
- propose des patchs minimaux.

## Regles de test

Avant chaque test, ecrire :

```text
Bouton / fonction :
Objectif utilisateur :
Etat attendu :
Preuve attendue :
Risque cout :
Action sensible : oui/non
```

Interdits sans validation Ludovic :

- SMS Twilio ;
- appel reel ;
- email reel ;
- paiement ;
- reservation ;
- suppression de donnees ;
- deploiement Cloud Run ;
- test long Simli/ElevenLabs.

## Preuves minimales

Pour chaque test reel :

- capture ecran avant/apres ;
- logs utiles uniquement, pas de dump enorme ;
- verdict : OK / KO / partiel ;
- fichier ou bouton concerne ;
- prochaine action proposee.

## Outillage Windows

Script prevu :

```powershell
.\tools\agents\phone_snapshot.ps1
```

Ce script doit rester non destructif :

- verifier `adb devices` ;
- capturer un screenshot ;
- capturer un court logcat ;
- ne pas cliquer ;
- ne pas taper ;
- ne pas lancer d'action sensible.

## Condition technique

Actuellement, dans la session Windows Codex, `adb` n'est pas disponible dans le PATH.

Action requise avant usage :

- installer Android Platform Tools, ou
- ajouter le dossier contenant `adb.exe` au PATH Windows, ou
- lancer les tests depuis la machine/session ou ADB fonctionne deja.

## Definition de succes

Le banc de test est valide quand :

- `adb devices` voit le telephone en `device` ;
- une capture ecran est produite ;
- un logcat court est produit ;
- les fichiers sont ranges dans `docs/AGENTS_COLLABORATION/phone_tests/` ou autre dossier dedie ;
- les agents peuvent commenter les preuves sur GitHub.

