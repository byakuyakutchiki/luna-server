# Note Sentry — Source d'observation du cerveau Luna

**Date** : 2026-05-25  
**Auteur** : Codex  
**Statut** : à intégrer dans la coordination équipe  

## Contexte

Ludovic dispose d'un accès Sentry Free. Sentry peut déjà recevoir des alertes et
événements utiles pour identifier les pannes frontend, WebView, serveur ou API.

Cet outil ne doit pas rester dans un angle mort individuel. Si Sentry observe une
panne, l'information doit être centralisée dans GitHub pour que Claude, Codex,
DeepSeek, Kimi et Cursor travaillent avec la même réalité.

## Principe central

Le cerveau Luna doit centraliser les signaux importants :

- cockpit fondateur ;
- heartbeat APK ;
- événements voix APK ;
- logs Cloud Run ;
- Redis diagnostics ;
- rapports agents ;
- Sentry.

Aucun serveur, outil de monitoring ou source d'erreur ne doit être connu par un
seul agent sans être résumé dans GitHub.

## Règles Sentry

1. Sentry est une source de diagnostic, pas une source de correction automatique.
2. Aucun secret, token, clé API, cookie, email privé ou donnée personnelle sensible
   ne doit être copié dans GitHub.
3. Les extraits Sentry doivent être filtrés/anonymisés.
4. Les accès complets Sentry ne doivent pas être donnés à tous les agents par défaut.
5. Claude peut lire Sentry si Ludovic lui donne accès ou fournit une capture.
6. Les autres agents doivent recevoir un rapport filtré dans GitHub.
7. Toute conclusion tirée depuis Sentry doit être reliée à une heure de test réelle.

## Rapport attendu

Créer ou mettre à jour :

`docs/AGENTS_COLLABORATION/RAPPORT_SENTRY_OBJECTIF_008.md`

Champs minimum :

- date et heure Europe/Paris ;
- projet Sentry concerné ;
- environnement si connu ;
- route, fichier ou composant concerné ;
- message d'erreur ;
- stack trace utile filtrée ;
- lien avec le test Ludovic ;
- hypothèse ;
- action recommandée ;
- données masquées.

## Recherches prioritaires pour Objectif 008

Chercher autour des tests réels de Ludovic :

- `voice`
- `startVoice`
- `WebSocket`
- `/ws/luna-voice`
- `OpenAI`
- `Realtime`
- `session.update`
- `response.audio.delta`
- `fondateur.html`
- `index.html`
- erreurs WebView Android
- erreurs UI mobile, notamment bouton `Déconnexion` coupé

## Message à l'équipe

Sentry fait partie du cerveau Luna en lecture filtrée.

Si Sentry contient une information utile, elle doit être résumée dans GitHub avant
qu'une correction majeure soit proposée. On ne garde pas des signaux de production
dans des silos séparés.

