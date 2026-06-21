"""
Client Gemini centralisé.

Tout ce qui parle au SDK google-genai passe par ici. Le reste de l'app
(agent_service, quiz_service) ne connaît jamais les noms de modèles
ni les détails de retry : il appelle `generate(...)` et reçoit du texte
ou une exception métier claire.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY est introuvable. Vérifie ton fichier .env")

# Modèles vérifiés sur la doc Google AI (juin 2026) :
# gemini-3.5-flash et gemini-3.1-flash-lite sont les remplaçants officiels
# des anciens modèles 2.0 arrêtés. À ajuster ici uniquement si Google
# republie de nouveaux noms.
MODEL_CANDIDATES: List[str] = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
]

MAX_RETRIES_PER_MODEL = 2          # avant: 3 -> trop long cumulé
BASE_BACKOFF_SECONDS = 1.5         # 1.5s, 3s -> raisonnable pour une UI synchrone


class GeminiUnavailableError(Exception):
    """Levée quand aucun modèle candidat n'a répondu après tous les essais."""

    def __init__(self, message: str, last_error: Optional[str] = None):
        super().__init__(message)
        self.last_error = last_error


@dataclass
class ChatTurn:
    role: str  # "user" | "model"
    text: str


_client = genai.Client(api_key=GEMINI_API_KEY)


def _to_genai_contents(history: List[ChatTurn]) -> List[types.Content]:
    """Convertit notre historique interne en vrais tours user/model pour l'API,
    au lieu de tout aplatir dans un seul gros prompt texte."""
    return [
        types.Content(role=turn.role, parts=[types.Part(text=turn.text)])
        for turn in history
    ]


def generate(
    system_instruction: str,
    history: List[ChatTurn],
    *,
    temperature: float = 0.7,
) -> str:
    """Appelle Gemini avec fallback entre modèles et retries courts.

    Lève GeminiUnavailableError si tous les modèles/tentatives échouent ;
    c'est à l'appelant (agent_service) de décider du fallback applicatif.
    """
    contents = _to_genai_contents(history)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=temperature,
    )

    last_error: Optional[str] = None

    for model_name in MODEL_CANDIDATES:
        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                response = _client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                )
                if response and response.text:
                    return response.text
                last_error = f"{model_name}: réponse vide"
            except Exception as exc:  # le SDK peut lever divers types d'erreurs réseau/API
                last_error = f"{model_name}: {exc}"
                logger.warning("Échec Gemini (%s, tentative %d): %s", model_name, attempt + 1, exc)

                is_last_attempt_for_model = attempt == MAX_RETRIES_PER_MODEL - 1
                if not is_last_attempt_for_model:
                    time.sleep(BASE_BACKOFF_SECONDS * (attempt + 1))

    raise GeminiUnavailableError(
        "Tous les modèles Gemini candidats ont échoué.",
        last_error=last_error,
    )