# Guardian — Politique de Comportement Officielle V2
**Référence : GUARDIAN_BEHAVIOR_POLICY_V2**
**Date : 15 juin 2026**
**Statut : DOCUMENT DE RÉFÉRENCE — remplace toute version antérieure**
**Audience : développeurs, auditeurs, partenaires exploitants**

---

## Préambule

Ce document définit le comportement officiel de Guardian.

Il ne contient aucune ligne de code. Il précède le code. Toute évolution du moteur Guardian doit être conforme à ce document, et tout écart entre ce document et le code constitue un bug comportemental à corriger.

### La question fondamentale

> Si Guardian surveille réellement un parent âgé pendant 365 jours, comment éviter qu'il devienne agaçant, ignoré, ou source de fausses alertes, tout en restant utile le jour où une vraie urgence survient ?

La réponse tient en une phrase :

**Guardian gagne la confiance dans ses silences. Il ne prend la parole que lorsque c'est vraiment nécessaire.**

### Principe cardinal

```
Guardian observe.
Guardian ne diagnostique pas.
Guardian vérifie avant d'alerter.
Guardian annule quand l'alerte était inutile.
```

L'ennemi numéro un de Guardian n'est pas le faux négatif (manquer une urgence). C'est le faux positif répété (signaler des urgences qui n'en sont pas), car les faux positifs tuent la confiance, et un Guardian dont on a coupé les notifications ne sert à rien le jour J.

---

## PARTIE 1 — CE QUE GUARDIAN PEUT OBSERVER

Guardian est un système d'observation passive. Il collecte des signaux. Il ne les interprète pas de façon médicale.

### 1.1 Signaux GPS

| Signal | Description | Valeur brute |
|---|---|---|
| Position | Latitude / longitude | Coordonnées WGS84 |
| Mouvement | Déplacement > seuil | distance > MOVE_THRESHOLD (10 m) |
| Immobilité | Absence de mouvement | durée en minutes |
| Vitesse | Vitesse calculée entre deux points | m/s |
| Zone | Dans / hors zone de confiance | booléen |
| Précision GPS | Qualité du signal GPS | mètres (±) |

### 1.2 Signaux Caméra

| Signal | Description |
|---|---|
| Personne visible | Une ou plusieurs personnes détectées dans le champ |
| Personne absente | Aucune personne détectée |
| Posture debout | Personne en position verticale |
| Posture assise | Personne en position assise |
| Posture allongée (lit) | Personne allongée sur une surface haute |
| Posture au sol | Personne allongée sur le sol (pas un lit) |
| Durée au sol | Temps écoulé depuis détection au sol |
| Durée d'absence | Temps écoulé depuis dernière personne visible |

### 1.3 Signaux Réseau et Système

| Signal | Description |
|---|---|
| Perte GPS | Satellite non disponible |
| Perte réseau | Connexion internet interrompue |
| Perte caméra | Flux caméra interrompu ou vide |
| Session active | Guardian en fonctionnement |
| Réponse utilisateur | L'utilisateur a répondu à une vérification |

---

## PARTIE 2 — CE QUE GUARDIAN NE DOIT JAMAIS CONCLURE

Guardian n'est pas un médecin. Il n'est pas un urgentiste. Il n'est pas un juge.

### 2.1 Diagnostics médicaux — jamais

Guardian ne doit jamais mentionner ni conclure :

- AVC
- Crise cardiaque
- Arrêt cardiaque
- Coma
- Décès
- Malaise vagal
- Hypoglycémie
- Crise d'épilepsie
- Chute (le mot "chute" est interdit dans les messages)
- Urgence médicale
- Problème de santé
- Danger immédiat pour la vie

### 2.2 Formulations interdites dans les messages Guardian

| Interdit | Remplacer par |
|---|---|
| "a chuté" | "est resté(e) au sol" |
| "ne répond plus" | "n'a pas encore répondu" |
| "semble inconscient(e)" | "nous n'avons pas pu le/la joindre" |
| "pourrait être en danger" | "nous aimerions confirmer qu'il/elle va bien" |
| "urgence médicale" | "situation qui mérite votre attention" |
| "appelle le SAMU" | "si vous ne parvenez pas à le joindre, vous pouvez appeler le 15 ou le 112" |

