"""
Luna Memory Schemas - Modèles de données pour la mémoire Redis
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class MessageRole(str, Enum):
    """Rôle de l'émetteur du message"""
    LUNA = "luna"
    SUBSCRIBER = "subscriber"  # Le souscripteur (proprio)
    CONTACT = "contact"  # Contact de confiance
    SYSTEM = "system"


class Channel(str, Enum):
    """Canal de communication"""
    APP = "app"           # Chat texte application
    VOICE = "voice"       # Voix application (sans video)
    SMS = "sms"           # SMS Twilio
    CALL = "call"         # Appel vocal Twilio
    VISIO = "visio"       # Video Tavus
    WEBHOOK = "webhook"   # Webhook externe


class ConversationStatus(str, Enum):
    """Statut d'une conversation"""
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class InstructionType(str, Enum):
    """Type d'instruction"""
    DAILY = "daily"  # Tous les jours
    RECURRING = "recurring"  # Récurrent (cron)
    ONE_TIME = "one_time"  # Une seule fois
    CONDITIONAL = "conditional"  # Si condition remplie


class ActionType(str, Enum):
    """Type d'action pour une instruction"""
    SMS = "sms"
    CALL = "call"
    VISIO = "visio"
    REMINDER = "reminder"  # Rappel au souscripteur
    NOTE = "note"  # Prendre une note
    ALERT = "alert"  # Alerter contacts de confiance


class TaskStatus(str, Enum):
    """Statut d'une tâche"""
    PENDING = "pending"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanType(str, Enum):
    """Type de forfait"""
    ESSENTIEL = "essentiel"
    CONFORT = "confort"
    PREMIUM = "premium"
    # Family Pack
    FAMILY_ESSENTIEL = "family_essentiel"
    FAMILY_CONFORT = "family_confort"
    FAMILY_PREMIUM = "family_premium"


# ============================================================================
# FAMILY PACK ENUMS
# ============================================================================

class FamilyRole(str, Enum):
    """Role d'un membre de la famille"""
    PRIMARY_CAREGIVER = "primary_caregiver"  # Aidant principal (reçoit tout)
    SECONDARY_CAREGIVER = "secondary_caregiver"  # Aidant secondaire
    EMERGENCY_CONTACT = "emergency_contact"  # Urgence uniquement
    INFORMATION_ONLY = "information_only"  # Lecture seule, notifications
    CHILD = "child"  # Enfant mineur (6-12 ans)
    TEEN = "teen"  # Adolescent (13-17 ans)
    SUBSCRIBER = "subscriber"  # Le souscripteur principal


class FamilyMemberType(str, Enum):
    """Type de membre famille selon l'age"""
    CHILD = "child"  # 6-12 ans
    TEEN = "teen"  # 13-17 ans
    ADULT = "adult"  # 18-64 ans
    SENIOR = "senior"  # 65+ ans


class EscalationLevel(str, Enum):
    """Niveau d'escalade"""
    INFO = "info"  # Information simple
    WARNING = "warning"  # Attention requise
    ALERT = "alert"  # Alerte active
    CRITICAL = "critical"  # Urgence critique


class DistressLevel(str, Enum):
    """Niveau de detresse detecte"""
    NONE = "none"
    LOW = "low"  # Inquietude legere
    MEDIUM = "medium"  # Preoccupant, proposer aide
    HIGH = "high"  # Urgent, alerter famille
    CRITICAL = "critical"  # Danger, alerte immediate + services urgence


class FamilyMessageType(str, Enum):
    """Type de message famille"""
    UPDATE = "update"  # Mise a jour simple
    QUESTION = "question"  # Question a la famille
    DECISION = "decision"  # Decision collective requise
    ALERT = "alert"  # Alerte automatique
    SUMMARY = "summary"  # Resume periodique
    RELAY = "relay"  # Message relaie par Luna


# ============================================================================
# MODELS
# ============================================================================

