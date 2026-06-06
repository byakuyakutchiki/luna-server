# Codex — Diagnostic Iris Command Screen Runtime — Objectif 033

Date : 2026-06-06
Agent : Codex
Type : diagnostic + patch minimal
Niveau : 1

## Constat Ludovic

Iris parle correctement en conversation, mais elle se detache de son Command Screen :

- elle dit parfois qu'elle ne peut pas afficher ou utiliser son panneau ;
- elle promet de preparer un tableau, un graphique ou un document sans rendre le resultat attendu ;
- le panneau s'ouvre parfois avec un squelette ou un diagnostic, mais pas avec un livrable professionnel ;
- les documents uploades sont lus/analysees, mais Iris ne se comporte pas comme une operatrice capable de transformer le document dans son espace de travail.

## Cause technique principale trouvee

La session vocale OpenAI etait configuree avec `turn_detection.create_response = true`.

Effet : OpenAI pouvait demarrer une reponse des que la parole utilisateur se terminait, avant que le serveur Luna ait recu la transcription finale, detecte le mode metier, mis a jour les tools autorises et impose le contrat Command Screen.

Donc le serveur pouvait faire :

1. utilisateur parle ;
2. OpenAI commence deja a repondre ;
3. seulement apres, le serveur recoit la transcription ;
4. seulement apres, le serveur detecte `tableau`, `graphique`, `document`, `recherche`, etc. ;
5. trop tard : Iris est deja partie en mode conversationnel.

C'est une course critique entre la voix et le routeur.

## Patch applique

Fichier : `integrations/openai/web_voice_bridge.py`

Changements :

1. `create_response` passe de `true` a `false`.
2. Quand la transcription utilisateur arrive, le serveur detecte d'abord le mode via `detect_mode_from_text`.
3. Le serveur appelle `set_mode(...)` si necessaire.
4. Ensuite seulement, le serveur declenche `response.create`.
5. Log ajoute : `WebVoice: response_created_after_mode mode=<mode>`.
6. Les auto-corrections de deni ICS couvrent maintenant tous les modes productifs, pas seulement `analyse`, `reunion`, `workspace`.
7. Les chemins `auto_correct_denial`, `document_uploaded` et `doc_action fallback` utilisent les tools filtres du mode actif au lieu de `VOICE_TOOLS` global.

## Pourquoi c'est important

Iris ne doit pas "decider" seule si elle a un panneau.

Le serveur doit imposer l'ordre :

```text
transcription utilisateur
-> detection mode
-> session.update avec tools filtres
-> response.create
-> tool_call
-> render
-> confirmation vocale courte
```

Avant le patch, l'ordre pouvait etre :

```text
parole utilisateur
-> response.create automatique
-> Iris parle
-> transcription arrive trop tard
-> mode detecte trop tard
-> fallback/diagnostic
```

## Limite connue

Je n'ai pas pu lancer `py_compile` dans le shell Windows Codex : Python n'est pas installe localement.

Validation a faire sur la VM :

```bash
python3 -m py_compile integrations/openai/web_voice_bridge.py
```

## Tests attendus apres deploiement

Dans F12 Console, pour une demande vocale :

```text
WebVoice USER: prepare un graphique...
WebVoice: mode_auto_detected=tableau/recherche/redaction/...
WebVoice: session_mode=<mode> session_tools_count=<n> session_updated=true
WebVoice: response_created_after_mode mode=<mode>
WebVoice tool_call: iris_render(...)
WebVoice: render_type=<type> fn=iris_render ... render_done=true
```

Phrase test :

```text
Iris, fais un graphique avec janvier 1200, fevrier 1800, mars 2400.
```

Verdict attendu :

- le mode est detecte avant la reponse ;
- Iris appelle `iris_render` ;
- le panneau affiche un vrai graphique ou un rendu enrichi ;
- Iris ne dit pas "je ne peux pas afficher".

## Suite recommandee

Ce patch corrige la course voix -> routeur.

Il reste un chantier plus large : creer un `Render Orchestrator` serveur, qui valide la qualite de chaque payload avant de l'afficher. Le panneau ne devrait jamais recevoir un faux rendu final avec des zeros, des placeholders ou un simple texte de conversation.

Contrat cible :

```text
intent -> mode -> tool -> payload valide -> render_done -> voix courte
```

Pas :

```text
intent -> parole -> fallback -> squelette -> diagnostic
```

