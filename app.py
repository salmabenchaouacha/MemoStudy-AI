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

# =====================================================================================
# DESIGN SYSTEM — "Synapse" (LED / circuit néon sur fond clair)
# Palette : indigo quasi-noir + trio néon violet · cyan · magenta sur fond lavande très clair.
# Typo    : Space Grotesk (display, géométrique/tech) + Inter (UI) + JetBrains Mono (chiffres)
# Signature : rail dégradé animé (violet→cyan→magenta) + glow pulsé, comme une trace de circuit.
# =====================================================================================
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');

:root {
  --navy: #12132B;
  --navy-light: #212145;
  --parchment: #F4F6FD;
  --parchment-alt: #E9EDFA;
  --gold: #7C5CFF;
  --gold-light: #62E8FF;
  --sage: #21E6A8;
  --coral: #FF3EA5;
  --ink: #14152A;
  --ink-light: #5E6480;
  --rule: #DCE1F5;
  --led-1: #7C5CFF;
  --led-2: #62E8FF;
  --led-3: #FF3EA5;
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
  background:
    radial-gradient(60rem 30rem at 8% -10%, rgba(124,92,255,0.10), transparent 60%),
    radial-gradient(50rem 26rem at 100% 0%, rgba(98,232,255,0.10), transparent 55%),
    radial-gradient(50rem 30rem at 50% 110%, rgba(255,62,165,0.07), transparent 60%),
    var(--parchment);
  color: var(--ink);
}

h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; color: var(--navy) !important; letter-spacing: -0.01em; }

/* ---------- HERO ---------- */
.hero-wrap {
  padding: 1.7rem 1.8rem 1.3rem 1.8rem;
  margin: -1rem -1rem 1rem -1rem;
  position: relative;
  overflow: hidden;
  animation: fadeSlideIn .6s ease;
}
.hero-wrap::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 3px;
  background: linear-gradient(90deg, var(--led-1), var(--led-2) 45%, var(--led-3) 90%);
  background-size: 200% 100%;
  box-shadow: 0 0 16px rgba(124,92,255,0.55), 0 0 26px rgba(98,232,255,0.35);
  animation: ledFlow 5s linear infinite;
}
.hero-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.6rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(100deg, var(--navy) 0%, var(--gold) 55%, var(--gold-light) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}
.hero-sub { color: var(--ink-light); font-size: .98rem; margin-top: .35rem; }
.hero-tag {
  position: absolute; top: 1.8rem; right: 1.8rem;
  display: inline-flex; align-items: center; gap: .4rem;
  font-family: 'JetBrains Mono', monospace;
  font-size: .7rem; color: var(--navy);
  border: 1px solid rgba(124,92,255,0.35);
  padding: .3rem .7rem .3rem .55rem; border-radius: 999px;
  background: rgba(124,92,255,0.07);
  letter-spacing: .04em;
  box-shadow: 0 0 0 rgba(124,92,255,0);
}
.hero-tag::before {
  content: ""; width: .45rem; height: .45rem; border-radius: 50%;
  background: var(--sage);
  box-shadow: 0 0 6px var(--sage), 0 0 12px var(--sage);
  animation: ledPulse 1.6s ease-in-out infinite;
}
@keyframes fadeSlideIn { from { opacity: 0; transform: translateY(-8px);} to { opacity: 1; transform: translateY(0);} }
@keyframes ledFlow { 0% { background-position: 0% 0; } 100% { background-position: 200% 0; } }
@keyframes ledPulse { 0%,100% { opacity: .55; transform: scale(.85); } 50% { opacity: 1; transform: scale(1); } }

