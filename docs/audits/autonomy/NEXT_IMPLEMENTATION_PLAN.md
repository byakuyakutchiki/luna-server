# NEXT_IMPLEMENTATION_PLAN — Vers l'autonomie complète contrôlée

Date : 2026-07-15T19:30:00+02:00  
Objectif final : Ludovic lance une mission puis peut quitter son ordinateur. Le système planifie, exécute, collecte les rapports, met à jour `AGENT_SHARED`, décide de la mission suivante, respecte budgets et garde-fous, et ne demande une validation humaine que pour les actions réellement risquées.

---

## Vision cible

```
Ludovic : luna-mission "Auditer Guardian voix en lecture seule"
        │
        ▼
   [mission_queue] → n8n webhook → mission_store
        │
        ▼
   [supervisor daemon] ──poll──▶ mission_store
        │
        ▼
   agent_caller (Kimi/DeepSeek/OpenAI)
        │
        ▼
   action_executor (lecture/adb/tests non destructifs)
        │
        ▼
   rapport n8n + AGENT_SHARED + mise à jour checklist
        │
        ▼
   [next_mission_planner] ──si autorisé──▶ création mission suivante
        │
        ▼
   [human_approval workflow] ──si action risquée──▶ notification + attente
```

---

## Phases d'implémentation

### Phase A — Fondations (P0)

**A1. Versionner le superviseur et nettoyer le workspace**
- Séparer sources à versionner (`tools/luna_supervisor/`, `config/*.yaml`, systemd) de secrets/artefacts/DB.
- Proposer/valider `.gitignore`.
- Créer branche `autonomy/supervisor-versioning-001`, commit sélectif.
- **Validation** : `git status --short` ne montre plus le code source du superviseur comme non suivi.

**A2. Créer la commande utilisateur `luna-mission`**
- Ajouter sous-commandes `create-from-prompt` et `submit` dans `cli.py` OU créer wrapper `luna-mission`.
- Version courte : `luna-mission "mon gros prompt" --role operator --budget 3 --expected needs_audit`.
- **Validation** : commande fonctionne, crée mission, retourne `mission_id` + `status=queued`.

**A3. Implémenter le planificateur de prochaine mission**
- Lire `AGENT_SHARED/AUTONOMY_COMPLETE_ROADMAP.md` et `YAWATCH_AUTONOMY_CHECKLIST.md`.
- Choisir la prochaine mission candidate selon règles :
  - ignorer missions BLOCKED sans validation humaine ;
  - ignorer actions Guardian/APK écriture, deploy, push, SMS/appels ;
  - respecter budget restant ;
  - s'arrêter si aucune mission sûre disponible.
- Créer la mission via `mission_store` uniquement si `auto_next=true` et action non destructive.
- **Validation** : fin d'une mission autonome non destructive déclenche création de la suivante ; mission risquée produit `waiting_human_approval`.

**A4. Workflow n8n d'approbation humaine**
- Créer workflow `Luna Human Approval` : webhook d'approbation, notification (email/Slack/telegram), attente.
- Le superviseur appelle ce workflow quand `requires_human_validation=true`.
- Endpoint de reprise : approuver/rejeter avec raison.
- **Validation** : mission bloquée notifie Ludovic ; approbation relance le cycle.

---

### Phase B — Durcissement (P1)

**B1. Rétablir une politique de budget saine**
- Repasser `max_total_ai_calls_per_day` à 6 et `kimi` à 4.
- Ajouter garde-fou : alerte si la politique dépasse 6 appels/jour sans flag `LUNA_DEV_BYPASS=1`.

**B2. Créer `adb-wifi-reconnect.service`**
- Utiliser `tools/luna_runner/adb_wifi_reconnect.sh`.
- Activer en user systemd.
- **Validation** : arrêt/relance ADB WiFi réussi automatiquement.

**B3. Versionner `luna-mission-store.service`**
- Copier l'unité active dans `tools/luna_supervisor/systemd/`.

**B4. Synchroniser les workflows n8n**
- Exporter les workflows cloud actuels, remplacer les JSON locaux, documenter IDs/credentials.

