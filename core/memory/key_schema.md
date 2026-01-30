# Luna Redis Key Schema

## Convention de nommage

```
luna:{tenant_id}:{domain}:{sub_key}
```

## Clés par domaine

### 1. Conversations
```redis
# Liste des conversations actives d'un tenant
luna:{tenant_id}:conversations                    → SET of conversation_ids

# Détails d'une conversation
luna:{tenant_id}:conv:{conv_id}:meta              → HASH {contact_phone, contact_name, started_at, last_activity, status}
luna:{tenant_id}:conv:{conv_id}:messages          → LIST [{role, content, timestamp, channel}...]

# Index par contact
luna:{tenant_id}:contact:{phone}:conversations    → SET of conversation_ids
```

### 2. Instructions du souscripteur
```redis
# Instructions actives
luna:{tenant_id}:instructions:active              → ZSET {instruction_id: priority}

# Détail d'une instruction
luna:{tenant_id}:instruction:{instr_id}           → HASH {
                                                      type,           # daily, recurring, one_time
                                                      description,    # "Rappelle-moi de prendre mes médicaments à 8h"
                                                      schedule,       # cron expression ou datetime
                                                      action,         # sms, call, reminder, note
                                                      target,         # contact_phone ou "self"
                                                      created_at,
                                                      last_executed,
                                                      enabled
                                                    }

# Instructions par type
luna:{tenant_id}:instructions:daily               → SET of instruction_ids
luna:{tenant_id}:instructions:recurring           → SET of instruction_ids
```

### 3. État des tâches
```redis
# Tâches en cours
luna:{tenant_id}:tasks:pending                    → ZSET {task_id: created_at}
luna:{tenant_id}:tasks:completed                  → ZSET {task_id: completed_at} (TTL 7 jours)

# Détail d'une tâche
luna:{tenant_id}:task:{task_id}                   → HASH {
                                                      type,           # sms, call, visio, note, reminder
                                                      status,         # pending, in_progress, completed, failed
                                                      description,
                                                      context,        # JSON avec détails
                                                      created_at,
                                                      started_at,
                                                      completed_at,
                                                      result
                                                    }
```

### 4. Contexte de session
```redis
# Session active Luna
luna:{tenant_id}:session:current                  → HASH {
                                                      started_at,
                                                      channel,        # app, sms, call, visio
                                                      mood,           # detected mood
                                                      topics,         # JSON array of discussed topics
                                                      pending_action  # action_id waiting confirmation
                                                    }

# Historique sessions (dernières 24h)
luna:{tenant_id}:sessions:history                 → LIST of session summaries (TTL 24h)
```

### 5. Contacts de confiance
```redis
# Liste des contacts vérifiés
luna:{tenant_id}:trusted_contacts                 → SET of contact_phones (max 5)

# Détails contact
luna:{tenant_id}:contact:{phone}:profile          → HASH {
                                                      name,
                                                      relation,       # fils, fille, voisin, aide-soignant...
                                                      verified_at,
                                                      last_contact,
                                                      preferences     # JSON {preferred_channel, quiet_hours...}
                                                    }
```

### 6. Notes et observations
```redis
# Notes prises par Luna
luna:{tenant_id}:notes                            → ZSET {note_id: timestamp}

# Détail note
luna:{tenant_id}:note:{note_id}                   → HASH {
                                                      content,
                                                      context,        # visio, call, observation
                                                      source,         # conversation_id ou "autonomous"
                                                      created_at,
                                                      tags            # JSON array
                                                    }
```

### 7. Quotas et usage mémoire
```redis
# Usage mémoire du tenant
luna:{tenant_id}:quota:memory                     → HASH {
                                                      used_bytes,
                                                      limit_bytes,
                                                      last_updated
                                                    }

# Compteurs quotidiens
luna:{tenant_id}:usage:{YYYY-MM-DD}               → HASH {
                                                      messages_count,
                                                      instructions_executed,
                                                      tasks_completed,
                                                      notes_created
                                                    }
```

## TTL (Time To Live)

| Clé | TTL | Raison |
|-----|-----|--------|
| Messages conversation | 30 jours | Conformité RGPD |
| Sessions history | 24h | Contexte court terme |
| Tâches completed | 7 jours | Audit trail |
| Notes | 90 jours | Historique utile |
| Usage quotidien | 90 jours | Reporting |

## Quotas mémoire par plan

| Plan | Limite | Conversations | Messages/conv | Notes |
|------|--------|---------------|---------------|-------|
| Essentiel | 100 MB | 10 actives | 100 | 50 |
| Confort | 500 MB | 50 actives | 500 | 200 |
| Premium | 2 GB | Illimité | 1000 | Illimité |
