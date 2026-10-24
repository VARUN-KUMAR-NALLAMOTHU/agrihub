"""Run:  python3 check_gemini.py   - tells you which Gemini models work with your key."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not key:
    raise SystemExit("No GEMINI_API_KEY in .env")
base = "https://generativelanguage.googleapis.com/v1beta"

r = requests.get(f"{base}/models", params={"key": key, "pageSize": 100}, timeout=20)
print("ListModels status:", r.status_code)
if r.status_code != 200:
    print(r.text[:400].replace(key, "***"))
    raise SystemExit("Key rejected - create a new one at https://aistudio.google.com/apikey")

models = [m["name"].split("/", 1)[1] for m in r.json().get("models", [])
          if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]]
print("Flash models your key can use:", *models, sep="\n  ")
print("\nTesting each (first 6)...")
for m in models[:6]:
    try:
        t = requests.post(f"{base}/models/{m}:generateContent", params={"key": key}, timeout=20,
                          json={"contents": [{"role": "user", "parts": [{"text": "Say OK"}]}]})
        print(f"  {m}: {t.status_code}", "WORKS" if t.status_code == 200 else t.text[:80].replace("\n", " "))
    except requests.RequestException as e:
        print(f"  {m}: network error {type(e).__name__}")
print("\nPut a WORKS model in .env as GEMINI_MODEL=<name>")