class Message(BaseModel):
    """Un message dans une conversation"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: MessageRole
    content: str
    channel: Channel
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = None

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis"""
        import json
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "channel": self.channel.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": json.dumps(self.metadata) if self.metadata else "",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "Message":
        """Crée depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            channel=Channel(data["channel"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=json.loads(data["metadata"]) if data.get("metadata") else None,
        )


class Conversation(BaseModel):
    """Une conversation avec un contact"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    contact_phone: str
    contact_name: Optional[str] = None
    relation: Optional[str] = None  # fils, aide-soignant, voisin...
    status: ConversationStatus = ConversationStatus.ACTIVE
    channel: Channel = Channel.APP
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    summary: Optional[str] = None  # Résumé auto-généré

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "contact_phone": self.contact_phone,
            "contact_name": self.contact_name or "",
            "relation": self.relation or "",
            "status": self.status.value,
            "channel": self.channel.value,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "message_count": str(self.message_count),
            "summary": self.summary or "",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "Conversation":
        """Crée depuis format Redis"""
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            contact_phone=data["contact_phone"],
            contact_name=data.get("contact_name") or None,
            relation=data.get("relation") or None,
            status=ConversationStatus(data["status"]),
            channel=Channel(data["channel"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            message_count=int(data.get("message_count", 0)),
            summary=data.get("summary") or None,
        )


class Instruction(BaseModel):
    """Une instruction donnée par le souscripteur à Luna"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    type: InstructionType
    description: str  # "Rappelle-moi de prendre mes médicaments à 8h"
    schedule: Optional[str] = None  # Cron expression ou datetime ISO
    action: ActionType
    target: str = "self"  # "self" ou phone number
    message_template: Optional[str] = None  # Template du message à envoyer
    priority: int = 5  # 1-10, 10 = urgent
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_executed: Optional[datetime] = None
    execution_count: int = 0

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "type": self.type.value,
            "description": self.description,
            "schedule": self.schedule or "",
            "action": self.action.value,
            "target": self.target,
            "message_template": self.message_template or "",
            "priority": str(self.priority),
            "enabled": "1" if self.enabled else "0",
            "created_at": self.created_at.isoformat(),
            "last_executed": self.last_executed.isoformat() if self.last_executed else "",
            "execution_count": str(self.execution_count),
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "Instruction":
        """Crée depuis format Redis"""
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            type=InstructionType(data["type"]),
            description=data["description"],
            schedule=data.get("schedule") or None,
            action=ActionType(data["action"]),
            target=data.get("target", "self"),
            message_template=data.get("message_template") or None,
            priority=int(data.get("priority", 5)),
            enabled=data.get("enabled") == "1",
            created_at=datetime.fromisoformat(data["created_at"]),
            last_executed=datetime.fromisoformat(data["last_executed"]) if data.get("last_executed") else None,
            execution_count=int(data.get("execution_count", 0)),
        )


class TaskState(BaseModel):
    """État d'une tâche en cours"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    type: ActionType
    status: TaskStatus = TaskStatus.PENDING
    description: str
    context: Optional[Dict[str, Any]] = None  # Détails spécifiques
    instruction_id: Optional[str] = None  # Si déclenché par instruction
    conversation_id: Optional[str] = None  # Si lié à une conversation
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
    error: Optional[str] = None

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        import json
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "type": self.type.value,
            "status": self.status.value,
            "description": self.description,
            "context": json.dumps(self.context) if self.context else "",
            "instruction_id": self.instruction_id or "",
            "conversation_id": self.conversation_id or "",
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
            "result": self.result or "",
            "error": self.error or "",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "TaskState":
        """Crée depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            type=ActionType(data["type"]),
            status=TaskStatus(data["status"]),
            description=data["description"],
            context=json.loads(data["context"]) if data.get("context") else None,
            instruction_id=data.get("instruction_id") or None,
            conversation_id=data.get("conversation_id") or None,
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            result=data.get("result") or None,
            error=data.get("error") or None,
        )


class Note(BaseModel):
    """Une note prise par Luna"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    content: str
    context: str  # visio, call, observation
    source: Optional[str] = None  # conversation_id ou "autonomous"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        import json
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "content": self.content,
            "context": self.context,
            "source": self.source or "",
            "tags": json.dumps(self.tags),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "Note":
        """Crée depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            content=data["content"],
            context=data["context"],
            source=data.get("source") or None,
            tags=json.loads(data["tags"]) if data.get("tags") else [],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class TrustedContact(BaseModel):
    """Un contact de confiance vérifié"""
    phone: str
    name: str
    relation: str  # fils, fille, voisin, aide-soignant...
    verified_at: datetime
    last_contact: Optional[datetime] = None
    preferred_channel: Channel = Channel.SMS
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None  # "07:00"
    emergency_only: bool = False  # Ne contacter qu'en urgence

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        return {
            "phone": self.phone,
            "name": self.name,
            "relation": self.relation,
            "verified_at": self.verified_at.isoformat(),
            "last_contact": self.last_contact.isoformat() if self.last_contact else "",
            "preferred_channel": self.preferred_channel.value,
            "quiet_hours_start": self.quiet_hours_start or "",
            "quiet_hours_end": self.quiet_hours_end or "",
            "emergency_only": "1" if self.emergency_only else "0",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "TrustedContact":
        """Crée depuis format Redis"""
        return cls(
            phone=data["phone"],
            name=data["name"],
            relation=data["relation"],
            verified_at=datetime.fromisoformat(data["verified_at"]),
            last_contact=datetime.fromisoformat(data["last_contact"]) if data.get("last_contact") else None,
            preferred_channel=Channel(data.get("preferred_channel", "sms")),
            quiet_hours_start=data.get("quiet_hours_start") or None,
            quiet_hours_end=data.get("quiet_hours_end") or None,
            emergency_only=data.get("emergency_only") == "1",
        )


class MemoryQuota(BaseModel):
    """Quotas mémoire par plan"""
    plan: PlanType
    memory_limit_bytes: int
    max_conversations: int
    max_messages_per_conv: int
    max_notes: int
    max_instructions: int

    @classmethod
    def for_plan(cls, plan: PlanType) -> "MemoryQuota":
        """Retourne les quotas pour un plan donné"""
        quotas = {
            PlanType.ESSENTIEL: cls(
                plan=PlanType.ESSENTIEL,
                memory_limit_bytes=100 * 1024 * 1024,  # 100 MB
                max_conversations=10,
                max_messages_per_conv=100,
                max_notes=50,
                max_instructions=10,
            ),
            PlanType.CONFORT: cls(
                plan=PlanType.CONFORT,
                memory_limit_bytes=500 * 1024 * 1024,  # 500 MB
                max_conversations=50,
                max_messages_per_conv=500,
                max_notes=200,
                max_instructions=50,
            ),
            PlanType.PREMIUM: cls(
                plan=PlanType.PREMIUM,
                memory_limit_bytes=2 * 1024 * 1024 * 1024,  # 2 GB
                max_conversations=1000,  # "Illimité" en pratique
                max_messages_per_conv=1000,
                max_notes=10000,  # "Illimité" en pratique
                max_instructions=200,
            ),
        }
        return quotas[plan]


class SubscriberProfile(BaseModel):
    """Profil complet du souscripteur - ce que Luna sait de son proprio"""
    tenant_id: int

    # --- Identite ---
    first_name: str = ""
    last_name: str = ""
    date_of_birth: Optional[str] = None  # "1985-03-15"
    address: str = ""
    city: str = ""
    department: str = ""
    phone: str = ""
    email: str = ""
    language: str = "fr"
    tutoiement: bool = True

    # --- Situation personnelle ---
    family_status: str = ""  # celibataire, marie, veuf, divorce
    children: str = ""  # "Marie (28 ans, fille), Thomas (25 ans, fils)"
    lives_alone: bool = True
    pets: str = ""
    autonomy: str = "autonome"  # autonome, aide_ponctuelle, aide_quotidienne
    mobility: str = "autonome"  # autonome, canne, fauteuil, ne_sort_plus

    # --- Situation professionnelle ---
    professional_status: str = ""  # actif, retraite, recherche, auto_entrepreneur, invalidite
    job_title: str = ""
    income_range: str = ""  # tranche pour evaluation aides
    siret: str = ""

    # --- Sante (factuel, jamais de conseil) ---
    doctor_name: str = ""
    doctor_phone: str = ""
    pharmacy: str = ""
    allergies: str = ""  # texte libre
    treatments: str = ""  # "Doliprane 1000 (8h, 20h), Metformine (midi)"
    conditions: str = ""  # "diabete type 2, hypertension"
    medical_contact_person: str = ""  # personne de confiance medicale
    mutual_name: str = ""
    mutual_number: str = ""
    carte_vitale: str = ""

    # --- Logement ---
    housing_type: str = ""  # appartement, maison, ehpad, residence_senior
    housing_status: str = ""  # proprietaire, locataire
    floor: str = ""  # "3eme, avec ascenseur"
    landlord_name: str = ""
    landlord_phone: str = ""
    home_insurance: str = ""  # numero contrat
    concierge: str = ""

    # --- Administratif ---
    tax_number: str = ""
    caf_number: str = ""
    france_travail_id: str = ""
    cpam_center: str = ""
    bank_name: str = ""
    bank_advisor: str = ""
    documents_expiry: str = ""  # JSON: {"cni": "2028-05-01", "passeport": "2030-11-15"}

    # --- Preferences ---
    tone: str = "chaleureux"  # chaleureux, formel, direct, humour
    wake_time: str = "08:00"
    sleep_time: str = "22:00"
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    sensitive_topics: str = ""  # sujets a eviter
    interests: str = ""  # centres d'interet
    habits: str = ""  # "cafe le matin, promenade a 14h"
    presentation: str = "l'assistante de {first_name}"  # comment Luna se presente aux tiers
    caution_mode: str = "assistif"  # passif | assistif | proactif | urgence_only

    # --- Instructions permanentes ---
    permanent_rules: str = ""  # regles toujours actives
    blacklist: str = ""  # personnes a eviter
    priorities: str = ""  # "ma fille passe toujours en premier"
    max_budget: str = ""  # "200 euros max pour un devis"

    # --- Meta ---
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        data = {}
        for field_name, value in self.__dict__.items():
            if field_name.startswith("_"):
                continue
            if isinstance(value, datetime):
                data[field_name] = value.isoformat()
            elif isinstance(value, bool):
                data[field_name] = "1" if value else "0"
            elif isinstance(value, int):
                data[field_name] = str(value)
            else:
                data[field_name] = str(value) if value is not None else ""
        return data

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "SubscriberProfile":
        """Cree depuis format Redis"""
        bool_fields = {"tutoiement", "lives_alone"}
        int_fields = {"tenant_id"}
        datetime_fields = {"created_at", "updated_at"}

        parsed = {}
        for key, value in data.items():
            if key in bool_fields:
                parsed[key] = value == "1"
            elif key in int_fields:
                parsed[key] = int(value) if value else 0
            elif key in datetime_fields:
                parsed[key] = datetime.fromisoformat(value) if value else datetime.utcnow()
            else:
                parsed[key] = value if value else None
        return cls(**{k: v for k, v in parsed.items() if v is not None})


# ============================================================================
# FAMILY PACK MODELS
# ============================================================================

class FamilyMember(BaseModel):
    """Un membre de la famille Luna"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    phone: str
    name: str
    relation: str  # fils, fille, petit-fils, parent, conjoint...
    member_type: FamilyMemberType = FamilyMemberType.ADULT
    role: FamilyRole = FamilyRole.INFORMATION_ONLY
    age: Optional[int] = None  # Age si connu (important pour mineurs)

    # Verification
    is_verified: bool = False
    verified_at: Optional[datetime] = None
    verification_code: Optional[str] = None  # OTP temporaire

    # Permissions
    can_see_history: bool = False  # Peut voir l'historique des conversations
    can_see_health: bool = False  # Peut voir les infos sante
    can_manage_instructions: bool = False  # Peut creer/modifier des instructions
    can_send_messages: bool = True  # Peut envoyer des messages via Luna
    can_receive_alerts: bool = True  # Recoit les alertes
    can_trigger_alerts: bool = False  # Peut declencher une alerte manuellement

    # Preferences
    preferred_channel: Channel = Channel.APP
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None  # "07:00"
    language: str = "fr"

    # Statut
    is_active: bool = True
    last_activity: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "phone": self.phone,
            "name": self.name,
            "relation": self.relation,
            "member_type": self.member_type.value,
            "role": self.role.value,
            "age": str(self.age) if self.age else "",
            "is_verified": "1" if self.is_verified else "0",
            "verified_at": self.verified_at.isoformat() if self.verified_at else "",
            "verification_code": self.verification_code or "",
            "can_see_history": "1" if self.can_see_history else "0",
            "can_see_health": "1" if self.can_see_health else "0",
            "can_manage_instructions": "1" if self.can_manage_instructions else "0",
            "can_send_messages": "1" if self.can_send_messages else "0",
            "can_receive_alerts": "1" if self.can_receive_alerts else "0",
            "can_trigger_alerts": "1" if self.can_trigger_alerts else "0",
            "preferred_channel": self.preferred_channel.value,
            "quiet_hours_start": self.quiet_hours_start or "",
            "quiet_hours_end": self.quiet_hours_end or "",
            "language": self.language,
            "is_active": "1" if self.is_active else "0",
            "last_activity": self.last_activity.isoformat() if self.last_activity else "",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "FamilyMember":
        """Cree depuis format Redis"""
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            phone=data["phone"],
            name=data["name"],
            relation=data["relation"],
            member_type=FamilyMemberType(data.get("member_type", "adult")),
            role=FamilyRole(data.get("role", "information_only")),
            age=int(data["age"]) if data.get("age") else None,
            is_verified=data.get("is_verified") == "1",
            verified_at=datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else None,
            verification_code=data.get("verification_code") or None,
            can_see_history=data.get("can_see_history") == "1",
            can_see_health=data.get("can_see_health") == "1",
            can_manage_instructions=data.get("can_manage_instructions") == "1",
            can_send_messages=data.get("can_send_messages", "1") == "1",
            can_receive_alerts=data.get("can_receive_alerts", "1") == "1",
            can_trigger_alerts=data.get("can_trigger_alerts") == "1",
            preferred_channel=Channel(data.get("preferred_channel", "app")),
            quiet_hours_start=data.get("quiet_hours_start") or None,
            quiet_hours_end=data.get("quiet_hours_end") or None,
            language=data.get("language", "fr"),
            is_active=data.get("is_active", "1") == "1",
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )

    def is_minor(self) -> bool:
        """Verifie si le membre est mineur (< 18 ans)"""
        if self.age is not None:
            return self.age < 18
        return self.member_type in [FamilyMemberType.CHILD, FamilyMemberType.TEEN]

    def needs_parental_consent(self) -> bool:
        """Verifie si le membre necessite un consentement parental (< 15 ans RGPD)"""
        if self.age is not None:
            return self.age < 15
        return self.member_type == FamilyMemberType.CHILD


