# AUTONOMY_COMPLETE_ROADMAP

Date : 2026-07-14
Objectif : passer de l'autonomie partielle a une autonomie journee controlee pour YAWatch/Luna.

## Etat actuel

- Pipeline n8n -> mission_store -> superviseur -> Kimi -> rapport fonctionne.
- Telephone ADB visible cote VM.
- Superviseur durci selon Kimi : expected_final_status, rapports, boucle, garde-fous.
- Checklist existe.
- Budget Kimi doit etre configure dynamiquement selon le forfait courant.

## Definition de l'autonomie complete controlee

Ludovic doit pouvoir lancer une commande ou deposer un gros prompt, puis partir.

Le systeme doit :
1. transformer le prompt en mission structuree ;
2. choisir role/budget/statut attendu ;
3. executer les etapes non destructives ;
4. collecter preuves/logs ;
5. produire rapport dans AGENT_SHARED ;
6. mettre a jour la checklist ;
7. proposer ou creer la mission suivante si elle est non destructive et budgetee ;
8. s'arreter sur action risquee ou budget atteint.

## Missions a faire dans l'ordre

### 1. CODEX-REVIEW-SUPERVISOR-HARDENING-001

But : audit sans appel Kimi du code de durcissement.

Kimi doit deposer :
- diffs exacts ou fichiers complets modifies ;
- tests executes ;
- service systemd ;
- preuve budget/block.

Statut attendu : `needs_audit`.

### 2. SUPERVISOR-GIT-CLEANUP-PLAN-001

But : separer fichiers a versionner / a ignorer / a ne jamais commit.

Sortie attendue : rapport avec :
- fichiers source a garder ;
- artefacts APK/build a ignorer ;
- `.env`, DB SQLite, logs a exclure ;
- proposition `.gitignore` si necessaire.

Statut attendu : `needs_audit`.

### 3. SUPERVISOR-COMMAND-ENTRYPOINT-001

But : creer une commande utilisateur simple.

Commande cible :
```bash
luna-mission --prompt-file mon_prompt.txt --role operator --budget 3 --expected needs_audit
```

Version courte future :
```bash
luna-mission "mon gros prompt"
```

Statut attendu : `needs_audit`.

### 4. SUPERVISOR-BUDGET-POLICY-001

But : rendre le budget dynamique.

Exigences :
- budget journalier configurable ;
- budget par mission configurable ;
- stop automatique si budget atteint ;
- rapport budget dans chaque mission.

Statut attendu : `needs_audit`.

### 5. SUPERVISOR-NEXT-MISSION-PLANNER-001

But : proposer la prochaine mission depuis la checklist.

Regles :
- peut proposer plusieurs missions ;
- ne lance automatiquement que les missions non destructives explicitement autorisees ;
- stop sur Guardian/APK ecriture, deploy, push, SMS/appels, install APK.

Statut attendu : `needs_audit`.

### 6. GUARDIAN-AUDIT-VOICE-002

But : premiere vraie mission app, audit non destructif Guardian voix.

Pre-requis : missions 1 a 5 OK ou explicitement acceptees.

Interdit : correction/deploy/SMS/appel reel.

Statut attendu : `needs_audit`.

## Regle de reparation

Kimi peut reparer uniquement dans une mission `FIX-*` ou `REPAIR-*` avec :
- branche dediee ;
- diff limite ;
- tests ;
- rapport ;
- statut `needs_review` ou `needs_audit` ;
- aucun push/deploy automatique.

Codex audite avant validation Ludovic.

## Feu vert actuel

GO pour :
- audit du durcissement superviseur ;
- plan nettoyage Git ;
- commande d'entree mission ;
- budget policy.

NO-GO pour :
- repair Guardian autonome ;
- deploy cloud ;
- push/merge ;
- APK install ;
- SMS/appels reels.
