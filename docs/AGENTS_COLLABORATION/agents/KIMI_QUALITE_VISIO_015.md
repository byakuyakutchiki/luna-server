# Kimi — Qualité voix/image visio — Objectif 015

**Agent** : Kimi (qualité terrain + crédibilité humaine)  
**Date** : 2026-05-31  
**Statut** : livré — en attente décisions Ludovic  
**Référence** : `OBJECTIF_015_VISIO_TEMPS_REEL_QUALITE.md`, `CODEX_TERRAIN_VERDICT_VISIO_AFTER_TTS_FIX_014.md`, `CLAUDE_DIAGNOSTIC_STT_IMAGE_014.md`

---

## 1. Verdict sur la voix actuelle

**Verdict : NON ACCEPTABLE pour produit.**

La voix actuelle (`ELEVENLABS_VOICE_ID=6BlZrFdruL4hpXFHmHUC`, "Alice") est fonctionnelle — elle parle, elle sort du haut-parleur. Mais elle casse la promesse "secrétaire visio crédible" sur 4 points irréductibles :

| Défaut | Impact sur la promesse |
|---|---|
| **Accent anglais prononcé** | On entend immédiatement que ce n'est pas une française. Le "R" est anglais, les voyelles sont plates. |
| **Voix lourde / pâteuse** | Perçue comme "en crise" ou robotique avancée, pas humaine. La lenteur renforce l'impression de machine. |
| **"Iris" prononcé "Riff"** | La voix anglaise ne sait pas dire "Iris" en français. Résultat : l'utilisateur ne comprend pas le nom de l'assistante. Identité cassée. |
| **Latence ressentie** | Le délai entre la fin du `firstMessage` et l'écoute réelle est long, donnant l'impression d'un monologue, pas d'une conversation. |

**Position Kimi** : Alice est une voix anglophone qui lit du français. `elevenlabsLanguageCode=fr` ne change pas l'accent natal de la voix. C'est comme demander à un anglophone de parler français — on comprend, mais ce n'est pas crédible comme secrétaire française. Il faut une voix **française native**.

---

## 2. Trois voix féminines FR candidates

Sélection parmi la galerie ElevenLabs publique. Critère de pré-sélection : voix **nativement française**, pas anglophone avec paramètre `languageCode=fr`.

### Candidate A — Camille (recommandée)

| Attribut | Valeur |
|---|---|
| **Voice ID** | `Z9ZHGvFZ90R0h0x1prsJ` |
| **Description ElevenLabs** | "Warm, expressive, unmistakably French. Ideal for storytelling, ads." |
| **Profil** | Jeune adulte, chaleureuse, expressive, parfaitement française. |
| **Pourquoi elle** | Accent 100% natif FR. Ton accueillant mais pas trop familier. "Unmistakably French" = exactement ce qu'on cherche. Expressive = capable de nuances conversationnelles. |
| **Risque** | Peut être légèrement trop "storytelling" pour une secrétaire. À valider sur la phrase de test. |

### Candidate B — Camille Martin (alternative professionnelle)

| Attribut | Valeur |
|---|---|
| **Voice ID** | `hFgOzpmS0CMtL2to8sAl` |
| **Description ElevenLabs** | "Calm and deep. Ideal for corporate, audiobooks." |
| **Profil** | Adulte mature, calme, posée, professionnelle. |
| **Pourquoi elle** | Si Camille A est trop expressive, Camille Martin apporte la sobriété d'une secrétaire senior. Voix profonde = crédibilité + autorité douce. |
| **Risque** | Peut manquer de chaleur pour une première impression. À valider sur la phrase de test. |

### Candidate C — Anaïs (alternative neutre)

| Attribut | Valeur |
|---|---|
| **Voice ID** | `5OnMHwgTFgvPVwE8jP6B` |
| **Description ElevenLabs** | "Middle aged French. Warm and clear. Podcast, e-learning, news." |
| **Profil** | Femme d'expérience, claire, chaleureuse, neutre. |
| **Pourquoi elle** | Le ton "e-learning/news" = articulation parfaite, clarté maximale. Pas de fioriture. Si Ludovic préfère une voix discrète et efficace. |
| **Risque** | Peut être perçue comme trop "institutionnelle" (radio/TV) pour une assistante personnelle. |

### Voix écartées (et pourquoi)

| Voice ID | Nom | Raison d'écart |
|---|---|---|
| `6BlZrFdruL4hpXFHmHUC` | Alice (actuelle) | Anglophone. Accent EN prononcé. "Iris" -> "Riff". |
| `21m00Tcm4TlvDq8ikWAM` | Rachel | Anglophone (voix EN par défaut du code). |
| `CKfuQaJKfvUG2Wtrda3Y` | Lison | "Naturally seductive" — trop séductrice pour une secrétaire professionnelle. |
| `FvmvwvObRqIHojkEGh5N` | Adina | "Young professional... social media" — trop jeune, trop dynamique, pas assez chaleureuse. |
| `sEk5ftjVl91hHjtOlmK1` | Lise | "Calm storyteller" — très douce, mais peut manquer de présence pour une conversation interactive. |

