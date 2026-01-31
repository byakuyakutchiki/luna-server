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
    APP = "app"
    SMS = "sms"
    CALL = "call"
    VISIO = "visio"
    WEBHOOK = "webhook"


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