/* ---------- SIDEBAR ---------- */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, var(--navy) 0%, var(--navy-light) 100%);
  border-right: 1px solid rgba(124,92,255,0.25);
}
[data-testid="stSidebar"] * { color: var(--parchment) !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  font-family: 'Space Grotesk', sans-serif !important; color: var(--gold-light) !important;
  border-bottom: 1px solid rgba(98,232,255,0.2); padding-bottom: .4rem;
  text-shadow: 0 0 12px rgba(98,232,255,0.35);
}
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
  background: rgba(255,255,255,0.06) !important;
  border: 1px solid rgba(124,92,255,0.3) !important;
  border-radius: 8px !important;
  transition: box-shadow .2s ease, border-color .2s ease;
}
[data-testid="stSidebar"] input:focus, [data-testid="stSidebar"] textarea:focus {
  border-color: var(--gold-light) !important;
  box-shadow: 0 0 0 2px rgba(98,232,255,0.25), 0 0 14px rgba(98,232,255,0.35) !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(124,92,255,0.2) !important; }
[data-testid="stSidebar"] .stButton>button { width: 100%; }

/* ---------- BUTTONS ---------- */
.stButton>button {
  background: linear-gradient(135deg, var(--led-1) 0%, var(--led-2) 100%);
  color: #fff !important; border: none; border-radius: 10px;
  padding: .5rem 1.1rem; font-weight: 600; letter-spacing: .01em;
  transition: all .18s ease;
  box-shadow: 0 2px 10px rgba(124,92,255,0.35), 0 0 0 rgba(98,232,255,0);
}
.stButton>button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(124,92,255,0.45), 0 0 22px rgba(98,232,255,0.45);
  filter: brightness(1.05);
}
.stButton>button:active { transform: translateY(0); }
button[kind="primary"] {
  background: linear-gradient(135deg, var(--led-3) 0%, var(--led-1) 100%) !important;
  box-shadow: 0 2px 10px rgba(255,62,165,0.4), 0 0 22px rgba(124,92,255,0.3) !important;
}

/* ---------- FORM INPUTS (zone de saisie) — zéro noir, focus néon ---------- */
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stNumberInput"] input,
div[data-testid="stChatInput"] textarea,
div[data-baseweb="select"] > div,
div[data-baseweb="base-input"],
div[data-baseweb="input"] {
  background: #ffffff !important;
  border: 1.5px solid var(--rule) !important;
  border-radius: 12px !important;
  color: var(--ink) !important;
  box-shadow: 0 1px 3px rgba(18,19,43,0.04) !important;
  transition: border-color .2s ease, box-shadow .2s ease !important;
}
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stTextArea"] textarea::placeholder,
div[data-testid="stChatInput"] textarea::placeholder {
  color: var(--ink-light) !important;
  opacity: .75;
}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stChatInput"] textarea:focus,
div[data-baseweb="select"]:focus-within > div,
div[data-baseweb="base-input"]:focus-within {
  border-color: var(--gold) !important;
  box-shadow: 0 0 0 3px rgba(124,92,255,0.15), 0 0 18px rgba(124,92,255,0.28) !important;
  outline: none !important;
}
/* icônes / flèches (selectbox, stepper) : plus de noir */
div[data-baseweb="select"] svg,
[data-testid="stNumberInput"] svg,
[data-testid="stTextInput"] svg,
[data-testid="baseButton-headerNoPadding"] svg {
  fill: var(--ink-light) !important;
}
/* menu déroulant du selectbox */
ul[data-testid="stSelectboxVirtualDropdown"], div[data-baseweb="popover"] ul {
  background: #ffffff !important;
  border: 1px solid var(--rule) !important;
  border-radius: 12px !important;
  box-shadow: 0 12px 28px rgba(18,19,43,0.14) !important;
  overflow: hidden;
}
ul[data-testid="stSelectboxVirtualDropdown"] li, div[data-baseweb="popover"] li {
  color: var(--ink) !important;
}
ul[data-testid="stSelectboxVirtualDropdown"] li:hover, div[data-baseweb="popover"] li:hover {
  background: rgba(124,92,255,0.08) !important;
}
[data-baseweb="menu"] li[aria-selected="true"] {
  background: rgba(124,92,255,0.12) !important;
  color: var(--gold) !important;
}
/* boîte englobante du chat input */
[data-testid="stChatInput"] {
  border-radius: 14px !important;
}
[data-testid="stChatInput"] > div {
  border: none !important;
  background: transparent !important;
}
/* stepper +/- du number_input */
[data-testid="stNumberInputStepUp"], [data-testid="stNumberInputStepDown"] {
  background: #fff !important; border: 1.5px solid var(--rule) !important; color: var(--ink-light) !important;
}
[data-testid="stNumberInputStepUp"]:hover, [data-testid="stNumberInputStepDown"]:hover {
  border-color: var(--gold) !important; color: var(--gold) !important;
}
/* slider — piste + poignée en dégradé néon plutôt que rouge par défaut */
div[data-testid="stSlider"] [role="slider"] {
  background: var(--gold) !important;
  box-shadow: 0 0 0 6px rgba(124,92,255,0.16), 0 0 14px rgba(124,92,255,0.45) !important;
  border: 2px solid #fff !important;
}
div[data-testid="stSlider"] > div > div > div > div {
  background: linear-gradient(90deg, var(--led-1), var(--led-2)) !important;
}
div[data-testid="stSlider"] > div > div > div {
  background: var(--rule) !important;
}
/* zone de saisie côté sidebar : mêmes règles de focus, texte clair conservé */
[data-testid="stSidebar"] div[data-baseweb="select"] > div,
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
  box-shadow: none !important;
}
[data-testid="stSidebar"] input:focus,
[data-testid="stSidebar"] textarea:focus,
[data-testid="stSidebar"] div[data-baseweb="select"]:focus-within > div {
  border-color: var(--gold-light) !important;
  box-shadow: 0 0 0 2px rgba(98,232,255,0.22), 0 0 16px rgba(98,232,255,0.35) !important;
}
[data-testid="stSidebar"] div[data-baseweb="select"] svg { fill: var(--parchment) !important; }

