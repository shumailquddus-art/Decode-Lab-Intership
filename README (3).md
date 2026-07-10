# 🤖 Custom AI Chatbot with Memory

**DecodeLabs — Generative AI Industrial Training, Project 1**

A terminal chatbot that remembers everything said earlier in the same
session, by maintaining an in-memory array of the conversation and resending
it with every turn — built on Anthropic's Claude API.

**Key features:**
- 🧠 Stateful multi-turn memory (Claude is stateless by default — this adds the session layer)
- 🛡️ Input validation gate (blocks empty/whitespace payloads before they hit the API)
- 🪟 Sliding-window FIFO pruning (prevents context/token overflow on long sessions)
- ✅ Offline self-test suite — verifies memory works without spending API credits

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Run it

```bash
python3 chatbot.py
```

Commands inside the chat:
- `/reset` — clear the in-memory history and start a fresh session
- `/history` — show how many turns/entries are currently stored
- `/quit` — exit

Options:
```bash
python3 chatbot.py --model claude-sonnet-4-5 --max-turns 20 --system "You are a helpful assistant."
```

## Run the offline memory exam (no API key needed)

This runs the exact 3-phase audit from the deck — state init, context
distraction, state extraction — against a scripted fake client, so you can
verify the memory loop works without spending API credits:

```bash
python3 chatbot.py --test
```

## How it maps to the project requirements

| Requirement (from the brief) | Where it lives |
|---|---|
| Connect to a frontier LLM via official SDK | `anthropic.Anthropic(api_key=...)` in `repl()` |
| In-memory list/array for history | `ChatSession.history` |
| Append every user input + model response | `ChatSession.send()` — "Terminal Append Sequence" |
| Block empty/whitespace payloads | `ChatSession.validate_input()` — "Structural Validation Gate" |
| Handle context window growth | `ChatSession._prune_history()` — FIFO sliding window, `--max-turns` |

## Notes / extensions

- The sliding window currently prunes by **turn count** (`--max-turns`).
  A natural next step (mentioned in the deck's conclusion) is pruning by
  **estimated token count** instead, so the window adapts to message length
  rather than a fixed number of turns.
- For persistence beyond a single process (surviving restarts, multiple
  users), the deck's later slides cover swapping the in-memory list for
  PostgreSQL, Firestore, or Firebase SQL Connect — this script intentionally
  keeps state in RAM, matching the Project 1 scope ("during a live session").

---

Built as part of the [DecodeLabs](https://www.decodelabs.tech) Generative AI
Industrial Training Kit, Batch 2026.
