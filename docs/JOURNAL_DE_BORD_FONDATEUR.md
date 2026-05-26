# Journal de bord fondateur — Luna

Ce journal raconte l'avancement de Luna en langage humain. Il complète GitHub :
les commits disent ce qui a changé dans le code ; ce journal explique pourquoi,
dans quel ordre, avec quelles décisions et ce qu'il reste à faire.

## Comment l'utiliser

- Ajouter une entrée datée à chaque étape importante.
- Écrire pour Ludovic, pas pour une machine.
- Toujours distinguer : idée, décision, code GitHub, déploiement Cloud Run,
  APK rebuildée, APK installée, test réel sur téléphone.
- Noter les validations attendues de Ludovic.
- Noter les risques et les suites.

---

## 2026-05-25 — Coordination IA et boucle téléphone réel

### Résumé humain

La journée a servi à transformer Luna d'un projet surveillé surtout côté serveur
en un système coordonné entre plusieurs IA, avec une première passerelle vers
le réel : le téléphone fondateur.

L'idée centrale posée aujourd'hui :

> GitHub et Cloud Run ne suffisent pas. Luna doit savoir ce que l'APK vit réellement sur le téléphone.

### Ce qui a été mis en place

#### 1. Espace de coordination multi-agents

Un espace de travail commun a été créé dans :

```text
docs/AGENTS_COLLABORATION/
```

Son but : éviter que Claude, Codex, DeepSeek, Kimi et Cursor travaillent chacun
dans leur coin sans savoir ce que les autres ont compris ou décidé.

Les règles posées :

- GitHub n'est pas la production.
- Cloud Run n'est pas forcément l'APK réelle.
- L'APK réelle n'est validée que quand Ludovic la teste sur son téléphone.
- Les modifications importantes passent par une validation.
- Aucun agent ne doit écraser le travail d'un autre.

#### 2. Rôles des IA clarifiés

Les rôles actuels :

| Agent | Rôle humainement résumé |
|---|---|
| Claude | Chef d'orchestre technique, synthèse finale, déploiement Cloud Run |
| Codex | Cadrage GitHub, PR, garde-fous, tests et contre-analyse |
| DeepSeek | Analyse technique, propositions de schémas, risques et moteurs de diagnostic |
| Kimi | Audit documentaire, clarté des promesses, textes compréhensibles |
| Cursor | Cohérence locale VS Code, frontend, Android, routes et affichage |
| Ludovic | Décision finale, validation réelle sur téléphone |

### Objectif 001 — Monitoring vocal réel

#### Problème

Le bouton vocal pouvait être silencieux dans l'APK et s'arrêter après environ
20 secondes. Le monitoring serveur disait que la voix était prête, mais ne
prouvait pas que le téléphone recevait réellement une voix.

#### Ce qui a été compris

Le monitoring existant vérifiait surtout :

- présence de code ;
- configuration serveur ;
- route WebSocket ;
- disponibilité des composants.

Mais il ne vérifiait pas :

- clic réel sur le téléphone ;
- permission micro réelle ;
- audio réellement envoyé ;
- audio réellement reçu ;
- voix entendue par l'utilisateur.

#### Décisions

- Garder une approche conservatrice sur OpenAI Realtime.
- Revenir à un modèle Realtime confirmé.
- Garder `pcm16` côté session.
- Garder la voix féminine `coral`.
- Augmenter le timeout WebSocket pour tenir compte de la WebView Android.
- Ne pas considérer le statut serveur comme preuve d'expérience utilisateur.

#### État

- Correctifs serveur voix déployés.
- Validation finale toujours dépendante du téléphone réel.

### Objectif 002 — Audit fonctionnel APK onglet par onglet

#### Problème

L'APK contient plusieurs onglets et boutons. Après les corrections voix,
monitoring et branding, il reste nécessaire de tester chaque parcours réel.

#### État

Objectif en attente. Il doit venir après la stabilisation du heartbeat APK et
du diagnostic fondateur.

### Objectif 003 — Cerveau APK / télémétrie appareil réel

#### Idée fondatrice

Ludovic a formulé le besoin suivant : l'APK ne doit pas être une WebView
muette. Elle doit avoir un petit "cerveau" capable de dire au serveur ce
qu'elle vit réellement.

La phrase de référence :

> Cloud Run sait ce qu'il sert. L'APK sait ce que l'utilisateur vit. Luna doit comparer les deux.

#### Phase 1 choisie

Commencer petit :

```text
APK -> POST /api/apk/heartbeat -> Cloud Run -> Redis -> /api/admin/objectives
```

Le heartbeat signale :

- version APK ;
- rôle appareil ;
- URL Cloud Run chargée ;
- version Android ;
- modèle téléphone ;
- dernier écran connu ;
- User-Agent `LunaApp/...` ;
- heure de réception serveur.

#### Ce qui a été codé par Claude

