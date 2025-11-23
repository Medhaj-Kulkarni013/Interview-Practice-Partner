# app/interview_agent.py
"""
InterviewAgent:
 - Generates questions dynamically using Groq AI
 - Uses Groq for follow-up questions and feedback when available
 - Falls back to rule-based feedback when Groq disabled
 - Tracks full session history
"""

import json
from pathlib import Path
from typing import Optional

# Handle imports for both package and direct execution contexts
try:
    from .llm_clients import groq_enabled, groq_generate
    from .feedback_engine import simple_scores, scores_to_feedback
except ImportError:
    # Fallback for direct execution
    from llm_clients import groq_enabled, groq_generate
    from feedback_engine import simple_scores, scores_to_feedback

# Find project root and construct paths
_PROJECT_ROOT = Path(__file__).parent.parent
RUBRIC_PATH = _PROJECT_ROOT / "sample_questions" / "rubric.json"


def _format_role_name(role: str) -> str:
    """Convert role identifier to human-readable format."""
    return role.replace("_", " ").title()  # "software_engineer" -> "Backend Engineer"


def detect_agentic_case(answer: str, candidate_history=None):
    """Detect answer edge cases for agentic/clarifying interviewer response."""
    if candidate_history is None:
        candidate_history = []
    a = (answer or "").strip().lower()
    if not a:
        return "EMPTY"
    if a in {"idk", "i don’t know", "i dont know", "don't know", "dont know", "no idea"}:
        return "IDK"
    if len(a.split()) < 5:
        return "TOO_SHORT"
    # 'Confused persona' patterns
    confused_phrases = [
        "help", "what do i do", "how does this work", "instructions", "explain", "lost", "don’t understand", "dont understand", "not sure", "confused"
    ]
    if any(p in a for p in confused_phrases):
        return "CONFUSED"
    # 'Chatty persona' / off-topic
    chatty_phrases = [
        "hello", "hi", "what's your name", "how are you", "good morning", "good afternoon", "good evening"
    ]
    if any(a.startswith(p) or a == p for p in chatty_phrases):
        return "CHATTY"
    return None


