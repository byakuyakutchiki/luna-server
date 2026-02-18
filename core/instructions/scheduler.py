"""
Luna Instruction Scheduler - Planification des instructions

Gère la planification et le déclenchement des instructions:
- Calcul des prochaines exécutions
- Gestion des récurrences
- File d'attente des tâches
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, time
from dataclasses import dataclass, field
from enum import Enum
import heapq

from .parser import ParsedInstruction, RecurrenceType, ConditionType

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Statut d'une tâche planifiée"""
    SCHEDULED = "scheduled"
    PENDING = "pending"  # Prête à être exécutée
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass(order=True)
class ScheduledTask:
    """Tâche planifiée dans la file d'attente"""
    scheduled_at: datetime  # Utilisé pour le tri
    instruction_id: str = field(compare=False)
    tenant_id: int = field(compare=False)
    instruction: ParsedInstruction = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.SCHEDULED, compare=False)
    attempt: int = field(default=0, compare=False)
    max_attempts: int = field(default=3, compare=False)
    created_at: datetime = field(default_factory=datetime.utcnow, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)
    result: Optional[str] = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)

    def is_due(self) -> bool:
        """Vérifie si la tâche est prête à être exécutée"""
        return datetime.utcnow() >= self.scheduled_at

    def time_until_due(self) -> timedelta:
        """Temps restant avant exécution"""
        return self.scheduled_at - datetime.utcnow()