### 2.3 Ce que Guardian peut dire

Guardian observe des faits. Il communique des faits.

- ✅ "Luna n'a pas encore reçu de réponse depuis 10 minutes."
- ✅ "Luna détecte que [Prénom] est resté(e) au sol depuis 6 minutes."
- ✅ "Luna n'a pas de nouvelles de [Prénom] depuis ce matin."
- ✅ "Fausse alerte — [Prénom] a confirmé qu'il/elle allait bien à 14h32."

---

## PARTIE 3 — LES CINQ NIVEAUX DE RISQUE

### Niveau 0 — NORMAL

**Définition :** Tout va bien. Aucun signal anormal.

**Comportement :** Surveillance silencieuse. Aucune action.

**Message utilisateur :** Aucun.

**Action autorisée :** Journalisation locale uniquement.

---

### Niveau 1 — DOUTE

**Définition :** Un signal inhabituel est détecté, mais il a une explication bénigne probable.

**Déclencheurs typiques :**

- Immobilité GPS > seuil pendant 5 à 15 minutes
- Absence caméra < 30 minutes
- Perte GPS ou réseau temporaire (< 5 minutes)
- Caméra coupée
- Téléphone posé sur table (personne absente du champ)

**Comportement :** Observer. Attendre. Ne rien faire.

**Délai :** Guardian attend la fin de la fenêtre de tolérance (voir Partie 4) avant de passer au niveau supérieur.

**Message utilisateur :** Aucun.

**Action autorisée :** Journalisation locale. Aucun message. Aucun SMS.

**Résolution :** Si le signal disparaît → retour automatique au Niveau 0.

---

### Niveau 2 — VÉRIFICATION

**Définition :** Le signal persiste au-delà de la fenêtre de tolérance. Guardian cherche à confirmer que tout va bien auprès de l'utilisateur.

**Déclencheurs typiques :**

- Immobilité GPS > seuil principal du profil (sans mode nuit actif)
- Personne au sol depuis 2 minutes
- Absence caméra > 30 minutes en journée (profil senior)
- Sortie de zone pendant plus de 10 minutes (profil SENIOR)
- Perte GPS ou réseau > 10 minutes

**Comportement :** Envoyer un message doux de vérification à l'utilisateur via l'application.

**Délai d'attente réponse :** **10 minutes minimum** (pas 2 minutes).

**Message utilisateur :**
> "Luna vous demande : tout va bien ? Appuyez sur le bouton vert pour confirmer."

**Action autorisée :** Message in-app uniquement. Aucun SMS aux contacts.

**Résolution :**
- Réponse "Tout va bien" → retour Niveau 0 + grace period 2h
- Pas de réponse dans les 10 min → passage au Niveau 3

---

### Niveau 3 — SUSPICION FORTE

**Définition :** L'utilisateur n'a pas répondu à la vérification, ou deux signaux indépendants convergent.

**Déclencheurs :**

- Pas de réponse Niveau 2 dans les 10 min
- Deux signaux actifs simultanément (ex. immobility + absence caméra)
- Personne au sol depuis 5 minutes (seuil CONCERN)
- Sortie de zone nocturne (22h-6h) sans réponse

**Comportement :**

1. Deuxième tentative de vérification (message + son d'alerte sur l'appareil)
2. Attente 5 minutes supplémentaires

**Message utilisateur :**
> "Luna essaie de vous joindre. Appuyez sur le bouton vert si vous allez bien. Si vous avez besoin d'aide, restez où vous êtes."

**Action autorisée :** Deuxième message in-app + son d'alerte. Toujours aucun SMS aux contacts.

**Résolution :**
- Réponse → retour Niveau 0 + grace period 2h + SMS annulation si contacts déjà prévenus
- Pas de réponse dans les 5 min → passage au Niveau 4

---

### Niveau 4 — ALERTE

**Définition :** Guardian n'a pas pu confirmer que l'utilisateur va bien après deux tentatives. Les contacts d'urgence sont notifiés.

**Déclencheurs :**

- Niveau 3 sans réponse dans les 5 minutes
- Ou : signal critique immédiat (voir exceptions ci-dessous)

**Comportement :**

1. Envoi SMS aux contacts d'urgence
2. Journalisation horodatée de l'alerte

