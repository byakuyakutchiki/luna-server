# Guardian — Arbre de Décision Officiel
**Référence : GUARDIAN_DECISION_TREE**
**Date : 15 juin 2026**
**Conforme à : GUARDIAN_BEHAVIOR_POLICY_V2.md**

---

## Lecture de ce document

Chaque nœud de l'arbre représente une question posée par Guardian.
Chaque branche représente une réponse possible.
Les feuilles (terminaux) indiquent l'action finale.

Symboles :
- `[?]` → Question / condition
- `→` → Si OUI ou condition remplie
- `⇢` → Si NON ou condition non remplie
- `✅` → Action positive / résolution
- `⚠️` → Action de vérification
- `🔔` → Alerte SMS
- `⛔` → Bloqué / non autorisé

---

## ARBRE PRINCIPAL — Vue d'ensemble

```
┌──────────────────────────────────────────────────┐
│            GUARDIAN — SESSION ACTIVE             │
│         Signal GPS ou Caméra reçu                │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │ [?] EST-CE LA NUIT ?    │
         │   (23h00 – 07h00)       │
         └─────────┬───────────────┘
                   │
         ┌─────────┴──────────┐
         │ OUI                │ NON
         ▼                    ▼
┌────────────────┐   ┌─────────────────────────────┐
│ [?] EN SAFE   │   │       ANALYSE DU SIGNAL      │
│    ZONE ?     │   │   (Arbre Signal — voir bas)  │
└──────┬─────────┘   └─────────────────────────────┘
       │
  ┌────┴────────┐
  │ OUI         │ NON
  ▼             ▼
┌────────┐  ┌──────────────────────────────────────┐
│SUSPENDRE│  │ Signaux actifs la nuit hors zone :   │
│immobility│  │ geofence_exit, night_anomaly         │
│→ NORMAL │  │ → Arbre Signal normal                │
└────────┘  └──────────────────────────────────────┘
```

---

## ARBRE SIGNAL — Analyse d'un signal

```
                    SIGNAL REÇU
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     SIGNAL GPS    SIGNAL CAMÉRA   SIGNAL RÉSEAU
          │             │             │
          ▼             ▼             ▼
  [Arbre GPS]   [Arbre Caméra]  [Arbre Réseau]
```

---

## ARBRE GPS

```
SIGNAL GPS
    │
    ├──→ [?] MOUVEMENT DÉTECTÉ (> 10m) ?
    │         │
    │    OUI  │  NON
    │         ▼
    │    ✅ NORMAL — Niveau 0
    │    Signaux immobility remis à zéro
    │
    └──→ [?] IMMOBILITÉ DÉTECTÉE ?
              │
              ▼
         [?] DURÉE D'IMMOBILITÉ ?
              │
    ┌─────────┼──────────┬──────────────┐
    ▼         ▼          ▼              ▼
  < seuil  seuil →    2x seuil →    > 2x seuil
  tolérance  Niveau 1   Niveau 1→2     → Niveau 2
              DOUTE      DOUTE          VÉRIFICATION
    │         │          │              │
    ▼         ▼          ▼              ▼
  NORMAL   Observer   Observer      [Arbre Vérification]
           Attendre   Attendre
           résolution résolution

Seuils par profil (jour) :
  SENIOR : 45 min
  DOG    : 90 min
  BABY   : 120 min
  HOME   : 240 min

    │
    └──→ [?] SORTIE DE ZONE (geofence_exit) ?
              │
         OUI  │  NON
              ▼
         [?] EST-CE LA NUIT (22h-6h) ?
              │
         OUI  │  NON
    ┌─────────┴──────────┐
    ▼                    ▼
  Niveau 2            Niveau 1
  VÉRIFICATION         DOUTE
  immédiate           Observer 10 min
  (après 10 min
  hors zone)
```

---

## ARBRE CAMÉRA