---

## 3. Phrase de test unique

### Pourquoi une phrase unique

Pour comparer objectivement 3 voix, il faut le **même texte** lu par chacune. Sinon on compare des apples et des oranges. La phrase doit tester :
- Les sons français difficiles pour un anglophone (R, U, ON, IN)
- La fluidité conversationnelle
- La prononciation du nom "Iris" (le point de friction actuel)
- Le ton chaleureux + professionnel

### La phrase

> **"Bonjour Ludovic, c'est Iris. Je vous entends bien. Comment puis-je vous aider aujourd'hui ?"**

### Ce que cette phrase teste

| Mot/son | Ce qui est testé |
|---|---|
| "Bonjour" | Son "R" français (uvulaire), pas roulé, pas anglais |
| "Ludovic" | Prénom de l'utilisateur — la voix doit le dire naturellement |
| "Iris" | Le nom problématique — doit être "I-ris", pas "Riff" |
| "entends" | Son "an" nasal français |
| "bien" | Son "ien" — fluidité |
| "Comment" | Son "om" — rondeur |
| "aujourd'hui" | Mot complexe, long, conversationnel — teste le rythme |

### Procédure de test

1. Aller sur [elevenlabs.io](https://elevenlabs.io) -> Voice Library (pas besoin de compte payant pour écouter les previews)
2. Rechercher "Camille", "Camille Martin", "Anaïs"
3. Coller la phrase exacte dans le champ texte
4. Écouter chaque preview
5. Noter sur les 5 critères (section 4)
6. Choisir la meilleure

**Temps estimé** : 5 minutes. **Coût** : 0€ (previews gratuits).

---

## 4. Critères de choix — grille d'évaluation

| Critère | Poids | Description | Comment évaluer |
|---|---|---|---|
| **Accent FR natif** | 25% | Accent français pur, sans trace anglaise. "R" uvulaire, voyelles pleines. | Écouter "Bonjour" et "Iris". Si on entend du EN -> 0/10. |
| **Naturel** | 25% | On oublie que c'est une machine. Pas de vibration artificielle, pas de débit robotique. | Écouter la phrase entière. Se demander : "Est-ce que je pourrais entendre ça au téléphone sans me douter ?" |
| **Rythme** | 20% | Débit fluide, pauses aux bons endroits, pas haché, pas accéléré. | "Comment puis-je vous aider" doit couler, pas être une suite de mots séparés. |
| **Chaleur** | 15% | Ton amical, accueillant, humain. Pas froid, pas distant. | La voix doit donner envie de continuer la conversation. |
| **Professionnalisme** | 10% | Claire, articulée, crédible comme secrétaire. Pas trop familière, pas trop rigide. | "Je vous entends bien" doit sonner compétent, pas copain. |
| **Prononciation "Iris"** | 5% | Dit correctement en français. | "I-ris" avec un "I" clair et un "ris" français. Pas "Riff", pas "Air-ris". |

**Score minimum pour validation** : 7/10 sur chaque critère, avec au moins 8/10 sur "Accent FR natif" et "Naturel".

---

## 5. Proposition image/avatar — sans distorsion

### Diagnostic de la distorsion actuelle

Claude a identifié 2 causes dans `static/simli.html` :

1. **`.phone-avatar-frame iframe`** (ligne 125) : `transform: scale(1.5)` — ce n'est que la miniature dans le téléphone de la cinématique. Elle disparaît quand on passe en plein écran.
2. **`#tavusFrame iframe`** (lignes 167-172) : a DÉJÀ un patch ratio 9:16 (`width: min(100vw, calc(100vh * 9/16))`). **Mais** ce patch est appliqué sur le conteneur iframe, pas sur la vidéo elle-même.

### Pourquoi l'avatar reste distordu malgré le patch

Le patch ratio 9:16 est correct en théorie, mais il suppose que l'avatar Simli est en format portrait (9:16). Or :
- Le `faceId` actuel (`b9e5fba3...`) est un avatar générique Simli
- Les avatars Simli peuvent avoir des ratios variables selon la source (photo uploadée, générée, etc.)
- Si l'avatar source est en 16:9 ou 4:3, forcer un conteneur 9:16 crée du letterboxing noir ou de la compression

### Proposition Kimi — 3 niveaux

#### Niveau 1 : CSS sans changement d'avatar (patch immédiat)

Remplacer le conteneur iframe actuel par une règle plus souple :

```css
#tavusFrame iframe {
  border: none;
  /* Ne pas forcer 9:16 — laisser la vidéo s'adapter à son propre ratio */
  width: 100%;
  height: 100%;
  object-fit: contain; /* ou cover selon le cas */
}
```

**Problème** : `object-fit` ne fonctionne pas sur un `iframe`. Il faut l'appliquer sur l'élément `<video>` à l'intérieur de l'iframe, ce qui est contrôlé par Daily.js/Simli, pas par notre CSS.

**Solution réaliste** : Utiliser `DailyIframe.createFrame()` avec une option de style qui force le ratio, OU ajouter un wrapper CSS :

```css
#tavusFrame {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
}
#tavusFrame iframe {
  border: none;
  /* Le iframe prend tout l'espace, mais la vidéo interne gère son propre ratio */
  width: 100%;
  height: 100%;
}
```

Mais cela ne résout pas le problème si Simli envoie une vidéo déjà étirée.

#### Niveau 2 : Choisir un avatar Simli au ratio portrait stable

Aller sur le dashboard Simli -> Faces -> filtrer "Female" -> choisir un avatar dont l'aperçu montre un format portrait (tête et épaules, pas paysage). Noter le `faceId`.

**Avantage** : rapide, pas de code complexe.  
**Inconvénient** : dépend de la qualité des avatars Simli disponibles.

#### Niveau 3 : Avatar personnalisé Luna (à long terme)

Uploader une photo de référence Luna (disponible dans `docs/assets/luna_avatar_sources/`) dans Simli pour générer un avatar personnalisé. Simli permet d'uploader des photos pour créer des avatars custom.

**Avantage** : Luna ressemble à Luna. Ratio contrôlé.  
**Inconvénient** : coût potentiel, délai de génération, nécessite un compte Simli avec accès custom avatar.

### Recommandation Kimi

1. **Immédiat** : Tester si la distorsion persiste avec un `faceId` Simli différent (format portrait). Si oui -> le problème est CSS/iframe. Si non -> le problème est l'avatar.
2. **Court terme** : Choisir un `faceId` féminin portrait stable dans la galerie Simli.
3. **Moyen terme** : Avatar personnalisé Luna quand la voix et le STT sont validés.

**Note** : La distorsion ne doit PAS être corrigée par un patch CSS au hasard sans diagnostic. Claude doit d'abord instrumenter pour savoir si c'est le conteneur, la vidéo Daily.js, ou l'avatar source.

---

## 6. Décisions Ludovic requises

### Décision 1 — Voix (niveau 2, bloquante)

**Question** : Quelle voix française native choisir pour Iris ?

| Option | Voice ID | Ton |
|---|---|---|
| A — Camille | `Z9ZHGvFZ90R0h0x1prsJ` | Chaleureuse, expressive, française |
| B — Camille Martin | `hFgOzpmS0CMtL2to8sAl` | Calme, profonde, professionnelle |
| C — Anaïs | `5OnMHwgTFgvPVwE8jP6B` | Claire, neutre, institutionnelle |

**Action** : Écouter les 3 previews sur ElevenLabs avec la phrase de test (5 min). Choisir une. Kimi configure Cloud Run.

### Décision 2 — Nom (niveau 2, bloquante)

**Question** : L'assistante visio s'appelle Iris ou Luna ?

| Option | Avantage | Inconvénient |
|---|---|---|
| **Iris** | Nom distinct de Luna = rôle clair (secrétaire). Pas de confusion. | L'utilisateur clique sur "Visio avec Luna" et entend "Iris". |
| **Luna** | Cohérence totale. L'utilisateur parle à Luna. | Luna devient secrétaire ET compagnon IA. Rôle moins clair. |
| **"Iris, secrétaire de Luna"** | Les deux. Clarté + cohérence. | Plus long à prononcer. |

**Impact voix** : Si on garde "Iris", la nouvelle voix française native la prononcera correctement ("I-ris"). Si on change pour "Luna", c'est encore mieux ("Luna" est facile à prononcer dans toutes les langues).

**Recommandation Kimi** : Choisir **un seul nom** et l'appliquer partout (écran, prompt, firstMessage, barre d'actions). L'incohérence actuelle casse la crédibilité.