/* ---------- TABS ---------- */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 2px solid var(--rule); }
.stTabs [data-baseweb="tab"] {
  background: var(--parchment-alt);
  border-radius: 999px;
  border: 1px solid var(--rule); border-bottom: 1px solid var(--rule);
  padding: .5rem 1.3rem;
  font-family: 'Space Grotesk', sans-serif; color: var(--ink-light); font-weight: 500;
  transition: all .18s ease;
}
.stTabs [data-baseweb="tab"]:hover { background: #fff; border-color: rgba(124,92,255,0.35); }
.stTabs [aria-selected="true"] {
  background: linear-gradient(120deg, var(--navy) 0%, var(--navy-light) 100%) !important;
  color: var(--gold-light) !important; border-color: var(--gold) !important;
  box-shadow: 0 0 14px rgba(124,92,255,0.45);
}

/* ---------- SECTION LABELS ---------- */
.section-label {
  font-family: 'Space Grotesk', sans-serif; color: var(--navy); font-size: 1.12rem; font-weight: 600;
  margin: 1.3rem 0 .6rem 0; padding-left: .7rem;
  border-left: 4px solid transparent;
  border-image: linear-gradient(180deg, var(--led-1), var(--led-2)) 1;
}

/* ---------- DASHBOARD CARDS ---------- */
.dash-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: .8rem 0 1.4rem 0; }
.dash-grid.small { grid-template-columns: repeat(2, 1fr); max-width: 560px; }
.dash-card {
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(6px);
  border: 1px solid var(--rule); border-radius: 16px;
  padding: 1rem 1.15rem; box-shadow: 0 1px 3px rgba(18,19,43,0.05);
  position: relative;
  transition: box-shadow .22s ease, transform .22s ease, border-color .22s ease;
}
.dash-card:hover {
  box-shadow: 0 12px 26px rgba(124,92,255,0.18), 0 0 0 1px rgba(124,92,255,0.25);
  transform: translateY(-3px);
  border-color: rgba(124,92,255,0.35);
}
.dash-card .label { font-size: .72rem; text-transform: uppercase; letter-spacing: .07em; color: var(--ink-light); font-weight: 600; }
.dash-card .value { font-family: 'JetBrains Mono', monospace; font-size: 1.75rem; color: var(--navy); font-weight: 600; margin-top: .15rem; }
.dash-card .value.accent {
  color: var(--gold);
  text-shadow: 0 0 18px rgba(124,92,255,0.35);
}