**Contenu SMS type :**
> "🔔 Luna Guardian — [Prénom] n'a pas répondu à nos vérifications depuis [durée].
> Dernière position connue : [lien Maps avec précision réduite ±100m]
> Luna n'a pas pu le/la joindre depuis [heure].
> Si vous souhaitez vérifier, vous pouvez l'appeler directement.
> Si vous ne parvenez pas à le joindre, vous pouvez appeler le 15 ou le 112.
> Répondez OUI si vous intervenez."

**Limites :**

- Maximum 3 alertes Niveau 4 par session de 24h
- Délai minimum entre deux alertes Niveau 4 : 30 minutes
- Si le plafond de 3 alertes est atteint : maintien en Niveau 3 sans nouveau SMS, attente de l'intervention humaine

**Action autorisée :** SMS aux contacts d'urgence. Notification in-app. Journalisation.

**Guardian ne peut jamais :**

- Appeler le 15 ou le 112 automatiquement
- Envoyer les forces de l'ordre
- Déclencher une alarme physique

---

### Exceptions — Passage direct au Niveau 4

Les situations suivantes permettent de passer au Niveau 4 **sans passer par les Niveaux 2 et 3**, mais uniquement après un délai de confirmation minimal de **2 minutes** :

| Situation | Délai avant Niveau 4 |
|---|---|
| Personne au sol depuis 10 minutes sans aucun mouvement | 2 min de confirmation |
| Sortie de zone nocturne (22h-6h) + immobilité > 20 min | 2 min de confirmation |

Ces exceptions restent soumises aux limites anti-spam (max 3 alertes/24h).

---

## PARTIE 4 — FENÊTRES DE TOLÉRANCE PAR PROFIL

Les fenêtres de tolérance définissent combien de temps Guardian observe avant de passer au Niveau 2. Elles doivent être calées sur les habitudes de vie réelles.

### 4.1 Mode Nuit (23h – 7h)

**Règle fondamentale :** Entre 23h et 7h, si l'utilisateur est dans sa zone de confiance (safe zone), les signaux d'immobilité sont **suspendus**. Dormir est normal.

Signaux suspendus la nuit (en safe zone) :
- `immobility`
- `prolonged_immobility`

Signaux maintenus la nuit :
- `geofence_exit` (sortir de sa zone à 2h du matin reste préoccupant)
- `night_anomaly` (hors zone + nuit)

**Conséquence directe** : Guardian ne dérangera jamais personne parce qu'elle dort dans son lit. Si le profil est "nuit calme + safe zone", Guardian reste en Niveau 0 jusqu'à 7h.

### 4.2 Tolérance par profil

| Profil | Immobilité Jour | Immobilité Nuit | Absence Caméra | Notes |
|---|---|---|---|---|
| SENIOR | 45 min | suspendu | 45 min | Tolérance augmentée vs actuel |
| DOG | 90 min | 120 min | N/A | Sieste chien = normale |
| BABY | 120 min | suspendu | N/A | Sieste bébé = normale |
| HOME | 240 min | 360 min | 120 min | Domicile vide = OK la nuit |

### 4.3 Grace Period

Après une réponse "Tout va bien" (Niveau 2 ou 3 résolu) :

- **Grace period de 2 heures** : Guardian ne peut pas passer au Niveau 2 pendant les 2 heures suivantes, même si les signaux persistent.
- Raison : L'utilisateur vient de confirmer qu'il allait bien. Guardian doit lui faire confiance.

---

## PARTIE 5 — LES 20 SCÉNARIOS OBLIGATOIRES

### Scénario 1 — Personne qui dort (nuit)

**Situation :** 22h30. Utilisateur couché dans son lit. Téléphone sur la table de nuit. GPS fixe.

**Ce que Guardian observe :** Immobilité GPS depuis 30 min. En safe zone. Heure : 22h30.

**Comportement attendu :** Mode nuit actif. Signal immobility suspendu. → **Niveau 0 NORMAL**

**Résultat :** Aucune alerte. Aucun message. Surveillance silencieuse jusqu'à 7h.

---

### Scénario 2 — Personne qui regarde la télévision

**Situation :** 20h. Utilisateur assis sur son canapé. GPS fixe depuis 1h30. Caméra le voit assis.

