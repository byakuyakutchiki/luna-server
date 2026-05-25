# Stratégie Auto-Guérison — Luna Server
## Document de travail — soumis à revue IA

---

## 1. Diagnostic racine

### Problème central
Luna tourne sur **Cloud Run** (sans état, sans Redis local). Le code suppose `localhost:6379` disponible.
Résultat : ~50% des endpoints crashent avec `ConnectionError: Error 111 connecting to localhost:6379`.

### Pourquoi `if not _redis_client:` est inutile
```python
_redis_client = RedisClient()  # TOUJOURS non-None (l'objet est créé)
if not _redis_client:           # TOUJOURS False → check inefficace
    return fallback             # JAMAIS atteint
_redis_client.client.get(key)  # CRASH si Redis serveur absent
```
**Fix appliqué** : `_redis_available()` fait un vrai ping avec cache 30s.

---

## 2. Architecture de guérison — 4 couches

### Couche 1 — Détection (implémentée)
```python
_redis_up: bool = False
_redis_last_check: float = 0.0

def _redis_available() -> bool:
    """Ping Redis toutes les 30s. Cache le résultat."""
    global _redis_up, _redis_last_check
    now = time.time()
    if now - _redis_last_check < 30:
        return _redis_up           # Cache chaud → pas de ping
    _redis_last_check = now
    try:
        _redis_client.client.ping()
        _redis_up = True
    except Exception:
        _redis_up = False
    return _redis_up
```
**Comportement** : 1 ping toutes les 30s max. Si Redis revient, détecté en ≤30s.

### Couche 2 — Dégradation par tiers (à implémenter)

| Tier | Services requis | Features |
|------|----------------|----------|
| 0 | Aucun | Login (env fallback), pages statiques, `/health` |
| 1 | OpenAI | Chat, TTS, STT, traduction |
| 2 | + Redis | Mémoire, quotas, social, notifications, géoloc |
| 3 | + Tavus API | Visio avatar |
| 4 | + Twilio | SMS, appels vocaux |

Chaque endpoint déclare son tier et retourne un fallback propre si son tier n'est pas disponible.

### Couche 3 — Circuit Breaker (à implémenter)

```python
class CircuitBreaker:
    """Empêche les appels répétés à un service mort."""
    def __init__(self, name: str, fail_threshold=3, reset_after=60):
        self.name = name
        self.failures = 0
        self.state = "closed"  # closed=OK, open=KO, half-open=test
        self.last_failure = 0
        self.fail_threshold = fail_threshold
        self.reset_after = reset_after

    def call(self, func, *args, fallback=None, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure > self.reset_after:
                self.state = "half-open"
            else:
                return fallback  # Court-circuit immédiat
        try:
            result = func(*args, **kwargs)
            self.failures = 0
            self.state = "closed"
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure = time.time()
            if self.failures >= self.fail_threshold:
                self.state = "open"
                logger.warning(f"Circuit {self.name} OUVERT après {self.failures} échecs")
            return fallback

# Usage:
_redis_cb = CircuitBreaker("redis", fail_threshold=3, reset_after=60)
# Chaque appel Redis passe par le circuit breaker
```

### Couche 4 — Infrastructure Cloud Redis (solution permanente)

**Action unique** : remplacer `REDIS_URL=redis://localhost:6379/0` par Upstash Redis.

```
Upstash Redis Free Tier:
- 256 MB stockage
- 10 000 req/jour (gratuit), 500K/mois (~0.0002€/commande au-delà)
- URL : rediss://default:<password>@<endpoint>.upstash.io:6379
- Compatible 100% avec le code existant (même client redis-py)
- Setup : 5 minutes sur upstash.com
```

**Coût estimé pour Luna** :
- Demo (~50 req/jour Redis) : 0€/mois
- 1 tenant actif (~5 000 req/jour) : 0€/mois
- 10 tenants (~50 000 req/jour) : ~1€/mois

---

## 3. Plan d'action priorisé

### Priorité 1 — IMMÉDIAT (fait dans cette session)
- [x] `_redis_available()` avec cache 30s
- [x] `_get_sops()` utilise `_redis_available()`
- [x] `geolocation`, `notifications`, `heartbeat` : fallback silencieux
- [x] `security_middleware` : try/except Redis (ne crash plus)
- [x] `_get_tenant_manager()` : fallback si Redis KO
- [x] `auth_login` : fallback env-vars si Redis KO

### Priorité 2 — COURT TERME (1-2h)
- [ ] **Upstash Redis** : créer compte, copier l'URL, `./deploy.sh` avec `REDIS_URL=rediss://...`
- [ ] Tous les features Redis redeviennent opérationnels instantanément

### Priorité 3 — MOYEN TERME
- [ ] CircuitBreaker pour Redis, Tavus, OpenAI, Twilio
- [ ] Endpoint `POST /api/admin/self-heal` : relance les connexions, reset les circuits
- [ ] Tableau de bord temps réel des circuits dans `/fondateur`

### Priorité 4 — LONG TERME
- [ ] Déclarer le tier de chaque endpoint dans le code
- [ ] Page de status public (`/status`) avec tier actuel
- [ ] Alerts Telegram automatiques si un tier descend

---

## 4. Erreurs restantes et leur cause

| Erreur | Cause | Fix |
|--------|-------|-----|
| `/api/social/heartbeat` 500 | Redis KO (ConnectionError dans sops) | `_redis_available()` + fallback ✓ |
| `/api/notifications/pending` 500 | Redis KO | `_redis_available()` + fallback ✓ |
| `/api/geolocation` 500 | Redis KO | `_redis_available()` + try/except ✓ |
| `/api/call` 503 | Tavus API KO OU Simli non configuré | Upstash ne résout pas — Tavus API key à tester |
| `/api/simli/start` 503 | Simli désactivé (supprimé) | Endpoint → 410 Gone ou rediriger vers /api/call |
| `No Listener: tabs:outgoing.message.ready` | Erreur vendor.js (extension Chrome ou tab messaging) | Erreur côté client non bloquante, ignorable |

---

## 5. Question ouverte pour les autres IA

**Architecture proposée** : chaque service (Redis, Tavus, OpenAI, Twilio) a son propre `CircuitBreaker`. Quand un circuit est ouvert, le serveur répond immédiatement avec un fallback (200 OK + données vides) plutôt qu'une erreur.

**Question** : Est-ce qu'un circuit breaker avec timeout de reset à 60s est suffisant pour Cloud Run où chaque instance repart de zéro ? Ou faut-il stocker l'état des circuits dans une clé Redis externe pour que toutes les instances partagent le même état ?

**Contrainte** : Cloud Run scale to zero — une nouvelle instance ne connaît pas l'historique des échecs des instances précédentes. Le circuit repart toujours à "closed" (optimiste). Est-ce acceptable ?

**Alternative** : Upstash Redis stocke l'état des circuits → toutes les instances voient le même état → circuit cohérent même en scale-out.
