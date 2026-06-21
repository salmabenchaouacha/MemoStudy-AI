"""Gestion du planning de révision (CRUD simple sur Memory.planning)."""

from __future__ import annotations

from typing import List

from models import Memory, PlanningTask, TaskStatus
from services.memory_service import memory_transaction, read_memory


def add_planning_task(task: str, duration_minutes: int) -> PlanningTask:
    with memory_transaction() as memory:
        new_task = PlanningTask(
            id=memory.next_planning_id(),
            task=task,
            duration_minutes=duration_minutes,
        )
        memory.planning.append(new_task)
    return new_task


def mark_task_done(task_id: int) -> Memory:
    with memory_transaction() as memory:
        for task in memory.planning:
            if task.id == task_id:
                task.status = TaskStatus.termine
    return memory


def remove_planning_task(task_id: int) -> Memory:
    with memory_transaction() as memory:
        memory.planning = [t for t in memory.planning if t.id != task_id]
    return memory


def get_planning() -> List[PlanningTask]:
    return read_memory().planning