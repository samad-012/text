# Saffron — Voice AI Restaurant Agen
The agent, **Ben**, can understand spoken customer requests, use tools to interact with a mock restaurant reservation backend, and respond naturally in voice.
The project provides two interaction modes using the same agent logic and tools:

1. **Turn-based / Non-streaming voice agent**
2. **Real-time streaming voice agent**
## Voice AI Assistant
The assistant is called **Ben**, the voice reservation assistant for the fictional restaurant **Saffron**.
The assistant can:
* Check table availability
* Create reservations
* Retrieve existing reservations
* Modify reservations
* Cancel reservations
* Answer supported restaurant-related questions
* Ask for missing information
* Confirm important actions before executing them
* Gracefully handle requests it cannot fulfill

The system prompt explicitly prevents the agent from inventing restaurant information or claiming an action was successful unless the corresponding tool actually succeeds.
# Tools

The agent uses function/tool calling to decide which backend operation is required based on the customer's request.

The reservation tools are implemented against mock/in-memory restaurant data.

The core tools include:

### `check_availability(date, time, party_size)`

Checks whether a table is available for the requested date, time, and party size.

### `book_reservation(name, phone, date, time, party_size)`

Creates a reservation after availability has been checked and the customer confirms the details.

The tool returns a confirmation ID when successful.

### `retrieve_reservation(confirmation_id or phone)`

Retrieves an existing reservation using either its confirmation ID or phone number.

### `cancel_reservation(confirmation_id)`

Cancels an existing reservation after the agent retrieves and confirms the relevant booking.

### Additional restaurant services

The agent also supports additional reservation/restaurant operations implemented in the tool registry, including reservation modification and restaurant information.

All tools are registered centrally through:
```text
app/tools/registry.py
```
The agent dynamically maps model-generated tool calls to the corresponding Python functions
# Agent Behaviour

The agent is instructed to behave conservatively and never fabricate information.

For example, before creating a reservation it must have:

* Customer name
* Phone number
* Date
* Time
* Party size

The booking flow is:

```text
Customer request
       ↓
Collect missing information
       ↓
Check availability
       ↓
Read reservation details back
       ↓
Ask customer for confirmation
       ↓
Book reservation
       ↓
Return confirmation ID
```

Similarly, cancellation requires the agent to retrieve the reservation when necessary, read the reservation details back to the customer, obtain confirmation, and only then execute the cancellation.

This prevents the model from accidentally performing destructive actions without confirmation.

---

# Architecture

The application separates the voice layer, agent layer, and tool layer.

```text
                    ┌─────────────────────┐
                    │      Customer       │
                    │       Voice         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │        STT          │
                    │  Speech → Text      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     Agent / LLM     │
                    │                     │
                    │  Understand intent  │
                    │  Select tools       │
                    │  Generate response  │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
             ┌─────────────┐       ┌─────────────┐
             │    Tools    │       │ Final Text  │
             │             │       │  Response   │
             │ Availability│       └──────┬──────┘
             │ Booking     │              │
             │ Retrieval   │              ▼
             │ Cancellation│       ┌─────────────┐
             │ Modification│       │     TTS     │
             └─────────────┘       │ Text → Voice│
                                    └──────┬──────┘
                                           │
                                           ▼
                                      Customer Voice

# Two Agent Modes
Both modes use the same:
* System prompt
* Tool schemas
* Tool implementations
* Tool execution function
* Conversation history format
* Agent decision-making behaviour

The main function is:

```python
run_turn_streaming()
```

It uses the asynchronous Groq client:

```python
AsyncGroq
```

and requests streamed LLM output:

```python
stream = await async_client.chat.completions.create(
    model=GROQ_MODEL,
    messages=history,
    tools=TOOL_SCHEMAS,
    tool_choice="auto",
    stream=True,
)
```

Instead of waiting for the complete response, the agent receives token fragments as they are generated.

```text
User speaks
    ↓
Streaming audio / STT
    ↓
LLM
    ↓
Token delta
    ↓
Token delta
    ↓
Token delta
    ↓
Sentence buffering
    ↓
TTS
    ↓