class FamilyGroup(BaseModel):
    """Groupe familial Luna"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    name: str = "Ma famille"
    description: str = ""

    # Membres (liste de phones, details dans FamilyMember)
    member_phones: List[str] = Field(default_factory=list)

    # Parametres groupe
    allow_internal_messaging: bool = True  # Messages entre membres via Luna
    share_activity_summary: bool = True  # Resume hebdo a tous les membres
    summary_day: str = "sunday"  # Jour du resume hebdo
    summary_time: str = "18:00"

    # Escalade par defaut
    default_escalation_delay_minutes: int = 5  # Delai entre niveaux
    auto_escalate: bool = True  # Escalade automatique

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        import json
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "member_phones": json.dumps(self.member_phones),
            "allow_internal_messaging": "1" if self.allow_internal_messaging else "0",
            "share_activity_summary": "1" if self.share_activity_summary else "0",
            "summary_day": self.summary_day,
            "summary_time": self.summary_time,
            "default_escalation_delay_minutes": str(self.default_escalation_delay_minutes),
            "auto_escalate": "1" if self.auto_escalate else "0",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "FamilyGroup":
        """Cree depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            name=data.get("name", "Ma famille"),
            description=data.get("description", ""),
            member_phones=json.loads(data["member_phones"]) if data.get("member_phones") else [],
            allow_internal_messaging=data.get("allow_internal_messaging", "1") == "1",
            share_activity_summary=data.get("share_activity_summary", "1") == "1",
            summary_day=data.get("summary_day", "sunday"),
            summary_time=data.get("summary_time", "18:00"),
            default_escalation_delay_minutes=int(data.get("default_escalation_delay_minutes", 5)),
            auto_escalate=data.get("auto_escalate", "1") == "1",
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


