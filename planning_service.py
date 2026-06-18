from datetime import date
from memory_service import read_memory, save_memory


def add_planning_task(task: str, duration_minutes: int):
    memory = read_memory()

    memory.setdefault("planning", [])

    new_task = {
        "id": len(memory["planning"]) + 1,
        "date": str(date.today()),
        "task": task,
        "duration_minutes": duration_minutes,
        "status": "à faire"
    }

    memory["planning"].append(new_task)
    save_memory(memory)

    return new_task


def mark_task_done(task_id: int):
    memory = read_memory()

    for task in memory.get("planning", []):
        if task["id"] == task_id:
            task["status"] = "terminé"

    save_memory(memory)
    return memory


def get_planning():
    memory = read_memory()
    return memory.get("planning", [])