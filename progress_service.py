from memory_service import read_memory


def get_progress_summary():
    memory = read_memory()
    progression = memory.get("progression", {})
    quiz_results = progression.get("quiz_results", [])
    planning = memory.get("planning", [])

    total_quiz = len(quiz_results)
    score_moyen = progression.get("score_moyen")
    chapitres_revises = progression.get("chapitres_revises", [])

    total_tasks = len(planning)

    done_tasks = len([
        task for task in planning
        if task.get("status") == "terminé"
    ])

    return {
        "total_quiz": total_quiz,
        "score_moyen": score_moyen,
        "chapitres_revises": chapitres_revises,
        "total_tasks": total_tasks,
        "done_tasks": done_tasks
    }