**Ce que Guardian observe :** Immobilité GPS depuis 1h30. Heure : 20h (pas nuit). Caméra : posture assise, personne présente.

**Comportement attendu :** Signal immobility déclenché à 45 min. Mais caméra confirme personne vivante assise. **Atténuation automatique si caméra active et personne visible.** → **Niveau 1 DOUTE** → résolution auto.

**Règle :** Si la caméra confirme une présence vivante dans une posture normale (assis, debout), l'immobility GPS est reclassée DOUTE et non VÉRIFICATION.

**Résultat :** Aucune alerte. Aucun message.

---

### Scénario 3 — Personne qui lit un livre

**Situation :** Identique au scénario 2. Même comportement attendu.

**Résultat :** Aucune alerte. Aucun message.

---

### Scénario 4 — Personne qui fait une sieste (jour)

**Situation :** 14h. Utilisateur allongé sur son lit. GPS fixe depuis 1h. Caméra : posture allongée.

**Ce que Guardian observe :** Immobility depuis 1h. Posture allongée (lit, pas sol). Mode nuit inactif (14h).

**Comportement attendu :**

- Profil SENIOR : tolérance 45 min → Niveau 2 à 45 min → message vérification
- Si utilisateur ne répond pas → Guardian attend 10 min → Niveau 3 → attend encore 5 min
- Si toujours pas de réponse → Niveau 4

**Problème réel :** Une sieste de 2h déclenche une alerte. C'est correct pour un profil senior seul. Mais irritant pour quelqu'un de robuste.

**Mitigation :** L'exploitant peut configurer un profil "SENIOR AUTONOME" avec tolérance à 90 min.

---

### Scénario 5 — Personne qui tombe puis se relève

**Situation :** Utilisateur trébuche. 15 secondes au sol. Se relève et reprend ses activités.

**Ce que Guardian observe :** Caméra : posture au sol pendant 15 secondes. Puis retour posture debout.

**Comportement attendu :** Durée au sol = 15s < seuil ATTENTION (2 min). → **Niveau 0 NORMAL**. Guardian ne fait rien.

**Résultat :** Aucune alerte. La personne s'est relevée — c'est la seule information qui compte.

**Signal speed_anomaly (GPS) :** Ce signal ne doit PAS être utilisé comme proxy pour une chute. Le GPS smartphone ne capture pas une chute de 0.4 seconde. Une vitesse GPS anormale reflète une perturbation du signal GPS, pas une chute. **Ce signal doit être désactivé comme indicateur de chute.**

---

### Scénario 6 — Personne qui tombe et reste au sol

**Situation :** Utilisateur tombe. Reste au sol. Ne se relève pas.

