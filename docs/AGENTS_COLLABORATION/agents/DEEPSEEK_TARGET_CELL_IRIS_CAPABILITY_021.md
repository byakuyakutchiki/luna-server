# DeepSeek — TARGET CELL — Iris Capability Gateway

Objectif : 021  
Source : retour DeepSeek transmis par Ludovic dans le fil Codex  
Statut : transcrit par Codex — DeepSeek doit encore confirmer/pousser directement si besoin

---

## Cellule 1 — Capacités Iris

### Target exacte

Iris est une passerelle de capacités activables à la voix, avec confirmation systématique pour toute action engageante, rendu visuel automatique, et respect des garde-fous.

### Capacités attendues

| # | Capacité | Description |
|---|---|---|
| 1 | Recherche web | Iris cherche une info externe et la projette |
| 2 | Porte-documents | Iris accède aux documents du souscripteur |
| 3 | Upload / Analyse | Iris analyse un document uploadé et projette sa synthèse |
| 4 | Carte / Map | Iris localise une adresse avec consentement |
| 5 | Twilio SMS | Iris envoie un SMS avec confirmation |
| 6 | Twilio Appel | Iris passe un appel avec confirmation |
| 7 | Email | Iris envoie un email avec confirmation |
| 8 | Teams | Iris gère les participants : invite, mute, kick, rôles |
| 9 | Rendu visuel | Iris choisit le type de projection adapté |
| 10 | Garde-fous | Consentement, horaires, quotas, blacklist |

---

## Cellule 2 — Contrat Intent → Tool → Render → Garde-fou

| Intent utilisateur | Tool déclenché | Render type | Garde-fou |
|---|---|---|---|
| "cherche X" / "trouve X" | search_web | context_panel | Aucun, lecture seule |
| "montre mes documents" | list_documents | table ou kpi_cards | Filtre par propriétaire |
| "analyse ce PDF" | analyze_document | document_insight | Fichier vérifié : type, taille |
| "où est X ?" / "carte de X" | show_map | map | Consentement géoloc |
| "envoie un SMS à X" | send_sms | action_board | Confirmation + horaires + blacklist |
| "appelle X" | make_call | action_board | Confirmation + horaires + blacklist |
| "envoie un email à X" | send_email | action_board | Confirmation |
| "invite X" / "exclure X" | manage_team | status_rail + action_board | Souscripteur seul |
| Toute demande d'info | Inférence auto | Meilleur render_type | Aucun |

---

## Cellule 3 — Vérification backend

Route : `/api/capability/...`

| Route | Tool | Statut |
|---|---|---|
| POST `/api/capability/search` | search_web | À vérifier |
| GET `/api/documents/v2/list` | list_documents | Existe |
| POST `/api/documents/v2/scan` | analyze_document | Existe |
| GET `/api/map/geocode` | show_map | À vérifier |
| POST `/api/sms/send` | send_sms | Désactivé |
| POST `/api/call/make` | make_call | À vérifier |
| POST `/api/email/send` | send_email | À vérifier |
| POST `/api/workspace/invite` | manage_team | Livré, commit c2b1990 |

---

## Cellule 4 — Garde-fous vérifiés

| Garde-fou | Statut | Preuve |
|---|---|---|
| Confirmation action | Présent | `validation_required` dans WS |
| Horaires 22h-7h | Présent | `_check_time_restriction()` |
| Blacklist secours | Présent | `FORBIDDEN_NUMBERS` |
| Quota voix | À vérifier | Mentionné dans spec, pas confirmé dans le code |
| Consentement géoloc | Absent | À coder |
| Filtre propriétaire docs | À vérifier | Route v2 existe, filtre à confirmer |
| Vérification fichier upload | À vérifier | Type + taille max |

---

## Cellule 5 — Verdict par capacité

| Capacité | Statut | Verdict |
|---|---|---|
| Recherche web | non code | Route API à créer selon DeepSeek, à vérifier car des tools recherche existent déjà |
| Porte-documents | partiel | Routes existent, rendu visuel à brancher |
| Upload / Analyse | partiel | Route scan existe, `document_insight` à connecter |
| Carte / Map | non code | Route à créer + consentement |
| SMS | code non prouvé | Route désactivée |
| Appel | non code | Route à créer |
| Email | non code | Route à créer |
| Teams | atteint | c2b1990 déployé selon retour équipe |
| Rendu visuel | partiel | `inferCommandRenderFromText` livré, intégration à prouver |
| Garde-fous | partiel | 3/7 vérifiés |

---

## Cellule 6 — Prochaines actions DeepSeek

| Priorité | Action | Qui |
|---|---|---|
| P0 | Intégrer `inferCommandRenderFromText` dans le flux WS | Claude |
| P0 | Activer route SMS avec confirmation | Claude |
| P0 | Créer route `search_web` | Claude |
| P1 | Créer route `show_map` + consentement géoloc | Claude |
| P1 | Créer routes `make_call` + `send_email` | Claude |
| P1 | Vérifier quota voix | Codex |
| P2 | UX Capability Gateway | Kimi |

---

## Arbitrage Codex

Codex ne valide pas "activer route SMS" comme P0 d'exécution réelle.

La version autorisée en P0 est :

1. préparer un `action_board` SMS ;
2. afficher destinataire, message, coût/risque ;
3. appliquer horaires + blacklist + quota ;
4. exiger validation owner ;
5. ne pas envoyer le SMS tant que la chaîne complète n'est pas prouvée.

Même règle pour appel et email.

---

## Message AGENT_CHANNEL proposé

Agent : DeepSeek  
Objectif : 021  
Type : TARGET CELL — Iris Capability Gateway  
Résumé : 10 capacités auditées selon la méthode TARGET_CELL. Verdicts : Teams = atteint, Porte-documents/Document/Rendu visuel/Garde-fous = partiel, Recherche/Map/Appel/Email = non code, SMS = code non prouvé. 3 P0 proposés : intégrer inferCommandRenderFromText, activer SMS, créer search_web. Codex corrige : SMS/appel/email restent action_board + validation_required, pas d'action réelle directe.  
Fichier concerné : docs/AGENTS_COLLABORATION/agents/DEEPSEEK_TARGET_CELL_IRIS_CAPABILITY_021.md  
Risque : 7 capacités sur 10 ne sont pas prouvées.  
Décision Ludovic requise : oui — prioriser P0  
Action proposée : Claude prépare un plan V1 sans action réelle, puis Codex tranche.

