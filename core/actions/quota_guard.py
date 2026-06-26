"""
Luna Quota Guard - Protection des quotas et limites de conversation

Vérifie et gère les quotas par forfait:
- Essentiel (79€): 25 SMS/mois, 40 min voix, 12 min visio, chat illimité
- Confort (149€): 50 SMS/mois, 100 min voix, 28 min visio, chat illimité
- Premium (249€): 100 SMS/mois, 180 min voix, 55 min visio, chat illimité

Alertes:
- 80%: avertissement au propriétaire
- 90%: Luna commence à limiter ses actions
- 100%: blocage des envois

PRINCIPE: Le propriétaire ne reçoit JAMAIS de facture surprise.
Luna doit toujours prévenir AVANT d'atteindre les limites.
JAMAIS de "illimité" sur aucune ressource facturée.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .models import ActionType

logger = logging.getLogger(__name__)


class PlanType(str, Enum):
    """Types de forfait"""
    FONDATEUR = "fondateur"
    ESSENTIEL = "essentiel"
    CONFORT = "confort"
    PREMIUM = "premium"


# Quotas SMS par forfait
PLAN_SMS_LIMITS = {
    PlanType.FONDATEUR: 999999,
    PlanType.ESSENTIEL: 25,
    PlanType.CONFORT: 50,
    PlanType.PREMIUM: 100,
}

# Quotas voix par forfait (minutes/mois)
PLAN_VOICE_LIMITS = {
    PlanType.FONDATEUR: 999999,
    PlanType.ESSENTIEL: 40,
    PlanType.CONFORT: 100,
    PlanType.PREMIUM: 180,
}

# Quotas visio Luna par forfait — Tavus désactivé, visio = add-on futur
PLAN_VISIO_LIMITS = {
    PlanType.FONDATEUR: 999999,
    PlanType.ESSENTIEL: 0,
    PlanType.CONFORT: 0,
    PlanType.PREMIUM: 0,
}

# Quotas messages chat par forfait (illimite en pratique)
PLAN_MESSAGE_LIMITS = {
    PlanType.FONDATEUR: 999999,
    PlanType.ESSENTIEL: 999999,
    PlanType.CONFORT: 999999,
    PlanType.PREMIUM: 999999,
}

# Tarifs depassement
OVERAGE_PRICES = {
    "sms": 0.20,       # €/SMS
    "visio": 3.00,     # €/minute
    "message": 0.15,   # €/message
}

# Seuils d'alerte (en pourcentage)
WARN_THRESHOLD = 80
LIMIT_THRESHOLD = 90
BLOCK_THRESHOLD = 100


@dataclass
class QuotaStatus:
    """Statut du quota pour une vérification"""
    allowed: bool  # L'action est-elle autorisée ?
    remaining: int  # Unités restantes
    used: int  # Unités utilisées
    limit: int  # Limite du forfait
    percentage: float  # Pourcentage utilisé (0-100)
    should_warn: bool  # Faut-il avertir le souscripteur ?
    should_limit: bool  # Luna doit-elle se limiter ?
    warning_message: Optional[str] = None  # Message d'avertissement
    message: str = ""  # Message descriptif

    def to_dict(self) -> Dict[str, Any]:
        """Sérialise pour API/stockage"""
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "used": self.used,
            "limit": self.limit,
            "percentage": round(self.percentage, 1),
            "should_warn": self.should_warn,
            "should_limit": self.should_limit,
            "warning_message": self.warning_message,
        }


class QuotaGuard:
    """
    Garde-fou des quotas.

    Vérifie les limites avant chaque action consommatrice
    et gère les alertes pour le propriétaire.

    NOTE: En production, les quotas sont stockés dans PostgreSQL
    (via le backend iawatch). Ici on gère le cache local et
    les vérifications côté Luna.
    """

    def __init__(
        self,
        memory_manager=None,
        redis_client=None,
    ):
        """
        Args:
            memory_manager: MemoryManager pour accéder aux quotas Redis
            redis_client: Client Redis pour persister les quotas (J9 — évite les pertes au redémarrage)
        """
        self.memory = memory_manager
        self._rc = redis_client  # J9: client Redis brut (redis_client.client)
        # Cache local: tenant_id -> {action_type -> count}
        self._usage_cache: Dict[int, Dict[str, int]] = {}
        # Cache des plans: tenant_id -> PlanType
        self._plan_cache: Dict[int, PlanType] = {}
        # Alertes déjà envoyées: tenant_id -> set(threshold)
        self._alerts_sent: Dict[int, set] = {}

    def check(
        self,
        tenant_id: int,
        action_type: ActionType,
        estimated_cost: int = 1,
    ) -> QuotaStatus:
        """
        Vérifie si une action est autorisée par le quota.

        Args:
            tenant_id: ID du tenant
            action_type: Type d'action
            estimated_cost: Coût estimé de l'action

        Returns:
            QuotaStatus avec le résultat
        """
        # Seuls les SMS consomment du quota pour l'instant
        if action_type not in (ActionType.SEND_SMS, ActionType.ALERT_CONTACTS):
            return QuotaStatus(
                allowed=True,
                remaining=999,
                used=0,
                limit=999,
                percentage=0.0,
                should_warn=False,
                should_limit=False,
                message="Action non soumise à quota",
            )

        plan = self._get_plan(tenant_id)
        limit = PLAN_SMS_LIMITS.get(plan, 50) + self.get_bonus(tenant_id, "sms")
        used = self._get_usage(tenant_id, "sms")
        remaining = max(0, limit - used)
        percentage = (used / limit * 100) if limit > 0 else 0

        # Vérifie si l'action est autorisée
        allowed = (used + estimated_cost) <= limit

        # Détermine les seuils
        should_warn = percentage >= WARN_THRESHOLD
        should_limit = percentage >= LIMIT_THRESHOLD

        # Construit le message d'avertissement
        warning_message = None
        if percentage >= BLOCK_THRESHOLD:
            warning_message = (
                f"Votre quota SMS est atteint ({used}/{limit}). "
                "Les envois sont bloqués jusqu'au prochain cycle."
            )
        elif percentage >= LIMIT_THRESHOLD:
            warning_message = (
                f"Attention, il ne vous reste que {remaining} SMS ce mois-ci "
                f"({used}/{limit} utilisés). "
                "Je vais limiter mes envois au strict nécessaire."
            )
        elif percentage >= WARN_THRESHOLD:
            warning_message = (
                f"Vous avez utilisé {int(percentage)}% de vos SMS ce mois "
                f"({used}/{limit}). Il vous reste {remaining} SMS."
            )

        # Message pour le résultat
        if not allowed:
            message = (
                f"Quota SMS atteint ({used}/{limit}). "
                "Action bloquée."
            )
        else:
            message = f"Quota OK: {remaining} SMS restants sur {limit}"

        status = QuotaStatus(
            allowed=allowed,
            remaining=remaining,
            used=used,
            limit=limit,
            percentage=percentage,
            should_warn=should_warn,
            should_limit=should_limit,
            warning_message=warning_message,
            message=message,
        )

        # Gère les alertes propriétaire
        self._check_and_send_alerts(tenant_id, status)

        return status

    def increment(
        self,
        tenant_id: int,
        action_type: ActionType,
        cost: int = 1,
    ) -> None:
        """
        Incrémente l'utilisation après une action réussie.

        Args:
            tenant_id: ID du tenant
            action_type: Type d'action
            cost: Coût réel de l'action
        """
        if action_type not in (ActionType.SEND_SMS, ActionType.ALERT_CONTACTS):
            return

        if tenant_id not in self._usage_cache:
            self._usage_cache[tenant_id] = {}

        # J9 — Persister en Redis avec TTL mensuel auto-reset
        new_total = self._usage_cache[tenant_id].get("sms", 0) + cost
        if self._rc:
            try:
                key = self._redis_quota_key(tenant_id)
                new_total = self._rc.incrby(key, cost)
                self._rc.expire(key, 35 * 86400)  # TTL 35 jours, reset naturel chaque mois
            except Exception:
                pass
        self._usage_cache[tenant_id]["sms"] = new_total

        logger.info(
            f"Quota incremented: tenant={tenant_id}, "
            f"sms={new_total}"
        )

    def get_usage_summary(self, tenant_id: int) -> Dict[str, Any]:
        """
        Récupère un résumé d'utilisation pour le dashboard propriétaire.

        Args:
            tenant_id: ID du tenant

        Returns:
            Dict avec les stats d'utilisation
        """
        plan = self._get_plan(tenant_id)
        base_limit = PLAN_SMS_LIMITS.get(plan, 50)
        bonus = self.get_bonus(tenant_id, "sms")
        limit = base_limit + bonus
        used = self._get_usage(tenant_id, "sms")
        remaining = max(0, limit - used)
        percentage = (used / limit * 100) if limit > 0 else 0

        return {
            "plan": plan.value,
            "sms": {
                "used": used,
                "limit": limit,
                "base_limit": base_limit,
                "bonus": bonus,
                "remaining": remaining,
                "percentage": round(percentage, 1),
            },
        }

    def set_plan(self, tenant_id: int, plan: PlanType) -> None:
        """
        Définit le forfait d'un tenant.

        Args:
            tenant_id: ID du tenant
            plan: Type de forfait
        """
        self._plan_cache[tenant_id] = plan
        logger.info(f"Plan set: tenant={tenant_id}, plan={plan.value}")

    def reset_monthly_usage(self, tenant_id: int) -> None:
        """
        Remet à zéro le compteur mensuel.
        Appelé en début de mois.

        Args:
            tenant_id: ID du tenant
        """
        if tenant_id in self._usage_cache:
            self._usage_cache[tenant_id] = {}
        if tenant_id in self._alerts_sent:
            self._alerts_sent[tenant_id] = set()

        logger.info(f"Monthly usage reset: tenant={tenant_id}")

    def should_luna_limit_conversation(self, tenant_id: int) -> Optional[str]:
        """
        Vérifie si Luna doit commencer à limiter la conversation.

        Retourne un message si Luna doit avertir le souscripteur
        que les quotas approchent.

        Args:
            tenant_id: ID du tenant

        Returns:
            Message d'avertissement ou None
        """
        plan = self._get_plan(tenant_id)
        limit = PLAN_SMS_LIMITS.get(plan, 50) + self.get_bonus(tenant_id, "sms")
        used = self._get_usage(tenant_id, "sms")
        percentage = (used / limit * 100) if limit > 0 else 0
        remaining = max(0, limit - used)

        if percentage >= 98:
            return (
                "Je suis désolée, mais votre quota de SMS est presque "
                "épuisé. Je ne pourrai bientôt plus envoyer de messages. "
                "Souhaitez-vous que je fasse quelque chose d'urgent avant ?"
            )
        elif percentage >= LIMIT_THRESHOLD:
            return (
                f"Je tiens à vous informer qu'il ne vous reste que "
                f"{remaining} SMS ce mois-ci. Je vais limiter mes envois "
                "au strict nécessaire."
            )

        return None

    # =========================================================================
    # MÉTHODES INTERNES
    # =========================================================================

    def _get_plan(self, tenant_id: int) -> PlanType:
        """Récupère le forfait du tenant"""
        return self._plan_cache.get(tenant_id, PlanType.ESSENTIEL)

    def _redis_quota_key(self, tenant_id: int) -> str:
        """Clé Redis mensuelle : expire naturellement après 35 jours (J9)."""
        month = datetime.utcnow().strftime("%Y-%m")
        return f"luna:{tenant_id}:quota:sms:{month}"

    def _redis_bonus_key(self, tenant_id: int, resource: str = "sms") -> str:
        """Clé Redis du bonus mensuel (geste commercial admin).

        Même cycle mensuel que le quota : le bonus se réinitialise naturellement
        chaque mois, comme le compteur d'usage.
        """
        month = datetime.utcnow().strftime("%Y-%m")
        return f"luna:{tenant_id}:quota:{resource}:bonus:{month}"

    def get_bonus(self, tenant_id: int, resource: str = "sms") -> int:
        """Bonus courant accordé par l'admin pour la ressource (0 si aucun)."""
        if not self._rc:
            return 0
        try:
            val = self._rc.get(self._redis_bonus_key(tenant_id, resource))
            return int(val) if val is not None else 0
        except Exception:
            return 0

    def grant_bonus(self, tenant_id: int, amount: int, resource: str = "sms") -> int:
        """Accorde (ou retire si négatif) un bonus de quota — geste commercial.

        Le bonus s'ajoute à la limite du forfait pour le mois en cours et
        expire avec lui. Retourne le nouveau total de bonus.

        Args:
            tenant_id: ID du tenant bénéficiaire
            amount: nombre d'unités à ajouter (peut être négatif pour corriger)
            resource: ressource concernée (sms uniquement aujourd'hui)

        Returns:
            Nouveau total de bonus pour le mois en cours.
        """
        if not self._rc:
            logger.warning(f"grant_bonus sans Redis: tenant={tenant_id} ignoré")
            return 0
        try:
            key = self._redis_bonus_key(tenant_id, resource)
            new_total = self._rc.incrby(key, int(amount))
            # Plancher à 0 : un bonus ne descend jamais sous zéro
            if new_total < 0:
                self._rc.set(key, 0)
                new_total = 0
            self._rc.expire(key, 35 * 86400)
            logger.info(
                f"Quota bonus granted: tenant={tenant_id}, {resource} "
                f"+{amount} → bonus_total={new_total}"
            )
            return new_total
        except Exception as e:
            logger.error(f"grant_bonus error tenant={tenant_id}: {e}")
            return self.get_bonus(tenant_id, resource)

    def _get_usage(self, tenant_id: int, resource: str) -> int:
        """Récupère l'utilisation courante — Redis en priorité, cache local en fallback (J9)."""
        if resource == "sms" and self._rc:
            try:
                val = self._rc.get(self._redis_quota_key(tenant_id))
                if val is not None:
                    return int(val)
            except Exception:
                pass
        return self._usage_cache.get(tenant_id, {}).get(resource, 0)

    def _check_and_send_alerts(
        self,
        tenant_id: int,
        status: QuotaStatus,
    ) -> None:
        """
        Vérifie si une alerte doit être envoyée au propriétaire.

        Les alertes sont envoyées une seule fois par seuil par mois.
        """
        if tenant_id not in self._alerts_sent:
            self._alerts_sent[tenant_id] = set()

        sent = self._alerts_sent[tenant_id]

        if status.percentage >= BLOCK_THRESHOLD and BLOCK_THRESHOLD not in sent:
            sent.add(BLOCK_THRESHOLD)
            logger.warning(
                f"QUOTA ALERT [100%]: tenant={tenant_id}, "
                f"used={status.used}/{status.limit}"
            )
            # En production: notification WebSocket + SMS au propriétaire

        elif status.percentage >= WARN_THRESHOLD and WARN_THRESHOLD not in sent:
            sent.add(WARN_THRESHOLD)
            logger.warning(
                f"QUOTA ALERT [80%]: tenant={tenant_id}, "
                f"used={status.used}/{status.limit}"
            )
            # En production: notification WebSocket au propriétaire


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_quota_guard(memory_manager=None) -> QuotaGuard:
    """
    Factory pour créer un QuotaGuard configuré.

    Args:
        memory_manager: MemoryManager optionnel

    Returns:
        QuotaGuard configuré
    """
    return QuotaGuard(memory_manager=memory_manager)
