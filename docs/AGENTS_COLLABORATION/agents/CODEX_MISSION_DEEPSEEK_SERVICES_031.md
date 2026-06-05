# Codex -> DeepSeek — Mission Services / readiness exploitant — Objectif 031

DeepSeek, mission prioritaire non destructive.

## Contexte fondateur

Ludovic est le fondateur. Il n'est pas l'entreprise exploitante finale qui utilisera Luna/Services avec ses propres clients, ses propres moyens de paiement, ses propres comptes Twilio/Stripe/Duffel/Email et ses propres responsabilites.

Donc on ne doit pas lui demander de tester en reel un compte Stripe entreprise, un paiement, une reservation, un SMS, un email ou un appel pour prouver que Services marche.

Le but est different : prouver que la section Services est prete pour un futur exploitant, ou lister exactement ce qui manque.

## Lien terrain

Production : https://luna-beta-674304336025.europe-west1.run.app/

Chemin : connexion -> onglet `Services`.

Dans le code, cet onglet correspond a :

- `static/index.html`
- bouton `data-tab="conciergerie"`
- panneau `#tab-conciergerie`
- cartes `.conc-card`
- handlers `CARD_HANDLERS`
- endpoint principal `POST /api/concierge/action`

## Fichiers a lire

Lis au minimum :

- `docs/AGENTS_COLLABORATION/OBJECTIF_031_SERVICES_EXPLOITANT_AUDIT.md`
- `static/index.html`
- `luna_web.py`
- `docs/AGENTS_COLLABORATION/agents/KIMI_AVIS_011.md`
- `docs/AGENTS_COLLABORATION/agents/DEEPSEEK_BUTTON_HANDLER_MAP.md`

Cherche aussi les routes liees a Stripe, Twilio, email, call, booking, reservation, visio/invitation.

## Ce que tu dois auditer

Pour chaque carte Services, construis la chaine complete :

Carte visible -> handler JS -> action envoyee -> endpoint -> outil/backend -> effet reel possible -> risque -> garde-fou.

Actions attendues dans la cartographie :

- Vols
- Hotels
- Restaurants
- Recherche web
- Autour de moi / commerces
- Meteo
- Actualites
- SMS
- Email
- Appel
- Visio / invitation
- Alerte contacts d'urgence
- Rappel
- Note
- Document
- Contacts de confiance
- Formulaires
- Stats
- Missions
- Badges
- Amis en ligne

## Questions auxquelles tu dois repondre

1. Quelles actions sont `READ_ONLY` et testables sans risque par Ludovic ?
2. Quelles actions sont `INTERNAL_ACTION` et testables avec donnees factices ?
3. Quelles actions sont `EXTERNAL_ACTION` et doivent etre bloquees ou confirmer clairement ?
4. Quelles actions sont `BOOKING_PAYMENT` et ne doivent pas etre testees en reel par le fondateur ?
5. Est-ce que `/api/concierge/action` melange trop d'actions de niveaux de risque differents ?
6. Est-ce que les erreurs serveur sont lisibles pour un exploitant, ou trop techniques ?
7. Est-ce qu'il manque un mode `founder_dry_run` ou `exploitant_ready_check` ?
8. Quels badges/labels UI faut-il ajouter pour distinguer lecture, action interne, action externe et paiement ?
9. Quelles variables/configs exploitant sont indispensables avant production ?
10. Quelle liste P0 Claude doit-il coder apres ton audit ?

## Interdictions

Audit seulement. Ne lance pas :

- SMS reel
- email reel
- appel reel
- visio avec SMS reel
- alerte contacts
- paiement Stripe
- reservation vol/hotel/restaurant
- modification de secrets
- deploiement

## Livrable obligatoire

Ecris et pousse sur GitHub :

`docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_SERVICES_EXPLOITANT_031.md`

Format obligatoire :

```markdown
# DeepSeek — Audit Services exploitant — Objectif 031

## Verdict court

## Carte complete Services
| Carte | Handler JS | Action | Endpoint | Classe risque | Test fondateur | Config exploitant | Garde-fou |

## Actions sensibles / cout reel
| Action | Cout/risque | Peut partir en reel ? | Bloque aujourd'hui ? | Correctif necessaire |

## Cas d'erreur a gerer
| Cas | Symptome utilisateur | Cause probable | Correctif |

## Incoherences UX / produit

## P0 pour Claude

## P1 pour Kimi

## Ce que Codex doit verifier

## Decision Ludovic requise
```

Message AGENT_CHANNEL a ajouter :

```markdown
Agent : DeepSeek
Objectif : 031
Type : audit Services / readiness exploitant
Resume : ...
Fichier concerne : docs/AGENTS_COLLABORATION/agents/DEEPSEEK_AUDIT_SERVICES_EXPLOITANT_031.md
Risque : audit non destructif ; ne pas tester paiements/SMS/email/appels/reservations reels.
Decision Ludovic requise : oui seulement pour action sensible, paiement, reservation ou deploy.
Action proposee : ...
```

Regle : si ce n'est pas pousse sur GitHub, ce n'est pas livre.

