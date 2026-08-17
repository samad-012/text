
# Voice AI Restaurant Reservation Agent

A voice AI restaurant reservation assistant built as a take-home assignment for **Anjan AI**.

The agent allows customers to interact with a fictional restaurant, **Saffron **, using natural voice conversation. It can understand speech, respond with speech, and take real actions through reservation tools.

The project implements **two voice interaction modes using the same agent and reservation tools**:

- **Real-time streaming mode** — continuous audio streaming with low-latency responses and barge-in support.
- **Non-streaming turn-based mode** — record a complete utterance, transcribe it, run the agent with tools, generate the response, and play the resulting audio.

---

## Features

- Voice input and voice output
- Real-time streaming conversation
- Non-streaming turn-based conversation
- LLM tool calling
- Restaurant reservation management
- Availability checking
- Booking reservations
- Retrieving reservations
- Modifying reservations
- Cancelling reservations
- Conversation history per session
- Barge-in/interruption support in streaming mode
- In-memory mock reservation backend
- Groq → Hugging Face LLM fallback when Groq rate limits are reached
- Tool execution trace displayed in the frontend
- REST API and WebSocket API

---

## Architecture

```text
                         ┌─────────────────────┐
                         │      Next.js UI     │
                         │      Frontend       │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┴────────────────┐
                    │                                │
              Turn-based                         Streaming
                    │                                │
              HTTP POST /api/turn              WebSocket /ws/stream
                    │                                │
                    └───────────────┬────────────────┘
                                    │
                         ┌──────────▼──────────┐
                         │      FastAPI        │
                         │      Backend        │
                         └──────────┬──────────┘
                                    │
                         ┌──────────▼──────────┐
                         │    Voice Agent      │
                         │  LLM + Tool Calling │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
         Availability            Booking             Retrieve
         Modify                 Cancel                Restaurant Info
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
                         In-memory reservation store
