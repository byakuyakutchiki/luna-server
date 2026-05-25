# Avis Claude

Agent : Claude (claude-sonnet-4-6)
Rôle : Lead technique, codeur final, décision d'architecture

---

## État production au 2026-05-25

- Cloud Run `luna-beta-00432-89z` déployé, score 30/32
- Objectif 003 Phase 1 livré : heartbeat APK opérationnel côté serveur
- fix sécurité fondateur.html : TOTP secret retiré du HTML
- APK v2.8 en attente de rebuild (sendHeartbeat() + User-Agent ajoutés)
- Objectif 004 cadré par Codex, mergé dans main

---

## Objectif 004 — Architecture Claude

### Ce que je valide dans le cadrage Codex

Le cadrage est juste. Les 4 niveaux d'action sont le bon modèle :
- Niveau 0 (observer) et Niveau 1 (action locale non-destructive) : implémenter maintenant
- Niveau 2 (action proposée, bouton de validation) : après test heartbeat réel
- Niveau 3 (rebuild, Cloud Run, env) : **jamais automatique**, toujours Claude + Ludovic

### Architecture `_analyze_apk_state()` — ma proposition

Fonction serveur pure, sans effet de bord, sans appel extérieur :

```python
def _analyze_apk_state(heartbeat: dict | None) -> dict:
    if not heartbeat:
        return {
            "status": "critical",
            "diagnosis": "Aucun heartbeat reçu",
            "probable_cause": "APK pas encore ouverte ou rebuild nécessaire",
            "recommended_action": "Ouvrir l'APK sur le téléphone fondateur",
            "action_level": 0,
            "can_auto_fix": False,
            "evidence": {},
        }
    age_s = time.time() - heartbeat.get("ts", 0)
    apk_version = heartbeat.get("apk_version", "")
    cloud_url = heartbeat.get("cloud_url", "")
    expected_version = CURRENT_APK_VERSION  # constante serveur
    # ... règles de diagnostic
```

Principe : règles explicites et lisibles, pas de ML, pas de LLM dans la boucle de diagnostic.

### Journal Redis

Clé : `luna:founder:actions:log` — liste, max 200 entrées, expire 30 jours.
Écriture à chaque appel à `_analyze_apk_state()`, que le résultat soit ok ou non.
Chaque entrée : `{ts, status, diagnosis, action_level, action_taken, evidence}`.

**Contrainte** : écriture journal = toujours asynchrone, jamais bloquante, jamais critique path.

### Affichage dans fondateur.html

Pas un nouvel onglet — une **section sous "APK Fondateur"** dans le tab Objectifs existant.
Format : texte en clair pour Ludovic, pas de jargon technique.

```
APK Fondateur — ATTENTION
Téléphone vu il y a 4 min.
Diagnostic : APK v2.7 détectée, v2.8 attendue.
Cause probable : ancienne APK installée ou auto-update non appliqué.
Recommandation : installer la dernière APK.
Action automatique : aucune.
```

### Ce que je n'autoriserai pas dans cette phase

- Aucune action niveau 2 ou 3 sans bouton de validation explicite Ludovic dans l'UI
- Aucune boucle de polling depuis le serveur vers l'APK (sens serveur→APK non existant)
- Aucun stockage de données APK au-delà du heartbeat : pas de screenshot, pas de logs JS privés

### Séquence d'implémentation recommandée

1. Attendre le heartbeat réel (rebuild APK en attente)
2. Implémenter `_analyze_apk_state()` — règles simples, tests unitaires d'abord
3. Exposer via `GET /api/admin/apk-diagnosis` (auth fondateur)
4. Intégrer dans fondateur.html (section, pas onglet)
5. Journal Redis `luna:founder:actions:log`
6. Valider avec Ludovic avant d'ajouter le moindre niveau 2

### Décision sur les niveaux d'action

**Ma recommandation à Ludovic** :

| Niveau | Autorisation |
|---|---|
| 0 — observer | ✅ oui, toujours |
| 1 — action locale (ex: afficher lien APK) | ✅ oui, sans confirmation |
| 2 — action proposée (ex: forcer refresh) | ⏸ après test heartbeat réel seulement |
| 3 — infra (rebuild, Cloud Run, env) | ❌ jamais automatique |

---

## Risques que j'identifie

1. **Journal Redis trop verbeux** : si le heartbeat est envoyé à chaque `onResume()`, le journal peut se remplir vite. Solution : écrire seulement si le statut change, ou max 1 entrée par tranche de 10 minutes.
2. **Diagnostic sans heartbeat = critical** : va apparaître en rouge dans les objectifs jusqu'au premier rebuild. C'est voulu mais peut paraître anxiogène. Proposer un statut `waiting_first_contact` distinct de `critical`.
3. **URL check trop strict** : si Cloud Run change de révision, l'URL reste la même mais la comparaison peut échouer sur des trailing slashes. Normaliser les deux URLs avant comparaison (déjà fait côté serveur).

---

## Validation attendue de Ludovic

- [ ] Confirmer niveau 1 autorisé sans bouton de validation
- [ ] Confirmer que le journal Redis est voulu (données conservées 30 jours)
- [ ] Valider le texte affiché fondateur avant implémentation UI (format ci-dessus)

---

*Claude — 2026-05-25*
