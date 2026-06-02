# Codex — Vérification audit outils / documents — Objectif 019

Date : 2026-06-02
Agent : Codex
Type : contre-vérification technique

## Résumé

L'audit DeepSeek/GPTK est utile sur les risques, mais sa cartographie des routes est partiellement incorrecte.

Point important : le fichier annoncé `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_OUTILS_019.md` n'est pas présent dans le dépôt au moment de cette vérification. Le contenu a été transmis par Ludovic dans le fil, mais pas livré sur GitHub.

## Routes Documents v2 réellement vues dans `luna_web.py`

Routes confirmées :

| Route | Méthode | Statut |
|---|---|---|
| `/documents` | GET | existe |
| `/api/documents/v2/dashboard` | GET | existe |
| `/api/documents/v2/actions/{doc_id}` | GET | existe |
| `/api/documents/v2/actions/execute` | POST | existe |
| `/api/documents/v2/timeline` | GET | existe |
| `/api/documents/v2/categories` | GET | existe |
| `/api/documents/v2/stats` | GET | existe |

Routes annoncées par DeepSeek mais non trouvées sous `/api/documents/v2/*` :

| Route annoncée | Vérification Codex |
|---|---|
| `/api/documents/v2/upload` | non trouvée |
| `/api/documents/v2/scan` | non trouvée |
| `/api/documents/v2/list` | non trouvée |
| `/api/documents/v2/categorize` | non trouvée |
| `/api/documents/v2/alerts` | non trouvée |
| `/api/documents/v2/explain` | non trouvée |
| `/api/documents/v2/delete` | non trouvée |

## Routes Vault réellement disponibles

Le module `core.vault.routes` est bien monté via `app.include_router(vault_router)`.

Routes utiles confirmées :

| Route | Méthode | Fonction |
|---|---|---|
| `/api/vault/consent` | GET | lire consentement |
| `/api/vault/consent` | POST | enregistrer consentement |
| `/api/vault/consent` | DELETE | révoquer consentement et supprimer données |
| `/api/vault/scan` | POST | scanner un document |
| `/api/vault/docs` | GET | lister documents |
| `/api/vault/doc/{doc_id}` | GET | lire un document |
| `/api/vault/doc/{doc_id}` | DELETE | supprimer un document |
| `/api/vault/reminders` | GET | rappels documents |
| `/api/vault/types` | GET | types de documents |
| `/api/vault/profile-data` | GET | données profil extraites |
| `/api/vault/apply-to-profile` | POST | appliquer au profil |

Conclusion : consentement et droit à l'effacement existent côté Vault. Le problème est plutôt l'absence d'unification claire entre Documents v2 et Vault.

## Actions sensibles

### SMS

`_tool_send_sms()` existe et vérifie :

- licence ;
- service SMS configuré ;
- quota via `_quota_guard.check(... SEND_SMS)` ;
- contact de confiance par nom.

Manques confirmés :

- pas de check horaire 22h-7h dans la fonction elle-même ;
- pas de confirmation serveur obligatoire dans la fonction elle-même.

### Email

`_tool_send_email()` existe et vérifie :

- licence ;
- mémoire ;
- service Gmail/SendGrid disponible ;
- contact de confiance si email direct.

Manques confirmés :

- pas de check horaire 22h-7h dans la fonction elle-même ;
- pas de confirmation serveur obligatoire dans la fonction elle-même.

### Appel

`_tool_call_contact()` existe et vérifie :

- licence ;
- mémoire ;
- client vocal configuré ;
- callback vocal ;
- contact de confiance ou numéro direct fourni.

Garde-fou confirmé :

- blacklist numéros d'urgence déjà présente : `15`, `17`, `18`, `112`, `114`, `115`, `119`, `3114`, `3977`.

Manques confirmés :

- pas de check horaire 22h-7h dans la fonction elle-même ;
- pas de compteur relance max 3 fois ;
- pas de confirmation serveur obligatoire dans la fonction elle-même.

### Paiement

`_tool_request_payment()` ne confirme pas automatiquement Stripe.

Garde-fous confirmés :

- plafond transaction ;
- plafond mensuel ;
- PaymentIntent créé avec `confirm=False`.

Reste à vérifier côté UI : parcours de confirmation utilisateur avant finalisation.

## Budget / quota Iris Audio

`/ws/iris-voice` appelle `_check_budget_guard()` avant de créer le bridge OpenAI Realtime.

Confirmé :

- budget API mensuel vérifié avant session Iris.

À vérifier :

- quota voix mensuel réel dans `QuotaGuard` pour Iris Audio, car le budget API existe mais la minute voix Iris Realtime doit être explicitement comptabilisée.

## Verdict Codex

DeepSeek a raison sur la direction :

- Workbench inexistant ;
- actions sensibles à verrouiller ;
- unification Documents/Vault nécessaire ;
- Iris doit produire des brouillons visibles avant d'exécuter.

Mais DeepSeek doit corriger sa cartographie :

- Documents v2 ≠ Vault ;
- DELETE existe côté Vault ;
- consentement existe côté Vault ;
- blacklist urgence existe déjà côté appel ;
- budget guard Iris existe déjà côté `/ws/iris-voice`.

## Décision recommandée

Ne pas demander à Claude de coder les 6 P0 tels quels.

Ordre correct :

1. Kimi livre la maquette Workbench V1.
2. DeepSeek pousse son audit corrigé sur GitHub avec routes exactes.
3. Claude prépare un patch **non destructif** :
   - panneau Workbench brouillon uniquement ;
   - aucune action réelle ;
   - routes Vault/Documents reliées en lecture ou sauvegarde contrôlée ;
   - confirmation explicite avant toute action sensible.
4. Codex valide la matrice route -> garde-fou -> preuve avant déploiement.

## Message agent

Agent : Codex  
Objectif : 019  
Type : contre-vérification audit DeepSeek/GPTK  
Résumé : Audit utile mais routes partiellement fausses. Documents v2 contient dashboard/actions/timeline/categories/stats ; scan/list/delete/consent sont côté `/api/vault/*`, pas `/api/documents/v2/*`. Consentement et DELETE existent côté Vault. Blacklist urgence existe déjà dans `_tool_call_contact`. Budget guard existe avant `/ws/iris-voice`. Manques réels : Workbench inexistant, pas de check horaire 22h-7h dans SMS/email/appel, pas de relance max 3, confirmation serveur à durcir, quota voix Iris à tracer.  
Fichier concerné : `luna_web.py`, `core/vault/routes.py`, `core/vault/redis_ops.py`  
Risque : moyen si Claude code sur une mauvaise cartographie ; élevé si Iris exécute des actions sans confirmation serveur  
Décision Ludovic requise : oui pour Workbench visible V1  
Action proposée : attendre Kimi UX, demander à DeepSeek de pousser un audit corrigé, puis Claude code Workbench brouillon sans action sensible.
