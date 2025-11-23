# app/main.py
"""
Streamlit UI for Interview Practice Partner.
Run with:
    streamlit run app/main.py
"""

import os
import sys
import streamlit as st

# Add current directory to path so imports work even when run from repo root
sys.path.append(os.path.dirname(__file__))

from interview_agent import InterviewAgent
from llm_clients import groq_enabled

# ---------------------------------------------------------
# Streamlit Page Setup
# ---------------------------------------------------------
st.set_page_config(
    page_title="Interview Practice Partner",
    page_icon="💼",
    layout="wide"
)
st.title("💼 Interview Practice Partner")
st.markdown("Practice your technical interview skills with AI-powered feedback")
st.markdown("---")

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
st.sidebar.header("⚙️ Settings")

role = st.sidebar.selectbox("Choose Role", ["software_engineer", "sales", "retail_associate"], index=0)

llm_status = "✅ Yes (Groq Enabled)" if groq_enabled() else "❌ No (Required)"
st.sidebar.write(f"**LLM Available:** {llm_status}")

if not groq_enabled():
    st.sidebar.error("⚠️ Groq API is required for full agentic mode. Please set GROQ_API_KEY in your .env file.")

st.sidebar.markdown("_Tip: type 'end interview' or 'quit' to finish the interview._")

if st.sidebar.button("🔄 Start New Interview", type="primary", use_container_width=True):
    try:
        st.session_state.agent = InterviewAgent(role=role)
        st.session_state.messages = []

        q = st.session_state.agent.get_next_question()
        if q:
            st.session_state.messages.append(("Interviewer", q))
        else:
            st.session_state.messages.append(("System", "Failed to generate question."))
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Error starting interview: {e}")

# ---------------------------------------------------------
# Initialize session state
# ---------------------------------------------------------
if "agent" not in st.session_state:
    st.session_state.agent = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------
# Display Messages (Chat Interface)
# ---------------------------------------------------------
if st.session_state.messages:
    # Create a container for the chat messages
    chat_container = st.container()
    with chat_container:
        for who, text in st.session_state.messages:
            if who == "Interviewer":
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(text)
            elif who == "You":
                with st.chat_message("user", avatar="👤"):
                    st.write(text)
            elif who == "Feedback":
                with st.chat_message("assistant", avatar="💡"):
                    st.markdown("**Feedback:**")
                    # Handle both list and string formats
                    if isinstance(text, list):
                        for bullet in text:
                            st.markdown(f"- {bullet}")
                    elif isinstance(text, str):
                        # Parse feedback bullets if they're in text format
                        for line in text.split("\n"):
                            if line.strip().startswith("-"):
                                st.markdown(line)
                            elif line.strip():
                                st.markdown(f"- {line}")
                    else:
                        st.write(text)
            else:
                with st.chat_message("system"):
                    st.info(text)
else:
    st.info("👆 Click 'Start New Interview' in the sidebar to begin!")

# ---------------------------------------------------------
# Answer Input Box
# ---------------------------------------------------------
if st.session_state.agent:
    st.markdown("---")
    with st.form("answer_form", clear_on_submit=True):
        answer = st.text_area(
            "Your Answer",
            height=150,
            placeholder="Type your answer here...",
            key="answer_input"
        )
        submitted = st.form_submit_button("📤 Submit Answer", type="primary", use_container_width=True)
        
        if submitted and answer.strip():
            # Fetch last question
            last_question = None
            for who, msg_text in reversed(st.session_state.messages):
                if who == "Interviewer":
                    last_question = msg_text
                    break

            if last_question is None:
                st.warning("⚠️ No active question. Please restart interview.")
            else:
                try:
                    # Process answer
                    with st.spinner("Processing your answer..."):
                        result = st.session_state.agent.process_answer(answer.strip(), last_question)

                    # Append user's answer
                    st.session_state.messages.append(("You", answer.strip()))

                    # If agent signalled the interview finished, handle it
                    if result.get("finished"):
                        # Add feedback (if any)
                        fb = result.get("feedback", [])
                        if fb:
                            st.session_state.messages.append(("Feedback", fb))
                        st.session_state.messages.append(("Interviewer", "Interview ended. Thank you!"))
                        # Reset agent so UI shows Start New Interview again
                        st.session_state.agent = None
                        st.rerun()

                    # Normal flow: add feedback then follow-up/next question
                    feedback_bullets = result.get("feedback", [])
                    if feedback_bullets:
                        st.session_state.messages.append(("Feedback", feedback_bullets))

                    if result.get("followup"):
                        st.session_state.messages.append(("Interviewer", result["followup"]))
                    else:
                        next_q = st.session_state.agent.get_next_question() if st.session_state.agent else None
                        if next_q:
                            st.session_state.messages.append(("Interviewer", next_q))
                        else:
                            st.session_state.messages.append(("Interviewer", "🎉 Interview complete! Thank you for practicing."))

                    st.rerun()
                except Exception as e:
                    st.error(f"Error processing answer: {e}")
        elif submitted and not answer.strip():
            st.warning("Please enter an answer before submitting.")

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown("---")
with st.expander("ℹ️ About"):
    st.markdown(
        """
        **How it works:**
        - The app uses Groq LLM to generate interview questions dynamically (when enabled)
        - Questions are AI-generated and adapt based on your role and previous answers
        - You'll receive AI-powered feedback on your answers and follow-up questions
        - Follow-up questions are always AI-generated to probe deeper into your responses
        
        **Requirements:**
        - `GROQ_API_KEY` must be set in your `.env` file for full agentic mode
        - Without an API key, the app will use a static question bank (non-agentic demo) and rule-based feedback
        
        **Tips:**
        - Be specific and detailed in your answers
        - Use the STAR method (Situation, Task, Action, Result) for behavioral questions
        - Think about trade-offs and edge cases for technical questions
        - Each interview session generates varied questions
        """
    )
