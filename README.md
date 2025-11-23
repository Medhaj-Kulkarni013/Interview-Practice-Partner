# Interview Practice Partner

An AI-powered conversational agent that helps users prepare for job interviews through mock interviews with intelligent follow-up questions and personalized feedback.

## 🎯 Overview

This project implements a chat-based AI agent that conducts mock interviews for various roles (software engineer, sales, retail associate). The agent uses Groq's LLM to dynamically generate interview questions, ask contextual follow-up questions, and provide detailed feedback on candidate responses.

## ✨ Features

- **Dynamic Question Generation**: AI-generated interview questions tailored to specific roles and experience levels
- **Intelligent Follow-ups**: Context-aware follow-up questions that probe deeper into candidate answers
- **AI-Powered Feedback**: Detailed, constructive feedback on communication, technical knowledge, and areas for improvement
- **Multi-Role Support**: Conduct interviews for software engineer, sales, and retail associate roles
- **Edge Case Handling**: Gracefully handles confused users, chatty users, and edge cases
- **Pure Agentic Design**: Fully AI-powered system requiring Groq API for all operations
- **Session Management**: Tracks full interview history for context-aware interactions

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (main.py)                    │
│  - Chat interface                                            │
│  - Session state management                                  │
│  - User input handling                                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              InterviewAgent (interview_agent.py)             │
│  - Question generation                                       │
│  - Answer processing                                         │
│  - Follow-up generation                                      │
│  - Feedback generation                                       │
│  - History tracking                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Client (llm_clients.py)                      │
│  - Groq SDK integration                                      │
│  - HTTP fallback for API calls                               │
│  - API key management                                        │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

#### 1. **Pure Agentic Architecture**
- **Decision**: Implement a fully AI-powered system that requires Groq API for all operations
- **Rationale**: Ensures consistent, high-quality AI-generated content throughout the interview experience. Aligns with assignment focus on agentic behavior.
- **Implementation**: 
  - All features (questions, follow-ups, feedback) use Groq LLM
  - System requires API key to start, ensuring consistent behavior
  - Error handling provides clear feedback when API is unavailable

#### 2. **Context-Aware Follow-up Questions**
- **Decision**: Generate follow-up questions that are specific to the candidate's answer, not generic
- **Rationale**: Mimics real interviewer behavior by probing deeper into specific points mentioned by the candidate
- **Implementation**: 
  - Uses recent conversation history (last 6 messages)
  - Limits to 2 follow-ups per main question to maintain interview flow
  - AI analyzes the answer to generate contextual probes

#### 3. **Edge Case Detection and Handling**
- **Decision**: Proactively detect and handle different user personas (confused, chatty, empty answers)
- **Rationale**: Improves user experience by providing helpful guidance when users are unsure or go off-topic
- **Implementation**: 
  - Pattern matching for common edge cases
  - Escalating responses for repeated edge cases
  - Maintains interview flow while being supportive

#### 4. **Session History Tracking**
- **Decision**: Maintain full conversation history throughout the interview
- **Rationale**: Enables context-aware question generation and prevents repetition
- **Implementation**: 
  - Stores all Q&A pairs with role metadata
  - Uses history to avoid repeating questions
  - Provides context for follow-up generation

#### 5. **Role-Based Question Generation**
- **Decision**: Generate questions appropriate for specific roles and experience levels
- **Rationale**: Ensures questions are relevant and achievable for entry-level candidates
- **Implementation**: 
  - Role-specific prompts to the LLM
  - Explicit instructions for entry-level (0-1 years) difficulty
  - Avoids advanced topics requiring extensive experience

#### 6. **AI-Powered Feedback System**
- **Decision**: Use AI exclusively for all feedback generation
- **Rationale**: Provides consistent, nuanced, and personalized feedback that adapts to each answer's specific content and context
- **Implementation**: 
  - AI analyzes communication clarity, structure, and conciseness
  - Assesses technical knowledge depth, accuracy, and relevance
  - Provides specific, actionable improvement suggestions
  - Maintains encouraging and constructive tone throughout

## 📁 Project Structure

