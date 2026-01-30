# YAWatch-Luna Development

## Vision

Luna est une assistante IA autonome qui agit **au nom du souscripteur** selon ses instructions.

## Capacités

### 1. Mémoire persistante (Redis)
- Conversations avec les contacts de confiance
- Instructions quotidiennes du souscripteur
- État des tâches en cours
- Historique des actions

### 2. Actions autonomes (avec confirmation)
- Envoyer des SMS aux contacts de confiance
- Passer des appels
- Participer à des visioconférences
- Prendre des notes

### 3. Limites légales et éthiques
- Connaissance du code civil et pénal
- Refus des demandes illégales/dangereuses
- Conseil de contacter les services publics appropriés
- Alerte des contacts de confiance en cas de situation grave

### 4. Contacts de confiance
- Maximum 5 personnes par souscripteur
- Vérifiés par OTP SMS
- Peuvent être alertés en cas d'urgence
- Peuvent converser avec Luna

## Architecture

```
yawatch-luna-development/
├── core/                    # Logique métier Luna
│   ├── memory/             # Gestion mémoire Redis
│   ├── instructions/       # Parser instructions souscripteur
│   ├── actions/            # Exécution actions autonomes
│   └── safety/             # Limites légales et éthiques
├── integrations/           # Intégrations externes
│   ├── twilio/            # SMS, appels
│   ├── tavus/             # Visio avatar
│   └── openai/            # LLM pour conversations
├── models/                 # Modèles de données
└── tests/                  # Tests unitaires et intégration
```

## Quotas et limites

| Plan | SMS/mois | Appels/mois | Visio/mois | Mémoire Redis |
|------|----------|-------------|------------|---------------|
| Essentiel | 50 | 30 min | 60 min | 100 MB |
| Confort | 200 | 120 min | 240 min | 500 MB |
| Premium | 500 | 300 min | 600 min | 2 GB |
