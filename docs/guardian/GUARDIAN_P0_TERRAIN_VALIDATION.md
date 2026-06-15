# Guardian P0 — Validation Terrain
**Date : 15 juin 2026**
**Statut : PRÊT POUR TEST RÉEL**
**Durée estimée : 45–60 min**

---

## Prérequis

- Téléphone Android (API 24+), APK Luna installé
- 1 vrai contact d'urgence configuré (ton propre second numéro ou quelqu'un de prévenu)
- Compte Twilio actif (numéro +17173409138)
- Session Guardian démarrée avec profil SENIOR
- GPS actif, réseau 4G ou Wi-Fi

---

## Problèmes connus avant de commencer

Ces deux blocages existaient avant P0 et **ne sont pas corrigés** (Sprint B, pas P0) :

**Blocage 1 — Caméra impossible sans contact d'urgence**
`POST /api/guardian/start` retourne 422 si aucun contact configuré → bouton "Activer caméra" affiche "Démarrez Guardian d'abord". Solution : configurer le contact d'urgence AVANT d'appuyer sur Démarrer.

**Blocage 2 — Permission caméra jamais pré-demandée**
La modal "Autoriser" ne demande que le micro. La caméra est demandée séparément au clic "Activer caméra". Si Android a mémorisé un refus antérieur → refus silencieux. Solution : aller dans Paramètres > Luna > Autorisations > Caméra > Autoriser manuellement avant le test.

---

## Séquence de test

### SETUP (5 min)

```
1. Ouvrir l'APK Luna
2. Se connecter (token utilisateur)
3. Aller dans Guardian
4. Ajouter contact d'urgence : ton second numéro
5. Configurer profil SENIOR
6. Vérifier GPS actif (icône en haut)
7. Aller dans Paramètres Android > Luna > Autorisations > activer Caméra + Micro
```

---

### TEST 1 — Guardian démarre (5 min)

**Action :** Appuyer sur "Démarrer Guardian"

**Attendu :**
- Confirmation "Guardian actif" ou indicateur vert
- GPS commence à envoyer des positions (vérifier logs Cloud Run : `gcloud logging read "resource.type=cloud_run_revision" --limit=20`)
- Aucun SMS envoyé

**Attendu PAS :** Erreur 422, toast d'erreur, écran blanc

**Résultat :** ☐ PASS ☐ FAIL — note :

---

### TEST 2 — Immobilité normale (15 min)

**Contexte :** Pose le téléphone sur la table. Reste assis. Ne touche pas l'application.

**Durée : 15 minutes**

**Attendu :**
- Entre 0 et 45 min (seuil SENIOR) : aucune notification
- Aucun SMS reçu par le contact d'urgence
- L'interface affiche l'état de surveillance

*(Avec P0-01 mode nuit : ce test est crucial de JOUR — la nuit le signal est supprimé. Tester en journée pour valider le chemin normal.)*

**Résultat :** ☐ PASS ☐ FAIL — SMS reçus : __ — note :

---

### TEST 3 — Vérification et réponse rapide (10 min)

**Action :** Laisser le téléphone immobile 50 minutes (ou simuler en ajustant le seuil temporairement à 2 min via config JSON si accès admin).

**Attendu :**
- Message de vérification in-app : "Luna vous demande : tout va bien ?"
- Bouton vert visible
- **Aucun SMS** envoyé pendant les 10 premières minutes sans réponse

**Action :** Appuyer sur le bouton vert

**Attendu après réponse :**
- Message de confirmation ("Merci...")
- **Aucun SMS** envoyé (pas d'alerte déclenchée)
- Grace period 2h active (Guardian reste silencieux même si immobilité reprend)

**Résultat :** ☐ PASS ☐ FAIL — note :

---

### TEST 4 — Escalade : ne pas répondre (20 min)

⚠️ **Ce test enverra un vrai SMS au contact configuré. Prévenir le contact avant.**

**Action :** Laisser une vérification sans réponse pendant 12 minutes.

**Attendu :**
- T+0 : message de vérification in-app
- T+10 min : escalade → SMS envoyé au contact
- Contenu SMS attendu : "⚠️ Luna Guardian — [Prénom] n'a pas bougé depuis..."
- SMS contient un lien Maps (coordonnées arrondies ±100m, pas exactes)
- SMS contient "appelez le 15/112"
- SMS contient "Répondez OUI si vous intervenez"

**Action :** Répondre "tout va bien" sur l'app

**Attendu :**
- SMS d'annulation envoyé au contact dans la minute
- Contenu : "✅ Luna Guardian — Fausse alerte confirmée..."

**Résultat :** ☐ PASS ☐ FAIL — SMS alerte reçu : ☐ — SMS annulation reçu : ☐ — note :

---

### TEST 5 — Mode nuit (si test en soirée)

**Contexte :** Heure entre 23h et 7h. Rester immobile dans la safe zone configurée.

**Attendu :**
- Aucune vérification
- Aucun SMS
- Guardian silencieux toute la nuit

**Résultat :** ☐ PASS ☐ FAIL — note :

---

### TEST 6 — Caméra (optionnel si permissions OK)

**Action :** Appuyer sur "Activer caméra"

**Attendu :** Flux caméra actif (diode ou indicateur), frames envoyées au serveur

**Si ça échoue :** Noter le message d'erreur exact. Consulter `GUARDIAN_CAMERA_DIAGNOSTIC.md` — c'est un bug Sprint B connu, pas un régresssion P0.

**Résultat :** ☐ PASS ☐ FAIL ☐ SKIP (bug connu) — note :

---

## Fiche de résultats rapide

```
Date du test :
Appareil :
Version Android :
Heure de début :

TEST 1 — Démarrage         : ☐ PASS  ☐ FAIL
TEST 2 — Immobilité 15 min : ☐ PASS  ☐ FAIL  SMS reçus : __
TEST 3 — Réponse rapide    : ☐ PASS  ☐ FAIL
TEST 4 — Escalade + cancel : ☐ PASS  ☐ FAIL  Alerte SMS : ☐  Annulation : ☐
TEST 5 — Mode nuit         : ☐ PASS  ☐ FAIL  ☐ NON TESTÉ (heure)
TEST 6 — Caméra            : ☐ PASS  ☐ FAIL  ☐ SKIP

Bugs bloquants : ___
Comportements inattendus : ___
```

---

## Si un SMS part quand il ne devrait pas

**Capturer :**
1. L'heure exacte du SMS
2. Le contenu exact
3. Les logs Cloud Run à cette heure : `gcloud logging read "resource.type=cloud_run_revision AND timestamp>=\"[HEURE]\"" --limit=30`
4. L'état de la session (heure, profil, safe zone, heure locale du serveur)

**Hypothèse probable :** Vérifier que `night_mode: True` est bien dans la config de la session (le flag était mort avant P0 — une session créée avant le déploiement P0 n'aura pas `night_mode` dans sa config Redis).

**Solution :** Recréer la session Guardian après le déploiement P0. Les anciennes sessions en Redis ont l'ancienne config.

---

## Verdict attendu

Guardian vient d'être aligné sur la Policy V2 comportementale.

Si les tests 1–4 passent, Guardian est **testable sérieusement** — faux positifs massifs éliminés, SMS annulation fonctionnel, timeout respectueux.

La caméra (Test 6) reste un bug Sprint B indépendant des corrections P0.
