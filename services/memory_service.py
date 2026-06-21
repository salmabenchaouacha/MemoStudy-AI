"""
Couche de persistance de la mémoire longue.

Responsabilités, et seulement ça :
- charger/sauvegarder le fichier JSON
- garantir que ce qui est lu/écrit respecte le schéma `models.Memory`
- éviter les écritures concurrentes corrompues (verrou de fichier + écriture atomique)

Aucune logique métier ici (pas de "ajouter une difficulté typique", etc.) :
ça vit dans les services au-dessus (planning_service, quiz_service...).
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock

from models import Memory

MEMORY_PATH = Path(os.getenv("MEMORY_PATH", "memory.json"))
LOCK_PATH = MEMORY_PATH.with_suffix(".lock")


def _write_atomic(path: Path, content: str) -> None:
    """Écrit dans un fichier temporaire puis renomme (atomique sur la plupart des OS),
    pour éviter un fichier à moitié écrit en cas de crash pendant l'écriture."""
    tmp_dir = path.parent if str(path.parent) else Path(".")
    fd, tmp_path = tempfile.mkstemp(dir=tmp_dir, prefix=".tmp_memory_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def read_memory() -> Memory:
    """Lit et valide la mémoire. Si le fichier n'existe pas encore, renvoie une mémoire vide
    (et ne l'écrit pas tout de suite — on laisse l'appelant décider quand sauvegarder)."""
    if not MEMORY_PATH.exists():
        return Memory()

    with FileLock(str(LOCK_PATH)):
        raw = MEMORY_PATH.read_text(encoding="utf-8")

    if not raw.strip():
        return Memory()

    data = json.loads(raw)
    return Memory.model_validate(data)


def save_memory(memory: Memory) -> None:
    """Sauvegarde la mémoire de façon atomique et verrouillée."""
    payload = memory.model_dump_json(indent=2)
    with FileLock(str(LOCK_PATH)):
        _write_atomic(MEMORY_PATH, payload)


@contextmanager
def memory_transaction() -> Iterator[Memory]:
    """Context manager pratique pour lire -> modifier -> sauvegarder en une seule
    section critique, évitant les races read-modify-write entre deux requêtes.

    Usage:
        with memory_transaction() as memory:
            memory.difficultes.append("nouvelle difficulté")
        # sauvegardé automatiquement à la sortie du bloc
    """
    with FileLock(str(LOCK_PATH)):
        raw = MEMORY_PATH.read_text(encoding="utf-8") if MEMORY_PATH.exists() else ""
        memory = Memory.model_validate(json.loads(raw)) if raw.strip() else Memory()
        yield memory
        _write_atomic(MEMORY_PATH, memory.model_dump_json(indent=2))


def reset_memory() -> Memory:
    fresh = Memory()
    save_memory(fresh)
    return fresh


# --- Opérations de haut niveau sur le profil / préférences ---
# (Restent ici car elles touchent directement et uniquement la structure Memory,
#  contrairement au planning/quiz qui ont leur propre fichier de service.)

def update_student_profile(name: str, matiere: str, niveau: str, objectif: str) -> Memory:
    with memory_transaction() as memory:
        memory.student.name = name
        memory.student.matiere = matiere
        memory.student.niveau = niveau  # validé par Pydantic (Enum) à la sauvegarde
        memory.student.objectif = objectif
    return memory


def update_preferences(style_reponse: str, format_reponse: str) -> Memory:
    with memory_transaction() as memory:
        memory.preferences.style_reponse = style_reponse
        memory.preferences.format = format_reponse
    return memory


def add_difficulty(difficulty: str) -> Memory:
    with memory_transaction() as memory:
        if difficulty not in memory.difficultes:
            memory.difficultes.append(difficulty)
    return memory


def remove_difficulty(difficulty: str) -> Memory:
    with memory_transaction() as memory:
        memory.difficultes = [d for d in memory.difficultes if d != difficulty]
    return memory