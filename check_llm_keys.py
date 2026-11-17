"""
Har LLM key ko ek chhote sawal se test karo. Kaun si key chal rahi hai, kaun si nahi.
Colab:  !python check_llm_keys.py
Agar kisi mein "model" ka error aaye to wo provider ke available model ke naam bhi dikhata hai.
"""
import requests

import llm_providers as L

_GROQ = ("https://api.groq.com/openai/v1/models", lambda k: {"Authorization": f"Bearer {k}"})
MODEL_LIST_URL = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/models",
               lambda k: {"x-goog-api-key": k}),
    "gptoss": _GROQ, "qwen": _GROQ, "allam": _GROQ,
    "cohere": ("https://api.cohere.com/v1/models", lambda k: {"Authorization": f"Bearer {k}"}),
}


def list_models(provider, key):
    url, hdr = MODEL_LIST_URL[provider]
    try:
        r = requests.get(url, headers=hdr(key), timeout=30)
        d = r.json()
        items = d.get("data") or d.get("models") or []
        names = [(m.get("id") or m.get("name") or "").replace("models/", "") for m in items]
        return names[:12]
    except Exception as e:
        return [f"(list nahi mili: {str(e)[:60]})"]


def main():
    for p in L.MODELS:
        key = L.get_key(p)
        if not key:
            print(f"{p:11} KEY NAHI ({L.KEY_ENV[p]} set nahi)")
            continue
        try:
            text, model = L.ask(p, "Reply with exactly one word: OK")
            print(f"{p:11} OK    model={model} jawab={text.strip()[:30]!r}")
        except Exception as e:
            print(f"{p:11} FAIL  model={L.MODELS[p]}  {str(e)[:160]}")
            if "404" in str(e) or "model" in str(e).lower():
                print(f"{'':11} available models: {list_models(p, key)}")
    print("\nYe poora output paste karo (keys nahi, sirf ye output).")


if __name__ == "__main__":
    main()
