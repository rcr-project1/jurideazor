import os

import requests
from dotenv import load_dotenv

load_dotenv()  # reads .env from the repository root

# In Colab: from google.colab import userdata ; key = userdata.get("GROQ_API_KEY")
key = os.getenv("GROQ_API_KEY")
if not key:
    raise SystemExit("GROQ_API_KEY is not set. Put it in .env or export it.")

r = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": "Réponds juste : OK"}],
    },
    timeout=60,
)
print(r.status_code)
print(r.json()["choices"][0]["message"]["content"])