class EscalationStage(BaseModel):
    """Etape d'escalade"""
    order: int  # 1, 2, 3...
    delay_minutes: int  # 0 = immediat, 5, 10, 15...
    target_roles: List[FamilyRole]  # Qui alerter a cette etape
    message_template: str  # Template du message
    include_emergency_numbers: bool = False  # Inclure 15/17/18/112

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order": self.order,
            "delay_minutes": self.delay_minutes,
            "target_roles": [r.value for r in self.target_roles],
            "message_template": self.message_template,
            "include_emergency_numbers": self.include_emergency_numbers,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationStage":
        return cls(
            order=data["order"],
            delay_minutes=data["delay_minutes"],
            target_roles=[FamilyRole(r) for r in data["target_roles"]],
            message_template=data["message_template"],
            include_emergency_numbers=data.get("include_emergency_numbers", False),
        )


class EscalationRule(BaseModel):
    """Regle d'escalade pour un type d'evenement"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    name: str  # "Alerte detresse ado"
    description: str = ""

    # Declencheurs
    trigger_distress_level: DistressLevel = DistressLevel.HIGH
    trigger_member_types: List[FamilyMemberType] = Field(default_factory=list)  # Vide = tous
    trigger_keywords: List[str] = Field(default_factory=list)  # Mots-cles additionnels

    # Etapes d'escalade
    stages: List[EscalationStage] = Field(default_factory=list)

    # Options
    enabled: bool = True
    notify_subscriber: bool = True  # Prevenir le souscripteur principal
    log_to_audit: bool = True

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        import json
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "trigger_distress_level": self.trigger_distress_level.value,
            "trigger_member_types": json.dumps([t.value for t in self.trigger_member_types]),
            "trigger_keywords": json.dumps(self.trigger_keywords),
            "stages": json.dumps([s.to_dict() for s in self.stages]),
            "enabled": "1" if self.enabled else "0",
            "notify_subscriber": "1" if self.notify_subscriber else "0",
            "log_to_audit": "1" if self.log_to_audit else "0",
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else "",
            "trigger_count": str(self.trigger_count),
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "EscalationRule":
        """Cree depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            name=data["name"],
            description=data.get("description", ""),
            trigger_distress_level=DistressLevel(data.get("trigger_distress_level", "high")),
            trigger_member_types=[FamilyMemberType(t) for t in json.loads(data["trigger_member_types"])] if data.get("trigger_member_types") else [],
            trigger_keywords=json.loads(data["trigger_keywords"]) if data.get("trigger_keywords") else [],
            stages=[EscalationStage.from_dict(s) for s in json.loads(data["stages"])] if data.get("stages") else [],
            enabled=data.get("enabled", "1") == "1",
            notify_subscriber=data.get("notify_subscriber", "1") == "1",
            log_to_audit=data.get("log_to_audit", "1") == "1",
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            last_triggered=datetime.fromisoformat(data["last_triggered"]) if data.get("last_triggered") else None,
            trigger_count=int(data.get("trigger_count", 0)),
        )


