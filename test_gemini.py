import os
from google import genai
from dotenv import load_dotenv

def test_api():
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment!")
        return

    print("API Key found. Initializing client...")
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Say: 'Gemini connectivity verification successful!'"
        )
        print("Gemini response:")
        print(response.text)
    except Exception as e:
        print(f"Error connecting to Gemini API: {e}")

if __name__ == "__main__":
    test_api()
