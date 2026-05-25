# Note validation Ludovic — Objectif 007

**Date** : 2026-05-25  
**Auteur** : Codex  

## Règle

Claude est l'intégrateur final de l'objectif 007 : il peut coder, corriger et
déployer lorsque Ludovic l'autorise.

Mais Claude ne valide pas seul l'objectif 007.

La validation fonctionnelle appartient à Ludovic, car l'objectif porte sur
l'expérience réelle de l'APK sur son téléphone.

## État actuel

Selon `CLAUDE_AVIS_007.md` :

- commit implémentation : `01ac7a5`
- révision Cloud Run : `luna-beta-00439-7v9`
- simulation serveur : positive

Cette simulation confirme le regroupement technique des événements, mais elle ne
remplace pas le test réel sur APK.

## Test réel attendu

1. Ludovic ouvre Luna sur le téléphone.
2. Il appuie une seule fois sur le bouton vocal.
3. Il attend 20 secondes.
4. Il recharge `fondateur.html`.
5. Il copie la section `Voix APK`.

## Condition de validation

L'objectif 007 est validé uniquement si le cockpit affiche :

- plus que `voice_session_ended` ;
- une chronologie de plusieurs étapes ;
- ou un point d'arrêt explicite expliquant où le flux vocal bloque.

Tant que ce test n'est pas fait, l'objectif 007 reste **déployé mais non validé**.
