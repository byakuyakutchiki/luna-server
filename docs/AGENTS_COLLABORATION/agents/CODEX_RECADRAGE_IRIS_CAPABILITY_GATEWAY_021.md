# Codex — Recadrage Iris Capability Gateway — Objectif 021

Date : 2026-06-02  
Agent : Codex  
Type : cadrage produit / coordination equipe

---

## Verdict

Ludovic a raison : Iris ne doit pas etre limitee a un ecran visuel. Le Command Screen est seulement la surface. Le vrai produit, c'est le **Capability Gateway** : un registre d'outils internes/externes, avec rendu visuel et garde-fous.

Le serveur contient deja beaucoup de briques : recherche web, lieux, meteo, news, documents, contacts, Twilio, carte, session Iris Teams. Le probleme restant est le branchement lisible et verifiable entre l'intention utilisateur, l'outil appele, le rendu visuel et la validation.

---

## Ce qui est interdit maintenant

- Dire a Ludovic "c'est bon" si Iris affiche seulement du texte.
- Coder un nouvel ecran isole qui n'est pas utilise dans `/simli`.
- Repondre "je n'ai pas acces" quand un outil existe.
- Lancer SMS, email, appel, invitation ou reservation sans validation owner.
- Deployer une action visible sans audit Kimi/DeepSeek et validation Ludovic.

---

## Scope a donner a Claude apres audits

Claude ne doit pas faire une refonte au hasard. La V1 attendue est :

1. brancher les outils lecture/recherche existants a Iris Audio/Command Screen ;
2. transformer les resultats en `research_board`, `data_board`, `document_insight`, `map_board`, `action_board` ;
3. afficher la cause exacte si l'outil manque ou echoue ;
4. garder toutes les actions sensibles en validation_required ;
5. faire un test par capacite avant deploy.

---

## Message canal

Agent : Codex  
Objectif : 021  
Type : recadrage produit / coordination  
Résumé : Iris Command Screen n'est pas suffisant. Nouvelle cible : Iris Capability Gateway. Iris doit relier recherche externe, documents internes, map, Twilio/actions, Teams et rendu visuel, avec garde-fous. Une capacite est livree seulement si outil backend + appel Iris + retour verifiable + render_type + validation sont tous OK. Kimi doit cadrer UX gateway, DeepSeek auditer outils/gaps, Claude attend scope Codex avant code.  
Fichier concerné : docs/AGENTS_COLLABORATION/OBJECTIF_021_IRIS_CAPABILITY_GATEWAY.md  
Risque : eleve si l'equipe continue a livrer des panneaux jolis mais non branches aux outils reels  
Décision Ludovic requise : oui avant deploy visible/action sensible  
Action proposée : Kimi + DeepSeek livrent audits 021 gateway, puis Codex donne consigne executable a Claude.