- `sendHeartbeat()` dans `MainActivity.java`.
- Endpoint `POST /api/apk/heartbeat` dans `luna_web.py`.
- Stockage Redis 7 jours.
- Check `_check_objective_apk_heartbeat()`.
- Intégration dans `/api/admin/objectives`.
- Correction sécurité `fondateur.html` : secret TOTP retiré du HTML public.
- Correction User-Agent heartbeat après remarque Codex.

#### État production

Claude a déployé Cloud Run.

Résultat après déploiement :

```text
Score : 30/32
APK Fondateur : heartbeat non reçu
```

C'est normal à ce stade : le serveur est prêt, mais l'APK doit être rebuildée,
installée et ouverte pour envoyer le premier heartbeat.

#### Prochaine étape attendue

- Rebuild APK avec les commits heartbeat.
- Installer sur le téléphone de Ludovic.
- Ouvrir l'application.
- Vérifier que `APK Fondateur` passe au vert dans `/api/admin/objectives`.

### Objectif 004 — API fondateur : diagnostic APK + journal des actions

#### Pourquoi cet objectif existe

Objectif 003 observe. Objectif 004 doit comprendre.

Recevoir un heartbeat brut ne suffit pas. Il faut que l'API fondateur dise :

- ce que Luna sait ;
- ce que Luna suppose ;
- ce que Luna ne sait pas ;
- quelle action est recommandée ;
- quelle action est interdite sans validation ;
- quelle trace a été conservée.

#### Principe retenu

```text
Observer -> Interpréter -> Proposer / agir -> Tracer
```

#### Règle importante

Objectif 004 n'est pas de l'auto-guérison complète.

Pour l'instant :

- Luna diagnostique ;
- Luna recommande ;
- Luna trace ;
- Luna n'agit pas sur la production sans Ludovic et Claude.

#### Décisions validées par Codex

- Niveau 1 sans confirmation : oui, si c'est seulement afficher ou proposer.
- Journal 30 jours : oui, raisonnable.
- `waiting_first_contact` : oui, indispensable avant le premier heartbeat réel.

#### Synthèse Claude

Claude prévoit :

- `_analyze_apk_state()`;
- `GET /api/admin/apk-diagnosis`;
- journal Redis `luna:founder:actions:log`;
- affichage dans `fondateur.html`;
- aucun changement Android pour cette phase.

#### Garde-fou Kimi

Kimi a insisté sur un point crucial :

> Luna ne doit jamais présenter une supposition comme une vérité.

Exemple : si aucun événement voix n'est reçu, Luna ne doit pas dire
"Ludovic n'a pas testé". Elle doit dire :

```text
Luna n'a pas reçu de signal vocal. Cela peut vouloir dire que le bouton n'a pas été testé, ou que le signal n'a pas pu remonter.
```

### Décisions de sécurité importantes

- Pas d'audio brut dans la télémétrie.
- Pas de transcript privé.
- Pas de position exacte.
- Pas de secret dans l'APK.
- Pas de clé API, cookie ou token loggé.
- Pas de déploiement déclenché par l'APK.
- Pas de correction production automatique.

### État global à la fin de cette étape

| Sujet | État |
|---|---|
| Coordination IA | En place |
| Rôles IA | Clarifiés |
| Objectif 001 voix | Correctifs serveur déployés, test téléphone encore nécessaire |
| Objectif 002 audit APK | En attente |
| Objectif 003 heartbeat APK | Serveur déployé, APK à rebuilder / installer |
| Objectif 004 diagnostic fondateur | Avis agents reçus, Claude commence l'implémentation |
| Production Cloud Run | Déployée avec heartbeat serveur |
| Téléphone Ludovic | Pas encore validé après rebuild heartbeat |

### Ce qu'il faut surveiller maintenant

1. Le premier heartbeat du téléphone doit apparaître.
2. Le statut `APK Fondateur` ne doit pas rester bloqué en erreur après installation.
3. Le diagnostic fondateur doit utiliser un langage humain.
4. Aucune action automatique production ne doit être ajoutée sans validation.
5. Les événements voix ne doivent venir qu'après validation du heartbeat.

### Prochaine décision Ludovic

Valider l'implémentation de l'objectif 004 Phase 1 :

- diagnostic APK ;
- journal d'actions ;
- affichage fondateur ;
- pas d'action corrective automatique.

---

## 2026-05-26 — Objectifs 010 et 011 + bug Déconnexion mobile

### Résumé humain

Journée de consolidation sur deux objectifs parallèles :
- **Objectif 010** (chat / titres / recherche) : le code est poussé, reste à valider sur téléphone.
- **Bug Déconnexion** : la cause réelle a été identifiée (header droit trop chargé sur mobile) et corrigée proprement.
- **Objectif 011** (services / conciergerie) : audit complet réalisé, SMS/email sécurisés confirmés, trous identifiés sur sandbox et confirmations voix/visio.

### Ce qui a été codé

#### Bug Déconnexion — correction définitive (commit `2452edc`)

