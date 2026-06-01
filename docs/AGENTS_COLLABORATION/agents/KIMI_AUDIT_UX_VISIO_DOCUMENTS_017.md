# Kimi — Audit UX visio + Documents — Objectif 017

Date : 2026-06-01
Agent : Kimi
Type : audit UX / risque
Niveau : 0

---

## 1. Visio — Ressenti utilisateur et position UX

### 1.1 Ce que dit le terrain (Ludovic)

| Critère | Verdict terrain | Seuil acceptable V1 |
|---|---|---|
| Voix féminine française naturelle | ❌ Bizarre, non naturelle | Acceptable = pas de robotique flagrante |
| Fluidité conversationnelle | ❌ Mauvaise | < 4 s tour complet |
| Latence perçue | ❌ Lente | < 3 s première réponse |
| Comprend ce que dit Ludovic | ❌ Non | 100 % sur phrases standard |
| Répond à la question posée | ❌ Non | 100 % pertinence |
| N'émet pas "je ne comprends pas" en boucle | ❌ Échoue | 0 % en phrases standard |
| Expérience secrétaire crédible | ❌ Non | Au moins chaleureuse + compétente |

### 1.2 Diagnostic UX des maillons (sans preuve de code)

La boucle technique dans `static/simli.html` est :

```
Web Speech API (fr-FR) → POST /api/chat → LLM → ElevenLabs TTS (Camille) → AudioElement → Simli avatar
```

| Maillon | Hypothèse UX | Impact ressenti |
|---|---|---|
| **Web Speech API** | `interimResults: false`, `continuous: true` — la détection est "tout-ou-rien". Si le navigateur coupe mal les phrases, le LLM reçoit du bruit ou du silence. | Luna "ne comprend pas" alors que Ludovic parle clairement. |
| **Latence LLM + TTS** | Séquentiel : STT attend fin de phrase → POST → LLM génère → TTS génère MP3 → télécharge → joue. Somme probable > 4 s. | Attente gênante entre question et réponse. L'utilisateur ne sait pas si Luna a entendu. |
| **Voix Camille** | Test API ElevenLabs HTTP 200, MP3 FR natif, 2.4 mots/s. Mais le rendu final passe par un `<audio>` joué dans un WebView mobile. La compression ou le buffer peuvent dégrader. | Voix "bizarre" malgré une source théoriquement bonne. |
| **Feedback visuel** | Pas d'indicateur "Luna écoute..." ou "Luna réfléchit..." visible dans la capture ADB. | Silence ambigu = l'utilisateur repose la question ou croit au plantage. |
| **Anti-boucle audio** | `_irisAudio.onplay` active le micro seulement après `audio_play_end`. C'est correct en théorie. | Si le timing est légèrement décalé, Luna peut s'écouter elle-même ou perdre le début de la réponse utilisateur. |

### 1.3 Position Kimi — NON VALIDÉ

La visio **ne sera pas validée** tant que :
1. Les logs `speech_start → total_latency_ms` d'un test réel ne prouvent pas un tour < 4 s.
2. Ludovic ne confirme pas avoir entendu une réponse pertinente à "Je m'appelle Ludovic. Qui suis-je ?"
3. Aucun indicateur visuel/sonore de "j'ai entendu" n'est ajouté.

**Recommandation immédiate** (avant tout patch voix/CSS) :
- Codex doit capturer `visio_realtime_capture.ps1` + console WebView.
- DeepSeek doit auditer si le POST `/api/chat` reçoit bien le texte STT et si la réponse LLM est pertinente.
- Claude ne doit patcher QUE le maillon identifié comme cassé par la matrice preuve → cause.

---

## 2. Documents — Gap mobile vs cible porte-document

### 2.1 Écran mobile actuel (`static/index.html`, onglet Documents)

Composants visibles :
- 4 compteurs `Total / En attente / En retard / Régle` (tous à 0 à vide)
- Champ recherche + bouton `Scanner`
- 1 filtre `Tous`
- État vide : "Aucun document scanné"
- Section repliée `<details>` : "Documents générés par Luna" (formulaire de génération + liste v1)

### 2.2 Écran cible (`static/documents.html`, v2 desktop)

Composants visibles :
- Summary banner avec message contextuel + actions
- Stats row : `Urgent` / `À traiter` / `À jour` (avec code couleur rouge/jaune/vert)
- Grille actions urgentes (`urgent-grid`)
- Catégories scrollables avec compteurs (`cats-row`)
- Timeline des documents (`timeline-list`)
- Détail modal avec actions exécutables
- Routes : `/api/documents/v2/dashboard`, `/timeline`, `/categories`, `/actions/{doc_id}`, `/actions/execute`