/* ---------- PILLS ---------- */
.diff-pill {
  display: inline-block; background: rgba(255,62,165,0.09); color: var(--coral);
  border: 1px solid rgba(255,62,165,0.35); border-radius: 999px;
  padding: .3rem .85rem; margin: .2rem .35rem .2rem 0; font-size: .85rem; font-weight: 500;
  box-shadow: 0 0 10px rgba(255,62,165,0.12);
}
.status-badge {
  display: inline-block; border-radius: 999px; padding: .15rem .65rem; font-size: .78rem; font-weight: 600;
}
.status-badge.todo {
  background: rgba(124,92,255,0.12); color: var(--gold); border: 1px solid rgba(124,92,255,0.4);
  box-shadow: 0 0 10px rgba(124,92,255,0.18);
}
.status-badge.done {
  background: rgba(33,230,168,0.14); color: #0E9E76; border: 1px solid rgba(33,230,168,0.45);
  box-shadow: 0 0 10px rgba(33,230,168,0.22);
}

/* ---------- QUIZ / BORDERED CONTAINERS — glass card with neon edge ---------- */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,255,255,0.82);
  backdrop-filter: blur(6px);
  border-radius: 14px !important; border: 1px solid var(--rule) !important;
  padding: .4rem .3rem; position: relative; box-shadow: 0 2px 10px rgba(18,19,43,0.05);
  margin-bottom: .9rem;
  overflow: hidden;
  transition: border-color .2s ease, box-shadow .2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: linear-gradient(180deg, var(--led-1), var(--led-2), var(--led-3));
  box-shadow: 0 0 10px rgba(124,92,255,0.5);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: rgba(124,92,255,0.4) !important;
  box-shadow: 0 8px 22px rgba(124,92,255,0.14);
}

.q-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 1.75rem; height: 1.75rem; border-radius: 50%;
  background: linear-gradient(135deg, var(--led-1), var(--led-2));
  color: #fff; font-family: 'JetBrains Mono', monospace;
  font-size: .8rem; font-weight: 600; margin-right: .5rem;
  box-shadow: 0 0 10px rgba(124,92,255,0.45);
}
.q-type-tag {
  font-family: 'JetBrains Mono', monospace; font-size: .68rem; color: var(--ink-light);
  text-transform: uppercase; letter-spacing: .05em;
}

/* ---------- CHAT ---------- */
[data-testid="stChatMessage"] {
  border-radius: 14px; padding: .4rem .3rem; margin-bottom: .3rem;
  background: rgba(255,255,255,0.6); border: 1px solid var(--rule);
}

/* ---------- DATAFRAME ---------- */
[data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; border: 1px solid var(--rule); }

/* ---------- MISC ---------- */
hr { border-top: 1px solid var(--rule) !important; }
[data-testid="stMetric"] { background: rgba(255,255,255,0.85); border: 1px solid var(--rule); border-radius: 14px; padding: .8rem 1rem; }
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track { background: var(--parchment-alt); }
::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, var(--led-1), var(--led-2));
  border-radius: 10px;
}
*:focus-visible { outline: 2px solid var(--gold-light) !important; outline-offset: 2px; }

