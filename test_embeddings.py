import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

candidate_models = [
    "text-embedding-004",
    "models/text-embedding-004",
    "text-multilingual-embedding-002",
    "models/text-multilingual-embedding-002",
    "embedding-001",
    "models/embedding-001",
    "text-embedding-gecko",
    "models/text-embedding-gecko"
]

print("Testing embedding models...")
for model in candidate_models:
    try:
        response = client.models.embed_content(
            model=model,
            contents="Hello world"
        )
        print(f"SUCCESS: {model}")
    except Exception as e:
        print(f"FAILED: {model} -> {e}")