class FamilyMessage(BaseModel):
    """Message interne famille via Luna"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int

    # Expediteur/Destinataire
    from_phone: str  # Phone du membre ou "luna" ou "system"
    from_name: str
    to_phone: Optional[str] = None  # None = message groupe
    to_name: Optional[str] = None

    # Contenu
    content: str
    message_type: FamilyMessageType = FamilyMessageType.UPDATE

    # Pour les decisions collectives
    requires_response: bool = False
    response_deadline: Optional[datetime] = None
    responses: Dict[str, str] = Field(default_factory=dict)  # {phone: "yes/no/maybe"}

    # Statut
    is_read: bool = False
    read_at: Optional[datetime] = None
    read_by: List[str] = Field(default_factory=list)  # Phones des lecteurs

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    related_event_id: Optional[str] = None  # Si lie a un evenement (alerte, etc.)

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        import json
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "from_phone": self.from_phone,
            "from_name": self.from_name,
            "to_phone": self.to_phone or "",
            "to_name": self.to_name or "",
            "content": self.content,
            "message_type": self.message_type.value,
            "requires_response": "1" if self.requires_response else "0",
            "response_deadline": self.response_deadline.isoformat() if self.response_deadline else "",
            "responses": json.dumps(self.responses),
            "is_read": "1" if self.is_read else "0",
            "read_at": self.read_at.isoformat() if self.read_at else "",
            "read_by": json.dumps(self.read_by),
            "created_at": self.created_at.isoformat(),
            "related_event_id": self.related_event_id or "",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "FamilyMessage":
        """Cree depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            from_phone=data["from_phone"],
            from_name=data["from_name"],
            to_phone=data.get("to_phone") or None,
            to_name=data.get("to_name") or None,
            content=data["content"],
            message_type=FamilyMessageType(data.get("message_type", "update")),
            requires_response=data.get("requires_response") == "1",
            response_deadline=datetime.fromisoformat(data["response_deadline"]) if data.get("response_deadline") else None,
            responses=json.loads(data["responses"]) if data.get("responses") else {},
            is_read=data.get("is_read") == "1",
            read_at=datetime.fromisoformat(data["read_at"]) if data.get("read_at") else None,
            read_by=json.loads(data["read_by"]) if data.get("read_by") else [],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            related_event_id=data.get("related_event_id") or None,
        )


