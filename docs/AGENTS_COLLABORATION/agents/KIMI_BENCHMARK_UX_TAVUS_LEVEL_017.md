# Kimi — Grille UX benchmark Tavus-level — Objectif 017

Date : 2026-06-01
Agent : Kimi
Type : benchmark UX / référence produit
Niveau : 0

Source benchmark : `docs/AGENTS_COLLABORATION/agents/CODEX_AUDIT_WEB_TAVUS_BENCHMARK_017.md`

---

## Principe

Tavus CVI n'est pas une fonctionnalité, c'est une **expérience**.
La grille ci-dessous traduit les capacités Tavus en critères UX mesurables pour Luna.
Chaque critère est noté sur une échelle de 0 à 5 :
- **0** = Absent / cassé
- **1** = Présent mais inutilisable
- **2** = Fonctionne parfois, frustrant
- **3** = Acceptable V1 (seuil minimum livrable)
- **4** = Bon, crédible comme secrétaire
- **5** = Excellent, niveau Tavus perçu

---

## Grille UX Tavus-level pour Luna

### A. Voix et parole (Tavus : TTS configurable, naturelle, vivante)

| # | Critère | Définition UX | Seuil V1 (3/5) | Luna actuel | Score |
|---|---|---|---|---|---|
| A1 | **Genre et langue** | Voix féminine, français natif, sans accent étranger. | Français natif reconnaissable. | Camille FR natif (ElevenLabs) test API OK. Rendu final terrain = bizarre. | 2 |
| A2 | **Débit** | Vitesse de parole humaine, ni hachée ni traînante. | 2-3 mots/s, pauses naturelles. | 2.4 mots/s en théorie. Buffer/WebView peut dégrader. | 2 |
| A3 | **Prosodie** | Intonations, montées/descentes, énergie adaptée au contenu. | Pas monotone, pas robotique. | Monotonie perçue terrain. Manque d'énergie. | 1 |
| A4 | **Chaleur** | Sensation d'humain bienveillant, pas froid ni dépressif. | Accueillante, professionnelle. | "Énergie dépressive" rapportée. | 1 |
| A5 | **Clarté phonique** | Pas de distorsion, pas de coupe, pas d'artefacts. | Compréhension sans effort. | Qualité dégradée par pipeline/buffer inconnu. | 2 |

**Sous-total A :** 8/25 — **Non atteint.**

### B. Réactivité et latence (Tavus : pipeline intégré, faible latence ressentie)

| # | Critère | Définition UX | Seuil V1 (3/5) | Luna actuel | Score |
|---|---|---|---|---|---|
| B1 | **Détection parole** | Temps entre "Ludovic commence à parler" et "Luna sait qu'il parle". | < 800 ms perçu. | Web Speech API — pas de preuve temps réel. | 1 |
| B2 | **Première réponse audible** | Temps entre fin de phrase utilisateur et début audio Luna. | < 3 s. | Structurellement STT + POST + LLM + TTS + DL. Probablement > 4 s. | 1 |
| B3 | **Tour complet moyen** | Durée moyenne d'un échange question-réponse. | < 4 s. | Non mesuré. Lenteur perçue terrain. | 1 |
| B4 | **Fluidité globale** | Pas de blanc gênant, pas de chevauchement, pas de coupures. | Conversations sans frustration. | Blanks, silences, "je ne comprends pas". | 1 |
| B5 | **Feedback d'écoute** | Indication visible/audible que Luna a entendu et réfléchit. | Au moins un indicateur discret. | Aucun indicateur visuel dans capture ADB. | 0 |

**Sous-total B :** 4/25 — **Non atteint.**

### C. Compréhension et dialogue (Tavus : STT temps réel, LLM, mémoire, outils)

| # | Critère | Définition UX | Seuil V1 (3/5) | Luna actuel | Score |
|---|---|---|---|---|---|
| C1 | **Transcription STT** | Ce que dit Ludovic arrive textuellement au LLM sans perte. | 95 % exact sur phrases standards. | "Ne comprend pas" rapporté. STT WebView probablement cassé. | 1 |
| C2 | **Compréhension sémantique** | Le LLM comprend l'intention, pas seulement les mots. | Réponses pertinentes aux 5 phrases test. | Non prouvé. | 1 |
| C3 | **Mémoire contextuelle** | Luna se souvient de l'appel en cours et des infos données. | Retient nom, sujet, consignes pendant l'appel. | Non testé. | 0 |
| C4 | **Identité utilisateur** | Sait que l'interlocuteur est Ludovic (si profil connu). | "Bonjour Ludovic" ou reconnaissance explicite. | Se présente mais peut dire "user" si profil absent. | 1 |
| C5 | **Action contextuelle** | Peut prendre une note, relancer, planifier sur demande. | "Prends une note" → note créée. | Non testé. | 0 |

**Sous-total C :** 3/25 — **Non atteint.**

### D. Avatar et présence visuelle (Tavus : Phoenix, micro-expressions, écoute active)

