import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key or "your_gemini_api_key_here" in api_key:
    print("API Key not found or invalid.")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    models = [m['name'] for m in data.get('models', []) if 'gemini' in m['name'].lower()]
    for m in models:
        print(m)
else:
    print("Error:", response.status_code, response.text)
