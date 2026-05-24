# Prompt Claude — Monitoring Objectif Formulaires

Contexte : Claude/Flo peuvent avoir des chantiers actifs sur Services, Documents ou les fichiers UI. Ne touche pas aux fichiers sensibles sans vérifier `git status`, `git fetch`, puis les derniers commits.

Repo :

https://github.com/byakuyakutchiki/luna-server

Source de vérité :

- `docs/CAHIER_DES_CHARGES_MONITORING.md`
- Section `## 8. Formulaires — Assistant Administratif Intelligent`
- Méthode fondateur : `docs/METHODE_TRAVAIL_FONDATEUR.md`

## Vision produit

Formulaires doit être compris comme un **assistant administratif intelligent**.

L'utilisateur ne doit pas seulement téléverser un PDF. Il doit pouvoir donner à Luna un formulaire compliqué, et Luna doit l'aider à :

- comprendre le document ;
- détecter les champs ;
- récupérer les bonnes données dans le profil ou le porte-document ;
- pré-remplir intelligemment ;
- signaler les zones incertaines ;
- laisser l'utilisateur corriger ;
- signer seulement avec confirmation ;
- générer un PDF final prêt à envoyer ;
- conserver une trace dans l'historique.

Le but fondateur est clair : réduire la charge administrative sans créer de risque juridique ou de remplissage faux.

## Objectif utilisateur

L'objectif est atteint seulement si un utilisateur peut faire le parcours complet :

```text
upload formulaire → analyse IA/OCR → preview → autofill → correction → PDF final → download → historique
```

Un simple upload réussi ne suffit pas.

## Périmètre attendu

Le monitoring doit couvrir au minimum :

| Sous-objectif | Attendu utilisateur |
|---|---|
| Upload | PDF/image accepté avec limites propres |
| Analyse | Champs, libellés, groupes et positions détectés |
| Preview | L'utilisateur voit le formulaire avant validation |
| Profil | Les données connues sont lisibles depuis Redis/profil |
| Vault bridge | Les données autorisées du porte-document peuvent aider |
| Autofill | Luna propose des valeurs, sans les imposer silencieusement |
| Correction | Les champs incertains sont visibles et modifiables |
| Signature | Jamais automatique sans confirmation |
| Génération | PDF final généré et lisible |
| Download | Le fichier final est récupérable |
| Historique | Le formulaire traité est retrouvé ensuite |

## Checks techniques suggérés

Implémenter ou compléter un check `_check_objective_formulaires()` dans l'esprit des autres objectifs.

Il doit idéalement vérifier :

- router `form_filler` monté ;
- endpoints existants :
  - `/api/form-filler/analyze`
  - `/api/form-filler/preview/{session_id}`
  - `/api/form-filler/autofill/{session_id}`
  - `/api/form-filler/fill`
  - `/api/form-filler/download/{session_id}`
  - `/api/form-filler/profile`
  - `/api/form-filler/history`
- import des modules `core.form_filler.routes`, `engine`, `redis_ops` ;
- disponibilité PyMuPDF/PIL si le code les utilise ;
- Redis accessible pour sessions/profil/historique ;
- présence de limites de taille/type fichier ;
- existence d'un chemin de fallback manuel quand l'IA ne reconnaît pas un champ.

## Checks fonctionnels suggérés

Prévoir un scénario de test sans document réel sensible :

1. Créer ou utiliser un formulaire test factice.
2. L'envoyer dans `/api/form-filler/analyze`.
3. Vérifier qu'un `session_id` existe.
4. Vérifier que la preview est disponible.
5. Vérifier que l'autofill retourne au moins une suggestion si le profil test est non vide.
6. Vérifier que les champs incertains restent visibles/corrigeables.
7. Générer un PDF final.
8. Télécharger le PDF.
9. Vérifier que l'historique contient l'entrée.

Le monitoring ne doit pas utiliser de CNI, facture ou document personnel réel.

## Statuts attendus

```text
ok
```

Parcours bout-en-bout disponible : analyse, preview, autofill, correction possible, génération PDF, download, historique.

```text
warning
```

Profil vide, peu de suggestions, ou formulaire test très simple, mais le remplissage manuel reste possible.

```text
degraded
```

IA, Vault ou Redis partiellement indisponible, mais fallback manuel ou profil local utilisable.

```text
critical
```

Impossible d'analyser, de générer ou de télécharger le PDF final.

## Auto-heal attendu

Le monitoring doit proposer des réparations ciblées :

| Problème | Auto-heal / réponse attendue |
|---|---|
| PDF image non remplissable | OCR/conversion puis overlay |
| Champ non reconnu | Liste de correction manuelle |
| Profil vide | Proposer saisie profil ou scan document |
| Vault indisponible | Fallback profil, statut `degraded` |
| Session expirée | Demander ré-upload clair |
| PDF corrompu/protégé | Message propre + pas de crash |
| Donnée ambiguë | Demander confirmation utilisateur |

## Limites à respecter

- Ne jamais signer sans confirmation explicite.
- Ne jamais envoyer le formulaire à un tiers sans validation humaine.
- Ne jamais cacher les champs incertains.
- Ne pas logger les données sensibles extraites.
- Ne pas considérer l'objectif atteint si seul l'upload marche.
- Ne pas toucher à `static/index.html` dans ce chantier.

## Sortie souhaitée

Merci de produire :

1. Le code du check monitoring Formulaires.
2. Les champs JSON retournés par `/api/admin/objectives`.
3. Les statuts `ok/warning/degraded/critical`.
4. Les auto-heal proposés.
5. Un résumé des fichiers modifiés.
6. Une note si un test réel nécessite une fixture PDF factice.

