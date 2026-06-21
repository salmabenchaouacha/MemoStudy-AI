"""
Génération et correction de quiz.

- generate_quiz : demande à Gemini un JSON structuré de questions, avec pour
  chaque question soit des choix QCM + réponse correcte, soit des points clés
  attendus (questions ouvertes). Repli template si l'IA échoue.
- correct_quiz : note les QCM/questions directes localement (comparaison
  texte), et envoie les réponses ouvertes à Gemini pour notation + feedback.
  Le score global est calculé automatiquement, plus de saisie manuelle.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List

from models import (
    Memory,
    QuestionFeedback,
    QuizCorrection,
    QuizQuestion,
    QuizQuestionType,
    QuizResult,
)
from services.gemini_client import ChatTurn, GeminiUnavailableError, generate
from services.memory_service import memory_transaction, read_memory

logger = logging.getLogger(__name__)


# --- Génération ---

def _quiz_system_prompt(memory: Memory, chapter: str, number_of_questions: int) -> str:
    return f"""Tu es un générateur de quiz pour un assistant de révision.

Étudiant : niveau {memory.student.niveau.value}, matière {memory.student.matiere or "générale"}.
Chapitre demandé : {chapter}
Nombre de questions : {number_of_questions}

Génère un mélange équilibré de types de questions :
- "qcm" : question à choix multiples avec 3 à 4 options plausibles
- "question directe" : réponse courte attendue (un mot, une phrase courte)
- "question ouverte" : réponse plus longue à rédiger

Réponds UNIQUEMENT avec un JSON valide (aucun texte avant/après, pas de
balises markdown), sous la forme d'une liste d'objets avec ces clés :
- "id" (entier, 1 à {number_of_questions})
- "question" (string)
- "type" ("qcm" | "question directe" | "question ouverte")
- "options" (liste de strings, UNIQUEMENT si type="qcm", sinon liste vide)
- "correct_answer" (string, réponse correcte exacte, pour "qcm" et
  "question directe" ; null pour "question ouverte")
- "expected_points" (liste de 2-3 strings, points clés attendus dans la
  réponse, UNIQUEMENT si type="question ouverte", sinon liste vide)
"""


def _parse_quiz_json(raw_text: str, chapter: str, matiere: str, niveau: str) -> List[QuizQuestion]:
    cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data = json.loads(cleaned)

    questions = []
    for item in data:
        questions.append(
            QuizQuestion(
                id=item["id"],
                chapter=chapter,
                matiere=matiere,
                niveau=niveau,
                question=item["question"],
                type=item.get("type", "question directe"),
                options=item.get("options") or [],
                correct_answer=item.get("correct_answer"),
                expected_points=item.get("expected_points") or [],
            )
        )
    return questions


def _template_fallback_quiz(chapter: str, number_of_questions: int, matiere: str, niveau: str) -> List[QuizQuestion]:
    questions = []
    for i in range(1, number_of_questions + 1):
        questions.append(
            QuizQuestion(
                id=i,
                chapter=chapter,
                matiere=matiere,
                niveau=niveau,
                question=f"[Mode secours] Explique un point important du chapitre '{chapter}' en {matiere}.",
                type=QuizQuestionType.ouverte,
                expected_points=["Définition correcte", "Exemple pertinent"],
            )
        )
    return questions


def generate_quiz(chapter: str, number_of_questions: int = 5) -> List[QuizQuestion]:
    memory = read_memory()
    matiere = memory.student.matiere or "matière"
    niveau = memory.student.niveau.value

    system_prompt = _quiz_system_prompt(memory, chapter, number_of_questions)
    history = [ChatTurn(role="user", text=f"Génère le quiz pour le chapitre : {chapter}")]

    try:
        raw_text = generate(system_instruction=system_prompt, history=history, temperature=0.5)
        return _parse_quiz_json(raw_text, chapter, matiere, niveau)
    except (GeminiUnavailableError, json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Génération de quiz par IA indisponible/invalide, repli template : %s", exc)
        return _template_fallback_quiz(chapter, number_of_questions, matiere, niveau)


# --- Correction ---

def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _correct_closed_question(question: QuizQuestion, user_answer: str) -> QuestionFeedback:
    """QCM et questions directes : comparaison texte locale, pas d'appel IA."""
    is_correct = _normalize(user_answer) == _normalize(question.correct_answer or "")
    return QuestionFeedback(
        question_id=question.id,
        is_correct=is_correct,
        points_awarded=1 if is_correct else 0,
        points_max=1,
        explanation=(
            "Bonne réponse !" if is_correct
            else f"Réponse correcte attendue : {question.correct_answer}"
        ),
    )


