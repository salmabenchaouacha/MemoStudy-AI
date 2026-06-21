"""Agrégations pour le tableau de bord."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel

from models import TaskStatus
from services.memory_service import read_memory


class ChapterScore(BaseModel):
    chapter: str
    score_moyen: float
    nb_quiz: int


class ProgressSummary(BaseModel):
    total_quiz: int
    score_moyen: Optional[float]
    chapitres_revises: List[str]
    scores_par_chapitre: List[ChapterScore]
    total_tasks: int
    done_tasks: int


def get_progress_summary() -> ProgressSummary:
    memory = read_memory()
    progression = memory.progression
    quiz_results = progression.quiz_results

    scores_by_chapter: Dict[str, List[int]] = {}
    for result in quiz_results:
        scores_by_chapter.setdefault(result.chapter, []).append(result.score)

    scores_par_chapitre = [
        ChapterScore(
            chapter=chapter,
            score_moyen=round(sum(scores) / len(scores), 2),
            nb_quiz=len(scores),
        )
        for chapter, scores in scores_by_chapter.items()
    ]

    done_tasks = sum(1 for t in memory.planning if t.status == TaskStatus.termine)

    return ProgressSummary(
        total_quiz=len(quiz_results),
        score_moyen=progression.score_moyen,
        chapitres_revises=progression.chapitres_revises,
        scores_par_chapitre=scores_par_chapitre,
        total_tasks=len(memory.planning),
        done_tasks=done_tasks,
    )