### Décision 3 — Image (niveau 2, non bloquante)

**Question** : Corriger l'image en même temps que la voix, ou après validation STT ?

| Option | Quand | Pourquoi |
|---|---|---|
| En même temps | Dès que la voix est choisie | Si l'image reste distordue, le test terrain sera faussé. |
| Après STT | Une fois que Iris entend et répond | Éviter de changer 2 variables en même temps. |

**Recommandation Kimi** : Corriger l'image **en même temps** que la voix, car un avatar distordu invalide le test terrain même si la voix est parfaite. Le changement de `faceId` est une seule ligne de code + env var.

### Décision 4 — Test terrain (niveau 2)

**Question** : Quand faire le test terrain ?

**Procédure proposée** :
1. Ludovic choisit voix + nom
2. Kimi met à jour Cloud Run (`ELEVENLABS_VOICE_ID` + `SIMLI_FACE_ID` si changé)
3. **Claude corrige d'abord le bug micro/STT** (race condition `allow="microphone"`) — c'est P0
4. Ludovic fait un test visio de **30 secondes max** :
   - Écouter le `firstMessage`
   - Dire "Tu m'entends ?"
   - Attendre une réponse pertinente
   - Raccrocher
5. Verdict immédiat : voix OK / pas OK + entendue / pas entendue