### 2.3 Matrice de gap

| Cible porte-document | Mobile actuel | Desktop v2 | Écart |
|---|---|---|---|
| Répertoires (Identité, Santé, Finances, etc.) | ❌ Absent | ✅ `/api/documents/v2/categories` | **Majeur** — l'onglet mobile n'appelle pas le v2 |
| Dashboard contextuel | ❌ 4 compteurs vides | ✅ Summary banner + stats | **Majeur** — pas de narration à l'état vide |
| Timeline | ❌ Absente | ✅ `/api/documents/v2/timeline` | **Majeur** |
| Actions urgentes | ❌ Absentes | ✅ Urgent grid + actions exécutables | **Majeur** |
| État vide utile | ❌ "Aucun document scanné" | ✅ Message + CTA scan | **Majeur** — l'état vide ne promet rien |
| Carte détail document | ❌ Non testable | ✅ Modal avec résumé, organisme, échéance | Majeur |
| Documents générés par Luna | ✅ Replié dans `<details>` | ❌ Pas dans documents.html | Confusion UX — deux concepts mélangés |

### 2.4 Hypothèse racine

L'onglet mobile Documents dans `static/index.html` appelle :
- `/api/documents` (v1 — liste brute)
- `/api/secretary/documents` (API secrétaire)

Il n'appelle **jamais** `/api/documents/v2/*`.

Le backend v2 existe (`luna_web.py` lignes 16865+). Le frontend v2 existe (`static/documents.html`).
Mais l'onglet mobile est resté sur l'ancienne surface v1.

### 2.5 Proposition UX Kimi — Documents mobile

**Principe** : Ne pas régresser le style Luna. Surface le v2 existant.

**État vide (priorité P1)** :
Remplacer "Aucun document scanné" par :
```
🗂️  Votre porte-document
    
    Scannez vos papiers, Luna les classe,
    retrouve les urgences et vous rappelle
    quoi faire.
    
    [ 📷 Scanner mon premier document ]
```

**Dashboard mobile (P1)** :
Rendre les 4 compteurs cliquables et narratifs :
- Si 0 partout : afficher un CTA scan au lieu de 4 zéros tristes.
- Si >0 : colorer `En retard` en rouge, `En attente` en jaune, `Régle` en vert.
- Ajouter un 5e compteur `Urgent` (rouge) si le v2 le fournit.

**Navigation par catégories (P2)** :
Remplacer le filtre unique `Tous` par une barre scrollable de catégories
(Identité 🪪, Santé 🏥, Finances 💰, Domicile 🏠, Véhicule 🚗, Administratif 📋, Factures 💡, Urgence 🚨).
Même à 0 document, les catégories doivent être visibles (promesse du porte-document).

**Séparation concepts (P2)** :
- `Porte-document` = documents scannés/uploadés par Ludovic, classés par Luna.
- `Documents générés par Luna` = courriers, résumés, etc. produits par l'IA.
Ne pas les mélanger dans le même `<details>`. Deux onglets ou deux sections bien distinctes.

**Recommandation technique** :
Claude ne doit PAS réécrire un nouveau documents.html mobile.
Il doit brancher l'onglet mobile sur les routes v2 existantes (`/api/documents/v2/*`)
et adapter le CSS au conteneur mobile (max-width, padding, safe-area).
C'est un patch niveau 1 (surfacage UI + branchement route existante).

---

## 3. Synthèse décision

| Sujet | Validé UX Kimi | Prochaine étape |
|---|---|---|
| Visio | ❌ **NON** | Attendre capture Codex + matrice preuve → cause |
| Documents mobile | ❌ **NON** | DeepSeek cartographie routes v2 → Claude branche l'onglet |
| Voix Camille seule | ⚠️ Théoriquement OK, terrain KO | Ne pas patcher isolément |
| CSS avatar seul | ⚠️ Théoriquement OK, terrain KO | Ne pas patcher isolément |

---

## 4. Action proposée

1. **Codex** : lancer `visio_realtime_capture.ps1` avec les 5 phrases standard. Produire matrice preuve → cause → correctif.
2. **DeepSeek** : vérifier dans `static/index.html` pourquoi l'onglet Documents n'appelle pas `/api/documents/v2/*`. Cartographier les appels existants.
3. **Claude** : attendre. Ne coder que le maillon identifié par la matrice (visio) ou le branchement v2 (documents).
4. **Ludovic** : ne pas déployer. Garder le téléphone prêt pour le prochain test court Codex.