Audio sent back
```

The streaming agent emits:

```text
tool_call
tool_result
text_delta
done
```

For example, the LLM may generate:

```text
"Sure, I can help"
```

as several token fragments:

```text
"Sure"
", I"
" can"
" help"
```

The streaming route can buffer those fragments into meaningful sentences before passing them to TTS.

This allows speech generation to begin before the entire LLM response has been generated.

---

# Why the Streaming Agent Is Separate

The streaming implementation is intentionally not just a modified version of the turn-based function.

The two execution models are different.

The turn-based agent uses synchronous execution:

```python
client.chat.completions.create(...)
```

while the streaming agent uses:

```python
AsyncGroq
```

and:

```python
stream=True
```

The streaming implementation also has to reconstruct tool calls because tool-call arguments can arrive across multiple streaming chunks.

For example:

```text
Chunk 1 → tool name
Chunk 2 → partial arguments
Chunk 3 → more arguments
Chunk 4 → remaining arguments
```

The streaming agent therefore collects tool-call fragments by index:

```python
tool_calls_by_index
```

and reconstructs the complete function call before executing it.

This keeps the two transport/execution models independent while maintaining identical tool behaviour.

---

# Keeping Tool Behaviour Consistent

Both modes use the same tool execution layer.

The turn-based agent uses:

```python
TOOL_FUNCTIONS
TOOL_SCHEMAS
run_tool()
```

The streaming implementation also calls:

```python
run_tool()
```

Therefore, the streaming mode does not implement a separate version of reservation logic.

The architecture is:

```text
                    Shared Agent Behaviour
                           │
              ┌────────────┴────────────┐
              │                         │
        Turn-Based                 Streaming
              │                         │
        run_turn()              run_turn_streaming()
              │                         │
              └────────────┬────────────┘
                           │
                     Shared Tools
                           │
                    run_tool()
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        Availability    Booking    Cancellation
```

This reduces the possibility of the two modes behaving differently.

---

# LLM Providers

The project uses Groq as the primary LLM provider.

The model is configured through:

```env
GROQ_MODEL=...
```

The application also supports a Hugging Face OpenAI-compatible endpoint as a fallback when Groq reaches a rate limit.

The fallback is configured through:

```env
HF_TOKEN=...
HF_MODEL=...
```

The agent therefore has the following high-level flow:

```text
Groq
  │
  ├── Request succeeds → use Groq response
  │
  └── Rate limit
          ↓
     Hugging Face
```

The fallback is intentionally triggered for rate-limit errors rather than silently replacing the primary provider for every request.

---

# Speech-to-Text

The project uses Groq's speech transcription API.

The configured STT model is:

```env
GROQ_STT_MODEL=whisper-large-v3-turbo
```

The STT layer converts the customer's speech into text before it is passed to the agent.

---

# Text-to-Speech

The project also supports Deepgram for speech generation.

The configured TTS model is:

```env
DEEPGRAM_TTS_MODEL=aura-2-thalia-en
```

Deepgram is responsible for converting the generated assistant response back into speech.

The streaming architecture is designed so that generated text can be buffered into sentence-sized pieces and sent to TTS without waiting for the entire LLM response.

---

# Error Handling

The agent is designed to fail safely.

## Missing information

If required booking information is missing, the assistant asks the customer instead of guessing.

For example:

```text
Customer:
"Book a table for four tomorrow."

Agent:
"Sure. What time would you like the table?"
```

## Tool failure

Tool execution is wrapped in error handling.

A failed tool returns:

```python
{
    "success": False,
    "error": "..."
}
```

The LLM then receives the tool result and can explain the problem to the customer.

## Invalid tool arguments

The agent catches invalid JSON generated for tool arguments and returns a tool error rather than crashing the request.

## LLM rate limits

If Groq reaches a rate limit, the application attempts to use the configured Hugging Face fallback provider.

If the fallback provider is also rate-limited, the customer receives a polite temporary-error response.

## Agent iteration limit

Both agent implementations have a maximum number of iterations:

```python
max_iterations=5
```

If the agent cannot complete a request within that limit, it returns a safe fallback message rather than looping indefinitely.

---

# Project Structure

The relevant architecture is approximately:

```text
backend/
│
├── app/
│   ├── agent/
│   │   ├── agent.py
│   │   └── streaming_agent.py
│   │
│   ├── routes/
│   │   ├── turn_based.py
│   │   └── streaming.py
│   │
│   ├── tools/
│   │   └── registry.py
│   │
│   ├── config.py
│   └── main.py
│
├── .env
├── requirements.txt
└── README.md
```

The exact project structure may contain additional frontend, service, or utility files.

## Installation

This project uses **[uv]** for Python environment and dependency management.

### 1. Clone the repository

```bash
git clone <your-github-repository-url>
cd <repository-name>
```

### 2. Install uv

If `uv` is not already installed, follow the official installation instructions at uv
``
### 3. Install project dependencies

The project's dependencies are defined in `pyproject.toml`.

Run:

```bash
uv sync
```

This creates the project's virtual environment and installs the required dependencies.

### 4. Activate the virtual environment

```bash
source .venv/bin/activate
```

Alternatively, commands can be run directly through `uv` without manually activating the environment.

### 5. Configure environment variables

Create a `.env` file in the backend directory.

Example:

```env
GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=your_available_groq_model
GROQ_STT_MODEL=whisper-large-v3-turbo

