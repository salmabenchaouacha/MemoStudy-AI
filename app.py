import streamlit as st

from memory_service import (
    read_memory,
    update_student_profile,
    update_preferences,
    add_difficulty,
    remove_difficulty,
    reset_memory
)

from agent_service import generate_ai_response
from quiz_service import generate_quiz, save_quiz_result
from planning_service import add_planning_task, mark_task_done, get_planning
from progress_service import get_progress_summary


st.set_page_config(
    page_title="MemoStudy AI",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 MemoStudy AI")
st.caption("Assistant intelligent de révision avec mémoire + Gemini API")

memory = read_memory()


with st.sidebar:
    st.header("Profil étudiant")

    student = memory.get("student", {})
    preferences = memory.get("preferences", {})

    name = st.text_input("Nom", value=student.get("name", ""))
    matiere = st.text_input("Matière", value=student.get("matiere", ""))

    niveau_options = ["débutant", "intermédiaire", "bac", "concours"]
    current_niveau = student.get("niveau", "intermédiaire")

    if current_niveau in niveau_options:
        niveau_index = niveau_options.index(current_niveau)
    else:
        niveau_index = 1

    niveau = st.selectbox(
        "Niveau",
        niveau_options,
        index=niveau_index
    )

    objectif = st.text_input("Objectif", value=student.get("objectif", ""))

    if st.button("Sauvegarder profil"):
        update_student_profile(name, matiere, niveau, objectif)
        st.success("Profil sauvegardé.")
        st.rerun()

    st.divider()

    st.header("Préférences")

    style_options = [
        "simple avec exemples",
        "très détaillé",
        "court et direct",
        "niveau concours"
    ]

    current_style = preferences.get("style_reponse", "simple avec exemples")

    if current_style in style_options:
        style_index = style_options.index(current_style)
    else:
        style_index = 0

    style_reponse = st.selectbox(
        "Style de réponse",
        style_options,
        index=style_index
    )

    format_options = [
        "structuré",
        "tableau",
        "fiche de révision",
        "questions/réponses"
    ]

    current_format = preferences.get("format", "structuré")

    if current_format in format_options:
        format_index = format_options.index(current_format)
    else:
        format_index = 0

    format_reponse = st.selectbox(
        "Format préféré",
        format_options,
        index=format_index
    )

    if st.button("Sauvegarder préférences"):
        update_preferences(style_reponse, format_reponse)
        st.success("Préférences sauvegardées.")
        st.rerun()


tab_dashboard, tab_chat, tab_quiz, tab_planning, tab_memory = st.tabs([
    "Dashboard",
    "Chat Gemini",
    "Quiz",
    "Planning",
    "Mémoire"
])


with tab_dashboard:
    st.subheader("Tableau de bord")

    progress = get_progress_summary()
    memory = read_memory()
    student = memory.get("student", {})
    difficultes = memory.get("difficultes", [])

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Matière", student.get("matiere", "Non définie"))
    col2.metric("Niveau", student.get("niveau", "Non défini"))
    col3.metric("Score moyen", progress.get("score_moyen") or "N/A")
    col4.metric("Quiz réalisés", progress.get("total_quiz"))

    st.write("### Difficultés enregistrées")

    if difficultes:
        for diff in difficultes:
            st.info(diff)
    else:
        st.warning("Aucune difficulté enregistrée.")

    st.write("### Chapitres révisés")

    chapitres = progress.get("chapitres_revises", [])

    if chapitres:
        for chapitre in chapitres:
            st.success(chapitre)
    else:
        st.warning("Aucun chapitre révisé pour le moment.")

    st.write("### Planning")

    col_a, col_b = st.columns(2)

    col_a.metric("Tâches totales", progress.get("total_tasks"))
    col_b.metric("Tâches terminées", progress.get("done_tasks"))


with tab_chat:
    st.subheader("Chat de révision avec Gemini")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    user_question = st.chat_input("Pose ta question de révision...")

    if user_question:
        st.session_state.messages.append({
            "role": "user",
            "content": user_question
        })

        with st.spinner("MemoStudy AI réfléchit avec Gemini..."):
            response = generate_ai_response(
                user_question=user_question,
                short_memory=st.session_state.messages
            )

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()


with tab_quiz:
    st.subheader("Quiz personnalisé")

    chapter = st.text_input(
        "Chapitre à réviser",
        placeholder="Exemple : respiration cellulaire"
    )

    number_of_questions = st.slider(
        "Nombre de questions",
        min_value=3,
        max_value=10,
        value=5
    )

    if st.button("Générer quiz"):
        if chapter.strip():
            quiz = generate_quiz(chapter, number_of_questions)
            st.session_state.quiz = quiz
            st.session_state.quiz_chapter = chapter
            st.success("Quiz généré.")
        else:
            st.error("Entre un chapitre.")

    if "quiz" in st.session_state:
        st.write("### Questions")

        for question in st.session_state.quiz:
            st.write(f"**{question['id']}. {question['question']}**")
            st.caption(f"Type : {question['type']}")

        st.divider()

        st.write("### Enregistrer le résultat")

        score = st.slider("Score obtenu", 0, 100, 70)

        feedback = st.text_area(
            "Feedback",
            placeholder="Exemple : difficultés dans les questions ouvertes"
        )

        if st.button("Sauvegarder résultat"):
            saved_chapter = st.session_state.get("quiz_chapter", chapter)
            save_quiz_result(saved_chapter, score, feedback)
            st.success("Résultat sauvegardé dans la mémoire.")
            st.rerun()


with tab_planning:
    st.subheader("Planning de révision")

    task = st.text_input(
        "Nouvelle tâche",
        placeholder="Exemple : Réviser la cellule"
    )

    duration = st.number_input(
        "Durée en minutes",
        min_value=10,
        max_value=180,
        value=45
    )

    if st.button("Ajouter tâche"):
        if task.strip():
            add_planning_task(task, duration)
            st.success("Tâche ajoutée.")
            st.rerun()
        else:
            st.error("Entre une tâche.")

    st.write("### Mes tâches")

    planning = get_planning()

    if planning:
        for item in planning:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            col1.write(f"**{item['task']}**")
            col2.write(f"{item['duration_minutes']} min")
            col3.write(item["status"])

            if item["status"] != "terminé":
                if col4.button("Terminer", key=f"done_{item['id']}"):
                    mark_task_done(item["id"])
                    st.rerun()
    else:
        st.warning("Aucune tâche pour le moment.")


with tab_memory:
    st.subheader("Mémoire longue")

    memory = read_memory()

    st.write("### Ajouter une difficulté")

    new_difficulty = st.text_input(
        "Nouvelle difficulté",
        placeholder="Exemple : manque de vocabulaire scientifique"
    )

    if st.button("Ajouter difficulté"):
        if new_difficulty.strip():
            add_difficulty(new_difficulty.strip())
            st.success("Difficulté ajoutée.")
            st.rerun()

    st.write("### Difficultés actuelles")

    for diff in memory.get("difficultes", []):
        col1, col2 = st.columns([4, 1])
        col1.write(diff)

        if col2.button("Supprimer", key=f"remove_{diff}"):
            remove_difficulty(diff)
            st.rerun()

    st.divider()

    st.write("### Mémoire complète")
    st.json(memory)

    st.divider()

    if st.button("Réinitialiser mémoire"):
        reset_memory()
        st.warning("Mémoire réinitialisée.")
        st.rerun()