Le bouton n'était pas juste "un peu coupé". Le header droit entier débordait sur téléphone :
- nouveau chat (icône) + wakeword (icône) + MAJ (texte court) + logo (30px) + "Deconnexion" (texte long) = trop large.
- Les padding `safe-area-inset-right` sur iPhone ajoutent encore ~20-40px de marge.
- Le texte "Deconnexion" (sans accent) compressait le bouton et le dernier caractère disparaissait.

**Solution implémentée** :
- Bouton `logout-btn` restructuré : icône SVG porte de sortie + span texte séparé.
- Desktop (>600px) : texte "Déconnexion" visible (avec accent corrigé).
- Mobile (<=600px) : texte masqué, icône seule dans un carré 44×44 tactile.
- Très petit écran (<=380px) : `gap` du header droit réduit à 2px.
- Classe `.header-right` ajoutée pour contrôler le `gap` proprement via CSS au lieu de `style` inline.

**Ce que ça change** :
- Économie d'environ 60px de largeur sur mobile.
- Le bouton reste utilisable (44×44 min, tactile accessible).
- Le style premium est conservé (bordure rougeâtre, hover glow).

#### Objectif 010 — validation code

Audit du commit `0d030c5` (titres style ChatGPT + loupe sidebar) :
- Deux blocs `auto_title` dans `luna_web.py` (lignes ~5638 et ~6311) — identiques, cohérents.
- Prompt : "2 à 4 mots maximum", exemples OK/refusés, pas de date, pas de guillemets.
- Garde-fou : si > 5 mots, troncature à 4 mots ; si > 40 caractères, troncature.
- Fallback : premiers 40 caractères du message utilisateur.
- Loupe 🔍 : CSS `::before` sur `.conv-search-wrap`, padding-left 28px, visible et bien positionnée.

**Validation attendue de Ludovic** :
- Créer une conversation claire sur téléphone.
- Vérifier que le titre devient "Services exploitant" ou "Bouton connexion" (2-4 mots).
- Vérifier que ce n'est PAS une phrase comme "Résumé de notre conversation".
- Vérifier que la loupe est visible dans le champ de recherche de la sidebar.
- Vérifier que la recherche filtre bien l'historique.

#### Objectif 011 — audit services (fichier `docs/AUDIT_011_SERVICES.md`)

**Services non sensibles** (10 identifiés) : météo, actualités, recherche web, lieux, stats, missions, badges, contacts, amis — tous en lecture seule, testables sans risque.

**Services sensibles protégés** :
- `send_sms` / `send_email` : confirmations client + garde-fou serveur contact confiance. ✅
- `alert_contacts` : confirmation client + limité aux contacts de confiance. ✅
- `book_flight` / `book_hotel` : confirmation client, mais **pas de mode sandbox**. ⚠️
- `request_payment` : plafond budget + Stripe, mais **pas de confirmation client directe** ni sandbox. ⚠️

**Services sensibles à renforcer** :
- `call_contact` : modal 2 étapes mais **pas de `_showConfirm` explicite** avant l'appel.
- `invite_visio` : picker durée puis redirection immédiate, **pas de confirmation explicite**.

**Risque critique identifié** :
- Absence totale de `LUNA_SANDBOX_MODE`. En mode test, un exploitant peut réserver un vrai vol/hôtel ou déclencher un vrai paiement Stripe.

### Ce qui reste à faire

1. **Valider Objectif 010 sur téléphone** — test réel obligatoire.
2. **Implémenter `LUNA_SANDBOX_MODE`** pour Duffel (vols/hôtels) et Stripe (paiements) avant tout test exploitant.
3. **Ajouter `_showConfirm`** sur `call_contact` et `invite_visio` si validé par Ludovic.
4. **Tester le Lot A** (services non sensibles) dès que possible.
5. **Rebuild APK** si le commit Déconnexion doit être inclus dans l'APK (frontend modifié).

### Risques / points d'attention

- Si l'APK n'est pas rebuildée, la correction Déconnexion ne sera pas visible sur téléphone.
- Sans sandbox, un test malencontreux sur `book_flight` peut engendrer un coût réel.
- Le LLM est le seul garde-fou pour `request_payment` côté conversation. Si le prompt est contourné, le paiement peut passer.

### Décision Ludovic attendue

1. Est-ce que le titre d'une conversation générée sur téléphone respecte bien le format 2-4 mots ?
2. Est-ce que le bouton Déconnexion est entièrement visible et cliquable après rebuild APK ?
3. Faut-il prioriser le mode sandbox avant de continuer l'audit 011 ?

---

## Modèle pour les prochaines entrées

```md
## YYYY-MM-DD — Titre court

### Résumé humain

### Ce qui a été décidé

### Ce qui a été codé

### Ce qui a été déployé

### Ce qui a été testé sur téléphone réel

### Ce qui reste à faire

### Risques / points d'attention

### Décision Ludovic attendue
```
