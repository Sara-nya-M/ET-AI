import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    print("Testing text-embedding-004...")
    response = client.models.embed_content(
        model="text-embedding-004",
        contents="Hello world"
    )
    print("SUCCESS: text-embedding-004 worked!")
except Exception as e:
    print(f"FAILED: text-embedding-004 -> {e}")

try:
    print("Testing text-embedding-004 with models/ prefix...")
    response = client.models.embed_content(
        model="models/text-embedding-004",
        contents="Hello world"
    )
    print("SUCCESS: models/text-embedding-004 worked!")
except Exception as e:
    print(f"FAILED: models/text-embedding-004 -> {e}")