```
SIGNAL CAMÉRA
    │
    ├──→ [?] PERSONNE VISIBLE ?
    │         │
    │    OUI  │  NON
    │         ▼
    │    [?] POSTURE ?
    │         │
    │  ┌──────┼──────────┬──────────┐
    │  ▼      ▼          ▼          ▼
    │ DEBOUT ASSIS   ALLONGÉE    AU SOL
    │  │      │      (lit/canapé)  │
    │  ▼      ▼          ▼          ▼
    │ NORMAL NORMAL     NORMAL   [Arbre Sol]
    │
    └──→ [?] DURÉE ABSENCE PERSONNE ?
              │
    ┌─────────┼──────────┐
    ▼         ▼          ▼
  < 30 min  30–60 min  > 60 min
    │         │          │
    ▼         ▼          ▼
  Niveau 0  Niveau 2   Niveau 2
  NORMAL    VÉRIF.     VÉRIF. (+urgent)
  (tolérance) "Vous êtes là ?"
```

---

## ARBRE SOL (Posture au sol détectée)

```
PERSONNE AU SOL DÉTECTÉE
    │
    ▼
[?] DURÉE AU SOL ?
    │
┌───┴────────┬────────────┬────────────┐
▼            ▼            ▼            ▼
0 – 2 min   2 – 5 min   5 – 10 min  > 10 min
    │            │            │            │
    ▼            ▼            ▼            ▼
  Niveau 1    Niveau 2     Niveau 3     Niveau 4*
  DOUTE      VÉRIFICATION  SUSPICION    ALERTE
  Observer   "Tout va bien ?" "2e appel"  SMS contacts
             attente 10 min  attente 5 min

* Avec délai de confirmation 2 min avant SMS effectif.

[?] Personne se relève avant fin de durée ?
    │
    ▼
✅ NORMAL — timer remis à zéro
```

---

## ARBRE RÉSEAU

```
SIGNAL RÉSEAU
    │
    ├──→ [?] PERTE GPS ?
    │         │
    │    OUI  │
    │         ▼
    │    → Niveau 1 DOUTE
    │    → Continuer sur caméra seule
    │    → Log "GPS indisponible"
    │    → Aucune alerte
    │
    ├──→ [?] PERTE RÉSEAU ?
    │         │
    │    OUI  │
    │         ▼
    │    → Niveau 1 DOUTE
    │    → Buffering local
    │    → Reconnexion auto
    │    [?] Durée perte réseau > 30 min ?
    │         │
    │    OUI  ▼
    │    → SMS informatif (pas alerte) :
    │      "Application hors ligne depuis 30 min"
    │
    └──→ [?] CAMÉRA COUPÉE ?
              │
         OUI  ▼
         → Niveau 1 DOUTE
         → Continuer sur GPS seul
         → Aucune alerte
         → Log "Caméra inactive"
```

---

## ARBRE VÉRIFICATION (Niveaux 2 et 3)

```
NIVEAU 2 DÉCLENCHÉ
    │
    ▼
[?] GRACE PERIOD ACTIVE ? (2h depuis dernier "tout va bien")
    │
OUI ▼              NON
→ Rester           │
  Niveau 1         ▼
  Observer    Envoyer vérification in-app :
              "Luna vous demande : tout va bien ?"
                   │
                   ▼
              ⏱ Attente réponse : 10 MINUTES
                   │
         ┌─────────┴──────────────┐
         ▼                        ▼
    RÉPONSE OUI             PAS DE RÉPONSE
         │                        │
         ▼                        ▼
    ✅ NORMAL                 NIVEAU 3
    Grace period 2h
    [?] SMS d'alerte déjà envoyé ?
         │
    OUI  ▼
    → SMS ANNULATION immédiat
         │
    NON  ▼
    → Aucun SMS nécessaire


NIVEAU 3 DÉCLENCHÉ
    │
    ▼
Envoyer 2e vérification in-app + son d'alerte :
"Luna essaie de vous joindre. Appuyez sur le bouton vert."
    │
    ▼
⏱ Attente réponse : 5 MINUTES
    │
    ├──→ RÉPONSE OUI → ✅ NORMAL + Grace period 2h
    │                    + SMS annulation si SMS déjà envoyé
    │
    └──→ PAS DE RÉPONSE → NIVEAU 4


NIVEAU 4 DÉCLENCHÉ
    │
    ▼
[?] PLAFOND 3 ALERTES/24H ATTEINT ?
    │
OUI ▼                     NON
→ Rester Niveau 3          │
  Attendre humain          ▼
                      [?] DÉLAI BACKOFF RESPECTÉ ?
                           │
                      NON  │  OUI
                      ▼         ▼
                  Attendre  🔔 ENVOYER SMS ALERTE
                             aux contacts d'urgence
                             │
                             ▼
                        Journaliser l'alerte
                        + Timestamp
                        + Incrémenter compteur alertes
```

