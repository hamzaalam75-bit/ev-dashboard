"""
5 LLM providers ek jaisi shakal mein. Har provider: ask(prompt) -> (text, model_name).
Keys sirf environment se aati hain (kabhi code mein mat likhna):
    GEMINI_API_KEY, GROQ_API_KEY (3 models: gpt-oss, Qwen, ALLaM), COHERE_API_KEY
Model ke naam aksar badalte rehte hain. Agar 404 / "model not found" aaye to neeche MODELS
mein naam badlo (check_llm_keys.py available naam dikha deta hai).
DRY_RUN=1 set karo to koi API call nahi hoti, nakli jawab aate hain (sirf pipeline test ke liye).
"""
import os
import re
import time

import requests

MODELS = {
    "gemini": "gemini-flash-latest",       # Google (2.5-flash naye users ke liye band hai)
    "gptoss": "openai/gpt-oss-120b",       # OpenAI open model, Groq par
    "qwen": "qwen/qwen3.8-27b",            # Alibaba, Groq par
    "allam": "allam-2-7b",                 # SDAIA (Saudi), Groq par. Agar ye fail ho to "openai/gpt-oss-20b" lagao
    "cohere": "command-a-03-2025",         # Cohere
}
KEY_ENV = {
    "gemini": "GEMINI_API_KEY", "gptoss": "GROQ_API_KEY", "qwen": "GROQ_API_KEY",
    "allam": "GROQ_API_KEY", "cohere": "COHERE_API_KEY",
}
GEMINI_FALLBACKS = ["gemini-flash-lite-latest", "gemini-2.5-flash-lite"]   # pehla model masroof ho to
TIMEOUT = 60
MAX_TOKENS = 1500
LAST = {"seconds": None}      # akhri kamyab API call ka time (retry ka intezaar shamil nahi)


def _post(url, headers, payload, retries=3):
    """429, 5xx aur timeout par ruk kar dobara koshish. Aakhir mein hamesha RuntimeError."""
    last = "unknown"
    for attempt in range(1, retries + 1):
        t0 = time.time()
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
            LAST["seconds"] = round(time.time() - t0, 1)   # sirf is ek call ka time
        except requests.RequestException as e:          # timeout / network masla
            last = f"network: {type(e).__name__}"
            if attempt < retries:
                time.sleep(10 * attempt)
                continue
            raise RuntimeError(last)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
            time.sleep(15 * attempt)
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        return r.json()
    raise RuntimeError(last)


def _openai_style(url, key, model, prompt, extra_headers=None):
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    headers.update(extra_headers or {})
    data = _post(url, headers, {
        "model": model, "max_tokens": MAX_TOKENS, "temperature": 0.2,
        "messages": [{"role": "user", "content": prompt}],
    })
    text = data["choices"][0]["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()   # Qwen ki "soch" hata do


def ask_gemini(prompt, key, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    data = _post(url, {"x-goog-api-key": key, "Content-Type": "application/json"}, {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": MAX_TOKENS * 3},
    })
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def ask_groq(prompt, key, model):
    return _openai_style("https://api.groq.com/openai/v1/chat/completions", key, model, prompt)


def ask_cohere(prompt, key, model):
    data = _post("https://api.cohere.com/v2/chat",
                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                 {"model": model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.2, "max_tokens": MAX_TOKENS})
    return "".join(c.get("text", "") for c in data["message"]["content"])


ASK = {"gemini": ask_gemini, "gptoss": ask_groq, "qwen": ask_groq,
       "allam": ask_groq, "cohere": ask_cohere}


def get_key(provider):
    return os.getenv(KEY_ENV[provider])


def ask(provider, prompt):
    """(text, model) wapas deta hai. Key na ho to RuntimeError('no_key')."""
    model = MODELS[provider]
    if os.getenv("DRY_RUN") == "1":
        return f"[DRY RUN {provider}] nakli jawab", model
    key = get_key(provider)
    if not key:
        raise RuntimeError("no_key")
    candidates = [model] + (GEMINI_FALLBACKS if provider == "gemini" else [])
    last = None
    for m in candidates:
        try:
            return ASK[provider](prompt, key, m), m      # asal model jo chala wahi CSV mein jayega
        except RuntimeError as e:
            last = e
    raise last
