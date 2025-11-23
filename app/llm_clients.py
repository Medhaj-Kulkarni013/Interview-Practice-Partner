# app/llm_clients.py
"""
Robust Groq client wrapper.

Behavior:
 - Load GROQ_API_KEY and GROQ_MODEL from .env automatically (via python-dotenv).
 - Try to use official Groq SDK if available.
 - If SDK initialization or call fails, automatically fall back to a direct HTTP POST using requests.
 - Exposes:
     - groq_enabled() -> bool
     - groq_generate(prompt, max_tokens=..., temperature=...) -> str

Note: this file tolerates small differences in SDK shapes and returns a string.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Find project root (parent of 'app' directory)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env from project root
load_dotenv(dotenv_path=ENV_FILE)

GROQ_API_KEY_RAW = os.getenv("GROQ_API_KEY", "")
# tolerate accidental surrounding quotes and whitespace
GROQ_API_KEY = GROQ_API_KEY_RAW.strip().strip('"').strip("'")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# HTTP endpoint for fallback (Groq's public API)
GROQ_HTTP_URL = os.getenv("GROQ_HTTP_URL", "https://api.groq.com/openai/v1/chat/completions")

def groq_enabled():
    return bool(GROQ_API_KEY)

# ---------------------------
# SDK client (lazy)
# ---------------------------
_sdk_client = None
def _init_sdk_client():
    global _sdk_client
    if _sdk_client is not None:
        return _sdk_client
    if not groq_enabled():
        return None
    try:
        from groq import Groq
        _sdk_client = Groq(api_key=GROQ_API_KEY)
        return _sdk_client
    except Exception:
        # SDK not usable — return None to trigger HTTP fallback
        _sdk_client = None
        return None

# ---------------------------
# HTTP fallback
# ---------------------------
def _groq_http_generate(prompt: str, max_tokens: int = 250, temperature: float = 0.2) -> str:
    """
    Fallback path using requests directly to Groq HTTP API.
    Returns the text result or raises RuntimeError with helpful message.
    """
    import requests
    if not groq_enabled():
        raise RuntimeError("GROQ_API_KEY missing for HTTP fallback.")
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    try:
        resp = requests.post(GROQ_HTTP_URL, headers=headers, json=payload, timeout=30)
    except Exception as e:
        raise RuntimeError(f"HTTP request to Groq failed: {e}") from e

    # Provide helpful error messages for common statuses
    if resp.status_code == 401 or resp.status_code == 403:
        raise RuntimeError(f"Groq API authentication failed (status {resp.status_code}). Check your GROQ_API_KEY and model permissions. Response: {resp.text}")
    if resp.status_code >= 400:
        raise RuntimeError(f"Groq HTTP error (status {resp.status_code}): {resp.text}")

    try:
        data = resp.json()
    except Exception:
        # Non-JSON response
        return resp.text

    # Try common response shapes
    try:
        # common: {"choices":[{"message":{"content":"..."}}]}
        if "choices" in data and len(data["choices"]) > 0:
            c0 = data["choices"][0]
            if isinstance(c0, dict):
                if "message" in c0 and isinstance(c0["message"], dict):
                    return c0["message"].get("content", "").strip()
                if "text" in c0:
                    return c0.get("text", "").strip()
        # fallback: return JSON string if we can't parse
        return json.dumps(data)
    except Exception as e:
        raise RuntimeError(f"Failed to parse Groq HTTP response: {e}. Raw response: {data}") from e

# ---------------------------
# Public function
# ---------------------------
def groq_generate(prompt: str, max_tokens: int = 250, temperature: float = 0.2) -> str:
    """
    Generate text using Groq. Tries SDK first, then HTTP fallback.
    Returns a string. Raises RuntimeError on unrecoverable errors.
    """
    if not groq_enabled():
        raise RuntimeError("GROQ_API_KEY not configured. Add to environment or .env.")

    # Try SDK path
    client = _init_sdk_client()
    if client is not None:
        try:
            resp = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            # Robust parsing of SDK reply
            try:
                choice0 = resp.choices[0]
                # SDK often exposes message as an object/dict
                if hasattr(choice0, "message"):
                    msg = choice0.message
                    if isinstance(msg, dict):
                        return msg.get("content", "").strip()
                    # object with attribute
                    return getattr(msg, "content", str(msg)).strip()
                if isinstance(choice0, dict):
                    if "message" in choice0 and isinstance(choice0["message"], dict):
                        return choice0["message"].get("content", "").strip()
                    if "text" in choice0:
                        return choice0.get("text", "").strip()
                return str(choice0).strip()
            except Exception:
                return str(resp).strip()
        except Exception as e:
            # If SDK call fails, fallthrough to HTTP fallback with a warning in the exception message
            sdk_err = e
            # attempt HTTP fallback
            try:
                return _groq_http_generate(prompt, max_tokens=max_tokens, temperature=temperature)
            except Exception as http_e:
                # Prefer returning an informative error that includes both SDK and HTTP errors
                raise RuntimeError(f"Groq SDK error: {sdk_err}. HTTP fallback error: {http_e}") from http_e

    # If SDK not available, use HTTP fallback
    return _groq_http_generate(prompt, max_tokens=max_tokens, temperature=temperature)
