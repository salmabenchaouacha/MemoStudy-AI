import os
from typing import List, Dict

from dotenv import load_dotenv
from google import genai

from memory_service import read_memory


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY est introuvable. Vérifie ton fichier .env")

client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-3.5-flash"


def build_system_prompt() -> str:
    memory = read_memory()

    return f"""
Tu es MemoStudy AI, un assistant intelligent de révision.

Ton rôle :
- aider l'étudiant à comprendre ses leçons ;
- générer des explications simples ;
- proposer des méthodes de réponse ;
- aider à préparer les concours ;
- utiliser la mémoire longue pour personnaliser tes réponses.

Mémoire longue de l'étudiant :
{memory}

Règles de réponse :
1. Réponds toujours en français.
2. Adapte la réponse à la matière, au niveau et à l'objectif.
3. Si le niveau est concours, donne une réponse structurée.
4. Si l'étudiant a une difficulté avec les questions ouvertes, propose un plan de réponse.
5. Si l'étudiant a une difficulté avec la gestion du temps, propose une méthode rapide.
6. Donne des exemples simples.
7. Termine souvent par une mini-question d'entraînement.
8. Ne dis pas que tu as une mémoire magique : utilise simplement les informations disponibles.
"""


def format_short_memory(short_memory: List[Dict[str, str]]) -> str:
    if not short_memory:
        return "Aucun historique récent."

    recent_messages = short_memory[-8:]

    formatted_messages = []

    for message in recent_messages:
        role = message.get("role", "unknown")
        content = message.get("content", "")

        if role == "user":
            formatted_messages.append(f"Étudiant : {content}")
        elif role == "assistant":
            formatted_messages.append(f"MemoStudy AI : {content}")

    return "\n".join(formatted_messages)


def generate_ai_response(user_question: str, short_memory: List[Dict[str, str]]) -> str:
    system_prompt = build_system_prompt()
    conversation_context = format_short_memory(short_memory)

    full_prompt = f"""
{system_prompt}

Historique récent de la conversation :
{conversation_context}

Nouvelle question de l'étudiant :
{user_question}

Réponds maintenant comme MemoStudy AI.
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt
        )

        return response.text

    except Exception as e:
        return f"""
Une erreur est survenue avec Gemini.

Détail technique :
{str(e)}

Vérifie :
- ta clé GEMINI_API_KEY dans .env ;
- ta connexion internet ;
- le nom du modèle dans MODEL_NAME ;
- l'installation de google-genai.
"""