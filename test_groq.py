# test_groq.py
"""
Quick test to verify Groq API connectivity.
Run:
    python test_groq.py
"""

import os
from app.llm_clients import groq_enabled, groq_generate

def main():
    print("Groq Enabled:", groq_enabled())

    if not groq_enabled():
        print("❌ GROQ_API_KEY missing. Add it to your .env or environment.")
        return

    try:
        response = groq_generate("Say 'Groq API is working!'", max_tokens=20, temperature=0.0)
        print("Groq Response:", response)
    except Exception as e:
        print("❌ Error communicating with Groq API:")
        print(e)

if __name__ == "__main__":
    main()
