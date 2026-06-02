# Codex — Fix syntaxe Command Screen Claude — Objectif 019

Date : 2026-06-02  
Agent : Codex  
Type : garde-fou / correction bloquante  
Niveau : 1

## Constat

Le commit Claude `fc5466d` et le rapport `8c135bc` sont bien pousses sur GitHub.

Avant de valider un deploiement, Codex a compile le JavaScript inline de `static/simli.html`.

Resultat initial :

```text
SyntaxError: Invalid or unexpected token
static/simli.html:script0
return String(s||’’).replace(/&/g,’&amp;’)
```

Cause :

Des guillemets typographiques `‘` / `’` etaient presents dans le bloc JavaScript Iris Command Screen.

## Correction

Correction mecanique :

- remplacement des guillemets typographiques par des quotes JavaScript ASCII ;
- conservation du comportement du Command Screen ;
- aucune modification fonctionnelle volontaire.

## Verification

Apres correction :

- compilation JavaScript inline `static/simli.html` : OK ;
- `py_compile` sur `luna_web.py` et `integrations/openai/web_voice_bridge.py` : OK ;
- `git diff --check` : OK.

## Decision

Ne pas deployer `fc5466d` seul.

Deployer uniquement un main qui inclut ce correctif Codex.