| # | Critère | Définition UX | Seuil V1 (3/5) | Luna actuel | Score |
|---|---|---|---|---|---|
| D1 | **Rendu fluide** | Pas de saccades, pas de distorsion, ratio correct. | Avatar visible sans artefact majeur. | Avatar visible. Distorsion possible selon Simli. | 2 |
| D2 | **Lip-sync** | Lèvres synchronisées avec l'audio. | Synchronisation approximative acceptable. | Non garanti par Simli avec notre pipeline. | 1 |
| D3 | **Écoute active** | L'avatar réagit visuellement quand Ludovic parle (hochements, regard). | Au moins un signe d'écoute. | Avatar figé pendant l'écoute. | 0 |
| D4 | **Expressivité** | Micro-expressions, émotions subtiles selon le contenu. | Neutre mais vivant, pas statue. | Statique. | 0 |
| D5 | **Cohérence visuo-audio** | Ce que dit Luna correspond à ce que montre l'avatar. | Pas de décalage jarring. | Audio et vidéo peuvent être désynchronisés. | 1 |

**Sous-total D :** 4/25 — **Non atteint.**

### E. Vision et multimodal (Tavus : Raven, perception audio/vidéo, environnement)

| # | Critère | Définition UX | Seuil V1 (3/5) | Luna actuel | Score |
|---|---|---|---|---|---|
| E1 | **Caméra active** | Luna voit le flux caméra de Ludovic. | Camera allumée, frame transmise. | Frame transmise toutes les 12s (320x240). | 2 |
| E2 | **Description simple** | Peut décrire ce qu'elle voit (couleur, mouvement, objet). | "Je vois une main" ou "un fond clair". | Non prouvé. `vision_no_track`. | 0 |
| E3 | **Contextualisation** | Intègre l'info visuelle dans la réponse conversationnelle. | "Je vois que tu es dans ta cuisine" (si pertinent). | Non prouvé. | 0 |
| E4 | **Confiance** | Ne prétend pas voir si elle ne voit pas. | Honnêteté sur les limites. | Non testé. | 0 |
| E5 | **Utilité** | L'info visuelle sert à quelque chose (action, réconfort, aide). | Au moins un cas utile démontré. | Non prouvé. | 0 |

**Sous-total E :** 2/25 — **Non atteint.**

---

## Synthèse scoring

| Domaine | Score | /25 | Seuil V1 |
|---|---|---|---|
| A. Voix et parole | 8 | 25 | ❌ |
| B. Réactivité et latence | 4 | 25 | ❌ |
| C. Compréhension et dialogue | 3 | 25 | ❌ |
| D. Avatar et présence | 4 | 25 | ❌ |
| E. Vision et multimodal | 2 | 25 | ❌ |
| **TOTAL** | **21** | **125** | ❌ |

**Score V1 minimum : 15/25 sur chaque domaine, soit 75/125 total.**
**Luna actuel : ~21/125 (17 % du seuil V1).**

---

## Position Kimi

**La visio Luna n'est pas à 80 % de la cible. Elle est à 17 % du seuil minimum acceptable.**

Ce n'est pas une question de "polish" ou de petits patchs CSS/voix.
C'est une question d'**architecture conversationnelle**.

**Ce qui ne suffira pas** (même combiné) :
- Changer la voix ElevenLabs
- Ajuster le `scale()` CSS de l'avatar
- Réparer la bulle "LUNA" en mobile
- Optimiser un prompt

**Ce qui serait nécessaire** pour atteindre Tavus-level :
- Pipeline STT fiable temps réel (pas Web Speech API WebView fragile)
- Streaming TTS (pas génération MP3 séquentielle)
- Latence maîtrisée end-to-end (< 2s idéalement)
- Avatar réactif à l'écoute (micro-expressions, lip-sync)
- Mémoire de conversation en temps réel
- Perception visuelle réelle et contextualisée

---

## Recommandations

### Court terme (Objectif 017)
1. **Codex** capture réelle avec `visio_realtime_capture.ps1`.
2. **DeepSeek** contre-audit architecture : Simli + pipeline Luna vs Tavus CVI vs pipeline maison (LiveKit/Pipecat).
3. **Claude** ne code **aucun patch** tant que le score est < 75/125.
4. **Ludovic** : garder le téléphone prêt, ne pas valider de déploiement.

### Moyen terme (Objectif 018+)
1. Si Simli + pipeline maison ne peut pas atteindre 3/5 sur A+B+C en 2-3 itérations, envisager **POC Tavus CVI** (offre gratuite, minutes limitées, test court contrôlé).
2. Si Tavus POC atteint > 3/5 sur A+B+C avec < 1h de config, documenter le delta coût/bénéfice pour décision Ludovic.
3. Ne **jamais** migrer complètement sans validation full-stack (voix FR, latence, coût, données).

---

## Fin de non-recevoir explicite

**Je ne validerai pas la visio Luna pour l'Objectif 017.**
Même si Codex prouve que le STT fonctionne parfois, même si Claude optimise le prompt, même si la voix est un peu mieux — le score global restera sous le seuil V1.

La prochaine validation UX Kimi sera possible uniquement si :
- Score A (voix) ≥ 12/25 **ET**
- Score B (réactivité) ≥ 12/25 **ET**
- Score C (compréhension) ≥ 12/25

Soit un total ≥ 75/125 avec minimum 12 sur les trois premiers domaines.

---

*Benchmark produit : Tavus CVI — https://www.tavus.io/cvi*