---

## ARBRE DE DÉSESCALADE

```
UTILISATEUR RÉPOND "TOUT VA BIEN"
    │
    ▼
→ Annuler état alerte
→ Retour Niveau 0
→ Activer Grace Period 2h
    │
    ▼
[?] SMS D'ALERTE AVAIT ÉTÉ ENVOYÉ ?
    │
OUI ▼                     NON
    │                      │
    ▼                      ▼
✅ ENVOYER SMS           Aucun SMS
   D'ANNULATION          nécessaire
   dans les 60 secondes
   "Fausse alerte —
    [Prénom] va bien
    à [heure]"
    │
    ▼
[?] D'AUTRES CONTACTS ONT RÉPONDU "OUI J'INTERVIENS" ?
    │
OUI ▼
→ Envoyer SMS info à ce contact :
  "La situation est résolue.
   [Prénom] va bien. Merci."
```

---

## ARBRE GRACE PERIOD

```
GRACE PERIOD (2h) ACTIVE
    │
    ▼
[?] NOUVEAU SIGNAL D'ALARME REÇU ?
    │
OUI ▼                         NON
    │                          │
    ▼                          ▼
[?] SIGNAL CRITIQUE ?        NORMAL
(sol > 5 min, niveau critique)  Rester Niveau 0
    │
OUI ▼                  NON
→ Ignorer Grace Period  → Maintenir Grace Period
→ Déclencher Arbre Sol  → Rester Niveau 0
  normalement            Aucune action
```

---

## ARBRE ANTI-SPAM (Vérification avant tout SMS)

```
AVANT CHAQUE SMS NIVEAU 4
    │
    ├──→ [?] COMPTEUR ALERTES 24H ≥ 3 ? → OUI → ⛔ BLOQUER SMS
    │
    ├──→ [?] DERNIER SMS < 30 MIN ? → OUI → ⛔ BLOQUER SMS (attendre backoff)
    │
    ├──→ [?] GRACE PERIOD ACTIVE ? → OUI → ⛔ BLOQUER SMS
    │
    ├──→ [?] CONTACTS D'URGENCE CONFIGURÉS ? → NON → ⛔ BLOQUER (log d'erreur)
    │
    └──→ ✅ AUTORISÉ → Envoyer SMS

Backoff progressif :
  1ère alerte → délai minimum suivant : 30 min
  2ème alerte → délai minimum suivant : 60 min
  3ème alerte → délai minimum suivant : 120 min
  → Puis bloqué jusqu'à réinitialisation manuelle ou fin de session
```

---

## FLUX COMPLET — De l'observation à la résolution

