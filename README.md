# Hotel Booking Agent

A conversational AI agent that helps users search for and book hotels. Powered by **gemma4:31b** running locally via Ollama, with real hotel data from Google Hotels (SerpApi).

## How It Works

```
User (terminal) <--> Agent Core (tool-use loop) <--> SerpApi (hotel search)
                           |                         Google Search (web search)
                      Ollama (local)
                      gemma4:31b
```

1. You type a message in the terminal
2. The full conversation history + system prompt is sent to gemma4 via Ollama
3. The model decides whether to call a tool or respond directly
4. If a tool is called, the result is fed back and the model responds based on real data
5. A structured `BookingState` tracks preferences across turns so the agent never forgets

## Tools

The model has 5 tools and decides autonomously which to use:

| Tool | Purpose | Data Source |
|------|---------|-------------|
| `search_hotels` | Find hotels by destination, dates, guests | SerpApi Google Hotels |
| `get_hotel_details` | Get detailed info about a specific hotel | SerpApi Google Hotels |
| `update_booking_state` | Save user preferences (dates, budget, etc.) | Internal state |
| `web_search` | Answer any real-time question (weather, events, etc.) | SerpApi Google Search |
| `run_python_code` | Execute Python for calculations or API calls | Local subprocess |

When the model answers from its own knowledge (no tool called), this is logged so you always know the data source.

## Setup

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- gemma4:31b model pulled: `ollama pull gemma4:31b`

### Install

```bash
git clone <repo-url>
cd booking-agent
pip install -r requirements.txt
```

### API Key

Get a free API key at [serpapi.com](https://serpapi.com) (100 searches/month on free tier).

```bash
cp .env.example .env
# Edit .env and add your key:
# SERPAPI_API_KEY=your_key_here
```

### Run

```bash
python run.py
```

## Project Structure

```
booking-agent/
├── run.py                # Entry point
├── .env                  # API key (gitignored)
├── .env.example          # Template
├── requirements.txt
└── src/
    ├── main.py           # Terminal loop, prerequisite checks
    ├── agent.py          # Core tool-use loop with Ollama
    ├── models.py         # BookingState, HotelSummary, BookingPhase (Pydantic)
    ├── tools.py          # Tool functions + JSON schema definitions for Ollama
    ├── hotel_api.py      # SerpApi HTTP client (hotels + web search)
    ├── prompts.py        # System prompt template with state injection
    └── display.py        # Rich terminal UI (tables, spinners, panels)
```

## Architecture Decisions

### Conversation Memory

Two mechanisms work together:

- **Full conversation history** — every message (user, assistant, tool calls, tool results) is stored in a Python list and sent to the model each turn. A sliding window keeps the last 40 messages.
- **Structured BookingState** — a Pydantic model injected into the system prompt every turn. Contains destination, dates, budget, preferences, and hotel search results with names/prices. This ensures critical info survives even when older messages are truncated by the context window.

### Why No LangChain

Ollama's Python library has native tool-calling support (`ollama.chat(tools=...)`). The entire agent loop is ~50 lines of Python. Adding LangChain would introduce framework complexity for no practical benefit at this scale.

### Context Window (num_ctx)

Set to 16384 tokens. On a 32GB M1 Pro with gemma4:31b (19GB model), this balances speed (~4-5s responses) with conversation capacity (~15-20 turns). The BookingState in the system prompt acts as a safety net when older messages are dropped.

### Temperature

Set to 0.7 (default is 1.0). Lower temperature improves reliability of tool-calling decisions while keeping conversation natural.

## Configuration

Key parameters in `src/agent.py`:

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `MODEL` | `gemma4:31b` | Ollama model name |
| `NUM_CTX` | `16384` | Context window size in tokens |
| `MAX_HISTORY_MESSAGES` | `40` | Sliding window for conversation history |
| `MAX_TOOL_ROUNDS` | `5` | Max tool calls per turn (prevents infinite loops) |
| `temperature` | `0.7` | Controls response randomness (0=deterministic, 1=creative) |

## Example Conversation

```
You: I want to find a hotel in Rome for next weekend, 2 people
  TOOL CALL: update_booking_state(destination='Rome', check_in='2026-05-03', ...)
  TOOL CALL: search_hotels(destination='Rome', check_in_date='2026-05-03', ...)

Here are the top options in Rome:
1. Courtyard by Marriott - $342/night - 4.3 rating - 4 stars
2. Virtus Prestige - $83/night - 4.1 rating - 3 stars
...

You: What will the weather be like there?
  TOOL CALL: web_search(query='weather in Rome May 3 2026')

Rome in early May is pleasant — around 20-25°C with mostly sunny skies...

You: What's the total cost for option 2 with 20% VAT for 2 nights?
  TOOL CALL: run_python_code(code='price=83; nights=2; vat=0.20; ...')

The total for Virtus Prestige: $199.20 (2 nights with 20% VAT)
```
