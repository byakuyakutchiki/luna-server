# Claude — Inbox de collaboration IA

Ce fichier sert de point de passage entre Ludo, Codex, Claude, Kimi et DeepSeek pour le chantier Luna.

---

## Gouvernance IA — Méthode de travail

### Rôles

**Claude = Lead technique**
- Analyse l'architecture et prend les décisions techniques
- Lit et écrit le code sur GitHub
- Valide tout changement avant application en production
- Garant de la stabilité, de la sécurité et des intérêts de Ludo (fondateur)

**ChatGPT/Codex = Interface vocale + Relai**
- Capture la voix de Ludo et reformule la demande proprement
- Peut générer des suggestions rapides de code
- Relaie les décisions de Claude vers Ludo à l'oral
- Ne pousse rien en production sans validation Claude

### Flux de travail

```
Ludo (voix) → ChatGPT reformule → Claude analyse + décide
     Claude implémente / valide → ChatGPT lit le résultat à Ludo
```

### Règles non-négociables

1. **Claude a le dernier mot** sur toute modification production
2. **Aucun push direct de Codex** sans revue Claude préalable
3. **Ludo valide** toute modification majeure avant merge sur `main`
4. **Anti-régression** : analyser les dépendances avant toute modification
5. **Validation humaine obligatoire** pour : refactorisation, changement d'API, sécurité, licensing, migration BDD
6. **Stabilité avant optimisation** : ne jamais casser une fonctionnalité stable pour un gain mineur

### Priorités fondateur

- Continuité de service pour les exploitants
- Modèle économique 70/30 préservé
- PV de recette et verrouillage serveur intacts
- Expérience utilisateur final avant tout

---

Objectif global : transformer le cahier des charges fonctionnel en monitoring concret, objectif par objectif, pour que chaque onglet de l'application soit vérifié sur sa promesse utilisateur réelle.

## Source de vérité

- Cahier des charges : `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Methode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`
- Repo principal : `byakuyakutchiki/luna-server`
- Backend : `luna_web.py`
- Guide technique : `GUIDE_DEV.md`

## Boussole fondateur

Ludo est le fondateur. Les IA travaillent dans son interet et dans l'interet de la qualite de Luna.

Priorites non negociables :

- l'application doit fonctionner avant d'ajouter de nouvelles ambitions ;
- tous les boutons visibles doivent etre audites progressivement ;
- aucune modification ne doit casser l'APK, le WebView ou les dashboards ;
- la qualite graphique doit rester premium ;
- le modele licence / royalties doit rester protege ;
- l'exploitant doit pouvoir exploiter, mais pas reproduire ou contourner la technologie ;
- le fondateur doit voir les indicateurs necessaires a ses droits, sans aspirer la comptabilite interne complete de l'exploitant.

Lire `docs/METHODE_TRAVAIL_FONDATEUR.md` avant de proposer une architecture ou une modification sensible.

## Règle de travail

Ne pas travailler sur tous les onglets en même temps.

On valide un objectif à la fois :

1. Instructions
2. Services / Concierge
3. Documents
4. Formulaires
5. Cartes
6. Puis les autres onglets

Pour chaque objectif, il faut produire :

- objectif utilisateur clair
- checks techniques
- checks fonctionnels
- statut `ok`, `warning`, `degraded`, `critical`
- preuves de réussite
- auto-heal possible
- limites à ne pas franchir
- procédure de test

## Tâche prioritaire actuelle

Implémenter le monitoring de l'objectif :

`## 4. Services / Concierge — Actions Déléguées`

Prompt détaillé prêt à utiliser :

`docs/PROMPT_CLAUDE_MONITORING_SERVICES.md`

État au 25 mai 2026 :

- Services / Concierge a déjà un premier commit de monitoring : `feat: monitoring Services/Concierge dans /api/admin/objectives`.
- Si ce bloc existe déjà et fonctionne, ne pas le refaire.
- Chantiers préparés ensuite :
  - `docs/PROMPT_CLAUDE_MONITORING_DOCUMENTS.md`
  - `docs/PROMPT_CLAUDE_MONITORING_FORMULAIRES.md`

Le but est d'ajouter ou compléter :

`GET /api/admin/objectives`

avec un bloc :

```json
{
  "objectives": {
    "services": {
      "status": "degraded",
      "checks": [],
      "subservices": {},
      "metrics": {},
      "auto_heal": []
    }
  }
}
```

## Sous-services Services / Concierge à surveiller

- SMS
- appel vocal
- email
- invitation visio
- compte-rendu / conclusions
- note / mémoire
- météo
- actualités
- recherche web
- lieux / commerces
- restaurants
- page web
- paiement
- vols
- hôtels
- secrétariat

## Contraintes fortes

Le monitoring ne doit jamais déclencher d'action réelle engageante.

Donc ne pas envoyer pendant un check :

- SMS réel
- appel réel
- email réel
- paiement Stripe
- réservation Duffel
- réservation hôtel
- réservation restaurant

Le monitoring doit seulement vérifier :

- fonctions présentes
- variables d'environnement présentes
- modules importables
- configuration cohérente
- dépendance optionnelle ou critique
- dernier état connu si disponible

## États attendus

- `ok` : objectif atteint
- `warning` : service optionnel absent ou profil incomplet
- `degraded` : service partiellement utilisable
- `critical` : objectif inutilisable ou action dangereuse possible

## Important

Stripe peut être absent sur le serveur fondateur sans être une panne critique.

Duffel peut être absent tant que les vols/hôtels ne sont pas activés en production.

Serper absent doit dégrader recherche web, lieux et restaurants, mais ne doit pas casser tout l'onglet Services.

Twilio absent est critique pour SMS/appels si ces actions sont promises à l'utilisateur.

## Réponse attendue après implémentation

Quand tu termines, indique :

- fichiers modifiés
- exemple JSON réel de `/api/admin/objectives`
- comment tester sans action réelle
- services `ok`, `warning`, `degraded`, `critical`
- ce qui reste à faire avant de passer à Documents
