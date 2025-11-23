# smoke_test.py
"""
Simple smoke test to ensure the InterviewAgent runs without Streamlit.
Requires GROQ_API_KEY to be set in .env file.
Run using:
    python smoke_test.py
"""

import os
import sys

# Add project root to Python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(ROOT_DIR)

from app.interview_agent import InterviewAgent


def run_smoke_test():
    print("=== Running Smoke Test ===")

    agent = InterviewAgent(role="software_engineer")

    # Step 1: Get a question
    q = agent.get_next_question()
    print("\nQuestion:", q)

    # Step 2: Provide a simple answer
    sample_answer = (
        "I improved performance by adding caching, indexing, and optimizing database queries."
    )

    # Step 3: Process the answer
    result = agent.process_answer(sample_answer, q)

    # Step 4: Display results
    print("\nFollow-up Question:", result.get("followup"))
    print("\nFeedback:")
    for bullet in result.get("feedback", []):
        print(" -", bullet)

    print("\nHistory entries:", len(result.get("history", [])))
    print("\n=== Smoke Test Completed ===")


if __name__ == "__main__":
    run_smoke_test()