def _open_questions_correction_prompt(items: List[Dict]) -> str:
    formatted = "\n\n".join(
        f"Question {it['id']} : {it['question']}\n"
        f"Points clés attendus : {', '.join(it['expected_points']) or 'aucun point précisé'}\n"
        f"Réponse de l'étudiant : {it['user_answer'] or '(aucune réponse donnée)'}"
        for it in items
    )

    return f"""Tu es un correcteur de quiz. Pour chaque question ouverte ci-dessous,
évalue la réponse de l'étudiant par rapport aux points clés attendus.

{formatted}

Réponds UNIQUEMENT avec un JSON valide (liste d'objets, un par question), clés :
- "question_id" (entier)
- "points_awarded" (nombre entre 0 et 1, peut être décimal, ex: 0.5 si réponse partielle)
- "explanation" (string courte, en français, expliquant la note donnée à l'étudiant)
"""


def _correct_open_questions(open_items: List[Dict]) -> Dict[int, QuestionFeedback]:
    if not open_items:
        return {}

    system_prompt = _open_questions_correction_prompt(open_items)
    history = [ChatTurn(role="user", text="Corrige ces réponses.")]

    try:
        raw_text = generate(system_instruction=system_prompt, history=history, temperature=0.3)
        cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)

        results = {}
        for item in data:
            qid = item["question_id"]
            points = max(0.0, min(1.0, float(item.get("points_awarded", 0))))
            results[qid] = QuestionFeedback(
                question_id=qid,
                is_correct=None,
                points_awarded=points,
                points_max=1,
                explanation=item.get("explanation", ""),
            )
        return results
    except (GeminiUnavailableError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("Correction IA des questions ouvertes indisponible, note neutre appliquée : %s", exc)
        return {
            it["id"]: QuestionFeedback(
                question_id=it["id"],
                is_correct=None,
                points_awarded=0.5,
                points_max=1,
                explanation="Correction automatique indisponible : note neutre appliquée. Relis ta réponse manuellement.",
            )
            for it in open_items
        }


def correct_quiz(questions: List[QuizQuestion], user_answers: Dict[int, str]) -> QuizCorrection:
    """Corrige un quiz complet : QCM/directes en local, ouvertes via l'IA.
    Calcule le score global automatiquement (0-100)."""
    closed_feedback: List[QuestionFeedback] = []
    open_items: List[Dict] = []

    for q in questions:
        answer = user_answers.get(q.id, "")
        if q.type in (QuizQuestionType.qcm, QuizQuestionType.directe):
            closed_feedback.append(_correct_closed_question(q, answer))
        else:
            open_items.append({
                "id": q.id,
                "question": q.question,
                "expected_points": q.expected_points,
                "user_answer": answer,
            })

    open_feedback_map = _correct_open_questions(open_items)
    open_feedback = [open_feedback_map[it["id"]] for it in open_items if it["id"] in open_feedback_map]

    all_feedback = sorted(closed_feedback + open_feedback, key=lambda f: f.question_id)

    total_awarded = sum(f.points_awarded for f in all_feedback)
    total_max = sum(f.points_max for f in all_feedback) or 1
    score = round((total_awarded / total_max) * 100)

    return QuizCorrection(feedback=all_feedback, score=score)


def save_quiz_result(chapter: str, score: int, feedback: str) -> Memory:
    with memory_transaction() as memory:
        memory.progression.quiz_results.append(
            QuizResult(chapter=chapter, score=score, feedback=feedback)
        )
        if chapter not in memory.progression.chapitres_revises:
            memory.progression.chapitres_revises.append(chapter)
    return memory