# Test Twilio / OpenAI avec vraies clés

> Document de validation des intégrations externes de YAWatch-Luna (Sprint B).
> Objectif : s'assurer qu'avec de vraies clés de production, Luna peut réellement envoyer des SMS via Twilio et générer des réponses via OpenAI.

## Prérequis

- Un compte Twilio actif avec un numéro de téléphone capable d'envoyer des SMS.
- Une clé API OpenAI active avec quota disponible.
- Le serveur Luna démarré avec les variables d'environnement correctes.

## 1. Configuration

Dans le fichier `.env` du serveur (ou les variables Cloud Run) :

```bash
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
OPENAI_MODEL=gpt-4o-mini

TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_SMS_FROM=+1XXXXXXXXXX   # numéro Twilio vérifié

ADMIN_NUMBER=+33XXXXXXXXX      # votre numéro de téléphone
```

Redémarrer le serveur après modification du `.env`.

Vérifier que les deux services sont détectés au démarrage :

```bash
curl https://localhost:8888/health
# attendu : {"status":"ok","openai":"ok"}

curl https://localhost:8888/api/status
# attendu : "twilio":"ok", "openai":"ok"
```

## 2. Test OpenAI

### 2.1 Via l'API chat

```bash
curl -X POST https://localhost:8888/api/chat \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Dis-moi bonjour en 10 mots maximum.",
    "session_id": "test-openai"
  }'
```

### 2.2 Critères de réussite

- Le serveur retourne une réponse JSON avec `response` non vide.
- La réponse est cohérente avec la question posée.
- Aucune erreur 500 ou 503 dans les logs.
- Le coût OpenAI est traçable dans `/api/status` ou les logs (`track_openai_cost`).

### 2.3 Débogage

- Si `OPENAI_API_KEY` est invalide, le log contient `OPENAI AUTH ERROR`.
- Si le quota est dépassé, le message de réponse contient "quota".
- Vérifier la connectivité réseau : `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`.

## 3. Test Twilio (SMS)

### 3.1 Créer un contact

Dans l'interface web (`/`) onglet **Contacts**, ou via API :

```bash
curl -X POST https://localhost:8888/api/contacts \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Twilio",
    "phone": "+336XXXXXXXX"
  }'
```

> ⚠️ Le numéro cible doit être capable de recevoir des SMS internationaux.

### 3.2 Demander à Luna d'envoyer un SMS

Dans le chat, taper :

```text
Envoie un SMS à Test Twilio disant "Ceci est un test depuis Luna".
```

Ou via `/api/chat` avec un message similaire.

### 3.3 Critères de réussite

- Une action pending apparaît dans le panneau **Actions en attente** (frontend) ou via `GET /api/actions/pending`.
- Après confirmation de l'utilisateur, le statut passe à `confirmed`.
- Le SMS est reçu sur le téléphone cible dans les 30 secondes.
- Le SMS apparaît dans la console Twilio (`Messaging > Try it out > Logs`).
- Les logs Luna contiennent une ligne du type :
  ```
  SMS sent to +336XXXXXXXX via Twilio, sid=SMxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```

### 3.4 Débogage

- Si Twilio n'est pas configuré, `/api/status` retourne `"twilio":"not_configured"`.
- Si le numéro cible est invalide, Twilio retourne une erreur `21211` ; le log Luna affiche l'erreur.
- En mode `FOUNDATION_TEST_MODE=true`, aucun SMS réel n'est envoyé même avec des clés valides.

## 4. Test combiné (OpenAI + Twilio)

Scénario utilisateur :

1. L'utilisateur demande : "Demande à Marie si elle est disponible demain à 14h et envoie-lui un SMS."
2. OpenAI génère le contenu du SMS.
3. Luna crée une action pending `send_sms` avec `message_body`.
4. L'utilisateur confirme via le panneau frontend ou `POST /api/actions/{id}/confirm`.
5. Twilio envoie le SMS.

Critères de réussite : le SMS reçu correspond au message généré par OpenAI.

## 5. Nettoyage

Après les tests, supprimer le contact de test et vider les actions pending si nécessaire :

```bash
curl -X DELETE "https://localhost:8888/api/contacts/+336XXXXXXXX" \
  -H "Authorization: Bearer <TOKEN>"
```

## 6. Notes de sécurité

- Ne jamais commiter les clés Twilio/OpenAI.
- Vérifier que `.env` est bien dans `.gitignore`.
- En production, utiliser Secret Manager (GCP) ou équivalent.