@media (prefers-reduced-motion: reduce) {
  .hero-wrap::after, .hero-tag::before { animation: none !important; }
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero-wrap">
      <span class="hero-tag">GEMINI · MÉMOIRE ACTIVE</span>
      <div class="hero-title">🧠 MemoStudy AI</div>
      <div class="hero-sub">Ton assistant de révision personnel — il retient tes difficultés, ton style et ta progression.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

memory = read_memory()

# --- Sidebar : profil & préférences ---
with st.sidebar:
    st.header("📖 Profil étudiant")

    name = st.text_input("Nom", value=memory.student.name)
    matiere = st.text_input("Matière", value=memory.student.matiere)

    niveau_options = ["débutant", "intermédiaire", "bac", "concours"]
    niveau = st.selectbox(
        "Niveau", niveau_options, index=niveau_options.index(memory.student.niveau.value)
    )

    objectif = st.text_input("Objectif", value=memory.student.objectif)

    if st.button("💾 Sauvegarder profil"):
        update_student_profile(name, matiere, niveau, objectif)
        st.success("Profil sauvegardé.")
        st.rerun()

    st.divider()
    st.header("⚙️ Préférences")

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

    if st.button("💾 Sauvegarder préférences"):
        update_preferences(style_reponse, format_reponse)
        st.success("Préférences sauvegardées.")
        st.rerun()


tab_dashboard, tab_chat, tab_quiz, tab_planning, tab_memory = st.tabs(
    ["📊 Dashboard", "💬 Chat Gemini", "📝 Quiz", "🗓️ Planning", "🧠 Mémoire"]
)

# --- Dashboard ---
with tab_dashboard:
    st.markdown('<div class="section-label">Vue d\'ensemble</div>', unsafe_allow_html=True)
    progress = get_progress_summary()

    score_display = progress.score_moyen if progress.score_moyen is not None else "—"

    st.markdown(
        f"""
        <div class="dash-grid">
          <div class="dash-card">
            <div class="label">Matière</div>
            <div class="value">{memory.student.matiere or "Non définie"}</div>
          </div>
          <div class="dash-card">
            <div class="label">Niveau</div>
            <div class="value">{memory.student.niveau.value}</div>
          </div>
          <div class="dash-card">
            <div class="label">Score moyen global</div>
            <div class="value accent">{score_display}</div>
          </div>
          <div class="dash-card">
            <div class="label">Quiz réalisés</div>
            <div class="value">{progress.total_quiz}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-label">Score moyen par chapitre</div>', unsafe_allow_html=True)
    if progress.scores_par_chapitre:
        st.dataframe(
            [{"Chapitre": c.chapter, "Score moyen": c.score_moyen, "Nb quiz": c.nb_quiz} for c in progress.scores_par_chapitre],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Aucun quiz réalisé pour le moment.")

    st.markdown('<div class="section-label">Difficultés enregistrées</div>', unsafe_allow_html=True)
    if memory.difficultes:
        pills_html = "".join(f'<span class="diff-pill">⚠ {d}</span>' for d in memory.difficultes)
        st.markdown(pills_html, unsafe_allow_html=True)
    else:
        st.warning("Aucune difficulté enregistrée.")

    st.markdown('<div class="section-label">Planning</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="dash-grid small">
          <div class="dash-card">
            <div class="label">Tâches totales</div>
            <div class="value">{progress.total_tasks}</div>
          </div>
          <div class="dash-card">
            <div class="label">Tâches terminées</div>
            <div class="value accent">{progress.done_tasks}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Chat ---
with tab_chat:
    st.markdown('<div class="section-label">Discussion avec ton assistant</div>', unsafe_allow_html=True)

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
    st.markdown('<div class="section-label">Générer un quiz</div>', unsafe_allow_html=True)

    chapter = st.text_input("Chapitre à réviser", placeholder="Exemple : respiration cellulaire")
    number_of_questions = st.slider("Nombre de questions", min_value=3, max_value=10, value=5)

    if st.button("✨ Générer quiz"):
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
        st.markdown('<div class="section-label">Réponds aux questions</div>', unsafe_allow_html=True)

        if "quiz_answers" not in st.session_state:
            st.session_state.quiz_answers = {}

        correction = st.session_state.get("quiz_correction")
        feedback_by_id = {f.question_id: f for f in correction.feedback} if correction else {}

        for q in st.session_state.quiz:
            with st.container(border=True):
                fb = feedback_by_id.get(q.id)

                st.markdown(
                    f'<span class="q-badge">{q.id}</span>'
                    f'<span style="font-family:\'Space Grotesk\', sans-serif; font-size:1.05rem; color:var(--navy); font-weight:600;">{q.question}</span>',
                    unsafe_allow_html=True,
                )

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

                st.markdown(f'<span class="q-type-tag">Type · {q.type.value}</span>', unsafe_allow_html=True)

        if st.button("✔️ Corriger le quiz", type="primary"):
            with st.spinner("Correction en cours..."):
                st.session_state.quiz_correction = correct_quiz(
                    st.session_state.quiz, st.session_state.quiz_answers
                )
            st.rerun()

        if correction:
            st.markdown(
                f"""
                <div class="dash-grid small">
                  <div class="dash-card">
                    <div class="label">Score obtenu</div>
                    <div class="value accent">{correction.score}/100</div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            saved_chapter = st.session_state.get("quiz_chapter", chapter)
            feedback_summary = "; ".join(
                f.explanation for f in correction.feedback if f.is_correct is False
            ) or "Bon travail, peu d'erreurs."

            if st.button("💾 Sauvegarder ce résultat dans la mémoire"):
                save_quiz_result(saved_chapter, correction.score, feedback_summary)
                st.success("Résultat sauvegardé dans la mémoire.")
                st.rerun()


# --- Planning ---
with tab_planning:
    st.markdown('<div class="section-label">Ajouter une tâche</div>', unsafe_allow_html=True)

    task = st.text_input("Nouvelle tâche", placeholder="Exemple : Réviser la cellule")
    duration = st.number_input("Durée en minutes", min_value=10, max_value=180, value=45)

    if st.button("➕ Ajouter tâche"):
        if task.strip():
            add_planning_task(task, duration)
            st.success("Tâche ajoutée.")
            st.rerun()
        else:
            st.error("Entre une tâche.")

    st.markdown('<div class="section-label">Mes tâches</div>', unsafe_allow_html=True)
    planning = get_planning()

    if planning:
        for item in planning:
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
                col1.markdown(f"**{item.task}**")
                col2.markdown(f"⏱ {item.duration_minutes} min")

                badge_class = "done" if item.status.value == "terminé" else "todo"
                col3.markdown(f'<span class="status-badge {badge_class}">{item.status.value}</span>', unsafe_allow_html=True)

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
    st.markdown('<div class="section-label">Ajouter une difficulté</div>', unsafe_allow_html=True)
    new_difficulty = st.text_input("Nouvelle difficulté", placeholder="Exemple : manque de vocabulaire scientifique")

    if st.button("➕ Ajouter difficulté"):
        if new_difficulty.strip():
            add_difficulty(new_difficulty.strip())
            st.success("Difficulté ajoutée.")
            st.rerun()

    st.markdown('<div class="section-label">Difficultés actuelles</div>', unsafe_allow_html=True)
    for i, diff in enumerate(memory.difficultes):
        col1, col2 = st.columns([4, 1])
        col1.markdown(f'<span class="diff-pill">⚠ {diff}</span>', unsafe_allow_html=True)
        if col2.button("Supprimer", key=f"remove_diff_{i}"):
            remove_difficulty(diff)
            st.rerun()

    st.divider()
    st.markdown('<div class="section-label">Mémoire complète</div>', unsafe_allow_html=True)
    st.json(memory.model_dump(mode="json"))

    st.divider()
    if st.button("🗑️ Réinitialiser mémoire"):
        reset_memory()
        st.warning("Mémoire réinitialisée.")
        st.rerun()