# app/interview_agent.py
"""
InterviewAgent:
 - Generates questions dynamically using Groq AI
 - Uses Groq for follow-up questions and feedback (pure agentic)
 - Tracks full session history
 - Requires Groq API for all operations
"""
from typing import Optional

# Handle imports for both package and direct execution contexts
try:
    from .llm_clients import groq_enabled, groq_generate
except ImportError:
    # Fallback for direct execution
    from llm_clients import groq_enabled, groq_generate


def _format_role_name(role: str) -> str:
    """Convert role identifier to human-readable format."""
    return role.replace("_", " ").title()  # "software_engineer" -> "Backend Engineer"


def detect_agentic_case(answer: str):
    """Detect answer edge cases for agentic/clarifying interviewer response."""
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
        self.followup_count = 0
        self.agentic_case_counter = {}

    def _generate_ai_followup(self, question: str, answer: str) -> Optional[str]:
        """
        Generate an AI-powered follow-up question that probes deeper into the candidate's answer.
        Returns None if Groq is unavailable or if we should move to the next main question.
        """
        if not groq_enabled():
            return None
        
        # Limit follow-ups to 2 per main question to keep interview flowing
        if self.followup_count >= 2:
            return None
        
        try:
            role_display = _format_role_name(self.role)
            
            # Build context from recent history
            recent_context = []
            for msg in self.history[-6:]:  # Last 3 Q&A pairs
                if msg.get("role") == "interviewer":
                    recent_context.append(f"Interviewer: {msg['text']}")
                elif msg.get("role") == "candidate":
                    recent_context.append(f"Candidate: {msg['text']}")
            
            followup_prompt = (
                f"You are a technical interviewer conducting a mock interview for a {role_display} position.\n\n"
                f"Current question: {question}\n"
                f"Candidate's answer: {answer}\n\n"
            )
            
            if recent_context:
                followup_prompt += "Recent conversation:\n" + "\n".join(recent_context[-4:]) + "\n\n"
            
            followup_prompt += (
                f"Generate ONE follow-up question that:\n"
                f"- Is EASY to MEDIUM difficulty - appropriate for freshers and entry-level candidates\n"
                f"- Probes deeper but keeps it SIMPLE - asks for clarification or a basic example\n"
                f"- Asks for simple explanations, basic examples, or fundamental understanding\n"
                f"- Is specific to what they mentioned (not generic)\n"
                f"- Helps assess their basic understanding and communication skills\n"
                f"- Should NOT require advanced knowledge, complex problem-solving, or deep technical analysis\n"
                f"- Can be answered in 30-60 seconds with basic knowledge\n\n"
                f"Examples of good follow-ups (keep them simple):\n"
                f"- 'Can you give me a simple example of that?'\n"
                f"- 'Can you explain that in simpler terms?'\n"
                f"- 'What would be a basic use case for that?'\n"
                f"- 'How would you explain this to someone new to the topic?'\n\n"
                f"AVOID complex follow-ups about trade-offs, edge cases, or advanced scenarios.\n"
                f"Keep it FRESH-FRIENDLY and EASY.\n\n"
                f"Respond with ONLY the follow-up question, no additional text or explanation."
            )
            
            followup = groq_generate(followup_prompt, max_tokens=120, temperature=0.7)
            followup = followup.strip()
            
            # Clean up common prefixes
            for prefix in ["Follow-up:", "Follow-up question:", "Q:", "Question:"]:
                if followup.lower().startswith(prefix.lower()):
                    followup = followup[len(prefix):].strip()
            
            if followup and len(followup) > 10:  # Ensure it's a real question
                self.followup_count += 1
                self.history.append({"role": "interviewer", "text": followup})
                return followup
            
            return None
        except Exception as e:
            # If AI generation fails, return None to fall back to next main question
            return None

    def _generate_ai_feedback(self, question: str, answer: str) -> list:
        """
        Generate AI-powered feedback on the candidate's answer.
        Returns a list of feedback bullet points.
        Pure agentic - requires Groq API.
        """
        if not groq_enabled():
            raise RuntimeError(
                "Groq API is required for feedback generation. "
                "Please set GROQ_API_KEY in your .env file."
            )
        
        try:
            role_display = _format_role_name(self.role)
            
            feedback_prompt = (
                f"You are an expert interview coach providing constructive feedback.\n\n"
                f"Role: {role_display}\n"
                f"Question: {question}\n"
                f"Candidate's Answer: {answer}\n\n"
                f"Provide constructive feedback on:\n"
                f"1. Communication: clarity, structure, conciseness\n"
                f"2. Technical Knowledge: depth, accuracy, relevance\n"
                f"3. Areas for Improvement: specific, actionable suggestions\n\n"
                f"Format your response as 3(not more than that) bullet points. Each bullet should:\n"
                f"- Start with a strength or area to improve\n"
                f"- Be specific and actionable\n"
                f"- Be encouraging and constructive\n"
                f"- Focus on what would make this answer stronger\n\n"
                f"Example format:\n"
                f"- Strong communication — you clearly explained the concept with good structure.\n"
                f"- Consider adding more technical details about implementation specifics.\n"
                f"- Great use of examples — try to quantify the impact when possible.\n\n"
                f"Provide feedback now (bullet points only, no additional text):"
            )
            
            feedback_text = groq_generate(feedback_prompt, max_tokens=300, temperature=0.5)
            feedback_text = feedback_text.strip()
            
            # Parse feedback into bullet points
            bullets = []
            for line in feedback_text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Remove common bullet markers
                for marker in ["-", "•", "*", "1.", "2.", "3.", "4.", "5."]:
                    if line.startswith(marker):
                        line = line[len(marker):].strip()
                if line:
                    bullets.append(line)
            
            # If parsing failed, return the text as a single bullet
            if not bullets:
                bullets = [feedback_text] if feedback_text else []
            
            # If still empty, raise error (pure agentic - no fallback)
            if not bullets:
                raise RuntimeError("AI feedback generation returned empty result.")
            
            return bullets[:5]  # Limit to 5 bullets max
            
        except Exception as e:
            # Re-raise with context (pure agentic - no fallback)
            raise RuntimeError(f"Failed to generate AI feedback: {e}") from e

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
                f"- EASY to MEDIUM difficulty only - suitable for freshers and entry-level candidates (0-1 years experience)\n"
                f"- Focused on BASIC concepts, fundamentals, and simple practical knowledge\n"
                f"- Should NOT require prior job experience, advanced knowledge, or complex problem-solving\n"
                f"- Easy enough for someone who just graduated, is a student, or switching careers\n"
                f"- Keep it SIMPLE - avoid complex topics, system design, architecture, or advanced algorithms\n"
                f"- Ask about basic definitions, simple examples, or fundamental understanding\n"
                f"- Different from questions already asked\n"
                f"- Can be answered in 1-2 minutes with basic knowledge (no essay or deep technical analysis required)\n\n"
                f"Examples of appropriate questions:\n"
                f"- 'What is [basic concept] and why is it useful?'\n"
                f"- 'Can you explain [simple topic] in your own words?'\n"
                f"- 'What are the basic steps to [simple task]?'\n"
                f"- 'Give me a simple example of [fundamental concept]'\n\n"
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
                self.followup_count = 0  # Reset follow-up count for this new question
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

        # =============== AGENTIC EDGE CASES ===============
        persona_case = detect_agentic_case(answer)
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
        # ========== AI-POWERED FEEDBACK GENERATION =========
        # ====================================================
        feedback_bullets = self._generate_ai_feedback(question_text, answer)
        
        # ====================================================
        # ========== AI-POWERED FOLLOW-UP GENERATION =========
        # ====================================================
        # Generate follow-up question (method handles limit checking)
        # Works for both main questions and follow-ups
        followup = self._generate_ai_followup(question_text, answer)
        
        # If no follow-up was generated (maxed out or error), followup is None
        # The UI will then call get_next_question() to move to the next main question

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

