import os
from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Erreur : GEMINI_API_KEY est introuvable dans le fichier .env")

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explique-moi en une phrase ce qu'est la photosynthèse."
)

print(response.text)