| Durée au sol | Niveau | Action |
|---|---|---|
| 0 – 2 min | 0 – 1 | Observer |
| 2 – 5 min | 2 | Message vérification (10 min d'attente) |
| 5 – 15 min sans réponse | 3 | Deuxième tentative (5 min) |
| > 15 min sans réponse | 4 | SMS contacts |

**Note :** Les délais sont plus courts que pour l'immobilité GPS car la posture au sol est un signal plus spécifique.

---

### Scénario 7 — Téléphone posé sur une table

**Situation :** Utilisateur pose son téléphone sur la table et fait autre chose (cuisine, sortie, douche).

**Ce que Guardian observe :** Caméra : absence de personne. GPS : position fixe.

**Comportement attendu :** → **Niveau 1 DOUTE**. Fenêtre de tolérance : 30 min (profil SENIOR). Si l'utilisateur revient → Niveau 0.

**Si l'absence persiste > 30 min (jour) :** → Niveau 2 → message vérification.

**Résultat :** Une absence de < 30 min ne déclenche aucune alerte. C'est la vie normale.

---

### Scénario 8 — Téléphone retourné

**Situation :** Utilisateur retourne son téléphone pendant un repas ou une conversation.

**Ce que Guardian observe :** Caméra : sol ou surface. Personne absente. GPS : position fixe.

**Comportement attendu :** Identique au scénario 7. Fenêtre de tolérance 30 min avant Niveau 2.

**Règle spéciale :** Un téléphone retourné ne déclenche jamais de signal caméra "personne au sol". La caméra voit une surface — ce n'est pas une posture humaine.

---

### Scénario 9 — Caméra coupée

**Situation :** L'utilisateur ferme l'application, place le téléphone dans sa poche, ou la caméra s'éteint.

**Ce que Guardian observe :** Signal caméra absent.

**Comportement attendu :** → **Niveau 1 DOUTE**. Guardian continue sur les signaux GPS uniquement. Aucun message. Aucun SMS.

**Règle :** La coupure caméra seule ne déclenche jamais d'alerte. La caméra est un signal auxiliaire, pas un signal principal.

**Pour le profil HOME (surveillance domicile) :** Une coupure caméra > 10 min pendant une session active est notée dans les logs et transmise à l'exploitant en tant qu'information, mais sans alerte aux contacts.

---

### Scénario 10 — GPS perdu

**Situation :** Signal GPS indisponible (intérieur, zone blanche, tunnel).

**Ce que Guardian observe :** Positions GPS absentes ou imprécises (précision > 50 m).

**Comportement attendu :** → **Niveau 1 DOUTE**. Guardian continue sur les signaux caméra uniquement si disponibles. Aucun message. Aucun SMS.

**Règle :** La perte GPS seule ne déclenche jamais d'alerte. Guardian note la perte dans les logs.

**Si GPS perdu + caméra absente :** → Niveau 2 si durée > 20 min. "Luna ne peut pas vous localiser depuis 20 minutes."

---

### Scénario 11 — Réseau perdu

**Situation :** Connexion internet interrompue (Wi-Fi coupé, sortie de couverture réseau).

**Ce que Guardian observe :** Websocket coupé. Pas de données reçues.

**Comportement attendu :** Buffering local sur l'appareil. Reconnexion automatique. Aucune alerte.

**Règle :** La perte réseau ne déclenche jamais d'alerte immédiate. Si la perte dure > 30 min, une notification est envoyée aux contacts uniquement si une session Guardian était active : "Luna a perdu le contact avec l'application de [Prénom] depuis 30 minutes. Vérifiez que le téléphone est chargé et connecté."

Ce n'est pas une alerte d'urgence. C'est une information.

---

### Scénario 12 — Utilisateur qui ne répond pas

**Situation :** Guardian envoie une vérification. L'utilisateur ne répond pas.

**Comportement attendu :**

```
Niveau 2 → message vérification → attente 10 min
                                         ↓
                                  Toujours sans réponse
                                         ↓
                              Niveau 3 → 2e tentative → attente 5 min
                                         ↓
                                  Toujours sans réponse
                                         ↓
                                    Niveau 4 → SMS contacts
```

**Raisons probables d'une non-réponse (toutes bénignes) :**

- Douche (10–20 min)
- Conduite (ne regarde pas son téléphone)
- Conversation téléphonique
- Sieste légère
- Travail en extérieur
- Téléphone en silencieux

C'est pourquoi le délai est de 10 + 5 = **15 minutes minimum** avant SMS. Pas 2 minutes.

---

### Scénario 13 — Utilisateur qui répond tardivement

**Situation :** Guardian a déjà envoyé un SMS Niveau 4. L'utilisateur répond ensuite "tout va bien."

**Comportement attendu :**

1. Retour immédiat au Niveau 0
2. Grace period 2h activée
3. **SMS d'annulation envoyé automatiquement aux contacts** dans les 60 secondes

**SMS d'annulation :**
> "✅ Luna Guardian — Fausse alerte confirmée. [Prénom] a confirmé qu'il/elle allait bien à [heure]. Aucune intervention nécessaire. Nous nous excusons pour l'inquiétude causée."

**Règle absolue :** Tout SMS d'alerte doit être suivi d'un SMS d'annulation si la situation est résolue. Les contacts ne doivent jamais rester dans l'incertitude.

---

### Scénario 14 — Utilisateur qui répond "tout va bien"

**Situation :** Niveau 2 ou 3. L'utilisateur appuie sur le bouton vert.

**Comportement attendu :**

- Retour immédiat Niveau 0
- Grace period 2h (pas de nouvelle vérification pendant 2h même si les signaux persistent)
- Log : "Vérification confirmée à [heure]"
- Aucun SMS aux contacts (si l'alerte n'a pas encore été envoyée)

**Règle de respect :** Guardian fait confiance à l'utilisateur. Si l'utilisateur dit qu'il va bien, Guardian croit l'utilisateur pendant 2h.

---

### Scénario 15 — Contact d'urgence qui reçoit déjà une alerte

**Situation :** Un SMS d'alerte Niveau 4 a été envoyé. Le contact répond "OUI" (j'interviens).

