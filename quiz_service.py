from memory_service import read_memory, save_memory


def generate_quiz(chapter: str, number_of_questions: int = 5) -> list[dict]:
    memory = read_memory()
    student = memory.get("student", {})
    niveau = student.get("niveau", "intermédiaire")
    matiere = student.get("matiere", "matière")

    questions = []

    for i in range(1, number_of_questions + 1):
        question_type = "question ouverte" if i % 2 == 0 else "question directe"

        questions.append({
            "id": i,
            "chapter": chapter,
            "matiere": matiere,
            "niveau": niveau,
            "question": f"Question {i} : Explique un point important du chapitre '{chapter}' en {matiere}.",
            "type": question_type
        })

    return questions


def save_quiz_result(chapter: str, score: int, feedback: str):
    memory = read_memory()

    memory.setdefault("progression", {})
    memory["progression"].setdefault("chapitres_revises", [])
    memory["progression"].setdefault("quiz_results", [])

    memory["progression"]["quiz_results"].append({
        "chapter": chapter,
        "score": score,
        "feedback": feedback
    })

    scores = [
        result["score"]
        for result in memory["progression"]["quiz_results"]
    ]

    memory["progression"]["score_moyen"] = round(sum(scores) / len(scores), 2)

    if chapter not in memory["progression"]["chapitres_revises"]:
        memory["progression"]["chapitres_revises"].append(chapter)

    save_memory(memory)
    return memory