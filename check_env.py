import os

print("--- Environment Variables ---")
for k, v in os.environ.items():
    if "GEMINI" in k or "API" in k or "PROXY" in k or "HTTP" in k:
        print(f"{k}: {v}")
