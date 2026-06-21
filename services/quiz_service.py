"""
Génération de quiz.

Avant: questions 100% template, jamais générées par l'IA malgré le nom du
projet. Ici on demande à Gemini un JSON structuré de questions adaptées au
chapitre et au profil ; si ça échoue, on retombe sur un template simple
(mais clairement étiqueté comme tel) pour ne jamais planter l'UI.
"""

from __future__ import annotations

import json
import logging
from typing import List

from models import Memory, QuizResult, QuizQuestion
from services.gemini_client import ChatTurn, GeminiUnavailableError, generate
from services.memory_service import memory_transaction, read_memory

logger = logging.getLogger(__name__)


def _quiz_system_prompt(memory: Memory, chapter: str, number_of_questions: int) -> str:
    return f"""Tu es un générateur de quiz pour un assistant de révision.

Étudiant : niveau {memory.student.niveau.value}, matière {memory.student.matiere or "générale"}.
Chapitre demandé : {chapter}
Nombre de questions : {number_of_questions}

Réponds UNIQUEMENT avec un JSON valide (aucun texte avant/après, pas de balises
markdown), sous la forme d'une liste d'objets avec exactement ces clés :
"id" (entier, 1 à {number_of_questions}), "question" (string), "type"
("question ouverte" ou "question directe").
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
            )
        )
    return questions


def _template_fallback_quiz(chapter: str, number_of_questions: int, matiere: str, niveau: str) -> List[QuizQuestion]:
    questions = []
    for i in range(1, number_of_questions + 1):
        question_type = "question ouverte" if i % 2 == 0 else "question directe"
        questions.append(
            QuizQuestion(
                id=i,
                chapter=chapter,
                matiere=matiere,
                niveau=niveau,
                question=f"[Mode secours] Explique un point important du chapitre '{chapter}' en {matiere}.",
                type=question_type,
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


def save_quiz_result(chapter: str, score: int, feedback: str) -> Memory:
    with memory_transaction() as memory:
        memory.progression.quiz_results.append(
            QuizResult(chapter=chapter, score=score, feedback=feedback)
        )
        if chapter not in memory.progression.chapitres_revises:
            memory.progression.chapitres_revises.append(chapter)
    return memory