class InstructionScheduler:
    """
    Planificateur d'instructions Luna.

    Responsabilités:
    - Calculer les prochaines exécutions
    - Maintenir une file de priorité des tâches
    - Gérer les récurrences
    - Réplanifier après exécution
    """

    def __init__(self):
        self._task_queue: List[ScheduledTask] = []
        self._tasks_by_id: Dict[str, ScheduledTask] = {}
        self._tasks_by_instruction: Dict[str, List[str]] = {}  # instruction_id -> [task_ids]

    def schedule(
        self,
        instruction_id: str,
        tenant_id: int,
        instruction: ParsedInstruction,
        start_from: Optional[datetime] = None,
    ) -> ScheduledTask:
        """
        Planifie une instruction.

        Args:
            instruction_id: ID unique de l'instruction
            tenant_id: ID du tenant
            instruction: L'instruction parsée
            start_from: Date de début (défaut: maintenant)

        Returns:
            La tâche planifiée
        """
        start_from = start_from or datetime.utcnow()

        # Calcule la prochaine exécution
        next_run = self._calculate_next_run(instruction, start_from)

        if not next_run:
            logger.warning(f"Could not calculate next run for instruction {instruction_id}")
            if instruction.recurrence != RecurrenceType.ONCE:
                # Recurring sans heure : planifier demain à 08:00 au lieu de boucler
                tomorrow_8am = datetime.combine(
                    (start_from + timedelta(days=1)).date(), time(hour=8, minute=0)
                )
                logger.info(
                    f"Recurring instruction {instruction_id} has no time, "
                    f"defaulting to {tomorrow_8am.isoformat()}"
                )
                next_run = tomorrow_8am
            else:
                # One-shot sans timing : exécuter maintenant
                next_run = datetime.utcnow()

        # Crée la tâche
        import uuid
        task = ScheduledTask(
            scheduled_at=next_run,
            instruction_id=instruction_id,
            tenant_id=tenant_id,
            instruction=instruction,
        )

        # Ajoute à la file
        task_id = str(uuid.uuid4())
        self._tasks_by_id[task_id] = task
        heapq.heappush(self._task_queue, task)

        # Index par instruction
        if instruction_id not in self._tasks_by_instruction:
            self._tasks_by_instruction[instruction_id] = []
        self._tasks_by_instruction[instruction_id].append(task_id)

        logger.info(
            f"Scheduled instruction {instruction_id} for {next_run.isoformat()}"
        )

        return task

    def _calculate_next_run(
        self,
        instruction: ParsedInstruction,
        from_time: datetime,
    ) -> Optional[datetime]:
        """Calcule la prochaine exécution d'une instruction"""

        if not instruction.scheduled_time:
            # Pas d'heure spécifiée
            if instruction.recurrence == RecurrenceType.ONCE:
                return from_time  # Exécuter maintenant
            return None

        target_time = time(
            hour=instruction.scheduled_time.hour,
            minute=instruction.scheduled_time.minute,
        )

        # Commence par aujourd'hui à l'heure cible
        candidate = datetime.combine(from_time.date(), target_time)

        # Si l'heure est passée, passe au jour suivant
        if candidate <= from_time:
            candidate += timedelta(days=1)

        # Ajuste selon la récurrence
        if instruction.recurrence == RecurrenceType.ONCE:
            return candidate

        elif instruction.recurrence == RecurrenceType.DAILY:
            return candidate

        elif instruction.recurrence == RecurrenceType.WEEKDAYS:
            while candidate.weekday() >= 5:  # Samedi=5, Dimanche=6
                candidate += timedelta(days=1)
            return candidate

        elif instruction.recurrence == RecurrenceType.WEEKEND:
            while candidate.weekday() < 5:  # Pas encore le week-end
                candidate += timedelta(days=1)
            return candidate

        elif instruction.recurrence == RecurrenceType.WEEKLY:
            if instruction.scheduled_days:
                # Trouve le prochain jour planifié
                for _ in range(7):
                    if candidate.weekday() in instruction.scheduled_days:
                        return candidate
                    candidate += timedelta(days=1)
            return candidate

        elif instruction.recurrence == RecurrenceType.MONTHLY:
            # Premier du mois prochain si déjà passé
            if candidate.day > 1:
                if candidate.month == 12:
                    candidate = candidate.replace(year=candidate.year + 1, month=1, day=1)
                else:
                    candidate = candidate.replace(month=candidate.month + 1, day=1)
            return datetime.combine(candidate.date(), target_time)

        return candidate

    def get_next_task(self) -> Optional[ScheduledTask]:
        """Récupère la prochaine tâche à exécuter (sans la retirer)"""
        while self._task_queue:
            task = self._task_queue[0]
            if task.status == TaskStatus.SCHEDULED:
                return task
            # Retire les tâches terminées/annulées
            heapq.heappop(self._task_queue)
        return None

    def pop_due_tasks(self) -> List[ScheduledTask]:
        """Récupère toutes les tâches prêtes à être exécutées"""
        due_tasks = []
        now = datetime.utcnow()

        while self._task_queue:
            task = self._task_queue[0]
            if task.status != TaskStatus.SCHEDULED:
                heapq.heappop(self._task_queue)
                continue
            if task.scheduled_at <= now:
                task.status = TaskStatus.PENDING
                due_tasks.append(heapq.heappop(self._task_queue))
            else:
                break

        return due_tasks

    def complete_task(
        self,
        task: ScheduledTask,
        result: str = "",
        reschedule: bool = True,
    ) -> Optional[ScheduledTask]:
        """
        Marque une tâche comme terminée et replanifie si récurrente.

        Args:
            task: La tâche terminée
            result: Résultat de l'exécution
            reschedule: Si True, replanifie les tâches récurrentes

        Returns:
            La nouvelle tâche planifiée si replanifiée, None sinon
        """
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.utcnow()
        task.result = result

        logger.info(f"Task completed for instruction {task.instruction_id}")

        # Replanifie si récurrent
        if reschedule and task.instruction.recurrence != RecurrenceType.ONCE:
            return self.schedule(
                instruction_id=task.instruction_id,
                tenant_id=task.tenant_id,
                instruction=task.instruction,
                start_from=datetime.utcnow(),
            )

        return None

    def fail_task(
        self,
        task: ScheduledTask,
        error: str,
        retry: bool = True,
    ) -> Optional[ScheduledTask]:
        """
        Marque une tâche comme échouée et retente si possible.

        Args:
            task: La tâche échouée
            error: Message d'erreur
            retry: Si True, retente si tentatives restantes

        Returns:
            La tâche replanifiée si retry, None sinon
        """
        task.attempt += 1
        task.error = error

        if retry and task.attempt < task.max_attempts:
            # Replanifie avec délai exponentiel
            delay = timedelta(minutes=5 * (2 ** task.attempt))
            task.scheduled_at = datetime.utcnow() + delay
            task.status = TaskStatus.SCHEDULED
            heapq.heappush(self._task_queue, task)
            logger.warning(
                f"Task failed for instruction {task.instruction_id}, "
                f"retry {task.attempt}/{task.max_attempts} in {delay}"
            )
            return task
        else:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            logger.error(
                f"Task failed permanently for instruction {task.instruction_id}: {error}"
            )
            return None

    def cancel_instruction(self, instruction_id: str) -> int:
        """
        Annule toutes les tâches d'une instruction.

        Returns:
            Nombre de tâches annulées
        """
        cancelled = 0
        task_ids = self._tasks_by_instruction.get(instruction_id, [])

        for task_id in task_ids:
            task = self._tasks_by_id.get(task_id)
            if task and task.status == TaskStatus.SCHEDULED:
                task.status = TaskStatus.CANCELLED
                cancelled += 1

        logger.info(f"Cancelled {cancelled} tasks for instruction {instruction_id}")
        return cancelled

    def get_scheduled_tasks(
        self,
        tenant_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[ScheduledTask]:
        """Récupère les tâches planifiées"""
        tasks = []
        for task in sorted(self._task_queue):
            if task.status != TaskStatus.SCHEDULED:
                continue
            if tenant_id and task.tenant_id != tenant_id:
                continue
            tasks.append(task)
            if len(tasks) >= limit:
                break
        return tasks

    def get_task_count(self, tenant_id: Optional[int] = None) -> Dict[str, int]:
        """Compte les tâches par statut"""
        counts = {status.value: 0 for status in TaskStatus}

        for task in self._tasks_by_id.values():
            if tenant_id and task.tenant_id != tenant_id:
                continue
            counts[task.status.value] += 1

        return counts

    def get_next_execution_time(
        self,
        instruction_id: str,
    ) -> Optional[datetime]:
        """Récupère la prochaine exécution d'une instruction"""
        task_ids = self._tasks_by_instruction.get(instruction_id, [])

        for task_id in task_ids:
            task = self._tasks_by_id.get(task_id)
            if task and task.status == TaskStatus.SCHEDULED:
                return task.scheduled_at

        return None
