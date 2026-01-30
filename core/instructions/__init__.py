"""
Luna Instructions Module - Gestion des instructions du souscripteur

Ce module gère:
- Parsing des instructions en langage naturel
- Planification des instructions récurrentes
- Exécution automatique selon le planning
- Templates d'instructions courantes
"""

from .parser import (
    InstructionParser,
    ParsedInstruction,
    ParsedTime,
    ActionType,
    RecurrenceType,
    ConditionType,
)
from .scheduler import InstructionScheduler, ScheduledTask, TaskStatus
from .executor import InstructionExecutor, ExecutionResult, ExecutionStatus
from .templates import (
    InstructionTemplate,
    TemplateCategory,
    COMMON_TEMPLATES,
    get_templates_by_category,
    get_template_by_id,
    find_matching_template,
    get_suggested_templates_for_new_user,
)

__all__ = [
    # Parser
    "InstructionParser",
    "ParsedInstruction",
    "ParsedTime",
    "ActionType",
    "RecurrenceType",
    "ConditionType",
    # Scheduler
    "InstructionScheduler",
    "ScheduledTask",
    "TaskStatus",
    # Executor
    "InstructionExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    # Templates
    "InstructionTemplate",
    "TemplateCategory",
    "COMMON_TEMPLATES",
    "get_templates_by_category",
    "get_template_by_id",
    "find_matching_template",
    "get_suggested_templates_for_new_user",
]
