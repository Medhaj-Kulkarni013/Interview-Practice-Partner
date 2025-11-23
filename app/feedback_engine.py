# app/feedback_engine.py
"""
Deterministic fallback feedback engine for when Groq is unavailable.
Provides:
 - simple_scores(answer, rubric) -> {"communication":int,...}
 - scores_to_feedback(scores, rubric) -> [bullets]
"""

import json
import re
from pathlib import Path

def load_rubric(rubric_path=None):
    """
    Load rubric.json from the sample_questions folder.
    """
    if rubric_path is None:
        project_root = Path(__file__).parent.parent
        rubric_path = project_root / "sample_questions" / "rubric.json"
    else:
        rubric_path = Path(rubric_path)
    
    if not rubric_path.exists():
        raise FileNotFoundError(
            f"Rubric file not found at {rubric_path}. "
            "Please ensure sample_questions/rubric.json exists."
        )
    
    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in rubric file: {e}") from e


def simple_scores(answer: str, rubric: dict = None):
    """
    Compute 3 scores (1-5 scale): communication, depth, relevance.
    Purely rule-based for fallback mode.
    """
    if rubric is None:
        rubric = load_rubric()

    if not answer or not answer.strip():
        return {
            "communication": 1,
            "depth": 1,
            "relevance": 1
        }

    tokens = [t for t in re.split(r"\s+", answer.strip()) if t]
    n_tokens = len(tokens)

    # Get thresholds with defaults
    thresholds = rubric.get("thresholds", {})
    short_answer_tokens = thresholds.get("short_answer_tokens", 12)
    good_depth_matches = thresholds.get("good_depth_matches", 2)

    # Communication score: based on answer length & structure
    if n_tokens >= short_answer_tokens:
        comm = 4 if n_tokens < 40 else 5
    else:
        comm = 2 if n_tokens >= 5 else 1

    # Depth score: keyword matching
    depth_keywords = rubric.get("depth_keywords", [])
    matches = sum(1 for kw in depth_keywords if kw.lower() in answer.lower())

    if matches >= good_depth_matches + 2:
        depth = 5
    elif matches >= good_depth_matches:
        depth = 4
    elif matches >= 1:
        depth = 3
    else:
        depth = 1

    # Relevance score: very simple heuristic
    relevance = 3
    if n_tokens < short_answer_tokens:
        relevance = 2
    if matches >= 1:
        relevance = min(5, relevance + 1)

    # Clamp scores to [1,5]
    def clamp(x): return max(1, min(5, int(x)))

    return {
        "communication": clamp(comm),
        "depth": clamp(depth),
        "relevance": clamp(relevance)
    }


def scores_to_feedback(scores: dict, rubric: dict = None):
    """
    Convert numeric scores into friendly feedback bullets.
    """
    if rubric is None:
        rubric = load_rubric()

    comm = scores.get("communication", 3)
    depth = scores.get("depth", 3)
    rel = scores.get("relevance", 3)

    bullets = []

    # Get messages with defaults
    messages = rubric.get("messages", {})
    structure_tip = messages.get("structure_tip", "Try structuring answers with STAR (Situation, Task, Action, Result).")
    detail_tip = messages.get("detail_tip", "Add concrete technical details: components, trade-offs, and numbers.")
    on_topic_tip = messages.get("on_topic_tip", "Keep answers focused on the asked problem; brief examples are fine.")

    # Communication feedback
    if comm >= 4:
        bullets.append("Strong communication — clear and structured.")
    elif comm == 3:
        bullets.append("Good clarity; could benefit from slightly more structure (use STAR method).")
    else:
        bullets.append(structure_tip)

    # Depth feedback
    if depth >= 4:
        bullets.append("Good technical depth — strong use of concepts and trade-offs.")
    elif depth == 3:
        bullets.append("Some technical details present; add more specifics like components or metrics.")
    else:
        bullets.append(detail_tip)

    # Relevance feedback
    if rel >= 4:
        bullets.append("Answer was highly relevant and on point.")
    elif rel == 3:
        bullets.append("Mostly relevant — try tying each statement directly to the question.")
    else:
        bullets.append(on_topic_tip)

    return bullets