```
Interview-Practice-Partner/
├── app/
│   ├── main.py                 # Streamlit UI and session management
│   ├── interview_agent.py      # Core agent logic (questions, follow-ups, feedback)
│   └── llm_clients.py          # Groq API client with SDK/HTTP fallback
├── requirements.txt            # Python dependencies
├── test_groq.py               # Groq API connectivity test
├── smoke_test.py              # Basic functionality test
└── README.md                  # This file
```

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Groq API key (get one at https://console.groq.com/)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Interview-Practice-Partner
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Create a `.env` file in the project root:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
   
   **Note**: The `.env` file is gitignored for security. Make sure to add your API key.

5. **Test Groq connectivity** (optional)
   ```bash
   python test_groq.py
   ```

6. **Run the application**
   ```bash
   streamlit run app/main.py
   ```

   The app will open in your browser at `http://localhost:8501`

7. **Deployment**

   I have deployed it using streamlit.io at https://interview-practice-partner-k7rwaoattaglu4afwewupp.streamlit.app/

## 🎮 Usage

1. **Start an Interview**
   - Select your role from the sidebar (Software Engineer, Sales, or Retail Associate)
   - Click "Start New Interview"
   - The AI will generate your first question

2. **Answer Questions**
   - Type your answer in the text area
   - Click "Submit Answer"
   - Receive AI-powered feedback and follow-up questions

3. **Continue the Interview**
   - Answer follow-up questions to dive deeper
   - After 2 follow-ups or when ready, the agent moves to the next main question
   - Continue until you're satisfied with your practice

4. **End the Interview**
   - Type "end interview", "quit", or "finish" to end the session
   - You can start a new interview at any time

## 🧪 Testing

### Smoke Test
Run the basic functionality test:
```bash
python smoke_test.py
```

This verifies:
- Agent initialization
- Question generation
- Answer processing
- Feedback generation

### Test Scenarios

The agent is designed to handle multiple user personas:

1. **The Confused User**: Asks for help or seems lost
   - Agent provides encouraging guidance
   - Example: "Just answer as best you can—there's no penalty for mistakes!"

2. **The Efficient User**: Wants quick results
   - Agent provides concise feedback
   - Follow-ups are limited to maintain flow

3. **The Chatty User**: Goes off-topic frequently
   - Agent gently redirects to interview questions
   - Example: "Let's focus on the interview questions; practice will help you improve!"

4. **Edge Case Users**: Provides invalid inputs or empty answers
   - Agent detects and handles gracefully
   - Provides helpful prompts to continue

## 🔧 Configuration

### Model Selection

Change the Groq model in `.env`:
```env
GROQ_MODEL=llama-3.3-70b-versatile  # or other Groq models
```

## 🎯 Assignment Requirements Coverage

✅ **Conduct mock interviews for specific roles**
- Supports software_engineer, sales, retail_associate roles
- Dynamic question generation based on role

✅ **Ask follow-up questions like a real interviewer**
- AI-generated contextual follow-ups
- Probes deeper into candidate answers
- Limited to 2 per question for natural flow

✅ **Provide post-interview feedback**
- AI-powered feedback on communication, technical knowledge
- Identifies areas for improvement
- Actionable and constructive suggestions

✅ **Handle multiple user personas**
- Confused user detection and guidance
- Chatty user redirection
- Edge case handling (empty, too short, off-topic)

✅ **Chat-based interaction**
- Streamlit chat interface
- Natural conversation flow
- Session management

## 🛠️ Technical Implementation Details

### LLM Integration

- **Primary**: Groq SDK with automatic HTTP fallback
- **Model**: llama-3.3-70b-versatile (configurable)
- **Error Handling**: Clear error messages when API is unavailable; UI gracefully handles errors

### Question Generation Strategy

1. Role-specific prompts ensure relevance
2. History tracking prevents repetition
3. Entry-level difficulty calibration
4. 1-2 minute answer length target

### Follow-up Generation Strategy

1. Analyzes candidate's answer for specific points
2. Generates contextual probes (examples, trade-offs, edge cases)
3. Uses recent conversation history for context
4. Limits follow-ups to maintain interview pacing

### Feedback Generation Strategy

1. Analyzes communication clarity and structure
2. Assesses technical depth and accuracy
3. Provides specific, actionable improvements
4. Encouraging and constructive tone

## 📝 Design Philosophy

This agent prioritizes:

1. **Conversation Quality**: Natural, flowing interactions over rigid Q&A
2. **Intelligence**: Context-aware responses that adapt to user input
3. **Pure Agentic Behavior**: Fully AI-powered system for consistent, high-quality interactions
4. **User Experience**: Supportive guidance for all user types, including edge cases
5. **Educational Value**: Detailed feedback that helps users improve

## 🔒 Security & Privacy

- API keys stored in `.env` (gitignored)
- No data persistence beyond session
- All processing happens locally (except API calls)
- No user data collection or storage

## 🐛 Known Limitations

- Requires Groq API key for all functionality (pure agentic design)
- Follow-up questions limited to 2 per main question
- System requires active API connection (no offline mode)
- No persistent interview history across sessions

## 🚀 Future Enhancements

Potential improvements:
- Voice interaction support
- Interview history persistence
- Performance analytics and trends
- Custom role/question templates
- Multi-round interview sessions
- Post-interview summary reports

## 📄 License

This project is created as part of the Eightfold.ai AI Agent Building Assignment.

## 👤 Author

Created for the Eightfold.ai assignment submission.

---

**Note**: This is a demonstration project. For production use, consider adding authentication, rate limiting, and enhanced error handling.
