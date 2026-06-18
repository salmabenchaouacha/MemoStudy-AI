import os
import time
from typing import List, Dict

from dotenv import load_dotenv
from google import genai

from memory_service import read_memory


load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY est introuvable. Vérifie ton fichier .env")

client = genai.Client(api_key=GEMINI_API_KEY)


# On met plusieurs modèles.
# Si le premier est saturé, l'app essaie le suivant.
MODEL_CANDIDATES = [
    "gemini-3.5-flash",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest"
]


def build_system_prompt() -> str:
    memory = read_memory()

    return f"""
Tu es MemoStudy AI, un assistant intelligent de révision.

Ton rôle :
- aider l'étudiant à comprendre ses leçons ;
- générer des exercices simples ;
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
7. Termine par une mini-question d'entraînement.
"""


def format_short_memory(short_memory: List[Dict[str, str]]) -> str:
    if not short_memory:
        return "Aucun historique récent."

    recent_messages = short_memory[-8:]
    formatted_messages = []

    for message in recent_messages:
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "user":
            formatted_messages.append(f"Étudiant : {content}")
        elif role == "assistant":
            formatted_messages.append(f"MemoStudy AI : {content}")

    return "\n".join(formatted_messages)


def local_fallback_response(user_question: str) -> str:
    """
    Réponse locale si Gemini est temporairement indisponible.
    Comme ça, l'application ne reste pas bloquée.
    """
    memory = read_memory()
    student = memory.get("student", {})
    matiere = student.get("matiere", "science")
    niveau = student.get("niveau", "concours")

    return f"""
Gemini est temporairement indisponible, donc je te donne une réponse locale simple.

### Exercice personnalisé

Matière : **{matiere}**  
Niveau : **{niveau}**

Ta demande :

> {user_question}

### Exercice simple

Explique avec tes mots la notion suivante :

**Pourquoi les plantes ont-elles besoin de lumière pour vivre ?**

### Aide pour répondre

Utilise cette structure :

1. Je donne une définition simple.
2. J’explique le rôle de la lumière.
3. Je donne un exemple.
4. Je termine par une phrase de conclusion.

### Réponse attendue courte

Les plantes ont besoin de lumière pour fabriquer leur nourriture grâce à la photosynthèse. Elles utilisent la lumière, l’eau et le dioxyde de carbone pour produire de la matière organique et libérer du dioxygène.

### Mini-question

Pourquoi la photosynthèse est-elle importante pour les êtres vivants ?
"""


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

    last_error = None

    for model_name in MODEL_CANDIDATES:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=full_prompt
                )

                if response and response.text:
                    return response.text

            except Exception as e:
                last_error = str(e)

                # Retry progressif : 2s, 4s, 8s
                wait_time = 2 ** (attempt + 1)
                time.sleep(wait_time)

    return f"""
Gemini est temporairement indisponible après plusieurs essais.

Détail technique :
{last_error}

Je continue avec une réponse locale pour ne pas bloquer l'application.

---

{local_fallback_response(user_question)}
"""