# Claude — Compréhension vision Iris / Objectif 014

Agent : Claude  
Date : 2026-05-30  
Type : vision + déploiement P0

---

## Ce que j'ai compris : Iris n'est pas un chat vidéo

Iris est une **présence assistante**. Sa valeur n'est pas dans l'interface — elle est dans la capacité à comprendre pourquoi elle est là, qui elle accompagne, et ce qu'elle a le droit de faire.

---

## Les 16 options / targets compris

| # | Target | Ce qu'Iris doit faire | Niveau |
|---|---|---|---|
| 1 | **Présence crédible** | Féminine, calme, professionnelle. L'utilisateur sent une aide, pas un gadget. | 2 |
| 2 | **Identité** | Dire "Ludovic" naturellement si le profil le permet. Pas générique. | 1 |
| 3 | **Compréhension vocale** | Comprendre une phrase simple dite au micro. Le texte = secours discret seulement. | 1 |
| 4 | **Vision caméra** | Voir présence, main levée, document, situation inquiétante. Ne pas inventer. | 2 |
| 5 | **Contexte implicite** | Détecter le cadre : personnel / pro / démo / fragile / invité / admin / urgence. | 2 |
| 6 | **Adaptation** | En pro → notes + résumé. Personnelle → naturelle. Fragile → ralentit et rassure. Urgence → calme, aucune promesse. | 2 |
| 7 | **Prise de notes** | Capter les points clés sans que Ludovic répète. Mode pro = note implicite ou discrète. | 1 |
| 8 | **Résumé final** | Sur demande ou à la fin : ce qui s'est dit, décisions, actions, rappels. | 1 |
| 9 | **Actions à suivre** | Extraire rappels, tâches, échéances, recherches — sans action sensible automatique. | 1 |
| 10 | **Recherche simple** | Météo, info, service proche — outil ou honnêteté si elle ne sait pas. | 1 |
| 11 | **Document montré / uploadé** | Lire, résumer, repérer une date, proposer une action. Pas inventer. | 1/2 |
| 12 | **Canal texte secours** | Si micro échoue : bouton discret, tiroir temporaire. Pas de barre permanente. | 2 |
| 13 | **Actions sensibles protégées** | SMS/appel/email/réservation/paiement/alerte : jamais automatique. Validation Ludovic niveau 3. | 3 |
| 14 | **Économie crédits** | Tests courts, pas de boucle, pas de session longue. Simli/ElevenLabs/Twilio protégés. | 1 |
| 15 | **Qualité visuelle** | Contrôles discrets, vidéo qui respire. Kimi valide. Rien qui couvre inutilement. | 2 |
| 16 | **Preuve terrain** | Une feature n'est validée que si : test réel + résultat + risque connu. Pas "ça existe dans le code". | tous |

---

## Ma règle avant tout nouveau code

Avant de coder, je dois répondre :
1. Quelle est la cible humaine ?
2. Dans quel contexte de visio ?
3. Quelle option Iris active ?
4. Quelle preuve terrain montre que ça marche ?
5. Est-ce sensible ou payant ?
6. Qui valide ?

Si ces réponses ne sont pas claires → je ne code pas.

---

## Déploiement P0 effectué — 2026-05-30

**Action** : Déploiement Cloud Run révision `luna-beta-00462-q7n`  
**Variables ajoutées** : `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID=6BlZrFdruL4hpXFHmHUC` (Alice, FR)  
**Code inclus** : barre texte Iris retirée, fallback SMS coupé, nom Iris dans system prompt  
**Smoke tests** : aucun SMS, appel, email, paiement, réservation, session Simli longue  

**Ce qui reste à prouver terrain** :
- La voix Alice est-elle maintenant entendue en prod ? → Test Ludovic < 30s
- Iris dit-elle "Ludovic" ? → Vérifier profil DB
- La vision caméra répond-elle à "tu me vois ?" ? → Test Ludovic

**Prochaine action** : Ludovic teste la voix en visio (< 30s, micro ouvert, dire une phrase simple).
