"""
Modèles de données validés (Pydantic) pour toute la mémoire de l'application.

Pourquoi Pydantic ici plutôt que des dicts bruts :
- validation automatique (types, valeurs par défaut) à la lecture ET à l'écriture
- autocomplete / typage dans tout le reste du code
- un seul endroit où la "forme" de la mémoire est définie
"""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Niveau(str, Enum):
    debutant = "débutant"
    intermediaire = "intermédiaire"
    bac = "bac"
    concours = "concours"


class StyleReponse(str, Enum):
    simple = "simple avec exemples"
    detaille = "très détaillé"
    court = "court et direct"
    concours = "niveau concours"


class FormatReponse(str, Enum):
    structure = "structuré"
    tableau = "tableau"
    fiche = "fiche de révision"
    qr = "questions/réponses"


class StudentProfile(BaseModel):
    model_config = {"validate_assignment": True}

    name: str = ""
    matiere: str = ""
    niveau: Niveau = Niveau.intermediaire
    objectif: str = ""


class Preferences(BaseModel):
    model_config = {"validate_assignment": True}

    style_reponse: StyleReponse = StyleReponse.simple
    format: FormatReponse = FormatReponse.structure


class TaskStatus(str, Enum):
    a_faire = "à faire"
    termine = "terminé"


class PlanningTask(BaseModel):
    model_config = {"validate_assignment": True}

    id: int
    date: date_type = Field(default_factory=date_type.today)
    task: str
    duration_minutes: int
    status: TaskStatus = TaskStatus.a_faire


class QuizResult(BaseModel):
    chapter: str
    score: int = Field(ge=0, le=100)
    feedback: str = ""
    created_at: datetime = Field(default_factory=datetime.now)


class Progression(BaseModel):
    chapitres_revises: List[str] = Field(default_factory=list)
    quiz_results: List[QuizResult] = Field(default_factory=list)

    @property
    def score_moyen(self) -> Optional[float]:
        if not self.quiz_results:
            return None
        return round(sum(r.score for r in self.quiz_results) / len(self.quiz_results), 2)


class Memory(BaseModel):
    """Racine de la mémoire longue, persistée en JSON."""
    student: StudentProfile = Field(default_factory=StudentProfile)
    preferences: Preferences = Field(default_factory=Preferences)
    difficultes: List[str] = Field(default_factory=list)
    planning: List[PlanningTask] = Field(default_factory=list)
    progression: Progression = Field(default_factory=Progression)

    def next_planning_id(self) -> int:
        return max((t.id for t in self.planning), default=0) + 1


class QuizQuestionType(str, Enum):
    qcm = "qcm"
    directe = "question directe"
    ouverte = "question ouverte"


class QuizQuestion(BaseModel):
    id: int
    chapter: str
    matiere: str
    niveau: Niveau
    question: str
    type: QuizQuestionType

    # QCM uniquement : liste des choix proposés à l'étudiant
    options: List[str] = Field(default_factory=list)
    # QCM / question directe : réponse correcte exacte (texte du bon choix,
    # ou réponse courte attendue). Non envoyée à l'UI tant que non corrigé.
    correct_answer: Optional[str] = None
    # Question ouverte : points clés attendus, utilisés par l'IA pour noter.
    expected_points: List[str] = Field(default_factory=list)


class QuestionFeedback(BaseModel):
    question_id: int
    is_correct: Optional[bool] = None  # None pour les questions ouvertes notées sur barème
    points_awarded: float = 0
    points_max: float = 1
    explanation: str = ""


class QuizCorrection(BaseModel):
    feedback: List[QuestionFeedback]
    score: int = Field(ge=0, le=100)
    overall_comment: str = ""


class ChatRole(str, Enum):
    user = "user"
    assistant = "assistant"


class ChatMessage(BaseModel):
    role: ChatRole
    content: str