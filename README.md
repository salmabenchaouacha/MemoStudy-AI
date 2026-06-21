# 🧠 MemoStudy AI

Assistant intelligent de révision avec mémoire longue, propulsé par l'API Gemini.

L'application aide un étudiant à réviser en tenant compte de son profil, de
son niveau et de ses difficultés, via un chat pédagogique, des quiz générés
et corrigés automatiquement, un planning de révision et un tableau de bord
de progression.

## Fonctionnalités

- Chat de révision personnalisé selon le profil et les préférences de l'étudiant
- Quiz générés par IA (QCM, questions directes, questions ouvertes) avec correction automatique
- Planning de révision avec suivi des tâches
- Tableau de bord de progression (scores, chapitres révisés)
- Mémoire longue persistée entre les sessions
- Repli automatique si l'API Gemini est indisponible

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env   # puis renseigne ta clé GEMINI_API_KEY
streamlit run app.py
```

## Structure du projet

```
memostudy-ai/
├── app.py                # Interface Streamlit
├── models.py              # Schéma de données (Pydantic)
└── services/
    ├── memory_service.py     # Persistance de la mémoire
    ├── gemini_client.py      # Appels à l'API Gemini
    ├── agent_service.py      # Logique du chat
    ├── quiz_service.py       # Génération et correction des quiz
    ├── planning_service.py   # Gestion du planning
    └── progress_service.py   # Statistiques du dashboard