**B5. Auditer Guardian en arrière-plan (non destructif)**
- Démarrer Luna contrôlé via ADB, capturer logcat, screenshot, dumpsys.
- Prouver que le service vocal est actif et à l'écoute.
- **Validation** : rapport `GUARDIAN-AUDIT-VOICE-002_REPORT.md` avec preuves.

**B6. Valider connectivité DeepSeek/OpenAI**
- Vérifier présence et validité des clés API.
- Exécuter dry-run avec chaque caller.

---

### Phase C — Robustesse (P2)

**C1. Nettoyer fichiers swap/backup et mettre à jour `.gitignore`.**
**C2. Remplacer serveur Flask de développement (optionnel).**
**C3. Corriger test unitaire daté.**
**C4. Ajouter rotation log `runs/supervisor.log`.**
**C5. Clarifier politique de fallback agent (Kimi vs blocage).**

---

## Garde-fous non négociables

1. **Aucune action destructive automatique** : edit_files, build_debug, install_debug, commit_local nécessitent branche `automation/*` ET validation humaine ou statut `needs_audit`.
2. **Zones protégées** : `.env`, `data/`, `android-app/src/`, fichiers de config budget/charte restent interdits sans `allows_guardian_modification=true`.
3. **Aucun push/merge/deploy/SMS/appel/cloud** sans validation explicite.
4. **Budget** : arrêt automatique si limite atteinte.
5. **Téléphone** : arrêt ou statut `device_unavailable` si ADB déconnecté.

---

## Liste des 10 prochaines missions techniques (ordre optimal)

1. **`AUTONOMY-VERSIONING-001`** — Versionner `tools/luna_supervisor/`, `config/*.yaml`, systemd et nettoyer `.gitignore`. Statut attendu : `needs_audit`.
2. **`SUPERVISOR-COMMAND-ENTRYPOINT-002`** — Créer/importer la commande `luna-mission` (create-from-prompt + submit). Statut attendu : `needs_audit`.
3. **`SUPERVISOR-NEXT-MISSION-PLANNER-001`** — Implémenter le planificateur de prochaine mission depuis roadmap/checklist. Statut attendu : `needs_audit`.
4. **`N8N-HUMAN-APPROVAL-WORKFLOW-001`** — Créer le workflow n8n de validation humaine et l'intégrer au superviseur. Statut attendu : `needs_audit`.
5. **`SUPERVISOR-BUDGET-POLICY-001`** — Rétablir les limites budget saines et ajouter garde-fou anti-dépassement. Statut attendu : `needs_audit`.
6. **`INFRA-ADB-WIFI-RECONNECT-001`** — Créer/activer le service `adb-wifi-reconnect.service`. Statut attendu : `needs_audit`.
7. **`N8N-WORKFLOW-SYNC-001`** — Exporter/versionner les workflows cloud actuels. Statut attendu : `needs_audit`.
8. **`AGENT-CONNECTIVITY-AUDIT-001`** — Tester DeepSeek et Codex (clés API, dry-run). Statut attendu : `needs_audit`.
9. **`GUARDIAN-AUDIT-VOICE-002`** — Premier audit non destructif Guardian voix avec preuves ADB. Statut attendu : `needs_audit`.
10. **`SUPERVISOR-ROBUSTNESS-001`** — Corriger tests unitaires datés, nettoyer swap/backup, rotation logs, politique fallback. Statut attendu : `needs_audit`.

---

## Critères d'acceptation de l'autonomie complète

- [ ] Ludovic peut lancer une mission via une commande simple.
- [ ] Le superviseur traite la mission sans intervention humaine si elle est non destructive.
- [ ] Un rapport est automatiquement écrit dans `AGENT_SHARED`.
- [ ] La checklist `YAWATCH_AUTONOMY_CHECKLIST.md` est mise à jour.
- [ ] Le système propose/crée la mission suivante si elle est sûre et budgétée.
- [ ] Le système s'arrête et notifie sur action risquée, budget épuisé ou ADB perdu.
- [ ] Aucune action Guardian prod, cloud, APK, SMS/appel/deploy/push n'est réalisée sans validation explicite.