**Règle** : Si Iris n'entend pas -> on ne teste pas la voix plus longtemps. On corrige le STT d'abord.

---

## 7. Résumé actionnable

| Priorité | Action | Qui | Quand |
|---|---|---|---|
| P0 | Ludovic écoute 3 previews ElevenLabs + choisit voix + nom | Ludovic | Maintenant (5 min) |
| P0 | Claude corrige race condition micro/Daily.js (`allow` avant `join`) | Claude | Dès que possible |
| P1 | Kimi met à jour `ELEVENLABS_VOICE_ID` + nom sur Cloud Run | Kimi | Après choix Ludovic |
| P1 | Test terrain 30s : voix + STT + réponse | Ludovic | Après fix micro + voix |
| P1 | Choisir `faceId` portrait stable OU corriger CSS distorsion | Kimi/Claude | En parallèle voix |
| P2 | Avatar personnalisé Luna | Tous | Après visio fonctionnelle |

---

*Kimi — garde qualité. Aucun déploiement, aucune session Simli, aucun crédit consommé.*

---

## 8. Mise à jour post-audit Codex logs (2026-05-31)

**Lu** : `CODEX_LOG_ANALYSIS_VISIO_015.md`

### Ce qui a été prouvé par les logs terrain

| Élément | Statut | Preuve |
|---|---|---|
| Micro local publié | ✅ OK | `probe_local_audio playable` |
| Bot Simli rejoint | ✅ OK | `bot_joined` |
| Audio bot sortant | ✅ OK | `probe_bot_audio playable` |
| SpeechRecognition navigateur | ✅ OK | `speech_captured "est-ce que tu m'entends"` |
| STT Simli natif | ❌ KO | Aucun `stt_user_utterance` remonté |
| Réponse conversationnelle | ❌ KO | `conversation.echo` ne déclenche pas de vraie réponse Simli |
| Vision caméra | ❌ KO | `vision_no_track camera non disponible` |
| Pont STT local | ❌ DANGER | Capte la voix d'Iris → risque de boucle. Désactivé par Codex. |

### Impact sur mon verdict voix/image

**Je maintiens mon verdict : la voix Alice est NON ACCEPTABLE.**

**Mais je rajoute une condition : même si on change pour Camille/Anaïs, l'expérience visio reste NON VALIDÉE tant que le STT n'est pas prouvé.**

Une belle voix française qui parle dans le vide (monologue sans écoute) n'est pas une secrétaire visio. C'est un lecteur audio avec un avatar.

### Position Kimi actualisée

1. **Voix** : choisir Camille/Anaïs **en préparation**, mais ne pas déployer seule pour un test "est-ce que ça parle mieux". Le test voix n'a de sens que si Simli écoute et répond.
2. **Image** : corriger la distorsion **en préparation**, mais ne pas valider l'avatar propre comme un succès. Un avatar beau qui ne répond pas = gadget.
3. **STT** : c'est le vrai P0. La voix et l'image sont P1 jusqu'à preuve de conversation.

### Recommandation pour Ludovic

**Ne pas tester les voix une par une sur Simli auto.** Chaque test coûte des crédits Simli pour un résultat connu d'avance : la voix sort, mais Iris n'écoute pas.

**Attendre que Claude/DeepSeek tranchent l'architecture avant de choisir la voix définitive.** La voix idéale pour Simli SDK/WebRTC (Option B) ou LiveKit/Pipecat (Option C) peut différer de celle pour Simli auto (Option A). Par exemple, en Option B/C, ElevenLabs est appelé directement par notre code — on a plus de contrôle sur le débit, les pauses, le style. En Option A, Simli contrôle le TTS et on ne peut pas ajuster.

### Décisions à reporter

| Décision | Avant les logs | Après les logs |
|---|---|---|
| Choisir voix FR | Urgent | Préparation seule — attendre architecture |
| Choisir nom Iris/Luna | Urgent | Préparation seule — attendre architecture |
| Corriger image | Court terme | Court terme — indépendant de l'architecture |
| Déployer quoi que ce soit | Jamais sans validation | **Jamais sans preuve STT + validation** |

---

*Mise à jour après lecture CODEX_LOG_ANALYSIS_VISIO_015.md. Position inchangée : voix = préparation, expérience = non validée.*
