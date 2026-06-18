import json
from pathlib import Path
from typing import Any, Dict


MEMORY_FILE = Path("memory.json")


DEFAULT_MEMORY = {
    "student": {
        "name": "",
        "matiere": "",
        "niveau": "intermédiaire",
        "objectif": ""
    },
    "preferences": {
        "style_reponse": "simple avec exemples",
        "format": "structuré"
    },
    "difficultes": [],
    "planning": [],
    "progression": {
        "chapitres_revises": [],
        "score_moyen": None,
        "quiz_results": []
    }
}


def read_memory() -> Dict[str, Any]:
    if not MEMORY_FILE.exists():
        save_memory(DEFAULT_MEMORY)
        return DEFAULT_MEMORY

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        save_memory(DEFAULT_MEMORY)
        return DEFAULT_MEMORY


def save_memory(memory: Dict[str, Any]) -> None:
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)


def update_student_profile(
    name: str,
    matiere: str,
    niveau: str,
    objectif: str
) -> Dict[str, Any]:
    memory = read_memory()

    memory["student"] = {
        "name": name,
        "matiere": matiere,
        "niveau": niveau,
        "objectif": objectif
    }

    save_memory(memory)
    return memory


def update_preferences(style_reponse: str, format_reponse: str) -> Dict[str, Any]:
    memory = read_memory()

    memory["preferences"] = {
        "style_reponse": style_reponse,
        "format": format_reponse
    }

    save_memory(memory)
    return memory


def add_difficulty(difficulty: str) -> Dict[str, Any]:
    memory = read_memory()

    memory.setdefault("difficultes", [])

    if difficulty and difficulty not in memory["difficultes"]:
        memory["difficultes"].append(difficulty)

    save_memory(memory)
    return memory


def remove_difficulty(difficulty: str) -> Dict[str, Any]:
    memory = read_memory()

    if difficulty in memory.get("difficultes", []):
        memory["difficultes"].remove(difficulty)

    save_memory(memory)
    return memory


def reset_memory() -> Dict[str, Any]:
    save_memory(DEFAULT_MEMORY)
    return DEFAULT_MEMORY