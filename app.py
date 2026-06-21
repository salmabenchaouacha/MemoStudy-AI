import streamlit as st

from models import ChatMessage, ChatRole
from services.memory_service import (
    read_memory,
    update_student_profile,
    update_preferences,
    add_difficulty,
    remove_difficulty,
    reset_memory,
)
from services.agent_service import generate_ai_response
from services.quiz_service import generate_quiz, save_quiz_result, correct_quiz
from models import QuizQuestionType
from services.planning_service import add_planning_task, mark_task_done, get_planning, remove_planning_task
from services.progress_service import get_progress_summary

st.set_page_config(page_title="MemoStudy AI", page_icon="🧠", layout="wide")
st.title("🧠 MemoStudy AI")
st.caption("Assistant intelligent de révision avec mémoire + Gemini API")

memory = read_memory()

# --- Sidebar : profil & préférences ---
with st.sidebar:
    st.header("Profil étudiant")

    name = st.text_input("Nom", value=memory.student.name)
    matiere = st.text_input("Matière", value=memory.student.matiere)

    niveau_options = ["débutant", "intermédiaire", "bac", "concours"]
    niveau = st.selectbox(
        "Niveau", niveau_options, index=niveau_options.index(memory.student.niveau.value)
    )

    objectif = st.text_input("Objectif", value=memory.student.objectif)

    if st.button("Sauvegarder profil"):
        update_student_profile(name, matiere, niveau, objectif)
        st.success("Profil sauvegardé.")
        st.rerun()

    st.divider()
    st.header("Préférences")

    style_options = ["simple avec exemples", "très détaillé", "court et direct", "niveau concours"]
    style_reponse = st.selectbox(
        "Style de réponse",
        style_options,
        index=style_options.index(memory.preferences.style_reponse.value),
    )

    format_options = ["structuré", "tableau", "fiche de révision", "questions/réponses"]
    format_reponse = st.selectbox(
        "Format préféré",
        format_options,
        index=format_options.index(memory.preferences.format.value),
    )

    if st.button("Sauvegarder préférences"):
        update_preferences(style_reponse, format_reponse)
        st.success("Préférences sauvegardées.")
        st.rerun()


tab_dashboard, tab_chat, tab_quiz, tab_planning, tab_memory = st.tabs(
    ["Dashboard", "Chat Gemini", "Quiz", "Planning", "Mémoire"]
)