```
┌──────────────────────────────────────────────────────────────────┐
│                    OBSERVATION                                   │
│  GPS + Caméra + Réseau → Signaux bruts collectés                │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FILTRAGE                                     │
│  Mode nuit ?  Grace period ?  Profil ?  Tolérance ?             │
│  → Application des fenêtres de tolérance par profil             │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ANALYSE                                      │
│  Signal unique → Niveau 1 DOUTE                                 │
│  Signal persistant → Niveau 2 VÉRIFICATION                      │
│  Signaux multiples ou critique → Niveau 3 SUSPICION             │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                  VÉRIFICATION (Niveau 2)                        │
│  Message in-app : "Tout va bien ?"                              │
│  Attente : 10 minutes                                           │
└────────────────┬─────────────────────────────┬──────────────────┘
                 │                             │
           RÉPONSE OUI                   PAS DE RÉPONSE
                 │                             │
                 ▼                             ▼
┌─────────────────────┐         ┌──────────────────────────────────┐
│    RÉSOLUTION       │         │   SUSPICION FORTE (Niveau 3)    │
│  ✅ NORMAL          │         │   2e tentative + son d'alerte    │
│  Grace period 2h    │         │   Attente : 5 minutes            │
│  SMS annulation     │         └──────────────┬───────────────────┘
│  si SMS déjà envoyé │                        │
└─────────────────────┘                        │
                                      ┌────────┴────────┐
                                      │                 │
                                RÉPONSE OUI       PAS DE RÉPONSE
                                      │                 │
                                      ▼                 ▼
                             ✅ RÉSOLUTION      ALERTE (Niveau 4)
                             Grace period 2h          │
                             SMS annulation           ▼
                                              Anti-spam check
                                                     │
                                            ┌────────┴──────────┐
                                            │                   │
                                      AUTORISÉ              BLOQUÉ
                                            │                   │
                                            ▼                   ▼
                                   🔔 SMS CONTACTS         Attendre
                                   "Luna n'a pas pu        Niveau 3
                                    joindre [Prénom]"      maintenu
                                            │
                                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                     ATTENTE HUMAINE                              │
│  Contact répond "OUI" → Intervention notée                      │
│  Utilisateur répond "tout va bien" → Désescalade                │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                  DÉSESCALADE                                     │
│  → ✅ Retour Niveau 0                                            │
│  → SMS d'annulation (dans 60s si SMS alerte envoyé)             │
│  → Grace period 2h activée                                      │
│  → Compteurs mis à jour                                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## RÈGLES D'OR (résumé exécutif)

```
1. La nuit (23h–7h) en safe zone → Silence total sur immobilité

2. Fenêtre de tolérance → Toujours observer avant d'agir

3. Vérification → Toujours 10 min d'attente (pas 2 min)

4. "Tout va bien" → Grace period 2h + confiance totale

5. SMS alerte → Maximum 3 par 24h, backoff progressif

6. SMS annulation → Obligatoire dans les 60s après résolution

7. Speed anomaly GPS → Ne jamais utiliser comme proxy de chute

8. Caméra coupée seule → Jamais une alerte

9. Perte GPS seule → Jamais une alerte

10. Guardian observe des faits. Il ne diagnostique jamais.
```

---

## MATRICE DÉCISION RAPIDE

```
SITUATION                          NIVEAU  DÉLAI→SMS      ACTION
─────────────────────────────────────────────────────────────────
Dort la nuit, safe zone            0       Jamais         Rien
Regarde TV, caméra active          0-1     Jamais         Rien
Sieste jour (profil senior)        1→2     45 min + 15    Vérif
Sieste bébé (profil baby)          0-1     120 min        Rien
Immobile < tolérance profil        1       Jamais         Rien
Immobile > tolérance (jour)        2       15 min         Vérif
Immobile > 2x seuil               2→3     15 + 5 min     2 vérif
Au sol < 2 min                     1       Jamais         Rien
Au sol 2–5 min                     2       15 min         Vérif
Au sol 5–10 min sans réponse       3       5 min          2e vérif
Au sol > 10 min sans réponse       4       2 min*         SMS
Téléphone retourné < 30 min        1       Jamais         Rien
Absence caméra < 30 min            1       Jamais         Rien
Perte GPS seule                    1       Jamais         Rien
Perte réseau seule                 1       Jamais         Rien
Perte réseau > 30 min              1       N/A            SMS info
Sortie zone (jour)                 1-2     10 min         Vérif
Sortie zone nocturne               2→3     15 + 5 min     2 vérif
Animal détecté                     0       Jamais         Rien
Conduite (GPS en mouvement)        0       Jamais         Rien
Douche (absence < 30 min)          1       Jamais         Rien
Pas de réponse vérification        3→4     5 + 2 min*     SMS
Répond "tout va bien"              0       N/A            Grace 2h
Grace period active                0       Jamais         Rien
─────────────────────────────────────────────────────────────────
* Délai de confirmation avant envoi effectif du SMS
```

---

*Ce document est conforme à GUARDIAN_BEHAVIOR_POLICY_V2.md.*
*Toute modification de ce document doit être validée par le fondateur.*
*Version 1.0 — Juin 2026*