HF_TOKEN=your_huggingface_token
HF_MODEL=your_huggingface_model

DEEPGRAM_API_KEY=your_deepgram_api_key
DEEPGRAM_TTS_MODEL=aura-2-thalia-en
DEEPGRAM_STT_MODEL=nova-3

# Running the Backend

From the backend directory:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Alternatively, after activating the environment:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

The backend will start at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

# Project Dependencies

Dependencies are managed through `pyproject.toml`.

The project does not require a manually maintained `requirements.txt` file.

The `uv.lock` file should also be committed to the repository so that the same dependency versions can be reproduced across environments.

The typical project setup is:

```text
backend/
├── pyproject.toml
├── uv.lock
├── .env
├── .gitignore
└── app/
```

`pyproject.toml` defines the project's dependencies and metadata, while `uv.lock` records the resolved dependency versions.

---

# Development Commands

Install/synchronize dependencies:

```bash
uv sync
```

Run the application:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

# Environment Variables

The application loads environment variables using `python-dotenv`.

The main configuration is handled through:

```text
app/config.py
```

The following services are used by the application:

| Variable             | Purpose                       |
| -------------------- | ----------------------------- |
| `GROQ_API_KEY`       | Groq API authentication       |
| `GROQ_MODEL`         | Primary LLM model             |
| `GROQ_STT_MODEL`     | Groq speech-to-text model     |
| `HF_TOKEN`           | Hugging Face authentication   |
| `HF_MODEL`           | Hugging Face fallback LLM     |
| `DEEPGRAM_API_KEY`   | Deepgram authentication       |
| `DEEPGRAM_TTS_MODEL` | Deepgram text-to-speech model |
| `DEEPGRAM_STT_MODEL` | Deepgram speech-to-text model |

---

# Quick Start

For a new environment, the complete setup is:

```bash
git clone <your-github-repository-url>
cd <repository-name>

uv sync

cp .env.example .env
# Add your API keys to .env

uv run uvicorn app.main:app --reload --port 8000
```

Then open:

```text
http://127.0.0.1:8000/docs
```

to access the API documentation.

---

# Why uv?

`uv` is used to provide a fast and reproducible Python development environment.

Instead of manually creating a virtual environment and installing packages with `pip`, the project configuration is defined in `pyproject.toml` and dependencies are synchronized using:

```bash
uv sync
```

The `uv.lock` file ensures that dependency versions can be reproduced consistently when setting up the project on another machine.

# Example Conversation

### Booking

```text
Customer:
"Hi, I'd like to book a table for four tomorrow at 7 PM."

Ben:
"Sure. May I have your name and phone number?"

Customer:
"John, 9876543210."

Ben:
"I'll check availability for four people tomorrow at 7 PM."

→ check_availability()

Ben:
"A table is available. To confirm, that's four people tomorrow at
7 PM under John. Shall I book it?"

Customer:
"Yes."

→ book_reservation()

Ben:
"Your reservation is confirmed. Your confirmation ID is..."
```

---

# Retrieving a Reservation

```text
Customer:
"Can you find my reservation?"

Ben:
"Sure. What's the phone number associated with the reservation?"

Customer:
"9876543210."

→ retrieve_reservation()

Ben:
"I found your reservation for four people at 7 PM..."
```

---

# Cancelling a Reservation

```text
Customer:
"I want to cancel my reservation."

→ retrieve_reservation()

Ben:
"I found your reservation for four people tomorrow at 7 PM.
Would you like me to cancel it?"

Customer:
"Yes."

→ cancel_reservation()

Ben:
"Your reservation has been cancelled."
```



## Provider Fallback

Groq is the primary LLM provider because of its low-latency inference.

Hugging Face is configured as a fallback for Groq rate-limit errors.

This provides additional resilience during the demo without changing the agent/tool architecture.

---