class FamilyAuditLog(BaseModel):
    """Log d'audit pour les actions Family Pack"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int

    # Action
    actor_phone: str  # Qui a fait l'action (phone ou "luna" ou "system")
    actor_name: str
    action: str  # "member_added", "alert_sent", "message_created", "escalation_triggered"...

    # Cible
    target_phone: Optional[str] = None
    target_name: Optional[str] = None

    # Details
    details: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "info"  # info, warning, alert, critical

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_redis(self) -> Dict[str, str]:
        """Convertit en format Redis HASH"""
        import json
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "actor_phone": self.actor_phone,
            "actor_name": self.actor_name,
            "action": self.action,
            "target_phone": self.target_phone or "",
            "target_name": self.target_name or "",
            "details": json.dumps(self.details),
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address or "",
            "user_agent": self.user_agent or "",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "FamilyAuditLog":
        """Cree depuis format Redis"""
        import json
        return cls(
            id=data["id"],
            tenant_id=int(data["tenant_id"]),
            actor_phone=data["actor_phone"],
            actor_name=data["actor_name"],
            action=data["action"],
            target_phone=data.get("target_phone") or None,
            target_name=data.get("target_name") or None,
            details=json.loads(data["details"]) if data.get("details") else {},
            severity=data.get("severity", "info"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            ip_address=data.get("ip_address") or None,
            user_agent=data.get("user_agent") or None,
        )


# ============================================================================
# DISTRESS DETECTION FOR FAMILY (Ados/Enfants)
# ============================================================================

class DistressKeywords:
    """Mots-cles de detection de detresse par categorie"""

    # Harcelement scolaire
    BULLYING = [
        "harcelement", "harcele", "harcelent", "harceleur",
        "moquent", "moque", "se moque", "moqueries",
        "insulte", "insultes", "insultent", "insulte",
        "frappe", "frappent", "tape", "tapent", "cogner",
        "personne me parle", "seul", "seule", "exclu", "exclue",
        "plus d'amis", "aucun ami", "deteste", "detestent",
        "rumeurs", "rumeur", "raconte des trucs",
        "photo", "photos", "video", "videos", "partage",  # Cyberharcelement
        "menace", "menaces", "menacent",
    ]

    # Detresse emotionnelle
    EMOTIONAL_DISTRESS = [
        "j'en peux plus", "je n'en peux plus", "en ai marre",
        "ca va pas", "ca ne va pas", "pas bien",
        "triste", "tristesse", "pleure", "pleurer",
        "angoisse", "anxieux", "anxieuse", "panique", "peur",
        "stress", "stresse", "stressant",
        "fatigue", "epuise", "epuisee", "plus la force",
        "nul", "nulle", "je suis nul", "je suis nulle",
        "personne m'aime", "personne ne m'aime",
        "comprend rien", "comprennent rien", "m'ecoute pas",
    ]

    # Pensees sombres (CRITIQUE - escalade immediate)
    DARK_THOUGHTS = [
        "mourir", "mort", "suicide", "suicider",
        "plus envie", "envie de rien", "a quoi bon",
        "disparaitre", "plus la", "partir",
        "faire du mal", "me faire du mal", "me blesser",
        "fin", "finir", "en finir", "tout arreter",
        "personne remarquerait", "manquerais a personne",
    ]

    # Violence/Abus
    ABUSE = [
        "frappe", "bat", "battu", "battue",
        "touche", "toucher", "attouchement",
        "force", "forcee", "oblige", "obligee",
        "fait peur", "j'ai peur de",
        "crie", "hurle", "engueule",
        "puni", "punie", "punition",
        "enferme", "enfermee", "sort pas",
    ]

    @classmethod
    def detect_level(cls, text: str) -> tuple[DistressLevel, List[str], str]:
        """
        Detecte le niveau de detresse et les mots-cles trouves.
        Retourne (niveau, mots_trouves, categorie)
        """
        text_lower = text.lower()
        found_keywords = []
        category = ""

        # Verifier pensees sombres en priorite (CRITICAL)
        for kw in cls.DARK_THOUGHTS:
            if kw in text_lower:
                found_keywords.append(kw)
                category = "dark_thoughts"
        if found_keywords:
            return DistressLevel.CRITICAL, found_keywords, category

        # Verifier abus (HIGH)
        found_keywords = []
        for kw in cls.ABUSE:
            if kw in text_lower:
                found_keywords.append(kw)
                category = "abuse"
        if found_keywords:
            return DistressLevel.HIGH, found_keywords, category

        # Verifier harcelement (HIGH si multiple, MEDIUM sinon)
        found_keywords = []
        for kw in cls.BULLYING:
            if kw in text_lower:
                found_keywords.append(kw)
                category = "bullying"
        if len(found_keywords) >= 2:
            return DistressLevel.HIGH, found_keywords, category
        elif found_keywords:
            return DistressLevel.MEDIUM, found_keywords, category

        # Verifier detresse emotionnelle (MEDIUM si multiple, LOW sinon)
        found_keywords = []
        for kw in cls.EMOTIONAL_DISTRESS:
            if kw in text_lower:
                found_keywords.append(kw)
                category = "emotional_distress"
        if len(found_keywords) >= 2:
            return DistressLevel.MEDIUM, found_keywords, category
        elif found_keywords:
            return DistressLevel.LOW, found_keywords, category

        return DistressLevel.NONE, [], ""


# ============================================================================
# FAMILY PACK QUOTAS
# ============================================================================

class FamilyQuota(BaseModel):
    """Quotas pour les plans Family Pack"""
    plan: PlanType
    max_family_members: int
    max_internal_messages_per_day: int
    include_senior: bool  # Inclut un senior dans le pack
    include_children: int  # Nombre d'enfants/ados inclus
    visio_minutes: int
    sms_alerts: int

    @classmethod
    def for_plan(cls, plan: PlanType) -> "FamilyQuota":
        """Retourne les quotas pour un plan Family Pack"""
        quotas = {
            PlanType.FAMILY_ESSENTIEL: cls(
                plan=PlanType.FAMILY_ESSENTIEL,
                max_family_members=4,  # 2 adultes + 2 enfants
                max_internal_messages_per_day=50,
                include_senior=False,
                include_children=2,
                visio_minutes=60,
                sms_alerts=100,
            ),
            PlanType.FAMILY_CONFORT: cls(
                plan=PlanType.FAMILY_CONFORT,
                max_family_members=7,  # 2 adultes + 4 enfants + 1 senior
                max_internal_messages_per_day=200,
                include_senior=True,
                include_children=4,
                visio_minutes=180,
                sms_alerts=300,
            ),
            PlanType.FAMILY_PREMIUM: cls(
                plan=PlanType.FAMILY_PREMIUM,
                max_family_members=15,  # Famille elargie
                max_internal_messages_per_day=1000,  # Quasi illimite
                include_senior=True,
                include_children=10,
                visio_minutes=300,
                sms_alerts=500,
            ),
        }
        return quotas.get(plan)


# ============================================================================
# UNIFIED MEMORY - Session temps reel multi-canal
# ============================================================================

class SessionStatus(str, Enum):
    """Statut de la session active"""
    IDLE = "idle"              # Pas d'interaction en cours
    ACTIVE = "active"          # Interaction en cours
    WAITING = "waiting"        # Attend reponse utilisateur
    PROCESSING = "processing"  # Luna traite une demande


class MoodIndicator(str, Enum):
    """Indicateur d'humeur detecte"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    ANXIOUS = "anxious"
    CONFUSED = "confused"
    URGENT = "urgent"


