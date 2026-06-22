import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("Listing models...")
try:
    for m in client.models.list():
        # print name and supported actions
        print(f"Model: {m.name}, Supported actions: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")