**Ce que Guardian doit faire :**

1. Enregistrer la réponse
2. Notifier l'application de l'utilisateur si elle est accessible
3. Si d'autres contacts d'urgence existent, leur envoyer : "Un proche ([prénom du contact] si autorisé sinon "un proche") a indiqué qu'il/elle intervenait."
4. Stopper les éventuels rappels automatiques vers ce contact

**Ce que Guardian ne doit pas faire :**

- Envoyer un nouveau SMS d'alerte si le contact a confirmé son intervention
- Spammer les contacts avec des rappels toutes les 5 minutes

---

### Scénario 16 — Animal dans le champ de la caméra

**Situation :** Un chat ou un chien passe devant la caméra.

**Ce que Guardian observe :** Le système Vision doit compter uniquement les personnes. Un animal est classé en objet, non en personne.

**Comportement attendu :** → **Niveau 0 NORMAL**. Aucune action.

**Règle :** Si `persons_count = 0` uniquement à cause d'un animal, le signal "absence de personne" est déclenché normalement. L'animal ne compte pas comme une présence.

---

### Scénario 17 — Bébé qui dort

**Situation :** Bébé dans son berceau. GPS du parent fixe ou téléphone posé. 14h. Sieste.

**Profil BABY :** Tolérance immobilité = 120 minutes (sieste normale d'un bébé).

**Mode nuit :** Actif entre 23h et 7h → signaux immobilité suspendus.

**Comportement attendu :** Aucune alerte pendant 120 minutes de sieste. Aucune alerte la nuit si en safe zone.

**Résultat :** Guardian surveille silencieusement. Ne dérange pas les parents.

---

### Scénario 18 — Personne âgée qui dort

**Situation :** Grand-mère de 82 ans. 22h30. Couchée. GPS fixe. Safe zone.

**Comportement attendu :** Mode nuit actif → signal immobilité suspendu → **Niveau 0 NORMAL** jusqu'à 7h.

**Ce qui resterait actif la nuit :**
- Si elle se lève et sort de chez elle (geofence_exit + night_anomaly) → Niveau 2 après 10 min hors zone
- Si elle chute au sol et reste plus de 5 min (caméra, si active)

**Résultat :** Guardian ne réveille personne pour une nuit normale de sommeil.

---

### Scénario 19 — Utilisateur qui conduit

**Situation :** Utilisateur dans sa voiture. GPS en mouvement. Vitesse GPS 50–130 km/h.

**Ce que Guardian observe :** Mouvement GPS continu → `is_immobile = False` → aucun signal immobilité.

**Signal speed_anomaly :** Ce signal est désactivé comme proxy de chute (voir Scénario 5). La conduite à vitesse normale ne déclenche rien.

**Sortie de zone :** Si l'utilisateur conduit hors de sa zone de confiance → signal geofence_exit. Mais ce signal seul ne déclenche qu'un Niveau 1 si le déplacement est fluide (vitesse normale, mouvement continu = conduite probable).

**Comportement attendu :** **Niveau 0 NORMAL** pour une conduite standard.

---

### Scénario 20 — Utilisateur sous la douche

**Situation :** Utilisateur sous la douche. Téléphone dans la salle de bain. GPS fixe. Caméra : personne absente (téléphone sur le rebord).

**Ce que Guardian observe :** GPS immobile. Caméra : absence de personne.

**Comportement attendu :** Fenêtre de tolérance absence caméra = 30 min. Une douche dure 5–20 min. → **Niveau 1 DOUTE** → résolution automatique au retour.

Si la douche dure exceptionnellement > 30 min → Niveau 2 → message de vérification → attente 10 min.

**Résultat :** Aucune alerte pour une douche normale. Guardian attend patiemment.

---

## PARTIE 6 — PROTOCOLE SMS

### 6.1 SMS d'alerte (Niveau 4)

**Quand envoyer :** Uniquement après échec de deux vérifications consécutives (Niveaux 2 et 3).

**À qui :** Contacts d'urgence enregistrés et consentants.

**Contenu obligatoire :**
- Prénom de l'utilisateur
- Description factuelle de la situation (sans diagnostic médical)
- Heure et durée depuis le dernier contact
- Lien de localisation avec précision réduite (±100m, jamais adresse exacte)
- Instructions claires : appeler directement, puis 15/112 si pas de réponse
- Option de réponse : "Répondez OUI si vous intervenez"

**Limites :** Maximum 3 alertes par tranche de 24 heures. Anti-spam progressif (voir Partie 7).

### 6.2 SMS d'annulation (obligatoire)

**Quand envoyer :** Dans les 60 secondes suivant une confirmation "Tout va bien" par l'utilisateur, si un SMS d'alerte avait été envoyé.

**Contenu :**
> "✅ Luna Guardian — Fausse alerte. [Prénom] a confirmé qu'il/elle allait bien à [heure]. Aucune intervention nécessaire."

**Règle absolue :** Un SMS d'alerte sans SMS d'annulation ultérieur laisse les contacts dans l'incertitude. C'est inacceptable.

### 6.3 SMS de retour à la normale (informatif)

**Quand envoyer :** Optionnel. Si l'exploitant l'active. Envoyé en fin de session Guardian quand l'utilisateur ferme la surveillance.

**Contenu :**
> "ℹ️ Luna Guardian — Session de surveillance terminée. [Prénom] a mis fin à la session à [heure]. Tout s'est bien passé."

---

## PARTIE 7 — ANTI-FAUX-POSITIFS

### 7.1 Temporisations cumulées

```
Signal détecté → Fenêtre de tolérance (selon profil)
                       ↓ Si signal persiste
               Niveau 2 → Attente réponse 10 min
                       ↓ Si pas de réponse
               Niveau 3 → Attente réponse 5 min
                       ↓ Si pas de réponse
               Niveau 4 → SMS → max 3/24h

Total minimal avant SMS : 45 min à 3h selon profil
```

### 7.2 Backoff progressif entre alertes Niveau 4

| Alerte n° | Délai minimum avant la suivante |
|---|---|
| 1ère | 30 minutes |
| 2ème | 60 minutes |
| 3ème | 120 minutes |
| Au-delà | Bloqué — attente humaine |

### 7.3 Grace period après confirmation

2 heures après un "Tout va bien" → Guardian ne déclenche pas de Niveau 2, même si les signaux persistent.

### 7.4 Combinaison de signaux requis (Niveau 3 direct)

Un seul signal ne suffit pas pour atteindre le Niveau 4 sans passer par le cycle complet. Exception : personne au sol > 10 min sans mouvement (1 seul signal suffit, délai réduit).

### 7.5 Plafond quotidien

3 alertes SMS maximum par session de 24h. Au-delà, Guardian reste en surveillance sans envoyer de SMS supplémentaires jusqu'à l'intervention humaine ou la fin de session.

---

## PARTIE 8 — RGPD

### 8.1 Ce qui est collecté

| Donnée | Durée de conservation | Localisation |
|---|---|---|
| Positions GPS | 24 heures (réduction recommandée vs actuel 7j) | Redis, chiffré |
| Frames caméra | 0 seconde — jamais stockées | Mémoire vive uniquement |
| Résultats d'analyse caméra | 24 heures | Redis |
| Historique alertes | 30 jours | Base de données (conformité légale) |
| Numéros contacts d'urgence | Durée de l'abonnement | Base de données chiffrée |
| Logs de vérification | 30 jours | Base de données |

### 8.2 Ce qui est envoyé à des tiers

| Donnée | Destinataire | Base légale |
|---|---|---|
| Frames caméra (analyse) | OpenAI Vision (API) | Nécessité contractuelle |
| Coordonnées GPS (résolution adresse) | Nominatim/OSM | Intérêt légitime |
| Contenu SMS | Twilio | Nécessité contractuelle |
| Localisation (lien Maps) | Contacts d'urgence | Consentement utilisateur |

**Note Nominatim :** L'usage de Nominatim (OpenStreetMap) dans un service commercial doit respecter les CGU. Alternativement, la précision de la localisation dans le SMS peut être réduite à ±100m en effectuant le calcul localement, sans appel Nominatim.

### 8.3 Consentement

1. **Utilisateur :** Doit accepter explicitement l'activation de Guardian (pas de pré-coché).
2. **Contacts d'urgence :** Doivent être informés qu'ils peuvent recevoir des SMS Luna. L'utilisateur déclare les avoir informés lors de l'ajout d'un contact.
3. **Droit à l'oubli :** Une route `DELETE /api/guardian/data` doit permettre à l'utilisateur d'effacer toutes ses données Guardian.

### 8.4 Minimisation des données

- Les frames caméra ne sont jamais stockées ni envoyées à des tiers en dehors de l'analyse temps réel.
- Les positions GPS dans les SMS sont arrondies à ±100m (3 décimales maximum).
- Les numéros de téléphone des contacts ne sont jamais inclus dans les logs.

---

## PARTIE 9 — LA RÉPONSE AUX 365 JOURS

> Si Guardian surveille réellement un parent âgé pendant 365 jours, comment éviter qu'il devienne agaçant, ignoré, ou source de fausses alertes ?

La réponse repose sur **5 principes de confiance** :

### Principe 1 — Le silence est une preuve de qualité

Guardian ne parle pas pour prouver qu'il fonctionne. Une journée sans message est une journée réussie. Les alertes doivent être des événements rares, pas des rappels quotidiens.

### Principe 2 — Respecter les rythmes humains

La nuit est sacrée. Les siestes sont normales. Regarder la télévision 2h est un acte banal. Guardian connaît ces rythmes et les respecte. Il ne demande pas "ça va ?" à une personne qui est en train de dormir.

### Principe 3 — Chaque alerte doit valoir quelque chose

Si les contacts reçoivent 3 SMS par semaine et que 95% sont des fausses alertes, ils vont ignorer le 4ème — qui sera peut-être le vrai. L'effet "loup" est le scénario catastrophe à éviter absolument. Une alerte rare mais fiable vaut 100 alertes ignorées.

### Principe 4 — L'annulation restaure la confiance

Un SMS d'annulation "Fausse alerte, [Prénom] va bien" n'est pas un aveu d'échec. C'est une preuve de sérieux. Il dit aux contacts : "On vous a prévenus, on vous tient au courant, vous pouvez nous faire confiance."

### Principe 5 — L'utilisateur a le dernier mot

Guardian peut observer. Guardian peut suggérer. Mais l'utilisateur valide. Un "Tout va bien" mérite 2h de silence en retour. Guardian ne sur-vérifie pas. Il fait confiance.

---

## ANNEXE — Tableau de synthèse des décisions

| Situation | Niveau | Délai avant SMS | Message utilisateur |
|---|---|---|---|
| Dort la nuit en safe zone | 0 | Jamais | Aucun |
| Regarde la TV (caméra active) | 0-1 | Jamais | Aucun |
| Immobile 45 min (jour, senior) | 2 | 15 min + | Vérification douce |
| Au sol 2 min | 2 | 15 min + | Vérification douce |
| Au sol 5 min sans réponse | 3 | 5 min + | Deuxième vérification |
| Au sol 10 min sans réponse | 4 | Immédiat* | SMS contacts |
| Téléphone retourné < 30 min | 1 | Jamais | Aucun |
| Absence caméra < 30 min | 1 | Jamais | Aucun |
| Perte GPS seule | 1 | Jamais | Aucun |
| Perte réseau seule | 1 | Jamais | Aucun |
| Pas de réponse vérification | 3→4 | 15 min total | 2 tentatives |
| Répond "tout va bien" | 0 | N/A | Grace 2h |
| Animal détecté | 0 | Jamais | Aucun |
| Conduit (GPS en mouvement) | 0 | Jamais | Aucun |
| Sous la douche < 30 min | 1 | Jamais | Aucun |

*Avec délai de confirmation 2 min.

---

*Ce document remplace tout comportement implicite ou non documenté du moteur Guardian.*
*Toute divergence entre ce document et le code constitue un bug à corriger.*
*Version 2.0 — Juin 2026*