class UnifiedSession(BaseModel):
    """Session active multi-canal"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    active_channel: Channel = Channel.APP
    status: SessionStatus = SessionStatus.IDLE
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    # Contexte temps reel
    current_topic: Optional[str] = None
    current_mood: MoodIndicator = MoodIndicator.NEUTRAL
    pending_action: Optional[str] = None  # Action en attente
    # Infos canal
    channel_session_id: Optional[str] = None  # ID session Tavus/Twilio
    is_voice_active: bool = False
    is_video_active: bool = False

    def to_redis(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "active_channel": self.active_channel.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "current_topic": self.current_topic or "",
            "current_mood": self.current_mood.value,
            "pending_action": self.pending_action or "",
            "channel_session_id": self.channel_session_id or "",
            "is_voice_active": "1" if self.is_voice_active else "0",
            "is_video_active": "1" if self.is_video_active else "0",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "UnifiedSession":
        return cls(
            id=data.get("id", ""),
            tenant_id=int(data.get("tenant_id", 0)),
            active_channel=Channel(data.get("active_channel", "app")),
            status=SessionStatus(data.get("status", "idle")),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else datetime.utcnow(),
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else datetime.utcnow(),
            current_topic=data.get("current_topic") or None,
            current_mood=MoodIndicator(data.get("current_mood", "neutral")),
            pending_action=data.get("pending_action") or None,
            channel_session_id=data.get("channel_session_id") or None,
            is_voice_active=data.get("is_voice_active") == "1",
            is_video_active=data.get("is_video_active") == "1",
        )


class UnifiedMessage(BaseModel):
    """Message unifie (tous canaux)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    channel: Channel
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # Metadata
    audio_duration_sec: Optional[float] = None  # Si voix
    detected_mood: Optional[MoodIndicator] = None
    detected_intent: Optional[str] = None  # Intent NLU
    tool_calls: Optional[List[str]] = None  # Outils appeles par Luna
    # Lien avec session
    session_id: Optional[str] = None

    def to_redis(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "channel": self.channel.value,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "audio_duration_sec": str(self.audio_duration_sec) if self.audio_duration_sec else "",
            "detected_mood": self.detected_mood.value if self.detected_mood else "",
            "detected_intent": self.detected_intent or "",
            "tool_calls": ",".join(self.tool_calls) if self.tool_calls else "",
            "session_id": self.session_id or "",
        }

    @classmethod
    def from_redis(cls, data: Dict[str, str]) -> "UnifiedMessage":
        return cls(
            id=data.get("id", ""),
            tenant_id=int(data.get("tenant_id", 0)),
            channel=Channel(data.get("channel", "app")),
            role=MessageRole(data.get("role", "subscriber")),
            content=data.get("content", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            audio_duration_sec=float(data["audio_duration_sec"]) if data.get("audio_duration_sec") else None,
            detected_mood=MoodIndicator(data["detected_mood"]) if data.get("detected_mood") else None,
            detected_intent=data.get("detected_intent") or None,
            tool_calls=data["tool_calls"].split(",") if data.get("tool_calls") else None,
            session_id=data.get("session_id") or None,
        )


class ChannelHandoff(BaseModel):
    """Transfert de canal (ex: chat -> voice)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: int
    from_channel: Channel
    to_channel: Channel
    reason: str  # "user_request", "escalation", "timeout"
    context_summary: str  # Resume du contexte transfere
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def to_redis(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "tenant_id": str(self.tenant_id),
            "from_channel": self.from_channel.value,
            "to_channel": self.to_channel.value,
            "reason": self.reason,
            "context_summary": self.context_summary,
            "timestamp": self.timestamp.isoformat(),
        }