class InterviewAgent:
    def __init__(self, role: str = "software_engineer"):
        if not groq_enabled():
            raise RuntimeError(
                "Groq API is required for question generation. "
                "Please set GROQ_API_KEY in your .env file."
            )
        
        self.role = role
        self.history = []   # Stores all Q&A messages
        self.rubric = self._load_rubric()
        self.current_main_question = None
        self.followup_count = 0
        self.agentic_case_counter = {}

    def _load_rubric(self) -> dict:
        """Load rubric with error handling."""
        if not RUBRIC_PATH.exists():
            raise FileNotFoundError(
                f"Rubric file not found at {RUBRIC_PATH}. "
                "Please ensure sample_questions/rubric.json exists."
            )
        try:
            with open(RUBRIC_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in rubric file: {e}") from e

    # ------------------------------------------
    # Get the next question
    # ------------------------------------------
    def get_next_question(self) -> Optional[str]:
        """Generate a new interview question dynamically using Groq AI."""
        if not groq_enabled():
            raise RuntimeError(
                "Groq API is required for question generation. "
                "Please set GROQ_API_KEY in your .env file."
            )
        
        try:
            # Format role name for better readability
            role_display = _format_role_name(self.role)
            
            # Generate a new question based on role and interview history
            question_prompt = (
                f"You are a technical interviewer conducting a mock interview for a {role_display} position.\n"
                f"Generate ONE interview question that is:\n"
                f"- Appropriate for a {role_display} role at entry-level or fresher (0-1 years experience)\n"
                f"- Focused on core concepts, fundamentals, or general ability\n"
                f"- Should NOT require prior job experience or advanced knowledge\n"
                f"- Easy enough for someone who just graduated or is switching careers\n"
                f"- Different from questions already asked\n"
                f"- Can be answered in 1-2 minutes (should not require essay or system design answers)\n\n"
            )
            
            # Add context about previous questions to avoid repetition
            if self.history:
                prev_questions = [
                    msg["text"] for msg in self.history 
                    if msg.get("role") == "interviewer"
                ]
                if prev_questions:
                    question_prompt += (
                        f"Previous questions asked:\n"
                        + "\n".join(f"- {q}" for q in prev_questions[-3:])  # Last 3 questions
                        + "\n\nGenerate a NEW, different question.\n"
                    )
            
            question_prompt += "Respond with ONLY the question, no additional text."
            
            q = groq_generate(question_prompt, max_tokens=100, temperature=0.7)
            q = q.strip()
            
            # Clean up common prefixes the LLM might add
            for prefix in ["Question:", "Q:", "Here's a question:", "Here's the question:"]:
                if q.startswith(prefix):
                    q = q[len(prefix):].strip()
            
            if q:
                self.current_main_question = q  # Track the last true main question
                self.followup_count = 0         # Reset follow-up count for this new question
                self.history.append({"role": "interviewer", "text": q})
                return q
            else:
                return None
                
        except Exception as e:
            raise RuntimeError(f"Failed to generate question: {e}") from e

    # ------------------------------------------
    # Process the candidate answer
    # ------------------------------------------
    def process_answer(self, answer: str, question_text: str) -> dict:
        """
        Returns:
        {
          "followup": Optional[str],
          "feedback": List[str],
          "history": List[dict]
        }
        """

        # -------------------------------------------
        # End interview command handling
        # -------------------------------------------
        if self.is_end_command(answer):
            # add the user's end request to history (so it's visible in logs)
            self.history.append({"role": "candidate", "text": answer})
            return {
                "followup": None,
                "feedback": ["Interview ended at your request."],
                "history": self.history,
                "finished": True
            }

        self.history.append({"role": "candidate", "text": answer})
        followup = None
        feedback_bullets = []

        # =============== AGENTIC EDGE CASES ===============
        persona_case = detect_agentic_case(answer, [msg["text"] for msg in self.history if msg.get("role") == "candidate"])
        clarifying = None
        persona_case_map = {
            "EMPTY": "Don't worry, just give your best try—even a short answer helps!",
            "IDK": "It's okay if you don't know. Take a guess or try to explain your thinking!",
            "TOO_SHORT": "Could you add a bit more detail to your answer? You'll get better feedback that way!",
            "CONFUSED": "Just answer as best you can—there's no penalty for mistakes!",
            "CHATTY": "Let's focus on the interview questions; practice will help you improve!",
        }
        if persona_case:
            clarifying = persona_case_map.get(persona_case, None)
            # Optionally, escalate after multiple chatty/confused in a row
            self.agentic_case_counter[persona_case] = self.agentic_case_counter.get(persona_case, 0) + 1
            if persona_case in {"CONFUSED", "CHATTY"} and self.agentic_case_counter[persona_case] > 1:
                clarifying += " (Try to give an answer to keep the practice going!)"
            return {
                "followup": clarifying,
                "feedback": ["Provide a more complete answer to get valuable feedback!"],
                "history": self.history,
            }
        # ====================================================
        # ========== RULE-BASED FALLBACK FEEDBACK ============
        # ====================================================
        if not feedback_bullets:
            scores = simple_scores(answer, rubric=self.rubric)
            feedback_bullets = scores_to_feedback(scores, rubric=self.rubric)

        # Return fully structured output
        return {
            "followup": followup,
            "feedback": feedback_bullets,
            "history": self.history
        }
    

    def is_end_command(self, answer: str) -> bool:
        """
        Return True if the candidate's answer is a command to end the interview.
        Comparison is case-insensitive and trims whitespace. 
        """
        if not answer:
            return False
        text = answer.strip().lower()
        end_phrases = {
            "end", "end interview", "stop", "stop interview", "quit", "exit", "finish", "finish interview", "terminate", "terminate interview"
        }
        # Exact phrase match (case-insensitive)
        if text in end_phrases:
            return True

        # Also accept short variants where user just types "end." or "quit."
        normalized = text.strip(".!?,")
        if normalized in end_phrases:
            return True
        return False

