"""
Logique de l'agent de révision : construit le prompt système à partir de la
mémoire, convertit l'historique court en tours de chat, et gère le fallback
local si Gemini est indisponible.
"""

from __future__ import annotations

from typing import List

from models import ChatMessage, ChatRole, Memory
from services.gemini_client import ChatTurn, GeminiUnavailableError, generate
from services.memory_service import read_memory

MAX_HISTORY_TURNS = 8


def build_system_prompt(memory: Memory) -> str:
    return f"""Tu es MemoStudy AI, un assistant intelligent de révision avec mémoire.

Tu dois :
- adapter les explications au profil de l'étudiant ;
- tenir compte de ses difficultés ;
- proposer des quiz ;
- donner des réponses structurées ;
- aider à préparer un concours ;
- proposer des méthodes de gestion du temps.

Tu dois répondre en français simple, clair et utile.

Profil de l'étudiant (mémoire longue) :
- Nom : {memory.student.name or "non renseigné"}
- Matière : {memory.student.matiere or "non renseignée"}
- Niveau : {memory.student.niveau.value}
- Objectif : {memory.student.objectif or "non renseigné"}
- Style de réponse préféré : {memory.preferences.style_reponse.value}
- Format préféré : {memory.preferences.format.value}
- Difficultés connues : {", ".join(memory.difficultes) or "aucune connue"}

Règles de réponse :
1. Réponds toujours en français simple, clair et utile.
2. Adapte la réponse à la matière, au niveau et à l'objectif de l'étudiant.
3. Si le niveau est concours, donne une réponse structurée.
4. Si l'étudiant a une difficulté avec les questions ouvertes, propose un plan de réponse.
5. Si l'étudiant a une difficulté avec la gestion du temps, propose une méthode rapide.
6. Propose un quiz ou un exercice quand c'est pertinent.
7. Donne des exemples simples.
8. Termine par une mini-question d'entraînement.
"""


def _to_chat_turns(short_memory: List[ChatMessage]) -> List[ChatTurn]:
    recent = short_memory[-MAX_HISTORY_TURNS:]
    return [
        ChatTurn(role="user" if m.role == ChatRole.user else "model", text=m.content)
        for m in recent
    ]


def local_fallback_response(user_question: str, memory: Memory, error_detail: str) -> str:
    """Réponse locale si Gemini est temporairement indisponible, pour que
    l'application ne reste pas bloquée. Le contenu de l'exercice reste
    générique car on ne peut pas appeler de LLM ici par définition,
    mais on garde la question de l'étudiant visible pour la transparence."""
    matiere = memory.student.matiere or "ta matière"
    niveau = memory.student.niveau.value

    return f"""⚠️ Gemini est temporairement indisponible, voici une réponse de secours locale.

**Détail technique (pour debug) :** {error_detail}

### Ta question
> {user_question}

### En attendant, voici une méthode générale ({matiere}, niveau {niveau})

1. Reformule la question avec tes propres mots.
2. Identifie 2 à 3 notions clés liées à la question.
3. Construis ta réponse en partant d'une définition, puis un mécanisme/exemple, puis une conclusion.
4. Vérifie que tu as bien répondu à ce qui était demandé.

### Mini-question d'entraînement
Quelle est la définition la plus simple que tu peux donner du sujet de ta question, en une phrase ?

*Réessaie dans quelques instants pour une réponse personnalisée par l'IA.*
"""


def generate_ai_response(user_question: str, short_memory: List[ChatMessage]) -> str:
    memory = read_memory()
    system_prompt = build_system_prompt(memory)

    history = _to_chat_turns(short_memory)
    history.append(ChatTurn(role="user", text=user_question))

    try:
        return generate(system_instruction=system_prompt, history=history)
    except GeminiUnavailableError as exc:
        return local_fallback_response(
            user_question=user_question,
            memory=memory,
            error_detail=exc.last_error or "erreur inconnue",
        )