# --- Dashboard ---
with tab_dashboard:
    st.subheader("Tableau de bord")
    progress = get_progress_summary()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Matière", memory.student.matiere or "Non définie")
    col2.metric("Niveau", memory.student.niveau.value)
    col3.metric("Score moyen global", progress.score_moyen if progress.score_moyen is not None else "N/A")
    col4.metric("Quiz réalisés", progress.total_quiz)

    st.write("### Score moyen par chapitre")
    if progress.scores_par_chapitre:
        st.dataframe(
            [{"Chapitre": c.chapter, "Score moyen": c.score_moyen, "Nb quiz": c.nb_quiz} for c in progress.scores_par_chapitre],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Aucun quiz réalisé pour le moment.")

    st.write("### Difficultés enregistrées")
    if memory.difficultes:
        for diff in memory.difficultes:
            st.info(diff)
    else:
        st.warning("Aucune difficulté enregistrée.")

    st.write("### Planning")
    col_a, col_b = st.columns(2)
    col_a.metric("Tâches totales", progress.total_tasks)
    col_b.metric("Tâches terminées", progress.done_tasks)


# --- Chat ---
with tab_chat:
    st.subheader("Chat de révision avec Gemini")

    if "messages" not in st.session_state:
        st.session_state.messages: list[ChatMessage] = []

    for message in st.session_state.messages:
        with st.chat_message(message.role.value):
            st.write(message.content)

    user_question = st.chat_input("Pose ta question de révision...")

    if user_question:
        st.session_state.messages.append(ChatMessage(role=ChatRole.user, content=user_question))

        with st.spinner("MemoStudy AI réfléchit avec Gemini..."):
            response = generate_ai_response(
                user_question=user_question,
                short_memory=st.session_state.messages,
            )

        st.session_state.messages.append(ChatMessage(role=ChatRole.assistant, content=response))
        st.rerun()


# --- Quiz ---
with tab_quiz:
    st.subheader("Quiz personnalisé")

    chapter = st.text_input("Chapitre à réviser", placeholder="Exemple : respiration cellulaire")
    number_of_questions = st.slider("Nombre de questions", min_value=3, max_value=10, value=5)

    if st.button("Générer quiz"):
        if chapter.strip():
            with st.spinner("Génération du quiz..."):
                st.session_state.quiz = generate_quiz(chapter, number_of_questions)
                st.session_state.quiz_chapter = chapter
                st.session_state.quiz_answers = {}
                st.session_state.pop("quiz_correction", None)
            st.success("Quiz généré.")
        else:
            st.error("Entre un chapitre.")

    if "quiz" in st.session_state:
        st.write("### Réponds aux questions")

        if "quiz_answers" not in st.session_state:
            st.session_state.quiz_answers = {}

        correction = st.session_state.get("quiz_correction")
        feedback_by_id = {f.question_id: f for f in correction.feedback} if correction else {}

        for q in st.session_state.quiz:
            st.write(f"**{q.id}. {q.question}**")
            fb = feedback_by_id.get(q.id)

            if q.type == QuizQuestionType.qcm:
                answer = st.radio(
                    "Ta réponse",
                    options=q.options,
                    index=None,
                    key=f"quiz_qcm_{q.id}",
                    label_visibility="collapsed",
                )
                st.session_state.quiz_answers[q.id] = answer or ""
            else:
                answer = st.text_area(
                    "Ta réponse",
                    key=f"quiz_open_{q.id}",
                    label_visibility="collapsed",
                    placeholder="Écris ta réponse ici...",
                )
                st.session_state.quiz_answers[q.id] = answer

            if fb is not None:
                if fb.is_correct is True:
                    st.success(f"✅ {fb.explanation}")
                elif fb.is_correct is False:
                    st.error(f"❌ {fb.explanation}")
                else:  # question ouverte notée sur barème
                    pct = fb.points_awarded / fb.points_max if fb.points_max else 0
                    if pct >= 0.75:
                        st.success(f"📝 {fb.points_awarded}/{fb.points_max} — {fb.explanation}")
                    elif pct >= 0.4:
                        st.warning(f"📝 {fb.points_awarded}/{fb.points_max} — {fb.explanation}")
                    else:
                        st.error(f"📝 {fb.points_awarded}/{fb.points_max} — {fb.explanation}")

            st.caption(f"Type : {q.type.value}")
            st.divider()

        if st.button("Corriger le quiz", type="primary"):
            with st.spinner("Correction en cours..."):
                st.session_state.quiz_correction = correct_quiz(
                    st.session_state.quiz, st.session_state.quiz_answers
                )
            st.rerun()

        if correction:
            st.write(f"### Score : {correction.score}/100")

            saved_chapter = st.session_state.get("quiz_chapter", chapter)
            feedback_summary = "; ".join(
                f.explanation for f in correction.feedback if f.is_correct is False
            ) or "Bon travail, peu d'erreurs."

            if st.button("Sauvegarder ce résultat dans la mémoire"):
                save_quiz_result(saved_chapter, correction.score, feedback_summary)
                st.success("Résultat sauvegardé dans la mémoire.")
                st.rerun()


# --- Planning ---
with tab_planning:
    st.subheader("Planning de révision")

    task = st.text_input("Nouvelle tâche", placeholder="Exemple : Réviser la cellule")
    duration = st.number_input("Durée en minutes", min_value=10, max_value=180, value=45)

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
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
            col1.write(f"**{item.task}**")
            col2.write(f"{item.duration_minutes} min")
            col3.write(item.status.value)

            if item.status.value != "terminé":
                if col4.button("Terminer", key=f"done_{item.id}"):
                    mark_task_done(item.id)
                    st.rerun()

            if col5.button("Suppr.", key=f"del_{item.id}"):
                remove_planning_task(item.id)
                st.rerun()
    else:
        st.warning("Aucune tâche pour le moment.")


# --- Mémoire ---
with tab_memory:
    st.subheader("Mémoire longue")

    st.write("### Ajouter une difficulté")
    new_difficulty = st.text_input("Nouvelle difficulté", placeholder="Exemple : manque de vocabulaire scientifique")

    if st.button("Ajouter difficulté"):
        if new_difficulty.strip():
            add_difficulty(new_difficulty.strip())
            st.success("Difficulté ajoutée.")
            st.rerun()

    st.write("### Difficultés actuelles")
    for i, diff in enumerate(memory.difficultes):
        col1, col2 = st.columns([4, 1])
        col1.write(diff)
        if col2.button("Supprimer", key=f"remove_diff_{i}"):
            remove_difficulty(diff)
            st.rerun()

    st.divider()
    st.write("### Mémoire complète")
    st.json(memory.model_dump(mode="json"))

    st.divider()
    if st.button("Réinitialiser mémoire"):
        reset_memory()
        st.warning("Mémoire réinitialisée.")
        st.rerun()