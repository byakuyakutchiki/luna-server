# Decisions validees

Historique court des decisions fondateur ou decisions de coordination deja actees.

---

## 2026-05-28 - Objectif 012 - Canal GitHub V1

Decision : utiliser GitHub comme salle de decision gratuite entre agents pour la V1.
Valide par : Ludovic
Portee : documentation, coordination, audit, propositions, risques, decisions a preparer.
Limite : aucun endpoint serveur, aucun cout supplementaire, aucun deploiement production.
Garde-fou : tout changement majeur reste soumis a validation Ludovic.

## 2026-05-28 - Protection UI Luna

Decision : Luna doit toujours aller vers plus beau, plus fluide et plus fonctionnel.
Valide par : Ludovic
Portee : tous les agents.
Garde-fou : ne pas refaire le graphisme valide sans raison produit claire ; toute regression graphique doit etre signalee.

## 2026-06-03 - Kimi agent de deploiement operationnel

Decision : Kimi peut deployer Cloud Run pour permettre a Ludovic de tester et travailler depuis son telephone.
Valide par : Ludovic
Portee : deploiements Cloud Run sur `luna-beta`, apres commit/push GitHub et checks minimaux.
Conditions obligatoires :
- deployer seulement un commit present sur `origin/main` ;
- lire `TARGET_REGISTER.md` et verifier que la target est claire ;
- verifier que le patch ne lance aucun SMS, appel, email, paiement, reservation, suppression ou secret ;
- annoncer dans `AGENT_CHANNEL.md` le commit deploye, la revision Cloud Run, le test attendu et le rollback possible ;
- garder les sessions de test payantes courtes ;
- si regression visible ou fonctionnelle, stopper et documenter immediatement.
Limites :
- APK, secrets, base de donnees, Twilio reel, SMS/email/appel reel, paiement et suppression restent niveau 3 et demandent validation explicite Ludovic juste avant action.
